#!/usr/bin/env python3
import socket
import os
import json
import threading

AGENT_SOCKET = "/tmp/ai-distro-agent.sock"
EVENT_SOCKET = "/tmp/ai-distro-events.sock"

def broadcast_event(event):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(EVENT_SOCKET)
            client.sendall(json.dumps(event).encode('utf-8') + b"\n")
    except Exception as e:
        print(f"Mock Agent Broadcast Error: {e}")

def handle_client(conn):
    with conn:
        file_obj = conn.makefile('r')
        for line in file_obj:
            if not line:
                break
            try:
                req = json.loads(line.strip())
                print(f"Mock Agent received: {req}")
                
                # Logic
                if req['name'] == 'natural_language':
                    text = req['payload'].lower()
                    msg = f"I understood you said: {text}. I'm on it!"
                    broadcast_event({"type": "info", "title": "Command", "message": msg})
                    resp = {"version": 1, "action": "natural_language", "status": "ok", "message": msg}
                elif req['name'] == 'proactive_suggestion':
                    payload = json.loads(req['payload'])
                    msg = payload['message']
                    broadcast_event({"type": "info", "title": "proactive_suggestion", "message": msg})
                    resp = {"version": 1, "action": "proactive_suggestion", "status": "ok", "message": "Broadcasted"}
                else:
                    resp = {"version": 1, "action": req['name'], "status": "ok", "message": "Mock success"}

                conn.sendall(json.dumps(resp).encode('utf-8') + b"\n")
            except Exception as e:
                print(f"Mock Agent error: {e}")

def main():
    if os.path.exists(AGENT_SOCKET):
        os.remove(AGENT_SOCKET)
    
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(AGENT_SOCKET)
    server.listen(5)
    print(f"Mock Agent listening on {AGENT_SOCKET}")
    
    while True:
        conn, _ = server.accept()
        threading.Thread(target=handle_client, args=(conn,)).start()

if __name__ == "__main__":
    main()
