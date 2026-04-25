#!/bin/sh
set -e

# RootFS build scaffold (Debian/Ubuntu base)
ROOT_DIR="/home/jmt3/AI_Distro"
OUT_DIR="$ROOT_DIR/build/rootfs"
LB_DIR="$ROOT_DIR/src/infra/rootfs/live-build"
PKG_SRC="$ROOT_DIR/build"
PKG_DST="$LB_DIR/config/includes.chroot/ai-distro-packages"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# Run live-build if available
if command -v lb >/dev/null 2>&1; then
  if [ -d "$PKG_SRC" ]; then
    mkdir -p "$PKG_DST"
    cp "$PKG_SRC"/mnemonicos*.deb "$PKG_DST"/ 2>/dev/null || true
  fi
  (cd "$LB_DIR" && sudo lb clean && sudo lb config && sudo lb build)
  SQUASHFS="$(find "$LB_DIR" -maxdepth 3 -type f -name '*.squashfs' | head -n 1)"
  if [ -n "$SQUASHFS" ]; then
    cp "$SQUASHFS" "$OUT_DIR/rootfs.squashfs"
  else
    echo "Warning: no squashfs found under $LB_DIR" >&2
  fi
else
  cat > "$OUT_DIR/README.txt" <<'EOS'
RootFS build output (scaffold)

Next steps:
- Install live-build: sudo apt install live-build
- Run: sudo lb clean && sudo lb config && sudo lb build
- Extract rootfs squashfs to build/rootfs/rootfs.squashfs
EOS
fi

echo "RootFS build step complete. Output at $OUT_DIR"
