use crate::state::{ChatResponse, OllamaChatResponse};

fn system_prompt(mode: &str) -> String {
    match mode {
        "agent" => "Ты выступаешь в роли технического помощника, который предлагает шаги и команды для решения задач разработки.".into(),
        "ide" => "Ты помогаешь разрабатывать и улучшать код, предлагая изменения и объяснения.".into(),
        _ => "Ты дружелюбный помощник, отвечающий кратко и по существу.".into(),
    }
}

pub async fn query_ollama(
    prompt: String,
    model: String,
    temperature: f32,
    mode: String,
) -> Result<ChatResponse, String> {
    let client = reqwest::Client::new();
    let payload = serde_json::json!({
        "model": model,
        "temperature": temperature,
        "stream": false,
        "messages": [
            {"role": "system", "content": system_prompt(&mode)},
            {"role": "user", "content": prompt}
        ]
    });

    let response = client
        .post("http://localhost:11434/api/chat")
        .json(&payload)
        .send()
        .await
        .map_err(|error| format!("Ошибка Ollama: {error}"))?;

    if !response.status().is_success() {
        return Err(format!("Ollama вернула статус {}", response.status()));
    }

    let body: OllamaChatResponse = response
        .json()
        .await
        .map_err(|error| format!("Ошибка чтения ответа Ollama: {error}"))?;

    Ok(ChatResponse {
        message: body.message.content,
    })
}
