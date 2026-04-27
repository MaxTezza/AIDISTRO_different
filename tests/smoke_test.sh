#!/bin/bash
# ── AI Distro Smoke Test ──────────────────────────────────────────────
# Validates the end-to-end pipeline: CLI → Agent → Brain → Response
#
# Run after install: bash tests/smoke_test.sh
# Exit codes: 0 = all pass, 1 = failures
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0
SKIP=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✔ PASS${NC}: $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}✘ FAIL${NC}: $1"; FAIL=$((FAIL + 1)); }
skip() { echo -e "  ${YELLOW}⊘ SKIP${NC}: $1"; SKIP=$((SKIP + 1)); }

echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo -e "${CYAN}  AI DISTRO SMOKE TEST${NC}"
echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo ""

# ── 1. Check compiled binaries ────────────────────────────────────────
echo -e "${CYAN}[1/7] Checking compiled binaries...${NC}"
for bin in ai-distro-agent ai-distro-cli ai-distro-core ai-distro-voice ai-distro-hud; do
    if [ -f "$ROOT_DIR/src/rust/target/release/$bin" ]; then
        pass "$bin exists"
    else
        fail "$bin not found in target/release/"
    fi
done

# ── 2. Check Python environment ──────────────────────────────────────
echo ""
echo -e "${CYAN}[2/7] Checking Python environment...${NC}"
VENV="$ROOT_DIR/.venv/bin/python3"
if [ -f "$VENV" ]; then
    pass "Virtual environment exists"
else
    fail "No .venv found (run install.sh first)"
fi

# Check critical Python imports
for pkg in json socket subprocess; do
    if "$VENV" -c "import $pkg" 2>/dev/null; then
        pass "Python import: $pkg"
    else
        fail "Python import: $pkg"
    fi
done

# Check llama-cpp-python (optional but important)
if "$VENV" -c "from llama_cpp import Llama" 2>/dev/null; then
    pass "llama-cpp-python available"
else
    skip "llama-cpp-python not installed (cloud fallback will be used)"
fi

# ── 3. Check model files ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}[3/7] Checking model files...${NC}"
CACHE_DIR="$HOME/.cache/ai-distro"

# LLM model
if ls "$CACHE_DIR/models/"*.gguf 1>/dev/null 2>&1; then
    MODEL=$(ls -1 "$CACHE_DIR/models/"*.gguf | head -1)
    SIZE=$(du -h "$MODEL" | awk '{print $1}')
    pass "LLM model present ($SIZE)"
else
    skip "No .gguf model found (use 'ai-distro intelligence mode cloud' or download a model)"
fi

# Piper TTS
PIPER_DIR="$CACHE_DIR/piper"
if [ -f "$PIPER_DIR/piper/piper" ]; then
    pass "Piper TTS binary present"
else
    fail "Piper TTS not found at $PIPER_DIR/piper/piper"
fi
if ls "$PIPER_DIR/"*.onnx 1>/dev/null 2>&1; then
    pass "Piper voice model present"
else
    fail "Piper .onnx voice model not found"
fi

# Vosk STT
VOSK_DIR="$CACHE_DIR/vosk"
if [ -d "$VOSK_DIR/model" ]; then
    pass "Vosk STT model present"
else
    fail "Vosk STT model not found at $VOSK_DIR/model"
fi

# ASR wrapper (the glue between Vosk and the Rust voice engine)
ASR_BIN="$ROOT_DIR/tools/voice/vosk_asr"
if [ -x "$ASR_BIN" ]; then
    pass "Vosk ASR wrapper is executable"
else
    fail "Vosk ASR wrapper not found or not executable at $ASR_BIN"
fi

# Moondream Vision
if [ -f "$CACHE_DIR/moondream_downloaded" ]; then
    pass "Moondream2 VLM cached"
elif "$VENV" -c "import moondream" 2>/dev/null; then
    skip "Moondream2 installed but may not be pre-cached (will download on first use)"
else
    skip "Moondream2 not installed (vision will use OCR fallback)"
fi

# ── 4. Check configurations ──────────────────────────────────────────
echo ""
echo -e "${CYAN}[4/7] Checking configuration files...${NC}"
CONFIG_DIR="/etc/ai-distro"
for cfg in agent.json voice.json policy.json; do
    if [ -f "$CONFIG_DIR/$cfg" ] || [ -f "$ROOT_DIR/configs/$cfg" ]; then
        pass "Config: $cfg"
    else
        fail "Config: $cfg not found"
    fi
done

# ── 5. Check IPC socket communication ────────────────────────────────
echo ""
echo -e "${CYAN}[5/7] Testing IPC communication (requires agent running)...${NC}"
SOCKET="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/ai-distro/agent.sock"
# Agent may also bind to /tmp
if [ ! -S "$SOCKET" ] && [ -S "/tmp/ai-distro-agent.sock" ]; then
    SOCKET="/tmp/ai-distro-agent.sock"
fi
if [ -S "$SOCKET" ]; then
    pass "Agent socket exists at $SOCKET"

    # Send a ping request
    RESPONSE=$(echo '{"version": 1, "name": "ping", "payload": null}' | \
        socat - UNIX-CONNECT:"$SOCKET" 2>/dev/null || echo "CONNECT_FAILED")

    if echo "$RESPONSE" | grep -q '"pong"'; then
        pass "Agent responded to ping"
    elif [ "$RESPONSE" = "CONNECT_FAILED" ]; then
        fail "Could not connect to agent socket"
    else
        fail "Agent ping returned unexpected: $RESPONSE"
    fi

    # Test get_capabilities
    RESPONSE=$(echo '{"version": 1, "name": "get_capabilities", "payload": null}' | \
        socat - UNIX-CONNECT:"$SOCKET" 2>/dev/null || echo "CONNECT_FAILED")

    if echo "$RESPONSE" | grep -q '"actions"'; then
        ACTION_COUNT=$(echo "$RESPONSE" | "$VENV" -c "import sys,json; print(len(json.load(sys.stdin).get('capabilities',{}).get('actions',[])))" 2>/dev/null || echo "0")
        pass "Agent reports $ACTION_COUNT registered actions"
    else
        fail "get_capabilities returned unexpected response"
    fi
else
    skip "Agent not running (start with: ai-distro start)"
fi

# ── 6. Check WebSocket bridge ────────────────────────────────────────
echo ""
echo -e "${CYAN}[6/7] Testing WebSocket bridge...${NC}"
if command -v curl &>/dev/null; then
    # Quick check if port 5001 is listening
    if curl -s --max-time 2 http://127.0.0.1:5001 &>/dev/null || \
       "$VENV" -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('127.0.0.1', 5001))
    s.close()
    print('open')
except:
    print('closed')
" 2>/dev/null | grep -q "open"; then
        pass "WebSocket bridge port 5001 is open"
    else
        skip "WebSocket bridge not running (start with: ai-distro start)"
    fi
else
    skip "curl not available to test WebSocket bridge"
fi

# ── 7. Check systemd services ────────────────────────────────────────
echo ""
echo -e "${CYAN}[7/7] Checking systemd user services...${NC}"
SERVICES=(ai-distro-agent ai-distro-wsbridge ai-distro-voice ai-distro-hud
          ai-distro-curator ai-distro-spirit ai-distro-healer
          ai-distro-hardware ai-distro-vision)
for svc in "${SERVICES[@]}"; do
    UNIT_FILE="$HOME/.config/systemd/user/${svc}.service"
    if [ -f "$UNIT_FILE" ]; then
        pass "Service unit: $svc"
    else
        fail "Missing service unit: $svc"
    fi
done

# ── Summary ───────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════════${NC}"
TOTAL=$((PASS + FAIL + SKIP))
echo -e "  ${GREEN}$PASS passed${NC}  ${RED}$FAIL failed${NC}  ${YELLOW}$SKIP skipped${NC}  ($TOTAL total)"

if [ $FAIL -eq 0 ]; then
    echo -e "  ${GREEN}All critical checks passed!${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "  ${RED}$FAIL check(s) failed. Fix the issues above before deploying.${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════${NC}"
    exit 1
fi
