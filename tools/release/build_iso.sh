#!/bin/bash
# AI Distro Forge: ISO Builder v1.0
set -e

echo "==========================================="
echo "   AI DISTRO FORGE: BUILDING THE FUTURE"
echo "==========================================="

# 1. Install Build Tools
sudo apt-get install -y live-build debootstrap xorriso squashfs-tools

# 2. Initialize Live Build
BUILD_DIR=~/ai-distro-live
mkdir -p $BUILD_DIR && cd $BUILD_DIR
lb config --binary-images iso-hybrid --debian-installer live --architectures amd64 --distribution bookworm

# 3. Configure Package List
cat > config/package-lists/my.list.chroot <<EOF
# Core
linux-image-amd64
live-boot
systemd-sysv
sudo

# Wayland / Sway
sway
xwayland
foot
wmenu
libasound2
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
wget
mpv
feh

# Networking
network-manager
bluez
EOF

# 4. Inject AI Distro Core & Assets
echo "[SYSTEM] Injecting AI Distro core..."
SKEL_DIR="config/includes.chroot/etc/skel/AI_Distro"
mkdir -p "$SKEL_DIR"
cp -r ~/AI_Distro/* "$SKEL_DIR/"

# Inject Models (This makes the ISO large but fully offline-ready)
MODEL_TARGET="config/includes.chroot/etc/skel/.cache/ai-distro/models"
mkdir -p "$MODEL_TARGET"
cp ~/.cache/ai-distro/models/*.gguf "$MODEL_TARGET/" || echo "No models found to inject"

# 5. Configure Systemd Services for the ISO
mkdir -p config/includes.chroot/etc/systemd/user/
cp ~/.config/systemd/user/ai-distro-*.service config/includes.chroot/etc/systemd/user/

# 6. Auto-start Sway on login
cat > config/includes.chroot/etc/profile.d/ai-distro-start.sh <<EOF
if [ -z "\$DISPLAY" ] && [ "\$(tty)" = "/dev/tty1" ]; then
  exec sway
fi
EOF

# 7. Final Build Command
echo "[SYSTEM] Setup complete. Ready to forge."
echo "To finish: Run 'sudo lb build' inside $BUILD_DIR"
echo "==========================================="
