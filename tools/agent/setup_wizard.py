#!/usr/bin/env python3
"""
AI Distro — First-Run Setup Wizard

Downloads required models, configures services, tests hardware,
and walks the user through personalization. Designed to take a fresh
install from "boots up" to "fully functional" in one sitting.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
CACHE_DIR = Path(os.path.expanduser("~/.cache/ai-distro"))
MODEL_DIR = CACHE_DIR / "models"
PIPER_DIR = CACHE_DIR / "piper"
CONFIG_DIR = Path(os.path.expanduser("~/.config"))
USER_CONFIG = CONFIG_DIR / "ai-distro-user.json"
SPIRIT_CONFIG = CONFIG_DIR / "ai-distro-spirit.json"
PIPER_BIN = PIPER_DIR / "piper" / "piper"
PIPER_MODEL = PIPER_DIR / "en_US-amy-medium.onnx"
PIPER_MODEL_JSON = PIPER_DIR / "en_US-amy-medium.onnx.json"

# ── Model URLs ───────────────────────────────────────────────────────
PIPER_VOICE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "en/en_US/amy/medium/en_US-amy-medium.onnx"
)
PIPER_VOICE_JSON_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "en/en_US/amy/medium/en_US-amy-medium.onnx.json"
)
PIPER_BINARY_URL = (
    "https://github.com/rhasspy/piper/releases/download/v1.2.0/"
    "piper_amd64.tar.gz"
)

# ── Terminal Colors ──────────────────────────────────────────────────
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
PURPLE = "\033[95m"
RESET = "\033[0m"


def banner():
    print(f"""
{PURPLE}{BOLD}╔══════════════════════════════════════════════════╗
║         AI DISTRO — FIRST-RUN SETUP              ║
║     Your Sentient Operating System Partner        ║
╚══════════════════════════════════════════════════╝{RESET}
""")


def step(num, title, total=6):
    print(f"\n{CYAN}{BOLD}[{num}/{total}]{RESET} {BOLD}{title}{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")


def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")


def warn(msg):
    print(f"  {YELLOW}⚠{RESET} {msg}")


def fail(msg):
    print(f"  {RED}✗{RESET} {msg}")


def ask(prompt, default=""):
    """Ask with default value."""
    suffix = f" [{default}]" if default else ""
    answer = input(f"  {BOLD}→{RESET} {prompt}{suffix}: ").strip()
    return answer if answer else default


def ask_yn(prompt, default=True):
    """Yes/no question."""
    hint = "Y/n" if default else "y/N"
    answer = input(f"  {BOLD}→{RESET} {prompt} ({hint}): ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def download_file(url, dest, label=""):
    """Download with progress bar."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        ok(f"Already downloaded: {dest.name}")
        return True

    display = label or dest.name
    print(f"  {DIM}Downloading {display}...{RESET}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Distro/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 65536
            tmp = dest.with_suffix(".part")

            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total > 0:
                        pct = downloaded * 100 // total
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        bar_len = 30
                        filled = bar_len * downloaded // total
                        bar = "█" * filled + "░" * (bar_len - filled)
                        print(
                            f"\r  {DIM}  [{bar}] {pct}%  "
                            f"{mb_down:.1f}/{mb_total:.1f} MB{RESET}",
                            end="", flush=True
                        )

            tmp.rename(dest)
            print()  # Newline after progress bar
            ok(f"Downloaded: {display}")
            return True

    except Exception as e:
        fail(f"Download failed: {e}")
        # Clean up partial
        tmp = dest.with_suffix(".part")
        if tmp.exists():
            tmp.unlink()
        return False


def extract_tar_gz(archive, dest_dir):
    """Extract a .tar.gz archive."""
    import tarfile
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(path=dest_dir, filter="data")
        ok(f"Extracted to {dest_dir}")
        return True
    except Exception as e:
        fail(f"Extraction failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
# STEP 1: Piper TTS (Voice)
# ═══════════════════════════════════════════════════════════════════
def setup_voice():
    step(1, "Voice Engine — Piper TTS")
    print(f"  {DIM}The AI needs a voice to talk to you.{RESET}")
    print(f"  {DIM}This downloads the Piper engine (~20MB) and Amy voice (~60MB).{RESET}")

    if PIPER_BIN.exists() and PIPER_MODEL.exists():
        ok("Piper engine and Amy voice already installed.")
        return True

    if not ask_yn("Download the voice engine now?"):
        warn("Skipped. The AI won't be able to speak. You can re-run setup later.")
        return False

    # Download Piper binary
    if not PIPER_BIN.exists():
        tar_path = PIPER_DIR / "piper_linux_x86_64.tar.gz"
        if download_file(PIPER_BINARY_URL, tar_path, "Piper engine"):
            extract_tar_gz(tar_path, PIPER_DIR)
            tar_path.unlink(missing_ok=True)
            if PIPER_BIN.exists():
                PIPER_BIN.chmod(0o755)
            else:
                fail("Piper binary not found after extraction.")
                return False

    # Download Amy voice model
    download_file(PIPER_VOICE_URL, PIPER_MODEL, "Amy voice model")
    download_file(PIPER_VOICE_JSON_URL, PIPER_MODEL_JSON, "Amy voice config")

    if PIPER_BIN.exists() and PIPER_MODEL.exists():
        ok("Voice engine ready!")
        return True

    fail("Voice setup incomplete.")
    return False


# ═══════════════════════════════════════════════════════════════════
# STEP 2: Vision Model (Moondream2)
# ═══════════════════════════════════════════════════════════════════
def setup_vision():
    step(2, "Vision Engine — Moondream2 VLM")
    print(f"  {DIM}This lets the AI see your screen and understand what's on it.{RESET}")
    print(f"  {DIM}The model is ~1.5GB and requires the 'moondream' pip package.{RESET}")

    # Check if moondream is installed
    try:
        import moondream  # noqa: F401
        ok("Moondream Python package is installed.")
    except ImportError:
        warn("The 'moondream' package is not installed.")
        if ask_yn("Install it now via pip?"):
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "moondream", "-q"],
                    stdout=subprocess.DEVNULL
                )
                ok("Installed moondream package.")
            except subprocess.CalledProcessError:
                fail("pip install failed. You may need to run: pip install moondream")
                return False
        else:
            warn("Skipped. The AI won't be able to see your screen.")
            return False

    print(f"  {DIM}The model will download automatically on first use (~1.5GB).{RESET}")
    ok("Vision engine configured. Model will load when the service starts.")
    return True


# ═══════════════════════════════════════════════════════════════════
# STEP 3: LLM Brain
# ═══════════════════════════════════════════════════════════════════
def setup_brain():
    step(3, "AI Brain — Local Language Model")
    print(f"  {DIM}The brain handles understanding and reasoning.{RESET}")
    print(f"  {DIM}Options: Local LLM (private, offline) or Cloud (faster, requires API key).{RESET}")

    # Check for Ollama
    ollama_available = shutil.which("ollama") is not None

    if ollama_available:
        ok("Ollama is installed.")
        # Check if a model is pulled
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )
            if "llama" in result.stdout.lower() or "mistral" in result.stdout.lower():
                ok("Local model already available.")
                return True
        except Exception:
            pass

        if ask_yn("Pull a local model (Llama 3.2 1B, ~700MB)?"):
            print(f"  {DIM}This may take a few minutes...{RESET}")
            try:
                subprocess.run(["ollama", "pull", "llama3.2:1b"], check=True)
                ok("Local brain ready!")
                return True
            except subprocess.CalledProcessError:
                fail("Model pull failed.")
    else:
        warn("Ollama is not installed.")
        print(f"  {DIM}To install: curl -fsSL https://ollama.com/install.sh | sh{RESET}")

    # Cloud fallback
    print()
    print(f"  {DIM}You can also use a cloud API (OpenAI, Gemini, etc.).{RESET}")
    api_key = ask("Enter an API key (or press Enter to skip)")
    if api_key:
        provider = ask("Provider (openai/gemini)", "openai")
        # Write directly to agent.json — this is what brain.py reads
        agent_config_paths = [
            Path("/etc/ai-distro/agent.json"),
            Path(os.path.expanduser("~/AI_Distro/configs/agent.json")),
        ]
        updated = False
        for cfg_path in agent_config_paths:
            if cfg_path.exists():
                try:
                    with open(cfg_path) as f:
                        cfg = json.load(f)
                    cfg.setdefault("intelligence", {})
                    cfg["intelligence"]["use_cloud"] = True
                    cfg["intelligence"]["cloud_provider"] = provider
                    cfg["intelligence"]["api_key"] = api_key
                    with open(cfg_path, "w") as f:
                        json.dump(cfg, f, indent=2)
                    ok(f"Cloud brain configured in {cfg_path}")
                    updated = True
                    break
                except PermissionError:
                    warn(f"Can't write to {cfg_path} (try sudo or edit manually)")
        if not updated:
            # Fallback: save to home config
            fallback = Path(os.path.expanduser("~/AI_Distro/configs/agent.json"))
            fallback.parent.mkdir(parents=True, exist_ok=True)
            cfg = {"intelligence": {"use_cloud": True, "cloud_provider": provider, "api_key": api_key}}
            with open(fallback, "w") as f:
                json.dump(cfg, f, indent=2)
            ok(f"Cloud brain configured ({provider}) in {fallback}")
        return True

    warn("No brain configured. The AI can still execute commands but won't reason.")
    return False


# ═══════════════════════════════════════════════════════════════════
# STEP 4: Audio Test
# ═══════════════════════════════════════════════════════════════════
def test_audio(voice_installed):
    step(4, "Audio Hardware Test")

    # Test speaker output
    if voice_installed and PIPER_BIN.exists() and PIPER_MODEL.exists():
        if ask_yn("Test speaker output? (You should hear a voice)"):
            try:
                test_text = "Hello. I am your AI Distro partner. Audio is working."
                p1 = subprocess.Popen(["echo", test_text], stdout=subprocess.PIPE)
                p2 = subprocess.Popen(
                    [str(PIPER_BIN), "--model", str(PIPER_MODEL), "--output_raw"],
                    stdin=p1.stdout, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )
                p3 = subprocess.Popen(
                    ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
                    stdin=p2.stdout, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                p1.stdout.close()
                p2.stdout.close()
                p3.wait(timeout=15)
                if ask_yn("Did you hear the voice?"):
                    ok("Speaker output confirmed!")
                else:
                    warn("Audio may need configuration. Check: pactl list sinks")
            except Exception as e:
                warn(f"Audio test failed: {e}")
    else:
        warn("Skipping voice test (Piper not installed).")

    # Test microphone + Vosk STT
    mic_available = shutil.which("arecord") is not None
    if mic_available:
        print(f"  {DIM}Microphone check...{RESET}")
        try:
            result = subprocess.run(
                ["arecord", "-l"], capture_output=True, text=True, timeout=5
            )
            if "card" in result.stdout.lower():
                ok("Microphone hardware detected.")
                # Check Vosk
                vosk_model = Path(os.path.expanduser("~/.cache/ai-distro/vosk/model"))
                if vosk_model.is_dir():
                    ok("Vosk STT model ready for voice input.")
                else:
                    warn("Vosk STT model not found. Run install.sh to download it.")
            else:
                warn("No microphone found. Voice input will be unavailable.")
        except Exception:
            warn("Could not check microphone.")
    else:
        warn("arecord not found. Install alsa-utils for microphone support.")


# ═══════════════════════════════════════════════════════════════════
# STEP 5: Telegram Remote Control (Spirit Bridge)
# ═══════════════════════════════════════════════════════════════════
def setup_telegram():
    step(5, "Telegram Remote Control (Optional)")
    print(f"  {DIM}Control your computer from your phone via Telegram.{RESET}")
    print(f"  {DIM}Requires a Telegram bot token from @BotFather.{RESET}")

    if SPIRIT_CONFIG.exists():
        ok("Telegram already configured.")
        return True

    if not ask_yn("Set up Telegram remote control?", default=False):
        warn("Skipped. You can configure this later in ~/.config/ai-distro-spirit.json")
        return False

    print(f"""
  {DIM}How to get a token:
  1. Open Telegram and message @BotFather
  2. Send /newbot and follow the prompts
  3. Copy the token it gives you
  4. Send any message to your new bot
  5. Visit https://api.telegram.org/bot<TOKEN>/getUpdates
  6. Find your chat_id in the response{RESET}
""")

    token = ask("Bot token")
    chat_id = ask("Your chat ID (numeric)")

    if token and chat_id:
        config = {"token": token, "master_id": chat_id}
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(SPIRIT_CONFIG, "w") as f:
            json.dump(config, f, indent=2)
        ok("Telegram configured!")
        return True

    warn("Incomplete info. Skipping Telegram setup.")
    return False


# ═══════════════════════════════════════════════════════════════════
# STEP 6: Personalization
# ═══════════════════════════════════════════════════════════════════
def personalize():
    step(6, "Personalization")

    name = ask("What should I call you?", "Pilot")

    print(f"\n  {DIM}Choose an assistant persona:{RESET}")
    print(f"  {BOLD}1.{RESET} Max  — Confident, proactive, direct")
    print(f"  {BOLD}2.{RESET} Alfred — Polished, formal, butler-style")
    persona = ask("Persona (1 or 2)", "1")
    persona_name = "alfred" if persona == "2" else "max"

    config = {
        "user_name": name,
        "persona": persona_name,
        "setup_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "setup_complete": True
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG, "w") as f:
        json.dump(config, f, indent=2)

    ok(f"Welcome, {name}! Your partner ({persona_name.title()}) is ready.")
    return config


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
def main():
    banner()

    # Check if already set up
    if USER_CONFIG.exists():
        try:
            with open(USER_CONFIG) as f:
                existing = json.load(f)
            if existing.get("setup_complete"):
                name = existing.get("user_name", "Pilot")
                print(f"  {DIM}Setup was already completed for {name}.{RESET}")
                if not ask_yn("Run setup again?", default=False):
                    print(f"\n  {GREEN}All good! Run 'ai-distro start' to begin.{RESET}\n")
                    return
        except Exception:
            pass

    results = {}

    # Step 1: Voice
    results["voice"] = setup_voice()

    # Step 2: Vision
    results["vision"] = setup_vision()

    # Step 3: Brain
    results["brain"] = setup_brain()

    # Step 4: Audio test
    test_audio(results["voice"])

    # Step 5: Telegram
    results["telegram"] = setup_telegram()

    # Step 6: Personalization
    user_config = personalize()
    user_config["capabilities"] = results

    # Save final config
    with open(USER_CONFIG, "w") as f:
        json.dump(user_config, f, indent=2)

    # ── Summary ──────────────────────────────────────────────────
    print(f"""
{PURPLE}{BOLD}╔══════════════════════════════════════════════════╗
║              SETUP COMPLETE                       ║
╚══════════════════════════════════════════════════╝{RESET}
""")

    for cap, status in results.items():
        icon = f"{GREEN}✓{RESET}" if status else f"{YELLOW}○{RESET}"
        print(f"  {icon} {cap.title()}")

    print(f"""
{BOLD}Next steps:{RESET}
  {CYAN}ai-distro start{RESET}    — Wake up all 9 services
  {CYAN}ai-distro status{RESET}   — Check system pulse
  {CYAN}ai-distro heal{RESET}     — Run diagnostics
  {CYAN}ai-distro setup{RESET}    — Re-run this wizard

{DIM}Your config: {USER_CONFIG}{RESET}
{GREEN}{BOLD}AI Distro: It doesn't just run your apps. It understands your world.{RESET}
""")


if __name__ == "__main__":
    main()
