## Plugin Manifest (Skill) Specification

### Goal
AI Distro exposes a plugin/skill directory so new actions can be added without touching the Rust core. A manifest is a small JSON file that declares:

- **What** the plugin does (`name`, `display_name`, `description`, `category`).
- **How** it is executed (`handler` section with either a built‑in Rust handler or a Python tool path).
- **When** it is safe to run (`parameters`, `examples`, `safety`, `tags`).

Plugins live in the directory controlled by `AI_DISTRO_SKILLS_DIR` (default `src/skills/core`). Both the Python brain (`tools/agent/brain.py`) and the agent loader (`ai_distro_agent::load_skills`) read every `*.json` file in that directory, so dropping a manifest there instantly registers it.

### Required fields

| Field | Description |
|---|---|
| `name` | Machine-readable identifier (used as the IPC action name). |
| `display_name` | Human-friendly label surfaced in the shell plugin catalog. |
| `description` | Short explanation of what the plugin does. |
| `category` | Logical group for the catalog (e.g., `system`, `utility`, `communications`, `dev`). |
| `handler` | Object describing where to route the request. See below. |
| `examples` | Array of sample user utterances (voice or shell) so the brain can map language. |

### Optional fields

- `parameters` – JSON Schema fragment describing the expected payload (type, required keys, enums, default values). The Python brain surface this schema in prompts so the LLM can emit valid requests.
- `safety` – Optional object with flags such as `requires_confirmation` (bool), `deny_list` (array of strings) and `rate_limit` that the agent policy layer can honor without hardcoding.  
- `tags` – Array of keywords to surface plugin variants in the shell search/filter UI.
- `dependencies` – List of other plugin `name`s that must be active first (useful for provider-specific tooling).
- `version` – Optional manifest version; increments when the plugin contract changes.
- `trigger` – For event-driven plugins you can declare `trigger` metadata referencing `nervous_system` signals (battery, network, calendar) so the shell knows when to show a proactive tile.

### Handler object

```json
"handler": {
  "type": "rust_builtin",
  "name": "power_management"
}
```

The `type` can be:

- `rust_builtin`: The `name` must match a handler registered inside the Rust agent (`ai_distro_agent::handlers`). These are fast, safe entrypoints for system actions (packages, power, SSH, policies).
- `python`: `path` points at a Python script (typically in `tools/agent/`). The script is responsible for parsing `payload` and returning JSON that matches `ActionResponse`. It can also invoke external services (weather APIs, calendar providers, etc.).

Custom handler types can be introduced if the agent expands (for example, a `script` type that runs `bash` with sandboxing). Each new type should be documented alongside this manifest file.

### Example

```json
{
  "name": "power_management",
  "display_name": "Power Control",
  "description": "Reboot, shutdown, or sleep the desktop.",
  "category": "system",
  "handler": {
    "type": "rust_builtin",
    "name": "power_management"
  },
  "parameters": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["reboot", "shutdown", "sleep"]
      }
    },
    "required": ["action"]
  },
  "safety": {
    "requires_confirmation": true
  },
  "examples": [
    "Restart my computer",
    "Shut down the PC",
    "Put the desktop to sleep"
  ]
}
```

The brain reads `examples` when building system prompts, so keeping them natural-language and varied improves intent coverage for average users and developers alike.

### Plugin lifecycle

1. Drop the manifest JSON into `AI_DISTRO_SKILLS_DIR`. The loader crawls it at runtime and merges it into `ai_distro_agent::load_skills`.
2. If the handler is `python`, ensure the script path resolves inside the ISO root (`tools/agent/...`). Use wrappers when necessary to set environment variables (assets, providers, model path).  
3. Restart the agent (`ai-distro-agent`) or reload the skill cache to register the new action.
4. Add any UI metadata (icons, cards) referencing the manifest's `category` and `tags`. The shell can highlight newly installed plugins in the “Plugin Catalog” view.

Developers can extend the catalog in `docs/VOICE_UX.md`, `docs/DESKTOP_UI.md`, or `assets/ui/shell` by reusing the manifest metadata for listing, filtering, and safety messaging. Keep this file up to date whenever new plugin schema features are added so community contributors have a clear place to reference.  

### Lifecycle & toggles
Plugins are enabled by default unless a user explicitly disables them via the shell catalog. The shell calls `/api/plugins/enable` and `/api/plugins/disable` to persist an opt-in flag under `AI_DISTRO_PLUGIN_STATE` (default `~/.config/ai-distro/plugins.json`). Keep this experience friendly by using the catalog buttons rather than asking users for API keys or configuration files—most plugins should “just work” out of the box once their manifest is dropped in place.

### Safety hints
Expose `safety.requires_confirmation`, `safety.deny_list`, and `safety.rate_limit` when available so the shell UI can show friendly reminders and warning tags before a user triggers the plugin. The catalog renders this copy automatically, so you don’t need to duplicate the logic elsewhere.
