use crate::lsp::servers::{Language, LanguageServer};

/// Проверяет, установлен ли LSP сервер для языка
#[tauri::command]
pub fn check_lsp_server(language: String) -> Result<bool, String> {
    let lang = match language.as_str() {
        "rust" => Language::Rust,
        "javascript" => Language::JavaScript,
        "typescript" => Language::TypeScript,
        "python" => Language::Python,
        "java" => Language::Java,
        _ => return Ok(false),
    };
    
    let server = LanguageServer::for_language(lang);
    Ok(server.is_installed())
}

/// Получает инструкции по установке LSP сервера
#[tauri::command]
pub fn get_lsp_installation_instructions(language: String) -> Result<String, String> {
    let lang = match language.as_str() {
        "rust" => Language::Rust,
        "javascript" => Language::JavaScript,
        "typescript" => Language::TypeScript,
        "python" => Language::Python,
        "java" => Language::Java,
        _ => return Err("Unknown language".to_string()),
    };
    
    let server = LanguageServer::for_language(lang);
    Ok(server.installation_instructions())
}

// Note: Full LSP implementation with goto_definition would require:
// 1. Managing LSP server processes per project
// 2. Handling LSP protocol messages
// 3. Maintaining document synchronization
// 4. Managing server lifecycle
//
// For now, we provide the infrastructure. Full implementation
// can be added incrementally as needed.

