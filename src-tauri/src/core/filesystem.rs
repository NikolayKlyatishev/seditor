use std::fs;
use std::path::Path;

use crate::core::state::FileNode;
use crate::error::AppResult;

/// Строит дерево файлов для указанной директории
pub fn build_file_tree(root: &Path, depth: usize) -> AppResult<Vec<FileNode>> {
    if depth == 0 {
        return Ok(vec![]);
    }

    let mut entries: Vec<FileNode> = fs::read_dir(root)?
        .filter_map(|entry| entry.ok())
        .filter_map(|entry| {
            let path = entry.path();
            let name = entry.file_name().to_string_lossy().to_string();
            
            // Пропускаем скрытые файлы
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

    // Сортируем: сначала директории, потом файлы
    entries.sort_by(|a, b| {
        match (a.is_dir, b.is_dir) {
            (true, false) => std::cmp::Ordering::Less,
            (false, true) => std::cmp::Ordering::Greater,
            _ => a.name.to_lowercase().cmp(&b.name.to_lowercase()),
        }
    });
    
    // Ограничиваем количество записей
    if entries.len() > 200 {
        entries.truncate(200);
    }
    
    Ok(entries)
}

