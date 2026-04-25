use crate::utils::{error_response, ok_response, resolve_python_tool, run_command};
use ai_distro_common::{ActionRequest, ActionResponse};
use std::fs;
use std::process::Command;

pub fn handle_open_url(req: &ActionRequest) -> ActionResponse {
    let Some(url) = req.payload.as_deref() else {
        return error_response(&req.name, "missing url");
    };

    if !is_valid_url(url) {
        return error_response(&req.name, "invalid or unsafe url");
    }

    match run_command("xdg-open", &[url], None) {
        Ok(_) => ok_response(&req.name, &format!("I've opened {} for you.", url)),
        Err(err) => error_response(&req.name, &err),
    }
}

pub fn handle_open_app(req: &ActionRequest) -> ActionResponse {
    let Some(app) = req.payload.as_deref() else {
        return error_response(&req.name, "missing app name");
    };

    if !is_valid_app_name(app) {
        return error_response(&req.name, "invalid app name");
    }

    match run_command(app, &[], None) {
        Ok(_) => ok_response(&req.name, &format!("I've launched {}.", app)),
        Err(err) => error_response(&req.name, &err),
    }
}

pub fn handle_list_files(req: &ActionRequest) -> ActionResponse {
    let path = req.payload.as_deref().unwrap_or(".");
    match fs::read_dir(path) {
        Ok(entries) => {
            let files: Vec<String> = entries
                .filter_map(|e| e.ok())
                .map(|e| e.file_name().to_string_lossy().to_string())
                .collect();
            ok_response(&req.name, &files.join(", "))
        }
        Err(err) => error_response(&req.name, &format!("failed to list files: {err}")),
    }
}

pub fn handle_screen_context(req: &ActionRequest) -> ActionResponse {
    let screenshot_path = "/tmp/ai-distro-screen.png";
    let vision_script = resolve_python_tool("AI_DISTRO_VISION_BRAIN", "vision_brain.py");

    // 1. Capture Screen
    if let Err(err) = run_command("scrot", &["-o", screenshot_path], None) {
        return error_response(&req.name, &format!("Failed to capture screen: {}", err));
    }

    // 2. Run Vision Analysis
    match Command::new("python3")
        .arg(&vision_script)
        .arg(screenshot_path)
        .arg(req.payload.as_deref().unwrap_or("What do you see?"))
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "I see your desktop, but couldn't identify specific details."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => {
            let err = String::from_utf8_lossy(&out.stderr).trim().to_string();
            error_response(&req.name, &format!("Vision analysis failed: {}", err))
        }
        Err(err) => error_response(&req.name, &format!("Failed to launch vision brain: {}", err)),
    }
}

pub fn handle_launch_app_semantic(req: &ActionRequest) -> ActionResponse {
    let Some(query) = req.payload.as_deref() else {
        return error_response(&req.name, "missing application search query");
    };

    let script = resolve_python_tool("AI_DISTRO_SEMANTIC_LAUNCHER", "semantic_launcher.py");

    match Command::new("python3")
        .arg(&script)
        .arg("launch")
        .arg(query)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "I found a match and launched it."
                } else {
                    &msg
                },
            )
        }
        _ => error_response(
            &req.name,
            "I couldn't find an application that matches your description.",
        ),
    }
}

fn is_valid_app_name(app: &str) -> bool {
    if app.is_empty() || app.len() > 96 {
        return false;
    }
    app.chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
}

fn is_valid_url(url: &str) -> bool {
    if url.is_empty() || url.len() > 2048 {
        return false;
    }
    if !(url.starts_with("http://") || url.starts_with("https://")) {
        return false;
    }
    if url.chars().any(|c| c.is_ascii_control() || c.is_whitespace()) {
        return false;
    }
    true
}
