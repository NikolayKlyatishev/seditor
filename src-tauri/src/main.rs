#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod state;
mod settings;
mod commands;
mod chat;

use tauri::{api::path::app_data_dir, Manager, State};
use std::path::PathBuf;

use state::{AppState, AppSettings, SettingsUpdate, CommandResult, ChatResponse};
use settings::{load_settings, save_settings};
use commands::{extract_cd_target, resolve_target_directory, build_file_tree, execute_command};
use chat::query_ollama;

#[tauri::command]
fn get_settings(state: State<'_, AppState>) -> AppSettings {
    state.settings.lock().clone()
}

#[tauri::command]
fn update_settings(state: State<'_, AppState>, data: SettingsUpdate) -> Result<AppSettings, String> {
    let mut settings = state.settings.lock();
    if let Some(theme_id) = data.theme_id {
        settings.theme_id = theme_id;
    }
    if let Some(font_family) = data.font_family {
        if !font_family.trim().is_empty() {
            settings.font_family = font_family;
        }
    }
    if let Some(font_size) = data.font_size {
        settings.font_size = font_size.clamp(10, 28);
    }
    if let Some(mode) = data.mode {
        settings.mode = state::Mode::from_str(&mode);
    }
    if let Some(ollama) = data.ollama {
        if let Some(model) = ollama.model {
            if !model.trim().is_empty() {
                settings.ollama.model = model;
            }
        }
        if let Some(temperature) = ollama.temperature {
            settings.ollama.temperature = temperature.clamp(0.0, 2.0);
        }
    }

    if let Err(error) = save_settings(&state.settings_path, &settings) {
        return Err(format!("Не удалось сохранить настройки: {error}"));
    }

    Ok(settings.clone())
}

#[tauri::command]
async fn run_terminal_command(state: State<'_, AppState>, command: String) -> Result<CommandResult, String> {
    let command = command.trim();
    if command.is_empty() {
        return Err("Команда не должна быть пустой".into());
    }

    if let Some(target) = extract_cd_target(command) {
        let mut current_dir = state.current_dir.lock();
        let new_dir = resolve_target_directory(&current_dir, &target)
            .and_then(|dir| dir.canonicalize().map_err(|error| anyhow::anyhow!(error)))
            .map_err(|error| format!("Не удалось перейти в каталог: {error}"))?;

        if !new_dir.is_dir() {
            return Err("Указанный путь не является директорией".into());
        }

        *current_dir = new_dir.clone();
        drop(current_dir);

        let file_tree = build_file_tree(&new_dir, 2)
            .map_err(|error| format!("Не удалось построить дерево файлов: {error}"))?;

        return Ok(CommandResult {
            stdout: format!("Перешли в {}", new_dir.to_string_lossy()),
            stderr: String::new(),
            code: None,
            current_dir: Some(new_dir.to_string_lossy().to_string()),
            file_tree: Some(file_tree),
        });
    }

    let current_dir = state.current_dir.lock().clone();
    execute_command(command, &current_dir).await
}

#[tauri::command]
async fn query_ollama_cmd(
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

    query_ollama(prompt, model, temperature, mode).await
}

#[tauri::command]
fn read_file(state: State<'_, AppState>, path: String) -> Result<String, String> {
    let current_dir = state.current_dir.lock().clone();
    let absolute = PathBuf::from(path);
    let canonical = absolute
        .canonicalize()
        .map_err(|error| format!("Не удалось открыть файл: {error}"))?;
    if !canonical.starts_with(&current_dir) {
        return Err("Доступ к файлу запрещён".into());
    }
    let mut file = std::fs::File::open(&canonical).map_err(|error| format!("Не удалось открыть файл: {error}"))?;
    let mut content = String::new();
    file.read_to_string(&mut content)
        .map_err(|error| format!("Не удалось прочитать файл: {error}"))?;
    Ok(content)
}

fn initialise_state(app: &tauri::App) -> anyhow::Result<AppState> {
    let current_dir = std::env::current_dir()?;
    let app_handle = app.handle();
    let mut settings_path = app_data_dir(&app_handle.config()).context("Не удалось определить каталог данных приложения")?;
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
            get_settings,
            update_settings,
            run_terminal_command,
            query_ollama_cmd,
            read_file
        ])
        .run(tauri::generate_context!())
        .expect("Не удалось запустить приложение Tauri");
}

#[cfg(test)]
mod tests {
    use super::commands::extract_cd_target;

    #[test]
    fn extract_cd_target_without_argument() {
        assert_eq!(extract_cd_target("cd"), Some("~".to_string()));
    }

    #[test]
    fn extract_cd_target_with_argument() {
        assert_eq!(extract_cd_target("cd src"), Some("src".to_string()));
    }

    #[test]
    fn extract_cd_target_invalid() {
        assert!(extract_cd_target("ls").is_none());
    }
}

