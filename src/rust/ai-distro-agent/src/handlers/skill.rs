use crate::utils::{error_response, ok_response};
use ai_distro_common::{ActionRequest, ActionResponse};
use std::fs;
use std::path::Path;

pub fn handle_skill_install(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing skill manifest URL or JSON");
    };

    let skills_dir = std::env::var("AI_DISTRO_SKILLS_DYNAMIC_DIR")
        .unwrap_or_else(|_| "src/skills/dynamic".to_string());

    if !Path::new(&skills_dir).exists() {
        let _ = fs::create_dir_all(&skills_dir);
    }

    // For now, assume payload is a JSON string of the manifest
    // In a real scenario, this would be a URL fetch + verification
    match serde_json::from_str::<ai_distro_common::SkillManifest>(payload) {
        Ok(manifest) => {
            let file_path = Path::new(&skills_dir).join(format!("{}.json", manifest.name));
            match fs::write(&file_path, payload) {
                Ok(_) => ok_response(
                    &req.name,
                    &format!("Skill '{}' installed successfully.", manifest.display_name),
                ),
                Err(err) => error_response(&req.name, &format!("Failed to save skill: {}", err)),
            }
        }
        Err(err) => error_response(&req.name, &format!("Invalid skill manifest: {}", err)),
    }
}

pub fn handle_skill_list(req: &ActionRequest) -> ActionResponse {
    let core_dir = "src/skills/core";
    let dynamic_dir = "src/skills/dynamic";

    let mut skills = Vec::new();
    for dir in &[core_dir, dynamic_dir] {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                if let Ok(content) = fs::read_to_string(entry.path()) {
                    if let Ok(manifest) =
                        serde_json::from_str::<ai_distro_common::SkillManifest>(&content)
                    {
                        skills.push(manifest.display_name);
                    }
                }
            }
        }
    }

    if skills.is_empty() {
        ok_response(&req.name, "No skills found.")
    } else {
        ok_response(
            &req.name,
            &format!("Available skills: {}", skills.join(", ")),
        )
    }
}
