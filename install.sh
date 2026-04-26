#!/bin/bash
# AI Distro Master Installer v2.0
# One-command installation that actually works.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_PREFIX="${AI_DISTRO_INSTALL_PREFIX:-/usr/local}"
CONFIG_DIR="/etc/ai-distro"
LIB_DIR="${INSTALL_PREFIX}/lib/ai-distro"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
CACHE_DIR="${HOME}/.cache/ai-distro"
MODEL_DIR="${CACHE_DIR}/models"
PIPER_DIR="${CACHE_DIR}/piper"

echo "==========================================="
echo "   AI DISTRO: OPERATING SYSTEM INSTALLER"
echo "   v2.0 — One-Command Revolution"
echo "==========================================="
echo ""

# ── 1. System Dependencies ─────────────────────────────────────────────
echo "[1/8] Installing System Dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    libasound2-dev pkg-config scrot tesseract-ocr espeak \
    wmctrl xdotool libatspi2.0-dev \
    python3-pip python3-venv \
    pulseaudio-utils network-manager \
    feh mpv jq curl wget \
    libdbus-1-dev \
    2>/dev/null
echo "  ✔ System dependencies installed"

# ── 2. Python Environment ──────────────────────────────────────────────
echo "[2/8] Setting up Python Virtual Environment..."
cd "$ROOT_DIR"
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q 2>/dev/null || true
pip install -q \
    websockets pytesseract Pillow chromadb sentence-transformers \
    moondream watchdog pypdf python-magic playwright \
    python-telegram-bot opencv-python psutil \
    2>/dev/null || true
playwright install chromium 2>/dev/null || echo "  ⚠ Playwright chromium install failed (non-critical)"
echo "  ✔ Python environment ready"

# ── 3. Neural Models ───────────────────────────────────────────────────
echo "[3/8] Downloading Neural Models..."
mkdir -p "$MODEL_DIR" "$PIPER_DIR"

# Llama 3.2 1B (Fast)
if [ ! -f "$MODEL_DIR/llama-3.2-1b-instruct.gguf" ]; then
    echo "  ↓ Downloading Llama 3.2 1B (~700MB)..."
    curl -L --progress-bar -o "$MODEL_DIR/llama-3.2-1b-instruct.gguf" \
        "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
else
    echo "  ✔ Llama 3.2 1B already present"
fi

# Llama 3.2 3B (Smart) — optional
if [ ! -f "$MODEL_DIR/llama-3.2-3b-instruct.gguf" ]; then
    echo "  ↓ Downloading Llama 3.2 3B (~1.8GB)..."
    curl -L --progress-bar -o "$MODEL_DIR/llama-3.2-3b-instruct.gguf" \
        "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf" || true
else
    echo "  ✔ Llama 3.2 3B already present"
fi

# Piper TTS
if [ ! -f "$PIPER_DIR/piper/piper" ]; then
    echo "  ↓ Downloading Piper TTS..."
    cd "$PIPER_DIR"
    curl -L --progress-bar -o piper.tar.gz \
        "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz"
    tar -xf piper.tar.gz
    rm -f piper.tar.gz
    curl -L --progress-bar -o en_US-amy-medium.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx?raw=true"
    curl -L --progress-bar -o en_US-amy-medium.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json?raw=true"
    cd "$ROOT_DIR"
else
    echo "  ✔ Piper TTS already present"
fi

# ── 4. Build Rust Core ─────────────────────────────────────────────────
echo "[4/8] Compiling Rust Core (Agent, Voice, HUD, CLI)..."
cd "$ROOT_DIR/src/rust"
cargo build --release 2>&1 | tail -5
cd "$ROOT_DIR"
echo "  ✔ Rust binaries compiled"

# ── 5. Install Binaries ───────────────────────────────────────────────
echo "[5/8] Installing binaries to ${INSTALL_PREFIX}/bin/..."
BINS=(ai-distro-cli ai-distro-agent ai-distro-core ai-distro-voice ai-distro-hud)
for bin in "${BINS[@]}"; do
    BIN_PATH="$ROOT_DIR/src/rust/target/release/$bin"
    if [ -f "$BIN_PATH" ]; then
        sudo ln -sf "$BIN_PATH" "${INSTALL_PREFIX}/bin/$bin"
        echo "  ✔ $bin"
    fi
done
# The CLI is also available as just 'ai-distro'
sudo ln -sf "$ROOT_DIR/src/rust/target/release/ai-distro-cli" "${INSTALL_PREFIX}/bin/ai-distro"
echo "  ✔ ai-distro (CLI alias)"

# ── 6. Install Configs ─────────────────────────────────────────────────
echo "[6/8] Installing configuration..."
sudo mkdir -p "$CONFIG_DIR"
for cfg in agent.json core.json voice.json policy.json persona.json; do
    SRC="$ROOT_DIR/configs/$cfg"
    DEST="$CONFIG_DIR/$cfg"
    if [ -f "$SRC" ] && [ ! -f "$DEST" ]; then
        sudo cp "$SRC" "$DEST"
        echo "  ✔ $cfg"
    elif [ -f "$DEST" ]; then
        echo "  ⊘ $cfg (already exists, preserved)"
    fi
done

# Install Python tools to lib directory
sudo mkdir -p "$LIB_DIR"
sudo cp -r "$ROOT_DIR/tools/agent/"*.py "$LIB_DIR/" 2>/dev/null || true
echo "  ✔ Python tools installed to $LIB_DIR"

# Create Spirit Bridge config template
SPIRIT_CONFIG="${HOME}/.config/ai-distro-spirit.json"
if [ ! -f "$SPIRIT_CONFIG" ]; then
    mkdir -p "$(dirname "$SPIRIT_CONFIG")"
    echo '{"token": "", "master_id": ""}' > "$SPIRIT_CONFIG"
    echo "  ✔ Spirit Bridge config template created"
fi

# ── 7. Install Systemd User Services ──────────────────────────────────
echo "[7/8] Installing systemd user services..."
mkdir -p "$SYSTEMD_USER_DIR"

# Agent Service
cat > "$SYSTEMD_USER_DIR/ai-distro-agent.service" << EOF
[Unit]
Description=AI Distro Agent — Brain & Action Engine
After=default.target

[Service]
Type=simple
ExecStart=${INSTALL_PREFIX}/bin/ai-distro-agent
Restart=on-failure
RestartSec=2
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
Environment=AI_DISTRO_TOOLS_DIR=${ROOT_DIR}/tools/agent
Environment=AI_DISTRO_SKILLS_CORE_DIR=${ROOT_DIR}/src/skills/core
Environment=AI_DISTRO_SKILLS_DYNAMIC_DIR=${ROOT_DIR}/src/skills/dynamic
Environment=AI_DISTRO_CONFIG=${CONFIG_DIR}/agent.json
RuntimeDirectory=ai-distro

[Install]
WantedBy=default.target
EOF

# Voice Service
cat > "$SYSTEMD_USER_DIR/ai-distro-voice.service" << EOF
[Unit]
Description=AI Distro Voice — Piper TTS & ASR Pipeline
After=ai-distro-agent.service sound.target
Requires=ai-distro-agent.service

[Service]
Type=simple
ExecStart=${INSTALL_PREFIX}/bin/ai-distro-voice
Restart=on-failure
RestartSec=2
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
Environment=AI_DISTRO_TTS_BINARY=${PIPER_DIR}/piper/piper
Environment=AI_DISTRO_TTS_MODEL=${PIPER_DIR}/en_US-amy-medium.onnx

[Install]
WantedBy=default.target
EOF

# HUD Service
cat > "$SYSTEMD_USER_DIR/ai-distro-hud.service" << EOF
[Unit]
Description=AI Distro HUD — Desktop Overlay
After=graphical-session.target ai-distro-agent.service
Requires=ai-distro-agent.service

[Service]
Type=simple
ExecStart=${INSTALL_PREFIX}/bin/ai-distro-hud
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0
Environment=WAYLAND_DISPLAY=wayland-0

[Install]
WantedBy=graphical-session.target
EOF

# Curator Service (Bayesian Proactive Engine)
cat > "$SYSTEMD_USER_DIR/ai-distro-curator.service" << EOF
[Unit]
Description=AI Distro Curator — Bayesian Proactive Intelligence
After=ai-distro-agent.service
Requires=ai-distro-agent.service

[Service]
Type=simple
ExecStart=${ROOT_DIR}/.venv/bin/python3 ${ROOT_DIR}/tools/agent/curator.py
Restart=on-failure
RestartSec=10
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
Environment=PYTHONPATH=${ROOT_DIR}/tools/agent
WorkingDirectory=${ROOT_DIR}

[Install]
WantedBy=default.target
EOF

# Spirit Bridge Service (Telegram Remote Control)
cat > "$SYSTEMD_USER_DIR/ai-distro-spirit.service" << EOF
[Unit]
Description=AI Distro Spirit Bridge — Telegram Remote Control
After=network-online.target ai-distro-agent.service
Wants=network-online.target
Requires=ai-distro-agent.service

[Service]
Type=simple
ExecStart=${ROOT_DIR}/.venv/bin/python3 ${ROOT_DIR}/tools/agent/spirit_bridge.py
Restart=on-failure
RestartSec=10
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
WorkingDirectory=${ROOT_DIR}

[Install]
WantedBy=default.target
EOF

# System Healer Service
cat > "$SYSTEMD_USER_DIR/ai-distro-healer.service" << EOF
[Unit]
Description=AI Distro Healer — Autonomous System Repair
After=ai-distro-agent.service

[Service]
Type=simple
ExecStart=${ROOT_DIR}/.venv/bin/python3 ${ROOT_DIR}/tools/agent/system_healer.py
Restart=on-failure
RestartSec=30
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
WorkingDirectory=${ROOT_DIR}

[Install]
WantedBy=default.target
EOF

# Hardware Events Daemon (Digital Nervous System)
cat > "$SYSTEMD_USER_DIR/ai-distro-hardware.service" << EOF
[Unit]
Description=AI Distro Hardware — Digital Nervous System (D-Bus)
After=ai-distro-agent.service
Requires=ai-distro-agent.service

[Service]
Type=simple
ExecStart=${ROOT_DIR}/.venv/bin/python3 ${ROOT_DIR}/tools/agent/hardware_events.py
Restart=on-failure
RestartSec=10
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
WorkingDirectory=${ROOT_DIR}

[Install]
WantedBy=default.target
EOF

# Vision Brain Service (Persistent VLM)
cat > "$SYSTEMD_USER_DIR/ai-distro-vision.service" << EOF
[Unit]
Description=AI Distro Vision — Persistent Moondream2 VLM
After=ai-distro-agent.service

[Service]
Type=simple
ExecStart=${ROOT_DIR}/.venv/bin/python3 ${ROOT_DIR}/tools/agent/vision_brain.py --server
Restart=on-failure
RestartSec=15
Environment=VISION_HOST=127.0.0.1
Environment=VISION_PORT=7860
WorkingDirectory=${ROOT_DIR}

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
echo "  ✔ All 8 systemd user services installed"

# ── 8. Create Directories & Finalize ──────────────────────────────────
echo "[8/8] Creating runtime directories..."
mkdir -p "${CACHE_DIR}/memory"
mkdir -p "${CACHE_DIR}/screenshots"
mkdir -p "${HOME}/.cache/ai-distro/bayesian"
mkdir -p "${ROOT_DIR}/tools/agent/custom"
mkdir -p "${ROOT_DIR}/src/skills/dynamic"
mkdir -p "${HOME}/ai-distro-projects"
echo "  ✔ Runtime directories created"

echo ""
echo "==========================================="
echo "   ✅ INSTALLATION COMPLETE"
echo "==========================================="
echo ""
echo "Quick Start:"
echo "  ai-distro start     — Wake up the sentient stack"
echo "  ai-distro status    — Check the system pulse"
echo "  ai-distro setup     — Voice-guided onboarding"
echo "  ai-distro heal      — Run autonomous diagnostics"
echo ""
echo "For Telegram remote control:"
echo "  1. Get a bot token from @BotFather"
echo "  2. Edit ~/.config/ai-distro-spirit.json"
echo "  3. ai-distro start"
echo ""
echo "Intelligence mode:"
echo "  ai-distro intelligence mode local   — Use on-device Llama 3.2"
echo "  ai-distro intelligence mode cloud   — Use cloud API"
echo "  ai-distro intelligence cloud openai YOUR_KEY"
echo ""
echo "==========================================="
echo "   AI DISTRO: It doesn't just run your apps."
echo "   It understands your world."
echo "==========================================="
