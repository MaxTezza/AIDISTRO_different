# AI Distro

> **Voice-first, agentic Linux with cryptographic audit trails.**

Your data never leaves your machine. Every action is logged in a tamper-proof SHA-256 hash chain. Perfect for healthcare, legal, and regulated industries where cloud AI cannot be used.

## Download

> **[Download Latest ISO](https://gitlab.com/jmt3/ai-distro/-/releases)** (coming soon)

Flash to USB with [BalenaEtcher](https://etcher.balena.io/) and boot. No terminal commands required.

## Features

- **Local LLM Brain:** Llama 3.2 1B running locally (Zero API keys)
- **Direct Voice Command:** "Computer" wake word triggers immediate actions
- **Day Planner:** Weather + calendar outfit recommendations
- **Cryptographic Audit:** SHA-256 hash-chain logging for all actions
- **Browser OAuth:** Connect Google/Microsoft accounts with one click

## Voice Commands

Speak naturally. No memorization needed.

| Say This | What Happens |
|----------|--------------|
| "I want to browse the web" | Opens Firefox |
| "Play some music" | Opens Spotify |
| "It's too loud" | Mutes volume |
| "Dark mode please" | Lowers brightness |
| "Get me ready for the day" | Checks weather, calendar, email |
| "What should I wear today?" | Outfit recommendation |
| "Summarize my email" | Inbox summary |
| "Lock my computer" | Sleep mode |

**Proactive Alerts:** The assistant notifies you about low battery, network changes, and system events.

## Architecture

```
┌─────────────────────────────────────┐
│  Web Shell (Face)                   │
│  React-like dashboard + voice UI    │
└─────────────────────────────────────┘
              ↓ IPC
┌─────────────────────────────────────┐
│  Rust Agent (Core)                  │
│  Security policy, audit log, events │
└─────────────────────────────────────┘
              ↓ Tool Calls
┌─────────────────────────────────────┐
│  Python Intelligence (Brain)        │
│  Local LLM intent parsing           │
└─────────────────────────────────────┘
```

## Quickstart

### Option 1: Pre-built ISO (Recommended)

1. Download ISO from [Releases](https://gitlab.com/jmt3/ai-distro/-/releases)
2. Flash to USB with [BalenaEtcher](https://etcher.balena.io/)
3. Boot from USB
4. The assistant launches automatically in fullscreen kiosk mode

### Option 2: Docker (Headless)

```bash
docker build -t ai-distro-agent .
docker run -v /tmp:/tmp -e AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock ai-distro-agent
```

### Option 3: Local Development

```bash
# Build Rust agent
cd src/rust/ai-distro-agent
cargo build --release

# Run agent
AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock ./target/release/ai-distro-agent

# In another terminal, run shell UI
AI_DISTRO_SHELL_STATIC_DIR="$PWD/assets/ui/shell" \
python3 tools/shell/ai_distro_shell.py

# Open http://127.0.0.1:17842/
```

## Connecting Google / Microsoft Accounts

**No terminal commands needed.** Connect accounts directly in the Web Shell:

1. Open `http://127.0.0.1:17842/` in your browser
2. In the sidebar, find **Calendar Provider** or **Email Provider**
3. Select `Google` or `Microsoft` from the dropdown
4. Click **Connect** - a browser tab opens for authorization
5. Approve access → Connection completes automatically

The Web Shell polls for completion and shows status in real-time. Tokens are stored securely in `~/.config/ai-distro/`.

### Manual OAuth (Headless/Advanced)

Only needed for scripts or headless servers:

```bash
# Google Calendar
AI_DISTRO_GOOGLE_CLIENT_ID=your_id \
AI_DISTRO_GOOGLE_CLIENT_SECRET=your_secret \
python3 tools/agent/google_calendar_oauth.py auth-url
# Authorize in browser, then:
python3 tools/agent/google_calendar_oauth.py exchange "<code>"

# Gmail
python3 tools/agent/google_gmail_oauth.py auth-url
python3 tools/agent/google_gmail_oauth.py exchange "<code>"

# Microsoft
python3 tools/agent/microsoft_outlook_oauth.py auth-url
python3 tools/agent/microsoft_outlook_oauth.py exchange "<code>"
```

### Local Calendar (No OAuth Required)

Store events in `~/.config/ai-distro/calendar-events.json`:

```json
[
  {
    "date": "2026-02-16",
    "start": "09:00",
    "title": "Office planning meeting",
    "dress_code": "business",
    "outdoor": false
  }
]
```

## Security

- **Deny by default:** Unknown or high-risk actions are blocked
- **Confirmation required:** Package installs, power operations, email drafts
- **Explicit memory:** `remember ...` commands are user-controlled
- **Audit trail:** All actions logged with hash-chain integrity

### Policy Configuration

Edit `configs/policy.json`:
- `open_url_allowed_domains` - Allowed URL domains
- `open_app_allowed` - Allowed applications
- `rate_limit_per_minute_*` - Rate limiting per action

## Development

### Quality Gate

```bash
make qa-voice
```

### Build ISO

```bash
make deps
make iso
```

## Documentation

- `docs/VOICE_UX.md` - Voice interaction patterns
- `docs/IPC.md` - Inter-process communication
- `docs/RUNTIME_ENV.md` - Environment variables
- `docs/AUNT_USABILITY_ROADMAP.md` - Future usability improvements

## License

MIT