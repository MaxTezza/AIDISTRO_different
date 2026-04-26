#!/usr/bin/env python3
"""
AI Distro — Skill SDK & Scaffolding

CLI tool and library for creating, validating, packaging, and testing
AI Distro skills. Generates boilerplate skill directories with proper
manifests, handler stubs, tests, and documentation.

Usage:
  python3 skill_sdk.py new my_skill                # Scaffold a new skill
  python3 skill_sdk.py new my_skill --template api  # Use a template
  python3 skill_sdk.py validate /path/to/skill      # Validate skill structure
  python3 skill_sdk.py test /path/to/skill          # Run skill tests
  python3 skill_sdk.py package /path/to/skill       # Package for distribution
  python3 skill_sdk.py docs /path/to/skill          # Generate documentation
  python3 skill_sdk.py lint /path/to/skill          # Lint skill code
  python3 skill_sdk.py templates                    # List available templates
"""
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import io
from datetime import datetime
from pathlib import Path

SKILLS_DIR = Path(os.path.expanduser("~/.config/ai-distro/skills"))
SKILL_VERSION = "1.0"

# ═══════════════════════════════════════════════════════════════════
# Templates
# ═══════════════════════════════════════════════════════════════════

TEMPLATES = {
    "basic": {
        "description": "Simple skill with intent handler and response",
        "files": {
            "handler.py": '''#!/usr/bin/env python3
"""
{skill_name} — Skill Handler

This is the main handler for the {skill_name} skill.
"""
import json
import sys


def handle(intent, payload=None, context=None):
    """
    Handle an intent invocation.

    Args:
        intent: The matched intent name
        payload: Raw text or structured data from the user
        context: Desktop context (active window, clipboard, etc.)

    Returns:
        dict with at minimum {{"response": str}} or {{"action": str, "data": ...}}
    """
    return {{
        "response": f"Hello from {skill_name}! You said: {{payload}}",
        "status": "ok",
    }}


def main():
    """CLI entry point for testing."""
    payload = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "test"
    result = handle("{skill_name}", payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
''',
        },
    },
    "api": {
        "description": "Skill that integrates with an external API",
        "files": {
            "handler.py": '''#!/usr/bin/env python3
"""
{skill_name} — API Integration Skill
"""
import json
import os
import sys
import urllib.request
import urllib.error


API_BASE = os.environ.get("{SKILL_NAME_UPPER}_API_URL", "https://api.example.com")
API_KEY = os.environ.get("{SKILL_NAME_UPPER}_API_KEY", "")


def _api_request(endpoint, method="GET", data=None):
    """Make an API request."""
    url = f"{{API_BASE}}/{{endpoint}}"
    headers = {{"Content-Type": "application/json"}}
    if API_KEY:
        headers["Authorization"] = f"Bearer {{API_KEY}}"

    req = urllib.request.Request(url, headers=headers, method=method)
    if data:
        req.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        return {{"error": str(e)}}


def handle(intent, payload=None, context=None):
    """Handle an intent invocation."""
    result = _api_request("endpoint", data={{"query": payload}})
    return {{
        "response": json.dumps(result, indent=2),
        "status": "ok" if "error" not in result else "error",
    }}


def main():
    payload = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "test"
    result = handle("{skill_name}", payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
''',
            "config.json": '''{{"api_base": "https://api.example.com", "requires_key": true}}''',
        },
    },
    "daemon": {
        "description": "Long-running background service skill",
        "files": {
            "handler.py": '''#!/usr/bin/env python3
"""
{skill_name} — Background Daemon Skill
"""
import json
import os
import sys
import time
import signal
import threading


class {skill_class}Daemon:
    """Background service for {skill_name}."""

    def __init__(self):
        self.running = False
        self.interval = 60  # seconds

    def start(self):
        """Start the daemon loop."""
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        signal.signal(signal.SIGINT, lambda s, f: self.stop())

        print(f"{{type(self).__name__}} started (interval: {{self.interval}}s)")
        while self.running:
            try:
                self.tick()
            except Exception as e:
                print(f"Tick error: {{e}}")
            time.sleep(self.interval)

    def stop(self):
        """Stop the daemon."""
        self.running = False
        print("Daemon stopping...")

    def tick(self):
        """Override this with your periodic logic."""
        pass


def handle(intent, payload=None, context=None):
    """Handle an intent invocation."""
    if payload == "start":
        daemon = {skill_class}Daemon()
        daemon.start()
        return {{"response": "Daemon started", "status": "ok"}}
    return {{"response": "Use 'start' to launch the daemon", "status": "ok"}}


def main():
    payload = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "start"
    result = handle("{skill_name}", payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
''',
        },
    },
}


def _to_class_name(snake):
    """Convert snake_case to PascalCase."""
    return "".join(word.title() for word in snake.split("_"))


def _generate_manifest(skill_name, template="basic"):
    """Generate a skill manifest."""
    return {
        "name": skill_name,
        "version": "0.1.0",
        "sdk_version": SKILL_VERSION,
        "description": f"AI Distro skill: {skill_name.replace('_', ' ').title()}",
        "author": os.environ.get("USER", "unknown"),
        "created": datetime.now().isoformat(),
        "entry": "handler.py",
        "intents": [skill_name],
        "triggers": [skill_name.replace("_", " ")],
        "permissions": "minimal",
        "template": template,
        "dependencies": [],
    }


def _generate_readme(skill_name):
    """Generate skill README."""
    title = skill_name.replace("_", " ").title()
    return f"""# {title}

AI Distro skill.

## Usage

This skill responds to the intent `{skill_name}`.

### Voice
> "Hey distro, {skill_name.replace('_', ' ')}"

### CLI
```bash
python3 handler.py "your input here"
```

## Configuration

Edit `manifest.json` to customize triggers, permissions, and dependencies.

## Development

```bash
# Validate structure
python3 ../../tools/agent/skill_sdk.py validate .

# Run tests
python3 ../../tools/agent/skill_sdk.py test .

# Package for distribution
python3 ../../tools/agent/skill_sdk.py package .
```
"""


def _generate_test(skill_name):
    """Generate a basic test file."""
    return f'''#!/usr/bin/env python3
"""Tests for {skill_name} skill."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from handler import handle


def test_basic_response():
    result = handle("{skill_name}", "hello world")
    assert "response" in result, "Handler must return a response"
    assert result.get("status") == "ok", f"Expected ok, got {{result.get('status')}}"
    print("  ✓ basic_response")


def test_empty_payload():
    result = handle("{skill_name}", "")
    assert "response" in result, "Handler must handle empty payload"
    print("  ✓ empty_payload")


def test_none_payload():
    result = handle("{skill_name}", None)
    assert "response" in result, "Handler must handle None payload"
    print("  ✓ none_payload")


if __name__ == "__main__":
    print(f"Testing {skill_name}...")
    test_basic_response()
    test_empty_payload()
    test_none_payload()
    print("  All tests passed!")
'''


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def new_skill(skill_name, template="basic"):
    """Scaffold a new skill."""
    if template not in TEMPLATES:
        return {"error": f"Unknown template: {template}", "available": list(TEMPLATES.keys())}

    skill_dir = SKILLS_DIR / skill_name
    if skill_dir.exists():
        return {"error": f"Skill already exists: {skill_dir}"}

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_class = _to_class_name(skill_name)
    created = []

    # Write manifest
    manifest = _generate_manifest(skill_name, template)
    (skill_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    created.append("manifest.json")

    # Write template files
    tmpl = TEMPLATES[template]
    for filename, content in tmpl["files"].items():
        rendered = content.format(
            skill_name=skill_name,
            skill_class=skill_class,
            SKILL_NAME_UPPER=skill_name.upper(),
        )
        (skill_dir / filename).write_text(rendered)
        created.append(filename)

    # Write README
    (skill_dir / "README.md").write_text(_generate_readme(skill_name))
    created.append("README.md")

    # Write test
    (skill_dir / "test_skill.py").write_text(_generate_test(skill_name))
    created.append("test_skill.py")

    return {
        "status": "ok",
        "path": str(skill_dir),
        "template": template,
        "files": created,
    }


def validate_skill(skill_path):
    """Validate skill structure and manifest."""
    skill_dir = Path(skill_path)
    issues = []
    warnings = []

    # Required files
    if not (skill_dir / "manifest.json").exists():
        issues.append("Missing manifest.json")
    else:
        try:
            with open(skill_dir / "manifest.json") as f:
                manifest = json.load(f)

            required_fields = ["name", "version", "entry", "intents", "permissions"]
            for field in required_fields:
                if field not in manifest:
                    issues.append(f"Manifest missing field: {field}")

            entry = manifest.get("entry", "handler.py")
            if not (skill_dir / entry).exists():
                issues.append(f"Entry point not found: {entry}")

            valid_perms = ["minimal", "network", "filesystem", "full"]
            if manifest.get("permissions") not in valid_perms:
                warnings.append(f"Unusual permissions: {manifest.get('permissions')}")

        except json.JSONDecodeError:
            issues.append("manifest.json is not valid JSON")

    if not (skill_dir / "README.md").exists():
        warnings.append("Missing README.md")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "path": str(skill_dir),
    }


def test_skill(skill_path):
    """Run skill tests."""
    skill_dir = Path(skill_path)
    test_file = skill_dir / "test_skill.py"

    if not test_file.exists():
        return {"error": "No test_skill.py found"}

    try:
        r = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True, text=True, timeout=30,
            cwd=str(skill_dir)
        )
        return {
            "status": "passed" if r.returncode == 0 else "failed",
            "output": r.stdout,
            "errors": r.stderr if r.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "Tests timed out after 30s"}


def package_skill(skill_path):
    """Package a skill for distribution."""
    skill_dir = Path(skill_path)
    validation = validate_skill(skill_path)
    if not validation["valid"]:
        return {"error": "Skill validation failed", "issues": validation["issues"]}

    with open(skill_dir / "manifest.json") as f:
        manifest = json.load(f)

    name = manifest["name"]
    version = manifest["version"]
    archive_name = f"{name}-{version}.tar.gz"
    archive_path = skill_dir.parent / archive_name

    # Create tarball
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for item in skill_dir.rglob("*"):
            if item.is_file() and "__pycache__" not in str(item):
                arcname = f"{name}/{item.relative_to(skill_dir)}"
                tar.add(str(item), arcname=arcname)

    data = buf.getvalue()
    archive_path.write_bytes(data)

    # Compute hash
    sha256 = hashlib.sha256(data).hexdigest()

    return {
        "status": "ok",
        "archive": str(archive_path),
        "size_kb": round(len(data) / 1024, 1),
        "sha256": sha256,
    }


def lint_skill(skill_path):
    """Lint skill Python files."""
    skill_dir = Path(skill_path)
    py_files = list(skill_dir.glob("*.py"))

    if not py_files:
        return {"status": "ok", "message": "No Python files to lint"}

    try:
        r = subprocess.run(
            ["ruff", "check"] + [str(f) for f in py_files],
            capture_output=True, text=True, timeout=30
        )
        return {
            "status": "clean" if r.returncode == 0 else "issues",
            "output": r.stdout or "All checks passed!",
        }
    except FileNotFoundError:
        return {"status": "skipped", "message": "ruff not installed"}


def list_templates():
    """List available templates."""
    return [{
        "name": name,
        "description": tmpl["description"],
        "files": list(tmpl["files"].keys()),
    } for name, tmpl in TEMPLATES.items()]


def main():
    if len(sys.argv) < 2:
        print("Usage: skill_sdk.py <new|validate|test|package|lint|docs|templates>")
        return

    cmd = sys.argv[1]

    if cmd == "new":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        if not name:
            print("Usage: skill_sdk.py new <skill_name> [--template basic|api|daemon]")
            return
        template = "basic"
        if "--template" in sys.argv:
            idx = sys.argv.index("--template")
            template = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "basic"
        print(json.dumps(new_skill(name, template), indent=2))

    elif cmd == "validate":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        result = validate_skill(path)
        print(json.dumps(result, indent=2))
        if not result["valid"]:
            sys.exit(1)

    elif cmd == "test":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        print(json.dumps(test_skill(path), indent=2))

    elif cmd == "package":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        print(json.dumps(package_skill(path), indent=2))

    elif cmd == "lint":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        print(json.dumps(lint_skill(path), indent=2))

    elif cmd == "templates":
        for t in list_templates():
            print(f"  {t['name']:12s} — {t['description']}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
