#!/bin/bash
# AI Distro Forge: ISO Builder v1.0
set -e

# This script is a blueprint for creating the standalone AI Distro ISO.
# It requires a Debian/Ubuntu host and 'live-build' tools.

echo "==========================================="
echo "   AI DISTRO FORGE: BUILDING THE FUTURE"
echo "==========================================="

# 1. Install Build Tools
sudo apt-get install -y live-build debootstrap xorriso

# 2. Initialize Live Build
mkdir -p ~/ai-distro-live && cd ~/ai-distro-live
lb config --binary-images iso-hybrid --debian-installer live

# 3. Configure Package List
cat > config/package-lists/my.list.chroot <<EOF
# Core
linux-image-amd64
live-boot
systemd-sysv

# Wayland / Sway
sway
xwayland
foot
wmenu
libasound2-dev
pkg-config
scrot
tesseract-ocr
espeak
python3-pip
python3-venv
python3-gi
python3-dbus
git
curl

# Networking
network-manager
bluez
EOF

# 4. Inject AI Distro Core
echo "[SYSTEM] Injecting AI Distro code and models..."
mkdir -p config/includes.chroot/etc/ai-distro
mkdir -p config/includes.chroot/usr/local/bin
mkdir -p config/includes.chroot/var/lib/ai-distro/models

# Copy our code (this assumes the script is run from the project root)
cp -r ~/AI_Distro config/includes.chroot/home/user/AI_Distro

# 5. Set up Auto-Onboarding
cat > config/includes.chroot/etc/systemd/user/ai-distro-onboarding.service <<EOF
[Unit]
Description=AI Distro First Boot Onboarding
After=sway.service

[Service]
ExecStart=/usr/bin/python3 /home/user/AI_Distro/tools/agent/setup_wizard.py
StandardInput=tty
StandardOutput=inherit

[Install]
WantedBy=default.target
EOF

# 6. Final Build Command
echo "[SYSTEM] Ready to forge. Run 'sudo lb build' to generate ai-distro.iso"
echo "==========================================="
