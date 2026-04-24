#!/usr/bin/env python3
import subprocess
import json
import socket
import time

AGENT_SOCKET = "/run/ai-distro/agent.sock"
EVENT_SOCKET = "/tmp/ai-distro-events.sock"

def broadcast_event(title, message):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(EVENT_SOCKET)
            event = {"type": "info", "title": title, "message": message}
            client.sendall(json.dumps(event).encode('utf-8') + b"\n")
    except Exception:
        pass

def check_logs():
    """Monitors journalctl for common failure patterns."""
    print("IT Department: Monitoring system logs for issues...")
    # Get logs from the last 5 minutes
    cmd = ["journalctl", "--since", "5 minutes ago", "--priority=3", "-n", "20", "--no-pager"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        logs = res.stdout
        
        # 1. Wi-Fi Issues
        if "wpa_supplicant" in logs or "NetworkManager" in logs:
            if "failed" in logs or "error" in logs:
                handle_repair("network", "I noticed a Wi-Fi connection error. I'm resetting the network stack for you.")

        # 2. Disk/IO Issues
        if "I/O error" in logs:
            broadcast_event("System Health", "I detected a disk I/O error. I recommend running a filesystem check soon.")

        # 3. Audio/ALSA Issues
        if "alsa" in logs.lower() and "error" in logs.lower():
            handle_repair("audio", "Audio driver seems unstable. Reloading sound modules.")

    except Exception as e:
        print(f"Log Monitor Error: {e}")

def handle_repair(category, message):
    broadcast_event("Auto-Repair", message)
    if category == "network":
        subprocess.run(["nmcli", "networking", "off"])
        time.sleep(1)
        subprocess.run(["nmcli", "networking", "on"])
    elif category == "audio":
        subprocess.run(["pulseaudio", "-k"]) # Force restart
        
def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check_now":
        check_logs()
    else:
        while True:
            check_logs()
            time.sleep(300) # Check every 5 minutes

if __name__ == "__main__":
    main()
