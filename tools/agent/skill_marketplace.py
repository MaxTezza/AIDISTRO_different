#!/usr/bin/env python3
"""
AI Distro — Skill Marketplace

Discover, install, update, and manage AI Distro skills (plugins).
Supports both local skill packs and a remote community repository.

Architecture:
  - Skills are JSON manifests in src/skills/core/ and src/skills/dynamic/
  - Community skills are fetched from a configurable Git repository
  - Each skill defines: name, description, version, intents, triggers, author
  - Marketplace provides: search, install, uninstall, update, list, info

Usage:
  python3 skill_marketplace.py list                 # List installed skills
  python3 skill_marketplace.py search <query>       # Search community repo
  python3 skill_marketplace.py install <skill_name> # Install from community
  python3 skill_marketplace.py uninstall <name>     # Remove a skill
  python3 skill_marketplace.py update               # Update all community skills
  python3 skill_marketplace.py info <name>          # Show skill details
  python3 skill_marketplace.py export               # Export installed list
  python3 skill_marketplace.py serve                # Start HTTP marketplace UI
"""
import hashlib
import http.server
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

CORE_SKILLS_DIR = Path(__file__).parent.parent.parent / "src" / "skills" / "core"
DYNAMIC_SKILLS_DIR = Path(__file__).parent.parent.parent / "src" / "skills" / "dynamic"
COMMUNITY_CACHE = Path(os.path.expanduser("~/.cache/ai-distro/marketplace"))
COMMUNITY_REPO_URL = os.environ.get(
    "AI_DISTRO_SKILL_REPO",
    "https://gitlab.com/maxtezza29464/ai_distro_skills.git",
)
MARKETPLACE_PORT = 7842
INSTALL_LOG = Path(os.path.expanduser("~/.cache/ai-distro/installed_skills.json"))


def _load_install_log():
    """Load the install log (tracks community skill metadata)."""
    if INSTALL_LOG.exists():
        with open(INSTALL_LOG) as f:
            return json.load(f)
    return {}


def _save_install_log(data):
    INSTALL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(INSTALL_LOG, "w") as f:
        json.dump(data, f, indent=2)


def _skill_hash(manifest):
    """Generate a deterministic hash for a skill manifest."""
    content = json.dumps(manifest, sort_keys=True).encode()
    return hashlib.sha256(content).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════
# Core Operations
# ═══════════════════════════════════════════════════════════════════

def list_installed():
    """List all installed skills (core + dynamic)."""
    skills = {"core": [], "dynamic": []}

    for skill_dir, category in [(CORE_SKILLS_DIR, "core"), (DYNAMIC_SKILLS_DIR, "dynamic")]:
        if not skill_dir.exists():
            continue
        for f in sorted(skill_dir.glob("*.json")):
            try:
                with open(f) as fh:
                    manifest = json.load(fh)
                skills[category].append({
                    "name": manifest.get("name", f.stem),
                    "description": manifest.get("description", ""),
                    "version": manifest.get("version", "1.0.0"),
                    "intents": len(manifest.get("intents", manifest.get("triggers", []))),
                    "file": f.name,
                })
            except (json.JSONDecodeError, KeyError):
                skills[category].append({"name": f.stem, "error": "invalid manifest"})

    return skills


def search_community(query):
    """Search the community skill repository."""
    catalog = _fetch_community_catalog()
    if not catalog:
        return {"error": "Could not fetch community catalog. Try again later."}

    query_lower = query.lower()
    results = []
    for skill in catalog:
        name = skill.get("name", "")
        desc = skill.get("description", "")
        tags = " ".join(skill.get("tags", []))
        if query_lower in name.lower() or query_lower in desc.lower() or query_lower in tags.lower():
            results.append(skill)
    return results


def install_skill(skill_name):
    """Install a skill from the community repository."""
    catalog = _fetch_community_catalog()
    if not catalog:
        return {"error": "Could not fetch community catalog."}

    # Find the skill
    match = None
    for skill in catalog:
        if skill.get("name", "").lower() == skill_name.lower():
            match = skill
            break
    if not match:
        return {"error": f"Skill '{skill_name}' not found in community catalog."}

    # Download and install
    DYNAMIC_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    target = DYNAMIC_SKILLS_DIR / f"{skill_name}.json"

    # If the skill has a download_url, fetch it
    if "download_url" in match:
        try:
            req = urllib.request.Request(match["download_url"])
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read()
            with open(target, "wb") as f:
                f.write(content)
        except Exception as e:
            return {"error": f"Download failed: {e}"}
    else:
        # Store the manifest directly
        with open(target, "w") as f:
            json.dump(match, f, indent=2)

    # Log installation
    log = _load_install_log()
    log[skill_name] = {
        "installed_at": datetime.now().isoformat(),
        "version": match.get("version", "1.0.0"),
        "hash": _skill_hash(match),
        "source": "community",
    }
    _save_install_log(log)

    return {"status": "ok", "message": f"Installed '{skill_name}' v{match.get('version', '?')}"}


def uninstall_skill(skill_name):
    """Remove an installed community skill."""
    target = DYNAMIC_SKILLS_DIR / f"{skill_name}.json"
    if not target.exists():
        return {"error": f"Skill '{skill_name}' not found in dynamic skills."}

    target.unlink()

    log = _load_install_log()
    log.pop(skill_name, None)
    _save_install_log(log)

    return {"status": "ok", "message": f"Uninstalled '{skill_name}'"}


def update_all():
    """Update all community-installed skills."""
    log = _load_install_log()
    catalog = _fetch_community_catalog()
    if not catalog:
        return {"error": "Could not fetch community catalog."}

    catalog_map = {s["name"]: s for s in catalog}
    updated = []

    for name, info in log.items():
        if name in catalog_map:
            remote = catalog_map[name]
            remote_hash = _skill_hash(remote)
            if remote_hash != info.get("hash"):
                result = install_skill(name)
                if result.get("status") == "ok":
                    updated.append(name)

    return {"updated": updated, "checked": len(log)}


def skill_info(skill_name):
    """Get detailed info about an installed skill."""
    for skill_dir in [CORE_SKILLS_DIR, DYNAMIC_SKILLS_DIR]:
        target = skill_dir / f"{skill_name}.json"
        if target.exists():
            with open(target) as f:
                return json.load(f)

    return {"error": f"Skill '{skill_name}' not found."}


def export_skills():
    """Export the list of installed skills for backup/migration."""
    installed = list_installed()
    log = _load_install_log()
    return {
        "exported_at": datetime.now().isoformat(),
        "core_skills": installed["core"],
        "dynamic_skills": installed["dynamic"],
        "install_log": log,
    }


# ═══════════════════════════════════════════════════════════════════
# Community Catalog
# ═══════════════════════════════════════════════════════════════════

def _fetch_community_catalog():
    """
    Fetch the community skill catalog.
    Strategy: Try git clone/pull → read catalog.json.
    Fallback: Return a built-in starter catalog.
    """
    catalog_file = COMMUNITY_CACHE / "catalog.json"

    # Try pulling community repo
    COMMUNITY_CACHE.mkdir(parents=True, exist_ok=True)
    repo_dir = COMMUNITY_CACHE / "repo"

    try:
        if (repo_dir / ".git").exists():
            subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=str(repo_dir), capture_output=True, timeout=15
            )
        else:
            subprocess.run(
                ["git", "clone", "--depth=1", COMMUNITY_REPO_URL, str(repo_dir)],
                capture_output=True, timeout=30
            )

        # Read catalog from repo
        repo_catalog = repo_dir / "catalog.json"
        if repo_catalog.exists():
            with open(repo_catalog) as f:
                return json.load(f)
    except Exception:
        pass

    # Fallback: cached catalog
    if catalog_file.exists():
        with open(catalog_file) as f:
            return json.load(f)

    # Fallback: built-in starter catalog
    return _builtin_catalog()


def _builtin_catalog():
    """Built-in starter catalog for when the remote repo is unavailable."""
    return [
        {
            "name": "smart_home",
            "description": "Control smart home devices (lights, thermostat, locks) via voice",
            "version": "1.0.0",
            "author": "ai-distro-community",
            "tags": ["iot", "home", "automation"],
            "intents": ["turn_on_lights", "set_temperature", "lock_door"],
            "triggers": ["turn on", "set temp", "lock"],
        },
        {
            "name": "code_assistant",
            "description": "Programming help: explain code, debug errors, suggest fixes",
            "version": "1.0.0",
            "author": "ai-distro-community",
            "tags": ["dev", "code", "programming"],
            "intents": ["explain_code", "debug_error", "suggest_fix"],
            "triggers": ["explain this code", "debug", "fix this"],
        },
        {
            "name": "media_controller",
            "description": "Control media playback: play music, pause, skip, volume",
            "version": "1.0.0",
            "author": "ai-distro-community",
            "tags": ["media", "music", "audio"],
            "intents": ["play_music", "pause", "skip_track", "set_volume"],
            "triggers": ["play", "pause", "next song", "volume"],
        },
        {
            "name": "fitness_tracker",
            "description": "Track workouts, step counts, and health goals",
            "version": "1.0.0",
            "author": "ai-distro-community",
            "tags": ["health", "fitness", "tracking"],
            "intents": ["log_workout", "show_steps", "set_goal"],
            "triggers": ["log workout", "how many steps", "fitness goal"],
        },
        {
            "name": "note_taker",
            "description": "Quick voice/text notes with search and organization",
            "version": "1.0.0",
            "author": "ai-distro-community",
            "tags": ["productivity", "notes", "organization"],
            "intents": ["create_note", "search_notes", "list_notes"],
            "triggers": ["take a note", "note:", "search notes"],
        },
    ]


# ═══════════════════════════════════════════════════════════════════
# HTTP Marketplace Server
# ═══════════════════════════════════════════════════════════════════

MARKETPLACE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Distro — Skill Marketplace</title>
<style>
:root {
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --text: #c9d1d9; --muted: #8b949e; --accent: #58a6ff;
  --green: #3fb950; --red: #f85149; --purple: #bc8cff;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Inter', 'SF Pro', -apple-system, sans-serif;
  background: var(--bg); color: var(--text);
  min-height: 100vh; padding: 2rem;
}
h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
h1 span { color: var(--accent); }
.subtitle { color: var(--muted); margin-bottom: 2rem; }
.tabs { display: flex; gap: 1rem; margin-bottom: 2rem; }
.tab {
  padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer;
  background: var(--surface); border: 1px solid var(--border);
  color: var(--muted); transition: all 0.2s;
}
.tab.active, .tab:hover { color: var(--accent); border-color: var(--accent); }
.search-box {
  width: 100%; padding: 0.8rem 1.2rem; border-radius: 10px;
  background: var(--surface); border: 1px solid var(--border);
  color: var(--text); font-size: 1rem; margin-bottom: 2rem;
}
.search-box:focus { outline: none; border-color: var(--accent); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.2rem; }
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 1.5rem; transition: all 0.2s;
}
.card:hover { border-color: var(--accent); transform: translateY(-2px); }
.card-title { font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem; }
.card-desc { color: var(--muted); font-size: 0.9rem; margin-bottom: 1rem; line-height: 1.5; }
.card-meta { display: flex; gap: 0.8rem; flex-wrap: wrap; align-items: center; }
.tag {
  padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.75rem;
  background: rgba(88,166,255,0.1); color: var(--accent);
}
.tag.core { background: rgba(63,185,80,0.1); color: var(--green); }
.version { color: var(--muted); font-size: 0.8rem; }
.btn {
  padding: 0.5rem 1rem; border-radius: 8px; border: none;
  cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: all 0.2s;
}
.btn-install { background: var(--accent); color: #fff; }
.btn-install:hover { filter: brightness(1.2); }
.btn-remove { background: rgba(248,81,73,0.15); color: var(--red); }
.btn-remove:hover { background: rgba(248,81,73,0.3); }
.empty { text-align: center; padding: 3rem; color: var(--muted); }
.stats { display: flex; gap: 2rem; margin-bottom: 2rem; }
.stat { text-align: center; }
.stat-val { font-size: 2rem; font-weight: 700; color: var(--accent); }
.stat-label { color: var(--muted); font-size: 0.85rem; }
</style>
</head>
<body>
<h1>🧩 <span>Skill Marketplace</span></h1>
<p class="subtitle">Discover, install, and manage AI capabilities</p>
<div class="stats" id="stats"></div>
<div class="tabs">
  <div class="tab active" onclick="showTab('installed')">Installed</div>
  <div class="tab" onclick="showTab('community')">Community</div>
</div>
<input class="search-box" placeholder="Search skills..." oninput="filterSkills(this.value)">
<div class="grid" id="grid"></div>
<script>
let currentTab = 'installed';
let allSkills = [];

async function load() {
  const r = await fetch('/api/list');
  const d = await r.json();
  allSkills = [
    ...(d.core||[]).map(s => ({...s, category:'core'})),
    ...(d.dynamic||[]).map(s => ({...s, category:'dynamic'}))
  ];
  const el = document.getElementById('stats');
  el.innerHTML = `
    <div class="stat"><div class="stat-val">${d.core?.length||0}</div><div class="stat-label">Core Skills</div></div>
    <div class="stat"><div class="stat-val">${d.dynamic?.length||0}</div><div class="stat-label">Community</div></div>
    <div class="stat"><div class="stat-val">${allSkills.reduce((a,s)=>a+(s.intents||0),0)}</div><div class="stat-label">Total Intents</div></div>
  `;
  render(allSkills);
}

async function showTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  if (tab === 'community') {
    const r = await fetch('/api/community');
    const d = await r.json();
    render(d.map(s => ({...s, category:'community'})));
  } else {
    load();
  }
}

function render(skills) {
  const grid = document.getElementById('grid');
  if (!skills.length) { grid.innerHTML = '<div class="empty">No skills found</div>'; return; }
  grid.innerHTML = skills.map(s => `
    <div class="card">
      <div class="card-title">${s.name||'?'}</div>
      <div class="card-desc">${s.description||''}</div>
      <div class="card-meta">
        <span class="tag ${s.category==='core'?'core':''}">${s.category||'?'}</span>
        ${s.version?`<span class="version">v${s.version}</span>`:''}
        ${(s.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('')}
        ${s.category==='community'?`<button class="btn btn-install" onclick="installSkill('${s.name}')">Install</button>`:''}
        ${s.category==='dynamic'?`<button class="btn btn-remove" onclick="removeSkill('${s.name}')">Remove</button>`:''}
      </div>
    </div>
  `).join('');
}

function filterSkills(q) {
  const lower = q.toLowerCase();
  const filtered = allSkills.filter(s =>
    (s.name||'').toLowerCase().includes(lower) ||
    (s.description||'').toLowerCase().includes(lower)
  );
  render(filtered);
}

async function installSkill(name) {
  const r = await fetch('/api/install?name='+encodeURIComponent(name), {method:'POST'});
  const d = await r.json();
  alert(d.message || d.error || 'Done');
  load();
}

async function removeSkill(name) {
  const r = await fetch('/api/uninstall?name='+encodeURIComponent(name), {method:'POST'});
  const d = await r.json();
  alert(d.message || d.error || 'Done');
  load();
}

load();
</script>
</body>
</html>"""


class MarketplaceHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._html(MARKETPLACE_HTML)
        elif self.path == "/api/list":
            self._json(list_installed())
        elif self.path == "/api/community":
            catalog = _fetch_community_catalog() or []
            self._json(catalog)
        elif self.path.startswith("/api/info"):
            name = self.path.split("name=")[-1] if "name=" in self.path else ""
            self._json(skill_info(name))
        elif self.path == "/api/export":
            self._json(export_skills())
        elif self.path == "/health":
            self._json({"status": "ok", "service": "skill_marketplace"})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path.startswith("/api/install"):
            name = self.path.split("name=")[-1] if "name=" in self.path else ""
            self._json(install_skill(name))
        elif self.path.startswith("/api/uninstall"):
            name = self.path.split("name=")[-1] if "name=" in self.path else ""
            self._json(uninstall_skill(name))
        elif self.path == "/api/update":
            self._json(update_all())
        else:
            self._json({"error": "not found"}, 404)

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, content):
        body = content.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve():
    """Start the marketplace HTTP server."""
    server = http.server.HTTPServer(("0.0.0.0", MARKETPLACE_PORT), MarketplaceHandler)
    print(f"Skill Marketplace → http://localhost:{MARKETPLACE_PORT}")
    server.serve_forever()


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage: skill_marketplace.py <command> [args]")
        print("Commands: list, search, install, uninstall, update, info, export, serve")
        return

    cmd = sys.argv[1]

    if cmd == "list":
        result = list_installed()
        print(json.dumps(result, indent=2))

    elif cmd == "search":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        results = search_community(query)
        print(json.dumps(results, indent=2))

    elif cmd == "install":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        if not name:
            print("Usage: skill_marketplace.py install <skill_name>")
            return
        print(json.dumps(install_skill(name), indent=2))

    elif cmd == "uninstall":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        if not name:
            print("Usage: skill_marketplace.py uninstall <skill_name>")
            return
        print(json.dumps(uninstall_skill(name), indent=2))

    elif cmd == "update":
        print(json.dumps(update_all(), indent=2))

    elif cmd == "info":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(skill_info(name), indent=2))

    elif cmd == "export":
        print(json.dumps(export_skills(), indent=2))

    elif cmd == "serve":
        serve()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
