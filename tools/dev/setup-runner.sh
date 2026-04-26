#!/bin/bash
set -euo pipefail

# AI Distro — Local GitLab Runner Setup
# Usage: bash tools/dev/setup-runner.sh <registration-token>
#
# Get your token from:
#   GitLab → AI_Distro → Settings → CI/CD → Runners → New project runner
#   The token starts with "glrt-"

RUNNER_BIN="$HOME/.local/bin/gitlab-runner"
CONFIG_DIR="$HOME/.gitlab-runner"
GITLAB_URL="https://gitlab.com"

if [ $# -lt 1 ]; then
    echo "Usage: bash $0 <registration-token>"
    echo ""
    echo "Get your token from:"
    echo "  1. Go to https://gitlab.com/maxtezza29464/ai_distro/-/settings/ci_cd"
    echo "  2. Expand 'Runners'"
    echo "  3. Click 'New project runner'"
    echo "  4. Select 'Linux' as the OS"
    echo "  5. Copy the token (starts with glrt-)"
    exit 1
fi

TOKEN="$1"

if ! command -v "$RUNNER_BIN" &>/dev/null; then
    echo "GitLab Runner not found at $RUNNER_BIN"
    echo "Download it first:"
    echo '  curl -L --output ~/.local/bin/gitlab-runner "https://s3.dualstack.us-east-1.amazonaws.com/gitlab-runner-downloads/latest/binaries/gitlab-runner-linux-amd64"'
    echo '  chmod +x ~/.local/bin/gitlab-runner'
    exit 1
fi

mkdir -p "$CONFIG_DIR"

echo "=== Registering GitLab Runner ==="
"$RUNNER_BIN" register \
    --non-interactive \
    --url "$GITLAB_URL" \
    --token "$TOKEN" \
    --executor "shell" \
    --config "$CONFIG_DIR/config.toml" \
    --description "ai-distro-local-$(hostname)" \
    --tag-list "local,shell,linux"

echo ""
echo "=== Runner Registered ==="
echo ""
echo "To start the runner:"
echo "  gitlab-runner run --config $CONFIG_DIR/config.toml"
echo ""
echo "To install as a user-level systemd service (auto-start on boot):"
echo "  gitlab-runner install --user $(whoami) --config $CONFIG_DIR/config.toml --working-directory $HOME"
echo "  gitlab-runner start"
echo ""
echo "To verify it's connected to GitLab:"
echo "  gitlab-runner verify --config $CONFIG_DIR/config.toml"
