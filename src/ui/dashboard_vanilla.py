import os
import json
import socket
import threading
import asyncio
import websockets
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Paths
UI_DIR = os.path.dirname(os.path.abspath(__file__))
EVENT_SOCKET_PATH = "/tmp/ai-distro-events.sock"

# Websocket clients
clients = set()

async def ws_handler(websocket, path):
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)

async def broadcast_ws(message):
    if clients:
        await asyncio.gather(*[client.send(message) for client in clients])

def listen_for_events():
    """Listens for events from the Rust agent (Unix Socket) and broadcasts to WebSockets."""
    if os.path.exists(EVENT_SOCKET_PATH):
        os.remove(EVENT_SOCKET_PATH)
    
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(EVENT_SOCKET_PATH)
    server.listen(5)
    
    print(f"Vanilla Dashboard listening for events on {EVENT_SOCKET_PATH}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        conn, _ = server.accept()
        file_obj = conn.makefile('r')
        for line in file_obj:
            if not line:
                break
            try:
                event_str = line.strip()
                print(f"Broadcasting event: {event_str}")
                asyncio.run_coroutine_threadsafe(broadcast_ws(event_str), loop)
            except Exception as e:
                print(f"Error: {e}")
        conn.close()

class CustomHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UI_DIR, **kwargs)

def start_http():
    print("Starting HTTP Dashboard on http://localhost:5000")
    httpd = HTTPServer(('0.0.0.0', 5000), CustomHandler)
    httpd.serve_forever()

async def main():
    # Start HTTP in a thread
    threading.Thread(target=start_http, daemon=True).start()
    # Start Event Listener in a thread
    threading.Thread(target=listen_for_events, daemon=True).start()
    
    # Start WebSocket Server
    print("Starting WebSocket Server on ws://localhost:5001")
    async with websockets.serve(ws_handler, "0.0.0.0", 5001):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
