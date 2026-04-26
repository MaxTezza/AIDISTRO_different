#!/usr/bin/env python3
"""
AI Distro — Bluetooth & Audio Device Manager

Auto-detects headphones, speakers, and microphones. Provides natural language
switching ("switch to my AirPods") and event-driven notifications when devices
connect or disconnect.

Architecture:
  - bluetoothctl for BT discovery, pairing, and connection
  - PipeWire/PulseAudio for audio sink/source management
  - Event bus integration for device connect/disconnect notifications
  - Voice-friendly device naming via aliases

Usage:
  python3 bluetooth_audio.py scan              # Discover nearby BT devices
  python3 bluetooth_audio.py list              # List paired/connected devices
  python3 bluetooth_audio.py connect <name>    # Connect by name or MAC
  python3 bluetooth_audio.py disconnect <name> # Disconnect a device
  python3 bluetooth_audio.py switch <name>     # Switch audio output to device
  python3 bluetooth_audio.py inputs            # List audio inputs (mics)
  python3 bluetooth_audio.py outputs           # List audio outputs (speakers)
  python3 bluetooth_audio.py set-input <name>  # Set default microphone
  python3 bluetooth_audio.py set-output <name> # Set default speaker
  python3 bluetooth_audio.py alias <mac> <name> # Set a friendly name
  python3 bluetooth_audio.py monitor           # Watch for device events
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ALIASES_FILE = Path(os.path.expanduser("~/.config/ai-distro/bt_aliases.json"))


def _run(cmd, timeout=10):
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", "Command timed out"


def _load_aliases():
    if ALIASES_FILE.exists():
        with open(ALIASES_FILE) as f:
            return json.load(f)
    return {}


def _save_aliases(aliases):
    ALIASES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ALIASES_FILE, "w") as f:
        json.dump(aliases, f, indent=2)


def _resolve_name(name_or_mac, devices=None):
    """Resolve a friendly name or partial MAC to a full MAC address."""
    if re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", name_or_mac):
        return name_or_mac

    aliases = _load_aliases()
    name_lower = name_or_mac.lower()

    # Check aliases first
    for mac, alias in aliases.items():
        if name_lower in alias.lower():
            return mac

    # Check paired devices
    if devices is None:
        devices = list_devices()
    for dev in devices:
        if name_lower in dev.get("name", "").lower():
            return dev.get("mac", "")
        if name_lower in dev.get("alias", "").lower():
            return dev.get("mac", "")

    return name_or_mac


def _has_pipewire():
    """Check if PipeWire is the audio server."""
    code, out, _ = _run(["pw-cli", "info", "0"])
    return code == 0


def _has_pulseaudio():
    """Check if PulseAudio (or pipewire-pulse) is available."""
    code, _, _ = _run(["pactl", "info"])
    return code == 0


# ═══════════════════════════════════════════════════════════════════
# Bluetooth Operations
# ═══════════════════════════════════════════════════════════════════

def scan(duration=10):
    """Scan for nearby Bluetooth devices."""
    # Start scan
    _run(["bluetoothctl", "scan", "on"], timeout=2)
    time.sleep(min(duration, 15))
    _run(["bluetoothctl", "scan", "off"], timeout=2)

    code, out, _ = _run(["bluetoothctl", "devices"])
    if code != 0:
        return {"error": "bluetoothctl not available"}

    devices = []
    for line in out.split("\n"):
        m = re.match(r"Device\s+([0-9A-Fa-f:]+)\s+(.+)", line)
        if m:
            devices.append({"mac": m.group(1), "name": m.group(2)})

    return {"found": len(devices), "devices": devices}


def list_devices():
    """List paired and connected devices."""
    code, paired_out, _ = _run(["bluetoothctl", "devices", "Paired"])
    if code != 0:
        # Fallback to all devices
        code, paired_out, _ = _run(["bluetoothctl", "devices"])

    if code != 0:
        return []

    aliases = _load_aliases()
    devices = []

    for line in paired_out.split("\n"):
        m = re.match(r"Device\s+([0-9A-Fa-f:]+)\s+(.+)", line)
        if not m:
            continue

        mac = m.group(1)
        name = m.group(2)

        # Check connection status
        info_code, info_out, _ = _run(["bluetoothctl", "info", mac])
        connected = "Connected: yes" in info_out
        device_type = "unknown"
        if "Audio Sink" in info_out or "audio-card" in info_out.lower():
            device_type = "audio"
        elif "input-" in info_out.lower():
            device_type = "input"

        dev = {
            "mac": mac,
            "name": name,
            "alias": aliases.get(mac, name),
            "connected": connected,
            "type": device_type,
        }
        devices.append(dev)

    return devices


def connect_device(name_or_mac):
    """Connect to a Bluetooth device."""
    mac = _resolve_name(name_or_mac)

    # Try to pair first if needed
    _run(["bluetoothctl", "pair", mac], timeout=15)
    _run(["bluetoothctl", "trust", mac])

    code, out, err = _run(["bluetoothctl", "connect", mac], timeout=15)

    if code == 0 or "successful" in out.lower():
        return {"status": "ok", "device": mac, "message": f"Connected to {name_or_mac}"}
    return {"error": f"Failed to connect: {err or out}", "device": mac}


def disconnect_device(name_or_mac):
    """Disconnect a Bluetooth device."""
    mac = _resolve_name(name_or_mac)
    code, out, err = _run(["bluetoothctl", "disconnect", mac])

    if code == 0:
        return {"status": "ok", "device": mac}
    return {"error": f"Failed to disconnect: {err or out}"}


def set_alias(mac, alias):
    """Set a friendly name for a device."""
    aliases = _load_aliases()
    aliases[mac] = alias
    _save_aliases(aliases)
    return {"status": "ok", "mac": mac, "alias": alias}


# ═══════════════════════════════════════════════════════════════════
# Audio Operations
# ═══════════════════════════════════════════════════════════════════

def list_audio_outputs():
    """List audio output devices (sinks)."""
    if _has_pipewire() or _has_pulseaudio():
        code, out, _ = _run(["pactl", "list", "short", "sinks"])
        if code != 0:
            return []

        sinks = []
        for line in out.split("\n"):
            parts = line.split("\t")
            if len(parts) >= 2:
                # Get the default
                _, default_out, _ = _run(["pactl", "get-default-sink"])
                sinks.append({
                    "id": parts[0],
                    "name": parts[1],
                    "default": parts[1] == default_out.strip(),
                    "state": parts[4] if len(parts) > 4 else "unknown",
                })
        return sinks
    return [{"error": "No audio server found"}]


def list_audio_inputs():
    """List audio input devices (sources/mics)."""
    if not (_has_pipewire() or _has_pulseaudio()):
        return [{"error": "No audio server found"}]

    code, out, _ = _run(["pactl", "list", "short", "sources"])
    if code != 0:
        return []

    sources = []
    _, default_out, _ = _run(["pactl", "get-default-source"])
    for line in out.split("\n"):
        parts = line.split("\t")
        if len(parts) >= 2 and ".monitor" not in parts[1]:
            sources.append({
                "id": parts[0],
                "name": parts[1],
                "default": parts[1] == default_out.strip(),
            })
    return sources


def set_default_output(name_or_id):
    """Set the default audio output sink."""
    sinks = list_audio_outputs()
    target = None

    for s in sinks:
        if name_or_id.lower() in s.get("name", "").lower() or s.get("id") == name_or_id:
            target = s["name"]
            break

    if not target:
        # Try as raw sink name
        target = name_or_id

    code, _, err = _run(["pactl", "set-default-sink", target])
    if code == 0:
        return {"status": "ok", "output": target}
    return {"error": f"Failed: {err}", "output": target}


def set_default_input(name_or_id):
    """Set the default audio input source."""
    sources = list_audio_inputs()
    target = None

    for s in sources:
        if name_or_id.lower() in s.get("name", "").lower() or s.get("id") == name_or_id:
            target = s["name"]
            break

    if not target:
        target = name_or_id

    code, _, err = _run(["pactl", "set-default-source", target])
    if code == 0:
        return {"status": "ok", "input": target}
    return {"error": f"Failed: {err}", "input": target}


def switch_audio_to(name_or_mac):
    """Connect BT device and switch audio output to it."""
    # First ensure connected
    mac = _resolve_name(name_or_mac)
    connect_result = connect_device(mac)

    # Wait for audio sink to appear
    time.sleep(2)

    # Find matching sink
    sinks = list_audio_outputs()
    mac_underscored = mac.replace(":", "_")
    for s in sinks:
        if mac_underscored in s.get("name", ""):
            set_default_output(s["name"])
            return {
                "status": "ok",
                "device": name_or_mac,
                "sink": s["name"],
                "connect": connect_result,
            }

    # Try fuzzy match by name
    devices = list_devices()
    for dev in devices:
        if dev["mac"] == mac:
            dev_name = dev["name"].lower().replace(" ", "")
            for s in sinks:
                if dev_name in s.get("name", "").lower().replace("_", ""):
                    set_default_output(s["name"])
                    return {"status": "ok", "device": name_or_mac, "sink": s["name"]}

    return {"status": "connected_no_audio", "device": name_or_mac,
            "message": "Device connected but audio sink not found. It may need a moment."}


def monitor():
    """Monitor for device connect/disconnect events."""
    print("Monitoring Bluetooth events... (Ctrl+C to stop)")
    try:
        proc = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True
        )
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if "Connected: yes" in line or "Connected: no" in line:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"  [{ts}] {line}")
            elif "NEW" in line or "DEL" in line or "CHG" in line:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"  [{ts}] {line}")
    except KeyboardInterrupt:
        print("\nStopped monitoring.")
    finally:
        proc.terminate()


def main():
    if len(sys.argv) < 2:
        print("Usage: bluetooth_audio.py <scan|list|connect|disconnect|switch|"
              "inputs|outputs|set-input|set-output|alias|monitor>")
        return

    cmd = sys.argv[1]
    arg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if cmd == "scan":
        print(json.dumps(scan(), indent=2))
    elif cmd == "list":
        print(json.dumps(list_devices(), indent=2))
    elif cmd == "connect":
        print(json.dumps(connect_device(arg), indent=2))
    elif cmd == "disconnect":
        print(json.dumps(disconnect_device(arg), indent=2))
    elif cmd == "switch":
        print(json.dumps(switch_audio_to(arg), indent=2))
    elif cmd == "inputs":
        print(json.dumps(list_audio_inputs(), indent=2))
    elif cmd == "outputs":
        print(json.dumps(list_audio_outputs(), indent=2))
    elif cmd == "set-input":
        print(json.dumps(set_default_input(arg), indent=2))
    elif cmd == "set-output":
        print(json.dumps(set_default_output(arg), indent=2))
    elif cmd == "alias":
        mac = sys.argv[2] if len(sys.argv) > 2 else ""
        name = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        print(json.dumps(set_alias(mac, name), indent=2))
    elif cmd == "monitor":
        monitor()
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
