use tauri::State;

use crate::core::chat::query_ollama;
use crate::core::state::{AppState, ChatResponse};

/// Отправляет запрос к Ollama
#[tauri::command]
pub async fn query_ollama_cmd(
    state: State<'_, AppState>,
    prompt: String,
    mode: Option<String>,
    model: Option<String>,
    temperature: Option<f32>,
) -> Result<ChatResponse, String> {
    let settings = state.settings.lock().clone();
    let model = model.unwrap_or_else(|| settings.ollama.model.clone());
    let temperature = temperature.unwrap_or(settings.ollama.temperature);
    let mode = mode.unwrap_or_else(|| settings.mode.as_str().to_string());

    query_ollama(prompt, model, temperature, mode)
        .await
        .map_err(|e| e.to_string())
}

