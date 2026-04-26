# --- Build Rust Stage ---
FROM rust:slim-bookworm AS builder

WORKDIR /usr/src/ai-distro
COPY src/rust src/rust
RUN apt-get update && apt-get install -y \
    pkg-config libssl-dev \
    libasound2-dev \
    libwayland-dev libxkbcommon-dev libegl1-mesa-dev libgbm-dev \
    libdbus-1-dev libfontconfig1-dev \
    && cargo build --release --manifest-path src/rust/Cargo.toml

# --- Final Image Stage ---
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    xdg-utils \
    pulseaudio-utils \
    brightnessctl \
    network-manager \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r aidistro && useradd -r -g aidistro aidistro

WORKDIR /app

# Copy binary from builder
COPY --from=builder /usr/src/ai-distro/src/rust/target/release/ai-distro-agent /usr/local/bin/

# Copy python tools and skill manifests
COPY tools /app/tools
COPY src/skills /app/skills
COPY configs /etc/ai-distro
COPY requirements.txt /app/

# Install dependencies and download model
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    python3-dev \
    libdbus-1-dev \
    libglib2.0-dev \
    libcairo2-dev \
    libgirepository1.0-dev \
    gobject-introspection \
    meson \
    ninja-build \
    portaudio19-dev \
    libasound2-dev \
    && pip3 install --upgrade pip setuptools wheel meson-python meson ninja --break-system-packages \
    && pip3 install pycairo --break-system-packages \
    && pip3 install -r /app/requirements.txt --break-system-packages \
    && apt-get remove -y build-essential cmake pkg-config python3-dev libdbus-1-dev libglib2.0-dev libcairo2-dev libgirepository1.0-dev gobject-introspection meson ninja-build portaudio19-dev libasound2-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
# Download model (optional in CI - will download on first run if skipped)
RUN python3 /app/tools/agent/download_model.py || echo "Model download skipped (will download on first run)"

# Set default env
ENV AI_DISTRO_IPC_SOCKET=/tmp/ai-distro-agent.sock
ENV AI_DISTRO_MEMORY_DIR=/var/lib/ai-distro/memory
ENV AI_DISTRO_CONFIRM_DIR=/var/lib/ai-distro/confirmations
ENV AI_DISTRO_INTENT_PARSER=/app/tools/agent/intent_parser.py
ENV AI_DISTRO_BRAIN=/app/tools/agent/brain.py
ENV AI_DISTRO_SKILLS_DIR=/app/skills/core

RUN mkdir -p /var/lib/ai-distro/memory /var/lib/ai-distro/confirmations && \
    chown -R aidistro:aidistro /var/lib/ai-distro /app

USER aidistro

ENTRYPOINT ["ai-distro-agent"]
