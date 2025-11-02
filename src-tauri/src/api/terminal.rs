use std::io::Read;
use std::path::PathBuf;
use tauri::State;

use crate::core::filesystem::build_file_tree;
use crate::core::state::{AppState, CommandResult};
use crate::core::terminal::{execute_command, extract_cd_target, resolve_target_directory};
use crate::error::AppError;

/// Выполняет команду терминала
#[tauri::command]
pub async fn run_terminal_command(
    state: State<'_, AppState>,
    command: String,
) -> Result<CommandResult, String> {
    let command = command.trim();
    if command.is_empty() {
        return Err(AppError::EmptyCommand.to_string());
    }

    // Обрабатываем команду cd отдельно
    if let Some(target) = extract_cd_target(command) {
        let mut current_dir = state.current_dir.lock();
        let new_dir = resolve_target_directory(&current_dir, &target)
            .and_then(|dir| {
                dir.canonicalize()
                    .map_err(|e| AppError::DirectoryChange(e.to_string()))
            })
            .map_err(|e| e.to_string())?;

        if !new_dir.is_dir() {
            return Err(AppError::NotADirectory.to_string());
        }

        *current_dir = new_dir.clone();
        drop(current_dir);

        let file_tree = build_file_tree(&new_dir, 2)
            .map_err(|e| AppError::FileTreeBuild(e.to_string()).to_string())?;

        return Ok(CommandResult {
            stdout: format!("Перешли в {}", new_dir.to_string_lossy()),
            stderr: String::new(),
            code: None,
            current_dir: Some(new_dir.to_string_lossy().to_string()),
            file_tree: Some(file_tree),
        });
    }

    // Выполняем обычную команду
    let current_dir = state.current_dir.lock().clone();
    execute_command(command, &current_dir)
        .await
        .map_err(|e| e.to_string())
}

/// Получает дерево файлов для указанной директории
#[tauri::command]
pub fn get_directory_tree(state: State<'_, AppState>, path: String) -> Result<Vec<crate::core::state::FileNode>, String> {
    let current_dir = state.current_dir.lock().clone();
    let dir_path = PathBuf::from(&path);
    
    let canonical = dir_path
        .canonicalize()
        .map_err(|e| format!("Не удалось открыть каталог: {}", e))?;
    
    // Проверяем, что каталог находится в текущей директории или является её родителем
    if !canonical.starts_with(&current_dir) && !current_dir.starts_with(&canonical) {
        return Err(AppError::AccessDenied.to_string());
    }
    
    if !canonical.is_dir() {
        return Err(AppError::NotADirectory.to_string());
    }
    
    let file_tree = build_file_tree(&canonical, 1)
        .map_err(|e| AppError::FileTreeBuild(e.to_string()).to_string())?;
    
    Ok(file_tree)
}

/// Читает содержимое файла
#[tauri::command]
pub fn read_file(state: State<'_, AppState>, path: String) -> Result<String, String> {
    let current_dir = state.current_dir.lock().clone();
    let absolute = PathBuf::from(path);
    
    let canonical = absolute
        .canonicalize()
        .map_err(|e| AppError::FileOpen(e.to_string()).to_string())?;
    
    // Проверяем, что файл находится в текущей директории
    if !canonical.starts_with(&current_dir) {
        return Err(AppError::AccessDenied.to_string());
    }
    
    let mut file = std::fs::File::open(&canonical)
        .map_err(|e| AppError::FileOpen(e.to_string()).to_string())?;
    
    let mut content = String::new();
    file.read_to_string(&mut content)
        .map_err(|e| AppError::FileRead(e.to_string()).to_string())?;
    
    Ok(content)
}

