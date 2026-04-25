#!/bin/sh
set -e

ROOT_DIR="/home/jmt3/AI_Distro"
ISO="$ROOT_DIR/build/ai-distro.iso"

if [ ! -f "$ISO" ]; then
  echo "ISO not found: $ISO" >&2
  exit 1
fi

if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
  echo "qemu-system-x86_64 not found. Install qemu-system-x86." >&2
  exit 2
fi

qemu-system-x86_64 \
  -m 4096 \
  -smp 2 \
  -cdrom "$ISO" \
  -boot d \
  -display gtk \
  $(if [ -e /dev/kvm ] && [ -r /dev/kvm ] && [ -w /dev/kvm ]; then echo "-enable-kvm"; else echo "-accel tcg"; fi)
