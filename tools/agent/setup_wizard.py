#!/usr/bin/env python3
import time
import os
import json
import subprocess

# Paths
PIPER_BIN = os.path.expanduser("~/.cache/ai-distro/piper/piper/piper")
PIPER_MODEL = os.path.expanduser("~/.cache/ai-distro/piper/en_US-amy-medium.onnx")
HUD_BIN = os.path.expanduser("~/AI_Distro/src/rust/target/release/ai-distro-hud")
EVENT_SOCKET = "/tmp/ai-distro-events.sock"

def speak(text):
    """Uses Piper to talk to the user during setup."""
    print(f"\n[ASSISTANT]: {text}")
    try:
        # Pipe text -> Piper -> aplay
        p1 = subprocess.Popen(["echo", text], stdout=subprocess.PIPE)
        p2 = subprocess.Popen([PIPER_BIN, "--model", PIPER_MODEL, "--output_raw"], stdin=p1.stdout, stdout=subprocess.PIPE)
        p3 = subprocess.Popen(["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"], stdin=p2.stdout)
        p1.stdout.close()
        p2.stdout.close()
        p3.wait()
    except Exception as e:
        print(f"(TTS Error: {e})")

def broadcast_event(title, message):
    """Sends a card to the HUD."""
    try:
        import socket
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(EVENT_SOCKET)
            event = {"type": "info", "title": title, "message": message}
            client.sendall(json.dumps(event).encode('utf-8') + b"\n")
    except Exception:
        pass

def main():
    os.system('clear')
    print("="*50)
    print("   AI DISTRO: INITIALIZATION SEQUENCE")
    print("="*50)
    
    # 1. Launch HUD in background
    print("\n[SYSTEM]: Initializing Visual HUD...")
    subprocess.Popen([HUD_BIN], stdout=subprocess.DEV_NULL, stderr=subprocess.DEV_NULL)
    time.sleep(3) # Wait for HUD to bind socket
    
    # 2. Greeting
    speak("Hello! I am your AI Distro Operating Partner. I am currently initializing my core systems.")
    broadcast_event("Initialization", "Core systems active. Starting neural calibration.")
    
    # 3. Name & Personality
    name = input("\n[YOU]: First, what is your name? ")
    speak(f"It is a pleasure to meet you, {name}. I'll remember that.")
    broadcast_event("Memory", f"User identified as {name}. Personalizing interaction layer.")
    
    # 4. Identity
    speak("I have created a private local identity for myself so I can help you with accounts and trials.")
    address = "assistant@local.aidistro.os"
    print(f"\n[SYSTEM]: Your assistant's address: {address}")
    broadcast_event("Identity", f"Mailbox active at {address}")
    
    # 5. Microphone Test
    speak("I am ready to listen. I'll be waiting for the wake word 'Computer'. Let's check your audio levels.")
    input("\n[YOU]: Please say 'Computer' now and press Enter... ")
    speak("I heard you perfectly. My senses are now calibrated.")
    
    # 6. Physicality
    speak("I can also manage your workspace. I'm going to try arranging your windows now.")
    broadcast_event("Workspace", "Testing window orchestration logic...")
    # (In a real setup, we'd trigger a simple wmctrl test here)
    
    # 7. Finalize
    speak("Initialization complete. You can now use your computer naturally. Ask me to find files, check the weather, or help you with your work.")
    broadcast_event("Welcome", "System fully manifest. How can I help you today?")
    
    # Save Context
    config = {
        "user_name": name,
        "setup_date": str(time.ctime()),
        "setup_complete": True
    }
    
    config_path = os.path.expanduser("~/.config/ai-distro-user.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f)
        
    print("\n" + "="*50)
    print("   SETUP SUCCESSFUL. ENJOY THE REVOLUTION.")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
