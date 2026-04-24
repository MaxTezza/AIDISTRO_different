// AI Distro Version: 1.0.1-test
use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{run_command, command_exists, ok_response, error_response};

pub fn handle_system_update(req: &ActionRequest) -> ActionResponse {
    log::info!("handler: system_update, payload={:?}", req.payload);
    
    // Check for immutable flag
    if std::path::Path::new("/etc/ai-distro/immutable").exists() {
        // In a real implementation, this would trigger the A/B partition swap logic.
        // For now, we simulate the check.
        return ok_response(&req.name, "System is immutable. Checking for OTA updates... (Simulator: System is up to date).");
    }

    // Legacy/Dev Mode: Use apt-get
    let env = Some(&[("DEBIAN_FRONTEND", "noninteractive")][..]);
    if let Err(err) = run_command("apt-get", &["update"], env) {
        if err.contains("Permission denied") || err.contains("Unable to lock directory") {
            return error_response(
                &req.name,
                "I need administrator permission to update system packages. Please confirm the action in the privileged agent session.",
            );
        }
        return error_response(&req.name, &err);
    }
    if let Err(err) = run_command("apt-get", &["upgrade", "-y"], env) {
        if err.contains("Permission denied") || err.contains("Unable to acquire the dpkg frontend lock") {
            return error_response(
                &req.name,
                "I need administrator permission to apply updates. Please confirm the action in the privileged agent session.",
            );
        }
        return error_response(&req.name, &err);
    }
    if command_exists("flatpak") {
        match run_command("flatpak", &["update", "-y"], None) {
            Ok(_) => ok_response(&req.name, "I finished updating your system and Flatpak apps."),
            Err(err) => ok_response(
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
             // We'll log the error but proceed to build if the error is just 'local changes'
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
