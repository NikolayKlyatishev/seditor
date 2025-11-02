use std::path::{Path, PathBuf};
use std::process::Command;

use once_cell::sync::Lazy;
use regex::Regex;

use crate::core::state::CommandResult;
use crate::error::{AppError, AppResult};

static CD_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^cd(?:\s+(?P<target>.+))?$").expect("invalid cd regex")
});

/// Извлекает целевую директорию из команды cd
pub fn extract_cd_target(command: &str) -> Option<String> {
    let command = command.trim();
    let captures = CD_REGEX.captures(command)?;
    let value = captures
        .name("target")
        .map(|m| m.as_str().trim().to_string())
        .filter(|target| !target.is_empty())
        .unwrap_or_else(|| "~".to_string());
    Some(value)
}

/// Разрешает целевую директорию относительно текущей
pub fn resolve_target_directory(current: &Path, target: &str) -> AppResult<PathBuf> {
    use directories::UserDirs;
    
    let target = target.trim();
    if target.is_empty() || target == "~" {
        UserDirs::new()
            .map(|dirs| dirs.home_dir().to_path_buf())
            .ok_or(AppError::HomeDirNotFound)
    } else if target.starts_with('/') {
        Ok(PathBuf::from(target))
    } else {
        Ok(current.join(target))
    }
}

/// Определяет пользовательский shell
fn get_user_shell() -> String {
    std::env::var("SHELL").unwrap_or_else(|_| "/bin/sh".to_string())
}

/// Выполняет команду в указанной директории через пользовательский shell
pub async fn execute_command(
    command: &str,
    current_dir: &PathBuf,
) -> AppResult<CommandResult> {
    let command = command.trim();
    if command.is_empty() {
        return Err(AppError::EmptyCommand);
    }

    let current_dir_for_output = current_dir.clone();
    let command_owned = command.to_string();
    let current_dir_owned = current_dir.clone();
    let shell = get_user_shell();
    
    let output = tauri::async_runtime::spawn_blocking(move || {
        // Используем login shell (-l) для загрузки профиля пользователя
        // и интерактивный режим (-i) для загрузки .zshrc и других конфигов
        Command::new(&shell)
            .arg("-l")  // login shell
            .arg("-i")  // interactive
            .arg("-c")  // command
            .arg(&command_owned)
            .current_dir(&current_dir_owned)
            .output()
    })
    .await
    .map_err(|e| AppError::CommandExecution(e.to_string()))?
    .map_err(|e| AppError::CommandSpawn(e.to_string()))?;

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();

    Ok(CommandResult {
        stdout,
        stderr,
        code: output.status.code(),
        current_dir: Some(current_dir_for_output.to_string_lossy().to_string()),
        file_tree: None,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_cd_target_without_argument() {
        assert_eq!(extract_cd_target("cd"), Some("~".to_string()));
    }

    #[test]
    fn test_extract_cd_target_with_argument() {
        assert_eq!(extract_cd_target("cd src"), Some("src".to_string()));
    }

    #[test]
    fn test_extract_cd_target_invalid() {
        assert!(extract_cd_target("ls").is_none());
    }
}

