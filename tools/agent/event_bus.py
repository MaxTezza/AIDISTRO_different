#!/usr/bin/env python3
"""
AI Distro — Unified Event Bus

Centralized notification system that all services publish to and subscribe from.
Replaces the ad-hoc EVENT_SOCKET pattern with a structured pub/sub event bus.

Architecture:
  - All services publish events to the bus via Unix socket
  - The bus fans out to registered listeners (HUD, Spirit Bridge, Healer log)
  - Events are typed, timestamped, and JSON-structured
  - Persistent event log for audit trail

Socket: /tmp/ai-distro-events.sock
Protocol: JSON-per-line  {"type": "info|warn|error", "source": "healer", "title": ..., "message": ...}
"""
import json
import os
import socket
import threading
from collections import deque
from datetime import datetime
from pathlib import Path

EVENT_SOCKET = os.environ.get("AI_DISTRO_EVENT_SOCKET", "/tmp/ai-distro-events.sock")
LOG_DIR = Path(os.path.expanduser("~/.local/share/ai-distro/events"))
MAX_HISTORY = 500  # Keep last N events in memory
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB per log file


class EventBus:
    """Central event hub for AI Distro services."""

    def __init__(self):
        self.history = deque(maxlen=MAX_HISTORY)
        self.listeners = []  # List of connected listener sockets
        self.listeners_lock = threading.Lock()
        self.log_file = None
        self._ensure_log()

    def _ensure_log(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / f"events-{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        self.log_file = open(log_path, "a")

    def publish(self, event):
        """Accept an event, store it, log it, and fan out to listeners."""
        # Enrich with timestamp
        event.setdefault("timestamp", datetime.now().isoformat())
        event.setdefault("type", "info")
        event.setdefault("source", "unknown")

        # Store in memory
        self.history.append(event)

        # Persist to disk
        try:
            self.log_file.write(json.dumps(event) + "\n")
            self.log_file.flush()
        except Exception:
            self._ensure_log()

        # Fan out to connected listeners
        event_bytes = (json.dumps(event) + "\n").encode("utf-8")
        dead = []
        with self.listeners_lock:
            for listener in self.listeners:
                try:
                    listener.sendall(event_bytes)
                except Exception:
                    dead.append(listener)
            for d in dead:
                self.listeners.remove(d)
                try:
                    d.close()
                except Exception:
                    pass

    def add_listener(self, conn):
        """Register a new listener socket (e.g., HUD, dashboard)."""
        with self.listeners_lock:
            self.listeners.append(conn)

    def get_history(self, count=50, event_type=None, source=None):
        """Retrieve recent events with optional filtering."""
        events = list(self.history)
        if event_type:
            events = [e for e in events if e.get("type") == event_type]
        if source:
            events = [e for e in events if e.get("source") == source]
        return events[-count:]


def handle_client(bus, conn, addr):
    """Handle a connected client — can be a publisher or listener."""
    buffer = b""
    try:
        # First message determines role
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buffer += data

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

                # Special command: subscribe to events
                if msg.get("action") == "subscribe":
                    bus.add_listener(conn)
                    # Send recent history
                    count = msg.get("history", 20)
                    for event in bus.get_history(count):
                        try:
                            conn.sendall(
                                (json.dumps(event) + "\n").encode("utf-8")
                            )
                        except Exception:
                            return
                    # Don't close — keep alive for streaming
                    return  # Exit handler, socket stays open in listeners

                # Special command: query history
                elif msg.get("action") == "history":
                    events = bus.get_history(
                        count=msg.get("count", 50),
                        event_type=msg.get("event_type"),
                        source=msg.get("source")
                    )
                    try:
                        conn.sendall(
                            (json.dumps({"events": events}) + "\n").encode("utf-8")
                        )
                    except Exception:
                        pass
                    return

                # Default: treat as a published event
                else:
                    bus.publish(msg)

    except (ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        print(f"[EventBus] Client error: {e}")
    finally:
        # Only close if not a listener
        with bus.listeners_lock:
            if conn not in bus.listeners:
                try:
                    conn.close()
                except Exception:
                    pass


def run_server(bus):
    """Run the event bus server."""
    # Clean up stale socket
    if os.path.exists(EVENT_SOCKET):
        os.unlink(EVENT_SOCKET)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(EVENT_SOCKET)
    os.chmod(EVENT_SOCKET, 0o666)  # Allow all local services to connect
    server.listen(32)
    server.settimeout(1.0)

    print(f"[EventBus] Listening on {EVENT_SOCKET}")
    print(f"[EventBus] Log directory: {LOG_DIR}")

    try:
        while True:
            try:
                conn, addr = server.accept()
                t = threading.Thread(
                    target=handle_client, args=(bus, conn, addr),
                    daemon=True
                )
                t.start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("\n[EventBus] Shutting down.")
    finally:
        server.close()
        if os.path.exists(EVENT_SOCKET):
            os.unlink(EVENT_SOCKET)


# ═══════════════════════════════════════════════════════════════════
# Client helper (importable by other services)
# ═══════════════════════════════════════════════════════════════════
def emit(title, message, level="info", source="unknown"):
    """Convenience function for services to emit events."""
    event = {
        "type": level,
        "source": source,
        "title": title,
        "message": message
    }
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(EVENT_SOCKET)
            s.sendall((json.dumps(event) + "\n").encode("utf-8"))
    except Exception:
        # Bus not running — silently ignore
        pass


def get_recent_events(count=50, event_type=None, source=None):
    """Query the event bus for recent events."""
    query = {"action": "history", "count": count}
    if event_type:
        query["event_type"] = event_type
    if source:
        query["source"] = source

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect(EVENT_SOCKET)
            s.sendall((json.dumps(query) + "\n").encode("utf-8"))
            data = b""
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break
            result = json.loads(data.decode("utf-8").strip())
            return result.get("events", [])
    except Exception:
        return []


if __name__ == "__main__":
    bus = EventBus()
    run_server(bus)
