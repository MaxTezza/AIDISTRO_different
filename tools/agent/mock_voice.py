#!/usr/bin/env python3
import socket
import json
import time

AGENT_SOCKET = "/tmp/ai-distro-agent.sock"

def send_command(text):
    print(f"\n[SIMULATED VOICE]: '{text}'")
    req = {"version": 1, "name": "natural_language", "payload": text}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(AGENT_SOCKET)
            client.sendall(json.dumps(req).encode('utf-8') + b"\n")
            resp = json.loads(client.recv(8192).decode('utf-8'))
            print(f"[AGENT RESPONSE]: {resp.get('message')}")
    except Exception as e:
        print(f"Mock Voice Error: {e}")

def main():
    print("Mock Voice Engine active. Simulating user commands...")
    time.sleep(5)
    send_command("What is the weather today?")
    time.sleep(10)
    send_command("What do you see on my screen?")
    time.sleep(15)
    send_command("Thank you, computer.")

if __name__ == "__main__":
    main()
