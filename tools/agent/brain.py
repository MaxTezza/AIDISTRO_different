#!/usr/bin/env python3
import json
import os
import sys
import requests
from pathlib import Path

# Paths
CONFIG_PATH = Path(os.path.expanduser("~/AI_Distro/configs/agent.json"))
MODEL_DIR = Path(os.path.expanduser("~/.cache/ai-distro/models"))
SKILLS_CORE_DIR = Path(os.environ.get("AI_DISTRO_SKILLS_CORE_DIR", "src/skills/core"))
SKILLS_DYNAMIC_DIR = Path(os.environ.get("AI_DISTRO_SKILLS_DYNAMIC_DIR", "src/skills/dynamic"))

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except:
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

def build_system_prompt(skills):
    prompt = "You are the AI Distro Orchestrator, a sentient operating system partner.\n"
    prompt += "Your goal is to achieve the user's goal by chaining together available actions.\n\n"
    prompt += "AVAILABLE ACTIONS:\n"
    for s in skills:
        prompt += f"- {s['name']}: {s['description']}\n"
    
    prompt += "\nGUIDELINES:\n"
    prompt += "1. Respond ONLY with a valid JSON object: {\"version\": 1, \"name\": \"action_name\", \"payload\": \"value\"}\n"
    prompt += "2. For complex tasks, perform the FIRST step. I will call you again with the result to get the next step.\n"
    prompt += "3. Use 'screen_context' to see the screen, 'remember' for facts, and 'web_task' for the internet.\n"
    prompt += "4. NEVER output technical error codes. Focus on the user's intent.\n"
    return prompt

def get_cloud_response(config, system_prompt, user_input):
    provider = config.get("intelligence", {}).get("cloud_provider", "openai")
    api_key = config.get("intelligence", {}).get("api_key", "")
    
    if not api_key:
        return None

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
        except:
            return None
    return None

def get_llama(config):
    try:
        from llama_cpp import Llama
        model_name = config.get("intelligence", {}).get("local_model", "llama-3.2-1b-instruct.gguf")
        model_path = MODEL_DIR / model_name
        if not model_path.exists():
            # Fallback to 1B if 3B is missing
            model_path = MODEL_DIR / "llama-3.2-1b-instruct.gguf"
        return Llama(model_path=str(model_path), n_ctx=2048, verbose=False)
    except Exception:
        return None

def load_memories(user_input):
    engine = os.path.join(os.path.dirname(__file__), "memory_engine.py")
    try:
        import subprocess
        res = subprocess.run(["python3", engine, "query", user_input], capture_output=True, text=True)
        if res.returncode == 0:
            return json.loads(res.stdout.strip())
    except Exception:
        pass
    return []

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"name": "unknown", "payload": "missing input"}))
        return

    user_input = " ".join(sys.argv[1:])
    config = load_config()
    skills = load_skills()
    memories = load_memories(user_input)
    
    system_prompt = build_system_prompt(skills)
    if memories:
        system_prompt += f"\n\nRELEVANT CONTEXT FROM PAST INTERACTIONS:\n- " + "\n- ".join(memories)
    
    # Decide: Cloud or Local
    result = None
    if config.get("intelligence", {}).get("use_cloud", False):
        result = get_cloud_response(config, system_prompt, user_input)
    
    if not result:
        llm = get_llama(config)
        if not llm:
            sys.exit(1)
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
