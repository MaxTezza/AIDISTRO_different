#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Paths
DEFAULT_MODEL_URL = "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
MODEL_DIR = Path(os.path.expanduser("~/.cache/ai-distro/models"))
MODEL_PATH = MODEL_DIR / "llama-3.2-1b-instruct.gguf"
SKILLS_CORE_DIR = Path(os.environ.get("AI_DISTRO_SKILLS_CORE_DIR", "src/skills/core"))
SKILLS_DYNAMIC_DIR = Path(os.environ.get("AI_DISTRO_SKILLS_DYNAMIC_DIR", "src/skills/dynamic"))

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
    prompt += "4. If a goal requires sending an email with data from the screen, your first step should be 'screen_context'.\n"
    prompt += "5. NEVER output technical error codes. Focus on the user's intent.\n"
    return prompt

def get_llama():
    try:
        from llama_cpp import Llama
        if not MODEL_PATH.exists():
            return None
        return Llama(model_path=str(MODEL_PATH), n_ctx=2048, verbose=False)
    except Exception:
        return None

def load_memories(user_input):
    """Retrieves relevant memories for the current input."""
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
    skills = load_skills()
    memories = load_memories(user_input)
    
    llm = get_llama()
    if not llm:
        sys.exit(1)

    system_prompt = build_system_prompt(skills)
    if memories:
        system_prompt += f"\n\nRELEVANT CONTEXT FROM PAST INTERACTIONS:\n- " + "\n- ".join(memories)
        system_prompt += "\nUse this context if relevant to provide a personalized response."
    
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        response_format={"type": "json_object"}
    )
    
    try:
        result = response["choices"][0]["message"]["content"]
        # Ensure it is valid JSON
        json.loads(result)
        print(result)
    except Exception:
        print(json.dumps({"name": "unknown", "payload": user_input}))

if __name__ == "__main__":
    main()
