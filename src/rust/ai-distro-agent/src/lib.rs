pub mod audit;
pub mod events;
pub mod handlers;
pub mod ipc;
pub mod policy;
pub mod utils;

use crate::utils::error_response;
use ai_distro_common::{ActionRequest, ActionResponse, Capabilities, PolicyConfig, PolicyDecision};
use std::collections::{HashMap, VecDeque};
use std::sync::{Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};

pub type Handler = fn(&ActionRequest) -> ActionResponse;
const MAX_PENDING_CONFIRMATIONS: usize = 128;

#[derive(Default)]
struct ConfirmationQueue {
    by_id: HashMap<String, ActionRequest>,
    order: VecDeque<String>,
}

static CONFIRMATION_QUEUE: OnceLock<Mutex<ConfirmationQueue>> = OnceLock::new();

pub fn load_skills(dir: &str) -> HashMap<String, ai_distro_common::SkillManifest> {
    let mut skills = HashMap::new();
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("json") {
                if let Ok(content) = std::fs::read_to_string(&path) {
                    if let Ok(manifest) =
                        serde_json::from_str::<ai_distro_common::SkillManifest>(&content)
                    {
                        skills.insert(manifest.name.clone(), manifest);
                    }
                }
            }
        }
    }
    skills
}

pub fn action_registry() -> HashMap<&'static str, Handler> {
    let mut map: HashMap<&'static str, Handler> = HashMap::new();

    // Package management
    map.insert(
        "package_install",
        handlers::package::handle_package_install as Handler,
    );
    map.insert(
        "package_remove",
        handlers::package::handle_package_remove as Handler,
    );

    // System management
    map.insert(
        "system_update",
        handlers::system::handle_system_update as Handler,
    );
    map.insert(
        "self_update",
        handlers::system::handle_self_update as Handler,
    );
    map.insert(
        "import_legacy_data",
        handlers::system::handle_import_legacy_data as Handler,
    );
    map.insert(
        "system_heal",
        handlers::system::handle_system_heal as Handler,
    );

    // Media controls
    map.insert("set_volume", handlers::media::handle_set_volume as Handler);
    map.insert(
        "set_brightness",
        handlers::media::handle_set_brightness as Handler,
    );

    // Network controls
    map.insert(
        "network_wifi_on",
        handlers::network::handle_wifi_on as Handler,
    );
    map.insert(
        "network_wifi_off",
        handlers::network::handle_wifi_off as Handler,
    );
    map.insert(
        "network_bluetooth_on",
        handlers::network::handle_bluetooth_on as Handler,
    );
    map.insert(
        "network_bluetooth_off",
        handlers::network::handle_bluetooth_off as Handler,
    );

    // Hardware control
    map.insert("wifi_scan", handlers::hardware::handle_wifi_scan as Handler);
    map.insert(
        "wifi_connect",
        handlers::hardware::handle_wifi_connect as Handler,
    );
    map.insert(
        "bluetooth_scan",
        handlers::hardware::handle_bluetooth_scan as Handler,
    );
    map.insert(
        "bluetooth_pair",
        handlers::hardware::handle_bluetooth_pair as Handler,
    );

    // Universal App Store
    map.insert(
        "store_search",
        handlers::store::handle_store_search as Handler,
    );
    map.insert(
        "store_install",
        handlers::store::handle_store_install as Handler,
    );

    // Power management
    map.insert(
        "power_reboot",
        handlers::power::handle_power_reboot as Handler,
    );
    map.insert(
        "power_shutdown",
        handlers::power::handle_power_shutdown as Handler,
    );
    map.insert(
        "power_sleep",
        handlers::power::handle_power_sleep as Handler,
    );

    // Memory and context
    map.insert("remember", handlers::memory::handle_remember as Handler);
    map.insert(
        "read_context",
        handlers::memory::handle_read_context as Handler,
    );

    // UI and filesystem
    map.insert("open_url", handlers::ui::handle_open_url as Handler);
    map.insert("open_app", handlers::ui::handle_open_app as Handler);
    map.insert("list_files", handlers::ui::handle_list_files as Handler);
    map.insert(
        "screen_context",
        handlers::ui::handle_screen_context as Handler,
    );
    map.insert(
        "launch_app_semantic",
        handlers::ui::handle_launch_app_semantic as Handler,
    );

    // External tools (Python-based)
    map.insert(
        "weather_get",
        handlers::tools::handle_weather_get as Handler,
    );
    map.insert(
        "calendar_add_event",
        handlers::tools::handle_calendar_add_event as Handler,
    );
    map.insert(
        "calendar_list_day",
        handlers::tools::handle_calendar_list_day as Handler,
    );
    map.insert(
        "email_inbox_summary",
        handlers::tools::handle_email_inbox_summary as Handler,
    );
    map.insert(
        "email_search",
        handlers::tools::handle_email_search as Handler,
    );
    map.insert(
        "email_draft",
        handlers::tools::handle_email_draft as Handler,
    );
    map.insert(
        "plan_day_outfit",
        handlers::tools::handle_plan_day_outfit as Handler,
    );

    // Grandma Skills
    map.insert(
        "player_control",
        handlers::tools::handle_player_control as Handler,
    );
    map.insert(
        "gallery_show",
        handlers::tools::handle_gallery_show as Handler,
    );
    map.insert(
        "news_headlines",
        handlers::tools::handle_news_headlines as Handler,
    );
    map.insert(
        "family_message",
        handlers::tools::handle_family_message as Handler,
    );

    // Privacy dashboard
    map.insert(
        "privacy_status",
        handlers::privacy::handle_privacy_status as Handler,
    );
    map.insert(
        "privacy_log",
        handlers::privacy::handle_privacy_log as Handler,
    );
    map.insert(
        "privacy_check_active",
        handlers::privacy::handle_privacy_check_active as Handler,
    );

    // Workspace management
    map.insert(
        "workspace_save",
        handlers::workspace::handle_workspace_save as Handler,
    );
    map.insert(
        "workspace_restore",
        handlers::workspace::handle_workspace_restore as Handler,
    );
    map.insert(
        "workspace_list",
        handlers::workspace::handle_workspace_list as Handler,
    );
    map.insert(
        "workspace_switch",
        handlers::workspace::handle_workspace_switch as Handler,
    );
    map.insert(
        "workspace_arrange",
        handlers::workspace::handle_workspace_arrange as Handler,
    );
    map.insert(
        "window_move",
        handlers::workspace::handle_window_move as Handler,
    );
    map.insert(
        "window_maximize",
        handlers::workspace::handle_window_maximize as Handler,
    );

    // UI Hands (AT-SPI Semantic Automation + xdotool fallback)
    map.insert("ui_click", handlers::hands::handle_ui_click as Handler);
    map.insert("ui_type", handlers::hands::handle_ui_type as Handler);
    map.insert(
        "ui_shortcut",
        handlers::hands::handle_ui_shortcut as Handler,
    );
    map.insert("ui_read", handlers::hands::handle_ui_read as Handler);
    map.insert("ui_list", handlers::hands::handle_ui_list as Handler);

    // Display and theme management
    map.insert(
        "set_dark_mode",
        handlers::display::handle_set_dark_mode as Handler,
    );
    map.insert(
        "set_light_mode",
        handlers::display::handle_set_light_mode as Handler,
    );
    map.insert(
        "toggle_theme",
        handlers::display::handle_toggle_theme as Handler,
    );
    map.insert(
        "set_theme_schedule",
        handlers::display::handle_set_theme_schedule as Handler,
    );
    map.insert(
        "get_theme_status",
        handlers::display::handle_get_theme_status as Handler,
    );
    map.insert(
        "set_night_light",
        handlers::display::handle_set_night_light as Handler,
    );
    map.insert(
        "apply_scheduled_theme",
        handlers::display::handle_apply_scheduled_theme as Handler,
    );

    // Skill management
    map.insert(
        "skill_install",
        handlers::skill::handle_skill_install as Handler,
    );
    map.insert("skill_list", handlers::skill::handle_skill_list as Handler);

    // Core built-ins
    map.insert("ping", handle_ping as Handler);
    map.insert("get_capabilities", handle_get_capabilities as Handler);
    map.insert(
        "proactive_suggestion",
        handle_proactive_suggestion as Handler,
    );
    map.insert("set_preference", handle_set_preference as Handler);

    // Identity and Email
    map.insert(
        "get_autonomous_address",
        handlers::tools::handle_get_autonomous_address as Handler,
    );
    map.insert(
        "poll_autonomous_mail",
        handlers::tools::handle_poll_autonomous_mail as Handler,
    );
    map.insert("web_task", handlers::tools::handle_web_task as Handler);

    // Software Forge (code generation & project scaffolding)
    map.insert(
        "software_forge_script",
        handlers::forge::handle_forge_script as Handler,
    );
    map.insert(
        "software_forge_project",
        handlers::forge::handle_forge_project as Handler,
    );
    map.insert(
        "software_forge_execute",
        handlers::forge::handle_forge_execute as Handler,
    );
    map.insert(
        "software_forge_generate",
        handlers::forge::handle_forge_generate as Handler,
    );

    // Hardware awareness
    map.insert(
        "battery_status",
        handlers::hardware::handle_battery_status as Handler,
    );
    map.insert("hw_info", handlers::hardware::handle_hw_info as Handler);

    map
}

pub fn handle_proactive_suggestion(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("{}");
    // Parse the payload to extract the message
    let msg = if let Ok(val) = serde_json::from_str::<serde_json::Value>(payload) {
        val["message"]
            .as_str()
            .unwrap_or("Insight detected")
            .to_string()
    } else {
        "Insight detected".to_string()
    };

    ActionResponse {
        version: 1,
        action: req.name.clone(),
        status: "ok".to_string(),
        message: Some(msg),
        capabilities: None,
        confirmation_id: None,
    }
}

pub fn handle_set_preference(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("{}");
    let (key, value) = if let Ok(val) = serde_json::from_str::<serde_json::Value>(payload) {
        (
            val["key"].as_str().unwrap_or("").to_string(),
            val["value"].as_str().unwrap_or("").to_string(),
        )
    } else {
        return error_response(
            &req.name,
            "Invalid preference payload. Use {\"key\": \"...\", \"value\": \"...\"}",
        );
    };

    if key.is_empty() || value.is_empty() {
        return error_response(&req.name, "Both key and value are required.");
    }

    let bayesian_path = std::env::var("AI_DISTRO_BAYESIAN_ENGINE").unwrap_or_else(|_| {
        let repo_root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
        repo_root
            .join("tools/agent/bayesian_engine.py")
            .to_string_lossy()
            .to_string()
    });

    match std::process::Command::new("python3")
        .arg(&bayesian_path)
        .arg("set_preference")
        .arg(&key)
        .arg(&value)
        .output()
    {
        Ok(out) if out.status.success() => ActionResponse {
            version: 1,
            action: req.name.clone(),
            status: "ok".to_string(),
            message: Some(format!(
                "Got it! I've set your preference: {} = {}. I'll remember this.",
                key, value
            )),
            capabilities: None,
            confirmation_id: None,
        },
        _ => error_response(&req.name, "Failed to save preference."),
    }
}

pub fn handle_ping(req: &ActionRequest) -> ActionResponse {
    ActionResponse {
        version: 1,
        action: req.name.clone(),
        status: "ok".to_string(),
        message: Some("pong".to_string()),
        capabilities: None,
        confirmation_id: None,
    }
}

pub fn handle_get_capabilities(req: &ActionRequest) -> ActionResponse {
    ActionResponse {
        version: 1,
        action: req.name.clone(),
        status: "ok".to_string(),
        message: None,
        capabilities: Some(Capabilities {
            ipc_version: 1,
            actions: action_registry().keys().map(|s| s.to_string()).collect(),
            protocol_version: 1,
        }),
        confirmation_id: None,
    }
}

pub fn handle_request(
    policy: &PolicyConfig,
    registry: &HashMap<&'static str, Handler>,
    request: ActionRequest,
) -> ActionResponse {
    let response = handle_request_inner(policy, registry, request.clone());

    // Cryptographic Audit Log
    let audit_log = std::env::var("AI_DISTRO_AUDIT_LOG")
        .unwrap_or_else(|_| "/var/log/ai-distro/audit.json".to_string());
    let audit_state = std::env::var("AI_DISTRO_AUDIT_STATE")
        .unwrap_or_else(|_| "/var/lib/ai-distro/audit_state.json".to_string());

    let mut state = audit::load_audit_chain_state(&audit_state);
    let event = serde_json::json!({
        "ts": audit::now_epoch_secs(),
        "action": request.name,
        "status": response.status,
        "payload": request.payload
    });
    let _ = audit::append_audit_record(&audit_log, &mut state, event);
    audit::persist_audit_chain_state(&audit_state, &state);

    // Multimodal Orchestration Loop (Recursive Reasoning)
    // If the last action was 'internal' (like seeing the screen) and we have a message,
    // feed it back to the brain to see if it wants to take a NEXT step.
    if response.status == "ok"
        && (request.name == "screen_context"
            || request.name == "read_context"
            || request.name == "get_autonomous_address")
    {
        if let Some(result_text) = &response.message {
            log::info!(
                "Orchestrator: Feeding result of '{}' back to brain...",
                request.name
            );
            let next_request = ActionRequest {
                version: Some(1),
                name: "natural_language".to_string(),
                payload: Some(format!("The result of the last action '{}' was: {}. Now proceed to the next step of the original goal.", request.name, result_text)),
            };
            return handle_request(policy, registry, next_request);
        }
    }

    // Bayesian Preference Learning
    {
        let outcome = if response.status == "ok" {
            "positive"
        } else {
            "negative"
        };
        let bayesian_path = std::env::var("AI_DISTRO_BAYESIAN_ENGINE").unwrap_or_else(|_| {
            let repo_root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
            repo_root
                .join("tools/agent/bayesian_engine.py")
                .to_string_lossy()
                .to_string()
        });
        let _ = std::process::Command::new("python3")
            .arg(&bayesian_path)
            .arg("observe")
            .arg(&request.name)
            .arg(outcome)
            .spawn();
    }

    response
}

fn new_confirmation_id(request_name: &str) -> String {
    let millis = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0);
    format!("confirm-{request_name}-{millis}")
}

fn queue_lock() -> &'static Mutex<ConfirmationQueue> {
    CONFIRMATION_QUEUE.get_or_init(|| Mutex::new(ConfirmationQueue::default()))
}

fn enqueue_confirmation(id: String, request: ActionRequest) {
    if let Ok(mut queue) = queue_lock().lock() {
        queue.by_id.insert(id.clone(), request);
        queue.order.push_back(id);
        while queue.by_id.len() > MAX_PENDING_CONFIRMATIONS {
            if let Some(oldest) = queue.order.pop_front() {
                queue.by_id.remove(&oldest);
            } else {
                break;
            }
        }
    }
}

fn dequeue_confirmation(id: &str) -> Option<ActionRequest> {
    let mut queue = queue_lock().lock().ok()?;
    let out = queue.by_id.remove(id);
    if out.is_some() {
        queue.order.retain(|item| item != id);
    }
    out
}

fn dispatch_action(
    registry: &HashMap<&'static str, Handler>,
    request: &ActionRequest,
) -> ActionResponse {
    if let Some(handler) = registry.get(request.name.as_str()) {
        handler(request)
    } else {
        error_response(&request.name, "no handler registered")
    }
}

fn handle_request_inner(
    policy: &PolicyConfig,
    registry: &HashMap<&'static str, Handler>,
    request: ActionRequest,
) -> ActionResponse {
    // 0. Handle natural language parsing
    if request.name == "natural_language" {
        if let Some(text) = request.payload.as_deref() {
            // Try LLM Brain first
            let brain_path = std::env::var("AI_DISTRO_BRAIN")
                .unwrap_or_else(|_| "tools/agent/brain.py".to_string());

            let mut parsed_req: Option<ActionRequest> = None;

            if let Ok(output) = std::process::Command::new("python3")
                .arg(&brain_path)
                .arg(text)
                .output()
            {
                if output.status.success() {
                    parsed_req = serde_json::from_slice(&output.stdout).ok();
                }
            }

            // Fallback to Regex Parser
            if parsed_req.is_none() {
                let parser_path = std::env::var("AI_DISTRO_INTENT_PARSER")
                    .unwrap_or_else(|_| "tools/agent/intent_parser.py".to_string());
                if let Ok(output) = std::process::Command::new("python3")
                    .arg(&parser_path)
                    .arg(text)
                    .output()
                {
                    if output.status.success() {
                        parsed_req = serde_json::from_slice(&output.stdout).ok();
                    }
                }
            }

            if let Some(new_req) = parsed_req {
                return handle_request(policy, registry, new_req);
            }
        }

        return ActionResponse {
            version: 1,
            action: "natural_language".to_string(),
            status: "error".to_string(),
            message: Some(
                "I couldn't understand that. Try a direct command like: open firefox, set volume to 40 percent, or what can you do."
                    .to_string(),
            ),
            capabilities: None,
            confirmation_id: None,
        };
    }

    if request.name == "confirm" {
        let confirmation_id = request
            .payload
            .clone()
            .unwrap_or_default()
            .trim()
            .to_string();
        if confirmation_id.is_empty() {
            return ActionResponse {
                version: 1,
                action: "confirm".to_string(),
                status: "error".to_string(),
                message: Some("missing confirmation id".to_string()),
                capabilities: None,
                confirmation_id: None,
            };
        }

        let Some(confirmed_request) = dequeue_confirmation(&confirmation_id) else {
            return ActionResponse {
                version: 1,
                action: "confirm".to_string(),
                status: "error".to_string(),
                message: Some("confirmation request expired or was not found".to_string()),
                capabilities: None,
                confirmation_id: None,
            };
        };

        if let Err(detail) = policy::enforce_action_allowlists(policy, &confirmed_request) {
            return ActionResponse {
                version: 1,
                action: confirmed_request.name.clone(),
                status: "deny".to_string(),
                message: Some(detail),
                capabilities: None,
                confirmation_id: None,
            };
        }
        if let Err(detail) = policy::enforce_rate_limit(policy, &confirmed_request) {
            return ActionResponse {
                version: 1,
                action: confirmed_request.name.clone(),
                status: "deny".to_string(),
                message: Some(detail),
                capabilities: None,
                confirmation_id: None,
            };
        }

        if let PolicyDecision::Deny = ai_distro_common::evaluate_policy_with_payload(
            policy,
            &confirmed_request.name,
            confirmed_request.payload.as_deref(),
        ) {
            return ActionResponse {
                version: 1,
                action: confirmed_request.name.clone(),
                status: "deny".to_string(),
                message: Some("action denied by policy".to_string()),
                capabilities: None,
                confirmation_id: None,
            };
        }

        return dispatch_action(registry, &confirmed_request);
    }

    // 1. Enforce allowlists
    if let Err(detail) = policy::enforce_action_allowlists(policy, &request) {
        return ActionResponse {
            version: 1,
            action: request.name.clone(),
            status: "deny".to_string(),
            message: Some(detail),
            capabilities: None,
            confirmation_id: None,
        };
    }

    // 2. Enforce rate limits
    if let Err(detail) = policy::enforce_rate_limit(policy, &request) {
        return ActionResponse {
            version: 1,
            action: request.name.clone(),
            status: "deny".to_string(),
            message: Some(detail),
            capabilities: None,
            confirmation_id: None,
        };
    }

    // 3. Enforce general policy (Allow/Deny/Confirm)
    match ai_distro_common::evaluate_policy_with_payload(
        policy,
        &request.name,
        request.payload.as_deref(),
    ) {
        PolicyDecision::Allow => dispatch_action(registry, &request),
        PolicyDecision::RequireConfirmation => {
            let confirmation_id = new_confirmation_id(&request.name);
            enqueue_confirmation(confirmation_id.clone(), request.clone());
            ActionResponse {
                version: 1,
                action: request.name.clone(),
                status: "confirm".to_string(),
                message: Some("user confirmation required".to_string()),
                capabilities: None,
                confirmation_id: Some(confirmation_id),
            }
        }
        PolicyDecision::Deny => ActionResponse {
            version: 1,
            action: request.name.clone(),
            status: "deny".to_string(),
            message: Some("action denied by policy".to_string()),
            capabilities: None,
            confirmation_id: None,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ai_distro_common::{ActionRequest, PolicyConfig};

    fn confirmation_policy_for_ping() -> PolicyConfig {
        let mut policy = PolicyConfig::default();
        policy.constraints.require_confirmation_for = vec!["ping".to_string()];
        policy
    }

    #[test]
    fn confirm_executes_queued_action_once() {
        let policy = confirmation_policy_for_ping();
        let registry = action_registry();

        let first = handle_request(
            &policy,
            &registry,
            ActionRequest {
                version: Some(1),
                name: "ping".to_string(),
                payload: None,
            },
        );
        assert_eq!(first.status, "confirm");
        let id = first.confirmation_id.expect("expected confirmation id");

        let confirmed = handle_request(
            &policy,
            &registry,
            ActionRequest {
                version: Some(1),
                name: "confirm".to_string(),
                payload: Some(id.clone()),
            },
        );
        assert_eq!(confirmed.action, "ping");
        assert_eq!(confirmed.status, "ok");

        let replay = handle_request(
            &policy,
            &registry,
            ActionRequest {
                version: Some(1),
                name: "confirm".to_string(),
                payload: Some(id),
            },
        );
        assert_eq!(replay.action, "confirm");
        assert_eq!(replay.status, "error");
    }

    #[test]
    fn confirm_requires_id() {
        let policy = confirmation_policy_for_ping();
        let registry = action_registry();

        let response = handle_request(
            &policy,
            &registry,
            ActionRequest {
                version: Some(1),
                name: "confirm".to_string(),
                payload: None,
            },
        );
        assert_eq!(response.action, "confirm");
        assert_eq!(response.status, "error");
    }
}
