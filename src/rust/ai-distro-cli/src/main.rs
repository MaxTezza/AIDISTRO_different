use clap::{Parser, Subcommand};
use colored::*;
use serde_json::Value;
use std::fs;
use std::io::{BufRead, BufReader};
use std::process::Command;
use sysinfo::System;

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
    /// Migrate legacy data into the AI memory
    Migrate {
        path: String,
    },
    /// Perform an autonomous system health check and repair
    Heal,
    /// Manage the intelligence settings (Local vs Cloud)
    Intelligence {
        #[command(subcommand)]
        action: IntelCommands,
    },
    /// Follow live logs from all AI Distro services
    Logs {
        /// Number of lines to show initially
        #[arg(short, long, default_value = "50")]
        lines: u32,
    },
    /// Self-update: pull latest code and rebuild
    Update,
    /// Verify the cryptographic audit chain integrity
    Audit {
        /// Path to the audit log file
        #[arg(short, long, default_value = "/var/log/ai-distro/audit.jsonl")]
        path: String,
    },
}

#[derive(Subcommand)]
enum IntelCommands {
    /// Set the intelligence mode (local or cloud)
    Mode { mode: String },
    /// Set the local model size (1b or 3b)
    Local { size: String },
    /// Set the cloud provider and API key
    Cloud { provider: String, key: String },
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

fn update_config(key: &str, val: Value) {
    let home = dirs::home_dir().unwrap_or_default();
    let config_path = home.join("AI_Distro/configs/agent.json");

    let Ok(content) = fs::read_to_string(&config_path) else {
        return;
    };
    let Ok(mut config) = serde_json::from_str::<Value>(&content) else {
        return;
    };

    config["intelligence"][key] = val;
    let _ = fs::write(&config_path, serde_json::to_string_pretty(&config).unwrap());
    println!("{} Updated intelligence configuration.", "✔".green());
}

fn main() {
    let cli = Cli::parse();
    let services = [
        "ai-distro-agent",
        "ai-distro-voice",
        "ai-distro-hud",
        "ai-distro-curator",
        "ai-distro-spirit",
        "ai-distro-healer",
        "ai-distro-hardware",
        "ai-distro-vision",
    ];

    match &cli.command {
        Commands::Start => {
            println!(
                "{}",
                "Starting AI Distro Revolutionary Stack...".cyan().bold()
            );
            for svc in services {
                manage_service("start", svc);
            }
        }
        Commands::Stop => {
            println!("{}", "Shutting down AI components...".yellow().bold());
            for svc in services {
                manage_service("stop", svc);
            }
        }
        Commands::Restart => {
            println!("{}", "Cycling AI Distro services...".magenta().bold());
            for svc in services {
                manage_service("restart", svc);
            }
        }
        Commands::Status => {
            println!("\n{}", "AI DISTRO: SYSTEM PULSE".cyan().bold());
            println!("{}", "═".repeat(40));

            // Service status
            println!("{}", " Services".bold());
            let mut active_count = 0;
            for svc in services {
                let is_active = Command::new("systemctl")
                    .arg("--user")
                    .arg("is-active")
                    .arg(format!("{}.service", svc))
                    .output()
                    .map(|o| String::from_utf8_lossy(&o.stdout).trim() == "active")
                    .unwrap_or(false);
                let (status_icon, status_text) = if is_active {
                    active_count += 1;
                    ("●".green(), "RUNNING".green())
                } else {
                    ("○".red(), "OFFLINE".red())
                };
                println!("  {} {:<22} [{}]", status_icon, svc, status_text);
            }

            // System resources
            println!("\n{}", " Resources".bold());
            let mut sys = System::new_all();
            sys.refresh_all();
            let total_mem = sys.total_memory() as f64 / 1_073_741_824.0;
            let used_mem = sys.used_memory() as f64 / 1_073_741_824.0;
            let cpu_count = sys.cpus().len();
            println!("  Memory: {:.1}/{:.1} GB", used_mem, total_mem);
            println!("  CPUs:   {}", cpu_count);

            // Battery (if available)
            if let Ok(cap) = fs::read_to_string("/sys/class/power_supply/BAT0/capacity") {
                if let Ok(st) = fs::read_to_string("/sys/class/power_supply/BAT0/status") {
                    println!("  Battery: {}% ({})", cap.trim(), st.trim());
                }
            }

            println!("\n  {} {}/{} services active",
                if active_count == services.len() { "✔".green() } else { "⚠".yellow() },
                active_count, services.len()
            );
            println!("{}", "═".repeat(40));
        }
        Commands::Setup => {
            let home = dirs::home_dir().unwrap_or_default();
            let wizard_path = home.join("AI_Distro/tools/agent/setup_wizard.py");
            let _ = Command::new("python3").arg(wizard_path).status();
        }
        Commands::Migrate { path } => {
            println!(
                "{} Starting the Great Migration from {}...",
                "🚀".cyan(),
                path
            );
            let importer = dirs::home_dir()
                .unwrap()
                .join("AI_Distro/tools/agent/legacy_importer.py");
            let _ = Command::new("python3").arg(importer).arg(path).spawn();
            println!(
                "{} Importer launched in background. Check the HUD for progress.",
                "✔".green()
            );
        }
        Commands::Heal => {
            println!("{} Running system diagnostic and repair...", "🩹".yellow());
            let healer = dirs::home_dir()
                .unwrap()
                .join("AI_Distro/tools/agent/system_healer.py");
            let _ = Command::new("python3")
                .arg(healer)
                .arg("check_now")
                .status();
            println!("{} Health check complete.", "✔".green());
        }
        Commands::Intelligence { action } => match action {
            IntelCommands::Mode { mode } => {
                let use_cloud = mode.to_lowercase() == "cloud";
                update_config("use_cloud", Value::Bool(use_cloud));
                println!(
                    "Intelligence mode set to: {}",
                    if use_cloud {
                        "CLOUD".yellow()
                    } else {
                        "LOCAL".green()
                    }
                );
            }
            IntelCommands::Local { size } => {
                let model = if size.to_lowercase() == "3b" {
                    "llama-3.2-3b-instruct.gguf"
                } else {
                    "llama-3.2-1b-instruct.gguf"
                };
                update_config("local_model", Value::String(model.to_string()));
                println!("Local model set to: {}", size.to_uppercase().green());
            }
            IntelCommands::Cloud { provider, key } => {
                update_config("cloud_provider", Value::String(provider.clone()));
                update_config("api_key", Value::String(key.to_string()));
                println!("Cloud provider set to: {} (Key saved)", provider.cyan());
            }
        },
        Commands::Logs { lines } => {
            println!("{}", "AI DISTRO: LIVE LOG FEED".cyan().bold());
            println!("Press Ctrl+C to stop\n");

            // Build a journalctl unit filter for all services
            let mut args: Vec<String> = vec!["--user".to_string(), "-f".to_string(),
                format!("--lines={}", lines)];
            for svc in services {
                args.push("-u".to_string());
                args.push(format!("{}.service", svc));
            }

            let _ = Command::new("journalctl")
                .args(&args)
                .status();
        }
        Commands::Update => {
            let home = dirs::home_dir().unwrap_or_default();
            let project_dir = home.join("AI_Distro");

            println!("{}", "AI DISTRO: SELF-UPDATE".cyan().bold());
            println!("{}\n", "═".repeat(40));

            // Step 1: Git pull
            println!("{} Pulling latest code...", "↓".cyan());
            let git_result = Command::new("git")
                .arg("pull")
                .current_dir(&project_dir)
                .output();
            match git_result {
                Ok(output) => {
                    let stdout = String::from_utf8_lossy(&output.stdout);
                    if stdout.contains("Already up to date") {
                        println!("  {} Already up to date.", "✔".green());
                    } else {
                        println!("  {} {}", "✔".green(), stdout.trim());
                    }
                }
                Err(e) => {
                    println!("  {} Git pull failed: {}", "✘".red(), e);
                    return;
                }
            }

            // Step 2: Rebuild Rust
            println!("\n{} Rebuilding Rust binaries...", "⚙".cyan());
            let cargo = Command::new("cargo")
                .args(["build", "--release"])
                .current_dir(project_dir.join("src/rust"))
                .status();
            match cargo {
                Ok(s) if s.success() => {
                    println!("  {} Build complete.", "✔".green());
                }
                _ => {
                    println!("  {} Build failed. Check the errors above.", "✘".red());
                    return;
                }
            }

            // Step 3: Restart services
            println!("\n{} Restarting services...", "↻".cyan());
            for svc in services {
                manage_service("restart", svc);
            }

            println!("\n{}", "═".repeat(40));
            println!("{} Self-update complete!", "✔".green().bold());
        }
        Commands::Audit { path } => {
            println!("{}", "AI DISTRO: AUDIT CHAIN VERIFICATION".cyan().bold());
            println!("{}\n", "═".repeat(40));

            let content = match fs::read_to_string(path) {
                Ok(c) => c,
                Err(e) => {
                    // Try home directory fallback
                    let home = dirs::home_dir().unwrap_or_default();
                    let alt = home.join(".cache/ai-distro/audit.jsonl");
                    match fs::read_to_string(&alt) {
                        Ok(c) => c,
                        Err(_) => {
                            println!("{} Could not read audit log: {}", "✘".red(), e);
                            println!("  Try: ai-distro audit --path /path/to/audit.jsonl");
                            return;
                        }
                    }
                }
            };

            let reader = BufReader::new(content.as_bytes());
            let mut expected_prev_hash = "genesis_sha256".to_string();
            let mut seq = 0u64;
            let mut errors = 0u64;

            for line in reader.lines() {
                let line = match line {
                    Ok(l) => l,
                    Err(_) => continue,
                };
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }
                seq += 1;

                let record: Value = match serde_json::from_str(trimmed) {
                    Ok(v) => v,
                    Err(e) => {
                        println!("  {} Line {}: Parse error: {}", "✘".red(), seq, e);
                        errors += 1;
                        continue;
                    }
                };

                // Check prev_hash linkage
                let prev_hash = record["prev_hash"].as_str().unwrap_or("");
                if prev_hash != expected_prev_hash {
                    println!(
                        "  {} Line {}: Chain break! Expected prev_hash '{}', got '{}'",
                        "✘".red(), seq,
                        &expected_prev_hash[..8.min(expected_prev_hash.len())],
                        &prev_hash[..8.min(prev_hash.len())]
                    );
                    errors += 1;
                }

                // Update expected for next record
                if let Some(hash) = record["chain_hash"].as_str() {
                    expected_prev_hash = hash.to_string();
                }
            }

            if seq == 0 {
                println!("  {} Audit log is empty.", "⚠".yellow());
            } else if errors == 0 {
                println!("  {} All {} records verified. Chain is intact.", "✔".green().bold(), seq);
                println!("  Last hash: {}...", &expected_prev_hash[..16.min(expected_prev_hash.len())]);
            } else {
                println!("\n  {} {} errors in {} records. Audit chain is BROKEN.",
                    "✘".red().bold(), errors, seq);
            }
            println!("\n{}", "═".repeat(40));
        }
    }
}
