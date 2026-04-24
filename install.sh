#!/bin/bash
# AI Distro Master Installer v1.0
set -e

echo "==========================================="
echo "   AI DISTRO: OPERATING SYSTEM INSTALLER"
echo "==========================================="

# 1. System Dependencies
echo "[1/6] Installing System Dependencies (ALSA, OCR, TTS)..."
sudo apt-get update
sudo apt-get install -y libasound2-dev pkg-config scrot tesseract-ocr espeak gh wmctrl xdotool libatspi2.0-dev python3-pip python3-venv

# 2. Python Environment
echo "[2/6] Setting up Python Virtual Environment..."
cd ~/AI_Distro
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install websockets pytesseract Pillow chromadb sentence-transformers moondream watchdog pypdf python-magic playwright
playwright install chromium

# 3. Neural Models
echo "[3/6] Downloading Neural Models (Llama 3.2, Moondream, Piper)..."
mkdir -p ~/.cache/ai-distro/models
mkdir -p ~/.cache/ai-distro/piper

# Llama 3.2
if [ ! -f ~/.cache/ai-distro/models/llama-3.2-1b-instruct.gguf ]; then
    echo "Downloading Llama 3.2 1B (Fast)..."
    curl -L -o ~/.cache/ai-distro/models/llama-3.2-1b-instruct.gguf "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
fi

if [ ! -f ~/.cache/ai-distro/models/llama-3.2-3b-instruct.gguf ]; then
    echo "Downloading Llama 3.2 3B (Smart)..."
    curl -L -o ~/.cache/ai-distro/models/llama-3.2-3b-instruct.gguf "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
fi

# Piper TTS
if [ ! -d ~/.cache/ai-distro/piper/piper ]; then
    cd ~/.cache/ai-distro/piper
    curl -L -o piper.tar.gz "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz"
    tar -xf piper.tar.gz
    curl -L -o en_US-amy-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx?raw=true"
    curl -L -o en_US-amy-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json?raw=true"
    cd ~/AI_Distro
fi

# 4. Build Rust Core
echo "[4/6] Compiling Rust Core (Agent, Voice, HUD, CLI)..."
cd src/rust
cargo build --release
sudo ln -sf $(pwd)/target/release/ai-distro-cli /usr/local/bin/ai-distro
cd ../..

# 5. Directories & Permissions
echo "[5/6] Configuring System Paths..."
sudo mkdir -p /var/log/ai-distro /var/lib/ai-distro
sudo chown $USER:$USER /var/log/ai-distro /var/lib/ai-distro

# 6. Systemd Services
echo "[6/6] Finalizing installation..."
echo "Run './tools/agent/setup_wizard.py' to begin your journey."

echo "==========================================="
echo "   INSTALLATION COMPLETE: ENJOY THE REVOLUTION"
echo "==========================================="
