#!/usr/bin/env python3
import sys
import subprocess
import os
import json

def start_slideshow(folder):
    path = os.path.expanduser(f"~/Pictures/{folder}")
    if not os.path.exists(path):
        # Fallback to just Pictures
        path = os.path.expanduser("~/Pictures")
    
    if not os.path.exists(path):
        return "I couldn't find your pictures folder."

    # Kill any existing feh
    subprocess.run(["pkill", "feh"])
    # feh -Z (auto-zoom) -z (random) -F (fullscreen) -D (delay seconds)
    subprocess.Popen(["feh", "-Z", "-z", "-F", "-D", "5", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Starting a slideshow of your {folder or 'photos'}."

def main():
    folder = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    result = start_slideshow(folder)
    print(json.dumps({"status": "ok", "message": result}))

if __name__ == "__main__":
    main()
