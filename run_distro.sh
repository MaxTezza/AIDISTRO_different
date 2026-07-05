#!/bin/bash
set -e

echo "=== Mnemonic OS / AI Distro Container Launcher ==="

# Check for docker
if ! command -v docker &> /dev/null; then
    echo "Error: docker is not installed. Please install Docker and try again."
    exit 1
fi

# Stop and remove existing container if running
if [ "$(docker ps -aq -f name=ai-distro)" ]; then
    echo "Stopping and removing existing container..."
    docker rm -f ai-distro >/dev/null
fi

# Build image
echo "Building Docker image (this may take a few minutes)..."
docker build -t ai-distro:latest .

# Setup host volume directory on the spacious /home partition
VOLUME_DIR="/home/jmt3/.config/ai-distro"
echo "Setting up persistent host configuration directory at $VOLUME_DIR..."
mkdir -p "$VOLUME_DIR"
chmod 777 "$VOLUME_DIR"

# Run container
echo "Launching container..."
docker run -d \
  --name ai-distro \
  -p 17842:17842 \
  -v "$VOLUME_DIR":/var/lib/ai-distro \
  --restart unless-stopped \
  ai-distro:latest

echo ""
echo "=== Success! ==="
echo "Mnemonic OS Shell is now running in Docker!"
echo "Access it in your browser here: http://localhost:17842"
echo ""
echo "To view logs, run: docker logs -f ai-distro"
echo "To stop the container, run: docker stop ai-distro"
