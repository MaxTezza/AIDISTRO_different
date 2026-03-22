#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

from provider_config import load_providers


def run_tool(tool_path: str, cmd: str, payload: str):
    proc = subprocess.run(
        [sys.executable, tool_path, cmd, payload],
        text=True,
        capture_output=True,
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return proc.returncode, out, err


def live_provider_unavailable(output_text: str) -> bool:
    text = (output_text or "").strip().lower()
    if not text:
        return True
    signals = (
        "oauth not configured",
        "unable to acquire",
        "request failed",
        "authorization failed",
        "access token",
    )
    return any(token in text for token in signals)


def main():
    if len(sys.argv) < 2:
        print("usage: calendar_router.py add|list [payload]")
        return 2
    cmd = sys.argv[1].strip().lower()
    payload = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    providers = load_providers()
    provider = providers.get("calendar", "local")

    here = Path(__file__).resolve().parent
    local_tool = str(here / "calendar_tool.py")
    google_tool = str(here / "calendar_google_tool.py")
    microsoft_tool = str(here / "calendar_microsoft_tool.py")
    tool = local_tool
    if provider == "google":
        tool = google_tool
    elif provider == "microsoft":
        tool = microsoft_tool

    code, out, err = run_tool(tool, cmd, payload)

    live_provider = provider in ("google", "microsoft")
    live_unavailable = live_provider and (code != 0 or live_provider_unavailable(out or err))
    if live_unavailable:
        local_code, local_out, local_err = run_tool(local_tool, cmd, payload)
        print(f"[calendar status] using local fallback; live provider unavailable ({provider}).")
        if out:
            print(f"[calendar status] live provider detail: {out}")
        elif err:
            print(f"[calendar status] live provider detail: {err}")
        if local_out:
            print(local_out)
        if local_code != 0 and local_err:
            print(local_err, file=sys.stderr)
        return local_code

    if live_provider:
        print(f"[calendar status] connected live provider: {provider}.")
    else:
        print("[calendar status] using local calendar provider.")
    if out:
        print(out)
    if code != 0 and err:
        print(err, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
