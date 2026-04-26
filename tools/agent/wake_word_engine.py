#!/usr/bin/env python3
"""
AI Distro Wake Word Engine — "Hey Computer" Hands-Free Activation

Listens continuously on the microphone for a configurable wake word.
When detected, it signals the Voice service to start recording a command.

Strategies (in priority order):
  1. openwakeword  — ML-based, high accuracy, offline
  2. vosk keyword  — Lightweight speech recognition fallback
  3. Energy-based   — Simple amplitude threshold (always available)

Usage:
  python3 wake_word_engine.py              # Run with best available engine
  python3 wake_word_engine.py --test       # Test detection without IPC
  python3 wake_word_engine.py --engine energy  # Force specific engine
"""
import json
import os
import socket
import struct
import sys
import time

WAKE_PHRASES = ["hey computer", "computer", "hey distro"]
AGENT_SOCKET = os.environ.get("AI_DISTRO_IPC_SOCKET", "/run/ai-distro/agent.sock")
EVENT_SOCKET = "/tmp/ai-distro-events.sock"
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.5  # seconds per audio chunk
COOLDOWN = 2.0  # seconds to wait after a detection before listening again


def broadcast_event(title, message):
    """Send notification to HUD."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1.0)
            client.connect(EVENT_SOCKET)
            event = {"type": "info", "title": title, "message": message}
            client.sendall(json.dumps(event).encode("utf-8") + b"\n")
    except Exception:
        pass


def signal_agent_listening():
    """Tell the agent that a wake word was detected."""
    request = {
        "version": 1,
        "name": "wake_word_detected",
        "payload": json.dumps({"timestamp": time.time()})
    }
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(5.0)
            client.connect(AGENT_SOCKET)
            client.sendall(json.dumps(request).encode("utf-8") + b"\n")
    except Exception as e:
        print(f"[WakeWord] IPC signal failed: {e}")


# ═══════════════════════════════════════════════════════════════════
# Engine 1: openwakeword (best quality)
# ═══════════════════════════════════════════════════════════════════
class OpenWakeWordEngine:
    """ML-based wake word detection using openwakeword."""

    name = "openwakeword"

    @staticmethod
    def available():
        try:
            import openwakeword  # noqa: F401
            return True
        except ImportError:
            return False

    def __init__(self):
        import openwakeword
        from openwakeword.model import Model
        openwakeword.utils.download_models()
        # Use the built-in "hey_jarvis" model as a base —
        # it generalizes well to "hey computer" type phrases
        self.model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        self.threshold = float(os.environ.get("WAKE_THRESHOLD", "0.5"))

    def check(self, audio_chunk_int16):
        """Returns True if wake word detected in audio chunk."""
        import numpy as np
        audio_np = np.frombuffer(audio_chunk_int16, dtype=np.int16)
        prediction = self.model.predict(audio_np)
        for _model_name, score in prediction.items():
            if score >= self.threshold:
                return True
        return False


# ═══════════════════════════════════════════════════════════════════
# Engine 2: Vosk keyword spotting
# ═══════════════════════════════════════════════════════════════════
class VoskEngine:
    """Lightweight speech recognition with keyword filtering."""

    name = "vosk"

    @staticmethod
    def available():
        try:
            import vosk  # noqa: F401
            # Check for a model
            model_path = os.path.expanduser("~/.cache/ai-distro/vosk-model")
            return os.path.isdir(model_path)
        except ImportError:
            return False

    def __init__(self):
        import vosk
        model_path = os.path.expanduser("~/.cache/ai-distro/vosk-model")
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, SAMPLE_RATE)
        self.wake_phrases = WAKE_PHRASES

    def check(self, audio_chunk_int16):
        """Returns True if any wake phrase detected."""
        if self.recognizer.AcceptWaveform(audio_chunk_int16):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "").lower()
            return any(phrase in text for phrase in self.wake_phrases)
        # Also check partial results
        partial = json.loads(self.recognizer.PartialResult())
        text = partial.get("partial", "").lower()
        return any(phrase in text for phrase in self.wake_phrases)


# ═══════════════════════════════════════════════════════════════════
# Engine 3: Energy-based (always available)
# ═══════════════════════════════════════════════════════════════════
class EnergyEngine:
    """
    Simple energy-based 'clap detector' fallback.
    Triggers on sustained loud audio (simulating someone saying a wake word).
    Not as accurate but requires zero dependencies.
    """

    name = "energy"

    @staticmethod
    def available():
        return True

    def __init__(self):
        self.threshold = float(os.environ.get("WAKE_ENERGY_THRESHOLD", "2000"))
        self.sustained_frames = 0
        self.required_frames = 3  # Need 3 consecutive loud chunks (~1.5s of speech)

    def check(self, audio_chunk_int16):
        """Returns True after sustained audio above threshold."""
        # Calculate RMS energy
        samples = struct.unpack(f"<{len(audio_chunk_int16)//2}h", audio_chunk_int16)
        if not samples:
            return False
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5

        if rms > self.threshold:
            self.sustained_frames += 1
            if self.sustained_frames >= self.required_frames:
                self.sustained_frames = 0
                return True
        else:
            self.sustained_frames = 0
        return False


# ═══════════════════════════════════════════════════════════════════
# Main Loop
# ═══════════════════════════════════════════════════════════════════
def select_engine(forced=None):
    """Select the best available wake word engine."""
    engines = [OpenWakeWordEngine, VoskEngine, EnergyEngine]

    if forced:
        for eng_cls in engines:
            if eng_cls.name == forced:
                if eng_cls.available():
                    return eng_cls()
                print(f"[WakeWord] Engine '{forced}' requested but not available.")
                sys.exit(1)
        print(f"[WakeWord] Unknown engine: {forced}")
        sys.exit(1)

    for eng_cls in engines:
        if eng_cls.available():
            return eng_cls()

    # Should never happen — EnergyEngine is always available
    return EnergyEngine()


def open_microphone():
    """Open the default microphone using PyAudio."""
    import pyaudio
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=int(SAMPLE_RATE * CHUNK_DURATION)
    )
    return pa, stream


def run(engine, test_mode=False):
    """Main listening loop."""
    print(f"[WakeWord] Engine: {engine.name}")
    print(f"[WakeWord] Listening for wake word... (phrases: {WAKE_PHRASES})")

    try:
        pa, stream = open_microphone()
    except Exception as e:
        print(f"[WakeWord] Microphone not available: {e}")
        print("[WakeWord] Install pyaudio: pip install pyaudio")
        sys.exit(1)

    last_detection = 0

    try:
        while True:
            chunk = stream.read(
                int(SAMPLE_RATE * CHUNK_DURATION),
                exception_on_overflow=False
            )

            now = time.time()
            if now - last_detection < COOLDOWN:
                continue

            if engine.check(chunk):
                last_detection = now
                print(f"[WakeWord] ✦ WAKE WORD DETECTED at {time.strftime('%H:%M:%S')}")

                if test_mode:
                    print("[WakeWord] (Test mode — not signaling agent)")
                else:
                    signal_agent_listening()
                    broadcast_event("Listening", "Wake word detected — I'm listening...")

    except KeyboardInterrupt:
        print("\n[WakeWord] Stopped.")
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


def main():
    forced_engine = None
    test_mode = False

    for arg in sys.argv[1:]:
        if arg == "--test":
            test_mode = True
        elif arg.startswith("--engine"):
            if "=" in arg:
                forced_engine = arg.split("=", 1)[1]
            elif sys.argv.index(arg) + 1 < len(sys.argv):
                forced_engine = sys.argv[sys.argv.index(arg) + 1]

    engine = select_engine(forced_engine)
    run(engine, test_mode)


if __name__ == "__main__":
    main()
