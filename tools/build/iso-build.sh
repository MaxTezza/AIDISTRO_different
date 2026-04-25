#!/bin/sh
set -e

# Scaffolded ISO build script
# TODO: integrate with live-build or custom ISO pipeline

ROOT_DIR="/home/jmt3/AI_Distro"
ISO_DIR="$ROOT_DIR/build/iso"
CALAMARES_DIR="$ROOT_DIR/src/infra/installer/calamares"
BOOT_DIR="$ROOT_DIR/src/infra/boot"
LB_OUT="$ROOT_DIR/src/infra/rootfs/live-build"

rm -rf "$ISO_DIR"
mkdir -p "$ISO_DIR/calamares" "$ISO_DIR/branding" "$ISO_DIR/boot" "$ISO_DIR/rootfs" "$ISO_DIR/casper" "$ISO_DIR/.disk"

# Copy Calamares configs into ISO staging
cp -r "$CALAMARES_DIR"/conf "$ISO_DIR"/calamares/
cp -r "$CALAMARES_DIR"/modules "$ISO_DIR"/calamares/ 2>/dev/null || true
cp -r "$CALAMARES_DIR"/scripts "$ISO_DIR"/calamares/
cp -r "$CALAMARES_DIR"/branding "$ISO_DIR"/calamares/

# Copy rootfs artifact if present
if [ -f "$ROOT_DIR/build/rootfs/rootfs.squashfs" ]; then
  cp "$ROOT_DIR/build/rootfs/rootfs.squashfs" "$ISO_DIR/rootfs/"
fi

# Wire live-build outputs if present (kernel/initrd/squashfs)
VMLINUX=""
INITRD=""

# Prefer canonical casper location from live-build output.
if [ -z "$VMLINUX" ] && ls "$LB_OUT/chroot/binary/casper"/vmlinuz-* >/dev/null 2>&1; then
  VMLINUX="$(ls "$LB_OUT/chroot/binary/casper"/vmlinuz-* | head -n 1)"
fi
if [ -z "$INITRD" ] && ls "$LB_OUT/chroot/binary/casper"/initrd.img-* >/dev/null 2>&1; then
  INITRD="$(ls "$LB_OUT/chroot/binary/casper"/initrd.img-* | head -n 1)"
fi

# Fallback to boot artifacts in chroot if casper paths are unavailable.
if [ -z "$VMLINUX" ]; then
  VMLINUX="$(find "$LB_OUT/chroot/boot" -maxdepth 2 -type f -name 'vmlinuz-*' 2>/dev/null | head -n 1)"
fi
if [ -z "$INITRD" ]; then
  INITRD="$(find "$LB_OUT/chroot/boot" -maxdepth 2 -type f -name 'initrd.img-*' 2>/dev/null | head -n 1)"
fi

SQUASHFS=""
if [ -f "$LB_OUT/chroot/binary/casper/filesystem.squashfs" ]; then
  SQUASHFS="$LB_OUT/chroot/binary/casper/filesystem.squashfs"
else
  SQUASHFS="$(find "$LB_OUT" -maxdepth 8 -type f \( -name 'filesystem.squashfs' -o -name '*.squashfs' \) 2>/dev/null | head -n 1)"
fi

if [ -n "$VMLINUX" ]; then
  cp "$VMLINUX" "$ISO_DIR/casper/vmlinuz"
fi
if [ -n "$INITRD" ]; then
  cp "$INITRD" "$ISO_DIR/casper/initrd"
fi
if [ -n "$SQUASHFS" ]; then
  cp "$SQUASHFS" "$ISO_DIR/casper/filesystem.squashfs"
fi

# Copy live media metadata used by casper for medium discovery.
if [ -d "$LB_OUT/chroot/binary/.disk" ]; then
  cp -a "$LB_OUT/chroot/binary/.disk/." "$ISO_DIR/.disk/"
fi

# Copy boot assets if present
if [ -d "$BOOT_DIR/grub" ]; then
  mkdir -p "$ISO_DIR/boot/grub"
  cp -r "$BOOT_DIR/grub/"* "$ISO_DIR/boot/grub/" 2>/dev/null || true
fi

# Optionally generate boot assets if requested
if [ "${AI_DISTRO_BOOT_ASSETS:-0}" = "1" ]; then
  "$ROOT_DIR/tools/build/boot-assets.sh"
fi

cat > "$ISO_DIR/README.txt" <<'EOF'
AI Distro ISO staging directory

This is a scaffold for building a bootable ISO with Calamares.
Next steps:
- Generate rootfs squashfs and place at rootfs/rootfs.squashfs
- Add bootloader config in boot/
- Include Calamares package in the live environment
EOF

echo "Staged ISO build directory at $ISO_DIR"
