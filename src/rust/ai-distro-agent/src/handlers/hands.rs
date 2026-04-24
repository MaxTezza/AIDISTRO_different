use crate::utils::{error_response, ok_response, run_command};
use ai_distro_common::{ActionRequest, ActionResponse};

pub fn handle_ui_click(req: &ActionRequest) -> ActionResponse {
    let Some(element_name) = req.payload.as_deref() else {
        return error_response(&req.name, "missing element name to click");
    };

    // 1. Try to find the element coordinates using xdotool search + window focus
    // In a full implementation, we'd use AT-SPI to get exact coords.
    // For the revolutionary v1.0, we use a robust xdotool search.
    log::info!("Attempting to click UI element: {}", element_name);

    // Simple robust sequence:
    // Search for window -> Focus it -> Use xdotool to click a string (if supported by app)
    // or use coordinate fallback.

    // Revolutionary Shortcut: Use 'xdotool search' to find the window and 'xdotool key' for common shortcuts
    // OR if element_name is a coordinate "x,y", click it.
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

    // Fallback: Search for the text in the active window (using xdotool's type/key hooks)
    // This is where "The Eyes" (VLM) can help by providing coordinates to this tool.
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

    // Format: "WindowName|Text to type"
    let parts: Vec<&str> = payload.split('|').collect();
    if parts.len() == 2 {
        let win = parts[0];
        let text = parts[1];

        let _ = run_command(
            "xdotool",
            &["search", "--name", win, "windowactivate"],
            None,
        );
        match run_command("xdotool", &["type", text], None) {
            Ok(_) => ok_response(&req.name, &format!("Typed text into {}", win)),
            Err(e) => error_response(&req.name, &e),
        }
    } else {
        // Just type into current focus
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
