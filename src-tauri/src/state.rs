use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Mode {
    Terminal,
    Ide,
    Chat,
    Agent,
}

impl Mode {
    pub fn from_str(value: &str) -> Self {
        match value.to_lowercase().as_str() {
            "ide" => Mode::Ide,
            "chat" => Mode::Chat,
            "agent" => Mode::Agent,
            _ => Mode::Terminal,
        }
    }

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

#[derive(Clone, Serialize, Deserialize)]
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

#[derive(Clone, Serialize, Deserialize)]
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

pub struct AppState {
    pub current_dir: Mutex<PathBuf>,
    pub settings: Mutex<AppSettings>,
    pub settings_path: PathBuf,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct FileNode {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub children: Option<Vec<FileNode>>,
}

#[derive(Serialize)]
pub struct CommandResult {
    pub stdout: String,
    pub stderr: String,
    pub code: Option<i32>,
    pub current_dir: Option<String>,
    pub file_tree: Option<Vec<FileNode>>,
}

#[derive(Deserialize)]
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

#[derive(Deserialize)]
pub struct OllamaSettingsUpdate {
    #[serde(default)]
    pub model: Option<String>,
    #[serde(default)]
    pub temperature: Option<f32>,
}

#[derive(Serialize)]
pub struct ChatResponse {
    pub message: String,
}

#[derive(Deserialize)]
pub struct OllamaChatResponse {
    pub message: OllamaChatMessage,
}

#[derive(Deserialize)]
pub struct OllamaChatMessage {
    #[serde(default)]
    pub role: Option<String>,
    pub content: String,
}
