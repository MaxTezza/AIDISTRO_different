//! Software Forge Handler — AI Distro's code generation and project scaffolding engine.
//! Bridges the Rust agent to the Python `software_forge.py` tool.

use crate::utils::{error_response, ok_response, resolve_python_tool};
use ai_distro_common::{ActionRequest, ActionResponse};
use std::process::Command;

/// Generate and register a standalone script
pub fn handle_forge_script(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("{}");

    // Parse JSON payload or treat as description
    let (name, description, language) = if payload.starts_with('{') {
        match serde_json::from_str::<serde_json::Value>(payload) {
            Ok(v) => (
                v["name"].as_str().unwrap_or("untitled").to_string(),
                v["description"]
                    .as_str()
                    .unwrap_or("A custom script")
                    .to_string(),
                v["language"].as_str().unwrap_or("python").to_string(),
            ),
            Err(_) => (
                "untitled".to_string(),
                payload.to_string(),
                "python".to_string(),
            ),
        }
    } else {
        (
            "untitled".to_string(),
            payload.to_string(),
            "python".to_string(),
        )
    };

    let tool = resolve_python_tool("AI_DISTRO_SOFTWARE_FORGE", "software_forge.py");
    match Command::new("python3")
        .arg(&tool)
        .arg("create_script")
        .arg(&name)
        .arg(&description)
        .arg(&language)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "Script generation failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("Software Forge failed: {err}")),
    }
}

/// Scaffold a complete project
pub fn handle_forge_project(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("{}");

    let (name, project_type, description) = if payload.starts_with('{') {
        match serde_json::from_str::<serde_json::Value>(payload) {
            Ok(v) => (
                v["name"]
                    .as_str()
                    .unwrap_or("my_project")
                    .to_string(),
                v["type"].as_str().unwrap_or("generic").to_string(),
                v["description"]
                    .as_str()
                    .unwrap_or("A new project")
                    .to_string(),
            ),
            Err(_) => (
                "my_project".to_string(),
                "generic".to_string(),
                payload.to_string(),
            ),
        }
    } else {
        (
            "my_project".to_string(),
            "generic".to_string(),
            payload.to_string(),
        )
    };

    let tool = resolve_python_tool("AI_DISTRO_SOFTWARE_FORGE", "software_forge.py");
    match Command::new("python3")
        .arg(&tool)
        .arg("create_project")
        .arg(&name)
        .arg(&project_type)
        .arg(&description)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "Project scaffolding failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("Software Forge failed: {err}")),
    }
}

/// Execute code in a sandboxed environment
pub fn handle_forge_execute(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("");
    if payload.is_empty() {
        return error_response(&req.name, "No code provided.");
    }

    let tool = resolve_python_tool("AI_DISTRO_SOFTWARE_FORGE", "software_forge.py");
    match Command::new("python3")
        .arg(&tool)
        .arg("execute")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "Execution failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("Software Forge failed: {err}")),
    }
}

/// Generate code without saving (returns code in response)
pub fn handle_forge_generate(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("");
    if payload.is_empty() {
        return error_response(&req.name, "No description provided.");
    }

    let tool = resolve_python_tool("AI_DISTRO_SOFTWARE_FORGE", "software_forge.py");
    match Command::new("python3")
        .arg(&tool)
        .arg("generate")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "Code generation failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("Software Forge failed: {err}")),
    }
}
