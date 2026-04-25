#!/bin/sh
set -e

# ISO assembly scaffold (xorriso/mkisofs)
ROOT_DIR="/home/jmt3/AI_Distro"
ISO_DIR="$ROOT_DIR/build/iso"
OUT_ISO="$ROOT_DIR/build/ai-distro.iso"

if [ ! -d "$ISO_DIR" ]; then
  echo "ISO staging dir missing. Run tools/build/iso-build.sh first." >&2
  exit 1
fi

if ! command -v xorriso >/dev/null 2>&1; then
  echo "xorriso not found. Install it to build the ISO." >&2
  exit 2
fi

BIOS_IMG="$ISO_DIR/boot/grub/i386-pc/eltorito.img"
EFI_IMG="$ISO_DIR/EFI/BOOT/BOOTX64.EFI"

if [ -f "$BIOS_IMG" ] || [ -f "$EFI_IMG" ]; then
  BIOS_FLAGS=""
  EFI_FLAGS=""
  if [ -f "$BIOS_IMG" ]; then
    BIOS_FLAGS="-eltorito-boot boot/grub/i386-pc/eltorito.img -no-emul-boot -boot-load-size 4 -boot-info-table"
  fi
  if [ -f "$EFI_IMG" ]; then
    EFI_FLAGS="-eltorito-alt-boot -e EFI/BOOT/BOOTX64.EFI -no-emul-boot"
  fi

  # ISO with BIOS/UEFI boot flags when assets are present
  xorriso -as mkisofs \
    -o "$OUT_ISO" \
    -V "AI_DISTRO" \
    -J -R \
    $BIOS_FLAGS \
    $EFI_FLAGS \
    "$ISO_DIR"
else
  echo "Warning: no BIOS/UEFI boot assets found. Building non-bootable ISO." >&2
  xorriso -as mkisofs \
    -o "$OUT_ISO" \
    -V "AI_DISTRO" \
    -J -R \
    "$ISO_DIR"
fi

echo "ISO built at $OUT_ISO"
