use ai_distro_common::{
    init_logging_with_config, load_typed_config, ActionRequest, ActionResponse, VoiceConfig,
};
use std::io::{self, BufRead, BufReader, Write};
use std::os::unix::net::UnixStream;
use std::process::{Command, Stdio};

fn agent_roundtrip(socket: &str, request: &ActionRequest) -> Result<ActionResponse, String> {
    let payload =
        serde_json::to_string(request).map_err(|e| format!("serialize request failed: {e}"))? + "\n";
    let mut stream = UnixStream::connect(socket).map_err(|e| format!("connect failed: {e}"))?;
    stream
        .write_all(payload.as_bytes())
        .map_err(|e| format!("write failed: {e}"))?;
    stream.flush().map_err(|e| format!("flush failed: {e}"))?;
    let mut line = String::new();
    let mut reader = BufReader::new(stream);
    reader
        .read_line(&mut line)
        .map_err(|e| format!("read failed: {e}"))?;
    serde_json::from_str::<ActionResponse>(line.trim())
        .map_err(|e| format!("invalid response: {e}"))
}

fn speak_text(cfg: &VoiceConfig, text: &str) -> Result<(), String> {
    let bin = std::env::var("AI_DISTRO_TTS_BINARY").unwrap_or_else(|_| cfg.tts_binary.clone());
    if bin.trim().is_empty() {
        return Err("tts binary is empty".to_string());
    }
    let args_raw = std::env::var("AI_DISTRO_TTS_ARGS").unwrap_or_default();
    let args: Vec<&str> = args_raw.split_whitespace().collect();
    let mut child = Command::new(bin)
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("spawn tts failed: {e}"))?;
    if let Some(stdin) = child.stdin.as_mut() {
        stdin
            .write_all(text.as_bytes())
            .map_err(|e| format!("write tts stdin failed: {e}"))?;
    }
    let output = child
        .wait_with_output()
        .map_err(|e| format!("wait tts failed: {e}"))?;
    if output.status.success() {
        Ok(())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).trim().to_string())
    }
}

fn main() {
    let cfg: VoiceConfig = load_typed_config("/etc/ai-distro/voice.json");
    init_logging_with_config(&cfg.service);
    log::info!("starting");
    log::info!(
        "voice config: asr={}, tts={}, device={}, asr_bin={}, tts_bin={}",
        cfg.asr_model,
        cfg.tts_model,
        cfg.audio_device,
        cfg.asr_binary,
        cfg.tts_binary
    );

    let agent_socket =
        std::env::var("AI_DISTRO_IPC_SOCKET").unwrap_or_else(|_| "/run/ai-distro/agent.sock".to_string());
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    log::info!(
        "ready: stdin text => natural_language request over {}",
        agent_socket
    );
    log::info!("tts: set AI_DISTRO_TTS_BINARY and optional AI_DISTRO_TTS_ARGS for speech output");

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };

        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        if let Some(text) = trimmed.strip_prefix("speak ") {
            let response = match speak_text(&cfg, text.trim()) {
                Ok(()) => ActionResponse {
                    version: 1,
                    action: "speak".to_string(),
                    status: "ok".to_string(),
                    message: Some("spoken".to_string()),
                    capabilities: None,
                    confirmation_id: None,
                },
                Err(err) => ActionResponse {
                    version: 1,
                    action: "speak".to_string(),
                    status: "error".to_string(),
                    message: Some(format!(
                        "tts unavailable: {} (configure AI_DISTRO_TTS_BINARY/AI_DISTRO_TTS_ARGS)",
                        err
                    )),
                    capabilities: None,
                    confirmation_id: None,
                },
            };
            if let Ok(payload) = serde_json::to_string(&response) {
                let _ = writeln!(stdout, "{payload}");
                let _ = stdout.flush();
            }
            continue;
        }

        let request = ActionRequest {
            version: Some(1),
            name: "natural_language".to_string(),
            payload: Some(trimmed.to_string()),
        };

        let response = match agent_roundtrip(&agent_socket, &request) {
            Ok(resp) => resp,
            Err(err) => ActionResponse {
                version: 1,
                action: "natural_language".to_string(),
                status: "error".to_string(),
                message: Some(format!("voice bridge failed: {err}")),
                capabilities: None,
                confirmation_id: None,
            },
        };

        if response.status == "ok" {
            if let Some(msg) = response.message.as_deref() {
                let _ = speak_text(&cfg, msg);
            }
        }
        if let Ok(payload) = serde_json::to_string(&response) {
            let _ = writeln!(stdout, "{payload}");
            let _ = stdout.flush();
        }
    }
}
