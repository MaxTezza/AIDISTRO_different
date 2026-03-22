//! Display and Theme Management
//! Handles dark/light mode scheduling, night light, and display settings

use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{ok_response, error_response, run_command, command_exists};
use std::fs;
use std::path::Path;

const THEME_CONFIG_PATH: &str = ".config/ai-distro/theme-schedule.json";

#[derive(serde::Serialize, serde::Deserialize, Clone)]
struct ThemeSchedule {
    enabled: bool,
    light_mode_start: String,  // e.g., "07:00"
    dark_mode_start: String,   // e.g., "19:00"
    current_theme: String,
    night_light_enabled: bool,
    night_light_start: String,
    night_light_end: String,
    night_light_temperature: u32,  // Kelvin, typically 2500-6500
}

impl Default for ThemeSchedule {
    fn default() -> Self {
        Self {
            enabled: true,
            light_mode_start: "07:00".to_string(),
            dark_mode_start: "19:00".to_string(),
            current_theme: "light".to_string(),
            night_light_enabled: false,
            night_light_start: "20:00".to_string(),
            night_light_end: "06:00".to_string(),
            night_light_temperature: 3500,
        }
    }
}

fn get_theme_config_path() -> std::path::PathBuf {
    dirs::home_dir()
        .map(|h| h.join(THEME_CONFIG_PATH))
        .unwrap_or_else(|| Path::new("/etc/ai-distro").join(THEME_CONFIG_PATH))
}

fn load_theme_schedule() -> ThemeSchedule {
    let path = get_theme_config_path();
    if let Ok(content) = fs::read_to_string(&path) {
        serde_json::from_str(&content).unwrap_or_default()
    } else {
        ThemeSchedule::default()
    }
}

fn save_theme_schedule(schedule: &ThemeSchedule) -> Result<(), String> {
    let path = get_theme_config_path();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    fs::write(&path, serde_json::to_string_pretty(schedule).unwrap_or_default())
        .map_err(|e| format!("Failed to save theme config: {}", e))
}

fn detect_desktop_env() -> String {
    std::env::var("XDG_CURRENT_DESKTOP")
        .or_else(|_| std::env::var("DESKTOP_SESSION"))
        .unwrap_or_else(|_| "unknown".to_string())
        .to_lowercase()
}

/// Set dark mode
pub fn handle_set_dark_mode(req: &ActionRequest) -> ActionResponse {
    let de = detect_desktop_env();
    let mut schedule = load_theme_schedule();
    
    let success = match de.as_str() {
        "gnome" | "ubuntu" | "pop" => {
            // Set GNOME dark mode
            let gtk_theme = run_command("gsettings", &["set", "org.gnome.desktop.interface", "gtk-theme", "Adwaita-dark"], None);
            let color_scheme = run_command("gsettings", &["set", "org.gnome.desktop.interface", "color-scheme", "prefer-dark"], None);
            gtk_theme.is_ok() || color_scheme.is_ok()
        }
        "kde" | "plasma" => {
            // Set KDE dark theme
            run_command("lookandfeeltool", &["-a", "org.kde.breeze.desktop"], None).is_ok() ||
            run_command("plasma-apply-colorscheme", &["BreezeDark"], None).is_ok()
        }
        "sway" | "hyprland" => {
            // For Wayland compositors, set GTK theme via gsettings
            run_command("gsettings", &["set", "org.gnome.desktop.interface", "gtk-theme", "Adwaita-dark"], None).is_ok()
        }
        _ => {
            // Fallback: try gsettings
            run_command("gsettings", &["set", "org.gnome.desktop.interface", "gtk-theme", "Adwaita-dark"], None).is_ok()
        }
    };
    
    if success {
        schedule.current_theme = "dark".to_string();
        let _ = save_theme_schedule(&schedule);
        ok_response(&req.name, "Dark mode enabled.")
    } else {
        error_response(&req.name, "Failed to set dark mode. Your desktop environment may not support this action.")
    }
}

/// Set light mode
pub fn handle_set_light_mode(req: &ActionRequest) -> ActionResponse {
    let de = detect_desktop_env();
    let mut schedule = load_theme_schedule();
    
    let success = match de.as_str() {
        "gnome" | "ubuntu" | "pop" => {
            let gtk_theme = run_command("gsettings", &["set", "org.gnome.desktop.interface", "gtk-theme", "Adwaita"], None);
            let color_scheme = run_command("gsettings", &["set", "org.gnome.desktop.interface", "color-scheme", "prefer-light"], None);
            gtk_theme.is_ok() || color_scheme.is_ok()
        }
        "kde" | "plasma" => {
            run_command("plasma-apply-colorscheme", &["BreezeLight"], None).is_ok()
        }
        "sway" | "hyprland" => {
            run_command("gsettings", &["set", "org.gnome.desktop.interface", "gtk-theme", "Adwaita"], None).is_ok()
        }
        _ => {
            run_command("gsettings", &["set", "org.gnome.desktop.interface", "gtk-theme", "Adwaita"], None).is_ok()
        }
    };
    
    if success {
        schedule.current_theme = "light".to_string();
        let _ = save_theme_schedule(&schedule);
        ok_response(&req.name, "Light mode enabled.")
    } else {
        error_response(&req.name, "Failed to set light mode. Your desktop environment may not support this action.")
    }
}

/// Toggle between dark and light mode
pub fn handle_toggle_theme(req: &ActionRequest) -> ActionResponse {
    let schedule = load_theme_schedule();
    if schedule.current_theme == "dark" {
        handle_set_light_mode(req)
    } else {
        handle_set_dark_mode(req)
    }
}

/// Configure automatic dark/light mode scheduling
pub fn handle_set_theme_schedule(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing schedule payload");
    };
    
    // Parse payload like "light:07:00,dark:19:00"
    let mut schedule = load_theme_schedule();
    schedule.enabled = true;
    
    for part in payload.split(',') {
        let kv: Vec<&str> = part.split(':').collect();
        if kv.len() >= 2 {
            match kv[0].to_lowercase().as_str() {
                "light" => {
                    schedule.light_mode_start = format!("{}:{}", kv.get(1).unwrap_or(&"07"), kv.get(2).unwrap_or(&"00"));
                }
                "dark" => {
                    schedule.dark_mode_start = format!("{}:{}", kv.get(1).unwrap_or(&"19"), kv.get(2).unwrap_or(&"00"));
                }
                "nightlight" => {
                    schedule.night_light_enabled = true;
                    schedule.night_light_start = format!("{}:{}", kv.get(1).unwrap_or(&"20"), kv.get(2).unwrap_or(&"00"));
                }
                _ => {}
            }
        }
    }
    
    match save_theme_schedule(&schedule) {
        Ok(_) => ok_response(&req.name, &format!(
            "Theme schedule configured: light mode at {}, dark mode at {}",
            schedule.light_mode_start, schedule.dark_mode_start
        )),
        Err(e) => error_response(&req.name, &e),
    }
}

/// Get current theme status and schedule
pub fn handle_get_theme_status(req: &ActionRequest) -> ActionResponse {
    let schedule = load_theme_schedule();
    
    // Check if night light is active (via gsettings for GNOME)
    let night_light_active = run_command(
        "gsettings",
        &["get", "org.gnome.settings-daemon.plugins.color", "night-light-enabled"],
        None
    ).map(|o| o.contains("true")).unwrap_or(false);
    
    ok_response(&req.name, &serde_json::json!({
        "current_theme": schedule.current_theme,
        "schedule_enabled": schedule.enabled,
        "light_mode_time": schedule.light_mode_start,
        "dark_mode_time": schedule.dark_mode_start,
        "night_light_enabled": night_light_active,
        "night_light_temperature": schedule.night_light_temperature
    }).to_string())
}

/// Enable/disable night light (blue light filter)
pub fn handle_set_night_light(req: &ActionRequest) -> ActionResponse {
    let enable = req.payload.as_deref()
        .map(|p| p.to_lowercase() == "true" || p == "on" || p == "1")
        .unwrap_or(true);
    
    let de = detect_desktop_env();
    let mut schedule = load_theme_schedule();
    
    let success = match de.as_str() {
        "gnome" | "ubuntu" | "pop" => {
            let setting = if enable { "true" } else { "false" };
            run_command("gsettings", &["set", "org.gnome.settings-daemon.plugins.color", "night-light-enabled", setting], None).is_ok()
        }
        "kde" | "plasma" => {
            // KDE uses Redshift or built-in Night Color
            if enable {
                run_command("redshift", &["-O", "3500", "-P"], None).is_ok()
            } else {
                run_command("redshift", &["-x"], None).is_ok()
            }
        }
        _ => {
            // Fallback: try redshift if available
            if command_exists("redshift") {
                if enable {
                    run_command("redshift", &["-O", "3500", "-P"], None).is_ok()
                } else {
                    run_command("redshift", &["-x"], None).is_ok()
                }
            } else if command_exists("gsettings") {
                let setting = if enable { "true" } else { "false" };
                run_command("gsettings", &["set", "org.gnome.settings-daemon.plugins.color", "night-light-enabled", setting], None).is_ok()
            } else {
                false
            }
        }
    };
    
    if success {
        schedule.night_light_enabled = enable;
        let _ = save_theme_schedule(&schedule);
        ok_response(&req.name, &format!("Night light {}.", if enable { "enabled" } else { "disabled" }))
    } else {
        error_response(&req.name, "Failed to toggle night light. Install redshift or use a supported desktop environment.")
    }
}

/// Apply scheduled theme based on current time
/// This should be called by a timer/cron job
pub fn handle_apply_scheduled_theme(req: &ActionRequest) -> ActionResponse {
    let schedule = load_theme_schedule();
    
    if !schedule.enabled {
        return ok_response(&req.name, "Theme scheduling is disabled.");
    }
    
    // Get current time
    let now = chrono_now_hour_minute();
    
    // Determine which mode should be active
    let light_time = parse_time(&schedule.light_mode_start);
    let dark_time = parse_time(&schedule.dark_mode_start);
    
    let should_be_dark = if dark_time < light_time {
        // Dark mode starts after midnight (e.g., 19:00 - 07:00 next day)
        now >= dark_time || now < light_time
    } else {
        // Normal case: dark mode starts after light mode (e.g., 07:00 - 19:00)
        now >= dark_time || now < light_time
    };
    
    // Only change if different from current
    if should_be_dark && schedule.current_theme != "dark" {
        handle_set_dark_mode(req)
    } else if !should_be_dark && schedule.current_theme != "light" {
        handle_set_light_mode(req)
    } else {
        ok_response(&req.name, &format!("Theme already set correctly to {} mode.", schedule.current_theme))
    }
}

// Helper functions

fn chrono_now_hour_minute() -> (u32, u32) {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    
    // Convert to hours and minutes (assuming UTC, but for scheduling purposes this is fine)
    let hours = ((secs / 3600) % 24) as u32;
    let minutes = ((secs % 3600) / 60) as u32;
    (hours, minutes)
}

fn parse_time(time_str: &str) -> (u32, u32) {
    let parts: Vec<u32> = time_str.split(':')
        .filter_map(|s| s.parse().ok())
        .collect();
    (parts.get(0).copied().unwrap_or(0), parts.get(1).copied().unwrap_or(0))
}
