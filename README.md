# AI Distro

AI Distro is an AI-integrated Linux distribution layer that automates system tasks, provides voice and text interaction, and utilizes local AI models to assist users.

## System Capabilities

### 1. Local AI & Reasoning
- **Voice Interaction:** Utilizes `Piper` for local Text-to-Speech (TTS) and `SpeechRecognition` for Speech-to-Text (STT) capabilities.
- **Screen Understanding:** Uses `Moondream2` Vision-Language Model (VLM) running as a local microservice to analyze screenshots and interpret UI state.
- **Semantic Memory:** Leverages `ChromaDB` for storing and retrieving past interactions and context semantically.
- **Preference Tracking:** Uses a Bayesian preference engine to track user habits and application usage patterns over time.

### 2. Desktop Automation & Control
- **Accessibility Automation (AT-SPI):** Interacts with applications semantically, allowing the agent to find and click UI elements by name or role rather than fixed screen coordinates.
- **Coordinate Automation:** Uses `xdotool` as a fallback for direct mouse and keyboard emulation.
- **System Events:** Integrates with Linux `D-Bus` and `udev` to monitor and react to hardware events (e.g., USB plugging, battery state, network changes).
- **Web Automation:** Uses `Playwright` to navigate websites, extract information, and perform autonomous web tasks.
- **System Monitoring:** Health checking scripts to autonomously monitor memory, CPU, and critical background services.

### 3. Pre-configured "Grandma" Skills
The system includes simple macros for basic tasks designed for non-technical users:
- **Multimedia:** Voice-controlled media playback via `mpv`.
- **Slideshows:** Automated photo viewing using `feh`.
- **Messaging:** Voice-to-text messaging features utilizing configured local or remote gateways.
- **News:** Fetches and reads current headlines.

### 4. Development & Utility Tools
- **Software Forge:** A project scaffolding engine that generates boilerplate code for scripts, web apps, and basic projects.
- **Telegram Remote Control:** A daemon (`ai-distro-spirit`) that connects the local OS agent to a Telegram bot, allowing users to send commands to their machine remotely.
- **Local Identity:** Automatically configures a local mailbox (`assistant@local.aidistro.os`) for managing autonomous agent communication.

## Architecture

The system is composed of several `systemd` user services:
- `ai-distro-agent`: The core reasoning and execution loop (Rust/Python).
- `ai-distro-voice`: The audio processing pipeline.
- `ai-distro-hud`: Desktop UI overlay built with `egui`.
- `ai-distro-vision`: The Moondream2 model server.
- `ai-distro-curator`: Context and memory management.
- `ai-distro-spirit`: Telegram bot integration.
- `ai-distro-healer`: Diagnostic and self-repair loops.
- `ai-distro-hardware`: D-Bus/udev listener.

## Installation

```bash
git clone https://gitlab.com/maxtezza29464/ai_distro.git ~/AI_Distro
cd ~/AI_Distro
bash install.sh
```

## Building a Live ISO
```bash
# Build a complete bootable live ISO:
bash tools/release/build_iso.sh
cd /tmp/ai-distro-live && sudo lb build

# Test in QEMU:
qemu-system-x86_64 -m 4G -cdrom live-image-amd64.hybrid.iso -enable-kvm
```

## CLI Usage

The `ai-distro` command manages the system:
- `ai-distro start`: Starts all background services.
- `ai-distro stop`: Stops all services.
- `ai-distro status`: Shows service health, memory, and system metrics.
- `ai-distro setup`: Runs the onboarding wizard.
- `ai-distro logs`: Tails the logs of the background services.
- `ai-distro heal`: Runs diagnostics and attempts auto-recovery of failed services.
