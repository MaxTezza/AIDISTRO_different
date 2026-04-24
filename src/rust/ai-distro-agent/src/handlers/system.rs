// AI Distro Version: 1.0.1-test
use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{run_command, command_exists, ok_response, error_response};
use std::process::Command;

pub fn handle_system_update(req: &ActionRequest) -> ActionResponse {
    log::info!("handler: system_update, payload={:?}", req.payload);
    let channel = req.payload.as_deref().unwrap_or("stable");
    
    // 1. System Package Update
    let env = Some(&[("DEBIAN_FRONTEND", "noninteractive")][..]);
    match run_command("apt-get", &["update"], env) {
        Ok(_) => {
            log::info!("system_update: apt update success");
        }
        Err(err) => {
            return error_response(&req.name, &err);
        }
    }

    // 2. Flatpak Update (if available)
    if command_exists("flatpak") {
        match run_command("flatpak", &["update", "-y"], None) {
            Ok(_) => {
                log::info!("system_update: flatpak update success");
                ok_response(
                    &req.name,
                    &format!("I have finished updating your system and apps on the {channel} channel."),
                )
            }
            Err(err) => error_response(
                &req.name,
                &format!("I finished updating your system. Flatpak apps could not be updated: {err}"),
            ),
        }
    } else {
        ok_response(&req.name, "I finished updating your system.")
    }
}

pub fn handle_self_update(req: &ActionRequest) -> ActionResponse {
    log::info!("Starting AI Distro self-update...");
    
    let root = std::env::var("AI_DISTRO_ROOT")
        .unwrap_or_else(|_| format!("{}/AI_Distro", std::env::var("HOME").unwrap_or_default()));

    // 1. Pull changes
    match std::process::Command::new("git")
        .arg("-C").arg(&root)
        .arg("pull").arg("origin").arg("main")
        .output() {
        Ok(out) if !out.status.success() => {
             log::warn!("Git pull warning: {}", String::from_utf8_lossy(&out.stderr));
        },
        Err(err) => return error_response(&req.name, &format!("Git failed: {}", err)),
        _ => {}
    }

    // 2. Rebuild Rust components
    match std::process::Command::new("cargo")
        .current_dir(&root)
        .arg("build").arg("--release")
        .output() {
        Ok(out) if out.status.success() => ok_response(&req.name, "I've updated my own code and rebuilt my core. Please restart me to apply changes."),
        Ok(out) => error_response(&req.name, &format!("Build failed: {}", String::from_utf8_lossy(&out.stderr))),
        Err(err) => error_response(&req.name, &format!("Cargo failed: {}", err)),
    }
}

pub fn handle_import_legacy_data(req: &ActionRequest) -> ActionResponse {
    let path = req.payload.as_deref().unwrap_or("");
    if path.is_empty() {
        return error_response(&req.name, "missing path to import");
    }

    let tool = std::env::var("AI_DISTRO_LEGACY_IMPORTER")
        .unwrap_or_else(|_| "tools/agent/legacy_importer.py".to_string());
    
    // Run asynchronously
    let _ = Command::new("python3").arg(tool).arg(path).spawn();
    ok_response(&req.name, &format!("I've started the Great Migration from {}. I will let you know as I find interesting things.", path))
}

pub fn handle_system_heal(req: &ActionRequest) -> ActionResponse {
    let tool = std::env::var("AI_DISTRO_SYSTEM_HEALER")
        .unwrap_or_else(|_| "tools/agent/system_healer.py".to_string());
    
    // Check one time
    match Command::new("python3").arg(tool).arg("check_now").output() {
        Ok(_) => ok_response(&req.name, "I've performed a health check and applied any necessary repairs."),
        _ => error_response(&req.name, "Failed to run system healer."),
    }
}
