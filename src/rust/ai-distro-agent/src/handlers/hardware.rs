use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{ok_response, error_response, run_command};

pub fn handle_wifi_scan(req: &ActionRequest) -> ActionResponse {
    match run_command("nmcli", &["-t", "-f", "SSID,SIGNAL", "dev", "wifi"], None) {
        Ok(out) => ok_response(&req.name, &format!("Available Wi-Fi networks:\n{}", out)),
        Err(e) => error_response(&req.name, &e),
    }
}

pub fn handle_wifi_connect(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("");
    let parts: Vec<&str> = payload.split('|').collect();
    if parts.len() == 2 {
        let ssid = parts[0];
        let password = parts[1];
        match run_command("nmcli", &["dev", "wifi", "connect", ssid, "password", password], None) {
            Ok(_) => ok_response(&req.name, &format!("Successfully connected to {}", ssid)),
            Err(e) => error_response(&req.name, &e),
        }
    } else {
        error_response(&req.name, "Invalid payload. Use 'SSID|Password'")
    }
}

pub fn handle_bluetooth_scan(req: &ActionRequest) -> ActionResponse {
    // Bluetooth scanning is usually async, for now we just list paired devices
    match run_command("bluetoothctl", &["devices"], None) {
        Ok(out) => ok_response(&req.name, &format!("Known Bluetooth devices:\n{}", out)),
        Err(e) => error_response(&req.name, &e),
    }
}

pub fn handle_bluetooth_pair(req: &ActionRequest) -> ActionResponse {
    let mac = req.payload.as_deref().unwrap_or("");
    if mac.is_empty() {
        return error_response(&req.name, "missing MAC address");
    }
    match run_command("bluetoothctl", &["pair", mac], None) {
        Ok(_) => ok_response(&req.name, &format!("Pairing request sent to {}", mac)),
        Err(e) => error_response(&req.name, &e),
    }
}
