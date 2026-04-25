#!/bin/sh
set -e

ROOT_DIR="/home/jmt3/AI_Distro"
RUST_DIR="$ROOT_DIR/src/rust"

cd "$RUST_DIR"

cargo build --release
