#!/bin/sh
set -e

ROOT_DIR="/home/jmt3/AI_Distro"
PKG_DIR="$ROOT_DIR/src/infra/packaging/deb"
BUILD_SRC="$ROOT_DIR/build/deb-src"
STAGE_ROOT="$ROOT_DIR/build/deb-root"

# Stage files first
"$ROOT_DIR/tools/build/stage-deb.sh" "$STAGE_ROOT"

# Prepare a minimal source tree for dpkg-buildpackage
rm -rf "$BUILD_SRC"
mkdir -p "$BUILD_SRC"
cp -r "$PKG_DIR/debian" "$BUILD_SRC/debian"

# Copy runtime assets referenced by debian/*.install
mkdir -p "$BUILD_SRC/configs" "$BUILD_SRC/assets" "$BUILD_SRC/src/infra/packaging/deb"
cp -r "$ROOT_DIR/configs" "$BUILD_SRC/"
cp -r "$ROOT_DIR/assets" "$BUILD_SRC/"
cp -r "$ROOT_DIR/src/infra/packaging/deb/logrotate" "$BUILD_SRC/src/infra/packaging/deb/"

# Add a minimal source file so the package isn't empty
cat > "$BUILD_SRC/README.md" <<'EOS'
# AI Distro (Debian Package)

This is a scaffolded source tree used to build a native Debian package.
EOS

# Copy staged root into the build tree for dh_install paths
mkdir -p "$BUILD_SRC/build"
cp -r "$STAGE_ROOT" "$BUILD_SRC/build/deb-root"

cd "$BUILD_SRC"

# Build a native package from the scaffolded source tree

dpkg-buildpackage -b -us -uc
