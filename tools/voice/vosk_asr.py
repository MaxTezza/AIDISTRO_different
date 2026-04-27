#!/usr/bin/env python3
"""
vosk_asr — Vosk Speech-to-Text CLI wrapper for AI Distro.

Contract: reads 16-bit mono 16kHz WAV from stdin, prints transcribed text to stdout.
This bridges the Vosk Python library to the Rust voice engine's subprocess interface.

Usage:
    echo <wav_data> | python3 vosk_asr.py
    python3 vosk_asr.py < recording.wav
"""
import json
import os
import sys
import wave
import io

def find_model_path():
    """Locate the Vosk model directory."""
    candidates = [
        os.environ.get("VOSK_MODEL_PATH", ""),
        os.path.expanduser("~/.cache/ai-distro/vosk/model"),
        os.path.expanduser("~/.cache/ai-distro/vosk/vosk-model-small-en-us-0.15"),
        "/usr/share/vosk/model",
    ]
    for p in candidates:
        if p and os.path.isdir(p):
            return p
    return None


def main():
    # Read raw WAV bytes from stdin
    wav_bytes = sys.stdin.buffer.read()
    if not wav_bytes:
        print("", end="")
        sys.exit(0)

    model_path = find_model_path()
    if not model_path:
        print("ERROR: No Vosk model found", file=sys.stderr)
        sys.exit(1)

    try:
        from vosk import Model, KaldiRecognizer
    except ImportError:
        print("ERROR: vosk not installed (pip install vosk)", file=sys.stderr)
        sys.exit(1)

    # Load model (cached by process lifetime)
    model = Model(model_path)

    # Parse WAV from stdin
    try:
        wf = wave.open(io.BytesIO(wav_bytes), "rb")
    except Exception as e:
        print(f"ERROR: Invalid WAV input: {e}", file=sys.stderr)
        sys.exit(1)

    sample_rate = wf.getframerate()
    rec = KaldiRecognizer(model, sample_rate)
    rec.SetWords(False)

    # Process audio in chunks
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        rec.AcceptWaveform(data)

    # Get final result
    result = json.loads(rec.FinalResult())
    text = result.get("text", "").strip()

    # Output transcribed text to stdout (what the Rust voice engine reads)
    print(text)


if __name__ == "__main__":
    main()
