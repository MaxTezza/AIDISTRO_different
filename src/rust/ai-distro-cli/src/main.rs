use clap::{Parser, Subcommand};
use colored::*;
use std::process::Command;
use sysinfo::System;
use std::fs;
use serde_json::Value;

#[derive(Parser)]
#[command(name = "ai-distro")]
#[command(about = "AI Distro: Master Control CLI for the Revolutionary OS", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Start,
    Stop,
    Restart,
    Status,
    Setup,
    /// Manage the intelligence settings (Local vs Cloud)
    Intelligence {
        #[command(subcommand)]
        action: IntelCommands,
    },
}

#[derive(Subcommand)]
enum IntelCommands {
    /// Set the intelligence mode (local or cloud)
    SetMode { mode: String },
    /// Set the local model size (1b or 3b)
    SetLocal { size: String },
    /// Set the cloud provider and API key
    SetCloud { provider: String, key: String },
}

fn manage_service(action: &str, service: &str) {
    let status = Command::new("systemctl").arg("--user").arg(action).arg(format!("{}.service", service)).status();
    if let Ok(s) = status {
        if s.success() { println!("{} {}: {}", "✔".green(), action, service); }
        else { println!("{} {} failed: {}", "✘".red(), action, service); }
    }
}

fn update_config(key: &str, val: Value) {
    let home = dirs::home_dir().unwrap_or_default();
    let config_path = home.join("AI_Distro/configs/agent.json");
    if let Ok(content) = fs::read_to_string(&config_path) {
        if let Ok(mut config) = serde_json::from_str::<Value>(&content) {
            config["intelligence"][key] = val;
            let _ = fs::write(&config_path, serde_json::to_string_pretty(&config).unwrap());
            println!("{} Updated intelligence configuration.", "✔".green());
        }
    }
}

fn main() {
    let cli = Cli::parse();
    let services = ["ai-distro-agent", "ai-distro-hud", "ai-distro-voice", "ai-distro-curator"];

    match &cli.command {
        Commands::Start => {
            println!("{}", "Starting AI Distro Revolutionary Stack...".cyan().bold());
            for svc in services { manage_service("start", svc); }
        }
        Commands::Stop => {
            println!("{}", "Shutting down AI components...".yellow().bold());
            for svc in services { manage_service("stop", svc); }
        }
        Commands::Restart => {
            println!("{}", "Cycling AI Distro services...".magenta().bold());
            for svc in services { manage_service("restart", svc); }
        }
        Commands::Status => {
            println!("\n{}", "AI DISTRO: SYSTEM PULSE".cyan().bold());
            println!("{}", "=".repeat(30));
            let mut sys = System::new_all();
            sys.refresh_all();
            for svc in services {
                let is_active = Command::new("systemctl").arg("--user").arg("is-active").arg(format!("{}.service", svc)).output()
                    .map(|o| String::from_utf8_lossy(&o.stdout).trim() == "active").unwrap_or(false);
                let status_icon = if is_active { "●".green() } else { "○".red() };
                let status_text = if is_active { "RUNNING".green() } else { "OFFLINE".red() };
                println!("{} {:<18} [{}]", status_icon, svc, status_text);
            }
            println!("{}\n", "=".repeat(30));
        }
        Commands::Setup => {
            let home = dirs::home_dir().unwrap_or_default();
            let wizard_path = home.join("AI_Distro/tools/agent/setup_wizard.py");
            let _ = Command::new("python3").arg(wizard_path).status();
        }
        Commands::Intelligence { action } => match action {
            IntelCommands::SetMode { mode } => {
                let use_cloud = mode.to_lowercase() == "cloud";
                update_config("use_cloud", Value::Bool(use_cloud));
                println!("Intelligence mode set to: {}", if use_cloud { "CLOUD".yellow() } else { "LOCAL".green() });
            }
            IntelCommands::SetLocal { size } => {
                let model = if size.to_lowercase() == "3b" { "llama-3.2-3b-instruct.gguf" } else { "llama-3.2-1b-instruct.gguf" };
                update_config("local_model", Value::String(model.to_string()));
                println!("Local model set to: {}", size.to_uppercase().green());
            }
            IntelCommands::SetCloud { provider, key } => {
                update_config("cloud_provider", Value::String(provider.clone()));
                update_config("api_key", Value::String(key.to_string()));
                println!("Cloud provider set to: {} (Key saved)", provider.cyan());
            }
        }
    }
}
