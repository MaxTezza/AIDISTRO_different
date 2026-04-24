#!/usr/bin/env python3
import sys
import os
import json
import time
import magic
from pypdf import PdfReader
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# We'll use the existing memory engine to store these as 'File Contexts'
MEMORY_ENGINE = os.path.join(os.path.dirname(__file__), "memory_engine.py")

class SemanticFileHandler(FileSystemEventHandler):
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.processed_files = set()

    def on_modified(self, event):
        if not event.is_directory:
            self.index_file(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self.index_file(event.src_path)

    def extract_content(self, path):
        mime = magic.from_file(path, mime=True)
        try:
            if mime == "application/pdf":
                reader = PdfReader(path)
                text = ""
                for page in reader.pages[:5]: # Index first 5 pages
                    text += page.extract_text() + " "
                return f"[FILE:PDF] {os.path.basename(path)}: {text[:500]}"
            elif mime.startswith("text/"):
                with open(path, "r", errors='ignore') as f:
                    return f"[FILE:TEXT] {os.path.basename(path)}: {f.read(500)}"
            elif mime.startswith("image/"):
                # In Phase 3, we would use the Vision Brain here
                return f"[FILE:IMAGE] {os.path.basename(path)}"
            else:
                return f"[FILE:OTHER] {os.path.basename(path)} ({mime})"
        except Exception as e:
            return None

    def index_file(self, path):
        if path in self.processed_files:
            return
        
        content = self.extract_content(path)
        if content:
            import subprocess
            # Tag the memory as a file reference
            note = f"Found a file at {path}. Content summary: {content}"
            subprocess.run(["python3", MEMORY_ENGINE, "remember", note], capture_output=True)
            self.processed_files.add(path)
            print(f"Indexed: {os.path.basename(path)}")

def main():
    watch_dir = os.path.expanduser("~/Documents")
    if not os.path.exists(watch_dir):
        os.makedirs(watch_dir, exist_ok=True)
        
    print(f"Semantic Indexer watching: {watch_dir}")
    event_handler = SemanticFileHandler(watch_dir)
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
