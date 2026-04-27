use ai_distro_common::ActionResponse;
use std::path::{Path, PathBuf};
use std::process::Command;

/// Resolve the project's venv Python, falling back to system python3.
/// Same logic as the CLI's get_python() helper.
pub fn resolve_venv_python() -> PathBuf {
    // Check relative to the repo root (CARGO_MANIFEST_DIR is src/rust/ai-distro-agent)
    let repo_root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
    let venv = repo_root.join(".venv/bin/python3");
    if venv.exists() {
        return venv;
    }
    // Also check ~/AI_Distro
    if let Some(home) = dirs::home_dir() {
        let venv = home.join("AI_Distro/.venv/bin/python3");
        if venv.exists() {
            return venv;
        }
    }
    PathBuf::from("python3")
}

pub fn resolve_python_tool(env_var: &str, filename: &str) -> String {
    if let Ok(value) = std::env::var(env_var) {
        if !value.trim().is_empty() {
            return value;
        }
    }

    let repo_root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
    let repo_tool = repo_root.join("tools/agent").join(filename);
    if repo_tool.exists() {
        return repo_tool.to_string_lossy().to_string();
    }

    Path::new("/usr/lib/ai-distro")
        .join(filename)
        .to_string_lossy()
        .to_string()
}

pub fn ok_response(action: &str, message: &str) -> ActionResponse {
    ActionResponse {
        version: 1,
        action: action.to_string(),
        status: "ok".to_string(),
        message: Some(message.to_string()),
        capabilities: None,
        confirmation_id: None,
    }
}

pub fn error_response(action: &str, message: &str) -> ActionResponse {
    ActionResponse {
        version: 1,
        action: action.to_string(),
        status: "error".to_string(),
        message: Some(message.to_string()),
        capabilities: None,
        confirmation_id: None,
    }
}

pub fn run_command(
    // ... rest of the file ...
    cmd: &str,
    args: &[&str],
    env: Option<&[(&str, &str)]>,
) -> Result<String, String> {
    let mut command = Command::new(cmd);
    command.args(args);
    if let Some(envs) = env {
        for (key, val) in envs {
            command.env(key, val);
        }
    }
    let output = command
        .output()
        .map_err(|e| format!("{} failed: {}", cmd, e))?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(format!(
            "{} failed: {}",
            cmd,
            String::from_utf8_lossy(&output.stderr).trim()
        ))
    }
}

pub fn command_exists(cmd: &str) -> bool {
    Command::new("sh")
        .arg("-c")
        .arg(format!("command -v {} >/dev/null 2>&1", cmd))
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}
