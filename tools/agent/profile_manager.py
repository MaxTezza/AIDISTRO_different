#!/usr/bin/env python3
"""
AI Distro — User Profile Manager

Export, import, and manage Bayesian learning profiles. Supports multi-user
switching, profile backup/restore, and migration between machines.

Usage:
  python3 profile_manager.py export [filename]   # Export current profile
  python3 profile_manager.py import <filename>    # Import a profile
  python3 profile_manager.py list                 # List saved profiles
  python3 profile_manager.py switch <name>        # Switch active profile
  python3 profile_manager.py create <name>        # Create new empty profile
  python3 profile_manager.py delete <name>        # Delete a profile
  python3 profile_manager.py stats                # Show current profile stats
"""
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BAYESIAN_DB = Path(os.path.expanduser("~/.cache/ai-distro/bayesian.db"))
PROFILES_DIR = Path(os.path.expanduser("~/.config/ai-distro/profiles"))
ACTIVE_PROFILE_FILE = PROFILES_DIR / ".active"
USER_CONFIG = Path(os.path.expanduser("~/.config/ai-distro-user.json"))
SPIRIT_CONFIG = Path(os.path.expanduser("~/.config/ai-distro-spirit.json"))
LOCALE_CONFIG = Path(os.path.expanduser("~/.config/ai-distro-locale.json"))


def _ensure_dirs():
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def _active_profile():
    if ACTIVE_PROFILE_FILE.exists():
        return ACTIVE_PROFILE_FILE.read_text().strip()
    return "default"


def _set_active(name):
    _ensure_dirs()
    ACTIVE_PROFILE_FILE.write_text(name)


def export_profile(filename=None):
    """Export the current Bayesian DB + configs into a portable JSON bundle."""
    profile_data = {
        "exported_at": datetime.now().isoformat(),
        "profile_name": _active_profile(),
        "version": "1.0",
    }

    # Export Bayesian DB
    if BAYESIAN_DB.exists():
        conn = sqlite3.connect(str(BAYESIAN_DB))
        c = conn.cursor()

        c.execute("SELECT context_key, action, alpha, beta, last_updated, total_observations FROM beliefs")
        profile_data["beliefs"] = [
            {"context_key": r[0], "action": r[1], "alpha": r[2], "beta": r[3],
             "last_updated": r[4], "total_observations": r[5]}
            for r in c.fetchall()
        ]

        c.execute("SELECT key, value, confidence, last_updated FROM preferences")
        profile_data["preferences"] = [
            {"key": r[0], "value": r[1], "confidence": r[2], "last_updated": r[3]}
            for r in c.fetchall()
        ]

        c.execute("SELECT prev_action, next_action, alpha, beta, count FROM action_chains")
        profile_data["action_chains"] = [
            {"prev_action": r[0], "next_action": r[1], "alpha": r[2], "beta": r[3], "count": r[4]}
            for r in c.fetchall()
        ]

        c.execute("SELECT COUNT(*) FROM interactions")
        profile_data["total_interactions"] = c.fetchone()[0]

        conn.close()

    # Export user configs
    for cfg_path, key in [(USER_CONFIG, "user_config"), (SPIRIT_CONFIG, "spirit_config"),
                          (LOCALE_CONFIG, "locale_config")]:
        if cfg_path.exists():
            with open(cfg_path) as f:
                profile_data[key] = json.load(f)

    # Write export
    if not filename:
        filename = f"ai-distro-profile-{_active_profile()}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    _ensure_dirs()
    out_path = PROFILES_DIR / filename if not os.path.isabs(filename) else Path(filename)
    with open(out_path, "w") as f:
        json.dump(profile_data, f, indent=2)

    beliefs_count = len(profile_data.get("beliefs", []))
    prefs_count = len(profile_data.get("preferences", []))
    return {
        "status": "ok",
        "file": str(out_path),
        "beliefs": beliefs_count,
        "preferences": prefs_count,
        "interactions": profile_data.get("total_interactions", 0),
    }


def import_profile(filename):
    """Import a profile bundle, replacing the current Bayesian DB."""
    path = Path(filename)
    if not path.exists():
        path = PROFILES_DIR / filename
    if not path.exists():
        return {"error": f"Profile file not found: {filename}"}

    with open(path) as f:
        data = json.load(f)

    if "version" not in data:
        return {"error": "Invalid profile format (missing version)"}

    # Backup current DB
    if BAYESIAN_DB.exists():
        backup = BAYESIAN_DB.with_suffix(f".backup-{datetime.now().strftime('%Y%m%d%H%M%S')}.db")
        shutil.copy2(BAYESIAN_DB, backup)

    # Rebuild Bayesian DB
    if BAYESIAN_DB.exists():
        BAYESIAN_DB.unlink()

    BAYESIAN_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(BAYESIAN_DB))
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS beliefs (
        context_key TEXT NOT NULL, action TEXT NOT NULL,
        alpha REAL DEFAULT 1.0, beta REAL DEFAULT 1.0,
        last_updated REAL DEFAULT 0, total_observations INTEGER DEFAULT 0,
        UNIQUE(context_key, action))""")

    c.execute("""CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL NOT NULL,
        context_key TEXT NOT NULL, action TEXT NOT NULL,
        outcome TEXT NOT NULL, metadata TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS preferences (
        key TEXT PRIMARY KEY, value TEXT NOT NULL,
        confidence REAL DEFAULT 0.5, last_updated REAL DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS action_chains (
        prev_action TEXT NOT NULL, next_action TEXT NOT NULL,
        alpha REAL DEFAULT 1.0, beta REAL DEFAULT 1.0,
        count INTEGER DEFAULT 0, UNIQUE(prev_action, next_action))""")

    for b in data.get("beliefs", []):
        c.execute("INSERT OR REPLACE INTO beliefs VALUES (?,?,?,?,?,?)",
                  (b["context_key"], b["action"], b["alpha"], b["beta"],
                   b["last_updated"], b["total_observations"]))

    for p in data.get("preferences", []):
        c.execute("INSERT OR REPLACE INTO preferences VALUES (?,?,?,?)",
                  (p["key"], p["value"], p["confidence"], p["last_updated"]))

    for ch in data.get("action_chains", []):
        c.execute("INSERT OR REPLACE INTO action_chains VALUES (?,?,?,?,?)",
                  (ch["prev_action"], ch["next_action"], ch["alpha"], ch["beta"], ch["count"]))

    conn.commit()
    conn.close()

    # Restore configs
    for key, cfg_path in [("user_config", USER_CONFIG), ("spirit_config", SPIRIT_CONFIG),
                          ("locale_config", LOCALE_CONFIG)]:
        if key in data:
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cfg_path, "w") as f:
                json.dump(data[key], f, indent=2)

    name = data.get("profile_name", "imported")
    _set_active(name)

    return {
        "status": "ok",
        "profile": name,
        "beliefs": len(data.get("beliefs", [])),
        "preferences": len(data.get("preferences", [])),
    }


def list_profiles():
    """List all saved profile bundles."""
    _ensure_dirs()
    profiles = []
    for f in sorted(PROFILES_DIR.glob("*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
            profiles.append({
                "file": f.name,
                "name": data.get("profile_name", f.stem),
                "exported_at": data.get("exported_at", "?"),
                "beliefs": len(data.get("beliefs", [])),
                "preferences": len(data.get("preferences", [])),
            })
        except (json.JSONDecodeError, KeyError):
            profiles.append({"file": f.name, "error": "invalid"})

    return {"active": _active_profile(), "profiles": profiles}


def create_profile(name):
    """Create a new empty profile (saves current, resets DB)."""
    # Auto-export current first
    export_profile()

    # Clear DB
    if BAYESIAN_DB.exists():
        BAYESIAN_DB.unlink()

    _set_active(name)
    return {"status": "ok", "message": f"Created and switched to profile '{name}'"}


def delete_profile(name):
    """Delete a saved profile."""
    _ensure_dirs()
    deleted = 0
    for f in PROFILES_DIR.glob(f"*{name}*.json"):
        f.unlink()
        deleted += 1
    return {"status": "ok", "deleted": deleted}


def stats():
    """Show stats for the current profile."""
    result = {"profile": _active_profile()}

    if BAYESIAN_DB.exists():
        conn = sqlite3.connect(str(BAYESIAN_DB))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM beliefs")
        result["beliefs"] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM interactions")
        result["interactions"] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM preferences")
        result["preferences"] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM action_chains")
        result["action_chains"] = c.fetchone()[0]
        conn.close()
    else:
        result["note"] = "No Bayesian DB found (fresh profile)"

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: profile_manager.py <export|import|list|switch|create|delete|stats>")
        return

    cmd = sys.argv[1]
    if cmd == "export":
        fn = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(export_profile(fn), indent=2))
    elif cmd == "import":
        fn = sys.argv[2] if len(sys.argv) > 2 else ""
        if not fn:
            print("Usage: profile_manager.py import <filename>")
            return
        print(json.dumps(import_profile(fn), indent=2))
    elif cmd == "list":
        print(json.dumps(list_profiles(), indent=2))
    elif cmd == "switch":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        profiles = list_profiles()
        matches = [p for p in profiles["profiles"] if name in p.get("name", "")]
        if matches:
            print(json.dumps(import_profile(matches[0]["file"]), indent=2))
        else:
            print(json.dumps({"error": f"No profile matching '{name}'"}))
    elif cmd == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else "new"
        print(json.dumps(create_profile(name), indent=2))
    elif cmd == "delete":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(delete_profile(name), indent=2))
    elif cmd == "stats":
        print(json.dumps(stats(), indent=2))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
