use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{ok_response, error_response, run_command, command_exists};

pub fn handle_store_search(req: &ActionRequest) -> ActionResponse {
    let query = req.payload.as_deref().unwrap_or("");
    let mut results = String::new();

    // 1. Search Flatpak
    if command_exists("flatpak") {
        if let Ok(out) = run_command("flatpak", &["search", "--columns=name,description", query], None) {
            results.push_str("--- Flatpak Results ---\n");
            results.push_str(&out);
        }
    }

    // 2. Search APT (limited)
    if let Ok(out) = run_command("apt-cache", &["search", "--names-only", query], None) {
        results.push_str("\n--- APT Results ---\n");
        results.push_str(&out.lines().take(10).collect::<Vec<_>>().join("\n"));
    }

    ok_response(&req.name, if results.is_empty() { "No results found." } else { &results })
}

pub fn handle_store_install(req: &ActionRequest) -> ActionResponse {
    let app = req.payload.as_deref().unwrap_or("");
    if app.is_empty() {
        return error_response(&req.name, "missing application ID");
    }

    // Heuristic: if it looks like a flatpak ID (com.domain.app), use flatpak
    if app.contains('.') && command_exists("flatpak") {
        match run_command("flatpak", &["install", "-y", "flathub", app], None) {
            Ok(_) => ok_response(&req.name, &format!("Successfully installed {} via Flatpak", app)),
            Err(e) => error_response(&req.name, &e),
        }
    } else {
        // Fallback to apt
        let env = Some(&[("DEBIAN_FRONTEND", "noninteractive")][..]);
        match run_command("apt-get", &["install", "-y", app], env) {
            Ok(_) => ok_response(&req.name, &format!("Successfully installed {} via APT", app)),
            Err(e) => error_response(&req.name, &e),
        }
    }
}
