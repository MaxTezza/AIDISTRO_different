#!/usr/bin/env python3
"""
WebSocket Bridge — Connects the Agent's Unix event socket to the HUD's WebSocket.

The Agent broadcasts events to /tmp/ai-distro-events.sock (Unix domain socket).
The HUD listens on ws://127.0.0.1:5001 (WebSocket).
This bridge connects the two: it listens on the Unix socket for events from
the agent, then rebroadcasts them to all connected WebSocket clients (the HUD).

This is the missing piece that makes the HUD show real-time agent events.
"""
import asyncio
import json
import os
import signal
import socket
import sys

try:
    import websockets
    from websockets.asyncio.server import serve
except ImportError:
    import time
    print("ws_bridge: websockets package not installed. Run: pip install websockets")
    print("ws_bridge: Sleeping and retrying every 5 minutes...")
    while True:
        time.sleep(300)
        try:
            import websockets  # noqa: F811
            from websockets.asyncio.server import serve  # noqa: F811
            print("ws_bridge: websockets found! Starting...")
            break
        except ImportError:
            continue

EVENT_SOCKET = os.environ.get("AI_DISTRO_EVENT_SOCKET", "/tmp/ai-distro-events.sock")
WS_HOST = os.environ.get("AI_DISTRO_WS_HOST", "127.0.0.1")
WS_PORT = int(os.environ.get("AI_DISTRO_WS_PORT", "5001"))

# Track all connected WebSocket clients
connected_clients = set()


async def ws_handler(websocket):
    """Handle a new WebSocket connection from the HUD."""
    connected_clients.add(websocket)
    remote = websocket.remote_address
    print(f"ws_bridge: HUD connected from {remote} ({len(connected_clients)} clients)")
    try:
        # Keep connection alive — the HUD only receives, never sends
        async for _ in websocket:
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"ws_bridge: HUD disconnected ({len(connected_clients)} clients)")


async def broadcast(message: str):
    """Send a message to all connected WebSocket clients."""
    if not connected_clients:
        return
    # Use gather to send concurrently, ignoring individual failures
    await asyncio.gather(
        *(client.send(message) for client in connected_clients),
        return_exceptions=True,
    )


async def unix_socket_listener():
    """Listen on the Unix domain socket for events from the Agent.

    The Agent sends one JSON event per line. We read each line and
    rebroadcast it to all WebSocket clients.
    """
    # Clean up stale socket file
    if os.path.exists(EVENT_SOCKET):
        try:
            os.unlink(EVENT_SOCKET)
        except OSError:
            pass

    # Ensure parent directory exists
    socket_dir = os.path.dirname(EVENT_SOCKET)
    if socket_dir:
        os.makedirs(socket_dir, exist_ok=True)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(EVENT_SOCKET)
    os.chmod(EVENT_SOCKET, 0o666)  # Allow agent (any user) to connect
    server.listen(8)
    server.setblocking(False)

    loop = asyncio.get_event_loop()
    print(f"ws_bridge: Listening on Unix socket {EVENT_SOCKET}")

    while True:
        try:
            client, _ = await loop.sock_accept(server)
            asyncio.create_task(_handle_unix_client(client))
        except Exception as e:
            print(f"ws_bridge: Unix accept error: {e}")
            await asyncio.sleep(1)


async def _handle_unix_client(client: socket.socket):
    """Handle a single connection from the Agent on the Unix socket."""
    loop = asyncio.get_event_loop()
    client.setblocking(False)
    buf = b""
    try:
        while True:
            data = await loop.sock_recv(client, 4096)
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if line:
                    try:
                        # Validate JSON before forwarding
                        json.loads(line)
                        await broadcast(line.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
    except Exception:
        pass
    finally:
        client.close()


async def main():
    print(f"ws_bridge: Starting WebSocket server on {WS_HOST}:{WS_PORT}")

    # Start WebSocket server
    async with serve(ws_handler, WS_HOST, WS_PORT):
        print(f"ws_bridge: WebSocket server ready at ws://{WS_HOST}:{WS_PORT}")

        # Start Unix socket listener in parallel
        await unix_socket_listener()


def shutdown(signum, frame):
    """Clean up the Unix socket on exit."""
    if os.path.exists(EVENT_SOCKET):
        try:
            os.unlink(EVENT_SOCKET)
        except OSError:
            pass
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        shutdown(None, None)
