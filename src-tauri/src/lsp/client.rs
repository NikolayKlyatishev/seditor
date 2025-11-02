use lsp_types::*;
use serde_json::Value;
use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{ChildStdin, ChildStdout, Command};
use tokio::sync::{Mutex, RwLock};

use crate::lsp::servers::LanguageServer;

type RequestId = u64;
type ResponseSender = tokio::sync::oneshot::Sender<Result<Value, String>>;

#[derive(Clone)]
pub struct LspClient {
    server_config: LanguageServer,
    stdin: Option<Arc<Mutex<ChildStdin>>>,
    request_id: Arc<AtomicU64>,
    pending_requests: Arc<RwLock<HashMap<RequestId, ResponseSender>>>,
    initialized: Arc<RwLock<bool>>,
}

impl LspClient {
    pub fn new(server_config: LanguageServer) -> Self {
        Self {
            server_config,
            stdin: None,
            request_id: Arc::new(AtomicU64::new(1)),
            pending_requests: Arc::new(RwLock::new(HashMap::new())),
            initialized: Arc::new(RwLock::new(false)),
        }
    }
    
    pub async fn start(&mut self, root_path: PathBuf) -> Result<(), String> {
        let mut cmd = Command::new(&self.server_config.command);
        cmd.args(&self.server_config.args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        
        let mut child = cmd.spawn().map_err(|e| format!("Failed to spawn LSP server: {}", e))?;
        
        let stdin = child.stdin.take().ok_or("Failed to get stdin")?;
        let stdout = child.stdout.take().ok_or("Failed to get stdout")?;
        
        self.stdin = Some(Arc::new(Mutex::new(stdin)));
        
        // Spawn child process in background (we won't track it directly)
        tokio::spawn(async move {
            let _ = child.wait().await;
        });
        
        // Start reading responses
        self.start_response_reader(stdout);
        
        // Initialize the server
        self.initialize(root_path).await?;
        
        Ok(())
    }
    
    fn start_response_reader(&self, stdout: ChildStdout) {
        let pending_requests = self.pending_requests.clone();
        
        tokio::spawn(async move {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();
            
            let mut content_length = 0;
            
            while let Ok(Some(line)) = lines.next_line().await {
                if line.starts_with("Content-Length:") {
                    if let Some(len_str) = line.strip_prefix("Content-Length:").map(|s| s.trim()) {
                        content_length = len_str.parse().unwrap_or(0);
                    }
                } else if line.is_empty() && content_length > 0 {
                    // Read the JSON content
                    let buffer = vec![0u8; content_length];
                    // Note: This is simplified - in production, use proper async reading
                    content_length = 0;
                    
                    if let Ok(json_str) = String::from_utf8(buffer) {
                        if let Ok(response) = serde_json::from_str::<Value>(&json_str) {
                            Self::handle_response(response, &pending_requests).await;
                        }
                    }
                }
            }
        });
    }
    
    async fn handle_response(
        response: Value,
        pending_requests: &Arc<RwLock<HashMap<RequestId, ResponseSender>>>,
    ) {
        if let Some(id) = response.get("id").and_then(|v| v.as_u64()) {
            let mut requests = pending_requests.write().await;
            if let Some(sender) = requests.remove(&id) {
                if let Some(result) = response.get("result") {
                    let _ = sender.send(Ok(result.clone()));
                } else if let Some(error) = response.get("error") {
                    let _ = sender.send(Err(error.to_string()));
                }
            }
        }
    }
    
    async fn send_request(&self, method: &str, params: Value) -> Result<Value, String> {
        let id = self.request_id.fetch_add(1, Ordering::SeqCst);
        
        let request = serde_json::json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params,
        });
        
        let (tx, rx) = tokio::sync::oneshot::channel();
        self.pending_requests.write().await.insert(id, tx);
        
        self.send_message(&request).await?;
        
        rx.await.map_err(|_| "Request cancelled".to_string())?
    }
    
    async fn send_message(&self, message: &Value) -> Result<(), String> {
        let content = serde_json::to_string(message).map_err(|e| e.to_string())?;
        let header = format!("Content-Length: {}\r\n\r\n", content.len());
        
        if let Some(stdin) = &self.stdin {
            let mut stdin = stdin.lock().await;
            stdin
                .write_all(header.as_bytes())
                .await
                .map_err(|e| e.to_string())?;
            stdin
                .write_all(content.as_bytes())
                .await
                .map_err(|e| e.to_string())?;
            stdin.flush().await.map_err(|e| e.to_string())?;
        }
        
        Ok(())
    }
    
    async fn initialize(&self, root_path: PathBuf) -> Result<(), String> {
        let params = serde_json::json!({
            "processId": std::process::id(),
            "rootPath": root_path,
            "rootUri": format!("file://{}", root_path.display()),
            "capabilities": {},
        });
        
        self.send_request("initialize", params).await?;
        
        // Send initialized notification
        let initialized = serde_json::json!({
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {},
        });
        self.send_message(&initialized).await?;
        
        *self.initialized.write().await = true;
        
        Ok(())
    }
    
    pub async fn goto_definition(
        &self,
        file_path: &str,
        line: u32,
        character: u32,
    ) -> Result<Option<Location>, String> {
        if !*self.initialized.read().await {
            return Err("LSP not initialized".to_string());
        }
        
        let params = serde_json::json!({
            "textDocument": {
                "uri": format!("file://{}", file_path),
            },
            "position": {
                "line": line,
                "character": character,
            },
        });
        
        let response = self.send_request("textDocument/definition", params).await?;
        
        // Parse response
        if response.is_null() {
            return Ok(None);
        }
        
        // Response can be Location | Location[] | LocationLink[]
        if let Ok(location) = serde_json::from_value::<Location>(response.clone()) {
            return Ok(Some(location));
        }
        
        if let Ok(locations) = serde_json::from_value::<Vec<Location>>(response) {
            return Ok(locations.into_iter().next());
        }
        
        Ok(None)
    }
    
    pub async fn shutdown(&mut self) -> Result<(), String> {
        if *self.initialized.read().await {
            let _ = self.send_request("shutdown", serde_json::json!({})).await;
            
            let exit = serde_json::json!({
                "jsonrpc": "2.0",
                "method": "exit",
                "params": {},
            });
            let _ = self.send_message(&exit).await;
        }
        
        *self.initialized.write().await = false;
        self.stdin = None;
        
        Ok(())
    }
}

