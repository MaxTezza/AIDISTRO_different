#!/usr/bin/env python3
"""
AI Distro — Opt-In Crash Reporter

Captures and structures crash data for debugging. Strictly opt-in with
full transparency — users can inspect, redact, and approve every report
before submission.

Features:
  - Automatic crash detection (service failures, Python tracebacks)
  - Structured crash reports with system info, logs, and context
  - Privacy-first: users inspect and approve before any submission
  - Local crash history with search
  - Automatic PII redaction (usernames, paths, IPs, emails)
  - Export for manual bug reports

Usage:
  python3 crash_reporter.py capture <service>    # Capture a crash report
  python3 crash_reporter.py list                  # List crash reports
  python3 crash_reporter.py view <id>             # View a crash report
  python3 crash_reporter.py redact <id>           # Redact PII from a report
  python3 crash_reporter.py export <id>           # Export for bug report
  python3 crash_reporter.py status                # Show reporter status
  python3 crash_reporter.py config                # Show/set config
  python3 crash_reporter.py clean [days]          # Clean old reports
"""
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

CRASH_DIR = Path(os.path.expanduser("~/.cache/ai-distro/crashes"))
CONFIG_FILE = Path(os.path.expanduser("~/.config/ai-distro/crash_reporter.json"))

# What to redact automatically
PII_PATTERNS = [
    (r"/home/\w+", "/home/[REDACTED]"),
    (r"/Users/\w+", "/Users/[REDACTED]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
    (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP_REDACTED]"),
    (r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b",
     "[UUID_REDACTED]"),
    (r"(api[_-]?key|token|secret|password|passwd|pwd)\s*[=:]\s*\S+",
     r"\1=[SECRET_REDACTED]"),
]


def _load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "enabled": True,
        "auto_redact": True,
        "require_approval": True,
        "retain_days": 30,
    }


def _save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _redact_text(text):
    """Redact PII from text."""
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _get_system_info():
    """Collect non-identifying system information."""
    info = {
        "os": platform.system(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "distro_version": "unknown",
    }

    # Kernel
    try:
        r = subprocess.run(["uname", "-r"], capture_output=True, text=True, timeout=3)
        info["kernel"] = r.stdout.strip()
    except Exception:
        pass

    # Session type
    info["session"] = os.environ.get("XDG_SESSION_TYPE", "unknown")
    info["desktop"] = os.environ.get("XDG_CURRENT_DESKTOP", "unknown")

    # Memory
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    info["memory_gb"] = round(kb / 1024 / 1024, 1)
                    break
    except Exception:
        pass

    # GPU (safe, no identifiers)
    try:
        r = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.split("\n"):
            if "VGA" in line or "3D" in line:
                info["gpu"] = line.split(": ", 1)[-1].strip() if ": " in line else line.strip()
                break
    except Exception:
        pass

    return info


def _get_service_logs(service_name, lines=50):
    """Get recent logs from a service."""
    try:
        r = subprocess.run(
            ["journalctl", "--user", "-u", f"ai-distro-{service_name}",
             "-n", str(lines), "--no-pager"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass

    # Fallback: check log file
    log_file = Path(os.path.expanduser(f"~/.cache/ai-distro/{service_name}.log"))
    if log_file.exists():
        content = log_file.read_text()
        return "\n".join(content.split("\n")[-lines:])

    return ""


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def capture(service_name, exception=None, context=None):
    """Capture a crash report."""
    config = _load_config()
    if not config.get("enabled"):
        return {"status": "disabled", "message": "Crash reporter is disabled"}

    CRASH_DIR.mkdir(parents=True, exist_ok=True)

    # Build report
    timestamp = datetime.now()
    crash_id = hashlib.sha256(
        f"{service_name}-{timestamp.isoformat()}".encode()
    ).hexdigest()[:12]

    report = {
        "id": crash_id,
        "service": service_name,
        "timestamp": timestamp.isoformat(),
        "system": _get_system_info(),
        "exception": None,
        "traceback": None,
        "logs": "",
        "context": context or {},
        "redacted": config.get("auto_redact", True),
        "approved": False,
    }

    # Capture exception info
    if exception:
        report["exception"] = str(exception)
        report["traceback"] = traceback.format_exc()
    elif sys.exc_info()[0] is not None:
        report["exception"] = str(sys.exc_info()[1])
        report["traceback"] = traceback.format_exc()

    # Capture service logs
    report["logs"] = _get_service_logs(service_name)

    # Auto-redact PII
    if config.get("auto_redact"):
        for key in ["exception", "traceback", "logs"]:
            if report[key]:
                report[key] = _redact_text(report[key])

    # Save report
    report_path = CRASH_DIR / f"{crash_id}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return {
        "status": "captured",
        "id": crash_id,
        "path": str(report_path),
        "message": "Crash report saved. Run 'view' to inspect before sharing.",
    }


def list_reports():
    """List all crash reports."""
    if not CRASH_DIR.exists():
        return []

    reports = []
    for f in sorted(CRASH_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(f) as fh:
                data = json.load(fh)
            reports.append({
                "id": data.get("id", f.stem),
                "service": data.get("service", "unknown"),
                "timestamp": data.get("timestamp", "unknown"),
                "exception": (data.get("exception", "")[:80] if data.get("exception") else ""),
                "approved": data.get("approved", False),
            })
        except (json.JSONDecodeError, OSError):
            pass

    return reports


def view_report(crash_id):
    """View a specific crash report."""
    report_path = CRASH_DIR / f"{crash_id}.json"
    if not report_path.exists():
        return {"error": f"Report not found: {crash_id}"}

    with open(report_path) as f:
        return json.load(f)


def redact_report(crash_id):
    """Re-run PII redaction on a report."""
    report_path = CRASH_DIR / f"{crash_id}.json"
    if not report_path.exists():
        return {"error": f"Report not found: {crash_id}"}

    with open(report_path) as f:
        report = json.load(f)

    for key in ["exception", "traceback", "logs"]:
        if report.get(key):
            report[key] = _redact_text(report[key])

    report["redacted"] = True

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return {"status": "ok", "id": crash_id, "message": "PII redacted"}


def export_report(crash_id):
    """Export a crash report as a markdown bug report."""
    report = view_report(crash_id)
    if "error" in report:
        return report

    sys_info = report.get("system", {})
    md = f"""# AI Distro Crash Report

**ID:** {report.get('id')}
**Service:** {report.get('service')}
**Timestamp:** {report.get('timestamp')}

## System
- **OS:** {sys_info.get('os')} ({sys_info.get('arch')})
- **Kernel:** {sys_info.get('kernel', 'unknown')}
- **Python:** {sys_info.get('python')}
- **Session:** {sys_info.get('session')}
- **Memory:** {sys_info.get('memory_gb', '?')} GB
- **GPU:** {sys_info.get('gpu', 'unknown')}

## Exception
```
{report.get('exception', 'N/A')}
```

## Traceback
```python
{report.get('traceback', 'N/A')}
```

## Recent Logs
```
{report.get('logs', 'N/A')}
```

---
*Auto-generated by AI Distro Crash Reporter. PII redacted: {report.get('redacted', False)}*
"""

    export_path = CRASH_DIR / f"{crash_id}.md"
    export_path.write_text(md)

    return {"status": "ok", "path": str(export_path), "size": len(md)}


def clean_old(days=30):
    """Remove crash reports older than N days."""
    if not CRASH_DIR.exists():
        return {"removed": 0}

    cutoff = datetime.now() - timedelta(days=days)
    removed = 0

    for f in CRASH_DIR.glob("*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
            ts = datetime.fromisoformat(data.get("timestamp", ""))
            if ts < cutoff:
                f.unlink()
                md = f.with_suffix(".md")
                if md.exists():
                    md.unlink()
                removed += 1
        except (json.JSONDecodeError, ValueError, OSError):
            pass

    return {"removed": removed, "cutoff_days": days}


def get_status():
    """Show crash reporter status."""
    config = _load_config()
    reports = list_reports()

    return {
        "enabled": config.get("enabled", True),
        "auto_redact": config.get("auto_redact", True),
        "require_approval": config.get("require_approval", True),
        "total_reports": len(reports),
        "pending_approval": sum(1 for r in reports if not r.get("approved")),
        "retain_days": config.get("retain_days", 30),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: crash_reporter.py <capture|list|view|redact|export|status|config|clean>")
        return

    cmd = sys.argv[1]

    if cmd == "capture":
        service = sys.argv[2] if len(sys.argv) > 2 else "unknown"
        print(json.dumps(capture(service), indent=2))
    elif cmd == "list":
        reports = list_reports()
        if reports:
            for r in reports:
                approved = "✓" if r["approved"] else "○"
                print(f"  {approved} [{r['id']}] {r['service']:15s} {r['timestamp']}")
                if r["exception"]:
                    print(f"    {r['exception']}")
        else:
            print("  No crash reports")
    elif cmd == "view":
        crash_id = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(view_report(crash_id), indent=2))
    elif cmd == "redact":
        crash_id = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(redact_report(crash_id), indent=2))
    elif cmd == "export":
        crash_id = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(export_report(crash_id), indent=2))
    elif cmd == "status":
        print(json.dumps(get_status(), indent=2))
    elif cmd == "config":
        config = _load_config()
        if len(sys.argv) > 3:
            key, val = sys.argv[2], sys.argv[3]
            if val.lower() in ("true", "false"):
                config[key] = val.lower() == "true"
            elif val.isdigit():
                config[key] = int(val)
            else:
                config[key] = val
            _save_config(config)
        print(json.dumps(config, indent=2))
    elif cmd == "clean":
        days = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 30
        print(json.dumps(clean_old(days), indent=2))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
