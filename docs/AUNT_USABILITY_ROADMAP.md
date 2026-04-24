# AI Distro: The "Aunt Usability" Roadmap

> **Goal:** Bridge the canyon between developer power-tool and universal accessibility.

## Executive Summary

The current system is architecturally brilliant (Rust IPC/security + Python intelligence + Web Shell). However, it requires terminal commands to install, terminal scripts for OAuth, and assumes users understand `make`, `cargo`, and Docker sockets.

**Target User Persona Shift:**
- Current: Linux developer who reads source code
- Target: Someone who "can barely check their email"

---

## Priority 0: Pre-Baked ISO (CRITICAL)

**Problem:** Quickstart requires `make rootfs`, `make iso-assemble`, `cargo build`. Aunt cannot do this.

**Solution:** Provide pre-built downloadable ISO.

### Implementation
1. CI/CD pipeline builds ISO on every release tag
2. Upload to GitHub Releases / GitLab Package Registry
3. Add prominent download link at **TOP** of README:

```markdown
## Download

> **[Download MnemonicOS-1.0.0-x86_64.iso](https://releases.ai-distro.org/MnemonicOS-1.0.0-x86_64.iso)**

Flash to USB with [BalenaEtcher](https://etcher.balena.io/) and boot.
```

4. Move `make` commands to `CONTRIBUTING.md`

### Files to Create
- `.gitlab-ci.yml` - Add ISO build + release job
- `scripts/release/publish_iso.sh` - Upload script
- Update `README.md` - Move download to top

---

## Priority 1: OAuth in Web Shell (CRITICAL)

**Problem:** Users must run 3+ Python scripts in terminal to authenticate Google/Microsoft.

**Solution:** OAuth flow happens entirely in browser.

### Architecture

```
User says: "Check my calendar"
     ↓
Web Shell detects no calendar token
     ↓
Web Shell shows modal: "Connect Google Calendar"
     ↓
User clicks → Opens OAuth popup (localhost redirect)
     ↓
Google redirects to localhost:17842/oauth/callback
     ↓
Web Shell exchanges code for token (server-side)
     ↓
Token stored in ~/.config/ai-distro/
     ↓
Calendar request proceeds
```

### Implementation
1. Add OAuth endpoints to `ai_distro_shell.py`:
   - `GET /oauth/{provider}/start` → Redirect to OAuth provider
   - `GET /oauth/{provider}/callback` → Exchange code for token
   - `GET /oauth/{provider}/status` → Check if connected

2. Add OAuth UI components to shell:
   - Connection status indicator
   - "Connect" button that triggers flow
   - Connection success/error toasts

3. Update providers:
   - `google_calendar`: Check for token before use
   - `google_gmail`: Same pattern
   - `microsoft_outlook`: Same pattern

### Files to Modify/Create
- `tools/shell/ai_distro_shell.py` - Add OAuth routes
- `tools/shell/static/oauth-modal.js` - UI component
- `tools/agent/calendar_google_tool.py` - Token check
- `tools/agent/gmail_tool.py` - Token check

---

## Priority 2: Tiered Brain System (HIGH)

**Problem:** Llama 3.2 1B fails on complex multi-intent requests.

**Example failure:**
> "Search my email for the invoice from the plumber last month and draft a reply telling him I'll pay Friday"

1B model cannot extract: (1) Search email, (2) Filter by date, (3) Draft email.

### Solution: Two-Tier Model Routing

```
┌─────────────────────────────────────┐
│  Tier 1: Reflex (Llama 3.2 1B)      │
│  - mute volume, dark mode, lock      │
│  - single-intent instant actions     │
│  - < 100ms latency                   │
└─────────────────────────────────────┘
              ↓ complex intent?
┌─────────────────────────────────────┐
│  Tier 2: Reasoning (Qwen 2.5 3B)    │
│  - email search + compose           │
│  - calendar operations              │
│  - web search + synthesis           │
│  - 300-800ms latency                │
└─────────────────────────────────────┘
```

### Routing Logic

```python
COMPLEX_INTENT_KEYWORDS = [
    "email", "calendar", "search", "find", "draft",
    "reply", "compose", "schedule", "remind"
]

def route_intent(user_input: str) -> str:
    """Returns 'reflex' or 'reasoning'."""
    text = user_input.lower()
    
    # Count distinct action verbs
    action_count = sum(1 for kw in COMPLEX_INTENT_KEYWORDS if kw in text)
    
    if action_count >= 2:
        return "reasoning"
    
    # Check for conjunctions (and, then, also)
    if any(c in text for c in [" and ", " then ", " also "]):
        return "reasoning"
    
    return "reflex"
```

### Implementation
1. Download Qwen 2.5 3B Instruct on first run (if > 8GB RAM)
2. Add `brain_router.py` to route between models
3. Update `brain.py` to support multiple backends
4. Add config: `AI_DISTRO_TIER2_MODEL` (default: qwen-2.5-3b)

### Files to Create/Modify
- `tools/agent/brain_router.py` - Routing logic
- `tools/agent/brain.py` - Multi-model support
- `tools/agent/download_model.py` - Add Qwen download

---

## Priority 3: Web Search Tool (HIGH)

**Problem:** "How many ounces in a cup?" → No answer.

### Solution: Add `web_search` action

```rust
// In handlers/tools.rs
pub async fn web_search(query: &str) -> Result<WebSearchResult> {
    // 1. Search DuckDuckGo (no API key needed)
    // 2. Scrape top 3 results with readability
    // 3. Summarize with LLM
    // 4. Return synthesized answer
}
```

### Implementation Details
1. Use `duckduckgo-search` crate (no API key)
2. Use `trafilatura` or `readability` for content extraction
3. Feed extracted text to LLM for synthesis
4. Log all web access in audit log

### Security
- Domain allowlist in `policy.json`
- Rate limit: 10 searches / minute
- Audit log entry for each search

### Files to Create/Modify
- `src/rust/ai-distro-agent/src/handlers/web.rs` - New handler
- `tools/agent/web_search_tool.py` - Python fallback
- `configs/policy.json` - Add web search rules

---

## Priority 4: Visual Audit Viewer (MEDIUM)

**Problem:** Cryptographic audit log exists but is invisible to users.

**Solution:** Web UI showing hash chain timeline.

### UI Mockup

```
┌──────────────────────────────────────────────────┐
│  🔐 Audit Trail                                   │
├──────────────────────────────────────────────────┤
│  09:02:14 │ Wake word detected                   │
│           │ Hash: 3f7a8b...                      │
│           │ Prev: a1c2d3...  ✓ Valid            │
├──────────────────────────────────────────────────┤
│  09:02:15 │ Intent: plan_day_outfit             │
│           │ Payload: "today"                     │
│           │ Hash: 7e4f9a...                      │
│           │ Prev: 3f7a8b...  ✓ Valid            │
├──────────────────────────────────────────────────┤
│  09:02:16 │ Policy check: ALLOWED                │
│           │ Hash: 2b8c1d...                      │
│           │ Prev: 7e4f9a...  ✓ Valid            │
└──────────────────────────────────────────────────┘
```

### Implementation
1. Add `GET /api/audit` endpoint to shell
2. Parse JSONL audit log, verify hash chain
3. Render as filterable timeline
4. Add "Export Audit" button (PDF/JSON)

### Files to Create/Modify
- `tools/shell/ai_distro_shell.py` - Audit API
- `tools/shell/static/audit-viewer.js` - UI
- `tools/shell/templates/audit.html` - Page

---

## Priority 5: First-Boot Wizard (MEDIUM)

**Problem:** ISO boots to Linux desktop, not voice assistant.

**Solution:** Auto-launch Web Shell in kiosk mode on first boot.

### Implementation
1. Build ISO with auto-login user
2. systemd service launches `ai-distro-shell` in kiosk mode
3. `~/.config/autostart/ai-distro.desktop` launches browser in kiosk mode
4. First-boot shows:
   - "Welcome! Let's set up your assistant"
   - Voice test: "Say 'Hello' to test your microphone"
   - Wake word calibration
   - Connect accounts (OAuth buttons)

### Files to Create/Modify
- `configs/ai-distro-kiosk.service` - systemd service
- `scripts/build/disable_desktop.sh` - Hide desktop
- `tools/shell/templates/onboarding.html` - Wizard

---

## Priority 6: Proactive Visual Alerts (MEDIUM)

**Problem:** Voice-only alerts are annoying.

**Solution:** Visual banners for proactive notifications.

### UI Pattern

```
┌──────────────────────────────────────────────────┐
│  ⚠️ Battery at 10%                               │
│  Would you like me to enable power saver?        │
│  [Yes] [No] [Dismiss]                            │
└──────────────────────────────────────────────────┘
```

### Implementation
1. SSE stream for proactive events: `/api/events`
2. Web Shell subscribes to event stream
3. Render banner for proactive messages
4. Banner includes action buttons

### Files to Modify
- `tools/shell/ai_distro_shell.py` - SSE endpoint
- `tools/shell/static/banner.js` - UI component

---

## Priority 7: Undo Button (LOW but builds trust)

**Problem:** "Close Firefox" by accident → No way back.

**Solution:** Last action undo.

### Implementation
1. Store last N actions in memory
2. Each action implements `undo()` method
3. UI button: "Undo: Close Firefox"
4. Keyboard shortcut: Ctrl+Z

### Files to Create/Modify
- `src/rust/ai-distro-agent/src/handlers/undo.rs`
- `tools/shell/static/undo-button.js`

---

## Priority 8: Home Assistant Integration (LOW)

**Problem:** Devs want voice control for smart homes.

**Solution:** MQTT/WebSocket bridge.

```rust
pub async fn home_assistant_bridge(event: IntentEvent) {
    // Publish to MQTT topic: ai-distro/intent
    // Home Assistant subscribes and executes automations
}
```

### Implementation
1. Add MQTT client to Rust agent
2. Map intents to MQTT topics
3. Config: `AI_DISTRO_MQTT_BROKER`, `AI_DISTRO_MQTT_TOPIC`

---

## Implementation Order

| Phase | Items | Duration |
|-------|-------|----------|
| 1 | P0: Pre-baked ISO, P1: OAuth in Web UI | 2 weeks |
| 2 | P2: Tiered Brain, P3: Web Search | 1 week |
| 3 | P4: Audit Viewer, P5: First-Boot Wizard | 1 week |
| 4 | P6: Visual Alerts, P7: Undo | 1 week |
| 5 | P8: Home Assistant | Ongoing |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Setup time (non-dev) | N/A (impossible) | 5 minutes |
| OAuth time | 15 min (terminal) | 30 seconds (click) |
| Complex intent success | 40% | 85% |
| Knowledge question success | 0% | 90% |

---

## Marketing Angle

After implementing P0-P4:

> **AI Distro: The only AI assistant with a cryptographically-verified audit log.**
>
> Your data never leaves your machine. Every action is logged in a tamper-proof hash chain. Perfect for healthcare, legal, and regulated industries where ChatGPT cannot be used.

This is your moat. Enterprise cannot use ChatGPT due to data residency. You can prove exactly what your AI did and when.