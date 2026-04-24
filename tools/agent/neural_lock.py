#!/usr/bin/env python3
import cv2
import sys
import os
import json
import subprocess

# Paths
VISION_BRAIN = os.path.expanduser("~/AI_Distro/tools/agent/vision_brain.py")
LOCK_FILE = "/tmp/ai-distro-locked"

def capture_face():
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    if ret:
        path = "/tmp/auth_face.jpg"
        cv2.imwrite(path, frame)
        cam.release()
        return path
    cam.release()
    return None

def verify_user(name):
    face_path = capture_face()
    if not face_path:
        return False, "Could not access camera."
    
    # Use our existing Vision Brain (Moondream) to verify
    prompt = f"Is the person in this image the authorized user named {name}? Answer only Yes or No."
    res = subprocess.run(["python3", VISION_BRAIN, face_path, prompt], capture_output=True, text=True)
    
    if "yes" in res.stdout.lower():
        return True, "User verified."
    return False, "User not recognized."

def main():
    if len(sys.argv) < 2:
        print("Usage: neural_lock.py [verify|lock|status] [name]")
        return

    cmd = sys.argv[1]
    if cmd == "verify" and len(sys.argv) > 2:
        name = sys.argv[2]
        success, msg = verify_user(name)
        if success:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
            print(json.dumps({"status": "ok", "message": "Neural Unlock Successful."}))
        else:
            print(json.dumps({"status": "error", "message": msg}))
            
    elif cmd == "lock":
        with open(LOCK_FILE, "w") as f:
            f.write("locked")
        print(json.dumps({"status": "ok", "message": "System Locked."}))
        
    elif cmd == "status":
        locked = os.path.exists(LOCK_FILE)
        print(json.dumps({"locked": locked}))

if __name__ == "__main__":
    main()
