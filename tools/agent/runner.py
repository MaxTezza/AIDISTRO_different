#!/usr/bin/env python3
import sys
import json
import subprocess
import requests
import os

# Paths
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_SCRIPT = os.path.join(AGENT_DIR, "brain.py")
INTENT_SCRIPT = os.path.join(AGENT_DIR, "intent_parser.py")
DAEMON_URL = "http://localhost:8000/direct_task"

def run_brain(text):
    """Try to parse intent using brain.py (LLM) or intent_parser.py (Regex)."""
    try:
        # Try brain.py first
        result = subprocess.check_output([sys.executable, BRAIN_SCRIPT, text], stderr=subprocess.DEVNULL).decode().strip()
        return json.loads(result)
    except:
        # Fallback to intent_parser.py
        try:
            result = subprocess.check_output([sys.executable, INTENT_SCRIPT, text], stderr=subprocess.DEVNULL).decode().strip()
            return json.loads(result)
        except:
            return {"name": "unknown", "payload": text}

def main():
    if len(sys.argv) < 2:
        print("Usage: mnemonic-run \"your command here\"")
        sys.exit(1)

    user_input = " ".join(sys.argv[1:])
    action = run_brain(user_input)
    
    print(f"[MnemonicRunner] Parsed intent: {action.get('name')}")
    
    try:
        # Forward to daemon
        payload = {
            "task": f"System Runner Execution: {user_input}",
            "priority": "HIGH"
        }
        # We wrap the specific action if needed, or just send the whole command
        # For now, let the daemon handle the task description directly as it has its own worker loop
        resp = requests.post(DAEMON_URL, json={"task": user_input})
        if resp.status_code == 200:
            print("✅ Task dispatched to MnemonicOS.")
        else:
            print(f"❌ Daemon error: {resp.text}")
    except Exception as e:
        print(f"❌ Failed to connect to MnemonicOS daemon: {e}")

if __name__ == "__main__":
    main()
