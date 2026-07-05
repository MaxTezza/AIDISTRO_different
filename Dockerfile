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

# Copy binaries from builder early
COPY --from=builder /usr/src/ai-distro/src/rust/target/release/ai-distro-agent /usr/local/bin/
COPY --from=builder /usr/src/ai-distro/src/rust/target/release/ai-distro-core /usr/local/bin/

# Copy only config files and requirements for pip / model download caching
COPY requirements.txt /app/
COPY configs/agent.json /etc/ai-distro/agent.json
COPY tools/agent/download_model.py /app/tools/agent/download_model.py

# Install dependencies
RUN apt-get update -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false && apt-get install -y \
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

# Setup model configuration environment
ENV AI_DISTRO_CONFIG=/etc/ai-distro/agent.json
ENV AI_DISTRO_MODEL_DIR=/var/lib/ai-distro/models

# Copy the rest of the changing source files (tools, assets, skills, entrypoint)
COPY tools /app/tools
COPY assets /app/assets
COPY entrypoint.sh /app/entrypoint.sh
COPY src/skills /app/skills
COPY configs /etc/ai-distro

# Set default env
ENV AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock
ENV AI_DISTRO_CORE_SOCKET=/tmp/ai-core.sock
ENV AI_DISTRO_CORE_STATE_DB=/tmp/ai-core-state.db
ENV AI_DISTRO_CORE_CONTEXT_DIR=/tmp/ai-core-context
ENV AI_DISTRO_SHELL_STATIC_DIR=/app/assets/ui/shell
ENV AI_DISTRO_SHELL_HOST=0.0.0.0
ENV AI_DISTRO_MEMORY_DIR=/var/lib/ai-distro/memory
ENV AI_DISTRO_CONFIRM_DIR=/var/lib/ai-distro/confirmations
ENV AI_DISTRO_INTENT_PARSER=/app/tools/agent/intent_parser.py
ENV AI_DISTRO_BRAIN=/app/tools/agent/brain.py
ENV AI_DISTRO_SKILLS_DIR=/app/skills/core
ENV AI_DISTRO_MODEL_DIR=/var/lib/ai-distro/models

RUN mkdir -p /var/lib/ai-distro/memory /var/lib/ai-distro/confirmations /var/lib/ai-distro/models && \
    chown -R aidistro:aidistro /var/lib/ai-distro /etc/ai-distro /app

USER aidistro

ENTRYPOINT ["/app/entrypoint.sh"]
