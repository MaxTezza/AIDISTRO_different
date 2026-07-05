#!/bin/bash
set -e

# Cleanup old sockets
rm -f /tmp/ai-distro.sock /tmp/ai-core.sock

# Ensure local model is present
echo "Checking local reasoning model..."
python3 /app/tools/agent/download_model.py || echo "Warning: model download check failed, starting agent anyway."

# Start agent
echo "Starting agent..."
ai-distro-agent &
AGENT_PID=$!

# Start core
echo "Starting core..."
ai-distro-core &
CORE_PID=$!

# Wait for sockets to appear
echo "Waiting for sockets..."
for i in {1..30}; do
    if [ -S /tmp/ai-distro.sock ] && [ -S /tmp/ai-core.sock ]; then
        echo "Sockets created successfully."
        break
    fi
    sleep 0.2
done

# Start shell web server
echo "Starting shell web server on port 17842..."
python3 /app/tools/shell/ai_distro_shell.py &
SHELL_PID=$!

# Define shutdown handler
cleanup() {
    echo "Shutting down daemons..."
    kill $SHELL_PID $CORE_PID $AGENT_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep script running and wait for background processes
wait $SHELL_PID $CORE_PID $AGENT_PID
