#!/usr/bin/env python3
"""
AI Distro Vision Brain — Persistent VLM Service

Runs Moondream2 as a persistent HTTP microservice so the model stays
loaded in GPU/CPU memory between calls. Eliminates cold-start latency.

Modes:
  - Server mode (default): Runs on localhost:7860
  - CLI mode (--image): One-shot invocation for backwards compatibility

API:
  POST /vision
    Body: {"image_path": "/path/to/img.png", "prompt": "What do you see?"}
    Response: {"answer": "I see a desktop with...", "status": "ok"}
"""
import json
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Lazy-load heavy imports
_model = None
_model_lock = threading.Lock()

BIND_HOST = os.environ.get("VISION_HOST", "127.0.0.1")
BIND_PORT = int(os.environ.get("VISION_PORT", "7860"))


def get_model():
    """Lazy-load and cache the VLM model."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:  # Double-check after acquiring lock
                print("[VisionBrain] Loading Moondream2 model...")
                t0 = time.time()
                try:
                    import moondream as md
                    _model = md.vl(model="moondream-latest.bit6.4.whl")
                    print(f"[VisionBrain] Model loaded in {time.time()-t0:.1f}s")
                except ImportError:
                    print(
                        "[VisionBrain] 'moondream' package not installed. "
                        "Vision will use OCR fallback."
                    )
                    print(
                        "[VisionBrain] Install it with: pip install moondream"
                    )
                    return None
                except Exception as e:
                    print(f"[VisionBrain] Failed to load model: {e}")
                    return None
    return _model


def analyze_image(image_path, prompt="What do you see?"):
    """Analyze an image with the VLM, with OCR fallback."""
    from PIL import Image

    if not os.path.exists(image_path):
        return {"status": "error", "answer": f"Image not found: {image_path}"}

    try:
        model = get_model()
        if model is None:
            raise RuntimeError("VLM not available")
        image = Image.open(image_path)
        encoded = model.encode_image(image)
        answer = model.answer_question(encoded, prompt)
        return {"status": "ok", "answer": answer}
    except Exception as e:
        # OCR fallback
        try:
            import pytesseract
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            if text.strip():
                return {
                    "status": "ok",
                    "answer": f"[OCR fallback] Text on screen: '{text.strip()[:500]}'",
                    "method": "ocr"
                }
        except Exception:
            pass

        return {"status": "error", "answer": f"Vision error: {e}"}


class VisionHandler(BaseHTTPRequestHandler):
    """HTTP handler for the vision microservice."""

    def log_message(self, format, *args):
        """Custom logging to include timestamp."""
        print(f"[VisionBrain] {args[0]} {args[1]} {args[2]}")

    def do_POST(self):
        if self.path == "/vision":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body)
                image_path = data.get("image_path", "")
                prompt = data.get("prompt", "What do you see?")

                if not image_path:
                    self._respond(400, {"status": "error", "answer": "Missing image_path"})
                    return

                result = analyze_image(image_path, prompt)
                self._respond(200, result)

            except json.JSONDecodeError:
                self._respond(400, {"status": "error", "answer": "Invalid JSON"})
            except Exception as e:
                self._respond(500, {"status": "error", "answer": str(e)})
        else:
            self._respond(404, {"status": "error", "answer": "Not found"})

    def do_GET(self):
        if self.path == "/health":
            moondream_installed = True
            try:
                import moondream  # noqa: F401
            except ImportError:
                moondream_installed = False
            self._respond(200, {
                "status": "ok",
                "model_loaded": _model is not None,
                "moondream_installed": moondream_installed,
                "service": "vision-brain"
            })
        else:
            self._respond(404, {"status": "error", "answer": "Not found"})

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def run_server():
    """Start the persistent VLM server."""
    print(f"[VisionBrain] Starting vision server on {BIND_HOST}:{BIND_PORT}")

    # Preload model in background
    def preload():
        try:
            get_model()
        except Exception as e:
            print(f"[VisionBrain] Preload failed (will retry on first request): {e}")

    threading.Thread(target=preload, daemon=True).start()

    server = HTTPServer((BIND_HOST, BIND_PORT), VisionHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[VisionBrain] Shutting down.")
        server.shutdown()


def run_cli(image_path, prompt):
    """Backwards-compatible CLI mode."""
    result = analyze_image(image_path, prompt)
    print(result.get("answer", "No response"))


def main():
    if len(sys.argv) < 2:
        # Server mode (default)
        run_server()
    elif sys.argv[1] == "--server":
        run_server()
    else:
        # CLI mode: vision_brain.py <image_path> [prompt...]
        image_path = sys.argv[1]
        prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "What do you see?"
        run_cli(image_path, prompt)


if __name__ == "__main__":
    main()
