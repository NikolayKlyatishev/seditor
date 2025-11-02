use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

use crate::core::state::AppSettings;
use crate::error::{AppError, AppResult};

/// Загружает настройки из файла
pub fn load_settings(path: &Path) -> AppResult<AppSettings> {
    if !path.exists() {
        return Ok(AppSettings::default());
    }
    
    let mut file = File::open(path).map_err(|e| {
        AppError::FileOpen(format!("Не удалось открыть {path:?}: {e}"))
    })?;
    
    let mut contents = String::new();
    file.read_to_string(&mut contents)
        .map_err(|e| AppError::FileRead(format!("Не удалось прочитать {path:?}: {e}")))?;
    
    let settings: AppSettings = serde_json::from_str(&contents)?;
    Ok(settings)
}

/// Сохраняет настройки в файл
pub fn save_settings(path: &Path, settings: &AppSettings) -> AppResult<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    
    let mut file = File::create(path)?;
    file.write_all(serde_json::to_string_pretty(settings)?.as_bytes())?;
    Ok(())
}

