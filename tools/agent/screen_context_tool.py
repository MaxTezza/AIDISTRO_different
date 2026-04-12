#!/usr/bin/env python3
import sys
import json
import subprocess
import os
from pathlib import Path

SCREENSHOT_DIR = Path(os.path.expanduser("~/.cache/ai-distro/screenshots"))

def capture_screen():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    filename = SCREENSHOT_DIR / "current_screen.png"
    
    try:
        # Use scrot to capture screen
        result = subprocess.run(["scrot", str(filename)], capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"Scrot failed: {result.stderr}"
        return filename, "Success"
    except Exception as e:
        return None, f"Capture failed: {str(e)}"

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

    path, status = capture_screen()
    
    if not path:
        print(json.dumps({"status": "error", "message": status}))
        return

    # In a full production system, we'd send this to a local VLM (Vision Language Model)
    # or run local Tesseract OCR.
    message = f"Screen captured successfully to {path}. "
    if action == "extract_text":
        message += "OCR module (Tesseract) is required for text extraction. Please install it via 'install tesseract'."
    else:
        message += "I can see your current desktop layout. (VLM reasoning simulated)."

    print(json.dumps({
        "status": "ok",
        "message": message,
        "data": {"screenshot_path": str(path)}
    }))

if __name__ == "__main__":
    main()
