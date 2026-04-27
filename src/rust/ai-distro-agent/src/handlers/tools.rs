use crate::utils::{error_response, ok_response, resolve_python_tool};
use ai_distro_common::{ActionRequest, ActionResponse};
use std::process::Command;

pub fn handle_plan_day_outfit(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("today");
    let planner = resolve_python_tool("AI_DISTRO_DAY_PLANNER", "day_planner.py");
    match Command::new(crate::utils::resolve_venv_python()).arg(planner).arg(payload).output() {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if msg.is_empty() {
                ok_response(&req.name, "No outfit recommendation available.")
            } else {
                ok_response(&req.name, &msg)
            }
        }
        Ok(out) => {
            let err = String::from_utf8_lossy(&out.stderr).trim().to_string();
            error_response(
                &req.name,
                if err.is_empty() {
                    "failed to build clothing recommendation"
                } else {
                    &err
                },
            )
        }
        Err(err) => error_response(&req.name, &format!("planner failed: {err}")),
    }
}

pub fn handle_weather_get(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("today");
    let tool = resolve_python_tool("AI_DISTRO_WEATHER_TOOL", "weather_router.py");
    match Command::new(crate::utils::resolve_venv_python()).arg(tool).arg(payload).output() {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if msg.is_empty() {
                ok_response(&req.name, "Weather unavailable.")
            } else {
                ok_response(&req.name, &msg)
            }
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "weather tool failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("weather tool launch failed: {err}")),
    }
}

pub fn handle_calendar_add_event(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing calendar payload");
    };
    let tool = resolve_python_tool("AI_DISTRO_CALENDAR_ROUTER", "calendar_router.py");
    match Command::new(crate::utils::resolve_venv_python())
        .arg(tool)
        .arg("add")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "Calendar event added."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "calendar add failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("calendar tool launch failed: {err}")),
    }
}

pub fn handle_calendar_list_day(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("today");
    let tool = resolve_python_tool("AI_DISTRO_CALENDAR_ROUTER", "calendar_router.py");
    match Command::new(crate::utils::resolve_venv_python())
        .arg(tool)
        .arg("list")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "No events found."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "calendar list failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("calendar tool launch failed: {err}")),
    }
}

pub fn handle_email_inbox_summary(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("in:inbox newer_than:2d");
    let tool = resolve_python_tool("AI_DISTRO_EMAIL_ROUTER", "email_router.py");
    match Command::new(crate::utils::resolve_venv_python())
        .arg(tool)
        .arg("summary")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "No inbox summary available."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "gmail summary failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("gmail tool launch failed: {err}")),
    }
}

pub fn handle_email_search(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("in:inbox");
    let tool = resolve_python_tool("AI_DISTRO_EMAIL_ROUTER", "email_router.py");
    match Command::new(crate::utils::resolve_venv_python())
        .arg(tool)
        .arg("search")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "No email search results."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "gmail search failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("gmail tool launch failed: {err}")),
    }
}

pub fn handle_email_draft(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing draft payload");
    };
    let tool = resolve_python_tool("AI_DISTRO_EMAIL_ROUTER", "email_router.py");
    match Command::new(crate::utils::resolve_venv_python())
        .arg(tool)
        .arg("draft")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "Draft created."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "gmail draft failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("gmail tool launch failed: {err}")),
    }
}

pub fn handle_get_autonomous_address(req: &ActionRequest) -> ActionResponse {
    let tool = resolve_python_tool("AI_DISTRO_IDENTITY_TOOL", "autonomous_identity_tool.py");
    match Command::new(crate::utils::resolve_venv_python())
        .arg(tool)
        .arg("get_address")
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        _ => error_response(&req.name, "failed to get autonomous address"),
    }
}

pub fn handle_poll_autonomous_mail(req: &ActionRequest) -> ActionResponse {
    let tool = resolve_python_tool("AI_DISTRO_IDENTITY_TOOL", "autonomous_identity_tool.py");
    match Command::new(crate::utils::resolve_venv_python()).arg(tool).arg("poll").output() {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        _ => error_response(&req.name, "failed to poll autonomous mail"),
    }
}

pub fn handle_web_task(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("");
    // format: "URL|Goal"
    let parts: Vec<&str> = payload.split('|').collect();
    if parts.len() < 2 {
        return error_response(&req.name, "Invalid payload. Use 'URL|Goal'");
    }
    let url = parts[0];
    let goal = parts[1..].join("|");

    let tool = resolve_python_tool("AI_DISTRO_WEB_NAVIGATOR", "web_navigator.py");
    match Command::new(crate::utils::resolve_venv_python())
        .arg(tool)
        .arg(url)
        .arg(goal)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        _ => error_response(&req.name, "failed to execute web task"),
    }
}

pub fn handle_player_control(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("play");
    let parts: Vec<&str> = payload.split('|').collect();
    let cmd = parts[0];
    let target = if parts.len() > 1 { parts[1] } else { "" };

    let tool = resolve_python_tool("AI_DISTRO_PLAYER_TOOL", "player_control.py");
    match Command::new(crate::utils::resolve_venv_python())
        .arg(tool)
        .arg(cmd)
        .arg(target)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        _ => error_response(&req.name, "failed to control music player"),
    }
}

pub fn handle_gallery_show(req: &ActionRequest) -> ActionResponse {
    let folder = req.payload.as_deref().unwrap_or("");
    let tool = resolve_python_tool("AI_DISTRO_GALLERY_TOOL", "gallery_show.py");
    match Command::new(crate::utils::resolve_venv_python()).arg(tool).arg(folder).output() {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        _ => error_response(&req.name, "failed to show photo gallery"),
    }
}

pub fn handle_news_headlines(req: &ActionRequest) -> ActionResponse {
    let tool = resolve_python_tool("AI_DISTRO_NEWS_TOOL", "news_reader.py");
    match Command::new(crate::utils::resolve_venv_python()).arg(tool).output() {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        _ => error_response(&req.name, "failed to fetch news headlines"),
    }
}

pub fn handle_family_message(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("");
    let parts: Vec<&str> = payload.split('|').collect();
    if parts.len() < 2 {
        return error_response(&req.name, "Invalid payload. Use 'FamilyMember|Message'");
    }
    let name = parts[0];
    let msg = parts[1..].join("|");

    let tool = resolve_python_tool("AI_DISTRO_FAMILY_TOOL", "family_messenger.py");
    match Command::new(crate::utils::resolve_venv_python())
        .arg(tool)
        .arg(name)
        .arg(msg)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, &msg)
        }
        _ => error_response(&req.name, "failed to send family message"),
    }
}
