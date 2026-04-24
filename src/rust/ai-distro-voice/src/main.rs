use ai_distro_common::{
    init_logging_with_config, load_typed_config, ActionRequest, ActionResponse, VoiceConfig,
};
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::io::{BufRead, Write};
use std::os::unix::net::UnixStream;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex, OnceLock};

static ACTIVE_SPEAKER: OnceLock<Mutex<Option<Child>>> = OnceLock::new();

fn stop_speaking() {
    if let Some(lock) = ACTIVE_SPEAKER.get() {
        if let Ok(mut opt_child) = lock.lock() {
            if let Some(mut child) = opt_child.take() {
                log::info!("Barge-in detected: Stopping speech.");
                let _ = child.kill();
            }
        }
    }
}

#[derive(Clone)]
struct AudioState {
    buffer: Vec<f32>,
    is_recording: bool,
}

fn agent_roundtrip(socket: &str, request: &ActionRequest) -> Result<ActionResponse, String> {
    let payload = serde_json::to_string(request)
        .map_err(|e| format!("serialize request failed: {e}"))?
        + "\n";
    let mut stream = UnixStream::connect(socket).map_err(|e| format!("connect failed: {e}"))?;
    stream
        .write_all(payload.as_bytes())
        .map_err(|e| format!("write failed: {e}"))?;
    stream.flush().map_err(|e| format!("flush failed: {e}"))?;

    let mut line = String::new();
    let mut reader = std::io::BufReader::new(stream);
    reader
        .read_line(&mut line)
        .map_err(|e| format!("read failed: {e}"))?;
    serde_json::from_str::<ActionResponse>(line.trim())
        .map_err(|e| format!("invalid response: {e}"))
}

fn speak_text(cfg: &VoiceConfig, text: &str) -> Result<(), String> {
    let bin = std::env::var("AI_DISTRO_TTS_BINARY").unwrap_or_else(|_| cfg.tts_binary.clone());
    let model = std::env::var("AI_DISTRO_TTS_MODEL").unwrap_or_else(|_| cfg.tts_model.clone());

    if bin.trim().is_empty() {
        return Err("tts binary is empty".to_string());
    }

    // Spawn Piper
    let mut piper = Command::new(bin)
        .args(["--model", &model, "--output_raw"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("spawn piper failed: {e}"))?;

    // Spawn aplay
    let aplay = Command::new("aplay")
        .args(["-r", "22050", "-f", "S16_LE", "-t", "raw", "-"])
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("spawn aplay failed: {e}"))?;

    // Store aplay handle for potential interruption
    if let Ok(mut lock) = ACTIVE_SPEAKER.get_or_init(|| Mutex::new(None)).lock() {
        *lock = Some(aplay);
    }

    if let Some(mut stdin) = piper.stdin.take() {
        let _ = stdin.write_all(text.as_bytes());
    }

    if let Some(mut piper_stdout) = piper.stdout.take() {
        if let Ok(mut lock) = ACTIVE_SPEAKER.get_or_init(|| Mutex::new(None)).lock() {
            if let Some(aplay_child) = lock.as_mut() {
                if let Some(mut aplay_stdin) = aplay_child.stdin.take() {
                    let _ = std::io::copy(&mut piper_stdout, &mut aplay_stdin);
                }
            }
        }
    }

    let _ = piper.wait();

    // Wait and clean up aplay
    if let Ok(mut lock) = ACTIVE_SPEAKER.get_or_init(|| Mutex::new(None)).lock() {
        if let Some(mut aplay_child) = lock.take() {
            let _ = aplay_child.wait();
        }
    }

    Ok(())
}

async fn run_asr(cfg: &VoiceConfig, audio_data: Vec<f32>) -> Result<String, String> {
    let bin = std::env::var("AI_DISTRO_ASR_BINARY").unwrap_or_else(|_| cfg.asr_binary.clone());
    if bin.trim().is_empty() {
        return Err("asr binary is empty".to_string());
    }

    // Prepare WAV data from f32 samples
    let mut wav_buffer = Vec::new();
    let spec = hound::WavSpec {
        channels: 1,
        sample_rate: 16000,
        bits_per_sample: 16,
        sample_format: hound::SampleFormat::Int,
    };
    {
        let mut writer =
            hound::WavWriter::new(std::io::Cursor::new(&mut wav_buffer), spec).unwrap();
        for &sample in &audio_data {
            let amplitude = i16::MAX as f32;
            writer.write_sample((sample * amplitude) as i16).unwrap();
        }
        writer.finalize().unwrap();
    }

    let mut child = Command::new(bin)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("spawn asr failed: {e}"))?;

    if let Some(mut stdin) = child.stdin.take() {
        stdin
            .write_all(&wav_buffer)
            .map_err(|e| format!("write asr failed: {e}"))?;
    }

    let output = child
        .wait_with_output()
        .map_err(|e| format!("wait asr failed: {e}"))?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).trim().to_string())
    }
}

#[allow(deprecated)]
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cfg: VoiceConfig = load_typed_config("/etc/ai-distro/voice.json");
    init_logging_with_config(&cfg.service);
    log::info!("Starting AI Distro Voice Engine (Rust)");

    let host = cpal::default_host();
    let device = if cfg.audio_device == "default" {
        host.default_input_device()
    } else {
        host.input_devices()?
            .find(|x| x.name().map(|n| n == cfg.audio_device).unwrap_or(false))
    }
    .expect("Failed to find input device");

    log::info!("Using audio device: {}", device.name()?);

    let config = device.default_input_config()?;
    let state = Arc::new(Mutex::new(AudioState {
        buffer: Vec::new(),
        is_recording: false,
    }));

    let state_cb = Arc::clone(&state);
    let stream = device.build_input_stream(
        &config.into(),
        move |data: &[f32], _: &cpal::InputCallbackInfo| {
            let mut s = state_cb.lock().unwrap();
            // Simple VAD threshold
            let rms = (data.iter().map(|&x| x * x).sum::<f32>() / data.len() as f32).sqrt();
            if rms > 0.01 {
                if !s.is_recording {
                    stop_speaking();
                }
                s.is_recording = true;
                s.buffer.extend_from_slice(data);
            } else if s.is_recording {
                // Silence detected, could signal end of command
                s.is_recording = false;
            }
        },
        |err| log::error!("Stream error: {}", err),
        None,
    )?;

    stream.play()?;
    log::info!("Listening for commands...");

    let agent_socket = std::env::var("AI_DISTRO_IPC_SOCKET")
        .unwrap_or_else(|_| "/run/ai-distro/agent.sock".to_string());

    loop {
        let mut audio_to_process = Vec::new();
        {
            let mut s = state.lock().unwrap();
            if !s.is_recording && !s.buffer.is_empty() {
                audio_to_process = std::mem::take(&mut s.buffer);
            }
        }

        if !audio_to_process.is_empty() {
            log::info!("Processing audio ({} samples)...", audio_to_process.len());
            match run_asr(&cfg, audio_to_process).await {
                Ok(text) => {
                    if text.is_empty() {
                        continue;
                    }
                    log::info!("Recognized: {}", text);

                    let request = ActionRequest {
                        version: Some(1),
                        name: "natural_language".to_string(),
                        payload: Some(text),
                    };

                    match agent_roundtrip(&agent_socket, &request) {
                        Ok(resp) => {
                            if resp.status == "ok" {
                                if let Some(msg) = resp.message.as_deref() {
                                    let _ = speak_text(&cfg, msg);
                                }
                            }
                            log::info!("Agent response: {:?}", resp);
                        }
                        Err(err) => log::error!("Agent IPC failed: {}", err),
                    }
                }
                Err(err) => log::error!("ASR failed: {}", err),
            }
        }

        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    }
}
