#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  AI DISTRO FORGE: Complete ISO Builder
#  Builds a bootable Debian Bookworm live ISO with AI Distro preinstalled
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="${BUILD_DIR:-/tmp/ai-distro-live}"
ISO_NAME="ai-distro-live-$(date +%Y%m%d).iso"

echo "═══════════════════════════════════════════════"
echo "  AI DISTRO FORGE: Building the Future"
echo "  Source:  $ROOT_DIR"
echo "  Build:   $BUILD_DIR"
echo "  Output:  $BUILD_DIR/$ISO_NAME"
echo "═══════════════════════════════════════════════"

# ── 1. Prerequisites ─────────────────────────────────────────────
echo "[1/8] Installing build tools..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    live-build debootstrap xorriso squashfs-tools \
    syslinux syslinux-utils isolinux grub-efi-amd64-bin \
    mtools dosfstools

# ── 2. Initialize live-build workspace ───────────────────────────
echo "[2/8] Initializing live-build workspace..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

lb config \
    --binary-images iso-hybrid \
    --mode debian \
    --architectures amd64 \
    --distribution bookworm \
    --debian-installer none \
    --bootappend-live "boot=live components locales=en_US.UTF-8 keyboard-layouts=us" \
    --iso-application "AI Distro" \
    --iso-volume "AI_DISTRO_LIVE" \
    --memtest none \
    --security true \
    --updates true

# ── 3. Package Lists ─────────────────────────────────────────────
echo "[3/8] Configuring package lists..."
mkdir -p config/package-lists

cat > config/package-lists/system.list.chroot << 'EOF'
# Kernel & Boot
linux-image-amd64
live-boot
live-config
systemd-sysv
sudo
locales

# Desktop Environment (Sway — lightweight Wayland)
sway
swayidle
swaylock
waybar
foot
wmenu
wl-clipboard
xwayland
grim
slurp
mako-notifier

# Audio
pipewire
pipewire-audio
pipewire-alsa
pipewire-pulse
wireplumber

# Networking
network-manager
network-manager-gnome
bluez
bluez-tools
wpasupplicant

# Utilities
curl
wget
git
htop
neofetch
unzip
file
man-db
less
vim
EOF

cat > config/package-lists/ai-distro.list.chroot << 'EOF'
# AI Distro Dependencies
python3
python3-pip
python3-venv
python3-gi
python3-dbus
python3-dev
build-essential
pkg-config
libdbus-1-dev

# Vision & OCR
tesseract-ocr
scrot

# Accessibility (AT-SPI)
at-spi2-core
libatspi2.0-dev
gir1.2-atspi-2.0

# Media
mpv
feh
espeak-ng

# Hardware monitoring
udev
upower
udisks2

# Browser engine (for web navigator)
# Note: Chromium pulled via playwright in venv
EOF

# ── 4. Hooks (run inside chroot during build) ────────────────────
echo "[4/8] Creating build hooks..."
mkdir -p config/hooks/normal

cat > config/hooks/normal/0100-ai-distro-setup.hook.chroot << 'HOOKEOF'
#!/bin/bash
set -e

# Create the ai-distro user
if ! id "pilot" &>/dev/null; then
    useradd -m -s /bin/bash -G sudo,audio,video,bluetooth,netdev,input pilot
    echo "pilot:aidistro" | chpasswd
    echo "pilot ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/pilot
fi

# Enable auto-login via getty override
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/override.conf << 'GETTY'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pilot --noclear %I $TERM
Type=idle
GETTY

# Generate locale
sed -i 's/# en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen
locale-gen

# Enable NetworkManager
systemctl enable NetworkManager 2>/dev/null || true
HOOKEOF
chmod +x config/hooks/normal/0100-ai-distro-setup.hook.chroot

# ── 5. Inject AI Distro source tree ─────────────────────────────
echo "[5/8] Injecting AI Distro core..."

SKEL_DIR="config/includes.chroot/home/pilot/AI_Distro"
mkdir -p "$SKEL_DIR"

# Copy source (excluding build artifacts and git)
rsync -a --exclude='.git' \
         --exclude='target/' \
         --exclude='__pycache__' \
         --exclude='.venv' \
         --exclude='*.pyc' \
         "$ROOT_DIR/" "$SKEL_DIR/"

# Copy pre-built Rust binaries if available
RELEASE_DIR="$ROOT_DIR/src/rust/target/release"
if [ -f "$RELEASE_DIR/ai-distro-agent" ]; then
    BINDIR="config/includes.chroot/usr/local/bin"
    mkdir -p "$BINDIR"
    for bin in ai-distro-agent ai-distro-cli ai-distro-core ai-distro-hud ai-distro-voice; do
        if [ -f "$RELEASE_DIR/$bin" ]; then
            cp "$RELEASE_DIR/$bin" "$BINDIR/"
            echo "  ✔ Injected $bin"
        fi
    done
fi

# Create symlink for the CLI
mkdir -p config/includes.chroot/usr/local/bin
cat > config/includes.chroot/usr/local/bin/ai-distro << 'CLISCRIPT'
#!/bin/bash
exec /usr/local/bin/ai-distro-cli "$@"
CLISCRIPT
chmod +x config/includes.chroot/usr/local/bin/ai-distro

# Copy branding assets
BRANDING_SRC="$ROOT_DIR/assets/branding"
if [ -d "$BRANDING_SRC" ]; then
    mkdir -p "config/includes.chroot/home/pilot/.local/share/wallpapers"
    cp -f "$BRANDING_SRC/wallpaper.png" \
        "config/includes.chroot/home/pilot/.local/share/wallpapers/ai-distro.png" 2>/dev/null || true
    echo "  ✔ Injected branding assets"
fi

# ── 6. Sway Autostart Configuration ─────────────────────────────
echo "[6/8] Configuring Sway desktop..."

SWAY_CONFIG="config/includes.chroot/home/pilot/.config/sway/config"
mkdir -p "$(dirname "$SWAY_CONFIG")"
cat > "$SWAY_CONFIG" << 'SWAYEOF'
# AI Distro — Sway Config
set $mod Mod4

# Basics
bindsym $mod+Return exec foot
bindsym $mod+d exec wmenu-run
bindsym $mod+Shift+q kill
bindsym $mod+Shift+e exec swaymsg exit

# Window Management
bindsym $mod+Left focus left
bindsym $mod+Right focus right
bindsym $mod+Up focus up
bindsym $mod+Down focus down
bindsym $mod+Shift+Left move left
bindsym $mod+Shift+Right move right
bindsym $mod+f fullscreen toggle
bindsym $mod+space floating toggle

# Workspaces
bindsym $mod+1 workspace 1
bindsym $mod+2 workspace 2
bindsym $mod+3 workspace 3
bindsym $mod+Shift+1 move container to workspace 1
bindsym $mod+Shift+2 move container to workspace 2
bindsym $mod+Shift+3 move container to workspace 3

# Screenshots
bindsym Print exec grim ~/Pictures/screenshot-$(date +%s).png
bindsym $mod+Print exec grim -g "$(slurp)" ~/Pictures/screenshot-$(date +%s).png

# Status Bar
bar {
    swaybar_command waybar
}

# Appearance
default_border pixel 2
gaps inner 8
gaps outer 4
client.focused #7c3aed #7c3aed #ffffff #7c3aed #7c3aed
client.unfocused #1e1e2e #1e1e2e #888888 #1e1e2e #1e1e2e

# Wallpaper
output * bg ~/.local/share/wallpapers/ai-distro.png fill

# AI Distro: Auto-start the stack
exec_always {
    systemctl --user daemon-reload
    ai-distro start
}

# Input
input type:keyboard {
    xkb_layout us
}
SWAYEOF

# Waybar config for status display
WAYBAR_DIR="config/includes.chroot/home/pilot/.config/waybar"
mkdir -p "$WAYBAR_DIR"
cat > "$WAYBAR_DIR/config" << 'WAYBAREOF'
{
    "layer": "top",
    "position": "top",
    "height": 30,
    "modules-left": ["sway/workspaces", "sway/mode"],
    "modules-center": ["clock"],
    "modules-right": ["pulseaudio", "network", "battery", "tray"],
    "clock": {
        "format": "{:%a %b %d  %H:%M}",
        "tooltip-format": "<big>{:%Y %B}</big>\n<tt>{calendar}</tt>"
    },
    "battery": {
        "format": "{icon} {capacity}%",
        "format-icons": ["", "", "", "", ""],
        "format-charging": " {capacity}%"
    },
    "network": {
        "format-wifi": " {essid}",
        "format-ethernet": " {ifname}",
        "format-disconnected": " Disconnected"
    },
    "pulseaudio": {
        "format": "{icon} {volume}%",
        "format-muted": " Muted",
        "format-icons": {"default": ["", "", ""]}
    }
}
WAYBAREOF

cat > "$WAYBAR_DIR/style.css" << 'WAYBARCSS'
* {
    font-family: "JetBrains Mono", "Noto Sans", monospace;
    font-size: 13px;
    color: #cdd6f4;
}
window#waybar {
    background: rgba(15, 15, 35, 0.92);
    border-bottom: 2px solid #7c3aed;
}
#workspaces button {
    padding: 0 6px;
    color: #888;
    border-bottom: 2px solid transparent;
}
#workspaces button.focused {
    color: #fff;
    border-bottom: 2px solid #7c3aed;
}
#clock, #battery, #network, #pulseaudio {
    padding: 0 10px;
}
#battery.charging { color: #a6e3a1; }
#battery.warning { color: #fab387; }
#battery.critical { color: #f38ba8; }
WAYBARCSS

# Auto-start sway on login
PROFILE_DIR="config/includes.chroot/home/pilot"
cat >> "$PROFILE_DIR/.bash_profile" << 'BASHPROF'
# Auto-start Sway on tty1
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    export XDG_CURRENT_DESKTOP=sway
    export MOZ_ENABLE_WAYLAND=1
    exec sway
fi
BASHPROF

# ── 7. Systemd User Services ────────────────────────────────────
echo "[7/8] Installing systemd user services..."

SYSTEMD_DIR="config/includes.chroot/home/pilot/.config/systemd/user"
mkdir -p "$SYSTEMD_DIR"

# Copy services from the install.sh template (or generate fresh)
for svc in agent voice hud curator spirit healer hardware; do
    SERVICE_NAME="ai-distro-${svc}"
    UNIT_FILE="$SYSTEMD_DIR/${SERVICE_NAME}.service"

    case $svc in
        agent)
            cat > "$UNIT_FILE" << SVCEOF
[Unit]
Description=AI Distro Agent — Brain & Action Engine
After=default.target

[Service]
Type=simple
ExecStart=/usr/local/bin/ai-distro-agent
Restart=always
RestartSec=5
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
Environment=AI_DISTRO_TOOLS_DIR=/home/pilot/AI_Distro/tools/agent
Environment=AI_DISTRO_CONFIG=/etc/ai-distro/agent.json
RuntimeDirectory=ai-distro

[Install]
WantedBy=default.target
SVCEOF
            ;;
        voice)
            cat > "$UNIT_FILE" << SVCEOF
[Unit]
Description=AI Distro Voice — Piper TTS & ASR Pipeline
After=ai-distro-agent.service sound.target
Requires=ai-distro-agent.service

[Service]
Type=simple
ExecStart=/usr/local/bin/ai-distro-voice
Restart=on-failure
RestartSec=5
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock

[Install]
WantedBy=default.target
SVCEOF
            ;;
        hud)
            cat > "$UNIT_FILE" << SVCEOF
[Unit]
Description=AI Distro HUD — Desktop Overlay
After=ai-distro-agent.service graphical-session.target

[Service]
Type=simple
ExecStart=/usr/local/bin/ai-distro-hud
Restart=on-failure
RestartSec=5
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock

[Install]
WantedBy=default.target
SVCEOF
            ;;
        curator)
            cat > "$UNIT_FILE" << SVCEOF
[Unit]
Description=AI Distro Curator — Bayesian Proactive Intelligence
After=ai-distro-agent.service

[Service]
Type=simple
ExecStart=/home/pilot/AI_Distro/.venv/bin/python3 /home/pilot/AI_Distro/tools/agent/curator.py
Restart=on-failure
RestartSec=15
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
WorkingDirectory=/home/pilot/AI_Distro

[Install]
WantedBy=default.target
SVCEOF
            ;;
        spirit)
            cat > "$UNIT_FILE" << SVCEOF
[Unit]
Description=AI Distro Spirit Bridge — Telegram Remote Control
After=ai-distro-agent.service network-online.target

[Service]
Type=simple
ExecStart=/home/pilot/AI_Distro/.venv/bin/python3 /home/pilot/AI_Distro/tools/agent/spirit_bridge.py
Restart=on-failure
RestartSec=10
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
WorkingDirectory=/home/pilot/AI_Distro

[Install]
WantedBy=default.target
SVCEOF
            ;;
        healer)
            cat > "$UNIT_FILE" << SVCEOF
[Unit]
Description=AI Distro Healer — Autonomous System Repair
After=ai-distro-agent.service

[Service]
Type=simple
ExecStart=/home/pilot/AI_Distro/.venv/bin/python3 /home/pilot/AI_Distro/tools/agent/system_healer.py
Restart=on-failure
RestartSec=30
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
WorkingDirectory=/home/pilot/AI_Distro

[Install]
WantedBy=default.target
SVCEOF
            ;;
        hardware)
            cat > "$UNIT_FILE" << SVCEOF
[Unit]
Description=AI Distro Hardware — Digital Nervous System (D-Bus)
After=ai-distro-agent.service

[Service]
Type=simple
ExecStart=/home/pilot/AI_Distro/.venv/bin/python3 /home/pilot/AI_Distro/tools/agent/hardware_events.py
Restart=on-failure
RestartSec=10
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
WorkingDirectory=/home/pilot/AI_Distro

[Install]
WantedBy=default.target
SVCEOF
            ;;
    esac
    echo "  ✔ Created $SERVICE_NAME.service"
done

# Additional Python services: wake word, event bus, dashboard
for extra_svc in wakeword eventbus dashboard; do
    case $extra_svc in
        wakeword)
            cat > "$SYSTEMD_DIR/ai-distro-wakeword.service" << SVCEOF
[Unit]
Description=AI Distro Wake Word — Hands-Free Activation
After=ai-distro-voice.service sound.target

[Service]
Type=simple
ExecStart=/home/pilot/AI_Distro/.venv/bin/python3 /home/pilot/AI_Distro/tools/agent/wake_word_engine.py
Restart=on-failure
RestartSec=10
WorkingDirectory=/home/pilot/AI_Distro

[Install]
WantedBy=default.target
SVCEOF
            ;;
        eventbus)
            cat > "$SYSTEMD_DIR/ai-distro-eventbus.service" << SVCEOF
[Unit]
Description=AI Distro Event Bus — Unified Notification System
Before=ai-distro-healer.service ai-distro-curator.service

[Service]
Type=simple
ExecStart=/home/pilot/AI_Distro/.venv/bin/python3 /home/pilot/AI_Distro/tools/agent/event_bus.py
Restart=always
RestartSec=3
WorkingDirectory=/home/pilot/AI_Distro

[Install]
WantedBy=default.target
SVCEOF
            ;;
        dashboard)
            cat > "$SYSTEMD_DIR/ai-distro-dashboard.service" << SVCEOF
[Unit]
Description=AI Distro Dashboard — Web Command Center (port 7841)
After=ai-distro-agent.service

[Service]
Type=simple
ExecStart=/home/pilot/AI_Distro/.venv/bin/python3 /home/pilot/AI_Distro/tools/agent/dashboard.py
Restart=on-failure
RestartSec=5
Environment=AI_DISTRO_IPC_SOCKET=%t/ai-distro/agent.sock
WorkingDirectory=/home/pilot/AI_Distro

[Install]
WantedBy=default.target
SVCEOF
            ;;
    esac
    echo "  ✔ Created ai-distro-${extra_svc}.service"
done

# ── 8. GRUB / Boot Configuration ────────────────────────────────
echo "[8/8] Configuring bootloader..."

mkdir -p config/includes.binary/boot/grub

# Copy splash screen if available
if [ -f "$ROOT_DIR/assets/branding/grub-splash.png" ]; then
    cp "$ROOT_DIR/assets/branding/grub-splash.png" config/includes.binary/boot/grub/splash.png
    echo "  ✔ Injected GRUB splash screen"
fi

cat > config/includes.binary/boot/grub/grub.cfg << 'GRUBEOF'
set default=0
set timeout=5

insmod all_video
insmod gfxterm
insmod png
set gfxmode=auto
terminal_output gfxterm

# Splash screen
if [ -f /boot/grub/splash.png ]; then
    background_image /boot/grub/splash.png
fi

set color_normal=light-gray/black
set color_highlight=white/dark-gray

menuentry "AI Distro — Boot Live System" {
    linux /live/vmlinuz boot=live components locales=en_US.UTF-8 keyboard-layouts=us quiet splash
    initrd /live/initrd.img
}

menuentry "AI Distro — Safe Mode (nomodeset)" {
    linux /live/vmlinuz boot=live components nomodeset locales=en_US.UTF-8
    initrd /live/initrd.img
}

menuentry "AI Distro — RAM Session (copy to RAM)" {
    linux /live/vmlinuz boot=live components toram locales=en_US.UTF-8
    initrd /live/initrd.img
}
GRUBEOF

# Fix file ownership in the chroot overlay
cat > config/hooks/normal/9999-fix-perms.hook.chroot << 'PERMEOF'
#!/bin/bash
if id pilot &>/dev/null; then
    chown -R pilot:pilot /home/pilot/ 2>/dev/null || true
fi
PERMEOF
chmod +x config/hooks/normal/9999-fix-perms.hook.chroot

# ── Build ────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "  Configuration complete!"
echo ""
echo "  To build the ISO:"
echo "    cd $BUILD_DIR"
echo "    sudo lb build 2>&1 | tee build.log"
echo ""
echo "  The ISO will be at:"
echo "    $BUILD_DIR/live-image-amd64.hybrid.iso"
echo ""
echo "  To test in a VM:"
echo "    qemu-system-x86_64 -m 4G -cdrom live-image-amd64.hybrid.iso -enable-kvm"
echo "═══════════════════════════════════════════════"
