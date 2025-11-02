use std::io;
use thiserror::Error;

/// Основной тип ошибок приложения
#[derive(Debug, Error)]
pub enum AppError {
    #[error("Ошибка ввода-вывода: {0}")]
    Io(#[from] io::Error),

    #[error("Ошибка сериализации JSON: {0}")]
    Json(#[from] serde_json::Error),

    #[error("Ошибка HTTP-запроса: {0}")]
    Http(#[from] reqwest::Error),

    #[error("Общая ошибка: {0}")]
    Anyhow(#[from] anyhow::Error),

    #[error("Команда не должна быть пустой")]
    EmptyCommand,

    #[error("Не удалось перейти в каталог: {0}")]
    DirectoryChange(String),

    #[error("Указанный путь не является директорией")]
    NotADirectory,

    #[error("Доступ к файлу запрещён")]
    AccessDenied,

    #[error("Не удалось определить каталог данных приложения")]
    AppDataDirNotFound,

    #[error("Не удалось определить домашний каталог")]
    HomeDirNotFound,

    #[error("Не удалось сохранить настройки: {0}")]
    SettingsSave(String),

    #[error("Не удалось построить дерево файлов: {0}")]
    FileTreeBuild(String),

    #[error("Не удалось открыть файл: {0}")]
    FileOpen(String),

    #[error("Не удалось прочитать файл: {0}")]
    FileRead(String),

    #[error("Ошибка исполнения команды: {0}")]
    CommandExecution(String),

    #[error("Ошибка запуска команды: {0}")]
    CommandSpawn(String),

    #[error("Ошибка Ollama: {0}")]
    OllamaRequest(String),

    #[error("Ollama вернула статус {0}")]
    OllamaStatus(u16),

    #[error("Ошибка чтения ответа Ollama: {0}")]
    OllamaResponse(String),
}

/// Результат операции приложения
pub type AppResult<T> = Result<T, AppError>;

impl From<AppError> for String {
    fn from(error: AppError) -> Self {
        error.to_string()
    }
}

