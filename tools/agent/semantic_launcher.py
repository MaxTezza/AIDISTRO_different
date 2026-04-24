#!/usr/bin/env python3
import os
import json
import subprocess
import glob
from pathlib import Path

# Paths
MEMORY_ENGINE = os.path.expanduser("~/AI_Distro/tools/agent/memory_engine.py")

def get_desktop_files():
    paths = [
        "/usr/share/applications/*.desktop",
        os.path.expanduser("~/.local/share/applications/*.desktop")
    ]
    files = []
    for p in paths:
        files.extend(glob.glob(p))
    return files

def parse_desktop_file(path):
    try:
        data = {}
        with open(path, "r", errors='ignore') as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    data[key] = val
        
        name = data.get("Name", "")
        comment = data.get("Comment", "")
        exec_cmd = data.get("Exec", "").split(" ")[0].replace("%u", "").replace("%U", "").strip()
        categories = data.get("Categories", "")
        
        if name and exec_cmd:
            return {
                "name": name,
                "comment": comment,
                "exec": exec_cmd,
                "categories": categories
            }
    except:
        pass
    return None

def index_apps():
    print("Scanning applications for semantic indexing...")
    files = get_desktop_files()
    apps = []
    for f in files:
        app = parse_desktop_file(f)
        if app:
            apps.append(app)
            # Store in vector brain
            note = f"[APP] {app['name']}: {app['comment']} (Category: {app['categories']}) | Exec: {app['exec']}"
            subprocess.run(["python3", MEMORY_ENGINE, "remember", note], capture_output=True)
    
    print(f"Indexed {len(apps)} applications.")

def search_apps(query):
    # Use memory engine to find relevant app
    res = subprocess.run(["python3", MEMORY_ENGINE, "query", f"find an app for: {query}"], capture_output=True, text=True)
    if res.returncode == 0:
        try:
            memories = json.loads(res.stdout.strip())
            for m in memories:
                if "[APP]" in m:
                    # Extract the exec command
                    exec_cmd = m.split("| Exec: ")[-1].strip()
                    app_name = m.split(":")[0].replace("[APP]", "").strip()
                    print(f"Found: {app_name} -> {exec_cmd}")
                    return exec_cmd
        except:
            pass
    return None

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: semantic_launcher.py [index|launch] [query]")
        return

    cmd = sys.argv[1]
    if cmd == "index":
        index_apps()
    elif cmd == "launch" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        exec_cmd = search_apps(query)
        if exec_cmd:
            print(f"Launching {exec_cmd}...")
            subprocess.Popen([exec_cmd], stdout=subprocess.DEV_NULL, stderr=subprocess.DEV_NULL)
        else:
            print(f"No application found for '{query}'")

if __name__ == "__main__":
    main()
