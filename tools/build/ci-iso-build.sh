#!/bin/bash
set -euo pipefail

# CI ISO Build Script
# Builds a bootable AI Distro ISO for releases

ROOT_DIR="${CI_PROJECT_DIR:-$(pwd)}"
BUILD_DIR="$ROOT_DIR/build"
RELEASE_DIR="$ROOT_DIR/release"
ISO_NAME="AI-Distro-${CI_COMMIT_TAG:-dev}.iso"

echo "=== AI Distro ISO Build ==="
echo "Root: $ROOT_DIR"
echo "Target: $ISO_NAME"

# Ensure build directories
mkdir -p "$BUILD_DIR" "$RELEASE_DIR"

# Build Rust components
echo "[1/4] Building Rust agent..."
cd "$ROOT_DIR/src/rust"
cargo build --release --all

mkdir -p "$BUILD_DIR/deb-root/usr/bin"
for bin in ai-distro-agent ai-distro-core ai-distro-voice; do
  if [ -f "target/release/$bin" ]; then
    cp "target/release/$bin" "$BUILD_DIR/deb-root/usr/bin/"
    echo "  + $bin"
  fi
done

# Build Python wheel
echo "[2/4] Building Python package..."
cd "$ROOT_DIR"
if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
  pip wheel . --no-deps -w "$BUILD_DIR/wheels/" 2>/dev/null || echo "  (Python wheel skipped)"
fi

# Stage ISO contents
echo "[3/4] Staging ISO contents..."
ISO_STAGING="$BUILD_DIR/iso-staging"
rm -rf "$ISO_STAGING"
mkdir -p "$ISO_STAGING"/{casper,.disk,boot/grub,usr/bin,usr/lib/ai-distro}

# Copy binaries
cp -r "$BUILD_DIR/deb-root/usr/bin/"* "$ISO_STAGING/usr/bin/" 2>/dev/null || true

# Copy Python tools
mkdir -p "$ISO_STAGING/usr/lib/ai-distro/tools"
cp -r "$ROOT_DIR/tools/agent" "$ISO_STAGING/usr/lib/ai-distro/tools/" 2>/dev/null || true
cp -r "$ROOT_DIR/tools/shell" "$ISO_STAGING/usr/lib/ai-distro/tools/" 2>/dev/null || true

# Copy configs
mkdir -p "$ISO_STAGING/etc/ai-distro"
cp -r "$ROOT_DIR/configs/"* "$ISO_STAGING/etc/ai-distro/" 2>/dev/null || true

# Copy UI assets
mkdir -p "$ISO_STAGING/usr/share/ai-distro/ui"
cp -r "$ROOT_DIR/assets/ui/shell" "$ISO_STAGING/usr/share/ai-distro/ui/" 2>/dev/null || true

# Generate minimal squashfs (for testing)
echo "[4/4] Creating ISO..."
if command -v mksquashfs &>/dev/null; then
  mksquashfs "$ISO_STAGING" "$BUILD_DIR/filesystem.squashfs" -noappend -comp xz
  mv "$BUILD_DIR/filesystem.squashfs" "$ISO_STAGING/casper/"
fi

# Create .disk info
echo "AI Distro $CI_COMMIT_TAG" > "$ISO_STAGING/.disk/info"
echo "AI Distro Live System" > "$ISO_STAGING/.disk/base_installable"
date -u +%Y-%m-%d-%H:%M > "$ISO_STAGING/.disk/mkfs"

# Generate ISO
if command -v genisoimage &>/dev/null || command -v xorriso &>/dev/null; then
  cd "$BUILD_DIR"
  if command -v xorriso &>/dev/null; then
    xorriso -as mkisofs \
      -o "$RELEASE_DIR/$ISO_NAME" \
      -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
      -c boot/isolinux/boot.cat \
      -b boot/isolinux/isolinux.bin \
      -no-emul-boot \
      -boot-load-size 4 \
      -boot-info-table \
      -V "AI Distro" \
      "$ISO_STAGING" || { echo "ERROR: xorriso ISO creation failed"; }
  elif command -v genisoimage &>/dev/null; then
    genisoimage -o "$RELEASE_DIR/$ISO_NAME" \
      -V "AI Distro" \
      -J -R \
      "$ISO_STAGING" || { echo "ERROR: genisoimage ISO creation failed"; }
  fi
fi

# Verify ISO was created
if [ ! -f "$RELEASE_DIR/$ISO_NAME" ]; then
  echo "ERROR: ISO build failed. Required tools (xorriso or genisoimage) are missing or the build encountered errors."
  echo "Install with: sudo apt-get install xorriso isolinux"
  exit 1
fi

echo "=== Build Complete ==="
echo "ISO: $RELEASE_DIR/$ISO_NAME"
ls -lh "$RELEASE_DIR/$ISO_NAME"