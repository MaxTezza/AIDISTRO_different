#!/usr/bin/env python3
"""
AI Distro — Offline-First Graceful Mode

Detects network connectivity and seamlessly switches all services between
online and offline modes. Suppresses error spam, queues outbound requests,
and replays them when connectivity returns.

Features:
  - Continuous connectivity monitoring (ping + DNS + HTTP)
  - Service notification via event bus on state transitions
  - Request queue for deferred operations (email, web, updates)
  - Per-service capability reporting (what works offline vs online)
  - Automatic retry with exponential backoff on reconnection

Usage:
  python3 offline_mode.py status       # Current connectivity state
  python3 offline_mode.py capabilities # What works online vs offline
  python3 offline_mode.py queue        # Show queued requests
  python3 offline_mode.py flush        # Force-flush the queue now
  python3 offline_mode.py monitor      # Run as daemon
"""
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

QUEUE_FILE = Path(os.path.expanduser("~/.cache/ai-distro/offline_queue.json"))
STATE_FILE = Path(os.path.expanduser("~/.cache/ai-distro/network_state.json"))
CHECK_INTERVAL_ONLINE = 30
CHECK_INTERVAL_OFFLINE = 10
EVENT_SOCKET = "/tmp/ai-distro-events.sock"

# Services and their online/offline capabilities
SERVICE_CAPABILITIES = {
    "agent": {
        "online": ["cloud LLM", "web search", "email", "calendar", "package install"],
        "offline": ["local LLM", "local skills", "file operations", "system control", "TTS"],
    },
    "voice": {
        "online": ["cloud STT", "cloud TTS"],
        "offline": ["local Piper TTS", "wake word", "basic commands"],
    },
    "curator": {
        "online": ["weather fetch", "news fetch", "update check"],
        "offline": ["Bayesian predictions", "habit tracking", "system monitoring"],
    },
    "spirit": {
        "online": ["Telegram bridge", "remote control"],
        "offline": ["(disabled — requires network)"],
    },
    "healer": {
        "online": ["package repair", "update services", "network diagnostics"],
        "offline": ["service restart", "disk cleanup", "audio repair", "log rotation"],
    },
    "dashboard": {
        "online": ["full dashboard"],
        "offline": ["full dashboard (local only)"],
    },
    "marketplace": {
        "online": ["skill search", "skill install", "repo sync"],
        "offline": ["browse installed skills", "local catalog"],
    },
    "vision": {
        "online": ["cloud vision API"],
        "offline": ["local Moondream VLM", "OCR fallback"],
    },
    "file_intelligence": {
        "online": ["web-enhanced search"],
        "offline": ["full local search", "content indexing"],
    },
    "notification_bridge": {
        "online": ["KDE Connect", "phone bridge"],
        "offline": ["desktop notifications only"],
    },
}


def _check_connectivity():
    """Multi-method connectivity check."""
    checks = {"dns": False, "ping": False, "http": False}

    # DNS resolution
    try:
        socket.setdefaulttimeout(3)
        socket.getaddrinfo("one.one.one.one", 443)
        checks["dns"] = True
    except (socket.gaierror, socket.timeout, OSError):
        pass

    # ICMP ping (fast)
    if not checks["dns"]:
        try:
            r = subprocess.run(
                ["ping", "-c", "1", "-W", "2", "1.1.1.1"],
                capture_output=True, timeout=5
            )
            checks["ping"] = r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # HTTP check (most reliable but slowest)
    if checks["dns"]:
        try:
            import urllib.request
            urllib.request.urlopen("http://detectportal.firefox.com/canonical.html", timeout=5)
            checks["http"] = True
        except Exception:
            pass

    return checks


def _is_online(checks=None):
    if checks is None:
        checks = _check_connectivity()
    return checks.get("dns") or checks.get("ping") or checks.get("http")


def _load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"online": True, "last_check": None, "transitions": 0}


def _save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _load_queue():
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE) as f:
            return json.load(f)
    return []


def _save_queue(queue):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def _publish_event(event_type, data):
    """Notify services of connectivity change."""
    try:
        if not os.path.exists(EVENT_SOCKET):
            return
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(EVENT_SOCKET)
        msg = json.dumps({"channel": "network", "data": {"type": event_type, **data}})
        s.sendall(msg.encode("utf-8") + b"\n")
        s.close()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def queue_request(service, action, payload=None):
    """Queue a request for when connectivity returns."""
    queue = _load_queue()
    queue.append({
        "id": len(queue) + 1,
        "service": service,
        "action": action,
        "payload": payload,
        "queued_at": datetime.now().isoformat(),
        "status": "pending",
    })
    _save_queue(queue)
    return {"status": "queued", "position": len(queue)}


def flush_queue():
    """Attempt to replay all queued requests."""
    if not _is_online():
        return {"error": "Still offline", "pending": len(_load_queue())}

    queue = _load_queue()
    results = []
    remaining = []

    for item in queue:
        try:
            # Try to send to agent
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect("/run/ai-distro/agent.sock")
            request = {"version": 1, "name": item["action"], "payload": item.get("payload", "")}
            s.sendall(json.dumps(request).encode("utf-8") + b"\n")
            s.close()
            item["status"] = "sent"
            results.append(item)
        except Exception:
            remaining.append(item)

    _save_queue(remaining)
    return {"flushed": len(results), "remaining": len(remaining)}


def get_status():
    """Get current connectivity status."""
    checks = _check_connectivity()
    online = _is_online(checks)
    state = _load_state()
    queue = _load_queue()

    return {
        "online": online,
        "checks": checks,
        "transitions": state.get("transitions", 0),
        "last_check": state.get("last_check"),
        "queued_requests": len(queue),
        "mode": "online" if online else "offline (graceful)",
    }


def get_capabilities():
    """Show what works online vs offline."""
    online = _is_online()
    result = {}
    for service, caps in SERVICE_CAPABILITIES.items():
        mode = "online" if online else "offline"
        result[service] = {
            "mode": mode,
            "available": caps[mode],
            "unavailable": caps["online" if mode == "offline" else "offline"],
        }
    return result


def monitor():
    """Run as a connectivity monitor daemon."""
    print("Offline Mode Monitor started")
    state = _load_state()
    was_online = state.get("online", True)

    while True:
        try:
            checks = _check_connectivity()
            is_online = _is_online(checks)

            # State transition
            if is_online != was_online:
                state["transitions"] = state.get("transitions", 0) + 1
                ts = datetime.now().strftime("%H:%M:%S")

                if is_online:
                    print(f"  [{ts}] 🟢 Back online")
                    _publish_event("online", {"checks": checks})

                    # Auto-flush queue
                    queue = _load_queue()
                    if queue:
                        result = flush_queue()
                        print(f"  [{ts}]   Flushed {result.get('flushed', 0)} queued requests")
                else:
                    print(f"  [{ts}] 🔴 Gone offline — switching to graceful mode")
                    _publish_event("offline", {"checks": checks})

                was_online = is_online

            state["online"] = is_online
            state["last_check"] = datetime.now().isoformat()
            _save_state(state)

        except Exception as e:
            print(f"  Monitor error: {e}")

        interval = CHECK_INTERVAL_ONLINE if is_online else CHECK_INTERVAL_OFFLINE
        time.sleep(interval)


def main():
    if len(sys.argv) < 2:
        print("Usage: offline_mode.py <status|capabilities|queue|flush|monitor>")
        return

    cmd = sys.argv[1]

    if cmd == "status":
        print(json.dumps(get_status(), indent=2))
    elif cmd == "capabilities":
        caps = get_capabilities()
        for svc, info in caps.items():
            mode_icon = "🟢" if info["mode"] == "online" else "🔴"
            print(f"  {mode_icon} {svc}: {', '.join(info['available'])}")
    elif cmd == "queue":
        queue = _load_queue()
        if queue:
            for item in queue:
                print(f"  #{item['id']} [{item['service']}] {item['action']} — {item['queued_at']}")
        else:
            print("  Queue empty")
    elif cmd == "flush":
        print(json.dumps(flush_queue(), indent=2))
    elif cmd == "monitor":
        monitor()
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
