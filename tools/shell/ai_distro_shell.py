#!/usr/bin/env python3
import json
import os
import sys
import socket
import subprocess
import time
import uuid
from collections import deque
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

DEFAULT_SOCKET = "/run/ai-distro/agent.sock"
DEFAULT_CORE_SOCKET = "/run/ai-distro/core.sock"
DEFAULT_STATIC = "/usr/share/ai-distro/ui/shell"
DEFAULT_PERSONA = "/etc/ai-distro/persona.json"
DEFAULT_PERSONA_ALFRED = "/etc/ai-distro/persona.alfred.json"
DEFAULT_ONBOARDING = os.path.expanduser("~/.config/ai-distro/shell-onboarding.json")
DEFAULT_PROVIDERS = os.path.expanduser("~/.config/ai-distro/providers.json")
DEFAULT_AUDIT_LOG = "/var/log/ai-distro-agent/audit.jsonl"


def agent_request(payload: dict, timeout=4.0):
    socket_path = os.environ.get("AI_DISTRO_IPC_SOCKET", DEFAULT_SOCKET)
    data = (json.dumps(payload) + "\n").encode("utf-8")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(socket_path)
        client.sendall(data)
        response = b""
        while not response.endswith(b"\n"):
            chunk = client.recv(4096)
            if not chunk:
                break
            response += chunk
        if not response:
            raise RuntimeError("empty response")
        return json.loads(response.decode("utf-8").strip())


def core_request(payload: dict, timeout=2.0):
    socket_path = os.environ.get("AI_DISTRO_CORE_SOCKET", DEFAULT_CORE_SOCKET)
    data = (json.dumps(payload) + "\n").encode("utf-8")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(socket_path)
        client.sendall(data)
        response = b""
        while not response.endswith(b"\n"):
            chunk = client.recv(4096)
            if not chunk:
                break
            response += chunk
        if not response:
            raise RuntimeError("empty response")
        return json.loads(response.decode("utf-8").strip())


class ShellHandler(SimpleHTTPRequestHandler):
    OAUTH_SESSIONS = {}
    PROACTIVE_QUEUE = deque(maxlen=10)

    def end_headers(self):
        # Keep shell UI assets fresh during rapid iteration and handoff recovery.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _user_state_dir(self):
        base = os.path.expanduser("~/.local/state/ai-distro-agent")
        os.makedirs(base, exist_ok=True)
        return base

    def _ensure_dir_with_fallback(self, preferred_dir, fallback_dir):
        try:
            os.makedirs(preferred_dir, exist_ok=True)
            return preferred_dir
        except PermissionError:
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir

    def _plain_error_message(self, message="", default_message="Request failed."):
        msg = str(message or "").strip()
        if not msg:
            return default_message
        lower = msg.lower()

        if "rate limit" in lower:
            return "The service is busy right now. Please wait a moment and try again."
        if any(token in lower for token in ("permission denied", "forbidden", "unauthorized", "access denied")):
            return "Access was denied. Check account permissions or reconnect the provider."
        if "timed out" in lower or "timeout" in lower:
            return "The request took too long. Please try again."
        if any(
            token in lower
            for token in (
                "connection refused",
                "connection reset",
                "network is unreachable",
                "temporary failure in name resolution",
                "proxy",
                "dns",
                "offline",
            )
        ):
            return "Network connection failed while contacting the service. Check connectivity and try again."
        if any(
            token in lower
            for token in (
                "invalid_grant",
                "invalid_client",
                "authorization code",
                "oauth",
                "consent_required",
            )
        ):
            return "Sign-in authorization failed. Start Connect again and approve access."
        if "not found" in lower or "no such file" in lower:
            return "Required resource was not found. Check setup and try again."
        if "agent unavailable" in lower or "empty response" in lower:
            return "The assistant service is temporarily unavailable. Please try again in a few seconds."

        return msg

    def _load_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _fallback_path(self, filename):
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(here, "..", ".."))
        candidate = os.path.join(repo_root, "configs", filename)
        if os.path.exists(candidate):
            return candidate
        return None

    def _agent_tool_path(self, filename):
        packaged = Path("/usr/lib/ai-distro") / filename
        if packaged.exists():
            return str(packaged)
        here = Path(__file__).resolve().parent
        repo_tool = here.parent / "agent" / filename
        if repo_tool.exists():
            return str(repo_tool)
        return str(packaged)

    def _server_base_url(self):
        host = os.environ.get("AI_DISTRO_SHELL_HOST", "127.0.0.1")
        port = int(os.environ.get("AI_DISTRO_SHELL_PORT", "17842"))
        return f"http://{host}:{port}"

    def _load_persona(self):
        path = os.environ.get("AI_DISTRO_PERSONA", DEFAULT_PERSONA)
        if os.path.exists(path):
            return self._load_json(path)
        fallback = self._fallback_path("persona.json")
        if fallback:
            return self._load_json(fallback)
        return {}

    def _load_persona_presets(self):
        presets = {}
        max_path = os.environ.get("AI_DISTRO_PERSONA", DEFAULT_PERSONA)
        if os.path.exists(max_path):
            presets["max"] = self._load_json(max_path)
        else:
            fallback = self._fallback_path("persona.json")
            if fallback:
                presets["max"] = self._load_json(fallback)

        alfred_path = DEFAULT_PERSONA_ALFRED
        if os.path.exists(alfred_path):
            presets["alfred"] = self._load_json(alfred_path)
        else:
            fallback = self._fallback_path("persona.alfred.json")
            if fallback:
                presets["alfred"] = self._load_json(fallback)
        return presets

    def _write_persona(self, preset_key):
        presets = self._load_persona_presets()
        if preset_key not in presets:
            return False, "unknown preset"
        path = os.environ.get("AI_DISTRO_PERSONA", DEFAULT_PERSONA)
        data = presets[preset_key]
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
                fh.write("\n")
            return True, path
        except Exception as exc:
            return False, str(exc)

    def _onboarding_path(self):
        return os.environ.get("AI_DISTRO_ONBOARDING_STATE", DEFAULT_ONBOARDING)

    def _load_onboarding(self):
        path = self._onboarding_path()
        if not os.path.exists(path):
            return {}
        return self._load_json(path)

    def _write_onboarding(self, state):
        path = self._onboarding_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2)
                fh.write("\n")
            return True, path
        except Exception as exc:
            return False, str(exc)

    def _providers_path(self):
        return os.environ.get("AI_DISTRO_PROVIDERS_FILE", DEFAULT_PROVIDERS)

    def _default_providers(self):
        return {"calendar": "local", "email": "gmail", "weather": "default"}

    def _normalize_provider_value(self, key, value):
        val = str(value or "").strip().lower()
        if not val:
            return self._default_providers().get(key, "")
        if key == "weather":
            if val in ("default", "wttr"):
                return val
            if val == "local":
                return "local"
            return "default"
        return val

    def _load_providers(self):
        path = self._providers_path()
        providers = self._default_providers()
        if not os.path.exists(path):
            return providers
        payload = self._load_json(path)
        if isinstance(payload, dict):
            for key in ("calendar", "email", "weather"):
                val = payload.get(key)
                if isinstance(val, str) and val.strip():
                    providers[key] = self._normalize_provider_value(key, val)
        return providers

    def _write_providers(self, providers):
        path = self._providers_path()
        data = self._default_providers()
        if isinstance(providers, dict):
            for key in ("calendar", "email", "weather"):
                val = providers.get(key)
                if isinstance(val, str) and val.strip():
                    data[key] = self._normalize_provider_value(key, val)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
                fh.write("\n")
            return True, path
        except Exception as exc:
            return False, str(exc)

    def _extract_url(self, text):
        m = re.search(r"https://[^\s]+", text or "")
        return m.group(0) if m else ""

    def _audit_log_path(self):
        path = os.environ.get("AI_DISTRO_AUDIT_LOG", DEFAULT_AUDIT_LOG)
        parent = os.path.dirname(path) or "."
        fallback_parent = self._user_state_dir()
        chosen_parent = self._ensure_dir_with_fallback(parent, fallback_parent)
        if chosen_parent != parent:
            return os.path.join(chosen_parent, "audit.jsonl")
        return path

    def _memory_notes_path(self):
        dir_path = os.environ.get(
            "AI_DISTRO_MEMORY_DIR", "/var/lib/ai-distro-agent/memory"
        )
        fallback_dir = os.path.join(self._user_state_dir(), "memory")
        dir_path = self._ensure_dir_with_fallback(dir_path, fallback_dir)
        return os.path.join(dir_path, "notes.jsonl")

    def _clear_memory_notes(self):
        path = self._memory_notes_path()
        try:
            if os.path.exists(path):
                os.remove(path)
            return True, "memory notes cleared"
        except Exception as exc:
            return False, str(exc)

    def _truncate_audit_log(self, keep_lines=64):
        path = self._audit_log_path()
        if not os.path.exists(path):
            return True, "audit log empty"
        try:
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            keep = int(os.environ.get("AI_DISTRO_AUDIT_KEEP_LINES", keep_lines))
            trimmed = lines[-keep:] if keep > 0 else []
            with open(path, "w", encoding="utf-8") as fh:
                fh.writelines(trimmed)
            return True, f"audit log truncated to {len(trimmed)} entries"
        except Exception as exc:
            return False, str(exc)

    def _load_notes(self):
        path = self._memory_notes_path()
        entries = []
        if not os.path.exists(path):
            return entries
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        note = str(data.get("note", "")).strip()
                        if note:
                            entries.append(note)
                    except Exception:
                        continue
        except Exception:
            pass
        return entries

    def _load_audit_messages(self, limit=32):
        path = self._audit_log_path()
        messages = []
        if not os.path.exists(path):
            return messages
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    if len(messages) >= limit:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    msg = str(data.get("message", "") or data.get("action", "")).strip()
                    if msg:
                        messages.append(msg)
        except Exception:
            pass
        return messages

    def _tag_summaries(self):
        keywords = {
            "Photos": ["photo", "image", "screenshot", "camera"],
            "Documents": ["document", "report", "pdf", "notes", "resume", "presentation"],
            "Videos": ["video", "movie", "clip"],
            "Music": ["music", "song", "track"],
            "Downloads": ["download", "installer", "zip"],
            "System": ["update", "upgrade", "install", "service"],
        }
        hits = {tag: [] for tag in keywords}
        entries = self._load_notes() + self._load_audit_messages()
        for text in entries:
            lower = text.lower()
            for tag, words in keywords.items():
                if any(word in lower for word in words):
                    hits[tag].append(text)
        summaries = []
        for tag, items in hits.items():
            if not items:
                continue
            summary = items[0]
            summaries.append(
                {
                    "category": tag,
                    "snippet": summary,
                    "count": len(items),
                    "suggested_command": f"show my {tag.lower()}",
                }
            )
            return summaries

    def _notification_title(self, event):
        if not isinstance(event, dict):
            return "System"
        event_type = str(event.get("type", "")).strip().lower()
        action = str(event.get("action", "")).strip().lower()
        target = str(event.get("target", "")).strip().lower()
        provider = str(event.get("provider", "")).strip().lower()
        status = str(event.get("status", "")).strip().lower()

        if event_type == "action_outcome":
            labels = {
                "package_install": "App install",
                "package_remove": "App removal",
                "system_update": "System update",
            }
            base = labels.get(action, "Task")
            if status in ("ok", "error", "confirm"):
                return f"{base} ({status})"
            return base
        if event_type in ("provider_connect", "provider_test"):
            pieces = []
            if target:
                pieces.append(target.title())
            if provider:
                pieces.append(provider.title())
            if status:
                pieces.append(status)
            if pieces:
                return " ".join(pieces)
            return "Provider"
        if event_type:
            return event_type.replace("_", " ").title()
        return "System"

    def _search_tokens(self, query):
        return [token for token in re.split(r"\s+", str(query or "").strip().lower()) if token]

    def _search_match(self, haystack, tokens):
        if not tokens:
            return False
        text = str(haystack or "").lower()
        return all(token in text for token in tokens)

    def _search_files(self, tokens, limit=8):
        roots = [
            Path(os.path.expanduser("~/Desktop")),
            Path(os.path.expanduser("~/Documents")),
            Path(os.path.expanduser("~/Downloads")),
            Path(os.path.expanduser("~/Pictures")),
        ]
        results = []
        seen = set()
        scan_budget = 2200
        for root in roots:
            if len(results) >= limit or scan_budget <= 0:
                break
            if not root.exists() or not root.is_dir():
                continue
            try:
                for current_root, dirs, files in os.walk(root):
                    dirs.sort()
                    files.sort()
                    for name in files:
                        if len(results) >= limit or scan_budget <= 0:
                            break
                        scan_budget -= 1
                        full = os.path.join(current_root, name)
                        if full in seen:
                            continue
                        rel = os.path.relpath(full, os.path.expanduser("~"))
                        if self._search_match(f"{name} {rel}", tokens):
                            results.append(
                                {
                                    "source": "files",
                                    "title": name,
                                    "detail": f"~/{rel}",
                                }
                            )
                            seen.add(full)
                    if len(results) >= limit or scan_budget <= 0:
                        break
            except Exception:
                continue
        return results

    def _search_settings(self, tokens, limit=6):
        providers = self._load_providers()
        onboarding = self._load_onboarding()
        persona = self._load_persona()
        lite_mode = self._load_lite_mode_state()
        entries = [
            ("settings", "Calendar provider", providers.get("calendar", "local")),
            ("settings", "Email provider", providers.get("email", "gmail")),
            ("settings", "Weather provider", providers.get("weather", "default")),
            ("settings", "Lite mode", "enabled" if lite_mode else "disabled"),
            ("settings", "Onboarding", "completed" if onboarding.get("completed") else "incomplete"),
            ("settings", "Persona voice", persona.get("voice_name") or "default"),
        ]
        out = []
        for source, title, value in entries:
            if len(out) >= limit:
                break
            blob = f"{title} {value}"
            if self._search_match(blob, tokens):
                out.append({"source": source, "title": title, "detail": str(value)})
        return out

    def _desktop_app_entries(self):
        app_dirs = [
            Path("/usr/share/applications"),
            Path(os.path.expanduser("~/.local/share/applications")),
        ]
        apps = []
        seen = set()
        for app_dir in app_dirs:
            if not app_dir.exists() or not app_dir.is_dir():
                continue
            try:
                for path in sorted(app_dir.glob("*.desktop")):
                    name = ""
                    exec_cmd = ""
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                            for line in fh:
                                line = line.strip()
                                if not name and line.startswith("Name="):
                                    name = line.split("=", 1)[1].strip()
                                elif not exec_cmd and line.startswith("Exec="):
                                    exec_cmd = line.split("=", 1)[1].strip()
                                if name and exec_cmd:
                                    break
                    except Exception:
                        continue
                    app_name = name or path.stem
                    key = app_name.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    apps.append(
                        {
                            "name": app_name,
                            "exec": exec_cmd,
                        }
                    )
            except Exception:
                continue
        return apps

    def _search_apps(self, tokens, limit=8):
        out = []
        for app in self._desktop_app_entries():
            if len(out) >= limit:
                break
            blob = f"{app.get('name', '')} {app.get('exec', '')}"
            if self._search_match(blob, tokens):
                out.append(
                    {
                        "source": "apps",
                        "title": app.get("name", "App"),
                        "detail": app.get("exec", ""),
                    }
                )
        return out

    def _search_provider_metadata(self, tokens, limit=6):
        providers = self._load_providers()
        out = []
        for target in ("calendar", "email"):
            sess = self._oauth_session_for(target)
            provider = providers.get(target, "")
            status = str(sess.get("status", "idle")) if isinstance(sess, dict) else "idle"
            message = str(sess.get("message", "")) if isinstance(sess, dict) else "no active connect session"
            title = f"{target.title()} provider"
            detail = f"{provider} ({status})"
            blob = f"{title} {detail} {message}"
            if self._search_match(blob, tokens):
                out.append(
                    {
                        "source": "providers",
                        "title": title,
                        "detail": f"{detail} - {message}",
                    }
                )
                if len(out) >= limit:
                    break
        return out

    def _universal_search(self, query, limit=24):
        tokens = self._search_tokens(query)
        if not tokens:
            return {
                "status": "ok",
                "query": "",
                "results": [],
                "scope": {"files": False, "settings": False, "apps": False, "providers": False},
            }
        max_items = max(1, min(int(limit), 50))
        files = self._search_files(tokens, limit=min(10, max_items))
        settings = self._search_settings(tokens, limit=min(8, max_items))
        apps = self._search_apps(tokens, limit=min(10, max_items))
        providers = self._search_provider_metadata(tokens, limit=min(8, max_items))
        merged = (files + settings + apps + providers)[:max_items]
        return {
            "status": "ok",
            "query": str(query).strip(),
            "results": merged,
            "scope": {
                "files": True,
                "settings": True,
                "apps": True,
                "providers": True,
            },
        }

    def _notifications(self, limit=6):
        path = self._audit_log_path()
        if not os.path.exists(path):
            return []

        recent = deque(maxlen=max(1, min(int(limit) * 8, 96)))
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    if isinstance(data, dict):
                        recent.append(data)
        except Exception:
            return []

        alerts = []
        for event in reversed(recent):
            msg = str(event.get("message", "") or event.get("action", "")).strip()
            if not msg:
                continue
            alerts.append(
                {
                    "title": self._notification_title(event),
                    "message": msg,
                    "ts": event.get("ts"),
                }
            )
            if len(alerts) >= limit:
                break
        return alerts

    def _get_system_stats(self):
        # Lightweight /proc based stats for Linux
        cpu_usage = 0
        mem_usage = 0
        try:
            # Memory
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
                total = int(lines[0].split()[1])
                available = int(lines[2].split()[1])
                mem_usage = round((1 - (available / total)) * 100)
            # CPU (very rough approximation)
            with open("/proc/loadavg", "r") as f:
                load = f.read().split()[0]
                cpu_usage = int(float(load) * 10) # scaled for 10 cores or just a proxy
                if cpu_usage > 100:
                    cpu_usage = 99
        except Exception:
            pass
        return {"cpu": cpu_usage, "mem": mem_usage}

    def _load_recent_task_events(self, limit=8):
        log_path = self._audit_log_path()
        if not os.path.exists(log_path):
            return []

        recent = deque(maxlen=max(1, min(int(limit), 30)))
        try:
            with open(log_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(obj, dict):
                        continue
                    if obj.get("type") != "action_outcome":
                        continue
                    action = str(obj.get("action", "")).strip()
                    if action not in ("package_install", "package_remove", "system_update"):
                        continue
                    status = str(obj.get("status", "")).strip().lower() or "unknown"
                    msg = str(obj.get("message", "")).strip() or "Task completed."
                    ts = obj.get("ts")
                    recent.append(
                        {
                            "ts": ts,
                            "action": action,
                            "status": status,
                            "message": msg,
                        }
                    )
        except Exception:
            return []

        out = list(recent)
        out.reverse()
        return out

    def _skills_dir(self):
        path = os.environ.get("AI_DISTRO_SKILLS_DIR", "src/skills/core")
        if os.path.isabs(path) and os.path.isdir(path):
            return path
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(here, "..", ".."))
        candidate = os.path.join(repo_root, path)
        if os.path.isdir(candidate):
            return candidate
        # fallback to packaged location
        packaged = os.path.join("/usr/lib/ai-distro/skills/core")
        if os.path.isdir(packaged):
            return packaged
        return candidate

    def _plugin_state_path(self):
        return os.environ.get("AI_DISTRO_PLUGIN_STATE", os.path.expanduser("~/.config/ai-distro/plugins.json"))

    def _load_plugin_state(self):
        path = self._plugin_state_path()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return {k: bool(v) for k, v in data.items()}
        except Exception:
            return {}
        return {}

    def _write_plugin_state(self, state):
        path = self._plugin_state_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2)
                fh.write("\n")
            return True, path
        except Exception as exc:
            return False, str(exc)

    def _plugin_enabled(self, name, state):
        return state.get(name, True)

    def _set_plugin_enabled(self, name, enabled):
        state = self._load_plugin_state()
        state[name] = bool(enabled)
        return self._write_plugin_state(state)

    def _load_skill_manifests(self):
        skills_dir = self._skills_dir()
        if not os.path.isdir(skills_dir):
            return []
        manifests = []
        for entry in sorted(Path(skills_dir).glob("*.json")):
            if not entry.is_file():
                continue
            data = self._load_json(str(entry))
            if not isinstance(data, dict):
                continue
            name = data.get("name")
            if not name:
                continue
            manifests.append(
                {
                    "name": name,
                    "display_name": data.get("display_name") or name,
                    "description": data.get("description", ""),
                    "category": data.get("category", "uncategorized"),
                    "handler": data.get("handler") or {},
                    "safety": data.get("safety") or {},
                    "examples": data.get("examples") or [],
                    "tags": data.get("tags") or [],
                    "parameters": data.get("parameters") or {},
                }
            )
        return manifests

    def _lite_mode_state_path(self):
        return os.environ.get(
            "AI_DISTRO_LIGHTWEIGHT_STATE",
            os.path.expanduser("~/.config/ai-distro/lite-mode.json"),
        )

    def _load_lite_mode_state(self):
        path = self._lite_mode_state_path()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh) if os.path.exists(path) else {}
                return bool(data.get("enabled"))
        except Exception:
            return False

    def _write_lite_mode_state(self, enabled):
        path = self._lite_mode_state_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"enabled": bool(enabled)}, fh, indent=2)
                fh.write("\n")
            return True, path
        except Exception as exc:
            return False, str(exc)
    def _provider_env(self, provider, payload):
        env = os.environ.copy()
        client_id = str(payload.get("client_id", "")).strip()
        client_secret = str(payload.get("client_secret", "")).strip()
        redirect_uri = str(payload.get("redirect_uri", "")).strip()
        state = str(payload.get("state", "")).strip()
        if provider in ("google", "gmail"):
            if client_id:
                env["AI_DISTRO_GOOGLE_CLIENT_ID"] = client_id
            if client_secret:
                env["AI_DISTRO_GOOGLE_CLIENT_SECRET"] = client_secret
            if redirect_uri:
                env["AI_DISTRO_GOOGLE_REDIRECT_URI"] = redirect_uri
        if provider in ("microsoft", "outlook"):
            if client_id:
                env["AI_DISTRO_MICROSOFT_CLIENT_ID"] = client_id
            if client_secret:
                env["AI_DISTRO_MICROSOFT_CLIENT_SECRET"] = client_secret
            if redirect_uri:
                env["AI_DISTRO_MICROSOFT_REDIRECT_URI"] = redirect_uri
        if state:
            env["AI_DISTRO_OAUTH_STATE"] = state
        return env

    def _oauth_start(self, target, provider, payload):
        state = uuid.uuid4().hex
        callback_uri = f"{self._server_base_url()}/oauth/callback"
        session = {
            "target": target,
            "provider": provider,
            "client_id": str(payload.get("client_id", "")).strip(),
            "client_secret": str(payload.get("client_secret", "")).strip(),
            "state": state,
            "redirect_uri": callback_uri,
            "status": "pending",
            "message": "",
            "code": "",
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
            "auth_url": "",
        }
        self.OAUTH_SESSIONS[state] = session
        run_payload = dict(payload)
        run_payload["redirect_uri"] = callback_uri
        run_payload["state"] = state
        env = self._provider_env(provider, run_payload)
        if target == "calendar" and provider == "google":
            tool = self._agent_tool_path("google_calendar_oauth.py")
            proc = subprocess.run(
                ["python3", tool, "auth-url"],
                text=True,
                capture_output=True,
                env=env,
                timeout=20,
            )
        elif target == "calendar" and provider == "microsoft":
            tool = self._agent_tool_path("microsoft_outlook_oauth.py")
            env["AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE"] = (
                "offline_access https://graph.microsoft.com/Calendars.ReadWrite"
            )
            proc = subprocess.run(
                ["python3", tool, "auth-url"],
                text=True,
                capture_output=True,
                env=env,
                timeout=20,
            )
        elif target == "email" and provider == "gmail":
            tool = self._agent_tool_path("google_gmail_oauth.py")
            proc = subprocess.run(
                ["python3", tool, "auth-url"],
                text=True,
                capture_output=True,
                env=env,
                timeout=20,
            )
        elif target == "email" and provider == "outlook":
            tool = self._agent_tool_path("microsoft_outlook_oauth.py")
            env["AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE"] = (
                "offline_access https://graph.microsoft.com/Mail.ReadWrite"
            )
            proc = subprocess.run(
                ["python3", tool, "auth-url"],
                text=True,
                capture_output=True,
                env=env,
                timeout=20,
            )
        else:
            return True, {"status": "ok", "message": "No OAuth needed for this provider."}

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0:
            session["status"] = "error"
            session["message"] = self._plain_error_message(
                err or out,
                "Couldn't start provider connection.",
            )
            session["updated_at"] = int(time.time())
            return False, {"status": "error", "message": session["message"]}
        url = self._extract_url(out)
        session["auth_url"] = url
        session["message"] = "Open the authorization page and approve access."
        session["updated_at"] = int(time.time())
        return True, {
            "status": "ok",
            "state": state,
            "auth_url": url,
            "message": "Authorization URL ready. Approve access and we’ll finish setup automatically.",
            "raw": out,
        }

    def _oauth_finish(self, target, provider, payload):
        code = str(payload.get("code", "")).strip()
        if not code:
            return False, {
                "status": "error",
                "message": "Authorization was not completed. Start Connect and approve access.",
            }
        env = self._provider_env(provider, payload)
        if target == "calendar" and provider == "google":
            tool = self._agent_tool_path("google_calendar_oauth.py")
            proc = subprocess.run(
                ["python3", tool, "exchange", code],
                text=True,
                capture_output=True,
                env=env,
                timeout=25,
            )
        elif target == "calendar" and provider == "microsoft":
            tool = self._agent_tool_path("microsoft_outlook_oauth.py")
            env["AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE"] = (
                "offline_access https://graph.microsoft.com/Calendars.ReadWrite"
            )
            proc = subprocess.run(
                ["python3", tool, "exchange", code],
                text=True,
                capture_output=True,
                env=env,
                timeout=25,
            )
        elif target == "email" and provider == "gmail":
            tool = self._agent_tool_path("google_gmail_oauth.py")
            proc = subprocess.run(
                ["python3", tool, "exchange", code],
                text=True,
                capture_output=True,
                env=env,
                timeout=25,
            )
        elif target == "email" and provider == "outlook":
            tool = self._agent_tool_path("microsoft_outlook_oauth.py")
            env["AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE"] = (
                "offline_access https://graph.microsoft.com/Mail.ReadWrite"
            )
            proc = subprocess.run(
                ["python3", tool, "exchange", code],
                text=True,
                capture_output=True,
                env=env,
                timeout=25,
            )
        else:
            return True, {"status": "ok", "message": "No OAuth needed for this provider."}

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0:
            return False, {
                "status": "error",
                "message": self._plain_error_message(
                    err or out,
                    "Could not finish sign-in. Please try Connect again.",
                ),
            }
        return True, {"status": "ok", "message": out or "Provider connected."}

    def _oauth_session_for(self, target):
        target = str(target or "").strip().lower()
        if target not in ("calendar", "email"):
            return None
        latest = None
        for sess in self.OAUTH_SESSIONS.values():
            if sess.get("target") != target:
                continue
            if latest is None or int(sess.get("updated_at", 0)) > int(latest.get("updated_at", 0)):
                latest = sess
        return latest

    def _oauth_handle_callback(self, parsed):
        qs = parse_qs(parsed.query or "")
        state = (qs.get("state") or [""])[0].strip()
        code = (qs.get("code") or [""])[0].strip()
        error = (qs.get("error") or [""])[0].strip()
        sess = self.OAUTH_SESSIONS.get(state) if state else None

        if not sess:
            return False, "Connection session was not found or expired."
        if error:
            sess["status"] = "error"
            sess["message"] = self._plain_error_message(
                f"authorization failed: {error}",
                "Authorization failed. Start Connect again.",
            )
            sess["updated_at"] = int(time.time())
            return False, sess["message"]
        if not code:
            sess["status"] = "error"
            sess["message"] = "Authorization did not return a valid code."
            sess["updated_at"] = int(time.time())
            return False, sess["message"]

        sess["code"] = code
        finish_payload = {
            "target": sess.get("target"),
            "provider": sess.get("provider"),
            "client_id": sess.get("client_id", ""),
            "client_secret": sess.get("client_secret", ""),
            "redirect_uri": sess.get("redirect_uri", ""),
            "code": code,
        }
        ok, body = self._oauth_finish(sess.get("target"), sess.get("provider"), finish_payload)
        sess["status"] = "connected" if ok else "error"
        sess["message"] = str(body.get("message", "Connected." if ok else "Connection failed."))
        sess["updated_at"] = int(time.time())
        return ok, sess["message"]

    def _provider_test(self, target, provider):
        env = os.environ.copy()
        provider = self._normalize_provider_value(target, provider)
        if target == "calendar":
            env["AI_DISTRO_CALENDAR_PROVIDER"] = provider
            tool = self._agent_tool_path("calendar_router.py")
            proc = subprocess.run(
                ["python3", tool, "list", "today"],
                text=True,
                capture_output=True,
                env=env,
                timeout=15,
            )
        elif target == "email":
            env["AI_DISTRO_EMAIL_PROVIDER"] = provider
            tool = self._agent_tool_path("email_router.py")
            proc = subprocess.run(
                ["python3", tool, "summary", "in:inbox newer_than:2d"],
                text=True,
                capture_output=True,
                env=env,
                timeout=15,
            )
        elif target == "weather":
            env["AI_DISTRO_WEATHER_PROVIDER"] = provider
            tool = self._agent_tool_path("weather_router.py")
            proc = subprocess.run(
                ["python3", tool, "today"],
                text=True,
                capture_output=True,
                env=env,
                timeout=15,
            )
        else:
            return {
                "ok": False,
                "message": "Unknown provider test target.",
                "provider_mode": "unknown",
                "status_label": "error",
            }
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        lower = (out or err).lower()
        prefix = "Calendar" if target == "calendar" else "Email" if target == "email" else "Weather"
        if "live provider unavailable" in lower and "fallback unavailable" in lower:
            return {
                "ok": False,
                "message": out or err or f"{prefix} live provider is unavailable and local fallback is unavailable.",
                "provider_mode": "unavailable",
                "status_label": "disconnected",
            }
        if "provider unavailable" in lower and "fallback unavailable" in lower:
            return {
                "ok": False,
                "message": out or err or f"{prefix} provider is unavailable and local fallback is unavailable.",
                "provider_mode": "unavailable",
                "status_label": "disconnected",
            }
        if "using local fallback" in lower:
            return {
                "ok": True,
                "message": out or err or f"{prefix} check passed using local fallback.",
                "provider_mode": "local_fallback",
                "status_label": "using local fallback",
            }
        if (
            "using local calendar provider" in lower
            or "using local email provider" in lower
            or "using local weather provider" in lower
        ):
            return {
                "ok": True,
                "message": out or err or f"{prefix} check passed with local provider.",
                "provider_mode": "local",
                "status_label": "ready",
            }
        if "connected live provider" in lower:
            return {
                "ok": True,
                "message": out or err or f"{prefix} live provider connected.",
                "provider_mode": "live",
                "status_label": "connected",
            }
        if proc.returncode != 0:
            return {
                "ok": False,
                "message": self._plain_error_message(err or out, "Provider test failed."),
                "provider_mode": "unknown",
                "status_label": "error",
            }
        return {
            "ok": True,
            "message": out or f"{prefix} provider test passed.",
            "provider_mode": "unknown",
            "status_label": "connected",
        }

    def translate_path(self, path):
        static_root = os.environ.get("AI_DISTRO_SHELL_STATIC_DIR", DEFAULT_STATIC)
        rel = path.lstrip("/")
        if not rel:
            rel = "index.html"
        return os.path.join(static_root, rel)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/oauth/callback":
            ok, message = self._oauth_handle_callback(parsed)
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            title = "Connected" if ok else "Connection Failed"
            body = (
                f"<h2>{title}</h2><p>{message}</p><p>You can close this tab and return to AI Distro Shell.</p>"
            )
            self.wfile.write(
                f"<!doctype html><html><body style='font-family:sans-serif;padding:24px'>{body}</body></html>".encode(
                    "utf-8"
                )
            )
            return
        if self.path.startswith("/api/"):
            if self.path == "/api/health":
                core = {"status": "unknown", "message": "core unavailable"}
                try:
                    core_resp = core_request({"name": "health"})
                    core = {
                        "status": core_resp.get("status", "unknown"),
                        "message": core_resp.get("message"),
                    }
                except Exception as exc:
                    core = {"status": "error", "message": self._plain_error_message(str(exc), "core unavailable")}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "persona": self._load_persona(), "core": core}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if parsed.path == "/api/core/status":
                try:
                    out = core_request({"name": "status"})
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok", "core": out}).encode("utf-8"))
                except Exception as exc:
                    self.send_response(502)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {
                                "status": "error",
                                "message": self._plain_error_message(
                                    str(exc),
                                    "Core service is temporarily unavailable.",
                                ),
                            }
                        ).encode("utf-8")
                    )
                return
            if parsed.path == "/api/core/recent-notes":
                qs = parse_qs(parsed.query or "")
                limit_raw = (qs.get("limit") or ["10"])[0]
                limit = int(limit_raw) if str(limit_raw).isdigit() else 10
                limit = max(1, min(limit, 200))
                try:
                    out = core_request({"name": "recent_notes", "payload": str(limit)})
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok", "core": out}).encode("utf-8"))
                except Exception as exc:
                    self.send_response(502)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {
                                "status": "error",
                                "message": self._plain_error_message(
                                    str(exc),
                                    "Could not read core notes right now.",
                                ),
                            }
                        ).encode("utf-8")
                    )
                return
            if self.path == "/api/persona":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "persona": self._load_persona()}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/persona-presets":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "presets": self._load_persona_presets()}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/onboarding":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "state": self._load_onboarding()}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/providers":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "providers": self._load_providers()}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if parsed.path == "/api/search":
                qs = parse_qs(parsed.query or "")
                query = (qs.get("q") or [""])[0]
                limit_raw = (qs.get("limit") or ["24"])[0]
                limit = int(limit_raw) if str(limit_raw).isdigit() else 24
                payload = self._universal_search(query, limit=limit)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/app-tasks":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "tasks": self._load_recent_task_events(limit=8)}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/proactive-events":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                events = list(self.PROACTIVE_QUEUE)
                self.PROACTIVE_QUEUE.clear()
                self.wfile.write(json.dumps({"status": "ok", "events": events}).encode("utf-8"))
                return
            if self.path == "/api/plugins":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                state = self._load_plugin_state()
                payload = {
                    "status": "ok",
                    "plugins": [
                        dict(manifest, enabled=self._plugin_enabled(manifest["name"], state))
                        for manifest in self._load_skill_manifests()
                    ],
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/plugins/enable" or self.path == "/api/plugins/disable":
                content_length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(content_length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    self.send_error(400, "invalid json")
                    return
                name = (payload.get("name") or "").strip()
                if not name:
                    self.send_error(400, "name is required")
                    return
                enable = self.path == "/api/plugins/enable"
                ok, detail = self._set_plugin_enabled(name, enable)
                if not ok:
                    self.send_response(500)
                else:
                    self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({
                        "status": "ok" if ok else "error",
                        "name": name,
                        "enabled": enable if ok else None,
                        "message": "" if ok else detail,
                        "detail": detail,
                    }).encode("utf-8")
                )
                return
            if self.path == "/api/context/tags":
                tags = self._tag_summaries()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "tags": tags}).encode("utf-8"))
                return
            if self.path == "/api/notifications":
                alerts = self._notifications()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "status": "ok",
                            "alerts": alerts,
                        }
                    ).encode("utf-8")
                )
                return
            if self.path == "/api/apps":
                apps = self._desktop_app_entries()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "apps": apps}).encode("utf-8"))
                return
            if self.path == "/api/system/stats":
                stats = self._get_system_stats()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(stats).encode("utf-8"))
                return
            if self.path == "/api/lite-mode":
                enabled = self._load_lite_mode_state()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "lite_mode": enabled}).encode("utf-8"))
                return
            if self.path == "/api/lite-mode/toggle":
                content_length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(content_length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    self.send_error(400, "invalid json")
                    return
                desired = payload.get("enabled")
                enabled = bool(desired) if isinstance(desired, bool) else not self._load_lite_mode_state()
                ok, detail = self._write_lite_mode_state(enabled)
                self.send_response(200 if ok else 500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "status": "ok" if ok else "error",
                            "lite_mode": enabled if ok else None,
                            "message": "lite mode enabled" if enabled and ok else "lite mode disabled" if ok else detail,
                            "detail": detail,
                        }
                    ).encode("utf-8")
                )
                return
            if parsed.path == "/api/provider/connect/status":
                target = (parse_qs(parsed.query or "").get("target") or [""])[0].strip().lower()
                sess = self._oauth_session_for(target)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if not sess:
                    self.wfile.write(json.dumps({"status": "idle", "target": target}).encode("utf-8"))
                    return
                payload = {
                    "status": str(sess.get("status", "pending")),
                    "target": str(sess.get("target", "")),
                    "provider": str(sess.get("provider", "")),
                    "message": str(sess.get("message", "")),
                    "auth_url": str(sess.get("auth_url", "")),
                    "updated_at": int(sess.get("updated_at", 0)),
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
        if self.path == "/api/calendar/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            tool = self._agent_tool_path("calendar_router.py")
            try:
                proc = subprocess.run([sys.executable, tool, "list", "today"], text=True, capture_output=True)
                out = proc.stdout.strip()
                lines = out.split("\n")
                events = []
                for line in lines:
                    line = line.strip()
                    if line.startswith("[calendar status]"):
                        continue
                    if "using" in line or "unavailable" in line or not line:
                        continue
                    if " - " in line:
                        time_part, title_part = line.split(" - ", 1)
                        events.append({"time": time_part.strip(), "title": title_part.strip()})
                self.wfile.write(json.dumps({"status": "ok", "events": events}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return
            
        if self.path == "/api/email/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            tool = self._agent_tool_path("email_router.py")
            try:
                proc = subprocess.run([sys.executable, tool, "summary", "in:inbox newer_than:2d"], text=True, capture_output=True)
                out = proc.stdout.strip()
                lines = out.split("\n")
                emails = []
                for line in lines:
                    line = line.strip()
                    if line.startswith("[email status]"):
                        continue
                    if "using" in line or "unavailable" in line or not line:
                        continue
                    # Match standard text output: From: ... | Subject: ...
                    if " | Subject: " in line:
                        try:
                            sender_part, subject_part = line.split(" | Subject: ", 1)
                            sender = sender_part.replace("From: ", "").strip()
                            subject = subject_part.strip()
                            emails.append({"sender": sender, "subject": subject})
                        except Exception:
                            pass
                self.wfile.write(json.dumps({"status": "ok", "emails": emails}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        self.send_error(404, "unknown api")
        return
    super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/provider/connect/start":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            target = str(payload.get("target", "")).strip().lower()
            provider = str(payload.get("provider", "")).strip().lower()
            if target not in ("calendar", "email"):
                self.send_error(400, "invalid target")
                return
            ok, body = self._oauth_start(target, provider, payload)
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode("utf-8"))
            return
        if parsed.path == "/api/core/remember-note":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            note = str(payload.get("note") or "").strip()
            if not note:
                self.send_error(400, "note is required")
                return
            try:
                out = core_request({"name": "remember_note", "payload": note})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "core": out}).encode("utf-8"))
            except Exception as exc:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "status": "error",
                            "message": self._plain_error_message(
                                str(exc),
                                "Could not save note in core service right now.",
                            ),
                        }
                    ).encode("utf-8")
                )
            return
        if parsed.path == "/api/provider/connect/finish":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            target = str(payload.get("target", "")).strip().lower()
            provider = str(payload.get("provider", "")).strip().lower()
            if target not in ("calendar", "email"):
                self.send_error(400, "invalid target")
                return
            ok, body = self._oauth_finish(target, provider, payload)
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode("utf-8"))
            return
        if parsed.path == "/api/provider/test":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            target = str(payload.get("target", "")).strip().lower()
            provider = str(payload.get("provider", "")).strip().lower()
            if target not in ("calendar", "email", "weather"):
                self.send_error(400, "invalid target")
                return
            result = self._provider_test(target, provider)
            ok = bool(result.get("ok"))
            message = str(result.get("message", "")).strip()
            code = 200 if ok else 500
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "status": "ok" if ok else "error",
                        "message": message,
                        "provider_mode": result.get("provider_mode", "unknown"),
                        "status_label": result.get("status_label", "error" if not ok else "connected"),
                    }
                ).encode("utf-8")
            )
            return
        if parsed.path == "/api/persona/set":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            preset = (payload.get("preset") or "").strip().lower()
            ok, detail = self._write_persona(preset)
            if not ok:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                msg = {"status": "error", "message": f"could not persist persona: {detail}"}
                self.wfile.write(json.dumps(msg).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            msg = {"status": "ok", "path": detail}
            self.wfile.write(json.dumps(msg).encode("utf-8"))
            return
        if parsed.path == "/api/context/clear-notes":
            ok, message = self._clear_memory_notes()
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"status": "ok" if ok else "error", "message": message}).encode(
                    "utf-8"
                )
            )
            return
        if parsed.path == "/api/context/forget-tasks":
            keep_lines = self.headers.get("X-Keep-Lines")
            keep_lines = int(keep_lines) if keep_lines and keep_lines.isdigit() else None
            ok, message = self._truncate_audit_log() if keep_lines is None else self._truncate_audit_log(
                keep_lines
            )
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"status": "ok" if ok else "error", "message": message}).encode(
                    "utf-8"
                )
            )
            return
        if parsed.path == "/api/onboarding":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            state = payload.get("state")
            if not isinstance(state, dict):
                self.send_error(400, "state must be object")
                return
            ok, detail = self._write_onboarding(state)
            if not ok:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                msg = {"status": "error", "message": f"could not persist onboarding: {detail}"}
                self.wfile.write(json.dumps(msg).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            msg = {"status": "ok", "path": detail}
            self.wfile.write(json.dumps(msg).encode("utf-8"))
            return
        if parsed.path == "/api/proactive-push":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
                message = payload.get("message", "")
                if message:
                    ShellHandler.PROACTIVE_QUEUE.append({"message": message, "ts": time.time()})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
            except Exception:
                self.send_error(400, "invalid push")
            return
        if parsed.path == "/api/providers":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            providers = payload.get("providers")
            if not isinstance(providers, dict):
                self.send_error(400, "providers must be object")
                return
            ok, detail = self._write_providers(providers)
            if not ok:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                msg = {"status": "error", "message": f"could not persist providers: {detail}"}
                self.wfile.write(json.dumps(msg).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            msg = {"status": "ok", "path": detail, "providers": self._load_providers()}
            self.wfile.write(json.dumps(msg).encode("utf-8"))
            return
        if parsed.path != "/api/command":
            self.send_error(404, "unknown api")
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "invalid json")
            return
        name = (payload.get("name") or "").strip()
        if name:
            request = {
                "version": 1,
                "name": name,
                "payload": payload.get("payload"),
            }
        else:
            text = (payload.get("text") or "").strip()
            if not text:
                self.send_error(400, "missing text")
                return
            request = {"version": 1, "name": "natural_language", "payload": text}
        try:
            response = agent_request(request)
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            msg = {
                "status": "error",
                "message": self._plain_error_message(
                    f"agent unavailable: {exc}",
                    "The assistant service is temporarily unavailable. Please try again in a few seconds.",
                ),
            }
            self.wfile.write(json.dumps(msg).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))


def run():
    host = os.environ.get("AI_DISTRO_SHELL_HOST", "127.0.0.1")
    port = int(os.environ.get("AI_DISTRO_SHELL_PORT", "17842"))
    server = HTTPServer((host, port), ShellHandler)
    print(f"ai-distro-shell listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
