#!/usr/bin/env python3
"""
Screen Context Tool — "The Eyes"

Captures the current screen and uses Moondream2 VLM to describe what's on it.
Falls back to Tesseract OCR if the VLM isn't available.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SCREENSHOT_DIR = Path(os.path.expanduser("~/.cache/ai-distro/screenshots"))
VISION_BRAIN = Path(os.path.dirname(__file__)) / "vision_brain.py"


def capture_screen():
    """Take a screenshot using scrot (X11) or grim (Wayland)."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    filename = SCREENSHOT_DIR / "current_screen.png"

    # Try scrot first (X11), then grim (Wayland)
    for tool, args in [
        ("scrot", [str(filename)]),
        ("grim", [str(filename)]),
    ]:
        try:
            result = subprocess.run(
                [tool] + args, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return filename, "Success"
        except FileNotFoundError:
            continue
        except Exception as e:
            return None, f"Capture failed: {e}"

    return None, "No screenshot tool available (install scrot or grim)"


def run_vlm(image_path, prompt="Describe what you see on this screen."):
    """Send the screenshot to Moondream2 VLM for reasoning.

    Tries the persistent HTTP service first (fast, ~100ms),
    then falls back to subprocess CLI (cold start, ~5-10s).
    """
    # Method 1: Persistent VLM service on localhost:7860
    try:
        import urllib.request
        req_data = json.dumps({
            "image_path": str(image_path),
            "prompt": prompt
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:7860/vision",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if result.get("status") == "ok":
                return result.get("answer", "")
    except Exception:
        pass

    # Method 2: Direct subprocess call (cold start)
    try:
        result = subprocess.run(
            [sys.executable, str(VISION_BRAIN), str(image_path), prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None



def run_ocr(image_path):
    """Fallback: extract text from the screenshot using Tesseract OCR."""
    try:
        result = subprocess.run(
            ["tesseract", str(image_path), "stdout"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            if text:
                return text
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return None


def get_active_windows():
    """Get the list of open windows for structural context."""
    windows = []
    try:
        result = subprocess.run(
            ["wmctrl", "-l", "-p"], capture_output=True, text=True
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                parts = line.split(None, 4)
                if len(parts) >= 5:
                    windows.append(parts[4])
    except Exception:
        pass

    # Fallback: xdotool
    if not windows:
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                windows.append(result.stdout.strip())
        except Exception:
            pass

    return windows


def main():
    action = "describe"
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action.startswith("{"):
            try:
                data = json.loads(action)
                action = data.get("action", "describe")
            except Exception:
                pass

    # 1. Capture screen
    path, status = capture_screen()
    if not path:
        print(json.dumps({"status": "error", "message": status}))
        return

    # 2. Get window context (structural awareness)
    windows = get_active_windows()

    # 3. Run VLM or OCR depending on action
    if action == "extract_text":
        ocr_text = run_ocr(path)
        if ocr_text:
            print(json.dumps({
                "status": "ok",
                "message": f"Text extracted from screen:\n{ocr_text[:2000]}",
                "data": {
                    "screenshot_path": str(path),
                    "ocr_text": ocr_text[:2000],
                    "open_windows": windows
                }
            }))
        else:
            print(json.dumps({
                "status": "error",
                "message": "Could not extract text. Tesseract may not be installed."
            }))
    else:
        # Visual reasoning with VLM
        prompt = "Describe what applications are open and what the user appears to be doing."
        vlm_description = run_vlm(path, prompt)

        if vlm_description:
            message = vlm_description
        else:
            # Fallback to structural context from window manager
            if windows:
                message = f"I can see you have these windows open: {', '.join(windows[:5])}."
                # Try OCR as a secondary context source
                ocr_text = run_ocr(path)
                if ocr_text:
                    # Extract a meaningful snippet
                    snippet = ocr_text[:300].replace("\n", " ").strip()
                    message += f" I can also read some text: '{snippet}...'"
            else:
                message = "I captured your screen but couldn't identify the contents. VLM and window manager access may need setup."

        print(json.dumps({
            "status": "ok",
            "message": message,
            "data": {
                "screenshot_path": str(path),
                "open_windows": windows,
                "vlm_available": vlm_description is not None
            }
        }))


if __name__ == "__main__":
    main()
