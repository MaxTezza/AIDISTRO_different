#!/usr/bin/env python3
"""
AI Distro — Automation Recipes

"If X then Y" rules defined through natural language, confirmed from
Bayesian pattern detection, or created manually. Recipes fire automatically
when their trigger conditions are met.

Trigger types:
  - time       → "at 9am", "every monday at 8pm"
  - wifi       → "when I connect to HomeWifi"
  - battery    → "when battery drops below 20%"
  - app        → "when I open Firefox"
  - usb        → "when a USB drive is plugged in"
  - pattern    → Auto-suggested from Bayesian engine observations

Usage:
  python3 automation_recipes.py list
  python3 automation_recipes.py add "when I connect to work wifi" "open slack and email"
  python3 automation_recipes.py remove <id>
  python3 automation_recipes.py enable <id>
  python3 automation_recipes.py disable <id>
  python3 automation_recipes.py check        # Evaluate all triggers now
  python3 automation_recipes.py suggest      # Get Bayesian-derived suggestions
  python3 automation_recipes.py serve        # Run as daemon (continuous evaluation)
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RECIPES_FILE = Path(os.path.expanduser("~/.config/ai-distro/recipes.json"))
AGENT_SOCKET = os.environ.get("AI_DISTRO_IPC_SOCKET", "/run/ai-distro/agent.sock")
CHECK_INTERVAL = 30  # seconds

# Add parent dir to path for Bayesian import
sys.path.insert(0, os.path.dirname(__file__))


def _load_recipes():
    RECIPES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if RECIPES_FILE.exists():
        with open(RECIPES_FILE) as f:
            return json.load(f)
    return {"recipes": [], "next_id": 1}


def _save_recipes(data):
    RECIPES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RECIPES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _send_to_agent(command):
    """Send a command to the AI agent via IPC socket."""
    try:
        if not os.path.exists(AGENT_SOCKET):
            return {"error": "Agent socket not found"}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect(AGENT_SOCKET)
            request = {"version": 1, "name": "execute_intent", "payload": command}
            s.sendall(json.dumps(request).encode("utf-8") + b"\n")
            return {"status": "sent", "command": command}
    except Exception as e:
        return {"error": str(e)}


def _parse_trigger(trigger_text):
    """Parse a natural language trigger into a structured trigger object."""
    text = trigger_text.lower().strip()
    trigger = {"raw": trigger_text, "type": "manual"}

    # Time-based: "at 9am", "at 8:30pm", "every day at 9am"
    time_match = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        ampm = time_match.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        trigger["type"] = "time"
        trigger["hour"] = hour
        trigger["minute"] = minute

        # Day-specific
        days = []
        for day_name, day_num in [("monday", 0), ("tuesday", 1), ("wednesday", 2),
                                   ("thursday", 3), ("friday", 4), ("saturday", 5), ("sunday", 6)]:
            if day_name in text:
                days.append(day_num)
        if "weekday" in text:
            days = [0, 1, 2, 3, 4]
        elif "weekend" in text:
            days = [5, 6]
        trigger["days"] = days or list(range(7))  # Default: every day
        return trigger

    # WiFi-based
    wifi_match = re.search(r"connect(?:ed)?\s+to\s+(.+?)(?:\s+wifi|\s*$)", text)
    if wifi_match or "wifi" in text:
        trigger["type"] = "wifi"
        trigger["ssid"] = wifi_match.group(1).strip() if wifi_match else ""
        return trigger

    # Battery-based
    batt_match = re.search(r"battery\s+(?:drops?\s+)?(?:below|under|at)\s+(\d+)", text)
    if batt_match:
        trigger["type"] = "battery"
        trigger["threshold"] = int(batt_match.group(1))
        trigger["direction"] = "below"
        return trigger

    # App-based
    app_match = re.search(r"(?:open|launch|start)\s+(.+)", text)
    if app_match:
        trigger["type"] = "app"
        trigger["app_name"] = app_match.group(1).strip()
        return trigger

    # USB-based
    if "usb" in text and ("plug" in text or "connect" in text or "insert" in text):
        trigger["type"] = "usb"
        return trigger

    return trigger


# ═══════════════════════════════════════════════════════════════════
# Recipe Management
# ═══════════════════════════════════════════════════════════════════

def add_recipe(trigger_text, action_text):
    """Add a new automation recipe."""
    data = _load_recipes()
    trigger = _parse_trigger(trigger_text)

    recipe = {
        "id": data["next_id"],
        "trigger": trigger,
        "action": action_text,
        "enabled": True,
        "created": datetime.now().isoformat(),
        "last_fired": None,
        "fire_count": 0,
    }

    data["recipes"].append(recipe)
    data["next_id"] += 1
    _save_recipes(data)

    return {"status": "ok", "recipe": recipe}


def remove_recipe(recipe_id):
    data = _load_recipes()
    data["recipes"] = [r for r in data["recipes"] if r["id"] != recipe_id]
    _save_recipes(data)
    return {"status": "ok", "removed": recipe_id}


def toggle_recipe(recipe_id, enabled):
    data = _load_recipes()
    for r in data["recipes"]:
        if r["id"] == recipe_id:
            r["enabled"] = enabled
            _save_recipes(data)
            return {"status": "ok", "id": recipe_id, "enabled": enabled}
    return {"error": f"Recipe {recipe_id} not found"}


def list_recipes():
    return _load_recipes()["recipes"]


# ═══════════════════════════════════════════════════════════════════
# Trigger Evaluation
# ═══════════════════════════════════════════════════════════════════

def _get_wifi_ssid():
    try:
        r = subprocess.run(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
                           capture_output=True, text=True, timeout=5)
        for line in r.stdout.strip().split("\n"):
            if line.startswith("yes:"):
                return line.split(":", 1)[1]
    except Exception:
        pass
    return None


def _get_battery_level():
    try:
        import psutil
        batt = psutil.sensors_battery()
        return batt.percent if batt else None
    except ImportError:
        # Fallback to sysfs
        try:
            cap = Path("/sys/class/power_supply/BAT0/capacity").read_text().strip()
            return int(cap)
        except Exception:
            return None


def _check_trigger(trigger):
    """Check if a trigger condition is currently met."""
    t = trigger.get("type", "manual")

    if t == "time":
        now = datetime.now()
        if now.weekday() not in trigger.get("days", range(7)):
            return False
        if now.hour == trigger.get("hour") and now.minute == trigger.get("minute"):
            return True
        return False

    elif t == "wifi":
        ssid = _get_wifi_ssid()
        target = trigger.get("ssid", "")
        if not target:
            return ssid is not None
        return ssid and target.lower() in ssid.lower()

    elif t == "battery":
        level = _get_battery_level()
        if level is None:
            return False
        threshold = trigger.get("threshold", 20)
        return level <= threshold

    elif t == "app":
        app_name = trigger.get("app_name", "")
        try:
            r = subprocess.run(["pgrep", "-fi", app_name],
                               capture_output=True, timeout=3)
            return r.returncode == 0
        except Exception:
            return False

    elif t == "usb":
        # Check if any USB mass storage is mounted
        try:
            r = subprocess.run(["lsblk", "-nro", "TRAN"],
                               capture_output=True, text=True, timeout=3)
            return "usb" in r.stdout
        except Exception:
            return False

    return False


def check_all():
    """Evaluate all recipe triggers and fire matching ones."""
    data = _load_recipes()
    fired = []

    for recipe in data["recipes"]:
        if not recipe.get("enabled", True):
            continue

        # Debounce: don't fire more than once per minute
        last = recipe.get("last_fired")
        if last:
            try:
                elapsed = (datetime.now() - datetime.fromisoformat(last)).total_seconds()
                if elapsed < 60:
                    continue
            except (ValueError, TypeError):
                pass

        if _check_trigger(recipe.get("trigger", {})):
            result = _send_to_agent(recipe["action"])
            recipe["last_fired"] = datetime.now().isoformat()
            recipe["fire_count"] = recipe.get("fire_count", 0) + 1
            fired.append({"id": recipe["id"], "action": recipe["action"], "result": result})

    if fired:
        _save_recipes(data)

    return fired


def suggest_recipes():
    """Generate recipe suggestions from Bayesian patterns."""
    try:
        from bayesian_engine import BayesianEngine
        engine = BayesianEngine()
        profile = engine.get_user_profile()

        suggestions = []
        for pattern in profile.get("behavioral_patterns", [])[:5]:
            ctx = pattern.get("context", "")
            action = pattern.get("action", "")
            prob = pattern.get("probability", 0)

            parts = ctx.split("|")
            time_bucket = parts[0] if parts else "unknown"
            day_type = parts[1] if len(parts) > 1 else ""

            time_map = {
                "early_morning": "6:00am", "morning": "9:00am",
                "afternoon": "1:00pm", "evening": "6:00pm", "night": "9:00pm"
            }
            trigger = f"every {day_type or 'day'} at {time_map.get(time_bucket, '9:00am')}"

            suggestions.append({
                "trigger": trigger,
                "action": action,
                "confidence": f"{prob:.0%}",
                "observations": pattern.get("count", 0),
            })

        return suggestions
    except Exception as e:
        return [{"error": str(e)}]


# ═══════════════════════════════════════════════════════════════════
# Daemon Mode
# ═══════════════════════════════════════════════════════════════════

def serve():
    """Run as a daemon, evaluating triggers every CHECK_INTERVAL seconds."""
    print(f"Automation Engine started — checking every {CHECK_INTERVAL}s")
    while True:
        try:
            fired = check_all()
            if fired:
                for f in fired:
                    print(f"  ⚡ Fired recipe #{f['id']}: {f['action']}")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(CHECK_INTERVAL)


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage: automation_recipes.py <list|add|remove|enable|disable|check|suggest|serve>")
        return

    cmd = sys.argv[1]

    if cmd == "list":
        recipes = list_recipes()
        if not recipes:
            print("No recipes defined. Use 'add' to create one.")
            return
        for r in recipes:
            status = "✓" if r.get("enabled") else "○"
            fires = r.get("fire_count", 0)
            print(f"  {status} #{r['id']} [{r['trigger']['type']}] → {r['action']} (fired {fires}x)")

    elif cmd == "add":
        trigger = sys.argv[2] if len(sys.argv) > 2 else ""
        action = sys.argv[3] if len(sys.argv) > 3 else ""
        if not trigger or not action:
            print("Usage: add <trigger> <action>")
            print('Example: add "every weekday at 9am" "open slack and email"')
            return
        print(json.dumps(add_recipe(trigger, action), indent=2))

    elif cmd == "remove":
        rid = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(remove_recipe(rid), indent=2))

    elif cmd == "enable":
        rid = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(toggle_recipe(rid, True), indent=2))

    elif cmd == "disable":
        rid = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(toggle_recipe(rid, False), indent=2))

    elif cmd == "check":
        fired = check_all()
        print(json.dumps(fired, indent=2) if fired else "No recipes triggered.")

    elif cmd == "suggest":
        suggestions = suggest_recipes()
        print(json.dumps(suggestions, indent=2))

    elif cmd == "serve":
        serve()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
