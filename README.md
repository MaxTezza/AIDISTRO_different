# AI Distro

A locally-hosted AI agent layer for Linux that automates desktop tasks via voice, text, and vision. Runs on Debian/Ubuntu systems and combines a Rust service mesh with Python tool scripts.

## What It Actually Does

### Local LLM Reasoning (`brain.py`)
- Routes user input through a pipeline: **Bayesian context → Memory recall → LLM inference**
- Runs **Llama 3.2 (1B, GGUF)** locally via `llama-cpp-python` for offline inference
- Falls back to **OpenAI (GPT-4o-mini)** or **Google Gemini** cloud APIs when configured
- Injects learned user preferences and recalled conversation history into the system prompt automatically

### Voice Pipeline (`ai-distro-voice`)
- **Speech-to-Text:** Records audio via `cpal`, pipes it to `Vosk` for local transcription
- **Text-to-Speech:** Synthesizes spoken replies through `Piper TTS`
- Supports barge-in detection (interrupts TTS when the user starts speaking)

### Screen Understanding (`vision_brain.py`, `screen_context_tool.py`)
- Runs **Moondream2 VLM** as a persistent HTTP microservice on `localhost:7860`
- Captures the screen via `scrot` (X11) or `grim` (Wayland), sends it to the VLM for visual reasoning
- Falls back to **Tesseract OCR** when the VLM is unavailable
- Also reads open window titles via `wmctrl`/`xdotool` for structural awareness

### Desktop Automation (`atspi_hands.py`)
- **AT-SPI semantic automation:** Finds and clicks UI elements by name/role across any accessible GTK/Qt application using the Linux accessibility stack
- **Scored fuzzy matching:** Searches the AT-SPI tree for the best match (exact → substring → reverse), preferring visible and interactive elements
- **xdotool fallback:** When AT-SPI is unavailable, falls back to coordinate-based clicking and keyboard emulation

### Conversation Memory (`conversation_memory.py`)
- Stores every AI interaction with timestamps in a local SQLite database
- Implements **TF-IDF semantic search** (zero external dependencies) to recall relevant past conversations
- Injects recent history and semantically recalled context into the AI system prompt for continuity

### Bayesian Preference Engine (`bayesian_engine.py`)
- Models user habits as **Beta(α, β) distributions** across time-of-day, day-of-week, and app context
- Applies exponential decay so the system adapts to changing routines
- Tracks sequential action chains (A → B) to predict what the user will do next
- Generates a `prompt_context` block that is injected into the LLM system prompt

### Hardware Event Listener (`hardware_events.py`)
- Subscribes to **D-Bus signals** for real-time hardware event monitoring:
  - `UPower` battery changes (low battery warnings, charge state)
  - `NetworkManager` connectivity changes (disconnect alerts, reconnect notifications)
  - `UDisks2` USB device plug/unplug events
- Falls back to polling `/sys/class/power_supply` and `nmcli` when D-Bus bindings are unavailable

### System Healer (`system_healer.py`)
- Runs on a 5-minute loop, performing automated health checks:
  - Restarts crashed `systemd --user` services with verification
  - Monitors disk space and runs emergency cleanup (apt cache, journal trim, temp files) above 95%
  - Monitors memory pressure and drops caches when available RAM is critically low
  - Tests network connectivity and attempts repair via `nmcli`
  - Checks audio subsystem (PipeWire/PulseAudio) and restarts if dead
  - Scans `journalctl` for recent critical errors and surfaces them

### Web Automation (`web_navigator.py`)
- Uses **Playwright** (headless Chromium) to navigate to URLs and execute goal-driven tasks
- DOM heuristics handle common actions: searching, clicking buttons by text, extracting page content
- Optionally uses the VLM to visually analyze page screenshots for reasoning

### Software Forge (`software_forge.py`)
- Generates scripts and projects by prompting the local LLM
- Scaffolds **Flask web apps**, **CLI tools**, **systemd services**, and generic Python projects from templates
- Executes generated code in a sandboxed temp environment with output capture
- Auto-registers generated scripts as dynamic agent skills (JSON manifest in `src/skills/dynamic/`)
- Can auto-fix broken code by feeding errors back to the LLM

### Intent Parser (`intent_parser.py`)
- A rule-based NLP parser (567 lines) that maps natural language to structured actions
- Handles: app launching, URL opening, Google search, volume/brightness, package management, Wi-Fi/Bluetooth toggle, power management, file listing, calendar, email, weather, outfit planning, code generation requests, and preference setting
- Falls back to an `intent-map.json` config for extensibility

### Telegram Remote Control (`spirit_bridge.py`)
- A `python-telegram-bot` daemon that bridges Telegram messages to the local agent via Unix domain socket IPC
- Master ID authentication prevents unauthorized access
- Forwards natural language commands to the local agent and returns responses

### Pre-configured Skills
- **Media playback** (`player_control.py`): Controls `mpv` with preset internet radio stations (Classical, Jazz, News) and system volume via `amixer`
- **Photo slideshows** (`gallery_show.py`): Launches `feh` in fullscreen random slideshow mode on `~/Pictures`
- **News reader** (`news_reader.py`): Fetches and parses BBC World RSS feed, returns top 5 headlines
- **Family messenger** (`family_messenger.py`): Maps family role names to email addresses in a persistent JSON config; sends real messages via Gmail OAuth, SMTP, or the email router

### Other Implemented Tools
- **Notification bridge** (`notification_bridge.py`): Desktop notification forwarding
- **Bluetooth audio** (`bluetooth_audio.py`): Bluetooth device scanning and connection
- **Crash reporter** (`crash_reporter.py`): Structured crash reporting with audit trails
- **Theming engine** (`theming_engine.py`): System theme management
- **Privacy dashboard** (`privacy_dashboard.py`): Privacy controls and audit interface
- **Offline mode** (`offline_mode.py`): Graceful degradation when internet is unavailable
- **Skill SDK** (`skill_sdk.py`): Framework for writing and registering custom agent skills
- **Hot reload** (`hot_reload.py`): Live-reload of skills without service restart
- **Day planner** (`day_planner.py`): Calendar + weather + outfit planning integration
- **File intelligence** (`file_intelligence.py`): Smart file search and organization
- **Wake word engine** (`wake_word_engine.py`): "Hey computer" activation detection
- **Encrypted DB** (`encrypted_db.py`): SQLCipher-backed encrypted local storage

## Architecture

The system runs as `systemd --user` services:

| Service | Language | Role |
|---------|----------|------|
| `ai-distro-agent` | Rust | Core IPC server, action routing, policy enforcement, skill loading |
| `ai-distro-voice` | Rust | Audio capture (cpal) → STT (Vosk) → agent → TTS (Piper) |
| `ai-distro-hud` | Rust | Desktop overlay (egui) that displays agent event cards |
| `ai-distro-vision` | Python | Moondream2 VLM HTTP server on port 7860 |
| `ai-distro-curator` | Python | Context management, memory and preference aggregation |
| `ai-distro-spirit` | Python | Telegram bot bridge |
| `ai-distro-healer` | Python | Autonomous health monitor and repair loop |
| `ai-distro-hardware` | Python | D-Bus/udev event listener |

Communication between services uses **Unix domain sockets** with JSON-over-newline IPC.

## CLI

```
ai-distro start          # Start all services
ai-distro stop           # Stop all services
ai-distro restart        # Restart all services
ai-distro status         # Show service health + system metrics
ai-distro setup          # Run onboarding wizard
ai-distro heal           # One-shot health check + auto-repair
ai-distro logs [--lines] # Tail service logs
ai-distro update         # Pull latest from git and rebuild
ai-distro audit <path>   # Security/integrity audit on a path
ai-distro intelligence   # Configure local/cloud LLM provider
ai-distro migrate <path> # Import legacy data into AI memory
```

## Installation

```bash
git clone https://gitlab.com/maxtezza29464/ai_distro.git ~/AI_Distro
cd ~/AI_Distro
bash install.sh
```

Requires: Debian/Ubuntu, Rust toolchain, Python 3.11+, and a working D-Bus session.

## Building a Live ISO

```bash
# Build the bootable ISO (requires sudo, ~20 min)
sudo ./iso/build-iso.sh

# Apply isohybrid for USB boot support
sudo isohybrid iso/build/chroot/binary.hybrid.iso

# Flash to USB (replace sdX with your drive)
sudo dd if=iso/build/chroot/binary.hybrid.iso of=/dev/sdX bs=4M status=progress && sync

# Or test in QEMU:
qemu-system-x86_64 -m 4G -cdrom iso/build/chroot/binary.hybrid.iso -enable-kvm
```

Build dependencies: `live-build`, `debootstrap`, `xorriso`, `isolinux`, `syslinux-common`, `syslinux-utils`

## Known Limitations

- Cloud LLM fallback requires manually setting API keys in `configs/agent.json`
- Email sending (family_messenger, IMAP draft) requires configuring SMTP or Gmail OAuth credentials
- AT-SPI automation only works on applications that expose accessibility interfaces (most GTK/Qt apps do)
- VLM (Moondream2) requires ~2GB RAM; systems with <4GB will rely on OCR fallback
- Model download (`download_model.py`) requires internet access and ~800MB–3.4GB of storage depending on model size
