use std::process::Command;
use serde::Serialize;

#[derive(Serialize)]
struct ConnectionInfo {
    protocol: String,
    destination: String,
    is_external: bool,
}

#[derive(Serialize)]
struct FileEntry {
    name: String,
    path: String,
    is_dir: bool,
    size_bytes: u64,
    modified_unix: u64,
}

#[derive(Serialize)]
struct WeatherForecastDay {
    day: String,
    high_f: i32,
    low_f: i32,
    condition: String,
}

#[derive(Serialize)]
struct WeatherReport {
    temp_f: i32,
    high_f: i32,
    low_f: i32,
    humidity: i32,
    wind_mph: i32,
    feels_like_f: i32,
    condition: String,
    description: String,
    forecast: Vec<WeatherForecastDay>,
}

fn home_dir() -> String {
    std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string())
}

fn has_unsafe_shell_chars(command: &str) -> bool {
    let forbidden = ['|', '&', ';', '>', '<', '$', '`', '\n', '\r'];
    command.chars().any(|ch| forbidden.contains(&ch)) || command.contains("$(")
}

#[tauri::command]
fn run_terminal_command(command: &str) -> Result<String, String> {
    use std::process::Command;

    let cmd = command.trim();
    if cmd.is_empty() {
        return Ok(String::new());
    }

    if has_unsafe_shell_chars(cmd) {
        return Err("Unsafe shell operators are blocked in terminal mode".to_string());
    }

    let binary = cmd.split_whitespace().next().unwrap_or_default();
    let allow_list = [
        "ls", "pwd", "whoami", "date", "uname", "uptime", "cat", "echo", "head", "tail", "df",
        "free", "ps", "ip", "ss", "ping", "id", "hostname", "env", "du", "find", "rg",
    ];

    if !allow_list.contains(&binary) {
        return Err(format!("Command '{}' is not allowed", binary));
    }

    let output = Command::new("bash")
        .arg("-lc")
        .arg(cmd)
        .output()
        .map_err(|e| format!("Failed to execute command: {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    Ok(format!("{}{}", stdout, stderr))
}

#[tauri::command]
fn save_to_canvas(content: &str) -> Result<(), String> {
    use std::fs::OpenOptions;
    use std::io::Write;

    let path = format!("{}/.mnemonic_canvas", home_dir());

    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
        .map_err(|e| e.to_string())?;

    writeln!(file, "---------------------\\n{}", content).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn get_media_files() -> Result<Vec<String>, String> {
    use base64::{engine::general_purpose::STANDARD as base64_standard, Engine as _};
    use std::fs;
    use std::path::Path;

    let pictures_path = format!("{}/Pictures", home_dir());
    let path = Path::new(&pictures_path);

    if !path.exists() || !path.is_dir() {
        return Ok(Vec::new());
    }

    let mut encoded_images = Vec::new();

    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let file_path = entry.path();
            if !file_path.is_file() {
                continue;
            }

            let Some(ext) = file_path.extension().and_then(|e| e.to_str()) else {
                continue;
            };

            let ext_lower = ext.to_lowercase();
            if ext_lower != "jpg" && ext_lower != "jpeg" && ext_lower != "png" && ext_lower != "webp" {
                continue;
            }

            if let Ok(file_bytes) = fs::read(&file_path) {
                let encoded = base64_standard.encode(&file_bytes);
                let mime = if ext_lower == "png" {
                    "image/png"
                } else if ext_lower == "webp" {
                    "image/webp"
                } else {
                    "image/jpeg"
                };

                let data_uri = format!("data:{};base64,{}", mime, encoded);
                encoded_images.push(data_uri);

                if encoded_images.len() >= 8 {
                    break;
                }
            }
        }
    }

    Ok(encoded_images)
}

#[tauri::command]
fn ping_host(host: Option<String>) -> Result<Option<u32>, String> {
    use std::process::Command;

    let host = host.unwrap_or_else(|| "8.8.8.8".to_string());
    let output = Command::new("ping")
        .arg("-c")
        .arg("1")
        .arg("-W")
        .arg("1")
        .arg(host)
        .output()
        .map_err(|e| format!("Failed to execute ping: {e}"))?;

    let out = String::from_utf8_lossy(&output.stdout);
    let latency = out
        .split_whitespace()
        .find_map(|token| token.strip_prefix("time="))
        .and_then(|t| t.parse::<f64>().ok())
        .map(|v| v.round() as u32);

    Ok(latency)
}

#[tauri::command]
fn list_established_connections(limit: Option<usize>) -> Result<Vec<ConnectionInfo>, String> {
    use std::process::Command;

    let limit = limit.unwrap_or(8).min(32);
    let output = Command::new("ss")
        .arg("-tun")
        .arg("state")
        .arg("established")
        .output()
        .map_err(|e| format!("Failed to execute ss: {e}"))?;

    let raw = String::from_utf8_lossy(&output.stdout);
    let mut results: Vec<ConnectionInfo> = Vec::new();

    for line in raw.lines().skip(1) {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 6 {
            continue;
        }

        let protocol = parts[0].to_uppercase();
        let destination = parts[5].to_string();

        let host_part = destination
            .rsplit(':')
            .nth(1)
            .unwrap_or(destination.as_str());

        let is_external = !host_part.starts_with("127.")
            && !host_part.starts_with("192.168.")
            && !host_part.starts_with("10.")
            && host_part != "localhost"
            && host_part != "::1";

        results.push(ConnectionInfo {
            protocol,
            destination,
            is_external,
        });

        if results.len() >= limit {
            break;
        }
    }

    Ok(results)
}

fn run_first_success_command(commands: &[(&str, &[&str])]) -> Result<(), String> {
    use std::process::Command;

    for (binary, args) in commands {
        let status = Command::new(binary).args(*args).status();
        if let Ok(exit) = status {
            if exit.success() {
                return Ok(());
            }
        }
    }

    Err("No supported audio backend succeeded".to_string())
}

#[tauri::command]
fn set_system_volume(percent: u8) -> Result<String, String> {
    let p = percent.min(100);
    let p_arg = format!("{}%", p);

    run_first_success_command(&[
        ("pactl", &["set-sink-volume", "@DEFAULT_SINK@", p_arg.as_str()]),
        ("amixer", &["-D", "pulse", "sset", "Master", p_arg.as_str()]),
    ])?;

    Ok(format!("Volume set to {}%", p))
}

#[tauri::command]
fn toggle_system_mute() -> Result<String, String> {
    run_first_success_command(&[
        ("pactl", &["set-sink-mute", "@DEFAULT_SINK@", "toggle"]),
        ("amixer", &["-D", "pulse", "sset", "Master", "toggle"]),
    ])?;

    Ok("Mute toggled".to_string())
}

#[tauri::command]
fn list_files(path: Option<String>, limit: Option<usize>) -> Result<Vec<FileEntry>, String> {
    use std::fs;
    use std::path::PathBuf;
    use std::time::UNIX_EPOCH;

    let raw_path = path.unwrap_or_else(home_dir);
    let expanded = if raw_path == "~" {
        home_dir()
    } else if raw_path.starts_with("~/") {
        format!("{}/{}", home_dir(), raw_path.trim_start_matches("~/"))
    } else {
        raw_path
    };

    let path = PathBuf::from(expanded);
    if !path.exists() || !path.is_dir() {
        return Ok(Vec::new());
    }

    let mut entries: Vec<FileEntry> = Vec::new();
    let limit = limit.unwrap_or(200).min(1000);

    for entry in fs::read_dir(path).map_err(|e| e.to_string())?.flatten() {
        if entries.len() >= limit {
            break;
        }

        let file_name = entry.file_name().to_string_lossy().to_string();
        if file_name.starts_with('.') {
            continue;
        }

        let Ok(metadata) = entry.metadata() else {
            continue;
        };

        let modified_unix = metadata
            .modified()
            .ok()
            .and_then(|m| m.duration_since(UNIX_EPOCH).ok())
            .map(|d| d.as_secs())
            .unwrap_or(0);

        entries.push(FileEntry {
            name: file_name,
            path: entry.path().display().to_string(),
            is_dir: metadata.is_dir(),
            size_bytes: metadata.len(),
            modified_unix,
        });
    }

    entries.sort_by(|a, b| b.modified_unix.cmp(&a.modified_unix));
    Ok(entries)
}

#[derive(serde::Deserialize)]
struct WttrResponse {
    current_condition: Vec<WttrCurrent>,
    weather: Vec<WttrForecast>,
}

#[derive(serde::Deserialize)]
struct WttrCurrent {
    #[serde(rename = "temp_F")]
    temp_f: String,
    #[serde(rename = "humidity")]
    humidity: String,
    #[serde(rename = "windspeedMiles")]
    wind_mph: String,
    #[serde(rename = "FeelsLikeF")]
    feels_like_f: String,
    #[serde(rename = "weatherDesc")]
    weather_desc: Vec<WttrTextValue>,
}

#[derive(serde::Deserialize)]
struct WttrForecast {
    date: String,
    #[serde(rename = "maxtempF")]
    max_temp_f: String,
    #[serde(rename = "mintempF")]
    min_temp_f: String,
    hourly: Vec<WttrHourly>,
}

#[derive(serde::Deserialize)]
struct WttrHourly {
    #[serde(rename = "weatherDesc")]
    weather_desc: Vec<WttrTextValue>,
}

#[derive(serde::Deserialize)]
struct WttrTextValue {
    value: String,
}

fn normalize_condition(text: &str) -> String {
    let lower = text.to_lowercase();
    if lower.contains("sun") || lower.contains("clear") {
        "sunny".to_string()
    } else if lower.contains("storm") || lower.contains("thunder") {
        "stormy".to_string()
    } else if lower.contains("snow") || lower.contains("sleet") {
        "snowy".to_string()
    } else if lower.contains("rain") || lower.contains("drizzle") {
        "rainy".to_string()
    } else if lower.contains("cloud") {
        "cloudy".to_string()
    } else {
        "partly-cloudy".to_string()
    }
}

fn encode_location_for_url(input: &str) -> String {
    input
        .trim()
        .chars()
        .map(|c| match c {
            'A'..='Z' | 'a'..='z' | '0'..='9' | '-' | '_' | '.' | '~' => c.to_string(),
            ' ' => "%20".to_string(),
            _ => format!("%{:02X}", c as u32),
        })
        .collect::<Vec<String>>()
        .join("")
}

#[tauri::command]
fn get_weather_report(location: Option<String>) -> Result<WeatherReport, String> {
    use std::process::Command;

    let loc = location
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "".to_string());

    let endpoint = if loc.is_empty() {
        "https://wttr.in/?format=j1".to_string()
    } else {
        format!("https://wttr.in/{}?format=j1", encode_location_for_url(&loc))
    };

    let body = Command::new("curl")
        .arg("-fsSL")
        .arg("--connect-timeout")
        .arg("5")
        .arg("--max-time")
        .arg("8")
        .arg(endpoint)
        .output()
        .map_err(|e| format!("Failed to execute curl for weather: {e}"))
        .and_then(|out| {
            if out.status.success() {
                Ok(String::from_utf8_lossy(&out.stdout).to_string())
            } else {
                Err(String::from_utf8_lossy(&out.stderr).to_string())
            }
        })?;

    let payload: WttrResponse =
        serde_json::from_str(&body).map_err(|e| format!("Failed parsing weather response: {e}"))?;

    let current = payload
        .current_condition
        .first()
        .ok_or_else(|| "Weather response missing current condition".to_string())?;

    let today = payload
        .weather
        .first()
        .ok_or_else(|| "Weather response missing forecast".to_string())?;

    let desc = current
        .weather_desc
        .first()
        .map(|d| d.value.clone())
        .unwrap_or_else(|| "Unknown".to_string());

    let mut forecast: Vec<WeatherForecastDay> = Vec::new();
    for day in payload.weather.iter().take(5) {
        let condition_text = day
            .hourly
            .first()
            .and_then(|h| h.weather_desc.first())
            .map(|d| d.value.clone())
            .unwrap_or_else(|| "Cloudy".to_string());

        forecast.push(WeatherForecastDay {
            day: day.date.clone(),
            high_f: day.max_temp_f.parse::<i32>().unwrap_or(0),
            low_f: day.min_temp_f.parse::<i32>().unwrap_or(0),
            condition: normalize_condition(&condition_text),
        });
    }

    Ok(WeatherReport {
        temp_f: current.temp_f.parse::<i32>().unwrap_or(0),
        high_f: today.max_temp_f.parse::<i32>().unwrap_or(0),
        low_f: today.min_temp_f.parse::<i32>().unwrap_or(0),
        humidity: current.humidity.parse::<i32>().unwrap_or(0),
        wind_mph: current.wind_mph.parse::<i32>().unwrap_or(0),
        feels_like_f: current.feels_like_f.parse::<i32>().unwrap_or(0),
        condition: normalize_condition(&desc),
        description: desc,
        forecast,
    })
}

#[tauri::command]
fn get_gmail_messages() -> Result<Vec<serde_json::Value>, String> {
    Ok(Vec::new()) // Now handled via HTTP
}

#[tauri::command]
fn get_google_calendar_events() -> Result<Vec<serde_json::Value>, String> {
    Ok(Vec::new()) // Now handled via HTTP
}

#[tauri::command]
fn set_brightness(percent: u8) -> Result<String, String> {
    let percent = percent.clamp(5, 100);
    Command::new("brightnessctl")
        .arg("set")
        .arg(format!("{}%", percent))
        .output()
        .map_err(|e| format!("Failed to set brightness: {e}"))?;
    Ok(format!("Brightness set to {}%", percent))
}

#[tauri::command]
fn toggle_wifi() -> Result<String, String> {
    // Check current state via nmcli
    let out = Command::new("nmcli")
        .arg("radio")
        .arg("wifi")
        .output()
        .map_err(|e| format!("Failed to check wifi state: {e}"))?;
        
    let state = String::from_utf8_lossy(&out.stdout).trim().to_lowercase();
    let next_state = if state == "enabled" { "off" } else { "on" };
    
    Command::new("nmcli")
        .arg("radio")
        .arg("wifi")
        .arg(next_state)
        .output()
        .map_err(|e| format!("Failed to toggle wifi: {e}"))?;
        
    Ok(format!("WiFi toggled {}", next_state))
}

#[tauri::command]
fn toggle_bluetooth() -> Result<String, String> {
    let out = Command::new("rfkill")
        .arg("list")
        .arg("bluetooth")
        .output()
        .map_err(|e| format!("Failed to check bluetooth state: {e}"))?;
        
    let output_str = String::from_utf8_lossy(&out.stdout);
    // If it says Soft blocked: yes, it's currently OFF.
    let is_blocked = output_str.contains("Soft blocked: yes");
    
    let action = if is_blocked { "unblock" } else { "block" };
    
    Command::new("rfkill")
        .arg(action)
        .arg("bluetooth")
        .output()
        .map_err(|e| format!("Failed to toggle bluetooth: {e}"))?;
        
    Ok(format!("Bluetooth toggled ({})", action))
}

#[tauri::command]
fn toggle_night_mode() -> Result<String, String> {
    Ok("Night mode toggled".to_string())
}

#[tauri::command]
fn toggle_do_not_disturb() -> Result<String, String> {
    Ok("Do not disturb toggled".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            run_terminal_command,
            save_to_canvas,
            get_media_files,
            ping_host,
            list_established_connections,
            set_system_volume,
            toggle_system_mute,
            list_files,
            get_weather_report,
            get_gmail_messages,
            get_google_calendar_events,
            set_brightness,
            toggle_wifi,
            toggle_bluetooth,
            toggle_night_mode,
            toggle_do_not_disturb
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
