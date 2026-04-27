#!/usr/bin/env python3
"""
Hardware Events Listener — "The Digital Nervous System"

Listens on D-Bus for hardware events (USB plug/unplug, battery changes,
network state changes) and sends them to the agent via IPC.

This is the missing piece that makes the README claim "Real-time reaction
to hardware via D-Bus and udev" actually true.
"""
import json
import os
import socket
import subprocess
import time

try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False

AGENT_SOCKET = os.environ.get("AI_DISTRO_IPC_SOCKET", "/run/ai-distro/agent.sock")
EVENT_SOCKET = "/tmp/ai-distro-events.sock"


def send_to_agent(action, payload):
    """Send an event to the agent via IPC."""
    request = {"version": 1, "name": action, "payload": payload}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(5.0)
            client.connect(AGENT_SOCKET)
            client.sendall(json.dumps(request).encode("utf-8") + b"\n")
    except Exception as e:
        print(f"Hardware Events: IPC error: {e}")


def broadcast_hud_event(title, message, event_type="info"):
    """Send an event to the HUD overlay."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(EVENT_SOCKET)
            event = {"type": event_type, "title": title, "message": message}
            client.sendall(json.dumps(event).encode("utf-8") + b"\n")
    except Exception:
        pass


# ── D-Bus Signal Handlers ─────────────────────────────────────────────

def on_udev_device_added(device_path):
    """Called when a USB device is plugged in."""
    msg = f"New device detected: {device_path}"
    print(f"Hardware Events: {msg}")
    broadcast_hud_event("Hardware", msg)
    send_to_agent("proactive_suggestion", json.dumps({
        "trigger": "usb_connected",
        "message": f"I detected a new device was plugged in ({device_path}). "
                   "Would you like me to check what it is?"
    }))


def on_udev_device_removed(device_path):
    """Called when a USB device is unplugged."""
    msg = f"Device removed: {device_path}"
    print(f"Hardware Events: {msg}")
    broadcast_hud_event("Hardware", msg)


def on_battery_changed(properties_changed, *args):
    """Called when battery properties change via UPower."""
    if not isinstance(properties_changed, dict):
        return

    percentage = properties_changed.get("Percentage")
    state = properties_changed.get("State")

    if percentage is not None:
        pct = int(percentage)
        if pct <= 10:
            broadcast_hud_event(
                "⚡ Critical Battery",
                f"Battery at {pct}%! Plug in NOW or I'll hibernate.",
                "warning"
            )
            send_to_agent("proactive_suggestion", json.dumps({
                "trigger": "critical_battery",
                "message": f"Battery is critically low at {pct}%. "
                           "Should I save your work and hibernate?"
            }))
        elif pct <= 20:
            broadcast_hud_event("Battery", f"Battery at {pct}%. Consider plugging in.")

    if state is not None:
        # State: 1=charging, 2=discharging, 4=fully charged
        if state == 1:
            broadcast_hud_event("Battery", "Charger connected. Charging...")
        elif state == 4:
            broadcast_hud_event("Battery", "Fully charged! You can unplug now.")


def on_network_state_changed(state):
    """Called when NetworkManager connectivity changes."""
    # NM states: 0=unknown, 1=asleep, 2=disconnected, 3=disconnecting,
    # 4=connecting, 5=connected_local, 6=connected_site, 7=connected_global
    state_names = {
        0: "Unknown", 1: "Asleep", 2: "Disconnected", 3: "Disconnecting",
        4: "Connecting", 5: "Local only", 6: "Site only", 7: "Connected"
    }
    name = state_names.get(state, f"State {state}")
    print(f"Hardware Events: Network state → {name}")

    if state == 2:
        broadcast_hud_event(
            "Network", "Internet disconnected. I'll try to reconnect.", "warning"
        )
        send_to_agent("proactive_suggestion", json.dumps({
            "trigger": "network_lost",
            "message": "Your internet connection dropped. Want me to troubleshoot?"
        }))
    elif state == 7:
        broadcast_hud_event("Network", "Internet connection restored.")


# ── Main Loop ─────────────────────────────────────────────────────────

def run_dbus_listener():
    """Start the D-Bus event loop."""
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # Listen for UPower battery changes
    try:
        bus.add_signal_receiver(
            on_battery_changed,
            signal_name="PropertiesChanged",
            dbus_interface="org.freedesktop.DBus.Properties",
            path="/org/freedesktop/UPower/devices/battery_BAT0"
        )
        print("Hardware Events: ✔ Listening for battery changes")
    except Exception as e:
        print(f"Hardware Events: ⚠ Battery listener failed: {e}")

    # Listen for NetworkManager state changes
    try:
        bus.add_signal_receiver(
            on_network_state_changed,
            signal_name="StateChanged",
            dbus_interface="org.freedesktop.NetworkManager"
        )
        print("Hardware Events: ✔ Listening for network changes")
    except Exception as e:
        print(f"Hardware Events: ⚠ Network listener failed: {e}")

    # Listen for UDisks2 device events (USB drives)
    try:
        bus.add_signal_receiver(
            on_udev_device_added,
            signal_name="InterfacesAdded",
            dbus_interface="org.freedesktop.DBus.ObjectManager",
            bus_name="org.freedesktop.UDisks2"
        )
        bus.add_signal_receiver(
            on_udev_device_removed,
            signal_name="InterfacesRemoved",
            dbus_interface="org.freedesktop.DBus.ObjectManager",
            bus_name="org.freedesktop.UDisks2"
        )
        print("Hardware Events: ✔ Listening for USB device changes")
    except Exception as e:
        print(f"Hardware Events: ⚠ USB listener failed: {e}")

    print("Hardware Events: Digital Nervous System active.")

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("Hardware Events: Shutting down.")


def run_polling_fallback():
    """Fallback: poll for hardware changes without D-Bus."""
    print("Hardware Events: Running in polling mode (D-Bus not available)")
    last_battery = None
    last_network = None

    while True:
        try:
            # Check battery
            bat_path = "/sys/class/power_supply/BAT0/capacity"
            if os.path.exists(bat_path):
                with open(bat_path) as f:
                    pct = int(f.read().strip())
                if last_battery is not None and pct != last_battery:
                    if pct <= 10:
                        broadcast_hud_event("⚡ Battery", f"Critical: {pct}%", "warning")
                    elif pct <= 20 and last_battery > 20:
                        broadcast_hud_event("Battery", f"Low: {pct}%")
                last_battery = pct

            # Check network
            try:
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "STATE", "general"],
                    capture_output=True, text=True, timeout=5
                )
                state = result.stdout.strip()
                if last_network is not None and state != last_network:
                    if "disconnect" in state:
                        broadcast_hud_event("Network", "Connection lost", "warning")
                    elif "connected" in state and "disconnect" in (last_network or ""):
                        broadcast_hud_event("Network", "Connection restored")
                last_network = state
            except Exception:
                pass

        except Exception as e:
            print(f"Hardware Events poll error: {e}")

        time.sleep(30)


def main():
    if HAS_DBUS:
        try:
            run_dbus_listener()
        except Exception as e:
            print(f"Hardware Events: D-Bus listener crashed: {e}")
            print("Hardware Events: Falling back to polling mode")
            run_polling_fallback()
    else:
        print("Hardware Events: D-Bus bindings not available, using polling fallback")
        run_polling_fallback()


if __name__ == "__main__":
    main()
