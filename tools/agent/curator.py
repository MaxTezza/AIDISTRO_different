#!/usr/bin/env python3
"""
Curator Engine — "The Intuition"

Proactive system monitor that uses the Bayesian Preference Engine to
learn user patterns and make intelligent, context-aware suggestions.

Monitors: battery, disk, system health, time-based events, and user habits.
Learns: what the user does at different times, on different days, in different contexts.
Suggests: proactive actions based on Bayesian posterior predictions.
"""
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Import the Bayesian Engine
sys.path.insert(0, os.path.dirname(__file__))
from bayesian_engine import BayesianEngine

try:
    import psutil
except ImportError:
    psutil = None

DAY_PLANNER_SCRIPT = os.path.join(os.path.dirname(__file__), "day_planner.py")
AGENT_SOCKET = os.environ.get("AI_DISTRO_IPC_SOCKET", "/run/ai-distro/agent.sock")
CHECK_INTERVAL_AC = 60    # seconds — on AC power
CHECK_INTERVAL_BATT = 120  # seconds — on battery (throttled)
GPU_CACHE_FILE = os.path.expanduser("~/.cache/ai-distro/gpu-info.json")


def detect_gpu():
    """Detect GPU/NPU hardware for optimal model inference routing."""
    info = {"nvidia": False, "amd": False, "intel": False, "device": "cpu"}

    # NVIDIA — check for nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            info["nvidia"] = True
            info["gpu_name"] = result.stdout.strip().split("\n")[0]
            info["device"] = "cuda"
    except FileNotFoundError:
        pass

    # AMD — check for rocm-smi
    if not info["nvidia"]:
        try:
            result = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and "GPU" in result.stdout:
                info["amd"] = True
                info["device"] = "rocm"
        except FileNotFoundError:
            pass

    # Intel — check for discrete Arc GPUs via sysfs
    if not info["nvidia"] and not info["amd"]:
        try:
            for card in Path("/sys/class/drm").glob("card*/device/vendor"):
                vendor = card.read_text().strip()
                if vendor == "0x8086":  # Intel vendor ID
                    info["intel"] = True
                    info["device"] = "xpu"
                    break
        except Exception:
            pass

    # Cache result
    os.makedirs(os.path.dirname(GPU_CACHE_FILE), exist_ok=True)
    with open(GPU_CACHE_FILE, "w") as f:
        json.dump(info, f, indent=2)

    return info


class Curator:
    def __init__(self):
        self.bayesian = BayesianEngine()
        self.last_battery_alert = 100
        self.sent_morning_briefing = False
        self.last_suggestion_slot = None
        self.last_action = None  # For action chain tracking
        self.on_battery = False
        self.gpu_info = None

    def log_habit(self, action, outcome="positive", app_context=None):
        """Log a user action to the Bayesian engine."""
        self.bayesian.observe(action, outcome, app_context)

        # Track action chains
        if self.last_action and self.last_action != action:
            self.bayesian.observe_chain(self.last_action, action)
        self.last_action = action

    def send_proactive_request(self, trigger, message):
        request = {
            "version": 1,
            "name": "proactive_suggestion",
            "payload": json.dumps({"trigger": trigger, "message": message})
        }
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(5.0)
                client.connect(AGENT_SOCKET)
                client.sendall(json.dumps(request).encode('utf-8') + b"\n")
        except Exception as e:
            print(f"Curator IPC Error: {e}")

    def check_system(self):
        if not psutil:
            return

        # Battery check
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            if percent <= 15 and self.last_battery_alert > 15:
                self.send_proactive_request(
                    "low_battery",
                    f"Battery is at {percent}%. Enable power saving?"
                )
                self.last_battery_alert = 15
            elif percent > 15:
                self.last_battery_alert = percent

        # Disk space check
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            self.send_proactive_request(
                "low_disk",
                f"Your main drive is {disk.percent}% full. Want me to find files to archive?"
            )

        # High memory usage
        mem = psutil.virtual_memory()
        if mem.percent > 85:
            # Get top memory consumers
            top_procs = sorted(
                psutil.process_iter(['name', 'memory_percent']),
                key=lambda p: p.info.get('memory_percent', 0) or 0,
                reverse=True
            )[:3]
            names = [p.info['name'] for p in top_procs if p.info.get('name')]
            self.send_proactive_request(
                "high_memory",
                f"Memory is at {mem.percent}%. Top consumers: {', '.join(names)}. "
                "Should I close something?"
            )

    def check_time_and_events(self):
        now = datetime.now()
        hour = now.hour

        # Morning Briefing (7 AM - 10 AM)
        if 7 <= hour <= 10 and not self.sent_morning_briefing:
            try:
                res = subprocess.run(
                    [sys.executable, DAY_PLANNER_SCRIPT, "today"],
                    capture_output=True, text=True
                )
                briefing = res.stdout.strip() or "Good morning!"
                self.send_proactive_request("morning_briefing", briefing)
                self.sent_morning_briefing = True
            except Exception:
                pass
        elif hour > 10:
            self.sent_morning_briefing = False

        # Bayesian Predictions — the core intelligence
        predictions = self.bayesian.predict(top_k=3)
        if predictions:
            best = predictions[0]
            slot = (now.year, now.month, now.day, now.hour)
            if self.last_suggestion_slot != slot:
                prob = best["probability"]
                action = best["action"]
                obs = best["observations"]

                if prob >= 0.8:
                    msg = (
                        f"Based on {obs} past observations, you usually "
                        f"'{action}' right about now ({prob:.0%} confidence). "
                        "Shall I set that up?"
                    )
                elif prob >= 0.65:
                    msg = (
                        f"You often '{action}' around this time. "
                        "Want me to get that going?"
                    )
                else:
                    msg = None

                if msg:
                    self.send_proactive_request("bayesian_suggestion", msg)
                    self.last_suggestion_slot = slot

        # Chain predictions — "you usually do X after Y"
        if self.last_action:
            chain_preds = self.bayesian.predict_next(self.last_action, top_k=1)
            if chain_preds and chain_preds[0]["probability"] >= 0.7:
                cp = chain_preds[0]
                self.send_proactive_request(
                    "chain_suggestion",
                    f"After '{self.last_action}', you usually "
                    f"'{cp['action']}'. Shall I?"
                )

    def check_health(self):
        """Checks for failed system services."""
        try:
            res = subprocess.run(
                ["systemctl", "--failed", "--quiet"],
                capture_output=True
            )
            if res.returncode != 0:
                self.send_proactive_request(
                    "system_health",
                    "I noticed some system services failed. Should I run a diagnostic?"
                )
        except Exception:
            pass

    def check_health_reminders(self):
        """Sends periodic reminders for medication, hydration, or movement."""
        now = datetime.now()
        if now.minute == 0:
            # Check if user has set custom health reminders
            reminder_pref = self.bayesian.get_preference("health_reminders")
            if reminder_pref["value"] == "disabled":
                return

            if now.hour == 9:
                self.send_proactive_request(
                    "health_reminder", "Time for your morning medication."
                )
            elif now.hour == 13:
                self.send_proactive_request(
                    "health_reminder", "Don't forget to stay hydrated!"
                )
            elif now.hour == 20:
                self.send_proactive_request(
                    "health_reminder", "Evening routine time."
                )

    def check_self_update(self):
        """Periodically check if the AI should update itself based on preferences."""
        now = datetime.now()
        # Only check once per day at 3 AM
        if now.hour != 3 or now.minute != 0:
            return

        auto_update = self.bayesian.get_preference("auto_update")
        if auto_update["value"] == "enabled":
            self.send_proactive_request(
                "self_update_check",
                "Running scheduled self-update check..."
            )
            # Trigger the self-update action
            request = {
                "version": 1,
                "name": "self_update",
                "payload": "scheduled"
            }
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.settimeout(30.0)
                    client.connect(AGENT_SOCKET)
                    client.sendall(json.dumps(request).encode('utf-8') + b"\n")
            except Exception:
                pass

    def detect_power_state(self):
        """Check if we're on battery and adjust scan interval."""
        if not psutil:
            return
        battery = psutil.sensors_battery()
        if battery:
            was_on_battery = self.on_battery
            self.on_battery = not battery.power_plugged
            if self.on_battery and not was_on_battery:
                print("Curator: Switching to battery-saver mode (slower scan).")
            elif not self.on_battery and was_on_battery:
                print("Curator: AC power restored. Resuming full scan rate.")

    def get_interval(self):
        """Return the appropriate check interval based on power state."""
        return CHECK_INTERVAL_BATT if self.on_battery else CHECK_INTERVAL_AC

    def run(self):
        print("Curator Engine (The Intuition) started — Bayesian mode.")

        # One-time GPU detection
        try:
            self.gpu_info = detect_gpu()
            dev = self.gpu_info.get('device', 'cpu')
            name = self.gpu_info.get('gpu_name', dev)
            print(f"Curator: GPU detected — {name} (inference device: {dev})")
        except Exception as e:
            print(f"Curator: GPU detection skipped: {e}")
            self.gpu_info = {"device": "cpu"}

        while True:
            try:
                self.detect_power_state()
                self.check_system()

                # Skip heavier checks on battery
                if not self.on_battery:
                    self.check_time_and_events()
                    self.check_health()

                self.check_health_reminders()
                self.check_self_update()
            except Exception as e:
                print(f"Curator loop error: {e}")
            time.sleep(self.get_interval())


if __name__ == "__main__":
    curator = Curator()
    if len(sys.argv) > 2 and sys.argv[1] == "log_habit":
        outcome = sys.argv[3] if len(sys.argv) > 3 else "positive"
        app_ctx = sys.argv[4] if len(sys.argv) > 4 else None
        curator.log_habit(sys.argv[2], outcome, app_ctx)
    elif len(sys.argv) > 1 and sys.argv[1] == "predict":
        predictions = curator.bayesian.predict()
        print(json.dumps(predictions, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "profile":
        profile = curator.bayesian.get_user_profile()
        print(json.dumps(profile, indent=2))
    else:
        curator.run()
