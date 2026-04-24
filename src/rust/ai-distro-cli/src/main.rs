use clap::{Parser, Subcommand};
use colored::*;
use std::process::Command;
use sysinfo::{System, ProcessExt, SystemExt};

#[derive(Parser)]
#[command(name = "ai-distro")]
#[command(about = "AI Distro: Master Control CLI for the Revolutionary OS", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Start the entire AI stack
    Start,
    /// Stop the entire AI stack
    Stop,
    /// Restart all AI components
    Restart,
    /// Show the health and pulse of the OS
    Status,
    /// Run the onboarding setup wizard
    Setup,
}

fn manage_service(action: &str, service: &str) {
    let status = Command::new("systemctl")
        .arg("--user")
        .arg(action)
        .arg(format!("{}.service", service))
        .status();
    
    if let Ok(s) = status {
        if s.success() {
            println!("{} {}: {}", "✔".green(), action, service);
        } else {
            println!("{} {} failed: {}", "✘".red(), action, service);
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
                let is_active = Command::new("systemctl")
                    .arg("--user")
                    .arg("is-active")
                    .arg(format!("{}.service", svc))
                    .output()
                    .map(|o| String::from_utf8_lossy(&o.stdout).trim() == "active")
                    .unwrap_or(false);
                
                let status_icon = if is_active { "●".green() } else { "○".red() };
                let status_text = if is_active { "RUNNING".green() } else { "OFFLINE".red() };
                println!("{} {:<18} [{}]", status_icon, svc, status_text);
            }
            
            // Check for Models
            let model_path = std::env::home_dir().unwrap().join(".cache/ai-distro/models/llama-3.2-1b-instruct.gguf");
            let model_status = if model_path.exists() { "LOADED".green() } else { "MISSING".red() };
            println!("\n{} {:<18} [{}]", "🧠", "Brain Model", model_status);
            
            println!("{}\n", "=".repeat(30));
        }
        Commands::Setup => {
            let wizard_path = std::env::home_dir().unwrap().join("AI_Distro/tools/agent/setup_wizard.py");
            let _ = Command::new("python3").arg(wizard_path).status();
        }
    }
}
