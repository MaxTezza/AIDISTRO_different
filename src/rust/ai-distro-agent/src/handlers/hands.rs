use crate::utils::{error_response, ok_response, run_command};
use ai_distro_common::{ActionRequest, ActionResponse};

/// The Hands — AT-SPI Deep UI Automation
///
/// Uses the Linux Accessibility Stack to interact with UI elements
/// semantically (by name/role) rather than by blind coordinate clicking.
/// Falls back to xdotool automatically when AT-SPI isn't available.

fn atspi_cmd(action: &str, args: &[&str]) -> Result<String, String> {
    let tools_dir = std::env::var("AI_DISTRO_TOOLS_DIR")
        .unwrap_or_else(|_| {
            let home = dirs::home_dir().unwrap_or_default();
            home.join("AI_Distro/tools/agent").to_string_lossy().to_string()
        });
    let script = format!("{}/atspi_hands.py", tools_dir);

    let mut cmd_args = vec![script.as_str(), action];
    cmd_args.extend_from_slice(args);

    run_command("python3", &cmd_args, None)
}

fn parse_atspi_result(output: &str) -> (bool, String) {
    if let Ok(val) = serde_json::from_str::<serde_json::Value>(output) {
        let status = val["status"].as_str().unwrap_or("error");
        let message = val["message"].as_str().unwrap_or("unknown");
        (status == "ok", message.to_string())
    } else {
        (false, output.to_string())
    }
}

pub fn handle_ui_click(req: &ActionRequest) -> ActionResponse {
    let Some(element_name) = req.payload.as_deref() else {
        return error_response(&req.name, "missing element name to click");
    };

    log::info!("Attempting to click UI element: {}", element_name);

    // Try AT-SPI semantic click first
    match atspi_cmd("click", &[element_name]) {
        Ok(output) => {
            let (ok, msg) = parse_atspi_result(&output);
            if ok {
                return ok_response(&req.name, &msg);
            }
            log::warn!("AT-SPI click failed: {}. Trying xdotool fallback.", msg);
        }
        Err(e) => {
            log::warn!("AT-SPI unavailable: {}. Falling back to xdotool.", e);
        }
    }

    // Fallback 1: Coordinate click
    if element_name.contains(',') {
        let parts: Vec<&str> = element_name.split(',').collect();
        if parts.len() == 2 {
            let x = parts[0];
            let y = parts[1];
            if run_command("xdotool", &["mousemove", x, y, "click", "1"], None).is_ok() {
                return ok_response(&req.name, &format!("Clicked coordinates {},{}", x, y));
            }
        }
    }

    // Fallback 2: xdotool window search
    match run_command(
        "xdotool",
        &["search", "--name", element_name, "windowactivate"],
        None,
    ) {
        Ok(_) => ok_response(
            &req.name,
            &format!("Focused and clicked element '{}'", element_name),
        ),
        Err(e) => error_response(&req.name, &format!("Could not find element: {}", e)),
    }
}

pub fn handle_ui_type(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing text to type");
    };

    log::info!("Attempting to type into UI element");

    // Format: "FieldName|Text to type"
    let parts: Vec<&str> = payload.split('|').collect();

    if parts.len() == 2 {
        let field = parts[0];
        let text = parts[1];

        // Try AT-SPI semantic type
        let atspi_payload = format!("{}|{}", field, text);
        match atspi_cmd("type", &[&atspi_payload]) {
            Ok(output) => {
                let (ok, msg) = parse_atspi_result(&output);
                if ok {
                    return ok_response(&req.name, &msg);
                }
                log::warn!("AT-SPI type failed: {}. Falling back.", msg);
            }
            Err(_) => {}
        }

        // Fallback: xdotool
        let _ = run_command(
            "xdotool",
            &["search", "--name", field, "windowactivate"],
            None,
        );
        match run_command("xdotool", &["type", text], None) {
            Ok(_) => ok_response(&req.name, &format!("Typed text into {}", field)),
            Err(e) => error_response(&req.name, &e),
        }
    } else {
        // Just type into current focus
        match atspi_cmd("type", &[payload]) {
            Ok(output) => {
                let (ok, msg) = parse_atspi_result(&output);
                if ok {
                    return ok_response(&req.name, &msg);
                }
            }
            Err(_) => {}
        }
        match run_command("xdotool", &["type", payload], None) {
            Ok(_) => ok_response(&req.name, "Typed text into active field."),
            Err(e) => error_response(&req.name, &e),
        }
    }
}

pub fn handle_ui_shortcut(req: &ActionRequest) -> ActionResponse {
    let Some(shortcut) = req.payload.as_deref() else {
        return error_response(&req.name, "missing shortcut (e.g. ctrl+c)");
    };
    match run_command("xdotool", &["key", shortcut], None) {
        Ok(_) => ok_response(&req.name, &format!("Executed shortcut {}", shortcut)),
        Err(e) => error_response(&req.name, &e),
    }
}

pub fn handle_ui_read(req: &ActionRequest) -> ActionResponse {
    let target = req.payload.as_deref().unwrap_or("");

    match atspi_cmd("read", &[target]) {
        Ok(output) => {
            let (ok, msg) = parse_atspi_result(&output);
            if ok {
                return ok_response(&req.name, &msg);
            }
            error_response(&req.name, &msg)
        }
        Err(e) => error_response(&req.name, &format!("AT-SPI read failed: {}", e)),
    }
}

pub fn handle_ui_list(req: &ActionRequest) -> ActionResponse {
    let role_filter = req.payload.as_deref().unwrap_or("");

    let args: Vec<&str> = if role_filter.is_empty() {
        vec![]
    } else {
        vec![role_filter]
    };

    match atspi_cmd("list", &args) {
        Ok(output) => ok_response(&req.name, &output),
        Err(e) => error_response(&req.name, &format!("AT-SPI list failed: {}", e)),
    }
}
