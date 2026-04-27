#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# AI Distro — ISO Builder
#
# Creates a bootable live ISO based on Debian with:
#   - XFCE desktop (lightweight, good for older hardware)
#   - All AI Distro services pre-installed
#   - Neural models pre-cached
#   - Auto-login to a live session
#   - "ai-distro setup" runs on first boot
#
# Requirements: live-build, debootstrap, xorriso
# Usage: sudo ./build-iso.sh [--no-models] [--arch amd64]
#
# Output: ai-distro-live-<date>.iso
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${SCRIPT_DIR}/build"
ARCH="amd64"
INCLUDE_MODELS=true
ISO_NAME="ai-distro-live-$(date +%Y%m%d)"
DEBIAN_SUITE="bookworm"  # Debian 12 (stable)

# ── Parse arguments ──────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-models)  INCLUDE_MODELS=false; shift ;;
        --arch)       ARCH="$2"; shift 2 ;;
        --suite)      DEBIAN_SUITE="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: sudo ./build-iso.sh [--no-models] [--arch amd64] [--suite bookworm]"
            echo ""
            echo "Options:"
            echo "  --no-models   Skip bundling neural models (saves ~3GB, downloads on first boot)"
            echo "  --arch        Target architecture (default: amd64)"
            echo "  --suite       Debian suite (default: bookworm)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Preflight checks ────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════"
echo "  AI DISTRO ISO BUILDER"
echo "  Building: ${ISO_NAME}.iso (${ARCH})"
echo "  Suite: ${DEBIAN_SUITE}"
echo "  Models: $([ "$INCLUDE_MODELS" = true ] && echo "bundled" || echo "download on first boot")"
echo "═══════════════════════════════════════════════════"
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root (sudo)."
    exit 1
fi

# Check for required tools
for tool in lb debootstrap xorriso; do
    if ! command -v "$tool" &>/dev/null; then
        echo "Installing missing tool: $tool"
        apt-get install -y -qq live-build debootstrap xorriso 2>/dev/null
        break
    fi
done

# ── Clean previous build ────────────────────────────────────────────
echo "[1/6] Preparing build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# ── Configure live-build ─────────────────────────────────────────────
echo "[2/6] Configuring live-build..."
lb config \
    --distribution "$DEBIAN_SUITE" \
    --architectures "$ARCH" \
    --binary-images iso-hybrid \
    --bootappend-live "boot=live components quiet splash" \
    --debian-installer false \
    --iso-application "AI Distro" \
    --iso-publisher "AI Distro Project" \
    --iso-volume "AI-DISTRO-LIVE" \
    --memtest none \
    --apt-recommends false \
    --firmware-binary true \
    --firmware-chroot true \
    2>/dev/null

# ── Package lists ────────────────────────────────────────────────────
echo "[3/6] Defining package lists..."

# Core desktop environment
mkdir -p config/package-lists
cat > config/package-lists/desktop.list.chroot <<'PKGLIST'
xfce4
xfce4-terminal
xfce4-panel
xfce4-session
xfce4-settings
thunar
lightdm
lightdm-gtk-greeter
network-manager
network-manager-gnome
pulseaudio
pavucontrol
firefox-esr
PKGLIST

# AI Distro system dependencies
cat > config/package-lists/ai-distro-deps.list.chroot <<'PKGLIST'
libasound2-dev
pkg-config
scrot
tesseract-ocr
espeak
wmctrl
xdotool
libatspi2.0-dev
python3-pip
python3-venv
python3-dev
pulseaudio-utils
feh
mpv
jq
curl
wget
git
build-essential
libdbus-1-dev
alsa-utils
sudo
locales
PKGLIST

# Firmware for common laptop hardware
cat > config/package-lists/firmware.list.chroot <<'PKGLIST'
firmware-linux
firmware-iwlwifi
firmware-realtek
firmware-atheros
firmware-misc-nonfree
PKGLIST

# ── Custom hooks (run inside chroot during build) ────────────────────
echo "[4/6] Setting up build hooks..."
mkdir -p config/hooks/live

# Hook: Create the ai-distro user and configure auto-login
cat > config/hooks/live/0100-create-user.hook.chroot <<'HOOK'
#!/bin/bash
set -e

# Create the ai-distro user
useradd -m -s /bin/bash -G sudo,audio,video,plugdev,netdev pilot 2>/dev/null || true
echo "pilot:pilot" | chpasswd
echo "pilot ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/pilot

# Configure auto-login via LightDM
mkdir -p /etc/lightdm/lightdm.conf.d
cat > /etc/lightdm/lightdm.conf.d/50-autologin.conf <<EOF
[Seat:*]
autologin-user=pilot
autologin-user-timeout=0
EOF

echo "[ISO] User 'pilot' created with auto-login"
HOOK
chmod +x config/hooks/live/0100-create-user.hook.chroot

# Hook: Set up locale
cat > config/hooks/live/0050-locale.hook.chroot <<'HOOK'
#!/bin/bash
set -e
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
update-locale LANG=en_US.UTF-8
HOOK
chmod +x config/hooks/live/0050-locale.hook.chroot

# ── Copy AI Distro source into the image ─────────────────────────────
echo "[5/6] Embedding AI Distro source..."
mkdir -p config/includes.chroot/home/pilot/AI_Distro

# Copy source tree (excluding build artifacts and .git)
rsync -a --exclude='.git' --exclude='target' --exclude='.venv' \
    --exclude='iso/build' --exclude='__pycache__' \
    "$ROOT_DIR/" config/includes.chroot/home/pilot/AI_Distro/

# Create first-boot setup script
mkdir -p config/includes.chroot/etc/xdg/autostart
cat > config/includes.chroot/home/pilot/.config/ai-distro-firstboot.sh <<'FIRSTBOOT'
#!/bin/bash
# AI Distro First Boot — runs once after live boot
MARKER="$HOME/.config/ai-distro-firstboot-done"

if [ -f "$MARKER" ]; then
    # Already ran — just start services
    if command -v ai-distro &>/dev/null; then
        ai-distro start &
    fi
    exit 0
fi

# Show welcome notification
notify-send "AI Distro" "Welcome! Running first-time setup..." -i dialog-information 2>/dev/null || true

# Run the installer (non-interactive parts)
cd "$HOME/AI_Distro"
if [ -f install.sh ]; then
    # Run install in a terminal so the user can see progress
    xfce4-terminal --title="AI Distro Setup" \
        -e "bash -c './install.sh && ai-distro setup; echo; echo \"Setup complete! Press Enter to close.\"; read'" &
fi

touch "$MARKER"
FIRSTBOOT
chmod +x config/includes.chroot/home/pilot/.config/ai-distro-firstboot.sh

# Desktop autostart entry for first-boot
mkdir -p config/includes.chroot/home/pilot/.config/autostart
cat > config/includes.chroot/home/pilot/.config/autostart/ai-distro-firstboot.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=AI Distro First Boot
Exec=/home/pilot/.config/ai-distro-firstboot.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=AI Distro first-time setup and service launcher
DESKTOP

# Desktop shortcut for AI Distro terminal
mkdir -p config/includes.chroot/home/pilot/Desktop
cat > config/includes.chroot/home/pilot/Desktop/ai-distro-terminal.desktop <<'DESKTOP'
[Desktop Entry]
Version=1.0
Type=Application
Name=AI Distro Terminal
Comment=Talk to your AI partner
Exec=xfce4-terminal --title="AI Distro" -e "bash -c 'ai-distro status; echo; echo \"Type a command or say: ai-distro setup\"; exec bash'"
Icon=utilities-terminal
Terminal=false
Categories=System;
DESKTOP

# Fix ownership (will be corrected by chroot hook too)
cat > config/hooks/live/0200-fix-perms.hook.chroot <<'HOOK'
#!/bin/bash
chown -R pilot:pilot /home/pilot/ 2>/dev/null || true
HOOK
chmod +x config/hooks/live/0200-fix-perms.hook.chroot

# ── Optionally bundle pre-downloaded models ──────────────────────────
if [ "$INCLUDE_MODELS" = true ]; then
    echo "  Bundling neural models (this makes the ISO larger but faster to start)..."
    MODEL_SRC="$HOME/.cache/ai-distro"
    if [ -d "$MODEL_SRC" ]; then
        mkdir -p config/includes.chroot/home/pilot/.cache/ai-distro
        # Copy models (but not huge ones if they'd make the ISO impractical)
        if [ -d "$MODEL_SRC/models" ]; then
            cp -r "$MODEL_SRC/models" config/includes.chroot/home/pilot/.cache/ai-distro/
            echo "  ✔ LLM models bundled"
        fi
        if [ -d "$MODEL_SRC/piper" ]; then
            cp -r "$MODEL_SRC/piper" config/includes.chroot/home/pilot/.cache/ai-distro/
            echo "  ✔ Piper TTS bundled"
        fi
        if [ -d "$MODEL_SRC/vosk" ]; then
            cp -r "$MODEL_SRC/vosk" config/includes.chroot/home/pilot/.cache/ai-distro/
            echo "  ✔ Vosk STT bundled"
        fi
    else
        echo "  ⚠ No cached models found at $MODEL_SRC — will download on first boot"
    fi
fi

# ── Build the ISO ────────────────────────────────────────────────────
echo "[6/6] Building ISO (this takes 10-30 minutes)..."
echo "  Coffee time ☕"
echo ""

lb build 2>&1 | tee "${SCRIPT_DIR}/build.log"

# ── Output ───────────────────────────────────────────────────────────
ISO_FILE=$(find . -maxdepth 1 -name "*.iso" -type f | head -1)
if [ -n "$ISO_FILE" ] && [ -f "$ISO_FILE" ]; then
    FINAL_ISO="${SCRIPT_DIR}/${ISO_NAME}.iso"
    mv "$ISO_FILE" "$FINAL_ISO"
    ISO_SIZE=$(du -h "$FINAL_ISO" | cut -f1)
    
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  ✔ ISO BUILD COMPLETE"
    echo "  File: $FINAL_ISO"
    echo "  Size: $ISO_SIZE"
    echo "═══════════════════════════════════════════════════"
    echo ""
    echo "  Flash to USB:"
    echo "    sudo dd if=$FINAL_ISO of=/dev/sdX bs=4M status=progress"
    echo ""
    echo "  Or use Balena Etcher, Ventoy, or Rufus."
    echo ""
    echo "  Boot → auto-login as 'pilot' → install.sh runs → ai-distro setup"
    echo "═══════════════════════════════════════════════════"
else
    echo ""
    echo "  ✗ ISO build failed. Check ${SCRIPT_DIR}/build.log"
    exit 1
fi
