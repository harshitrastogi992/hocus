mod engine;

use tauri::{Manager, RunEvent};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(engine::EngineState::default())
        .invoke_handler(tauri::generate_handler![
            engine::engine_info,
            engine::restart_engine
        ])
        .setup(|app| {
            if let Err(error) = engine::start(app.handle()) {
                let state = app.state::<engine::EngineState>();
                state.info.lock().unwrap().error = Some(error);
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building the Hocus app");
    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            engine::stop(handle);
        }
    });
}
