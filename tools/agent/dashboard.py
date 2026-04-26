#!/usr/bin/env python3
"""
AI Distro — Web Status Dashboard

A lightweight, self-contained HTTP dashboard showing real-time
system status, service health, Bayesian learning state, event log,
and skill inventory.

Runs on port 7841 by default.
No external dependencies — uses only Python stdlib + AI Distro modules.
"""
import http.server
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

PORT = int(os.environ.get("AI_DISTRO_DASHBOARD_PORT", "7841"))
AGENT_SOCKET = os.environ.get("AI_DISTRO_IPC_SOCKET", "/run/ai-distro/agent.sock")
VISION_URL = "http://127.0.0.1:7860/health"
SKILLS_CORE_DIR = Path(os.environ.get(
    "AI_DISTRO_SKILLS_CORE_DIR",
    os.path.expanduser("~/AI_Distro/src/skills/core")
))
SKILLS_DYNAMIC_DIR = Path(os.environ.get(
    "AI_DISTRO_SKILLS_DYNAMIC_DIR",
    os.path.expanduser("~/AI_Distro/src/skills/dynamic")
))
USER_CONFIG = Path(os.path.expanduser("~/.config/ai-distro-user.json"))

SERVICES = [
    "ai-distro-agent",
    "ai-distro-voice",
    "ai-distro-hud",
    "ai-distro-curator",
    "ai-distro-spirit",
    "ai-distro-healer",
    "ai-distro-hardware",
    "ai-distro-vision",
    "ai-distro-eventbus",
    "ai-distro-wakeword",
]


def get_service_statuses():
    """Check systemd user service statuses."""
    statuses = []
    for svc in SERVICES:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", svc],
                capture_output=True, text=True, timeout=3
            )
            state = result.stdout.strip()
        except Exception:
            state = "unknown"
        statuses.append({"name": svc, "state": state})
    return statuses


def get_system_stats():
    """Get CPU, memory, disk stats."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()
        return {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "memory_used_gb": round(mem.used / (1024**3), 1),
            "memory_total_gb": round(mem.total / (1024**3), 1),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "battery_percent": battery.percent if battery else None,
            "battery_charging": battery.power_plugged if battery else None,
        }
    except ImportError:
        return {"error": "psutil not installed"}


def get_vision_health():
    """Check vision microservice."""
    try:
        req = urllib.request.Request(VISION_URL)
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read())
    except Exception:
        return {"status": "unreachable"}


def get_bayesian_profile():
    """Get Bayesian learning state."""
    try:
        from bayesian_engine import BayesianEngine
        engine = BayesianEngine()
        return engine.get_user_profile()
    except Exception as e:
        return {"error": str(e)}


def get_skills():
    """List installed skills."""
    skills = []
    for d in [SKILLS_CORE_DIR, SKILLS_DYNAMIC_DIR]:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                with open(p) as f:
                    skill = json.load(f)
                skills.append({
                    "name": skill.get("name", p.stem),
                    "description": skill.get("description", ""),
                    "type": "core" if "core" in str(d) else "dynamic",
                    "handler": skill.get("handler_type", "unknown"),
                })
            except Exception:
                pass
    return skills


def get_recent_events(count=30):
    """Query event bus for recent events."""
    try:
        from event_bus import get_recent_events as _get_events
        return _get_events(count)
    except Exception:
        return []


def get_user_config():
    """Read user config."""
    try:
        with open(USER_CONFIG) as f:
            return json.load(f)
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════
# HTML Template
# ═══════════════════════════════════════════════════════════════════
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Distro — Command Center</title>
<meta name="description" content="AI Distro system status dashboard">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg-primary: #0a0a1a;
    --bg-card: rgba(20, 20, 45, 0.8);
    --bg-card-hover: rgba(30, 30, 60, 0.9);
    --border: rgba(124, 58, 237, 0.3);
    --border-glow: rgba(124, 58, 237, 0.6);
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-dim: #64748b;
    --accent: #7c3aed;
    --accent-light: #a78bfa;
    --green: #22c55e;
    --yellow: #eab308;
    --red: #ef4444;
    --blue: #3b82f6;
  }

  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Background glow */
  body::before {
    content: '';
    position: fixed;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 20%, rgba(124, 58, 237, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 70% 80%, rgba(59, 130, 246, 0.05) 0%, transparent 50%);
    z-index: -1;
    animation: bgPulse 20s ease-in-out infinite alternate;
  }

  @keyframes bgPulse {
    0% { opacity: 0.6; }
    100% { opacity: 1; }
  }

  /* Header */
  .header {
    padding: 24px 32px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    backdrop-filter: blur(20px);
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(10, 10, 26, 0.85);
  }
  .header h1 {
    font-size: 1.4rem;
    font-weight: 600;
    background: linear-gradient(135deg, var(--accent-light), var(--blue));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
  }
  .header .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 8px;
    animation: pulse 2s ease-in-out infinite;
  }
  .header .status-dot.active { background: var(--green); box-shadow: 0 0 8px var(--green); }
  .header .status-dot.inactive { background: var(--red); }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
    font-size: 0.85rem;
    color: var(--text-secondary);
  }

  .refresh-btn {
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--accent-light);
    padding: 6px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.82rem;
    transition: all 0.2s;
  }
  .refresh-btn:hover {
    border-color: var(--border-glow);
    background: var(--bg-card-hover);
  }

  /* Grid */
  .dashboard {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
    gap: 20px;
    padding: 24px 32px;
    max-width: 1600px;
    margin: 0 auto;
  }

  /* Cards */
  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 20px 24px;
    backdrop-filter: blur(12px);
    transition: border-color 0.3s, transform 0.2s;
  }
  .card:hover {
    border-color: var(--border-glow);
    transform: translateY(-2px);
  }
  .card h2 {
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .card h2 .icon {
    font-size: 1.1rem;
  }
  .card.wide { grid-column: span 2; }
  @media (max-width: 800px) { .card.wide { grid-column: span 1; } }

  /* Service List */
  .service-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .service-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 8px;
    background: rgba(15, 15, 35, 0.5);
    font-size: 0.82rem;
    font-family: 'JetBrains Mono', monospace;
  }
  .service-item .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .dot.active { background: var(--green); box-shadow: 0 0 6px var(--green); }
  .dot.inactive { background: var(--red); }
  .dot.unknown { background: var(--yellow); }
  .service-item .name { color: var(--text-primary); }

  /* Stats */
  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }
  .stat-row:last-child { border-bottom: none; }
  .stat-label { color: var(--text-secondary); font-size: 0.85rem; }
  .stat-value { font-weight: 600; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; }

  .progress-bar {
    width: 120px;
    height: 6px;
    background: rgba(255,255,255,0.08);
    border-radius: 3px;
    overflow: hidden;
    margin-left: 12px;
  }
  .progress-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s ease;
  }
  .progress-fill.green { background: var(--green); }
  .progress-fill.yellow { background: var(--yellow); }
  .progress-fill.red { background: var(--red); }

  /* Event Log */
  .event-log {
    max-height: 300px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }
  .event-item {
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    font-size: 0.82rem;
    display: grid;
    grid-template-columns: 70px 70px 1fr;
    gap: 8px;
    align-items: start;
  }
  .event-time { color: var(--text-dim); font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; }
  .event-source {
    color: var(--accent-light);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .event-msg { color: var(--text-secondary); }

  /* Skills */
  .skill-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .skill-tag {
    background: rgba(124, 58, 237, 0.15);
    border: 1px solid rgba(124, 58, 237, 0.3);
    color: var(--accent-light);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', monospace;
    cursor: default;
    transition: all 0.2s;
  }
  .skill-tag:hover {
    background: rgba(124, 58, 237, 0.25);
    border-color: var(--accent);
  }
  .skill-tag.dynamic {
    background: rgba(59, 130, 246, 0.15);
    border-color: rgba(59, 130, 246, 0.3);
    color: #93c5fd;
  }

  /* Bayesian */
  .prediction-item {
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }
  .prediction-item:last-child { border-bottom: none; }
  .prediction-action {
    font-weight: 500;
    margin-bottom: 4px;
  }
  .prediction-meta {
    display: flex;
    gap: 16px;
    font-size: 0.78rem;
    color: var(--text-dim);
  }
  .confidence-bar {
    width: 100%;
    height: 4px;
    background: rgba(255,255,255,0.05);
    border-radius: 2px;
    margin-top: 6px;
  }
  .confidence-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--accent-light));
    border-radius: 2px;
    transition: width 0.8s ease;
  }

  /* Empty state */
  .empty { color: var(--text-dim); font-style: italic; font-size: 0.85rem; padding: 12px 0; }
</style>
</head>
<body>

<div class="header">
  <div style="display:flex;align-items:center;gap:12px;">
    <span class="status-dot active" id="pulse-dot"></span>
    <h1>AI DISTRO — COMMAND CENTER</h1>
  </div>
  <div class="header-right">
    <span id="user-greeting"></span>
    <span id="clock"></span>
    <button class="refresh-btn" onclick="refresh()">↻ Refresh</button>
  </div>
</div>

<div class="dashboard">

  <!-- Services -->
  <div class="card" id="services-card">
    <h2><span class="icon">⚙</span> Services</h2>
    <div class="service-grid" id="service-grid">
      <div class="empty">Loading...</div>
    </div>
  </div>

  <!-- System Stats -->
  <div class="card" id="stats-card">
    <h2><span class="icon">📊</span> System</h2>
    <div id="stats-content">
      <div class="empty">Loading...</div>
    </div>
  </div>

  <!-- Bayesian Intelligence -->
  <div class="card" id="bayesian-card">
    <h2><span class="icon">🧠</span> Bayesian Intelligence</h2>
    <div id="bayesian-content">
      <div class="empty">Loading...</div>
    </div>
  </div>

  <!-- Vision -->
  <div class="card" id="vision-card">
    <h2><span class="icon">👁</span> Vision Engine</h2>
    <div id="vision-content">
      <div class="empty">Loading...</div>
    </div>
  </div>

  <!-- Event Log -->
  <div class="card wide" id="events-card">
    <h2><span class="icon">📜</span> Event Log</h2>
    <div class="event-log" id="event-log">
      <div class="empty">Loading...</div>
    </div>
  </div>

  <!-- Skills -->
  <div class="card wide" id="skills-card">
    <h2><span class="icon">🔧</span> Installed Skills</h2>
    <div class="skill-list" id="skill-list">
      <div class="empty">Loading...</div>
    </div>
  </div>

</div>

<script>
  // Clock
  function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent =
      now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) +
      '  ' + now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }
  setInterval(updateClock, 1000);
  updateClock();

  async function fetchJSON(path) {
    const resp = await fetch(path);
    return resp.json();
  }

  function progressColor(pct) {
    if (pct < 60) return 'green';
    if (pct < 85) return 'yellow';
    return 'red';
  }

  async function refresh() {
    // Services
    try {
      const services = await fetchJSON('/api/services');
      const grid = document.getElementById('service-grid');
      grid.innerHTML = services.map(s => {
        const stateClass = s.state === 'active' ? 'active' : (s.state === 'inactive' ? 'inactive' : 'unknown');
        const name = s.name.replace('ai-distro-', '');
        return `<div class="service-item"><span class="dot ${stateClass}"></span><span class="name">${name}</span></div>`;
      }).join('');
    } catch(e) { console.error('Services:', e); }

    // Stats
    try {
      const stats = await fetchJSON('/api/stats');
      const el = document.getElementById('stats-content');
      if (stats.error) {
        el.innerHTML = `<div class="empty">${stats.error}</div>`;
      } else {
        let html = '';
        html += statRow('CPU', `${stats.cpu_percent}%`, stats.cpu_percent);
        html += statRow('Memory', `${stats.memory_used_gb} / ${stats.memory_total_gb} GB`, stats.memory_percent);
        html += statRow('Disk', `${stats.disk_used_gb} / ${stats.disk_total_gb} GB`, stats.disk_percent);
        if (stats.battery_percent !== null) {
          const charge = stats.battery_charging ? ' ⚡' : '';
          html += statRow('Battery', `${stats.battery_percent}%${charge}`, 100 - stats.battery_percent);
        }
        el.innerHTML = html;
      }
    } catch(e) { console.error('Stats:', e); }

    // Bayesian
    try {
      const profile = await fetchJSON('/api/bayesian');
      const el = document.getElementById('bayesian-content');
      if (profile.error) {
        el.innerHTML = `<div class="empty">${profile.error}</div>`;
      } else {
        const preds = profile.predictions || [];
        if (preds.length === 0) {
          el.innerHTML = `<div class="empty">No predictions yet. The AI is still learning your patterns.</div>`;
        } else {
          el.innerHTML = preds.slice(0, 5).map(p => `
            <div class="prediction-item">
              <div class="prediction-action">${p.action}</div>
              <div class="prediction-meta">
                <span>Confidence: ${(p.probability * 100).toFixed(0)}%</span>
                <span>Observations: ${p.observations}</span>
              </div>
              <div class="confidence-bar">
                <div class="confidence-fill" style="width: ${p.probability * 100}%"></div>
              </div>
            </div>
          `).join('');
        }
      }
    } catch(e) { console.error('Bayesian:', e); }

    // Vision
    try {
      const vision = await fetchJSON('/api/vision');
      const el = document.getElementById('vision-content');
      if (vision.status === 'unreachable') {
        el.innerHTML = `<div class="stat-row"><span class="stat-label">Status</span><span class="stat-value" style="color:var(--red)">Offline</span></div>`;
      } else {
        let html = `<div class="stat-row"><span class="stat-label">Status</span><span class="stat-value" style="color:var(--green)">Online</span></div>`;
        html += `<div class="stat-row"><span class="stat-label">Model Loaded</span><span class="stat-value">${vision.model_loaded ? '✓ Yes' : '✗ No'}</span></div>`;
        if (vision.moondream_installed !== undefined) {
          html += `<div class="stat-row"><span class="stat-label">Moondream Installed</span><span class="stat-value">${vision.moondream_installed ? '✓' : '✗'}</span></div>`;
        }
        el.innerHTML = html;
      }
    } catch(e) { console.error('Vision:', e); }

    // Events
    try {
      const events = await fetchJSON('/api/events');
      const el = document.getElementById('event-log');
      if (events.length === 0) {
        el.innerHTML = `<div class="empty">No events recorded yet.</div>`;
      } else {
        el.innerHTML = events.reverse().map(ev => {
          const time = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString('en-US', {hour:'2-digit',minute:'2-digit'}) : '';
          return `<div class="event-item">
            <span class="event-time">${time}</span>
            <span class="event-source">${ev.source || ''}</span>
            <span class="event-msg">${ev.message || ev.title || ''}</span>
          </div>`;
        }).join('');
      }
    } catch(e) { console.error('Events:', e); }

    // Skills
    try {
      const skills = await fetchJSON('/api/skills');
      const el = document.getElementById('skill-list');
      if (skills.length === 0) {
        el.innerHTML = `<div class="empty">No skills installed.</div>`;
      } else {
        el.innerHTML = skills.map(s =>
          `<span class="skill-tag ${s.type}" title="${s.description}">${s.name}</span>`
        ).join('');
      }
    } catch(e) { console.error('Skills:', e); }

    // User greeting
    try {
      const config = await fetchJSON('/api/config');
      const name = config.user_name || 'Pilot';
      document.getElementById('user-greeting').textContent = `Hello, ${name}`;
    } catch(e) {}
  }

  function statRow(label, value, pct) {
    const color = progressColor(pct);
    return `<div class="stat-row">
      <span class="stat-label">${label}</span>
      <div style="display:flex;align-items:center;">
        <span class="stat-value">${value}</span>
        <div class="progress-bar"><div class="progress-fill ${color}" style="width:${Math.min(pct, 100)}%"></div></div>
      </div>
    </div>`;
  }

  // Initial load + auto-refresh
  refresh();
  setInterval(refresh, 15000);
</script>
</body>
</html>"""


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for the dashboard."""

    def log_message(self, fmt, *args):
        # Suppress default access logs
        pass

    def _respond_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _respond_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._respond_html(DASHBOARD_HTML)
        elif self.path == "/api/services":
            self._respond_json(get_service_statuses())
        elif self.path == "/api/stats":
            self._respond_json(get_system_stats())
        elif self.path == "/api/vision":
            self._respond_json(get_vision_health())
        elif self.path == "/api/bayesian":
            self._respond_json(get_bayesian_profile())
        elif self.path == "/api/skills":
            self._respond_json(get_skills())
        elif self.path == "/api/events":
            self._respond_json(get_recent_events())
        elif self.path == "/api/config":
            self._respond_json(get_user_config())
        elif self.path == "/health":
            self._respond_json({"status": "ok", "service": "dashboard"})
        else:
            self.send_error(404)


def main():
    server = http.server.HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"[Dashboard] AI Distro Command Center running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Dashboard] Shutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
