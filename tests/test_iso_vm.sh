#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# AI Distro — ISO VM Test Script
#
# Boots the ISO in a QEMU VM for installer validation.
# Tests: boot, live session, Calamares launch, and installed system.
#
# Usage:
#   ./test_iso_vm.sh path/to/ai-distro.iso
#   ./test_iso_vm.sh path/to/ai-distro.iso --headless
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

ISO="${1:?Usage: $0 <path-to-iso> [--headless]}"
HEADLESS="${2:-}"
VM_DISK="/tmp/ai-distro-test-disk.qcow2"
VM_RAM="4096"
VM_CPUS="2"
VM_DISK_SIZE="20G"

RED='\033[91m'
GREEN='\033[92m'
CYAN='\033[96m'
DIM='\033[2m'
RESET='\033[0m'

echo -e "${CYAN}AI Distro ISO VM Tester${RESET}"
echo -e "${DIM}════════════════════════════════════════${RESET}"

# Check dependencies
for cmd in qemu-system-x86_64 qemu-img; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}✗ Missing: $cmd${RESET}"
        echo "Install: sudo apt install qemu-system-x86 qemu-utils"
        exit 1
    fi
done

# Verify ISO exists
if [ ! -f "$ISO" ]; then
    echo -e "${RED}✗ ISO not found: $ISO${RESET}"
    exit 1
fi

echo -e "  ISO:  ${ISO}"
echo -e "  RAM:  ${VM_RAM}MB"
echo -e "  CPUs: ${VM_CPUS}"
echo -e "  Disk: ${VM_DISK_SIZE}"
echo ""

# Create virtual disk
echo -e "${DIM}Creating test disk...${RESET}"
qemu-img create -f qcow2 "$VM_DISK" "$VM_DISK_SIZE" >/dev/null 2>&1
echo -e "  ${GREEN}✔${RESET} Created $VM_DISK"

# Build QEMU args
QEMU_ARGS=(
    -m "$VM_RAM"
    -smp "$VM_CPUS"
    -cdrom "$ISO"
    -drive "file=${VM_DISK},format=qcow2,if=virtio"
    -boot d
    -enable-kvm
    -cpu host
    -net nic,model=virtio
    -net user,hostfwd=tcp::7841-:7841,hostfwd=tcp::7842-:7842
    -usb
    -device usb-tablet
    -device virtio-vga
    -device intel-hda
    -device hda-duplex
)

# UEFI if OVMF is available
OVMF_PATH="/usr/share/OVMF/OVMF_CODE.fd"
if [ -f "$OVMF_PATH" ]; then
    QEMU_ARGS+=(-bios "$OVMF_PATH")
    echo -e "  ${GREEN}✔${RESET} UEFI boot (OVMF)"
else
    echo -e "  ${DIM}○ Legacy BIOS boot (install ovmf for UEFI)${RESET}"
fi

# Headless mode
if [ "$HEADLESS" = "--headless" ]; then
    QEMU_ARGS+=(-nographic -serial mon:stdio)
    echo -e "  ${DIM}Running headless${RESET}"
else
    QEMU_ARGS+=(-display gtk)
fi

echo ""
echo -e "${CYAN}Launching VM...${RESET}"
echo -e "${DIM}Dashboard will be forwarded to localhost:7841${RESET}"
echo -e "${DIM}Marketplace forwarded to localhost:7842${RESET}"
echo -e "${DIM}Press Ctrl+C to stop${RESET}"
echo ""

qemu-system-x86_64 "${QEMU_ARGS[@]}"

# Cleanup
echo ""
echo -e "${DIM}Cleaning up test disk...${RESET}"
rm -f "$VM_DISK"
echo -e "${GREEN}✔ Done${RESET}"
