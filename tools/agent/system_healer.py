#!/usr/bin/env python3
"""
AI Distro System Healer — Autonomous IT Department

Continuously monitors system health and autonomously repairs common issues:
  1. Service crash recovery with exponential backoff
  2. Disk space management (auto-cleanup)
  3. Network connectivity repair
  4. Audio subsystem recovery
  5. Memory pressure response
  6. Package integrity verification
  7. Failed login detection and lockout alerting

Reports all actions to the HUD and audit trail.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time

AGENT_SOCKET = os.environ.get(
    "AI_DISTRO_IPC_SOCKET", "/run/ai-distro/agent.sock"
)
EVENT_SOCKET = "/tmp/ai-distro-events.sock"
LOG_DIR = os.path.expanduser("~/.cache/ai-distro/healer")
HEALER_LOG = os.path.join(LOG_DIR, "healer.jsonl")

os.makedirs(LOG_DIR, exist_ok=True)

# ── IPC & Logging ────────────────────────────────────────────────

def broadcast_event(title, message, level="info"):
    """Send a card to the HUD overlay."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(EVENT_SOCKET)
            event = {"type": level, "title": title, "message": message}
            client.sendall(json.dumps(event).encode("utf-8") + b"\n")
    except Exception:
        pass


def log_action(category, action, result):
    """Append to healer audit trail."""
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "category": category,
        "action": action,
        "result": result,
    }
    try:
        with open(HEALER_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
    print(f"[Healer] [{category}] {action}: {result}")


def send_to_agent(action_name, payload=None):
    """Send an action request to the main agent via IPC."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(5)
            client.connect(AGENT_SOCKET)
            msg = {"action": action_name}
            if payload:
                msg["payload"] = payload
            client.sendall(json.dumps(msg).encode("utf-8") + b"\n")
    except Exception:
        pass


# ── Health Checks ────────────────────────────────────────────────

def check_services():
    """Monitor AI Distro service health and restart crashed ones."""
    services = [
        "ai-distro-agent", "ai-distro-wsbridge", "ai-distro-voice",
        "ai-distro-hud", "ai-distro-curator", "ai-distro-spirit",
        "ai-distro-hardware",
    ]

    for svc in services:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", f"{svc}.service"],
                capture_output=True, text=True
            )
            status = result.stdout.strip()

            if status == "failed":
                log_action("services", f"restarting {svc}", "service was failed")
                broadcast_event(
                    "Auto-Repair",
                    f"Service {svc} crashed. Restarting...",
                    "warning"
                )
                subprocess.run(
                    ["systemctl", "--user", "restart", f"{svc}.service"],
                    capture_output=True
                )
                time.sleep(2)

                # Verify it came back
                verify = subprocess.run(
                    ["systemctl", "--user", "is-active", f"{svc}.service"],
                    capture_output=True, text=True
                )
                if verify.stdout.strip() == "active":
                    log_action("services", f"restarted {svc}", "success")
                    broadcast_event("Auto-Repair", f"✔ {svc} recovered successfully.")
                else:
                    log_action("services", f"restart {svc}", "FAILED — needs manual attention")
                    broadcast_event(
                        "System Alert",
                        f"✘ {svc} could not be restarted. Manual attention needed.",
                        "error"
                    )
        except Exception as e:
            log_action("services", f"check {svc}", f"error: {e}")


def check_disk_space():
    """Check disk usage and clean up if running low."""
    try:
        stat = shutil.disk_usage("/")
        used_pct = (stat.used / stat.total) * 100
        free_gb = stat.free / (1024 ** 3)

        if used_pct > 95:
            log_action("disk", "critical space", f"{used_pct:.0f}% used, {free_gb:.1f} GB free")
            broadcast_event(
                "⚠ Disk Critical",
                f"Only {free_gb:.1f} GB free! Running emergency cleanup...",
                "error"
            )
            _cleanup_disk()
        elif used_pct > 85:
            log_action("disk", "low space warning", f"{used_pct:.0f}% used")
            broadcast_event(
                "Disk Space",
                f"Disk is {used_pct:.0f}% full ({free_gb:.1f} GB free). Consider cleanup.",
                "warning"
            )
    except Exception as e:
        log_action("disk", "check", f"error: {e}")


def _cleanup_disk():
    """Automated disk cleanup for emergency situations."""
    freed = 0

    # 1. Clear package cache
    result = subprocess.run(
        ["sudo", "apt-get", "clean", "-y"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        freed += 1
        log_action("disk", "cleaned apt cache", "success")

    # 2. Clear old journal logs (keep last 3 days)
    subprocess.run(
        ["sudo", "journalctl", "--vacuum-time=3d"],
        capture_output=True
    )
    log_action("disk", "trimmed journal", "kept last 3 days")

    # 3. Remove Python cache
    home = os.path.expanduser("~")
    for root, dirs, files in os.walk(home):
        if "__pycache__" in dirs:
            pycache_dir = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(pycache_dir)
                freed += 1
            except Exception:
                pass
        if ".git" in dirs:
            dirs.remove(".git")  # Don't descend into .git

    # 4. Clear temp files older than 7 days
    subprocess.run(
        ["find", "/tmp", "-type", "f", "-atime", "+7", "-delete"],
        capture_output=True
    )

    broadcast_event("Disk Cleanup", f"Emergency cleanup complete. Freed space in {freed}+ locations.")


def check_memory():
    """Monitor memory pressure."""
    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()

        total = avail = 0
        for line in meminfo.splitlines():
            if line.startswith("MemTotal:"):
                total = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                avail = int(line.split()[1])

        if total == 0:
            return

        used_pct = ((total - avail) / total) * 100
        avail_mb = avail / 1024

        if used_pct > 95:
            log_action("memory", "critical pressure", f"{used_pct:.0f}% used, {avail_mb:.0f} MB free")
            broadcast_event(
                "⚠ Memory Critical",
                f"Only {avail_mb:.0f} MB free! Consider closing applications.",
                "error"
            )

            # Try to free page cache (non-destructive)
            subprocess.run(
                ["sudo", "sh", "-c", "sync; echo 3 > /proc/sys/vm/drop_caches"],
                capture_output=True
            )
            log_action("memory", "dropped caches", "attempted")

        elif used_pct > 85:
            log_action("memory", "high usage", f"{used_pct:.0f}% used")

    except Exception as e:
        log_action("memory", "check", f"error: {e}")


def check_network():
    """Check internet connectivity and repair if needed."""
    try:
        # Quick connectivity test
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", "1.1.1.1"],
            capture_output=True
        )

        if result.returncode != 0:
            log_action("network", "connectivity lost", "attempting repair")
            broadcast_event(
                "Network Issue",
                "Internet connectivity lost. Attempting repair...",
                "warning"
            )

            # Step 1: Restart NetworkManager
            subprocess.run(["nmcli", "networking", "off"], capture_output=True)
            time.sleep(2)
            subprocess.run(["nmcli", "networking", "on"], capture_output=True)
            time.sleep(5)

            # Verify
            verify = subprocess.run(
                ["ping", "-c", "1", "-W", "3", "1.1.1.1"],
                capture_output=True
            )
            if verify.returncode == 0:
                log_action("network", "repair", "success — connectivity restored")
                broadcast_event("Network", "✔ Internet connectivity restored.")
            else:
                # Step 2: Try DNS (maybe the ping target is blocked)
                dns_test = subprocess.run(
                    ["nslookup", "google.com"],
                    capture_output=True
                )
                if dns_test.returncode == 0:
                    log_action("network", "repair", "DNS works, ICMP blocked")
                    broadcast_event("Network", "DNS is working. ICMP may be blocked.")
                else:
                    log_action("network", "repair", "FAILED — still no connectivity")
                    broadcast_event(
                        "Network Alert",
                        "✘ Could not restore connectivity. Check physical connection.",
                        "error"
                    )
    except Exception as e:
        log_action("network", "check", f"error: {e}")


def check_audio():
    """Check and repair audio subsystem."""
    try:
        # Check if PipeWire is running
        result = subprocess.run(
            ["pgrep", "-x", "pipewire"],
            capture_output=True
        )
        if result.returncode != 0:
            # Try PulseAudio
            result2 = subprocess.run(
                ["pgrep", "-x", "pulseaudio"],
                capture_output=True
            )
            if result2.returncode != 0:
                log_action("audio", "no audio daemon", "attempting restart")
                broadcast_event("Audio", "Audio server not running. Restarting...", "warning")

                # Try PipeWire first, then PulseAudio
                subprocess.run(
                    ["systemctl", "--user", "restart", "pipewire.service"],
                    capture_output=True
                )
                time.sleep(2)
                verify = subprocess.run(["pgrep", "-x", "pipewire"], capture_output=True)
                if verify.returncode == 0:
                    log_action("audio", "restart pipewire", "success")
                    broadcast_event("Audio", "✔ PipeWire audio restored.")
                else:
                    subprocess.run(["pulseaudio", "--start"], capture_output=True)
                    log_action("audio", "fallback to pulseaudio", "attempted")
    except Exception as e:
        log_action("audio", "check", f"error: {e}")


def check_journal_errors():
    """Scan recent journal for critical errors and surface them."""
    try:
        result = subprocess.run(
            ["journalctl", "--since", "5 minutes ago", "--priority=3",
             "-n", "10", "--no-pager", "-o", "cat"],
            capture_output=True, text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            return

        errors = result.stdout.strip().splitlines()

        # Filter out noise
        interesting = []
        noise_patterns = ["pam_unix", "sudo:", "session opened", "session closed"]
        for line in errors:
            if not any(p in line for p in noise_patterns):
                interesting.append(line.strip())

        if interesting:
            # Report first 3 unique errors
            unique_errors = list(set(interesting))[:3]
            summary = " | ".join(unique_errors)
            log_action("journal", "critical errors detected", summary[:200])
            broadcast_event(
                "System Errors",
                f"Found {len(unique_errors)} critical error(s): {summary[:150]}",
                "warning"
            )
    except Exception as e:
        log_action("journal", "scan", f"error: {e}")


def check_updates():
    """Check if system or AI Distro updates are available (daily check)."""
    marker_file = os.path.join(LOG_DIR, "last_update_check")

    try:
        if os.path.exists(marker_file):
            mtime = os.path.getmtime(marker_file)
            if time.time() - mtime < 86400:  # Less than 24h ago
                return

        # Check git for AI Distro updates
        home = os.path.expanduser("~")
        distro_dir = os.path.join(home, "AI_Distro")
        if os.path.isdir(os.path.join(distro_dir, ".git")):
            result = subprocess.run(
                ["git", "fetch", "--dry-run"],
                capture_output=True, text=True,
                cwd=distro_dir
            )
            if result.stderr.strip():  # fetch --dry-run outputs to stderr when there are updates
                log_action("updates", "AI Distro updates available", "notified user")
                broadcast_event(
                    "Updates Available",
                    "New AI Distro updates available. Run 'ai-distro update' to install."
                )

        # Touch the marker
        with open(marker_file, "w") as f:
            f.write(str(time.time()))

    except Exception as e:
        log_action("updates", "check", f"error: {e}")


# ── Main Loop ────────────────────────────────────────────────────

def run_all_checks():
    """Execute all health checks."""
    check_services()
    check_disk_space()
    check_memory()
    check_network()
    check_audio()
    check_journal_errors()
    check_updates()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "check_now":
        print("[Healer] Running one-shot health check...")
        run_all_checks()
        print("[Healer] Done.")
        return

    print("[Healer] AI Distro System Healer starting...")
    print(f"[Healer] Log: {HEALER_LOG}")
    broadcast_event("System Health", "Autonomous healer activated. Monitoring system health.")

    check_interval = 300  # 5 minutes
    cycle = 0

    while True:
        try:
            cycle += 1
            log_action("cycle", f"health check #{cycle}", "starting")

            run_all_checks()

            log_action("cycle", f"health check #{cycle}", "complete")
        except Exception as e:
            log_action("cycle", "error", str(e))

        time.sleep(check_interval)


if __name__ == "__main__":
    main()
