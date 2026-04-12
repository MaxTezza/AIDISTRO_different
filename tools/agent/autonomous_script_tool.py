#!/usr/bin/env python3
import sys
import json
import subprocess
import tempfile
import os

CUSTOM_TOOLS_DIR = Path("tools/agent/custom")
DYNAMIC_SKILLS_DIR = Path("src/skills/dynamic")

def save_tool(name, description, code):
    CUSTOM_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    DYNAMIC_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    
    script_path = CUSTOM_TOOLS_DIR / f"{name}_tool.py"
    with open(script_path, "w") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("import sys, json\n\n")
        f.write(code)
        f.write("\n\nif __name__ == '__main__':\n")
        f.write("    # Generic runner for dynamic tools\n")
        f.write("    print(json.dumps({'status': 'ok', 'message': 'Dynamic tool executed.'}))\n")
    
    os.chmod(script_path, 0o755)
    
    skill_def = {
        "name": name,
        "display_name": name.replace("_", " ").title(),
        "description": description or f"Custom tool for {name}",
        "category": "custom",
        "handler": {
            "type": "python_script",
            "path": str(script_path)
        },
        "parameters": {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input for the tool"}
            }
        },
        "tags": ["custom", "dynamic"]
    }
    
    skill_path = DYNAMIC_SKILLS_DIR / f"{name}.json"
    with open(skill_path, "w") as f:
        json.dump(skill_def, f, indent=2)
    
    return f"Tool '{name}' saved and registered successfully."

def execute_code(code):
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(code.encode("utf-8"))
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout
        error = result.stderr
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "output": output,
            "error": error,
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Script timed out after 30 seconds."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def main():
    if len(sys.argv) < 2:
        print("Usage: autonomous_script_tool.py \"payload\"")
        return

    payload = sys.argv[1]
    code = ""
    description = ""
    save_as_tool = None
    tool_description = ""

    if payload.startswith("{"):
        try:
            data = json.loads(payload)
            code = data.get("code", "")
            description = data.get("description", "Executing script...")
            save_as_tool = data.get("save_as_tool")
            tool_description = data.get("tool_description", description)
        except:
            code = payload # fallback
    else:
        code = payload

    if not code:
        print(json.dumps({"status": "error", "message": "No code provided."}))
        return

    result = execute_code(code)
    
    message = f"Script execution finished. Result: {result.get('output', '')}"
    if result["status"] == "ok" and save_as_tool:
        save_msg = save_tool(save_as_tool, tool_description, code)
        message += f"\n{save_msg}"

    print(json.dumps({
        "status": result["status"],
        "message": message,
        "data": result
    }))

if __name__ == "__main__":
    main()
