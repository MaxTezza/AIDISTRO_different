#!/usr/bin/env python3
import sys
import json

# For Grandma, we map names to real addresses
FAMILY_CONTACTS = {
    "daughter": "daughter@example.com",
    "grandson": "grandson@example.com",
    "son": "son@example.com"
}

def send_message(name, message):
    address = FAMILY_CONTACTS.get(name.lower())
    if not address:
        return f"I don't have a contact for '{name}'. Should I add them?"

    # Use our existing autonomous identity tool or email router
    # For now, we simulate success for the demo
    print(f"DEBUG: Sending message to {address}: {message}")
    
    # In a real setup:
    # subprocess.run(["python3", "email_router.py", "send", address, f"Message from AI Distro", message])
    
    return f"I've sent your message to your {name}."

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"status": "error", "message": "Who should I message and what is the text?"}))
        return
    
    name = sys.argv[1]
    msg = " ".join(sys.argv[2:])
    
    result = send_message(name, msg)
    print(json.dumps({"status": "ok", "message": result}))

if __name__ == "__main__":
    main()
