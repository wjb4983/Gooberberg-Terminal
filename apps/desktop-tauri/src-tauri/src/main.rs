use std::time::Duration;

use serde::{Deserialize, Serialize};

const SERVICE_NAME: &str = "com.gooberberg.desktop";
const API_TOKEN_ACCOUNT: &str = "api_token";

#[derive(Debug, Deserialize)]
struct ApiHttpRequest {
    method: String,
    url: String,
    headers: Vec<(String, String)>,
    body: Option<String>,
}

#[derive(Debug, Serialize)]
struct ApiHttpResponse {
    status: u16,
    body: String,
}

#[tauri::command]
fn save_api_token(token: String) -> Result<(), String> {
    let entry = keyring::Entry::new(SERVICE_NAME, API_TOKEN_ACCOUNT).map_err(|error| error.to_string())?;
    entry
        .set_password(&token)
        .map_err(|error| format!("failed to save token to secure keychain: {error}"))
}

#[tauri::command]
fn get_api_token() -> Result<String, String> {
    let entry = keyring::Entry::new(SERVICE_NAME, API_TOKEN_ACCOUNT).map_err(|error| error.to_string())?;
    match entry.get_password() {
        Ok(token) => Ok(token),
        Err(keyring::Error::NoEntry) => Ok(String::new()),
        Err(error) => Err(format!("failed to read token from secure keychain: {error}")),
    }
}

#[tauri::command]
fn delete_api_token() -> Result<(), String> {
    let entry = keyring::Entry::new(SERVICE_NAME, API_TOKEN_ACCOUNT).map_err(|error| error.to_string())?;
    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()),
        Err(error) => Err(format!("failed to delete token from secure keychain: {error}")),
    }
}

#[tauri::command]
async fn api_http_request(request: ApiHttpRequest) -> Result<ApiHttpResponse, String> {
    let method = request
        .method
        .parse::<reqwest::Method>()
        .map_err(|error| format!("invalid HTTP method: {error}"))?;

    let url = reqwest::Url::parse(&request.url).map_err(|error| format!("invalid API URL: {error}"))?;
    if url.scheme() != "http" && url.scheme() != "https" {
        return Err("API URL must use http or https".to_string());
    }

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|error| format!("failed to create HTTP client: {error}"))?;

    let mut builder = client.request(method, url);
    for (name, value) in request.headers {
        builder = builder.header(name, value);
    }
    if let Some(body) = request.body {
        builder = builder.body(body);
    }

    let response = builder
        .send()
        .await
        .map_err(|error| format!("API request failed: {error}"))?;
    let status = response.status().as_u16();
    let body = response
        .text()
        .await
        .map_err(|error| format!("failed to read API response: {error}"))?;

    Ok(ApiHttpResponse { status, body })
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            save_api_token,
            get_api_token,
            delete_api_token,
            api_http_request
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
