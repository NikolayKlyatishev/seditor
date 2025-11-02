use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::lsp::client::LspClient;
use crate::lsp::servers::{Language, LanguageServer};

pub struct LspManager {
    clients: Arc<RwLock<HashMap<Language, LspClient>>>,
    root_path: PathBuf,
}

impl LspManager {
    pub fn new(root_path: PathBuf) -> Self {
        Self {
            clients: Arc::new(RwLock::new(HashMap::new())),
            root_path,
        }
    }
    
    pub async fn start_server(&self, language: Language) -> Result<(), String> {
        let server_config = LanguageServer::for_language(language.clone());
        
        if !server_config.is_installed() {
            return Err(format!(
                "LSP server not installed: {}\n\n{}",
                server_config.name,
                server_config.installation_instructions()
            ));
        }
        
        let mut client = LspClient::new(server_config);
        client.start(self.root_path.clone()).await?;
        
        self.clients.write().await.insert(language, client);
        
        Ok(())
    }
    
    pub async fn get_client(&self, language: &Language) -> Option<LspClient> {
        self.clients.read().await.get(language).cloned()
    }
    
    pub async fn is_running(&self, language: &Language) -> bool {
        self.clients.read().await.contains_key(language)
    }
    
    pub async fn shutdown_server(&self, language: &Language) -> Result<(), String> {
        if let Some(mut client) = self.clients.write().await.remove(language) {
            client.shutdown().await?;
        }
        Ok(())
    }
    
    pub async fn shutdown_all(&self) -> Result<(), String> {
        let mut clients = self.clients.write().await;
        for (_, mut client) in clients.drain() {
            let _ = client.shutdown().await;
        }
        Ok(())
    }
}

