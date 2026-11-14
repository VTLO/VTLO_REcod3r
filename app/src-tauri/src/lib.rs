//! Coque Tauri 2 : mêmes routes que le serveur local, exposées par une seule commande `api`.
use recod3r_core::api::App;
use serde_json::Value;

#[tauri::command]
fn api(app: tauri::State<'_, App>, route: String, body: Value) -> Value {
    app.handle(&route, &body)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(App::new())
        .invoke_handler(tauri::generate_handler![api])
        .run(tauri::generate_context!())
        .expect("erreur au lancement de VTLO_REcod3r");
}
