#[tauri::command]
fn save_api_token(_token: String) -> Result<(), String> {
    // Integration point: wire this command to OS keychain/credential vault.
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![save_api_token])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
