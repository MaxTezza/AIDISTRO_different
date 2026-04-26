#!/usr/bin/env python3
"""
AI Distro — Notification Bridge

Bridges phone notifications to the desktop AI via KDE Connect protocol,
aggregates desktop notifications, and provides AI-powered summarization.

Features:
  - Receive phone notifications (KDE Connect / GSConnect)
  - Capture desktop notifications (D-Bus org.freedesktop.Notifications)
  - AI summarization of notification batches
  - Priority filtering (urgent, normal, low, muted apps)
  - Event bus integration for real-time notification dispatch
  - Notification history with search

Usage:
  python3 notification_bridge.py serve         # Run bridge daemon
  python3 notification_bridge.py recent [n]    # Show recent notifications
  python3 notification_bridge.py summary       # AI summary of unread
  python3 notification_bridge.py mute <app>    # Mute an app's notifications
  python3 notification_bridge.py unmute <app>  # Unmute an app
  python3 notification_bridge.py status        # Show bridge status
  python3 notification_bridge.py clear         # Clear notification history
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.path.expanduser("~/.cache/ai-distro/notifications.db"))
CONFIG_PATH = Path(os.path.expanduser("~/.config/ai-distro/notifications.json"))


def _init_db():
    """Initialize the notification database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        source TEXT NOT NULL,
        app_name TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT,
        urgency TEXT DEFAULT 'normal',
        read INTEGER DEFAULT 0,
        dismissed INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()


def _load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"muted_apps": [], "priority_apps": ["Phone", "Slack", "Signal", "WhatsApp"]}


def _save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def _store_notification(source, app_name, title, body="", urgency="normal"):
    """Store a notification in the database."""
    cfg = _load_config()
    if app_name.lower() in [m.lower() for m in cfg.get("muted_apps", [])]:
        return None  # Muted

    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.execute(
        "INSERT INTO notifications (timestamp, source, app_name, title, body, urgency) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().timestamp(), source, app_name, title, body, urgency)
    )
    nid = c.lastrowid
    conn.commit()
    conn.close()

    # Publish to event bus
    _publish_event({
        "type": "notification",
        "source": source,
        "app": app_name,
        "title": title,
        "body": body[:200],
        "urgency": urgency,
    })

    return nid


def _publish_event(data):
    """Publish to the event bus if available."""
    try:
        import socket as sock
        EVENT_SOCKET = "/tmp/ai-distro-events.sock"
        if not os.path.exists(EVENT_SOCKET):
            return
        s = sock.socket(sock.AF_UNIX, sock.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(EVENT_SOCKET)
        msg = json.dumps({"channel": "notifications", "data": data})
        s.sendall(msg.encode("utf-8") + b"\n")
        s.close()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
# Desktop Notification Monitor (D-Bus)
# ═══════════════════════════════════════════════════════════════════

def _monitor_desktop_notifications():
    """Monitor desktop notifications via dbus-monitor."""
    try:
        proc = subprocess.Popen(
            ["dbus-monitor", "--session",
             "interface='org.freedesktop.Notifications',member='Notify'"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        buffer = []
        for line in proc.stdout:
            line = line.strip()
            buffer.append(line)

            # Parse notification when we get a complete message
            if line.startswith("string") and len(buffer) > 3:
                _parse_dbus_notification(buffer)
                buffer = []

    except FileNotFoundError:
        print("  ⚠ dbus-monitor not found, desktop notifications disabled")
    except Exception as e:
        print(f"  ⚠ Desktop monitor error: {e}")


def _parse_dbus_notification(lines):
    """Extract notification fields from dbus-monitor output."""
    strings = []
    for line in lines:
        m = re.match(r'\s*string\s+"(.+)"', line)
        if m:
            strings.append(m.group(1))

    if len(strings) >= 3:
        app_name = strings[0] or "Desktop"
        title = strings[1] if len(strings) > 1 else ""
        body = strings[2] if len(strings) > 2 else ""
        if title:
            _store_notification("desktop", app_name, title, body)


# ═══════════════════════════════════════════════════════════════════
# KDE Connect Phone Notifications
# ═══════════════════════════════════════════════════════════════════

def _get_kdeconnect_devices():
    """List KDE Connect paired devices."""
    code = subprocess.run(
        ["kdeconnect-cli", "--list-available"],
        capture_output=True, text=True, timeout=5
    )
    if code.returncode != 0:
        return []

    devices = []
    for line in code.stdout.strip().split("\n"):
        m = re.match(r"- (.+):\s+([a-f0-9]+)", line)
        if m:
            devices.append({"name": m.group(1), "id": m.group(2)})
    return devices


def _poll_kdeconnect_notifications():
    """Poll KDE Connect for new phone notifications."""
    try:
        # Check if kdeconnect-cli is available
        result = subprocess.run(
            ["kdeconnect-cli", "--list-notifications"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return

        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            # Format varies, try to extract app and content
            parts = line.split(":", 1)
            app = parts[0].strip() if parts else "Phone"
            body = parts[1].strip() if len(parts) > 1 else line
            _store_notification("phone", app, body)

    except FileNotFoundError:
        pass  # KDE Connect not installed
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def get_recent(n=20):
    """Get recent notifications."""
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM notifications ORDER BY timestamp DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()

    return [{
        "id": r["id"],
        "time": datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M:%S"),
        "source": r["source"],
        "app": r["app_name"],
        "title": r["title"],
        "body": r["body"],
        "urgency": r["urgency"],
        "read": bool(r["read"]),
    } for r in rows]


def get_unread_count():
    """Count unread notifications."""
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    count = conn.execute("SELECT COUNT(*) FROM notifications WHERE read = 0").fetchone()[0]
    conn.close()
    return count


def summarize():
    """Generate a summary of recent unread notifications."""
    unread = [n for n in get_recent(50) if not n["read"]]
    if not unread:
        return {"summary": "No unread notifications.", "count": 0}

    # Group by app
    by_app = {}
    for n in unread:
        app = n["app"]
        by_app.setdefault(app, []).append(n)

    lines = []
    for app, notifs in sorted(by_app.items(), key=lambda x: -len(x[1])):
        count = len(notifs)
        if count == 1:
            lines.append(f"• {app}: {notifs[0]['title']}")
        else:
            lines.append(f"• {app}: {count} notifications")
            for n in notifs[:3]:
                lines.append(f"  – {n['title']}")
            if count > 3:
                lines.append(f"  – ...and {count - 3} more")

    cfg = _load_config()
    priority = [n for n in unread if n["app"] in cfg.get("priority_apps", [])]

    return {
        "summary": "\n".join(lines),
        "count": len(unread),
        "priority_count": len(priority),
        "apps": list(by_app.keys()),
    }


def mute_app(app_name):
    """Mute notifications from an app."""
    cfg = _load_config()
    muted = cfg.setdefault("muted_apps", [])
    if app_name not in muted:
        muted.append(app_name)
    _save_config(cfg)
    return {"status": "ok", "muted": app_name}


def unmute_app(app_name):
    """Unmute an app."""
    cfg = _load_config()
    cfg["muted_apps"] = [m for m in cfg.get("muted_apps", []) if m.lower() != app_name.lower()]
    _save_config(cfg)
    return {"status": "ok", "unmuted": app_name}


def mark_all_read():
    """Mark all notifications as read."""
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    count = conn.execute("UPDATE notifications SET read = 1 WHERE read = 0").rowcount
    conn.commit()
    conn.close()
    return {"status": "ok", "marked": count}


def clear_history():
    """Clear all notification history."""
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    count = conn.execute("DELETE FROM notifications").rowcount
    conn.commit()
    conn.close()
    return {"status": "ok", "cleared": count}


def bridge_status():
    """Show notification bridge status."""
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    total = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
    unread = conn.execute("SELECT COUNT(*) FROM notifications WHERE read = 0").fetchone()[0]
    conn.close()

    cfg = _load_config()

    # Check capabilities
    has_dbus = subprocess.run(
        ["which", "dbus-monitor"], capture_output=True
    ).returncode == 0
    has_kdeconnect = subprocess.run(
        ["which", "kdeconnect-cli"], capture_output=True
    ).returncode == 0

    return {
        "total_notifications": total,
        "unread": unread,
        "muted_apps": cfg.get("muted_apps", []),
        "priority_apps": cfg.get("priority_apps", []),
        "capabilities": {
            "desktop_notifications": has_dbus,
            "phone_bridge": has_kdeconnect,
        },
    }


def serve():
    """Run the notification bridge daemon."""
    _init_db()
    print("Notification Bridge started")
    status = bridge_status()
    caps = status["capabilities"]
    print(f"  Desktop: {'✓' if caps['desktop_notifications'] else '✗'}")
    print(f"  Phone:   {'✓' if caps['phone_bridge'] else '✗ (install kdeconnect)'}")

    # Start desktop notification monitor in a thread
    if caps["desktop_notifications"]:
        t = threading.Thread(target=_monitor_desktop_notifications, daemon=True)
        t.start()
        print("  → Listening for desktop notifications")

    # Poll KDE Connect periodically
    if caps["phone_bridge"]:
        print("  → Polling KDE Connect every 30s")

    try:
        while True:
            if caps["phone_bridge"]:
                _poll_kdeconnect_notifications()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    if len(sys.argv) < 2:
        print("Usage: notification_bridge.py <serve|recent|summary|mute|unmute|status|clear>")
        return

    cmd = sys.argv[1]
    arg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if cmd == "serve":
        serve()
    elif cmd == "recent":
        n = int(arg) if arg.isdigit() else 20
        print(json.dumps(get_recent(n), indent=2))
    elif cmd == "summary":
        print(json.dumps(summarize(), indent=2))
    elif cmd == "mute":
        print(json.dumps(mute_app(arg), indent=2))
    elif cmd == "unmute":
        print(json.dumps(unmute_app(arg), indent=2))
    elif cmd == "status":
        print(json.dumps(bridge_status(), indent=2))
    elif cmd == "clear":
        print(json.dumps(clear_history(), indent=2))
    elif cmd == "read":
        print(json.dumps(mark_all_read(), indent=2))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
