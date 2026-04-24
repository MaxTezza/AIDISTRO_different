import os
import json
import socket
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

EVENT_SOCKET_PATH = os.environ.get("AI_DISTRO_EVENT_SOCKET", "/tmp/ai-distro-events.sock")

def listen_for_events():
    """Listens for events from the Rust agent and broadcasts them to the web UI."""
    if os.path.exists(EVENT_SOCKET_PATH):
        os.remove(EVENT_SOCKET_PATH)
    
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(EVENT_SOCKET_PATH)
    server.listen(5)
    
    print(f"Dashboard listening for events on {EVENT_SOCKET_PATH}")
    
    while True:
        conn, _ = server.accept()
        threading.Thread(target=handle_client, args=(conn,)).start()

def handle_client(conn):
    with conn:
        file_obj = conn.makefile('r')
        for line in file_obj:
            if not line:
                break
            try:
                event = json.loads(line.strip())
                print(f"Broadcasting event: {event}")
                socketio.emit('ai_event', event)
            except Exception as e:
                print(f"Error parsing event: {e}")

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Start the event listener in a background thread
    threading.Thread(target=listen_for_events, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000)
