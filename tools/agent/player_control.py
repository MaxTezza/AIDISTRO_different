#!/usr/bin/env python3
import sys
import subprocess
import os
import json

# For a Grandma, we want simple stations: "Classical", "Jazz", "News"
STATIONS = {
    "classical": "http://stream.radioparadise.com/mellow-128",
    "jazz": "http://stream.radioparadise.com/rock-128",
    "news": "https://stream.live.vc.bbc.com/bbc_world_service"
}

def control_player(command, target=None):
    if command == "play":
        url = STATIONS.get(target.lower(), target) if target else STATIONS["classical"]
        # Kill any existing mpv
        subprocess.run(["pkill", "mpv"])
        subprocess.Popen(["mpv", "--no-video", url], stdout=subprocess.DEV_NULL, stderr=subprocess.DEV_NULL)
        return f"Playing {target or 'music'} for you."
    elif command == "stop":
        subprocess.run(["pkill", "mpv"])
        return "I've stopped the music."
    elif command == "volume":
        # target would be a number like "50"
        vol = target if target else "50"
        subprocess.run(["amixer", "set", "Master", f"{vol}%"])
        return f"Volume set to {vol}%."
    return "Unknown player command."

def main():
    if len(sys.argv) < 2:
        return
    
    cmd = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = control_player(cmd, target)
    print(json.dumps({"status": "ok", "message": result}))

if __name__ == "__main__":
    main()
