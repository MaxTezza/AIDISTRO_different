#!/usr/bin/env python3
"""
AI Distro — Privacy Dashboard

A zero-dependency web UI showing exactly what data the AI has collected,
what it has accessed, and providing one-click controls to forget everything.

Endpoints:
  GET  /              → Dashboard HTML
  GET  /health        → Health check
  GET  /api/summary   → Data collection summary
  GET  /api/beliefs   → All Bayesian beliefs
  GET  /api/interactions → Recent interaction log
  GET  /api/preferences → Stored preferences
  GET  /api/audit     → Event bus audit log entries
  POST /api/forget    → Wipe all learned data
  POST /api/forget/beliefs    → Wipe beliefs only
  POST /api/forget/interactions → Wipe interaction log only
  POST /api/forget/preferences  → Wipe preferences only

Port: 7843
"""
import http.server
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

PRIVACY_PORT = 7843
BAYESIAN_DB = Path(os.path.expanduser("~/.cache/ai-distro/bayesian.db"))
EVENT_LOG = Path("/tmp/ai-distro-events.jsonl")
USER_CONFIG = Path(os.path.expanduser("~/.config/ai-distro-user.json"))
SPIRIT_CONFIG = Path(os.path.expanduser("~/.config/ai-distro-spirit.json"))
LOCALE_CONFIG = Path(os.path.expanduser("~/.config/ai-distro-locale.json"))


def _db_query(sql, params=()):
    """Safe DB query that returns [] if DB doesn't exist."""
    if not BAYESIAN_DB.exists():
        return []
    conn = sqlite3.connect(str(BAYESIAN_DB))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _db_execute(sql, params=()):
    if not BAYESIAN_DB.exists():
        return 0
    conn = sqlite3.connect(str(BAYESIAN_DB))
    try:
        c = conn.execute(sql, params)
        conn.commit()
        return c.rowcount
    finally:
        conn.close()


def get_summary():
    """Get a high-level summary of all stored data."""
    beliefs = _db_query("SELECT COUNT(*) as c FROM beliefs")
    interactions = _db_query("SELECT COUNT(*) as c FROM interactions")
    preferences = _db_query("SELECT COUNT(*) as c FROM preferences")
    chains = _db_query("SELECT COUNT(*) as c FROM action_chains")

    # Check what files exist
    files = {}
    for name, path in [("bayesian_db", BAYESIAN_DB), ("event_log", EVENT_LOG),
                        ("user_config", USER_CONFIG), ("spirit_config", SPIRIT_CONFIG),
                        ("locale_config", LOCALE_CONFIG)]:
        if path.exists():
            stat = path.stat()
            files[name] = {
                "path": str(path),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }

    # Oldest and newest interaction
    oldest = _db_query("SELECT MIN(timestamp) as t FROM interactions")
    newest = _db_query("SELECT MAX(timestamp) as t FROM interactions")

    return {
        "beliefs": beliefs[0]["c"] if beliefs else 0,
        "interactions": interactions[0]["c"] if interactions else 0,
        "preferences": preferences[0]["c"] if preferences else 0,
        "action_chains": chains[0]["c"] if chains else 0,
        "data_files": files,
        "tracking_since": datetime.fromtimestamp(oldest[0]["t"]).isoformat() if oldest and oldest[0]["t"] else None,
        "last_activity": datetime.fromtimestamp(newest[0]["t"]).isoformat() if newest and newest[0]["t"] else None,
    }


def get_beliefs():
    return _db_query(
        "SELECT context_key, action, alpha, beta, total_observations, last_updated "
        "FROM beliefs ORDER BY total_observations DESC LIMIT 100"
    )


def get_interactions(limit=50):
    rows = _db_query(
        "SELECT timestamp, context_key, action, outcome, metadata "
        "FROM interactions ORDER BY timestamp DESC LIMIT ?", (limit,)
    )
    for r in rows:
        if r.get("timestamp"):
            r["time"] = datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
    return rows


def get_preferences():
    return _db_query("SELECT key, value, confidence, last_updated FROM preferences")


def get_audit_log(limit=50):
    """Read recent event bus audit log entries."""
    if not EVENT_LOG.exists():
        return []
    lines = []
    try:
        with open(EVENT_LOG) as f:
            all_lines = f.readlines()
        for line in all_lines[-limit:]:
            try:
                lines.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    lines.reverse()
    return lines


def forget_all():
    """Nuclear option: wipe all learned data."""
    deleted = {}
    for table in ["beliefs", "interactions", "preferences", "action_chains"]:
        deleted[table] = _db_execute(f"DELETE FROM {table}")
    if EVENT_LOG.exists():
        EVENT_LOG.unlink()
        deleted["event_log"] = "deleted"
    return {"status": "ok", "deleted": deleted, "timestamp": datetime.now().isoformat()}


def forget_table(table):
    if table not in ("beliefs", "interactions", "preferences", "action_chains"):
        return {"error": f"Unknown table: {table}"}
    count = _db_execute(f"DELETE FROM {table}")
    return {"status": "ok", "table": table, "rows_deleted": count}


# ═══════════════════════════════════════════════════════════════════
# HTML Dashboard
# ═══════════════════════════════════════════════════════════════════

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Distro — Privacy Center</title>
<style>
:root {
  --bg: #0a0e14; --surface: #131920; --border: #1e2a36;
  --text: #c5cdd8; --muted: #6b7a8d; --accent: #00d4aa;
  --red: #ff4757; --orange: #ffa502; --green: #2ed573;
  --purple: #a55eea;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Inter', -apple-system, sans-serif;
  background: var(--bg); color: var(--text); min-height: 100vh;
  padding: 2rem; max-width: 1100px; margin: 0 auto;
}
h1 { font-size: 1.6rem; margin-bottom: .3rem; }
h1 span { color: var(--accent); }
.sub { color: var(--muted); margin-bottom: 2rem; font-size: .9rem; }
.cards { display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 1rem; margin-bottom: 2rem; }
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 1.2rem; text-align: center;
}
.card-val { font-size: 2rem; font-weight: 700; color: var(--accent); }
.card-label { color: var(--muted); font-size: .8rem; margin-top: .3rem; }
.section { margin-bottom: 2rem; }
.section h2 { font-size: 1.1rem; margin-bottom: 1rem; color: var(--text); }
table {
  width: 100%; border-collapse: collapse; font-size: .85rem;
  background: var(--surface); border-radius: 10px; overflow: hidden;
}
th { background: var(--border); color: var(--muted); text-align: left; padding: .7rem .8rem; font-weight: 500; }
td { padding: .6rem .8rem; border-top: 1px solid var(--border); }
.actions { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem; }
.btn {
  padding: .7rem 1.4rem; border-radius: 10px; border: none;
  cursor: pointer; font-size: .9rem; font-weight: 600; transition: all .2s;
}
.btn-danger { background: rgba(255,71,87,.15); color: var(--red); }
.btn-danger:hover { background: rgba(255,71,87,.3); }
.btn-warn { background: rgba(255,165,2,.12); color: var(--orange); }
.btn-warn:hover { background: rgba(255,165,2,.25); }
.files { font-size: .8rem; color: var(--muted); }
.files span { display: block; margin: .2rem 0; }
.tag { display: inline-block; padding: .15rem .5rem; border-radius: 6px; font-size: .75rem; }
.tag-pos { background: rgba(46,213,115,.12); color: var(--green); }
.tag-neg { background: rgba(255,71,87,.12); color: var(--red); }
.empty { text-align: center; padding: 2rem; color: var(--muted); }
#toast {
  position: fixed; bottom: 2rem; right: 2rem; background: var(--surface);
  border: 1px solid var(--accent); color: var(--accent); padding: 1rem 1.5rem;
  border-radius: 10px; display: none; font-weight: 500; z-index: 999;
}
</style>
</head>
<body>
<h1>🛡️ <span>Privacy Center</span></h1>
<p class="sub">Everything AI Distro knows about you — full transparency, full control</p>

<div class="cards" id="cards">
  <div class="card"><div class="card-val" id="s-beliefs">—</div><div class="card-label">Learned Beliefs</div></div>
  <div class="card"><div class="card-val" id="s-interactions">—</div><div class="card-label">Interactions Logged</div></div>
  <div class="card"><div class="card-val" id="s-prefs">—</div><div class="card-label">Preferences</div></div>
  <div class="card"><div class="card-val" id="s-chains">—</div><div class="card-label">Action Chains</div></div>
</div>

<div class="actions">
  <button class="btn btn-warn" onclick="forgetTable('interactions')">🗑 Clear Interaction Log</button>
  <button class="btn btn-warn" onclick="forgetTable('beliefs')">🗑 Clear Beliefs</button>
  <button class="btn btn-warn" onclick="forgetTable('preferences')">🗑 Clear Preferences</button>
  <button class="btn btn-danger" onclick="forgetAll()">💣 Forget Everything</button>
</div>

<div class="section"><h2>Recent Interactions</h2><table id="t-interactions"><thead><tr><th>Time</th><th>Context</th><th>Action</th><th>Outcome</th></tr></thead><tbody></tbody></table></div>
<div class="section"><h2>Stored Preferences</h2><table id="t-prefs"><thead><tr><th>Key</th><th>Value</th><th>Confidence</th></tr></thead><tbody></tbody></table></div>
<div class="section"><h2>Top Beliefs</h2><table id="t-beliefs"><thead><tr><th>Context</th><th>Action</th><th>Probability</th><th>Observations</th></tr></thead><tbody></tbody></table></div>
<div class="section"><h2>Data Files</h2><div class="files" id="files"></div></div>

<div id="toast"></div>

<script>
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3000);
}

async function load() {
  const s = await (await fetch('/api/summary')).json();
  document.getElementById('s-beliefs').textContent = s.beliefs || 0;
  document.getElementById('s-interactions').textContent = s.interactions || 0;
  document.getElementById('s-prefs').textContent = s.preferences || 0;
  document.getElementById('s-chains').textContent = s.action_chains || 0;

  const fl = document.getElementById('files');
  fl.innerHTML = Object.entries(s.data_files||{}).map(([k,v]) =>
    `<span>📄 <b>${k}</b>: ${v.path} (${v.size_kb} KB, modified ${v.modified})</span>`
  ).join('') || '<span>No data files found</span>';

  // Interactions
  const ints = await (await fetch('/api/interactions')).json();
  const ib = document.querySelector('#t-interactions tbody');
  ib.innerHTML = ints.map(i => `<tr><td>${i.time||'?'}</td><td>${i.context_key||''}</td><td>${i.action||''}</td><td><span class="tag ${i.outcome==='positive'?'tag-pos':'tag-neg'}">${i.outcome}</span></td></tr>`).join('') || '<tr><td colspan=4 class="empty">No interactions logged</td></tr>';

  // Preferences
  const prefs = await (await fetch('/api/preferences')).json();
  const pb = document.querySelector('#t-prefs tbody');
  pb.innerHTML = prefs.map(p => `<tr><td>${p.key}</td><td>${p.value}</td><td>${(p.confidence*100).toFixed(0)}%</td></tr>`).join('') || '<tr><td colspan=3 class="empty">No preferences</td></tr>';

  // Beliefs
  const bel = await (await fetch('/api/beliefs')).json();
  const bb = document.querySelector('#t-beliefs tbody');
  bb.innerHTML = bel.map(b => {
    const prob = (b.alpha/(b.alpha+b.beta)*100).toFixed(1);
    return `<tr><td>${b.context_key}</td><td>${b.action}</td><td>${prob}%</td><td>${b.total_observations}</td></tr>`;
  }).join('') || '<tr><td colspan=4 class="empty">No beliefs</td></tr>';
}

async function forgetTable(t) {
  if (!confirm('Clear all '+t+'? This cannot be undone.')) return;
  const r = await (await fetch('/api/forget/'+t, {method:'POST'})).json();
  toast(r.status==='ok' ? '✓ Cleared '+t : r.error);
  load();
}

async function forgetAll() {
  if (!confirm('⚠️ FORGET EVERYTHING? All learned behavior, preferences, and logs will be permanently deleted.')) return;
  if (!confirm('Are you absolutely sure? This is irreversible.')) return;
  const r = await (await fetch('/api/forget', {method:'POST'})).json();
  toast(r.status==='ok' ? '✓ All data erased' : 'Error');
  load();
}

load();
setInterval(load, 30000);
</script>
</body>
</html>"""


class PrivacyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._html(DASHBOARD_HTML)
        elif self.path == "/health":
            self._json({"status": "ok", "service": "privacy_dashboard"})
        elif self.path == "/api/summary":
            self._json(get_summary())
        elif self.path == "/api/beliefs":
            self._json(get_beliefs())
        elif self.path.startswith("/api/interactions"):
            self._json(get_interactions())
        elif self.path == "/api/preferences":
            self._json(get_preferences())
        elif self.path == "/api/audit":
            self._json(get_audit_log())
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/forget":
            self._json(forget_all())
        elif self.path.startswith("/api/forget/"):
            table = self.path.split("/")[-1]
            self._json(forget_table(table))
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


def main():
    server = http.server.HTTPServer(("0.0.0.0", PRIVACY_PORT), PrivacyHandler)
    print(f"Privacy Center → http://localhost:{PRIVACY_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
