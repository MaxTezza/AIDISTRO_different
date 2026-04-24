#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import json

# Paths
MEMORY_ENGINE = os.path.expanduser("~/AI_Distro/tools/agent/memory_engine.py")

def index_path(path):
    print(f"Starting Great Migration for: {path}")
    count = 0
    # Walk the directory
    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            # Skip hidden files and large binaries
            if file.startswith('.') or os.path.getsize(file_path) > 1024 * 1024 * 5: # 5MB limit
                continue
                
            try:
                # Use our existing file_indexer logic or direct memory feed
                # For high-speed migration, we feed a condensed summary
                ext = os.path.splitext(file)[1].lower()
                important_exts = ['.py', '.rs', '.js', '.txt', '.md', '.pdf', '.doc', '.docx']
                
                if ext in important_exts:
                    note = f"[MIGRATED FILE] {file} found in {root}. Path: {file_path}"
                    # We'll use the memory engine directly
                    subprocess.run(["python3", MEMORY_ENGINE, "remember", note], capture_output=True)
                    count += 1
                    if count % 10 == 0:
                        print(f"Indexed {count} files...")
            except Exception as e:
                print(f"Skipping {file}: {e}")

    print(f"Migration complete. {count} legacy items are now part of my semantic memory.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: legacy_importer.py <directory_path>")
    else:
        index_path(sys.argv[1])
