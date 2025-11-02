use tauri::State;

use crate::core::settings::save_settings;
use crate::core::state::{AppSettings, AppState, Mode, SettingsUpdate};
use crate::error::AppError;

/// Получает текущие настройки приложения
#[tauri::command]
pub fn get_settings(state: State<'_, AppState>) -> AppSettings {
    state.settings.lock().clone()
}

/// Обновляет настройки приложения
#[tauri::command]
pub fn update_settings(
    state: State<'_, AppState>,
    data: SettingsUpdate,
) -> Result<AppSettings, String> {
    let mut settings = state.settings.lock();
    
    // Обновляем тему
    if let Some(theme_id) = data.theme_id {
        settings.theme_id = theme_id;
    }
    
    // Обновляем шрифт
    if let Some(font_family) = data.font_family {
        if !font_family.trim().is_empty() {
            settings.font_family = font_family;
        }
    }
    
    // Обновляем размер шрифта
    if let Some(font_size) = data.font_size {
        settings.font_size = font_size.clamp(10, 28);
    }
    
    // Обновляем режим
    if let Some(mode) = data.mode {
        settings.mode = Mode::from_str(&mode);
    }
    
    // Обновляем настройки Ollama
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

    // Сохраняем настройки
    save_settings(&state.settings_path, &settings)
        .map_err(|e| AppError::SettingsSave(e.to_string()).to_string())?;

    Ok(settings.clone())
}

