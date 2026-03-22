//! Privacy Dashboard Handler
//! Provides visibility into camera, microphone, and location access history

use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{ok_response, error_response};
use std::fs;
use std::path::Path;

const PRIVACY_LOG_PATH: &str = "/var/log/ai-distro/privacy-events.json";
const USER_PRIVACY_PATH: &str = ".config/ai-distro/privacy-history.json";

#[derive(serde::Serialize, serde::Deserialize, Clone)]
struct PrivacyEvent {
    timestamp: u64,
    event_type: String,  // "camera", "microphone", "location"
    application: String,
    action: String,      // "accessed", "denied", "granted"
}

/// Get privacy dashboard summary - shows recent camera/mic/location access
pub fn handle_privacy_status(req: &ActionRequest) -> ActionResponse {
    let mut events: Vec<PrivacyEvent> = Vec::new();
    
    // Load system privacy events
    if let Ok(content) = fs::read_to_string(PRIVACY_LOG_PATH) {
        if let Ok(mut system_events) = serde_json::from_str::<Vec<PrivacyEvent>>(&content) {
            events.append(&mut system_events);
        }
    }
    
    // Load user privacy events
    let user_path = Path::new("/etc/ai-distro").join(USER_PRIVACY_PATH);
    let user_path = dirs::home_dir()
        .map(|h| h.join(USER_PRIVACY_PATH))
        .unwrap_or(user_path);
    
    if let Ok(content) = fs::read_to_string(&user_path) {
        if let Ok(mut user_events) = serde_json::from_str::<Vec<PrivacyEvent>>(&content) {
            events.append(&mut user_events);
        }
    }
    
    // Get last 50 events, most recent first
    events.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
    events.truncate(50);
    
    // Summarize by type
    let mut camera_count = 0;
    let mut mic_count = 0;
    let mut location_count = 0;
    let mut recent_apps: Vec<String> = Vec::new();
    
    for event in &events {
        match event.event_type.as_str() {
            "camera" => camera_count += 1,
            "microphone" => mic_count += 1,
            "location" => location_count += 1,
            _ => {}
        }
        if !recent_apps.contains(&event.application) && recent_apps.len() < 10 {
            recent_apps.push(event.application.clone());
        }
    }
    
    let summary = serde_json::json!({
        "total_events": events.len(),
        "camera_access_count": camera_count,
        "microphone_access_count": mic_count,
        "location_access_count": location_count,
        "recent_applications": recent_apps,
        "last_24h_events": events.iter().take(24).collect::<Vec<_>>()
    });
    
    ok_response(&req.name, &summary.to_string())
}

/// Record a privacy event (used by other components)
pub fn handle_privacy_log(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing event payload");
    };
    
    let event: Result<PrivacyEvent, _> = serde_json::from_str(payload);
    let Ok(mut event) = event else {
        return error_response(&req.name, "invalid event format");
    };
    
    event.timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    
    let user_path = dirs::home_dir()
        .map(|h| h.join(USER_PRIVACY_PATH))
        .unwrap_or_else(|| Path::new("/etc/ai-distro").join(USER_PRIVACY_PATH));
    
    // Ensure directory exists
    if let Some(parent) = user_path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    
    // Load existing events
    let mut events: Vec<PrivacyEvent> = if let Ok(content) = fs::read_to_string(&user_path) {
        serde_json::from_str(&content).unwrap_or_default()
    } else {
        Vec::new()
    };
    
    // Add new event (keep last 1000)
    events.push(event);
    if events.len() > 1000 {
        events = events.into_iter().rev().take(1000).rev().collect();
    }
    
    // Save
    match fs::write(&user_path, serde_json::to_string_pretty(&events).unwrap_or_default()) {
        Ok(_) => ok_response(&req.name, "Privacy event logged."),
        Err(e) => error_response(&req.name, &format!("Failed to log privacy event: {}", e)),
    }
}

/// Check if camera/mic/location permission is currently active
pub fn handle_privacy_check_active(req: &ActionRequest) -> ActionResponse {
    let resource = req.payload.as_deref().unwrap_or("all");
    
    // Check for active camera/mic usage via /proc and pulseaudio/pipewire
    let mut active: Vec<String> = Vec::new();
    
    // Check for camera processes
    if resource == "all" || resource == "camera" {
        if let Ok(output) = std::process::Command::new("sh")
            .arg("-c")
            .arg("lsof /dev/video* 2>/dev/null | grep -v COMMAND | awk '{print $1}' | sort -u")
            .output()
        {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for app in stdout.lines().filter(|l| !l.is_empty()) {
                active.push(format!("camera:{}", app));
            }
        }
    }
    
    // Check for microphone via pulseaudio/pipewire
    if resource == "all" || resource == "microphone" {
        if let Ok(output) = std::process::Command::new("sh")
            .arg("-c")
            .arg("pactl list source-outputs 2>/dev/null | grep 'application.name' | cut -d'\"' -f2 | sort -u")
            .output()
        {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for app in stdout.lines().filter(|l| !l.is_empty()) {
                active.push(format!("microphone:{}", app));
            }
        }
    }
    
    // Location is typically via geoclue or GPS daemon
    if resource == "all" || resource == "location" {
        if let Ok(output) = std::process::Command::new("sh")
            .arg("-c")
            .arg("pgrep -la 'geoclue|gpsd' 2>/dev/null")
            .output()
        {
            let stdout = String::from_utf8_lossy(&output.stdout);
            if !stdout.is_empty() {
                for line in stdout.lines() {
                    if let Some(name) = line.split_whitespace().nth(1) {
                        active.push(format!("location:{}", name));
                    }
                }
            }
        }
    }
    
    ok_response(&req.name, &serde_json::json!({
        "resource": resource,
        "active": active,
        "count": active.len()
    }).to_string())
}
