#!/usr/bin/env python3
"""
AT-SPI Deep UI Automation — "The Hands"

Provides semantic access to UI elements in ANY application through the
Linux Accessibility Stack (AT-SPI2). This replaces blind coordinate-based
clicking with intelligent, named-element interaction.

Capabilities:
  - Find buttons, text fields, menus by name/role across all apps
  - Click, type into, and read from any accessible widget
  - List all interactive elements in the focused window
  - Navigate tab structures and tree views

Fallback: Uses xdotool when AT-SPI is unavailable.
"""
import json
import subprocess
import sys


def _has_atspi():
    """Check if AT-SPI python bindings are available."""
    try:
        import gi
        gi.require_version('Atspi', '2.0')
        from gi.repository import Atspi  # noqa: F401
        return True
    except Exception:
        return False


HAS_ATSPI = _has_atspi()


# ── AT-SPI Core ───────────────────────────────────────────────────────

def get_desktop():
    """Get the AT-SPI desktop object (root of all accessible apps)."""
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi
    return Atspi.get_desktop(0)


def iter_children(node, max_depth=10, _depth=0):
    """Recursively iterate all accessible children of a node."""
    if _depth > max_depth:
        return
    try:
        count = node.get_child_count()
    except Exception:
        return
    for i in range(count):
        try:
            child = node.get_child_at_index(i)
            if child is not None:
                yield child
                yield from iter_children(child, max_depth, _depth + 1)
        except Exception:
            continue


def get_focused_app():
    """Find the currently focused application via AT-SPI."""
    desktop = get_desktop()
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app is None:
            continue
        for child in iter_children(app, max_depth=3):
            try:
                state_set = child.get_state_set()
                import gi
                gi.require_version('Atspi', '2.0')
                from gi.repository import Atspi
                if state_set.contains(Atspi.StateType.FOCUSED) or \
                   state_set.contains(Atspi.StateType.ACTIVE):
                    return app
            except Exception:
                continue
    # Fallback: return first app
    if desktop.get_child_count() > 0:
        return desktop.get_child_at_index(0)
    return None


def find_element(target_name, target_role=None, app=None):
    """
    Find a UI element by name and optional role.

    Args:
        target_name: Text/name of the element (case-insensitive substring match)
        target_role: Optional role filter (e.g., 'push button', 'text', 'menu item')
        app: Optional app node to search in; defaults to focused app
    """
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi

    search_root = app or get_focused_app() or get_desktop()
    target_lower = target_name.lower()

    best_match = None
    best_score = 0

    for element in iter_children(search_root, max_depth=15):
        try:
            name = element.get_name() or ""
            role = element.get_role_name() or ""

            # Role filter
            if target_role and target_role.lower() not in role.lower():
                continue

            # Name matching with scoring
            name_lower = name.lower()
            score = 0

            if target_lower == name_lower:
                score = 100  # Exact match
            elif target_lower in name_lower:
                score = 80  # Substring match
            elif name_lower in target_lower:
                score = 60  # Reverse substring

            # Check if element is actually interactive
            state_set = element.get_state_set()
            is_visible = state_set.contains(Atspi.StateType.VISIBLE)
            is_showing = state_set.contains(Atspi.StateType.SHOWING)
            is_sensitive = state_set.contains(Atspi.StateType.SENSITIVE)

            if score > 0 and is_visible and is_showing:
                if is_sensitive:
                    score += 10  # Prefer interactive elements

                if score > best_score:
                    best_score = score
                    best_match = element

        except Exception:
            continue

    return best_match


def click_element(element):
    """Click an accessible element using AT-SPI actions or coordinate fallback."""
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi

    # Method 1: AT-SPI DoDefaultAction
    try:
        action = element.get_action_iface()
        if action:
            n_actions = action.get_n_actions()
            for i in range(n_actions):
                action_name = action.get_action_name(i)
                if action_name in ("click", "activate", "press", ""):
                    action.do_action(i)
                    return True, f"Clicked via AT-SPI action '{action_name}'"
    except Exception:
        pass

    # Method 2: Get component coordinates and click via xdotool
    try:
        component = element.get_component_iface()
        if component:
            extent = component.get_extents(Atspi.CoordType.SCREEN)
            x = extent.x + extent.width // 2
            y = extent.y + extent.height // 2
            subprocess.run(
                ["xdotool", "mousemove", str(x), str(y), "click", "1"],
                capture_output=True
            )
            return True, f"Clicked at coordinates ({x}, {y})"
    except Exception:
        pass

    return False, "Could not click element"


def type_into_element(element, text):
    """Type text into an accessible element."""
    # Method 1: AT-SPI EditableText interface
    try:
        editable = element.get_editable_text_iface()
        if editable:
            # Clear existing text
            text_iface = element.get_text_iface()
            if text_iface:
                existing_len = text_iface.get_character_count()
                if existing_len > 0:
                    editable.delete_text(0, existing_len)
            editable.insert_text(0, text, len(text))
            return True, "Typed via AT-SPI EditableText"
    except Exception:
        pass

    # Method 2: Focus element and use xdotool type
    try:
        click_element(element)  # Focus it first
        import time
        time.sleep(0.2)
        subprocess.run(["xdotool", "type", "--clearmodifiers", text], capture_output=True)
        return True, "Typed via xdotool (after AT-SPI focus)"
    except Exception as e:
        return False, f"Could not type text: {e}"


def read_element(element):
    """Read text content from an accessible element."""
    try:
        text_iface = element.get_text_iface()
        if text_iface:
            count = text_iface.get_character_count()
            return text_iface.get_text(0, count)
    except Exception:
        pass

    try:
        return element.get_name() or ""
    except Exception:
        return ""


def list_elements(role_filter=None, app=None):
    """List all interactive elements in the focused window."""
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi

    search_root = app or get_focused_app() or get_desktop()
    elements = []

    for element in iter_children(search_root, max_depth=10):
        try:
            name = element.get_name() or ""
            role = element.get_role_name() or ""

            # Skip unnamed/structural elements
            if not name and role in ("filler", "panel", "separator", "scroll bar"):
                continue

            state_set = element.get_state_set()
            if not state_set.contains(Atspi.StateType.SHOWING):
                continue

            if role_filter and role_filter.lower() not in role.lower():
                continue

            elements.append({
                "name": name,
                "role": role,
                "sensitive": state_set.contains(Atspi.StateType.SENSITIVE),
            })

            if len(elements) >= 100:
                break

        except Exception:
            continue

    return elements


# ── xdotool Fallback ─────────────────────────────────────────────────

def xdotool_click(target):
    """Fallback: click using xdotool coordinate or window search."""
    if "," in target:
        parts = target.split(",")
        if len(parts) == 2:
            result = subprocess.run(
                ["xdotool", "mousemove", parts[0], parts[1], "click", "1"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return True, f"Clicked at ({parts[0]}, {parts[1]})"

    result = subprocess.run(
        ["xdotool", "search", "--name", target, "windowactivate"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return True, f"Activated window matching '{target}'"

    return False, f"Could not find element '{target}'"


def xdotool_type(text, window=None):
    """Fallback: type using xdotool."""
    if window:
        subprocess.run(
            ["xdotool", "search", "--name", window, "windowactivate"],
            capture_output=True
        )
        import time
        time.sleep(0.2)

    result = subprocess.run(["xdotool", "type", text], capture_output=True, text=True)
    return result.returncode == 0, "Typed via xdotool"


# ── Main CLI Interface ───────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Usage: atspi_hands.py <action> [args...]",
            "actions": ["click", "type", "read", "list", "find"]
        }))
        return

    action = sys.argv[1]

    if action == "click":
        target = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not target:
            print(json.dumps({"status": "error", "message": "Missing click target"}))
            return

        if HAS_ATSPI:
            element = find_element(target)
            if element:
                ok, msg = click_element(element)
                print(json.dumps({"status": "ok" if ok else "error", "message": msg}))
            else:
                # AT-SPI didn't find it, try xdotool
                ok, msg = xdotool_click(target)
                print(json.dumps({"status": "ok" if ok else "error", "message": msg}))
        else:
            ok, msg = xdotool_click(target)
            print(json.dumps({"status": "ok" if ok else "error", "message": msg}))

    elif action == "type":
        if len(sys.argv) < 3:
            print(json.dumps({"status": "error", "message": "Usage: type <field_name>|<text>"}))
            return

        payload = " ".join(sys.argv[2:])
        parts = payload.split("|", 1)

        if len(parts) == 2 and HAS_ATSPI:
            field_name, text = parts
            element = find_element(field_name, target_role="text")
            if not element:
                element = find_element(field_name, target_role="entry")
            if element:
                ok, msg = type_into_element(element, text)
                print(json.dumps({"status": "ok" if ok else "error", "message": msg}))
            else:
                ok, msg = xdotool_type(text, window=field_name)
                print(json.dumps({"status": "ok" if ok else "error", "message": msg}))
        else:
            text = payload
            ok, msg = xdotool_type(text)
            print(json.dumps({"status": "ok" if ok else "error", "message": msg}))

    elif action == "read":
        target = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not HAS_ATSPI:
            print(json.dumps({"status": "error", "message": "AT-SPI not available for reading"}))
            return

        if target:
            element = find_element(target)
            if element:
                text = read_element(element)
                print(json.dumps({"status": "ok", "message": text or "(empty)"}))
            else:
                print(json.dumps({"status": "error", "message": f"Element '{target}' not found"}))
        else:
            # Read focused element
            app = get_focused_app()
            if app:
                print(json.dumps({"status": "ok", "message": read_element(app)}))
            else:
                print(json.dumps({"status": "error", "message": "No focused app"}))

    elif action == "list":
        role = sys.argv[2] if len(sys.argv) > 2 else None
        if not HAS_ATSPI:
            print(json.dumps({
                "status": "error",
                "message": "AT-SPI not available. Install python3-gi and libatspi2.0-dev"
            }))
            return

        elements = list_elements(role_filter=role)
        print(json.dumps({
            "status": "ok",
            "message": f"Found {len(elements)} elements",
            "elements": elements[:50]  # Cap output
        }))

    elif action == "find":
        target = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not target or not HAS_ATSPI:
            print(json.dumps({"status": "error", "message": "AT-SPI not available or missing target"}))
            return

        element = find_element(target)
        if element:
            name = element.get_name() or ""
            role = element.get_role_name() or ""
            print(json.dumps({
                "status": "ok",
                "message": f"Found: '{name}' ({role})",
                "name": name,
                "role": role
            }))
        else:
            print(json.dumps({"status": "error", "message": f"Element '{target}' not found"}))

    else:
        print(json.dumps({
            "status": "error",
            "message": f"Unknown action: {action}",
            "actions": ["click", "type", "read", "list", "find"]
        }))


if __name__ == "__main__":
    main()
