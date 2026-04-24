use zbus::Connection;
use std::error::Error;
use log::{info, error};
use tokio::sync::mpsc;
use serde::{Serialize, Deserialize};
use serde_json::json;
use crate::ipc::broadcast_event;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum SystemEvent {
    BatteryLow(u8),
    NetworkChanged(String),
    HardwareAdded(String),
    TimeTrigger(String),
}

pub struct NervousSystem {
    tx: mpsc::Sender<SystemEvent>,
}

impl NervousSystem {
    pub fn new(tx: mpsc::Sender<SystemEvent>) -> Self {
        Self { tx }
    }

    pub async fn start(&self) -> Result<(), Box<dyn Error>> {
        let connection = Connection::system().await?;
        
        // 1. Monitor Battery
        let tx_battery = self.tx.clone();
        let conn_clone = connection.clone();
        tokio::spawn(async move {
            if let Err(e) = monitor_battery(&conn_clone, tx_battery).await {
                error!("Battery monitor error: {}", e);
            }
        });

        // 2. Monitor Hardware (USB/Devices)
        let tx_hw = self.tx.clone();
        tokio::spawn(async move {
            if let Err(e) = monitor_hardware(tx_hw).await {
                error!("Hardware monitor error: {}", e);
            }
        });

        Ok(())
    }
}

async fn monitor_battery(_conn: &Connection, tx: mpsc::Sender<SystemEvent>) -> Result<(), Box<dyn Error>> {
    let mut last_val = 100;
    loop {
        // Read from sysfs for maximum reliability across distros
        if let Ok(content) = std::fs::read_to_string("/sys/class/power_supply/BAT0/capacity") {
            if let Ok(pct) = content.trim().parse::<u8>() {
                if pct <= 15 && last_val > 15 {
                    let _ = tx.send(SystemEvent::BatteryLow(pct)).await;
                }
                last_val = pct;
            }
        }
        tokio::time::sleep(tokio::time::Duration::from_secs(60)).await;
    }
}

async fn monitor_hardware(tx: mpsc::Sender<SystemEvent>) -> Result<(), Box<dyn Error>> {
    use tokio::process::Command;
    use std::process::Stdio;
    use tokio::io::{BufReader, AsyncBufReadExt};

    // Use udevadm monitor to catch real-time kernel events
    let mut child = Command::new("udevadm")
        .args(["monitor", "--subsystem-match=usb", "--property"])
        .stdout(Stdio::piped())
        .spawn()?;

    let stdout = child.stdout.take().ok_or("Failed to capture udevadm stdout")?;
    let mut reader = BufReader::new(stdout).lines();

    info!("Nervous System: Hardware monitor active.");

    while let Ok(Some(line)) = reader.next_line().await {
        if line.contains("ID_MODEL=") {
            let model = line.split('=').last().unwrap_or("Unknown Device");
            let _ = tx.send(SystemEvent::HardwareAdded(model.to_string())).await;
        }
    }
    Ok(())
}

pub async fn process_events(mut rx: mpsc::Receiver<SystemEvent>) {
    while let Some(event) = rx.recv().await {
        let message = match event {
            SystemEvent::BatteryLow(pct) => {
                format!("Battery is low ({}%). Should I enable power saving mode?", pct)
            },
            SystemEvent::NetworkChanged(net) => {
                format!("Connected to {}. Need anything for this network?", net)
            },
            SystemEvent::HardwareAdded(dev) => {
                format!("I see a new device: {}. Should I index its files or help you open it?", dev)
            },
            SystemEvent::TimeTrigger(msg) => msg,
        };

        info!("Nervous System Event: {}", message);
        
        // Broadcast directly to the Visual HUD
        broadcast_event(json!({
            "type": "info",
            "title": "proactive_suggestion",
            "message": message
        })).await;
    }
}
