use crate::{handle_request, Handler};
use ai_distro_common::{ActionRequest, ActionResponse, PolicyConfig};
use serde_json::json;
use std::collections::HashMap;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::{UnixListener, UnixStream};

pub async fn broadcast_event(event: serde_json::Value) {
    let path = std::env::var("AI_DISTRO_EVENT_SOCKET")
        .unwrap_or_else(|_| "/tmp/ai-distro-events.sock".to_string());
    if let Ok(mut stream) = UnixStream::connect(&path).await {
        let payload = event.to_string() + "\n";
        let _ = stream.write_all(payload.as_bytes()).await;
    }
}

pub async fn run_ipc_socket(
    policy: PolicyConfig,
    registry: HashMap<&'static str, Handler>,
    path: &str,
) {
    let _ = fs::remove_file(path);
    let listener = match UnixListener::bind(path) {
        Ok(l) => l,
        Err(err) => {
            log::error!("failed to bind socket {}: {}", path, err);
            return;
        }
    };

    let mode = std::env::var("AI_DISTRO_IPC_SOCKET_MODE")
        .ok()
        .and_then(|v| u32::from_str_radix(v.trim_start_matches("0o"), 8).ok())
        .unwrap_or(0o660);
    let _ = fs::set_permissions(path, fs::Permissions::from_mode(mode));

    log::info!("ipc socket listening at {}", path);

    loop {
        match listener.accept().await {
            Ok((stream, _)) => {
                let policy = policy.clone();
                let registry = registry.clone();
                tokio::spawn(async move {
                    let (reader, mut writer) = tokio::io::split(stream);
                    let mut reader = BufReader::new(reader);
                    let mut line = String::new();

                    while let Ok(n) = reader.read_line(&mut line).await {
                        if n == 0 {
                            break;
                        }
                        let trimmed = line.trim();
                        if !trimmed.is_empty() {
                            broadcast_event(json!({"type": "status", "message": "Processing..."}))
                                .await;

                            let response = match serde_json::from_str::<ActionRequest>(trimmed) {
                                Ok(req) => {
                                    // Audit Log
                                    let audit_path = "/var/log/ai-distro/audit.json";
                                    let mut state = crate::audit::load_audit_chain_state(
                                        "/var/lib/ai-distro/audit_state.json",
                                    );
                                    let _ = crate::audit::append_audit_record(
                                        audit_path,
                                        &mut state,
                                        serde_json::to_value(&req).unwrap_or_default(),
                                    );
                                    crate::audit::persist_audit_chain_state(
                                        "/var/lib/ai-distro/audit_state.json",
                                        &state,
                                    );

                                    handle_request(&policy, &registry, req)
                                }
                                Err(err) => ActionResponse {
                                    version: 1,
                                    action: "unknown".to_string(),
                                    status: "error".to_string(),
                                    message: Some(format!("invalid request: {}", err)),
                                    capabilities: None,
                                    confirmation_id: None,
                                },
                            };

                            if let Some(msg) = &response.message {
                                broadcast_event(json!({
                                    "type": "info",
                                    "title": response.action,
                                    "message": msg
                                }))
                                .await;
                            }

                            if let Ok(payload) = serde_json::to_string(&response) {
                                let _ = writer.write_all(payload.as_bytes()).await;
                                let _ = writer.write_all(b"\n").await;
                                let _ = writer.flush().await;
                            }
                            broadcast_event(json!({"type": "status", "message": "System Ready"}))
                                .await;
                        }
                        line.clear();
                    }
                });
            }
            Err(err) => {
                log::warn!("ipc accept error: {}", err);
            }
        }
    }
}
