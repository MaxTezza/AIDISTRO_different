#!/usr/bin/env python3
"""
AI Distro — Context-Aware Intent Router

Enriches intent parsing with the user's current desktop context: active
window, open applications, clipboard contents, and screen region. When the
user says "run this" or "save that," the router knows what "this" and "that"
refer to by inspecting the live desktop state.

Architecture:
  1. Capture active window (title, app, PID) via wmctrl/swaymsg
  2. Capture clipboard contents via wl-paste/xclip
  3. Map context + utterance to the best matching skill
  4. Inject resolved context into the skill invocation

Usage (library):
  from context_router import ContextRouter
  router = ContextRouter()
  result = router.route("run this")
  # → {"skill": "software_forge_script", "context": {"file": "main.py", ...}}

Usage (CLI):
  python3 context_router.py route "run this"
  python3 context_router.py context            # Show current desktop context
  python3 context_router.py resolve "save that" # Show how an utterance resolves
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))

# App class → skill mapping
APP_SKILL_MAP = {
    # Code editors
    "code": "software_forge_script",
    "vscodium": "software_forge_script",
    "vim": "software_forge_script",
    "nvim": "software_forge_script",
    "emacs": "software_forge_script",
    "gedit": "software_forge_script",
    "kate": "software_forge_script",
    "sublime": "software_forge_script",
    # Terminals
    "foot": "autonomous_script",
    "alacritty": "autonomous_script",
    "kitty": "autonomous_script",
    "xterm": "autonomous_script",
    "gnome-terminal": "autonomous_script",
    # Browsers
    "firefox": "web_agent",
    "chromium": "web_agent",
    "chrome": "web_agent",
    "brave": "web_agent",
    "qutebrowser": "web_agent",
    # File managers
    "thunar": "semantic_launcher",
    "nautilus": "semantic_launcher",
    "dolphin": "semantic_launcher",
    "pcmanfm": "semantic_launcher",
    # Media
    "mpv": "grandma_multimedia",
    "vlc": "grandma_multimedia",
    "spotify": "grandma_multimedia",
    "rhythmbox": "grandma_multimedia",
    # Mail
    "thunderbird": "grandma_comm_news",
    "evolution": "grandma_comm_news",
    "geary": "grandma_comm_news",
}

# Context-dependent pronoun resolution
DEICTIC_PATTERNS = {
    r"\b(?:run|execute|start)\s+(?:this|it)\b": "run_current",
    r"\b(?:save|export)\s+(?:this|it|that)\b": "save_current",
    r"\b(?:close|kill|quit)\s+(?:this|it|that)\b": "close_current",
    r"\b(?:copy|duplicate)\s+(?:this|that)\b": "copy_current",
    r"\b(?:open|show)\s+(?:this|that|it)\b": "open_current",
    r"\b(?:search|find|look up)\s+(?:this|that)\b": "search_clipboard",
    r"\b(?:explain|what is|tell me about)\s+(?:this|that)\b": "explain_context",
    r"\b(?:fix|debug|help with)\s+(?:this|that)\b": "fix_current",
    r"\b(?:send|share|email)\s+(?:this|that)\b": "share_current",
    r"\b(?:translate)\s+(?:this|that)\b": "translate_clipboard",
}


class ContextRouter:
    """Enriches user utterances with live desktop context for intent routing."""

    def __init__(self):
        self._sway = self._detect_sway()

    def _detect_sway(self):
        """Check if we're running under Sway."""
        return os.environ.get("SWAYSOCK") is not None or os.environ.get("WAYLAND_DISPLAY") is not None

    def _run(self, cmd, timeout=3):
        """Run a command and return stdout, or empty string on failure."""
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""

    # ── Desktop Context Capture ─────────────────────────────────

    def get_active_window(self):
        """Get info about the currently focused window."""
        if self._sway:
            return self._get_sway_window()
        return self._get_x11_window()

    def _get_sway_window(self):
        """Get focused window via swaymsg."""
        out = self._run(["swaymsg", "-t", "get_tree"])
        if not out:
            return {"app": "unknown", "title": "", "pid": None}
        try:
            tree = json.loads(out)
            focused = self._find_focused(tree)
            if focused:
                return {
                    "app": focused.get("app_id", "") or focused.get("window_properties", {}).get("class", "unknown"),
                    "title": focused.get("name", ""),
                    "pid": focused.get("pid"),
                    "geometry": focused.get("rect", {}),
                }
        except json.JSONDecodeError:
            pass
        return {"app": "unknown", "title": "", "pid": None}

    def _find_focused(self, node):
        """Recursively find the focused node in sway tree."""
        if node.get("focused"):
            return node
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            found = self._find_focused(child)
            if found:
                return found
        return None

    def _get_x11_window(self):
        """Get focused window via xdotool/wmctrl."""
        wid = self._run(["xdotool", "getactivewindow"])
        if not wid:
            return {"app": "unknown", "title": "", "pid": None}

        name = self._run(["xdotool", "getactivewindow", "getwindowname"])
        pid_str = self._run(["xdotool", "getactivewindow", "getwindowpid"])
        wm_class = self._run(["xdotool", "getactivewindow", "getwindowclassname"])

        return {
            "app": wm_class.lower() if wm_class else "unknown",
            "title": name,
            "pid": int(pid_str) if pid_str.isdigit() else None,
        }

    def get_clipboard(self):
        """Get current clipboard contents."""
        if self._sway:
            text = self._run(["wl-paste", "--no-newline"])
        else:
            text = self._run(["xclip", "-selection", "clipboard", "-o"])
        return text[:500] if text else ""

    def get_open_apps(self):
        """List all open application windows."""
        if self._sway:
            out = self._run(["swaymsg", "-t", "get_tree"])
            if not out:
                return []
            try:
                tree = json.loads(out)
                apps = []
                self._collect_apps(tree, apps)
                return apps
            except json.JSONDecodeError:
                return []
        else:
            out = self._run(["wmctrl", "-l"])
            return [line.split(None, 3)[-1] for line in out.split("\n") if line] if out else []

    def _collect_apps(self, node, apps):
        """Collect all app windows from sway tree."""
        if node.get("app_id") or node.get("window_properties", {}).get("class"):
            apps.append({
                "app": node.get("app_id", "") or node.get("window_properties", {}).get("class", ""),
                "title": node.get("name", ""),
                "focused": node.get("focused", False),
            })
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            self._collect_apps(child, apps)

    def get_context(self):
        """Capture the full desktop context."""
        window = self.get_active_window()
        clipboard = self.get_clipboard()

        # Infer file context from window title
        file_context = self._infer_file_from_title(window.get("title", ""))

        return {
            "active_window": window,
            "clipboard": clipboard,
            "file": file_context,
            "open_apps": self.get_open_apps(),
        }

    def _infer_file_from_title(self, title):
        """Try to extract a file path/name from the window title."""
        if not title:
            return None

        # Common patterns: "filename.ext — Editor" or "/path/to/file"
        # VSCode: "filename.py — FolderName — Visual Studio Code"
        # Vim: "filename.py (~/.config/) - VIM"
        patterns = [
            r"^(.+?\.\w{1,6})\s*[—–\-]",  # "file.ext — Editor"
            r"(/[\w/\-\.]+\.\w{1,6})",  # "/path/to/file.ext"
            r"^(.+?\.\w{1,6})\s*\(",  # "file.ext (~/dir)"
        ]
        for pat in patterns:
            m = re.search(pat, title)
            if m:
                return m.group(1).strip()
        return None

    # ── Intent Routing ──────────────────────────────────────────

    def resolve_deictic(self, utterance):
        """Resolve pronouns like 'this' and 'that' using context."""
        text = utterance.lower()
        for pattern, intent in DEICTIC_PATTERNS.items():
            if re.search(pattern, text):
                return intent
        return None

    def route(self, utterance):
        """Route an utterance using desktop context."""
        context = self.get_context()
        deictic = self.resolve_deictic(utterance)

        active_app = context["active_window"].get("app", "").lower()
        active_title = context["active_window"].get("title", "")
        clipboard = context.get("clipboard", "")
        file_ctx = context.get("file")

        result = {
            "utterance": utterance,
            "context": context,
            "resolved_intent": deictic,
            "suggested_skill": None,
            "enrichment": {},
        }

        # App-based skill suggestion
        for app_key, skill in APP_SKILL_MAP.items():
            if app_key in active_app:
                result["suggested_skill"] = skill
                break

        # Deictic resolution
        if deictic:
            if deictic == "run_current" and file_ctx:
                result["suggested_skill"] = "software_forge_script"
                result["enrichment"]["file"] = file_ctx
                result["enrichment"]["action"] = "execute"

            elif deictic == "save_current" and file_ctx:
                result["enrichment"]["file"] = file_ctx
                result["enrichment"]["action"] = "save"

            elif deictic == "close_current":
                result["suggested_skill"] = "workspace_orchestrator"
                result["enrichment"]["pid"] = context["active_window"].get("pid")
                result["enrichment"]["action"] = "close"

            elif deictic == "search_clipboard" and clipboard:
                result["suggested_skill"] = "web_research"
                result["enrichment"]["query"] = clipboard

            elif deictic == "explain_context":
                if clipboard:
                    result["enrichment"]["subject"] = clipboard
                elif file_ctx:
                    result["enrichment"]["subject"] = file_ctx
                elif active_title:
                    result["enrichment"]["subject"] = active_title

            elif deictic == "fix_current" and file_ctx:
                result["suggested_skill"] = "software_forge_script"
                result["enrichment"]["file"] = file_ctx
                result["enrichment"]["action"] = "debug"

            elif deictic == "share_current":
                if clipboard:
                    result["enrichment"]["content"] = clipboard
                elif file_ctx:
                    result["enrichment"]["file"] = file_ctx

            elif deictic == "translate_clipboard" and clipboard:
                result["enrichment"]["text"] = clipboard
                result["enrichment"]["action"] = "translate"

        return result


def main():
    router = ContextRouter()

    if len(sys.argv) < 2:
        print("Usage: context_router.py <context|route|resolve> [utterance]")
        return

    cmd = sys.argv[1]

    if cmd == "context":
        print(json.dumps(router.get_context(), indent=2, default=str))

    elif cmd == "route":
        utterance = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not utterance:
            print("Usage: context_router.py route <utterance>")
            return
        print(json.dumps(router.route(utterance), indent=2, default=str))

    elif cmd == "resolve":
        utterance = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        intent = router.resolve_deictic(utterance)
        ctx = router.get_context()
        print(json.dumps({
            "utterance": utterance,
            "resolved_intent": intent,
            "active_app": ctx["active_window"].get("app"),
            "active_file": ctx.get("file"),
            "clipboard_preview": ctx.get("clipboard", "")[:100],
        }, indent=2))

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
