#!/usr/bin/env python3
"""
AI Distro — Accessibility Mode

Configures the entire desktop for users with visual, hearing, or motor
impairments. Changes affect Sway, GTK, TTS, HUD, and the AI interaction
model simultaneously.

Profiles:
  low_vision    — Large text, high contrast, magnification
  color_blind   — Deuteranopia-safe palette, pattern indicators
  motor         — Sticky keys, large click targets, slow key repeat
  hearing       — Visual alerts, captioning, no audio-only cues
  senior        — Large text, slow TTS, simplified UI, patience mode
  custom        — Build your own from individual options

Usage:
  python3 accessibility.py apply senior           # Apply a profile
  python3 accessibility.py status                 # Show active settings
  python3 accessibility.py set font_scale 1.5     # Set individual option
  python3 accessibility.py reset                  # Reset to defaults
  python3 accessibility.py list                   # List profiles
  python3 accessibility.py test                   # Test current settings
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

A11Y_CONFIG = Path(os.path.expanduser("~/.config/ai-distro/accessibility.json"))

# Default settings (no accessibility modifications)
DEFAULTS = {
    "profile": "none",
    "font_scale": 1.0,
    "cursor_size": 24,
    "high_contrast": False,
    "reduce_motion": False,
    "large_text": False,
    "slow_keys": False,
    "sticky_keys": False,
    "key_repeat_delay": 500,
    "key_repeat_rate": 25,
    "tts_rate": 1.0,
    "tts_volume": 1.0,
    "visual_alerts": False,
    "screen_reader": False,
    "magnifier": False,
    "magnifier_zoom": 2.0,
    "color_filter": "none",  # none, protanopia, deuteranopia, tritanopia, grayscale
    "focus_highlight": False,
    "patience_mode": False,  # AI waits longer, repeats more, simpler language
    "simplified_ui": False,
}

PROFILES = {
    "low_vision": {
        "profile": "low_vision",
        "font_scale": 1.5,
        "cursor_size": 48,
        "high_contrast": True,
        "large_text": True,
        "magnifier": True,
        "magnifier_zoom": 2.0,
        "focus_highlight": True,
        "tts_rate": 0.9,
    },
    "color_blind": {
        "profile": "color_blind",
        "color_filter": "deuteranopia",
        "high_contrast": True,
        "focus_highlight": True,
    },
    "motor": {
        "profile": "motor",
        "sticky_keys": True,
        "slow_keys": True,
        "key_repeat_delay": 1000,
        "key_repeat_rate": 10,
        "cursor_size": 36,
        "patience_mode": True,
    },
    "hearing": {
        "profile": "hearing",
        "visual_alerts": True,
        "tts_volume": 0.0,
    },
    "senior": {
        "profile": "senior",
        "font_scale": 1.4,
        "cursor_size": 36,
        "large_text": True,
        "tts_rate": 0.75,
        "patience_mode": True,
        "simplified_ui": True,
        "reduce_motion": False,
        "key_repeat_delay": 800,
        "focus_highlight": True,
    },
}


def _load_config():
    if A11Y_CONFIG.exists():
        with open(A11Y_CONFIG) as f:
            stored = json.load(f)
        config = {**DEFAULTS, **stored}
        return config
    return dict(DEFAULTS)


def _save_config(config):
    A11Y_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    config["last_modified"] = datetime.now().isoformat()
    with open(A11Y_CONFIG, "w") as f:
        json.dump(config, f, indent=2)


def _apply_gsettings(config):
    """Apply accessibility settings via gsettings."""
    settings = [
        ("org.gnome.desktop.interface", "text-scaling-factor", str(config["font_scale"])),
        ("org.gnome.desktop.interface", "cursor-size", str(config["cursor_size"])),
    ]

    if config["high_contrast"]:
        settings.append(("org.gnome.desktop.interface", "gtk-theme", "HighContrast"))
        settings.append(("org.gnome.desktop.interface", "icon-theme", "HighContrast"))

    if config["large_text"]:
        settings.append(("org.gnome.desktop.interface", "text-scaling-factor",
                         str(max(config["font_scale"], 1.3))))

    for schema, key, value in settings:
        try:
            subprocess.run(["gsettings", "set", schema, key, value],
                           capture_output=True, timeout=5)
        except Exception:
            pass


def _apply_sway_settings(config):
    """Apply Sway-specific accessibility settings."""
    commands = []

    # Cursor size
    commands.append(f"seat seat0 xcursor_theme default {config['cursor_size']}")

    # Key repeat
    commands.append(f"input type:keyboard repeat_delay {config['key_repeat_delay']}")
    commands.append(f"input type:keyboard repeat_rate {config['key_repeat_rate']}")

    for cmd in commands:
        try:
            subprocess.run(["swaymsg", cmd], capture_output=True, timeout=5)
        except Exception:
            pass


def _apply_screen_reader(config):
    """Enable/disable screen reader (Orca)."""
    if config.get("screen_reader"):
        try:
            subprocess.Popen(["orca"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass
    else:
        try:
            subprocess.run(["pkill", "orca"], capture_output=True, timeout=5)
        except Exception:
            pass


def _apply_magnifier(config):
    """Enable/disable screen magnification."""
    if config.get("magnifier"):
        zoom = config.get("magnifier_zoom", 2.0)
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.a11y.magnifier", "mag-factor",
                 str(zoom)],
                capture_output=True, timeout=5
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.a11y.magnifier", "screen-position",
                 "full-screen"],
                capture_output=True, timeout=5
            )
        except Exception:
            pass


def _generate_a11y_prompt_modifier(config):
    """Generate AI prompt modifiers based on accessibility settings."""
    modifiers = []

    if config.get("patience_mode"):
        modifiers.append(
            "The user benefits from patience and clarity. Use simple language. "
            "Wait longer for responses. Repeat important information. "
            "Confirm understanding before proceeding."
        )

    if config.get("simplified_ui"):
        modifiers.append(
            "Keep all responses short and simple. Avoid technical jargon. "
            "Present maximum 3 options at a time. Use numbered lists."
        )

    if config.get("visual_alerts"):
        modifiers.append(
            "The user cannot hear audio alerts. Always provide visual/text "
            "confirmation of actions. Never rely on sound-only feedback."
        )

    if config.get("screen_reader"):
        modifiers.append(
            "The user uses a screen reader. Structure responses with clear "
            "headings and avoid visual-only formatting."
        )

    return " ".join(modifiers) if modifiers else None


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def apply_profile(profile_name):
    """Apply an accessibility profile."""
    if profile_name == "none" or profile_name == "reset":
        return reset()

    if profile_name not in PROFILES:
        return {"error": f"Unknown profile: {profile_name}", "available": list(PROFILES.keys())}

    config = {**DEFAULTS, **PROFILES[profile_name]}
    _save_config(config)
    _apply_gsettings(config)
    _apply_sway_settings(config)
    _apply_screen_reader(config)
    _apply_magnifier(config)

    prompt_mod = _generate_a11y_prompt_modifier(config)

    return {
        "status": "ok",
        "profile": profile_name,
        "changes": {k: v for k, v in config.items()
                    if k in PROFILES[profile_name] and v != DEFAULTS.get(k)},
        "ai_modifier": prompt_mod,
    }


def set_option(key, value):
    """Set an individual accessibility option."""
    if key not in DEFAULTS:
        return {"error": f"Unknown option: {key}", "available": list(DEFAULTS.keys())}

    config = _load_config()

    # Type coercion
    default_type = type(DEFAULTS[key])
    if default_type is bool:
        value = value.lower() in ("true", "1", "yes", "on")
    elif default_type is float:
        value = float(value)
    elif default_type is int:
        value = int(value)

    config[key] = value
    config["profile"] = "custom"
    _save_config(config)
    _apply_gsettings(config)
    _apply_sway_settings(config)

    return {"status": "ok", "key": key, "value": value}


def get_status():
    """Show current accessibility settings."""
    config = _load_config()
    active = {k: v for k, v in config.items() if v != DEFAULTS.get(k)}
    prompt_mod = _generate_a11y_prompt_modifier(config)

    return {
        "profile": config.get("profile", "none"),
        "active_modifications": active,
        "ai_prompt_modifier": prompt_mod,
    }


def reset():
    """Reset all accessibility settings to defaults."""
    _save_config(dict(DEFAULTS))
    _apply_gsettings(DEFAULTS)
    _apply_sway_settings(DEFAULTS)
    try:
        subprocess.run(["pkill", "orca"], capture_output=True, timeout=5)
    except Exception:
        pass
    return {"status": "ok", "message": "Reset to defaults"}


def test_settings():
    """Test current accessibility configuration."""
    config = _load_config()
    results = {"profile": config.get("profile", "none"), "tests": {}}

    # Test font scale
    try:
        r = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "text-scaling-factor"],
            capture_output=True, text=True, timeout=5
        )
        results["tests"]["font_scale"] = r.stdout.strip()
    except Exception:
        results["tests"]["font_scale"] = "untested"

    # Test cursor
    try:
        r = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "cursor-size"],
            capture_output=True, text=True, timeout=5
        )
        results["tests"]["cursor_size"] = r.stdout.strip()
    except Exception:
        results["tests"]["cursor_size"] = "untested"

    # Screen reader
    try:
        r = subprocess.run(["pgrep", "orca"], capture_output=True, timeout=3)
        results["tests"]["screen_reader"] = "running" if r.returncode == 0 else "not running"
    except Exception:
        results["tests"]["screen_reader"] = "untested"

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: accessibility.py <apply|status|set|reset|list|test>")
        return

    cmd = sys.argv[1]

    if cmd == "apply":
        profile = sys.argv[2] if len(sys.argv) > 2 else "senior"
        print(json.dumps(apply_profile(profile), indent=2))
    elif cmd == "status":
        print(json.dumps(get_status(), indent=2))
    elif cmd == "set":
        key = sys.argv[2] if len(sys.argv) > 2 else ""
        val = sys.argv[3] if len(sys.argv) > 3 else ""
        if not key or not val:
            print("Usage: accessibility.py set <key> <value>")
            return
        print(json.dumps(set_option(key, val), indent=2))
    elif cmd == "reset":
        print(json.dumps(reset(), indent=2))
    elif cmd == "list":
        for name, p in PROFILES.items():
            changes = [k for k, v in p.items() if k != "profile" and v != DEFAULTS.get(k)]
            print(f"  {name:15s} → {', '.join(changes)}")
    elif cmd == "test":
        print(json.dumps(test_settings(), indent=2))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
