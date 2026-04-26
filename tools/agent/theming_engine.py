#!/usr/bin/env python3
"""
AI Distro — Theming Engine

Natural language theme changes across Sway, GTK, and HUD.
"Make it dark blue" → updates Sway colors, GTK theme, wallpaper tint,
dashboard accent, and HUD overlay.

Built-in presets:
  midnight, ocean, forest, sunset, aurora, rose, monochrome, cyberpunk

Usage:
  python3 theming_engine.py apply midnight        # Apply a preset
  python3 theming_engine.py apply "dark blue"     # Natural language
  python3 theming_engine.py list                  # List presets
  python3 theming_engine.py current               # Show active theme
  python3 theming_engine.py create <name> <json>  # Create custom preset
  python3 theming_engine.py reset                 # Reset to defaults
  python3 theming_engine.py export                # Export current theme
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

THEME_CONFIG = Path(os.path.expanduser("~/.config/ai-distro/theme.json"))
SWAY_COLORS = Path(os.path.expanduser("~/.config/sway/colorscheme"))
GTK3_CSS = Path(os.path.expanduser("~/.config/gtk-3.0/gtk.css"))
GTK4_CSS = Path(os.path.expanduser("~/.config/gtk-4.0/gtk.css"))
WAYBAR_COLORS = Path(os.path.expanduser("~/.config/waybar/colors.css"))

# ═══════════════════════════════════════════════════════════════════
# Built-in Presets
# ═══════════════════════════════════════════════════════════════════

PRESETS = {
    "midnight": {
        "name": "Midnight",
        "bg": "#0a0e14", "surface": "#131920", "border": "#1e2a36",
        "text": "#c5cdd8", "muted": "#6b7a8d",
        "accent": "#7c3aed", "accent_light": "#a78bfa",
        "success": "#2ed573", "warning": "#ffa502", "error": "#ff4757",
        "gtk_theme": "Adwaita-dark", "icon_theme": "Papirus-Dark",
    },
    "ocean": {
        "name": "Ocean",
        "bg": "#0b1622", "surface": "#0f2033", "border": "#1a3a5c",
        "text": "#b8d4e3", "muted": "#5b8ca8",
        "accent": "#00bcd4", "accent_light": "#4dd0e1",
        "success": "#26a69a", "warning": "#ffb74d", "error": "#ef5350",
        "gtk_theme": "Adwaita-dark", "icon_theme": "Papirus-Dark",
    },
    "forest": {
        "name": "Forest",
        "bg": "#0d1a0d", "surface": "#142214", "border": "#1e3a1e",
        "text": "#c5d8c5", "muted": "#6b8d6b",
        "accent": "#4caf50", "accent_light": "#81c784",
        "success": "#66bb6a", "warning": "#ffc107", "error": "#e53935",
        "gtk_theme": "Adwaita-dark", "icon_theme": "Papirus-Dark",
    },
    "sunset": {
        "name": "Sunset",
        "bg": "#1a0e0a", "surface": "#261510", "border": "#3d2218",
        "text": "#e0c8b8", "muted": "#a07860",
        "accent": "#ff6b35", "accent_light": "#ff8a65",
        "success": "#66bb6a", "warning": "#ffd54f", "error": "#e53935",
        "gtk_theme": "Adwaita-dark", "icon_theme": "Papirus-Dark",
    },
    "aurora": {
        "name": "Aurora",
        "bg": "#0a0a1a", "surface": "#10102a", "border": "#1a1a3d",
        "text": "#d0d0e8", "muted": "#7070a0",
        "accent": "#00d4aa", "accent_light": "#4de8c2",
        "success": "#2ed573", "warning": "#ffa502", "error": "#ff4757",
        "gtk_theme": "Adwaita-dark", "icon_theme": "Papirus-Dark",
    },
    "rose": {
        "name": "Rosé",
        "bg": "#1a0a14", "surface": "#261020", "border": "#3d1830",
        "text": "#e0c0d0", "muted": "#a06888",
        "accent": "#e91e63", "accent_light": "#f06292",
        "success": "#4caf50", "warning": "#ff9800", "error": "#f44336",
        "gtk_theme": "Adwaita-dark", "icon_theme": "Papirus-Dark",
    },
    "monochrome": {
        "name": "Monochrome",
        "bg": "#0e0e0e", "surface": "#1a1a1a", "border": "#2a2a2a",
        "text": "#d0d0d0", "muted": "#707070",
        "accent": "#ffffff", "accent_light": "#e0e0e0",
        "success": "#a0a0a0", "warning": "#c0c0c0", "error": "#808080",
        "gtk_theme": "Adwaita-dark", "icon_theme": "Papirus-Dark",
    },
    "cyberpunk": {
        "name": "Cyberpunk",
        "bg": "#0a0014", "surface": "#120022", "border": "#1e0038",
        "text": "#e0d0ff", "muted": "#8060c0",
        "accent": "#ff00ff", "accent_light": "#ff66ff",
        "success": "#00ff88", "warning": "#ffff00", "error": "#ff0044",
        "gtk_theme": "Adwaita-dark", "icon_theme": "Papirus-Dark",
    },
}

# Natural language color mapping
COLOR_MAP = {
    "blue": "ocean", "dark blue": "ocean", "navy": "ocean",
    "green": "forest", "dark green": "forest", "nature": "forest",
    "orange": "sunset", "warm": "sunset", "fire": "sunset",
    "purple": "midnight", "dark purple": "midnight", "violet": "midnight",
    "pink": "rose", "magenta": "rose",
    "teal": "aurora", "cyan": "aurora", "mint": "aurora",
    "gray": "monochrome", "grey": "monochrome", "minimal": "monochrome", "clean": "monochrome",
    "neon": "cyberpunk", "cyber": "cyberpunk", "hacker": "cyberpunk",
    "dark": "midnight", "default": "aurora",
}


def _resolve_theme(name_or_description):
    """Resolve a theme name or natural language description to a preset."""
    text = name_or_description.lower().strip()

    # Direct preset match
    if text in PRESETS:
        return PRESETS[text]

    # Natural language mapping
    for keyword, preset_name in COLOR_MAP.items():
        if keyword in text:
            return PRESETS[preset_name]

    return None


def _generate_sway_config(theme):
    """Generate Sway color configuration."""
    return f"""# AI Distro Theme: {theme['name']}
# Auto-generated — do not edit manually

set $bg {theme['bg']}
set $surface {theme['surface']}
set $border {theme['border']}
set $text {theme['text']}
set $muted {theme['muted']}
set $accent {theme['accent']}
set $accent_light {theme['accent_light']}
set $success {theme['success']}
set $warning {theme['warning']}
set $error {theme['error']}

# Window colors          border    bg        text     indicator  child_border
client.focused          $accent   $surface  $text    $accent    $accent
client.unfocused        $border   $bg       $muted   $border    $border
client.focused_inactive $border   $surface  $muted   $border    $border
client.urgent           $error    $error    $text    $error     $error

# Bar colors
bar {{
    colors {{
        background $bg
        statusline $text
        separator  $border
        focused_workspace  $accent  $accent  $bg
        active_workspace   $surface $surface $text
        inactive_workspace $bg      $bg      $muted
        urgent_workspace   $error   $error   $text
    }}
}}
"""


def _generate_gtk_css(theme):
    """Generate GTK CSS overrides."""
    return f"""/* AI Distro Theme: {theme['name']} */
@define-color theme_bg_color {theme['bg']};
@define-color theme_fg_color {theme['text']};
@define-color theme_base_color {theme['surface']};
@define-color theme_selected_bg_color {theme['accent']};
@define-color theme_selected_fg_color {theme['bg']};
@define-color borders {theme['border']};
@define-color success_color {theme['success']};
@define-color warning_color {theme['warning']};
@define-color error_color {theme['error']};

headerbar, .titlebar {{
    background: {theme['surface']};
    color: {theme['text']};
    border-bottom: 1px solid {theme['border']};
}}

window, dialog {{
    background: {theme['bg']};
    color: {theme['text']};
}}

button:hover {{
    background: {theme['accent']};
    color: {theme['bg']};
}}
"""


def _generate_waybar_css(theme):
    """Generate Waybar color variables."""
    return f"""/* AI Distro Theme: {theme['name']} */
@define-color bg {theme['bg']};
@define-color surface {theme['surface']};
@define-color border {theme['border']};
@define-color text {theme['text']};
@define-color muted {theme['muted']};
@define-color accent {theme['accent']};
@define-color success {theme['success']};
@define-color warning {theme['warning']};
@define-color error {theme['error']};
"""


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def apply_theme(name_or_description):
    """Apply a theme by name or natural language description."""
    theme = _resolve_theme(name_or_description)
    if not theme:
        return {"error": f"Unknown theme: '{name_or_description}'",
                "available": list(PRESETS.keys()),
                "hint": "Try: midnight, ocean, forest, sunset, aurora, rose, monochrome, cyberpunk"}

    applied = []

    # Write Sway colors
    SWAY_COLORS.parent.mkdir(parents=True, exist_ok=True)
    SWAY_COLORS.write_text(_generate_sway_config(theme))
    applied.append("sway")

    # Write GTK CSS
    for gtk_path in [GTK3_CSS, GTK4_CSS]:
        gtk_path.parent.mkdir(parents=True, exist_ok=True)
        gtk_path.write_text(_generate_gtk_css(theme))
    applied.append("gtk")

    # Write Waybar colors
    WAYBAR_COLORS.parent.mkdir(parents=True, exist_ok=True)
    WAYBAR_COLORS.write_text(_generate_waybar_css(theme))
    applied.append("waybar")

    # Set GTK theme via gsettings
    try:
        gtk_theme = theme.get("gtk_theme", "Adwaita-dark")
        subprocess.run(["gsettings", "set", "org.gnome.desktop.interface",
                        "gtk-theme", gtk_theme], capture_output=True, timeout=5)
        icon_theme = theme.get("icon_theme", "Papirus-Dark")
        subprocess.run(["gsettings", "set", "org.gnome.desktop.interface",
                        "icon-theme", icon_theme], capture_output=True, timeout=5)
        applied.append("gsettings")
    except Exception:
        pass

    # Reload Sway if running
    try:
        subprocess.run(["swaymsg", "reload"], capture_output=True, timeout=5)
        applied.append("sway-reload")
    except Exception:
        pass

    # Save current theme
    THEME_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(THEME_CONFIG, "w") as f:
        json.dump({**theme, "applied_at": datetime.now().isoformat()}, f, indent=2)

    return {"status": "ok", "theme": theme["name"], "applied_to": applied}


def current_theme():
    """Get the currently active theme."""
    if THEME_CONFIG.exists():
        with open(THEME_CONFIG) as f:
            return json.load(f)
    return {"theme": "default (aurora)", "note": "No custom theme applied"}


def list_presets():
    """List all available presets."""
    return [{
        "name": name,
        "display": p["name"],
        "accent": p["accent"],
        "bg": p["bg"],
    } for name, p in PRESETS.items()]


def create_preset(name, theme_json):
    """Create a custom theme preset."""
    try:
        custom = json.loads(theme_json) if isinstance(theme_json, str) else theme_json
    except json.JSONDecodeError:
        return {"error": "Invalid JSON"}

    required = ["bg", "surface", "border", "text", "accent"]
    missing = [k for k in required if k not in custom]
    if missing:
        return {"error": f"Missing required fields: {missing}"}

    custom.setdefault("name", name.title())
    custom.setdefault("muted", "#707070")
    custom.setdefault("accent_light", custom["accent"])
    custom.setdefault("success", "#2ed573")
    custom.setdefault("warning", "#ffa502")
    custom.setdefault("error", "#ff4757")
    custom.setdefault("gtk_theme", "Adwaita-dark")
    custom.setdefault("icon_theme", "Papirus-Dark")

    PRESETS[name] = custom
    return {"status": "ok", "preset": name, "theme": custom}


def reset_theme():
    """Reset to the default aurora theme."""
    return apply_theme("aurora")


def main():
    if len(sys.argv) < 2:
        print("Usage: theming_engine.py <apply|list|current|create|reset|export>")
        return

    cmd = sys.argv[1]

    if cmd == "apply":
        name = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "aurora"
        result = apply_theme(name)
        print(json.dumps(result, indent=2))
    elif cmd == "list":
        for p in list_presets():
            print(f"  {p['name']:15s} accent={p['accent']}  bg={p['bg']}")
    elif cmd == "current":
        print(json.dumps(current_theme(), indent=2))
    elif cmd == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        theme_json = sys.argv[3] if len(sys.argv) > 3 else "{}"
        print(json.dumps(create_preset(name, theme_json), indent=2))
    elif cmd == "reset":
        print(json.dumps(reset_theme(), indent=2))
    elif cmd == "export":
        print(json.dumps(current_theme(), indent=2))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
