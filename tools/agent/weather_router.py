#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

from provider_config import load_providers


def run_tool(tool_path: str, payload: str):
    proc = subprocess.run(
        [sys.executable, tool_path, payload],
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
        "weather unavailable",
        "unable to acquire",
        "request failed",
        "timed out",
        "name resolution",
        "network",
    )
    return any(token in text for token in signals)


def main():
    payload = "today" if len(sys.argv) < 2 else " ".join(sys.argv[1:])
    providers = load_providers()
    provider = providers.get("weather", "default")
    provider = provider.strip().lower() if isinstance(provider, str) else "default"

    here = Path(__file__).resolve().parent
    live_tool = str(here / "weather_tool.py")
    local_tool = str(here / "weather_local_tool.py")

    if provider in ("default", "wttr"):
        code, out, err = run_tool(live_tool, payload)
        if code == 0 and not live_provider_unavailable(out or err):
            print("[weather status] connected live provider: wttr.")
            if out:
                print(out)
            return 0

        local_code, local_out, local_err = run_tool(local_tool, payload)
        if local_code == 0 and local_out:
            print("[weather status] using local fallback; live provider unavailable (wttr).")
            if out:
                print(f"[weather status] live provider detail: {out}")
            elif err:
                print(f"[weather status] live provider detail: {err}")
            print(local_out)
            return 0

        print("[weather status] live provider unavailable (wttr) and local fallback unavailable.")
        if out:
            print(f"[weather status] live provider detail: {out}")
        elif err:
            print(f"[weather status] live provider detail: {err}")
        if local_out:
            print(f"[weather status] local fallback detail: {local_out}")
        elif local_err:
            print(f"[weather status] local fallback detail: {local_err}")
        return 1

    if provider == "local":
        code, out, err = run_tool(local_tool, payload)
        if code == 0 and out:
            print("[weather status] using local weather provider.")
            print(out)
            return 0
        print("[weather status] local weather provider unavailable.")
        if out:
            print(f"[weather status] local detail: {out}")
        elif err:
            print(f"[weather status] local detail: {err}")
        return 1

    code, out, err = run_tool(local_tool, payload)
    if code == 0 and out:
        print(f"[weather status] provider '{provider}' is unknown. Using local fallback.")
        print(out)
        return 0
    print(f"[weather status] provider '{provider}' is unknown and local fallback unavailable.")
    if out:
        print(f"[weather status] local fallback detail: {out}")
    elif err:
        print(f"[weather status] local fallback detail: {err}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
