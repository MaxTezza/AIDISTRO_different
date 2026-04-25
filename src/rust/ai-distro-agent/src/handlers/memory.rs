use crate::utils::{error_response, ok_response, resolve_python_tool};
use ai_distro_common::{ActionRequest, ActionResponse};
use std::process::Command;

pub fn handle_remember(req: &ActionRequest) -> ActionResponse {
    let Some(note) = req.payload.as_deref() else {
        return error_response(&req.name, "missing memory text");
    };

    let engine = resolve_python_tool("AI_DISTRO_MEMORY_ENGINE", "memory_engine.py");

    match Command::new("python3")
        .arg(&engine)
        .arg("remember")
        .arg(note)
        .output()
    {
        Ok(out) if out.status.success() => ok_response(&req.name, "I'll remember that."),
        _ => error_response(&req.name, "Failed to store memory."),
    }
}

pub fn handle_read_context(req: &ActionRequest) -> ActionResponse {
    let query = req.payload.as_deref().unwrap_or("current context");
    let engine = resolve_python_tool("AI_DISTRO_MEMORY_ENGINE", "memory_engine.py");

    match Command::new("python3")
        .arg(&engine)
        .arg("query")
        .arg(query)
        .output()
    {
        Ok(out) if out.status.success() => {
            let memories = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &format!("Relevant memories: {}", memories))
        }
        _ => ok_response(&req.name, "No relevant context found."),
    }
}
