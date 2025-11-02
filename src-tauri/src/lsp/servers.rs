use std::process::Command;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Language {
    Rust,
    JavaScript,
    TypeScript,
    Python,
    Java,
}

impl Language {
    pub fn from_extension(ext: &str) -> Option<Self> {
        match ext.to_lowercase().as_str() {
            "rs" => Some(Language::Rust),
            "js" | "jsx" => Some(Language::JavaScript),
            "ts" | "tsx" => Some(Language::TypeScript),
            "py" => Some(Language::Python),
            "java" => Some(Language::Java),
            _ => None,
        }
    }
    
    pub fn as_str(&self) -> &str {
        match self {
            Language::Rust => "rust",
            Language::JavaScript => "javascript",
            Language::TypeScript => "typescript",
            Language::Python => "python",
            Language::Java => "java",
        }
    }
}

#[derive(Debug, Clone)]
pub struct LanguageServer {
    pub language: Language,
    pub command: String,
    pub args: Vec<String>,
    pub name: String,
}

impl LanguageServer {
    pub fn for_language(language: Language) -> Self {
        match language {
            Language::Rust => Self {
                language,
                command: "rust-analyzer".to_string(),
                args: vec![],
                name: "rust-analyzer".to_string(),
            },
            Language::JavaScript | Language::TypeScript => Self {
                language,
                command: "typescript-language-server".to_string(),
                args: vec!["--stdio".to_string()],
                name: "typescript-language-server".to_string(),
            },
            Language::Python => Self {
                language,
                command: "pyright-langserver".to_string(),
                args: vec!["--stdio".to_string()],
                name: "Pyright".to_string(),
            },
            Language::Java => Self {
                language,
                command: "jdtls".to_string(),
                args: vec![],
                name: "Eclipse JDT LS".to_string(),
            },
        }
    }
    
    /// Check if the LSP server is installed
    pub fn is_installed(&self) -> bool {
        Command::new("which")
            .arg(&self.command)
            .output()
            .map(|output| output.status.success())
            .unwrap_or(false)
    }
    
    /// Get installation instructions
    pub fn installation_instructions(&self) -> String {
        match self.language {
            Language::Rust => {
                "Install rust-analyzer:\n\
                 - Via rustup: rustup component add rust-analyzer\n\
                 - Or download from: https://rust-analyzer.github.io/".to_string()
            }
            Language::JavaScript | Language::TypeScript => {
                "Install typescript-language-server:\n\
                 npm install -g typescript-language-server typescript".to_string()
            }
            Language::Python => {
                "Install Pyright:\n\
                 npm install -g pyright".to_string()
            }
            Language::Java => {
                "Install Eclipse JDT Language Server:\n\
                 Download from: https://download.eclipse.org/jdtls/snapshots/".to_string()
            }
        }
    }
}

