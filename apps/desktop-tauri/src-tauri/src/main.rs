const SERVICE_NAME: &str = "com.gooberberg.desktop";
const API_TOKEN_ACCOUNT: &str = "api_token";

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

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![save_api_token, get_api_token, delete_api_token])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
