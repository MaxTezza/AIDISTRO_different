#!/usr/bin/env python3
"""
Download Model — Fetches the configured GGUF model for local LLM inference.

Downloads from Hugging Face using direct HTTP (no HF library needed).
Supports resume on interrupted downloads via Range headers.

Usage:
  python3 download_model.py                 # Download default model from agent.json
  python3 download_model.py <model_name>    # Download a specific model by name
"""
import json
import os
import sys
import urllib.request
import urllib.error

MODEL_DIR = os.path.expanduser("~/.cache/ai-distro/models")
CONFIG_PATH = os.environ.get(
    "AI_DISTRO_CONFIG",
    os.path.expanduser("~/AI_Distro/configs/agent.json")
)

# Known model registry: name → (HF repo, filename, expected size in bytes, sha256 prefix)
MODEL_REGISTRY = {
    "llama-3.2-1b-instruct.gguf": {
        "repo": "bartowski/Llama-3.2-1B-Instruct-GGUF",
        "file": "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "size_mb": 776,
    },
    "llama-3.2-3b-instruct.gguf": {
        "repo": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_mb": 2019,
    },
    "moondream2.gguf": {
        "repo": "vikhyatk/moondream2",
        "file": "moondream2-text-model-f16.gguf",
        "size_mb": 3400,
    },
}


def load_config_model():
    """Read the model name from agent.json."""
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        return cfg.get("intelligence", {}).get("local_model", "llama-3.2-1b-instruct.gguf")
    except Exception:
        return "llama-3.2-1b-instruct.gguf"


def hf_url(repo, filename):
    """Build a Hugging Face direct download URL."""
    return f"https://huggingface.co/{repo}/resolve/main/{filename}"


def download_file(url, dest_path, expected_mb=0):
    """Download a file with progress reporting and resume support."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    partial_path = dest_path + ".partial"
    existing_size = 0

    # Resume support: check for partial download
    if os.path.exists(partial_path):
        existing_size = os.path.getsize(partial_path)
        print(f"  Resuming from {existing_size / 1024 / 1024:.1f} MB...")

    headers = {}
    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            # Check if server supports range (206) or sends full file (200)
            if resp.status == 200 and existing_size > 0:
                # Server ignored Range header, start over
                existing_size = 0

            content_length = resp.headers.get("Content-Length")
            total_size = int(content_length) + existing_size if content_length else 0

            mode = "ab" if existing_size > 0 and resp.status == 206 else "wb"
            downloaded = existing_size if mode == "ab" else 0

            with open(partial_path, mode) as f:
                chunk_size = 1024 * 1024  # 1 MB chunks
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Progress bar
                    if total_size > 0:
                        pct = downloaded / total_size * 100
                        bar_len = 40
                        filled = int(bar_len * downloaded / total_size)
                        bar = "█" * filled + "░" * (bar_len - filled)
                        print(
                            f"\r  [{bar}] {pct:.1f}% "
                            f"({downloaded / 1024 / 1024:.0f}/{total_size / 1024 / 1024:.0f} MB)",
                            end="", flush=True
                        )
                    else:
                        print(
                            f"\r  Downloaded {downloaded / 1024 / 1024:.0f} MB...",
                            end="", flush=True
                        )

            print()  # Newline after progress bar

    except urllib.error.HTTPError as e:
        print(f"\n  HTTP error: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"\n  Download interrupted: {e}")
        print("  Partial file saved. Re-run to resume.")
        return False

    # Move partial to final
    os.rename(partial_path, dest_path)
    final_size = os.path.getsize(dest_path)
    print(f"  Saved: {dest_path} ({final_size / 1024 / 1024:.0f} MB)")
    return True


def download_model(model_name):
    """Download a model by name from the registry."""
    if model_name not in MODEL_REGISTRY:
        print(f"Unknown model: {model_name}")
        print(f"Available models: {', '.join(MODEL_REGISTRY.keys())}")
        return False

    entry = MODEL_REGISTRY[model_name]
    dest_path = os.path.join(MODEL_DIR, model_name)

    # Check if already downloaded
    if os.path.exists(dest_path):
        size_mb = os.path.getsize(dest_path) / 1024 / 1024
        if size_mb > 10:  # Sanity check: model should be at least 10 MB
            print(f"✔ Model already exists: {dest_path} ({size_mb:.0f} MB)")
            return True
        else:
            print(f"  Existing file too small ({size_mb:.1f} MB), re-downloading...")
            os.remove(dest_path)

    url = hf_url(entry["repo"], entry["file"])
    print(f"Downloading {model_name}...")
    print(f"  Source: {url}")
    print(f"  Expected size: ~{entry['size_mb']} MB")
    print()

    return download_file(url, dest_path, entry["size_mb"])


def main():
    if len(sys.argv) > 1:
        model_name = sys.argv[1].strip()
    else:
        model_name = load_config_model()

    print("AI Distro Model Downloader")
    print(f"Model: {model_name}")
    print(f"Target: {MODEL_DIR}/")
    print()

    os.makedirs(MODEL_DIR, exist_ok=True)

    ok = download_model(model_name)
    if ok:
        print("\n✔ Ready for inference.")
    else:
        print("\n✘ Download failed. Check your network and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
