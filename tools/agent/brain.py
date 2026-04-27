#!/usr/bin/env python3
"""
Brain — AI Distro's LLM reasoning engine.

Routes user input through: Bayesian context → Memory recall → LLM inference.
Uses local Llama 3.2 with cloud fallback (OpenAI/Gemini).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

# Paths
CONFIG_PATH = Path(os.environ.get(
    "AI_DISTRO_CONFIG",
    os.path.expanduser("~/AI_Distro/configs/agent.json")
))
MODEL_DIR = Path(os.path.expanduser("~/.cache/ai-distro/models"))
SKILLS_CORE_DIR = Path(os.environ.get("AI_DISTRO_SKILLS_CORE_DIR", "src/skills/core"))
SKILLS_DYNAMIC_DIR = Path(os.environ.get("AI_DISTRO_SKILLS_DYNAMIC_DIR", "src/skills/dynamic"))


def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def load_skills():
    skills = []
    for d in [SKILLS_CORE_DIR, SKILLS_DYNAMIC_DIR]:
        if not d.exists():
            continue
        for p in d.glob("*.json"):
            try:
                with open(p, "r") as f:
                    skills.append(json.load(f))
            except Exception:
                pass
    return skills


def build_system_prompt(skills, bayesian_context="", memories=None):
    prompt = "You are the AI Distro Pilot, a sentient operating system partner.\n"
    prompt += "You don't just give advice; you PERFORM the work to achieve the user's goal.\n\n"
    prompt += "PILOT RULES:\n"
    prompt += "1. If a button needs clicking, use 'ui_click' to do it yourself. Don't tell the user to click it.\n"
    prompt += "2. If a file is needed, find and open it using 'open_url' or 'list_files'.\n"
    prompt += "3. For complex goals, perform the FIRST physical or digital step. I will feed you the result.\n"
    prompt += "4. Be the 'Hands' for the user. Minimize instructions, maximize autonomous completion.\n"
    prompt += "5. If the user wants software written, use 'software_forge' to generate, test, and register it.\n"
    prompt += "6. Learn from user behavior. Adapt your suggestions to match their patterns.\n\n"

    # Inject Bayesian user context (learned preferences & predictions)
    if bayesian_context:
        prompt += f"\n{bayesian_context}\n\n"

    # Inject memories
    if memories:
        prompt += "RELEVANT CONTEXT FROM PAST INTERACTIONS:\n- " + "\n- ".join(memories) + "\n\n"

    prompt += "AVAILABLE ACTIONS:\n"
    for s in skills:
        prompt += f"- {s['name']}: {s['description']}\n"

    # Software generation actions
    prompt += "- software_forge_script: Generate a standalone script (payload: JSON with 'name', 'description', 'language')\n"
    prompt += "- software_forge_project: Scaffold a project (payload: JSON with 'name', 'type', 'description')\n"
    prompt += "- software_forge_execute: Execute code in sandbox (payload: JSON with 'code', 'language')\n"

    prompt += "\nRespond ONLY with a valid JSON object: {\"version\": 1, \"name\": \"action_name\", \"payload\": \"value\"}\n"
    return prompt


def get_cloud_response(config, system_prompt, user_input):
    provider = config.get("intelligence", {}).get("cloud_provider", "openai")
    api_key = config.get("intelligence", {}).get("api_key", "")

    if not api_key:
        return None

    import requests

    if provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "response_format": {"type": "json_object"}
        }
        try:
            res = requests.post(url, headers=headers, json=data, timeout=10)
            return res.json()["choices"][0]["message"]["content"]
        except Exception:
            return None

    elif provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        data = {
            "contents": [{
                "parts": [{"text": f"{system_prompt}\n\nUser: {user_input}"}]
            }],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        try:
            res = requests.post(url, json=data, timeout=15)
            content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            return content
        except Exception:
            return None

    return None


def get_llama(config):
    try:
        from llama_cpp import Llama
        model_name = config.get("intelligence", {}).get("local_model", "llama-3.2-3b-instruct.gguf")
        model_path = MODEL_DIR / model_name
        
        # If configured model doesn't exist, try any available .gguf file
        if not model_path.exists():
            available = sorted(MODEL_DIR.glob("*.gguf"), key=lambda p: p.stat().st_size, reverse=True)
            # Pick the largest model available (likely most capable)
            available = [m for m in available if m.stat().st_size > 1_000_000]  # Skip stubs
            if available:
                model_path = available[0]
                print(f"[Brain] Configured model not found, using {model_path.name}", file=sys.stderr)
            else:
                return None
        
        return Llama(model_path=str(model_path), n_ctx=2048, verbose=False)
    except Exception:
        return None


def load_memories(user_input):
    engine = os.path.join(os.path.dirname(__file__), "memory_engine.py")
    try:
        res = subprocess.run(
            ["python3", engine, "query", user_input],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            return json.loads(res.stdout.strip())
    except Exception:
        pass
    return []


def load_bayesian_context():
    """Get adaptive context from the Bayesian preference engine."""
    engine = os.path.join(os.path.dirname(__file__), "bayesian_engine.py")
    try:
        res = subprocess.run(
            [sys.executable, engine, "prompt_context"],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"name": "unknown", "payload": "missing input"}))
        return

    user_input = " ".join(sys.argv[1:])
    config = load_config()
    skills = load_skills()
    memories = load_memories(user_input)
    bayesian_context = load_bayesian_context()

    system_prompt = build_system_prompt(skills, bayesian_context, memories)

    result = None
    if config.get("intelligence", {}).get("use_cloud", False):
        result = get_cloud_response(config, system_prompt, user_input)

    if not result:
        llm = get_llama(config)
        if not llm:
            # Graceful degradation: return a helpful response instead of crashing
            fallback = {
                "version": 1,
                "name": "natural_language",
                "payload": json.dumps({
                    "message": f"I heard you say: \"{user_input}\". "
                               "My local LLM isn't loaded yet (model may still be downloading). "
                               "Try 'ai-distro intelligence mode cloud' with an API key, "
                               "or wait for the model download to finish."
                })
            }
            print(json.dumps(fallback))
            return
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"}
        )
        result = response["choices"][0]["message"]["content"]

    try:
        json.loads(result)
        print(result)
    except Exception:
        print(json.dumps({"name": "unknown", "payload": user_input}))


if __name__ == "__main__":
    main()
