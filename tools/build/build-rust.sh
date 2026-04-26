#!/bin/sh
set -e

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RUST_DIR="$ROOT_DIR/src/rust"

cd "$RUST_DIR"

cargo build --release
