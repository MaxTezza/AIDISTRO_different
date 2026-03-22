#!/usr/bin/env python3
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


def local_provider_unavailable(output_text: str) -> bool:
    text = (output_text or "").strip().lower()
    if not text:
        return True
    signals = (
        "imap is not configured",
        "unable to connect",
        "request failed",
        "not enabled yet",
    )
    return any(token in text for token in signals)


def main():
    if len(sys.argv) < 2:
        print("usage: email_router.py summary|search|draft [payload]")
        return 2
    cmd = sys.argv[1].strip().lower()
    payload = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    providers = load_providers()
    provider = providers.get("email", "gmail")
    here = Path(__file__).resolve().parent

    imap_tool = str(here / "email_imap_tool.py")
    live_tools = {
        "gmail": str(here / "gmail_tool.py"),
        "outlook": str(here / "outlook_tool.py"),
    }

    if provider in live_tools:
        code, out, err = run_tool(live_tools[provider], cmd, payload)
        live_unavailable = code != 0 or live_provider_unavailable(out or err)
        if live_unavailable:
            local_code, local_out, local_err = run_tool(imap_tool, cmd, payload)
            local_unavailable = local_code != 0 or local_provider_unavailable(local_out or local_err)
            if local_unavailable:
                print(f"[email status] live provider unavailable ({provider}) and local fallback unavailable.")
                if out:
                    print(f"[email status] live provider detail: {out}")
                elif err:
                    print(f"[email status] live provider detail: {err}")
                if local_out:
                    print(f"[email status] local fallback detail: {local_out}")
                elif local_err:
                    print(f"[email status] local fallback detail: {local_err}")
                return 1
            print(f"[email status] using local fallback; live provider unavailable ({provider}).")
            if out:
                print(f"[email status] live provider detail: {out}")
            elif err:
                print(f"[email status] live provider detail: {err}")
            if local_out:
                print(local_out)
            if local_code != 0 and local_err:
                print(local_err, file=sys.stderr)
            return 0

        print(f"[email status] connected live provider: {provider}.")
        if out:
            print(out)
        if code != 0 and err:
            print(err, file=sys.stderr)
        return code

    if provider == "imap":
        code, out, err = run_tool(imap_tool, cmd, payload)
        print("[email status] using local email provider (imap).")
        if out:
            print(out)
        if code != 0 and err:
            print(err, file=sys.stderr)
        return code

    print(f"[email status] provider '{provider}' is not configured.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
