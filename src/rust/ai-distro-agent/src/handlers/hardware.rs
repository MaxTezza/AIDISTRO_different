use crate::utils::{error_response, ok_response, run_command};
use ai_distro_common::{ActionRequest, ActionResponse};

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
        match run_command(
            "nmcli",
            &["dev", "wifi", "connect", ssid, "password", password],
            None,
        ) {
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

pub fn handle_battery_status(req: &ActionRequest) -> ActionResponse {
    // Read real battery info from sysfs
    let capacity = std::fs::read_to_string("/sys/class/power_supply/BAT0/capacity")
        .unwrap_or_else(|_| "N/A".to_string());
    let status = std::fs::read_to_string("/sys/class/power_supply/BAT0/status")
        .unwrap_or_else(|_| "Unknown".to_string());
    ok_response(
        &req.name,
        &format!("Battery: {}% ({})", capacity.trim(), status.trim()),
    )
}

pub fn handle_hw_info(req: &ActionRequest) -> ActionResponse {
    let mut info = Vec::new();

    // CPU info
    if let Ok(cpuinfo) = std::fs::read_to_string("/proc/cpuinfo") {
        if let Some(model_line) = cpuinfo.lines().find(|l| l.starts_with("model name")) {
            info.push(format!(
                "CPU: {}",
                model_line.split(':').nth(1).unwrap_or("?").trim()
            ));
        }
    }

    // Memory info
    if let Ok(meminfo) = std::fs::read_to_string("/proc/meminfo") {
        let mut total_kb = 0u64;
        let mut avail_kb = 0u64;
        for line in meminfo.lines() {
            if line.starts_with("MemTotal:") {
                total_kb = line
                    .split_whitespace()
                    .nth(1)
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(0);
            } else if line.starts_with("MemAvailable:") {
                avail_kb = line
                    .split_whitespace()
                    .nth(1)
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(0);
            }
        }
        info.push(format!(
            "Memory: {:.1} GB available / {:.1} GB total",
            avail_kb as f64 / 1_048_576.0,
            total_kb as f64 / 1_048_576.0
        ));
    }

    // Disk usage
    if let Ok(out) = run_command("df", &["-h", "--output=target,size,avail,pcent", "/"], None) {
        info.push(format!("Disk:\n{}", out));
    }

    ok_response(&req.name, &info.join("\n"))
}
