//! Starts the Python engine next to the window and tells the UI where to find it.

use std::sync::Mutex;

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};

#[derive(Clone, Default, Serialize)]
pub struct EngineInfo {
    pub url: Option<String>,
    pub error: Option<String>,
}

#[derive(Default)]
pub struct EngineState {
    pub info: Mutex<EngineInfo>,
    pub child: Mutex<Option<CommandChild>>,
}

const SERVE_ARGS: [&str; 5] = [
    "serve",
    "--port",
    "0",
    "--exit-with-stdin",
    "--host=127.0.0.1",
];

pub fn start(app: &AppHandle) -> Result<(), String> {
    let token = uuid::Uuid::new_v4().simple().to_string();
    let command = if cfg!(debug_assertions) {
        // Development: run the engine from its virtualenv so Python edits apply on restart.
        let python = std::env::var("HOCUS_PYTHON").unwrap_or_else(|_| dev_python());
        app.shell()
            .command(python)
            .args(["-m", "hocus"])
            .args(SERVE_ARGS)
    } else {
        app.shell()
            .sidecar("hocus-engine")
            .map_err(|e| e.to_string())?
            .args(SERVE_ARGS)
    };
    let (mut events, child) = command
        .env("HOCUS_TOKEN", &token)
        .spawn()
        .map_err(|e| format!("Could not start the Hocus engine: {e}"))?;

    let state = app.state::<EngineState>();
    *state.child.lock().unwrap() = Some(child);

    let app = app.clone();
    tauri::async_runtime::spawn(async move {
        let mut stderr_tail: Vec<String> = Vec::new();
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let line = String::from_utf8_lossy(&line).trim().to_string();
                    if let Some(port) = line.strip_prefix("HOCUS_READY ") {
                        let url = format!("ws://127.0.0.1:{port}/?token={token}");
                        set_info(&app, Some(url), None);
                    }
                }
                CommandEvent::Stderr(line) => {
                    let line = String::from_utf8_lossy(&line).trim().to_string();
                    eprintln!("[engine] {line}");
                    stderr_tail.push(line);
                    if stderr_tail.len() > 12 {
                        stderr_tail.remove(0);
                    }
                }
                CommandEvent::Terminated(status) => {
                    let detail = stderr_tail.join("\n");
                    let message = format!(
                        "The Hocus engine stopped (exit code {:?}).{}",
                        status.code,
                        if detail.is_empty() {
                            String::new()
                        } else {
                            format!("\n\n{detail}")
                        }
                    );
                    set_info(&app, None, Some(message));
                }
                _ => {}
            }
        }
    });
    Ok(())
}

fn set_info(app: &AppHandle, url: Option<String>, error: Option<String>) {
    let state = app.state::<EngineState>();
    let info = EngineInfo { url, error };
    *state.info.lock().unwrap() = info.clone();
    let _ = app.emit("engine", info);
}

pub fn stop(app: &AppHandle) {
    if let Some(child) = app.state::<EngineState>().child.lock().unwrap().take() {
        let _ = child.kill();
    }
}

fn dev_python() -> String {
    let engine = concat!(env!("CARGO_MANIFEST_DIR"), "/../../engine/.venv");
    if cfg!(windows) {
        format!("{engine}/Scripts/python.exe")
    } else {
        format!("{engine}/bin/python")
    }
}

#[tauri::command]
pub fn engine_info(state: tauri::State<'_, EngineState>) -> EngineInfo {
    state.info.lock().unwrap().clone()
}

#[tauri::command]
pub fn restart_engine(app: AppHandle) -> Result<(), String> {
    stop(&app);
    set_info(&app, None, None);
    start(&app)
}
