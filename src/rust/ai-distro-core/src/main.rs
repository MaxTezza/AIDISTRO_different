use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

use ai_distro_common::{init_logging_with_config, load_typed_config, CoreConfig};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct CoreRequest {
    name: String,
    payload: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct CoreResponse {
    status: String,
    message: Option<String>,
    ts: u64,
}

fn now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

fn response_ok(message: impl Into<String>) -> CoreResponse {
    CoreResponse {
        status: "ok".to_string(),
        message: Some(message.into()),
        ts: now_epoch(),
    }
}

fn response_error(message: impl Into<String>) -> CoreResponse {
    CoreResponse {
        status: "error".to_string(),
        message: Some(message.into()),
        ts: now_epoch(),
    }
}

fn ensure_paths(cfg: &CoreConfig) -> Result<(), String> {
    if let Some(parent) = Path::new(&cfg.ipc_socket).parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create ipc dir failed: {e}"))?;
    }
    fs::create_dir_all(&cfg.context_dir).map_err(|e| format!("create context dir failed: {e}"))?;
    if let Some(parent) = Path::new(&cfg.state_db_path).parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create state dir failed: {e}"))?;
    }
    OpenOptions::new()
        .create(true)
        .append(true)
        .open(&cfg.state_db_path)
        .map_err(|e| format!("open state db failed: {e}"))?;
    Ok(())
}

fn append_note(cfg: &CoreConfig, note: &str) -> Result<(), String> {
    let notes_path = Path::new(&cfg.context_dir).join("notes.log");
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(notes_path)
        .map_err(|e| format!("open notes failed: {e}"))?;
    writeln!(file, "{}|{}", now_epoch(), note).map_err(|e| format!("write note failed: {e}"))?;
    Ok(())
}

fn recent_notes(cfg: &CoreConfig, limit: usize) -> Result<String, String> {
    let notes_path = Path::new(&cfg.context_dir).join("notes.log");
    let content = fs::read_to_string(notes_path).unwrap_or_default();
    let mut lines: Vec<&str> = content.lines().collect();
    if lines.is_empty() {
        return Ok("No notes yet.".to_string());
    }
    if lines.len() > limit {
        lines = lines.split_off(lines.len() - limit);
    }
    Ok(lines.join("\n"))
}

fn handle_request(cfg: &CoreConfig, req: CoreRequest) -> CoreResponse {
    match req.name.as_str() {
        "ping" | "health" => response_ok("core online"),
        "status" => response_ok(format!(
            "state_db={}, context_dir={}, ipc_socket={}",
            cfg.state_db_path, cfg.context_dir, cfg.ipc_socket
        )),
        "remember_note" => {
            let note = req.payload.unwrap_or_default().trim().to_string();
            if note.is_empty() {
                return response_error("missing note text");
            }
            match append_note(cfg, &note) {
                Ok(()) => response_ok("note saved"),
                Err(err) => response_error(err),
            }
        }
        "recent_notes" => {
            let limit = req
                .payload
                .as_deref()
                .and_then(|s| s.trim().parse::<usize>().ok())
                .unwrap_or(10)
                .clamp(1, 200);
            match recent_notes(cfg, limit) {
                Ok(text) => response_ok(text),
                Err(err) => response_error(err),
            }
        }
        _ => response_error("unknown core action"),
    }
}

fn handle_client(cfg: &CoreConfig, stream: UnixStream) {
    let mut writer = match stream.try_clone() {
        Ok(s) => s,
        Err(err) => {
            log::warn!("stream clone failed: {}", err);
            return;
        }
    };
    let reader = BufReader::new(stream);
    for line in reader.lines() {
        let line = match line {
            Ok(v) => v,
            Err(err) => {
                log::warn!("read error: {}", err);
                break;
            }
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let response = match serde_json::from_str::<CoreRequest>(trimmed) {
            Ok(req) => handle_request(cfg, req),
            Err(err) => response_error(format!("invalid request: {err}")),
        };
        if let Ok(payload) = serde_json::to_string(&response) {
            let _ = writer.write_all(payload.as_bytes());
            let _ = writer.write_all(b"\n");
            let _ = writer.flush();
        }
    }
}

fn main() {
    let mut cfg: CoreConfig = load_typed_config("/etc/ai-distro/core.json");
    if let Ok(v) = std::env::var("AI_DISTRO_CORE_SOCKET") {
        if !v.trim().is_empty() {
            cfg.ipc_socket = v;
        }
    }
    if let Ok(v) = std::env::var("AI_DISTRO_CORE_STATE_DB") {
        if !v.trim().is_empty() {
            cfg.state_db_path = v;
        }
    }
    if let Ok(v) = std::env::var("AI_DISTRO_CORE_CONTEXT_DIR") {
        if !v.trim().is_empty() {
            cfg.context_dir = v;
        }
    }

    init_logging_with_config(&cfg.service);
    log::info!("starting");

    if let Err(err) = ensure_paths(&cfg) {
        log::error!("startup failed: {}", err);
        return;
    }

    let socket_path = Path::new(&cfg.ipc_socket);
    if socket_path.exists() {
        let _ = fs::remove_file(socket_path);
    }

    let listener = match UnixListener::bind(socket_path) {
        Ok(v) => v,
        Err(err) => {
            log::error!("failed to bind core socket {}: {}", cfg.ipc_socket, err);
            return;
        }
    };
    let _ = fs::set_permissions(socket_path, fs::Permissions::from_mode(0o660));
    log::info!("core socket listening at {}", cfg.ipc_socket);

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => handle_client(&cfg, stream),
            Err(err) => log::warn!("accept error: {}", err),
        }
    }
}
