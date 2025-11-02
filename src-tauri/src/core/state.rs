use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Режим работы приложения
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Mode {
    Terminal,
    Ide,
    Chat,
    Agent,
}

impl Mode {
    /// Создаёт режим из строки
    pub fn from_str(value: &str) -> Self {
        match value.to_lowercase().as_str() {
            "ide" => Mode::Ide,
            "chat" => Mode::Chat,
            "agent" => Mode::Agent,
            _ => Mode::Terminal,
        }
    }

    /// Возвращает строковое представление режима
    pub fn as_str(&self) -> &'static str {
        match self {
            Mode::Terminal => "terminal",
            Mode::Ide => "ide",
            Mode::Chat => "chat",
            Mode::Agent => "agent",
        }
    }
}

impl Default for Mode {
    fn default() -> Self {
        Mode::Terminal
    }
}

/// Настройки Ollama
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct OllamaSettings {
    pub model: String,
    pub temperature: f32,
}

impl Default for OllamaSettings {
    fn default() -> Self {
        Self {
            model: "llama3".into(),
            temperature: 0.4,
        }
    }
}

/// Настройки приложения
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AppSettings {
    pub theme_id: String,
    pub font_family: String,
    pub font_size: u16,
    pub mode: Mode,
    pub ollama: OllamaSettings,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            theme_id: "graphite".into(),
            font_family: "IBM Plex Mono".into(),
            font_size: 15,
            mode: Mode::Terminal,
            ollama: OllamaSettings::default(),
        }
    }
}

/// Глобальное состояние приложения
pub struct AppState {
    pub current_dir: Mutex<PathBuf>,
    pub settings: Mutex<AppSettings>,
    pub settings_path: PathBuf,
}

/// Узел дерева файлов
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FileNode {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub children: Option<Vec<FileNode>>,
}

/// Результат выполнения команды
#[derive(Debug, Serialize)]
pub struct CommandResult {
    pub stdout: String,
    pub stderr: String,
    pub code: Option<i32>,
    pub current_dir: Option<String>,
    pub file_tree: Option<Vec<FileNode>>,
}

/// Обновление настроек (частичное)
#[derive(Debug, Deserialize)]
pub struct SettingsUpdate {
    #[serde(default)]
    pub theme_id: Option<String>,
    #[serde(default)]
    pub font_family: Option<String>,
    #[serde(default)]
    pub font_size: Option<u16>,
    #[serde(default)]
    pub mode: Option<String>,
    #[serde(default)]
    pub ollama: Option<OllamaSettingsUpdate>,
}

/// Обновление настроек Ollama (частичное)
#[derive(Debug, Deserialize)]
pub struct OllamaSettingsUpdate {
    #[serde(default)]
    pub model: Option<String>,
    #[serde(default)]
    pub temperature: Option<f32>,
}

/// Ответ от чата
#[derive(Debug, Serialize)]
pub struct ChatResponse {
    pub message: String,
}

/// Ответ от Ollama API
#[derive(Debug, Deserialize)]
pub struct OllamaChatResponse {
    pub message: OllamaChatMessage,
}

/// Сообщение от Ollama
#[derive(Debug, Deserialize)]
pub struct OllamaChatMessage {
    #[serde(default)]
    #[allow(dead_code)]
    pub role: Option<String>,
    pub content: String,
}

