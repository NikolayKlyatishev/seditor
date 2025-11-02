use anyhow::Context;
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

use crate::state::AppSettings;

pub fn load_settings(path: &Path) -> anyhow::Result<AppSettings> {
    if !path.exists() {
        return Ok(AppSettings::default());
    }
    let mut file = File::open(path).with_context(|| format!("Не удалось открыть {path:?}"))?;
    let mut contents = String::new();
    file.read_to_string(&mut contents)?;
    let settings: AppSettings = serde_json::from_str(&contents)?;
    Ok(settings)
}

pub fn save_settings(path: &Path, settings: &AppSettings) -> anyhow::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut file = File::create(path)?;
    file.write_all(serde_json::to_string_pretty(settings)?.as_bytes())?;
    Ok(())
}
