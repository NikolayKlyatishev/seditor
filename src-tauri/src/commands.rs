use std::process::Command;
use std::path::{Path, PathBuf};
use std::fs;
use anyhow::Context;
use once_cell::sync::Lazy;
use regex::Regex;

use crate::state::{CommandResult, FileNode};

static CD_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^cd(?:\s+(?P<target>.+))?$").expect("invalid cd regex")
});

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

pub fn resolve_target_directory(current: &Path, target: &str) -> anyhow::Result<PathBuf> {
    use directories::UserDirs;
    
    let target = target.trim();
    if target.is_empty() || target == "~" {
        UserDirs::new()
            .map(|dirs| dirs.home_dir().to_path_buf())
            .context("Не удалось определить домашний каталог")
    } else if target.starts_with('/') {
        Ok(PathBuf::from(target))
    } else {
        Ok(current.join(target))
    }
}

pub fn build_file_tree(root: &Path, depth: usize) -> anyhow::Result<Vec<FileNode>> {
    if depth == 0 {
        return Ok(vec![]);
    }

    let mut entries: Vec<FileNode> = fs::read_dir(root)?
        .filter_map(|entry| entry.ok())
        .filter_map(|entry| {
            let path = entry.path();
            let name = entry.file_name().to_string_lossy().to_string();
            if name.starts_with('.') {
                return None;
            }
            let is_dir = path.is_dir();
            let children = if is_dir {
                match build_file_tree(&path, depth - 1) {
                    Ok(children) => Some(children),
                    Err(_) => Some(vec![]),
                }
            } else {
                None
            };
            Some(FileNode {
                name,
                path: path.to_string_lossy().to_string(),
                is_dir,
                children,
            })
        })
        .collect();

    entries.sort_by(|a, b| {
        match (a.is_dir, b.is_dir) {
            (true, false) => std::cmp::Ordering::Less,
            (false, true) => std::cmp::Ordering::Greater,
            _ => a.name.to_lowercase().cmp(&b.name.to_lowercase()),
        }
    });
    if entries.len() > 200 {
        entries.truncate(200);
    }
    Ok(entries)
}

pub async fn execute_command(
    command: &str,
    current_dir: &PathBuf,
) -> Result<CommandResult, String> {
    let command = command.trim();
    if command.is_empty() {
        return Err("Команда не должна быть пустой".into());
    }

    let current_dir_for_output = current_dir.clone();
    let command_owned = command.to_string();
    let output = tauri::async_runtime::spawn_blocking(move || {
        Command::new("/bin/sh")
            .arg("-c")
            .arg(&command_owned)
            .current_dir(current_dir)
            .output()
    })
    .await
    .map_err(|error| format!("Ошибка исполнения: {error}"))
    .and_then(|result| result.map_err(|error| format!("Ошибка запуска команды: {error}")))?;

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
