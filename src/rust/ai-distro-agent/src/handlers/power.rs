use crate::utils::{error_response, ok_response, run_command};
use ai_distro_common::{ActionRequest, ActionResponse};

pub fn handle_power_reboot(req: &ActionRequest) -> ActionResponse {
    match run_command("systemctl", &["reboot"], None) {
        Ok(_) => ok_response(&req.name, "Rebooting now."),
        Err(err) => error_response(&req.name, &err),
    }
}

pub fn handle_power_shutdown(req: &ActionRequest) -> ActionResponse {
    match run_command("systemctl", &["poweroff"], None) {
        Ok(_) => ok_response(&req.name, "Shutting down now."),
        Err(err) => error_response(&req.name, &err),
    }
}

pub fn handle_power_sleep(req: &ActionRequest) -> ActionResponse {
    match run_command("systemctl", &["suspend"], None) {
        Ok(_) => ok_response(&req.name, "Sleeping now."),
        Err(err) => error_response(&req.name, &err),
    }
}
