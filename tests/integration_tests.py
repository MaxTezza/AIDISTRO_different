#!/usr/bin/env python3
"""
AI Distro — End-to-End Integration Test Suite

Tests the full pipeline from intent → agent → action → response.
Covers: IPC connectivity, tool dispatch, voice pipeline, vision service,
Bayesian engine, event bus, and system healer.

Usage:
  python3 integration_tests.py           # Run all tests
  python3 integration_tests.py --quick   # Skip slow tests (model loading)
  python3 integration_tests.py --json    # Output results as JSON
"""
import json
import os
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

AGENT_SOCKET = os.environ.get("AI_DISTRO_IPC_SOCKET", "/run/ai-distro/agent.sock")
EVENT_SOCKET = "/tmp/ai-distro-events.sock"
VISION_URL = "http://127.0.0.1:7860"
DASHBOARD_URL = "http://127.0.0.1:7841"
TOOLS_DIR = Path(__file__).parent.parent / "tools" / "agent"
ROOT_DIR = Path(__file__).parent.parent

results = []


def test(name, *, slow=False):
    """Decorator factory: register a test function with a name."""
    def decorator(func):
        def wrapper(quick_mode=False):
            if slow and quick_mode:
                results.append({"name": name, "status": "skipped", "reason": "slow"})
                return
            try:
                msg = func()
                results.append({"name": name, "status": "pass", "message": msg or ""})
            except AssertionError as e:
                results.append({"name": name, "status": "fail", "message": str(e)})
            except Exception as e:
                results.append({"name": name, "status": "error", "message": str(e)})
        wrapper._name = name
        wrapper._slow = slow
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════
# Test Definitions
# ═══════════════════════════════════════════════════════════════════

@test("Source tree integrity")
def test_source_tree():
    """Verify all critical files exist."""
    critical_files = [
        "tools/agent/brain.py",
        "tools/agent/curator.py",
        "tools/agent/system_healer.py",
        "tools/agent/vision_brain.py",
        "tools/agent/spirit_bridge.py",
        "tools/agent/hardware_events.py",
        "tools/agent/bayesian_engine.py",
        "tools/agent/atspi_hands.py",
        "tools/agent/wake_word_engine.py",
        "tools/agent/event_bus.py",
        "tools/agent/dashboard.py",
        "tools/agent/setup_wizard.py",
        "tools/agent/day_planner.py",
        "src/skills/core/autonomous_script.json",
        "configs/agent.json",
        "install.sh",
        "tools/release/build_iso.sh",
    ]
    missing = []
    for f in critical_files:
        if not (ROOT_DIR / f).exists():
            missing.append(f)
    assert not missing, f"Missing files: {', '.join(missing)}"
    return f"All {len(critical_files)} critical files present"


@test("Rust binaries compile")
def test_rust_compile():
    """Verify Rust workspace compiles cleanly."""
    result = subprocess.run(
        ["cargo", "check", "--all", "--manifest-path",
         str(ROOT_DIR / "src/rust/Cargo.toml")],
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, f"Cargo check failed:\n{result.stderr[-500:]}"
    return "All Rust crates compile"


@test("Python lint clean")
def test_python_lint():
    """Verify Python code passes linting."""
    result = subprocess.run(
        ["ruff", "check", str(ROOT_DIR)],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"Lint errors:\n{result.stdout[-500:]}"
    return "All Python files pass ruff"


@test("Shell scripts parse")
def test_shell_scripts():
    """Verify all shell scripts have valid syntax."""
    scripts = list(ROOT_DIR.glob("**/*.sh"))
    errors = []
    for script in scripts:
        r = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            errors.append(f"{script.name}: {r.stderr.strip()}")
    assert not errors, f"Syntax errors: {'; '.join(errors)}"
    return f"All {len(scripts)} shell scripts parse cleanly"


@test("Bayesian engine")
def test_bayesian():
    """Test the Bayesian preference engine."""
    sys.path.insert(0, str(TOOLS_DIR))
    from bayesian_engine import BayesianEngine

    engine = BayesianEngine()

    # Observe some events
    engine.observe("open_browser", "positive")
    engine.observe("open_browser", "positive")
    engine.observe("open_terminal", "positive")

    # Predict
    predictions = engine.predict(top_k=3)
    assert isinstance(predictions, list), "Predictions should be a list"

    # Profile
    profile = engine.get_user_profile()
    assert isinstance(profile, dict), "Profile should be a dict"

    return f"Engine works: {len(predictions)} predictions generated"


@test("Skill manifests valid")
def test_skills():
    """Verify all skill JSON manifests are parseable."""
    skills_dirs = [
        ROOT_DIR / "src/skills/core",
        ROOT_DIR / "src/skills/dynamic"
    ]
    count = 0
    errors = []
    for d in skills_dirs:
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                assert "name" in data, f"{f.name}: missing 'name'"
                count += 1
            except Exception as e:
                errors.append(f"{f.name}: {e}")
    assert not errors, f"Invalid skills: {'; '.join(errors)}"
    return f"{count} skill manifests valid"


@test("Agent IPC socket")
def test_agent_ipc():
    """Test if the agent is listening on the IPC socket."""
    if not os.path.exists(AGENT_SOCKET):
        raise AssertionError(
            f"Agent socket not found: {AGENT_SOCKET}. "
            "Is the agent running?"
        )

    # Try connecting
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(3.0)
        s.connect(AGENT_SOCKET)
        # Send a health check
        request = {"version": 1, "name": "health_check", "payload": ""}
        s.sendall(json.dumps(request).encode("utf-8") + b"\n")
    return "Agent socket reachable"


@test("Vision service health", slow=True)
def test_vision_health():
    """Check if the vision microservice is responding."""
    try:
        req = urllib.request.Request(f"{VISION_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        assert data.get("status") == "ok", f"Unexpected status: {data}"
        return f"Vision OK — model_loaded={data.get('model_loaded')}"
    except Exception as e:
        raise AssertionError(f"Vision service unreachable: {e}")


@test("Dashboard health")
def test_dashboard():
    """Check if the dashboard is responding."""
    try:
        req = urllib.request.Request(f"{DASHBOARD_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        assert data.get("status") == "ok", f"Unexpected: {data}"
        return "Dashboard responding"
    except Exception as e:
        raise AssertionError(f"Dashboard unreachable: {e}")


@test("Event bus")
def test_event_bus():
    """Test event bus connectivity."""
    if not os.path.exists(EVENT_SOCKET):
        raise AssertionError("Event bus socket not found. Is it running?")

    # Publish a test event
    event = {
        "type": "info",
        "source": "integration_test",
        "title": "Test Event",
        "message": "Integration test ping"
    }
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(3.0)
        s.connect(EVENT_SOCKET)
        s.sendall(json.dumps(event).encode("utf-8") + b"\n")
    return "Event published successfully"


@test("TTS pipeline")
def test_tts():
    """Verify Piper TTS binary and model exist."""
    piper_dir = Path(os.path.expanduser("~/.cache/ai-distro/piper"))
    piper_bin = piper_dir / "piper" / "piper"
    piper_model = piper_dir / "en_US-amy-medium.onnx"

    if not piper_bin.exists():
        raise AssertionError(
            "Piper binary not found. Run setup_wizard.py to install."
        )
    if not piper_model.exists():
        raise AssertionError(
            "Piper voice model not found. Run setup_wizard.py to install."
        )

    # Test that Piper runs (dry run)
    result = subprocess.run(
        [str(piper_bin), "--help"],
        capture_output=True, timeout=5
    )
    assert result.returncode in (0, 1), "Piper binary not executable"
    return "Piper TTS binary + Amy model present"


@test("Config files")
def test_configs():
    """Verify configuration files are valid JSON."""
    config_files = [
        ROOT_DIR / "configs/agent.json",
    ]
    # User-level configs (optional)
    user_configs = [
        Path(os.path.expanduser("~/.config/ai-distro-user.json")),
        Path(os.path.expanduser("~/.config/ai-distro-spirit.json")),
    ]

    for f in config_files:
        try:
            with open(f) as fh:
                json.load(fh)
        except FileNotFoundError:
            raise AssertionError(f"Config missing: {f.name}")
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON in {f.name}: {e}")

    user_found = 0
    for f in user_configs:
        if f.exists():
            try:
                with open(f) as fh:
                    json.load(fh)
                user_found += 1
            except json.JSONDecodeError as e:
                raise AssertionError(f"Invalid JSON in {f.name}: {e}")

    return f"Core configs valid, {user_found} user configs found"


@test("ISO build script")
def test_iso_script():
    """Verify the ISO build script has valid syntax."""
    script = ROOT_DIR / "tools/release/build_iso.sh"
    result = subprocess.run(
        ["bash", "-n", str(script)],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"build_iso.sh syntax error: {result.stderr}"
    return "ISO build script syntax valid"


@test("Branding assets")
def test_branding():
    """Verify branding assets exist."""
    assets = ROOT_DIR / "assets/branding"
    assert assets.is_dir(), "assets/branding/ directory missing"
    splash = assets / "grub-splash.png"
    wallpaper = assets / "wallpaper.png"
    assert splash.exists(), "GRUB splash screen missing"
    assert wallpaper.exists(), "Desktop wallpaper missing"
    return f"Splash ({splash.stat().st_size//1024}KB) + Wallpaper ({wallpaper.stat().st_size//1024}KB)"


# ═══════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════

# Collect all test functions
ALL_TESTS = [
    test_source_tree,
    test_rust_compile,
    test_python_lint,
    test_shell_scripts,
    test_bayesian,
    test_skills,
    test_configs,
    test_branding,
    test_iso_script,
    test_tts,
    test_agent_ipc,
    test_vision_health,
    test_dashboard,
    test_event_bus,
]


def run_all(quick_mode=False, json_output=False):
    global results
    results = []

    if not json_output:
        print(f"\n{BOLD}{CYAN}AI Distro Integration Tests{RESET}")
        print(f"{DIM}{'═' * 55}{RESET}\n")

    for test_func in ALL_TESTS:
        test_func(quick_mode)
        r = results[-1]

        if not json_output:
            name = r["name"]
            status = r["status"]
            msg = r.get("message", "")

            if status == "pass":
                icon = f"{GREEN}✓{RESET}"
            elif status == "fail":
                icon = f"{RED}✗{RESET}"
            elif status == "skipped":
                icon = f"{YELLOW}○{RESET}"
            else:
                icon = f"{RED}!{RESET}"

            print(f"  {icon} {name}")
            if msg and status != "pass":
                for line in msg.split("\n")[:3]:
                    print(f"    {DIM}{line}{RESET}")

    # Summary
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    errors = sum(1 for r in results if r["status"] == "error")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    total = len(results)

    if json_output:
        print(json.dumps({
            "results": results,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
            }
        }, indent=2))
    else:
        print(f"\n{DIM}{'═' * 55}{RESET}")
        color = GREEN if failed == 0 and errors == 0 else RED
        print(
            f"  {color}{BOLD}{passed}/{total} passed{RESET}"
            f"  {DIM}({failed} failed, {errors} errors, {skipped} skipped){RESET}"
        )
        print()

    return failed == 0 and errors == 0


def main():
    quick = "--quick" in sys.argv
    json_out = "--json" in sys.argv
    success = run_all(quick_mode=quick, json_output=json_out)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
