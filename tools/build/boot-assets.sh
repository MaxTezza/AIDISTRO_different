#!/bin/sh
set -e

# Boot asset generation scaffold
ROOT_DIR="/home/jmt3/AI_Distro"
ISO_DIR="$ROOT_DIR/build/iso"
BOOT_DIR="$ISO_DIR/boot"
EFI_DIR="$ISO_DIR/EFI/BOOT"
GRUB_DIR="$BOOT_DIR/grub"

mkdir -p "$GRUB_DIR/i386-pc" "$EFI_DIR"

# Embed a minimal GRUB config to find the real grub.cfg on the ISO.
cat > "$GRUB_DIR/grub-embed.cfg" <<'EOF'
search --no-floppy --set=root --file /boot/grub/grub.cfg
set prefix=($root)/boot/grub
configfile /boot/grub/grub.cfg
EOF

# Requires grub-pc-bin and grub-efi-amd64-bin
if command -v grub-mkimage >/dev/null 2>&1; then
  # BIOS El Torito image
  grub-mkimage \
    -O i386-pc-eltorito \
    -o "$GRUB_DIR/i386-pc/eltorito.img" \
    -c "$GRUB_DIR/grub-embed.cfg" \
    -p /boot/grub \
    biosdisk iso9660 normal linux configfile search

  # EFI bootloader
  grub-mkimage \
    -O x86_64-efi \
    -o "$EFI_DIR/BOOTX64.EFI" \
    -c "$GRUB_DIR/grub-embed.cfg" \
    -p /boot/grub \
    part_gpt part_msdos fat iso9660 normal linux configfile search
else
  echo "grub-mkimage not found. Install grub-pc-bin and grub-efi-amd64-bin." >&2
  exit 1
fi

echo "Boot assets generated under $ISO_DIR/boot and $ISO_DIR/EFI/BOOT"
