//! Persistent Workspace Management
//! Save and restore desktop workspace state across reboots

use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{ok_response, error_response, run_command};
use std::fs;
use std::path::Path;
use std::collections::HashMap;

const WORKSPACE_STATE_PATH: &str = ".config/ai-distro/workspaces.json";

#[derive(serde::Serialize, serde::Deserialize, Clone, Default)]
struct WindowState {
    app_name: String,
    window_title: String,
    workspace: i32,
    x: i32,
    y: i32,
    width: i32,
    height: i32,
    minimized: bool,
    #[serde(default)]
    pid: Option<u32>,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Default)]
struct WorkspaceState {
    id: i32,
    name: String,
    windows: Vec<WindowState>,
    active: bool,
}

#[derive(serde::Serialize, serde::Deserialize, Default)]
struct WorkspaceSnapshot {
    workspaces: Vec<WorkspaceState>,
    timestamp: u64,
    desktop_environment: String,  // "gnome", "kde", "sway", etc.
}

fn get_workspace_path() -> std::path::PathBuf {
    dirs::home_dir()
        .map(|h| h.join(WORKSPACE_STATE_PATH))
        .unwrap_or_else(|| Path::new("/etc/ai-distro").join(WORKSPACE_STATE_PATH))
}

fn detect_desktop_env() -> String {
    std::env::var("XDG_CURRENT_DESKTOP")
        .or_else(|_| std::env::var("DESKTOP_SESSION"))
        .unwrap_or_else(|_| "unknown".to_string())
        .to_lowercase()
}

/// Save current workspace state
pub fn handle_workspace_save(req: &ActionRequest) -> ActionResponse {
    let de = detect_desktop_env();
    let mut snapshot = WorkspaceSnapshot {
        workspaces: Vec::new(),
        timestamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0),
        desktop_environment: de.clone(),
    };
    
    // Get window list based on desktop environment
    match de.as_str() {
        "gnome" | "ubuntu" | "pop" => {
            // Use wmctrl for GNOME-based environments
            if let Ok(output) = run_command("wmctrl", &["-l"], None) {
                // Parse window list
                for line in output.lines() {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if parts.len() >= 4 {
                        let window_id = parts.get(0).unwrap_or(&"");
                        let workspace: i32 = parts.get(1).unwrap_or(&"0").parse().unwrap_or(0);
                        let hostname = parts.get(2).unwrap_or(&"");
                        let title = parts[3..].join(" ");
                        
                        // Get window geometry
                        let (x, y, w, h) = get_window_geometry(window_id);
                        
                        snapshot.workspaces.push(WorkspaceState {
                            id: workspace,
                            name: format!("Workspace {}", workspace + 1),
                            windows: vec![WindowState {
                                app_name: guess_app_from_title(&title),
                                window_title: title,
                                workspace,
                                x,
                                y,
                                width: w,
                                height: h,
                                minimized: false,
                                pid: None,
                            }],
                            active: false,
                        });
                    }
                }
            }
        }
        "kde" | "plasma" => {
            // Use wmctrl for KDE as well
            if let Ok(output) = run_command("wmctrl", &["-l"], None) {
                for line in output.lines() {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if parts.len() >= 4 {
                        let window_id = parts.get(0).unwrap_or(&"");
                        let workspace: i32 = parts.get(1).unwrap_or(&"0").parse().unwrap_or(0);
                        let title = parts[3..].join(" ");
                        let (x, y, w, h) = get_window_geometry(window_id);
                        
                        snapshot.workspaces.push(WorkspaceState {
                            id: workspace,
                            name: format!("Workspace {}", workspace + 1),
                            windows: vec![WindowState {
                                app_name: guess_app_from_title(&title),
                                window_title: title,
                                workspace,
                                x, y,
                                width: w,
                                height: h,
                                minimized: false,
                                pid: None,
                            }],
                            active: false,
                        });
                    }
                }
            }
        }
        "sway" | "hyprland" => {
            // Use swaymsg or hyprctl for Wayland compositors
            if let Ok(output) = run_command("swaymsg", &["-t", "get_tree"], None) {
                // Parse JSON tree (simplified - would need proper JSON parsing)
                // For now, just note that it's a Wayland session
                snapshot.workspaces.push(WorkspaceState {
                    id: 0,
                    name: "Main".to_string(),
                    windows: vec![],
                    active: true,
                });
            }
        }
        _ => {
            // Fallback: use wmctrl if available
            if let Ok(output) = run_command("wmctrl", &["-l"], None) {
                for line in output.lines().take(20) {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if parts.len() >= 4 {
                        let workspace: i32 = parts.get(1).unwrap_or(&"0").parse().unwrap_or(0);
                        let title = parts[3..].join(" ");
                        
                        snapshot.workspaces.push(WorkspaceState {
                            id: workspace,
                            name: format!("Workspace {}", workspace + 1),
                            windows: vec![WindowState {
                                app_name: guess_app_from_title(&title),
                                window_title: title,
                                workspace,
                                x: 0, y: 0,
                                width: 800, height: 600,
                                minimized: false,
                                pid: None,
                            }],
                            active: false,
                        });
                    }
                }
            }
        }
    }
    
    // Merge windows into same workspace
    let mut merged: HashMap<i32, WorkspaceState> = HashMap::new();
    for ws in snapshot.workspaces {
        let entry = merged.entry(ws.id).or_insert_with(|| WorkspaceState {
            id: ws.id,
            name: ws.name.clone(),
            windows: Vec::new(),
            active: false,
        });
        entry.windows.extend(ws.windows);
    }
    snapshot.workspaces = merged.into_values().collect();
    
    // Save to file
    let path = get_workspace_path();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    
    match fs::write(&path, serde_json::to_string_pretty(&snapshot).unwrap_or_default()) {
        Ok(_) => ok_response(&req.name, &format!(
            "Saved {} workspaces with {} windows total.",
            snapshot.workspaces.len(),
            snapshot.workspaces.iter().map(|w| w.windows.len()).sum::<usize>()
        )),
        Err(e) => error_response(&req.name, &format!("Failed to save workspace state: {}", e)),
    }
}

/// Restore workspace state
pub fn handle_workspace_restore(req: &ActionRequest) -> ActionResponse {
    let path = get_workspace_path();
    
    let content = match fs::read_to_string(&path) {
        Ok(c) => c,
        Err(e) => return error_response(&req.name, &format!("No saved workspace found: {}", e)),
    };
    
    let snapshot: WorkspaceSnapshot = match serde_json::from_str(&content) {
        Ok(s) => s,
        Err(e) => return error_response(&req.name, &format!("Invalid workspace state: {}", e)),
    };
    
    let current_de = detect_desktop_env();
    if snapshot.desktop_environment != current_de {
        return ok_response(&req.name, &format!(
            "Warning: Desktop environment changed from {} to {}. Some windows may not restore correctly.",
            snapshot.desktop_environment, current_de
        ));
    }
    
    let mut restored = 0;
    let mut failed = 0;
    
    // Restore windows by launching apps
    for ws in &snapshot.workspaces {
        for window in &ws.windows {
            // Launch the application
            let launch_result = launch_app(&window.app_name);
            if launch_result {
                restored += 1;
                
                // Note: Restoring exact position would require window manager integration
                // For now, we just launch the app and let the WM place it
            } else {
                failed += 1;
            }
        }
    }
    
    ok_response(&req.name, &format!(
        "Restored {} windows. {} could not be launched.",
        restored, failed
    ))
}

/// List saved workspaces
pub fn handle_workspace_list(req: &ActionRequest) -> ActionResponse {
    let path = get_workspace_path();
    
    let content = match fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return ok_response(&req.name, "No saved workspaces found."),
    };
    
    let snapshot: WorkspaceSnapshot = match serde_json::from_str(&content) {
        Ok(s) => s,
        Err(e) => return error_response(&req.name, &format!("Invalid workspace state: {}", e)),
    };
    
    let summary: Vec<String> = snapshot.workspaces.iter().map(|ws| {
        format!(
            "Workspace {}: {} windows ({})",
            ws.id,
            ws.windows.len(),
            ws.windows.iter().map(|w| &w.app_name).take(3).cloned().collect::<Vec<_>>().join(", ")
        )
    }).collect();
    
    ok_response(&req.name, &serde_json::json!({
        "timestamp": snapshot.timestamp,
        "desktop": snapshot.desktop_environment,
        "workspaces": summary,
        "total_windows": snapshot.workspaces.iter().map(|w| w.windows.len()).sum::<usize>()
    }).to_string())
}

/// Switch to a specific workspace
pub fn handle_workspace_switch(req: &ActionRequest) -> ActionResponse {
    let workspace = req.payload.as_deref().unwrap_or("0");
    let de = detect_desktop_env();
    
    match de.as_str() {
        "gnome" | "ubuntu" | "pop" => {
            // Use wmctrl to switch workspace
            match run_command("wmctrl", &["-s", workspace], None) {
                Ok(_) => ok_response(&req.name, &format!("Switched to workspace {}", workspace)),
                Err(e) => error_response(&req.name, &e),
            }
        }
        "kde" | "plasma" => {
            match run_command("qdbus", &["org.kde.KWin", "/KWin", "org.kde.KWin.setCurrentDesktop", workspace], None) {
                Ok(_) => ok_response(&req.name, &format!("Switched to workspace {}", workspace)),
                Err(_) => {
                    // Fallback to wmctrl
                    match run_command("wmctrl", &["-s", workspace], None) {
                        Ok(_) => ok_response(&req.name, &format!("Switched to workspace {}", workspace)),
                        Err(e) => error_response(&req.name, &e),
                    }
                }
            }
        }
        "sway" => {
            match run_command("swaymsg", &["workspace", &format!("number {}", workspace)], None) {
                Ok(_) => ok_response(&req.name, &format!("Switched to workspace {}", workspace)),
                Err(e) => error_response(&req.name, &e),
            }
        }
        _ => {
            match run_command("wmctrl", &["-s", workspace], None) {
                Ok(_) => ok_response(&req.name, &format!("Switched to workspace {}", workspace)),
                Err(e) => error_response(&req.name, &e),
            }
        }
    }
}

// Helper functions

fn get_window_geometry(window_id: &str) -> (i32, i32, i32, i32) {
    if let Ok(output) = run_command("xdotool", &["getwindowgeometry", window_id], None) {
        // Parse output like: Position: 100,200 (screen: 0) Geometry: 800x600
        let mut x = 0; let mut y = 0; let mut w = 800; let mut h = 600;
        for line in output.lines() {
            if line.contains("Position:") {
                let pos: Vec<&str> = line.split_whitespace().collect();
                if pos.len() >= 2 {
                    let coords: Vec<&str> = pos[1].split(',').collect();
                    if coords.len() == 2 {
                        x = coords[0].parse().unwrap_or(0);
                        y = coords[1].parse().unwrap_or(0);
                    }
                }
            }
            if line.contains("Geometry:") {
                let geo: Vec<&str> = line.split_whitespace().collect();
                if geo.len() >= 2 {
                    let dims: Vec<&str> = geo[1].split('x').collect();
                    if dims.len() == 2 {
                        w = dims[0].parse().unwrap_or(800);
                        h = dims[1].parse().unwrap_or(600);
                    }
                }
            }
        }
        (x, y, w, h)
    } else {
        (0, 0, 800, 600)
    }
}

fn guess_app_from_title(title: &str) -> String {
    let title_lower = title.to_lowercase();
    
    // Common applications
    if title_lower.contains("firefox") || title_lower.contains("mozilla") {
        return "firefox".to_string();
    }
    if title_lower.contains("chrome") || title_lower.contains("chromium") {
        return "chromium-browser".to_string();
    }
    if title_lower.contains("code") || title_lower.contains("vs code") || title_lower.contains("visual studio code") {
        return "code".to_string();
    }
    if title_lower.contains("terminal") || title_lower.contains("konsole") || title_lower.contains("gnome-terminal") {
        return "gnome-terminal".to_string();
    }
    if title_lower.contains("nautilus") || title_lower.contains("files") || title_lower.contains("dolphin") {
        return "nautilus".to_string();
    }
    if title_lower.contains("slack") {
        return "slack".to_string();
    }
    if title_lower.contains("discord") {
        return "discord".to_string();
    }
    if title_lower.contains("spotify") {
        return "spotify".to_string();
    }
    
    // Default: use first word of title
    title.split_whitespace().next().unwrap_or("unknown").to_string()
}

fn launch_app(app_name: &str) -> bool {
    run_command(app_name, &[], None).is_ok()
}
