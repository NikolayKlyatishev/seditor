#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod api;
mod core;
mod error;

use tauri::{api::path::app_data_dir, Manager};

use core::settings::load_settings;
use core::state::AppState;
use error::AppError;

/// Инициализирует состояние приложения
fn initialise_state(app: &tauri::App) -> Result<AppState, AppError> {
    let current_dir = std::env::current_dir()?;
    let app_handle = app.handle();
    
    let mut settings_path = app_data_dir(&app_handle.config())
        .ok_or(AppError::AppDataDirNotFound)?;
    settings_path.push("settings.json");
    
    let settings = load_settings(&settings_path).unwrap_or_default();
    
    Ok(AppState {
        current_dir: parking_lot::Mutex::new(current_dir),
        settings: parking_lot::Mutex::new(settings),
        settings_path,
    })
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let state = initialise_state(app).map_err(|error| {
                tauri::Error::FailedToExecuteApi(tauri::api::Error::Io(std::io::Error::new(
                    std::io::ErrorKind::Other,
                    error.to_string(),
                )))
            })?;
            app.manage(state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            api::settings::get_settings,
            api::settings::update_settings,
            api::terminal::run_terminal_command,
            api::terminal::get_directory_tree,
            api::terminal::read_file,
            api::chat::query_ollama_cmd,
        ])
        .run(tauri::generate_context!())
        .expect("Не удалось запустить приложение Tauri");
}
