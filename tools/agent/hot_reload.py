#!/usr/bin/env python3
"""
AI Distro — Plugin Hot-Reload

Watches the skills directory for file changes and reloads modified skills
without restarting the agent. Uses inotify (via inotifywait) or polling
fallback for cross-platform support.

Features:
  - File system monitoring (inotify or poll-based)
  - Automatic handler module reload on change
  - Manifest re-parsing on update
  - Skill load/unload lifecycle hooks
  - Reload history and error tracking
  - Event bus notification on skill reload

Usage:
  python3 hot_reload.py watch                     # Watch and auto-reload
  python3 hot_reload.py reload my_skill           # Force-reload a skill
  python3 hot_reload.py list                      # List loaded skills
  python3 hot_reload.py history                   # Show reload history
"""
import importlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SKILLS_DIR = Path(os.path.expanduser("~/.config/ai-distro/skills"))
BUILTIN_SKILLS = Path(os.path.dirname(__file__)) / ".." / ".." / "skills"
HISTORY_FILE = Path(os.path.expanduser("~/.cache/ai-distro/reload_history.json"))
EVENT_SOCKET = "/tmp/ai-distro-events.sock"

POLL_INTERVAL = 2  # seconds
MAX_HISTORY = 100

# In-memory skill registry
_loaded_skills = {}
_file_mtimes = {}


def _publish_event(data):
    """Notify the event bus."""
    try:
        if not os.path.exists(EVENT_SOCKET):
            return
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(EVENT_SOCKET)
        msg = json.dumps({"channel": "skills", "data": data})
        s.sendall(msg.encode("utf-8") + b"\n")
        s.close()
    except Exception:
        pass


def _save_history(entry):
    """Append to reload history."""
    history = []
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                history = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    history.append(entry)
    history = history[-MAX_HISTORY:]  # Trim

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def _load_skill_module(skill_dir):
    """Load a skill's handler module dynamically."""
    manifest_path = skill_dir / "manifest.json"
    if not manifest_path.exists():
        return None, "No manifest.json"

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"Invalid manifest: {e}"

    entry = manifest.get("entry", "handler.py")
    handler_path = skill_dir / entry
    if not handler_path.exists():
        return None, f"Handler not found: {entry}"

    skill_name = manifest.get("name", skill_dir.name)

    try:
        spec = importlib.util.spec_from_file_location(
            f"skill_{skill_name}", str(handler_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return {
            "name": skill_name,
            "manifest": manifest,
            "module": module,
            "path": str(skill_dir),
            "loaded_at": datetime.now().isoformat(),
            "handler": getattr(module, "handle", None),
        }, None

    except Exception as e:
        return None, f"Load error: {e}"


def _get_skill_files(skill_dir):
    """Get all tracked files and their mtimes."""
    files = {}
    for f in skill_dir.rglob("*"):
        if f.is_file() and "__pycache__" not in str(f):
            try:
                files[str(f)] = f.stat().st_mtime
            except OSError:
                pass
    return files


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def load_all():
    """Load all skills from the skills directory."""
    loaded = 0
    errors = 0

    for skills_base in [SKILLS_DIR, BUILTIN_SKILLS]:
        if not skills_base.exists():
            continue
        for skill_dir in skills_base.iterdir():
            if not skill_dir.is_dir():
                continue
            if not (skill_dir / "manifest.json").exists():
                continue

            skill_info, error = _load_skill_module(skill_dir)
            if skill_info:
                _loaded_skills[skill_info["name"]] = skill_info
                _file_mtimes[skill_info["name"]] = _get_skill_files(skill_dir)
                loaded += 1
            else:
                errors += 1
                print(f"  ⚠ Failed to load {skill_dir.name}: {error}")

    return {"loaded": loaded, "errors": errors}


def reload_skill(skill_name):
    """Force-reload a specific skill."""
    # Find skill directory
    skill_dir = None
    for base in [SKILLS_DIR, BUILTIN_SKILLS]:
        candidate = base / skill_name
        if candidate.exists() and (candidate / "manifest.json").exists():
            skill_dir = candidate
            break

    if not skill_dir:
        return {"error": f"Skill not found: {skill_name}"}

    # Unload old module
    old_module_name = f"skill_{skill_name}"
    if old_module_name in sys.modules:
        del sys.modules[old_module_name]

    # Reload
    skill_info, error = _load_skill_module(skill_dir)
    if skill_info:
        _loaded_skills[skill_name] = skill_info
        _file_mtimes[skill_name] = _get_skill_files(skill_dir)

        entry = {
            "skill": skill_name,
            "action": "reload",
            "timestamp": datetime.now().isoformat(),
            "status": "ok",
        }
        _save_history(entry)
        _publish_event({"type": "skill_reloaded", "skill": skill_name})

        return {"status": "ok", "skill": skill_name, "loaded_at": skill_info["loaded_at"]}
    else:
        entry = {
            "skill": skill_name,
            "action": "reload",
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": error,
        }
        _save_history(entry)
        return {"error": error, "skill": skill_name}


def list_loaded():
    """List all loaded skills."""
    return [{
        "name": info["name"],
        "version": info["manifest"].get("version", "?"),
        "path": info["path"],
        "loaded_at": info["loaded_at"],
        "has_handler": info["handler"] is not None,
    } for info in _loaded_skills.values()]


def get_history():
    """Get reload history."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []


def invoke_skill(skill_name, payload=None, context=None):
    """Invoke a loaded skill's handler."""
    if skill_name not in _loaded_skills:
        return {"error": f"Skill not loaded: {skill_name}"}

    handler = _loaded_skills[skill_name].get("handler")
    if not handler:
        return {"error": f"Skill has no handle() function: {skill_name}"}

    try:
        return handler(skill_name, payload, context)
    except Exception as e:
        return {"error": f"Skill error: {e}"}


def watch():
    """Watch for skill file changes and auto-reload."""
    print("Hot-Reload Watcher started")

    # Initial load
    result = load_all()
    print(f"  Loaded {result['loaded']} skills ({result['errors']} errors)")
    print(f"  Watching: {SKILLS_DIR}")
    if BUILTIN_SKILLS.exists():
        print(f"  Watching: {BUILTIN_SKILLS}")

    # Try inotifywait first
    has_inotify = subprocess.run(
        ["which", "inotifywait"], capture_output=True
    ).returncode == 0

    if has_inotify:
        print("  Mode: inotify (efficient)")
        _watch_inotify()
    else:
        print("  Mode: polling (install inotify-tools for efficiency)")
        _watch_poll()


def _watch_inotify():
    """Watch using inotifywait (Linux-native, efficient)."""
    dirs = [str(d) for d in [SKILLS_DIR, BUILTIN_SKILLS] if d.exists()]
    try:
        proc = subprocess.Popen(
            ["inotifywait", "-m", "-r", "-e", "modify,create,delete",
             "--format", "%w%f"] + dirs,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        debounce = {}
        for line in proc.stdout:
            filepath = line.strip()
            if not filepath or "__pycache__" in filepath:
                continue

            # Debounce: skip if same file changed <1s ago
            now = time.time()
            if filepath in debounce and now - debounce[filepath] < 1.0:
                continue
            debounce[filepath] = now

            # Determine which skill was modified
            for skill_name, info in _loaded_skills.items():
                if filepath.startswith(info["path"]):
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"  [{ts}] 🔄 Change detected in {skill_name}: {Path(filepath).name}")
                    result = reload_skill(skill_name)
                    status = "✓" if result.get("status") == "ok" else "✗"
                    print(f"  [{ts}]   {status} Reload: {result.get('status', result.get('error'))}")
                    break

    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        print(f"  inotify error, falling back to poll: {e}")
        _watch_poll()


def _watch_poll():
    """Watch using polling (cross-platform fallback)."""
    try:
        while True:
            for skill_name in list(_loaded_skills.keys()):
                info = _loaded_skills[skill_name]
                skill_dir = Path(info["path"])

                current_mtimes = _get_skill_files(skill_dir)
                stored_mtimes = _file_mtimes.get(skill_name, {})

                changed = False
                for filepath, mtime in current_mtimes.items():
                    if filepath not in stored_mtimes or stored_mtimes[filepath] != mtime:
                        changed = True
                        break

                if changed:
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"  [{ts}] 🔄 Change detected in {skill_name}")
                    result = reload_skill(skill_name)
                    status = "✓" if result.get("status") == "ok" else "✗"
                    print(f"  [{ts}]   {status} Reload: {result.get('status', result.get('error'))}")

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    if len(sys.argv) < 2:
        print("Usage: hot_reload.py <watch|reload|list|history>")
        return

    cmd = sys.argv[1]

    if cmd == "watch":
        watch()
    elif cmd == "reload":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        if not name:
            print("Usage: hot_reload.py reload <skill_name>")
            return
        load_all()
        print(json.dumps(reload_skill(name), indent=2))
    elif cmd == "list":
        load_all()
        for s in list_loaded():
            status = "✓" if s["has_handler"] else "✗"
            print(f"  {status} {s['name']:25s} v{s['version']:8s} {s['loaded_at']}")
    elif cmd == "history":
        for entry in get_history()[-20:]:
            icon = "✓" if entry.get("status") == "ok" else "✗"
            print(f"  {icon} [{entry['timestamp']}] {entry['skill']} — {entry['action']}")
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
