#!/usr/bin/env python3
import sys
import json
import subprocess
import re

def get_active_email():
    try:
        result = subprocess.run(["agent-email", "accounts", "list"], capture_output=True, text=True)
        # Parse the output to find the active email (usually marked or the first one)
        # The output is JSON-ish based on the previous command
        data = json.loads(result.stdout)
        if data.get("ok"):
            # Assuming the tool returns a list of accounts and we pick the active one
            for acc in data.get("data", []):
                if acc.get("isActive"):
                    return acc.get("email")
        return "No active email found. Run 'agent-email create' first."
    except Exception as e:
        return f"Error getting email: {str(e)}"

def read_inbox(filter_service=None):
    try:
        result = subprocess.run(["agent-email", "read", "default"], capture_output=True, text=True)
        data = json.loads(result.stdout)
        if not data.get("ok"):
            return f"Error reading inbox: {data.get('message')}"
        
        messages = data.get("data", [])
        if filter_service:
            messages = [m for m in messages if filter_service.lower() in m.get("from", {}).get("address", "").lower() or filter_service.lower() in m.get("subject", "").lower()]
        
        if not messages:
            return "Inbox is empty."
            
        summary = "Latest messages:\n"
        for m in messages[:5]:
            summary += f"- From: {m.get('from', {}).get('address')} | Subject: {m.get('subject')} | Date: {m.get('createdAt')}\n"
        return summary
    except Exception as e:
        return f"Error reading inbox: {str(e)}"

def get_verification_code(service_name):
    try:
        # Get full message content to find codes
        result = subprocess.run(["agent-email", "read", "default", "--full"], capture_output=True, text=True)
        data = json.loads(result.stdout)
        if not data.get("ok"):
            return f"Error: {data.get('message')}"
        
        messages = data.get("data", [])
        # Find latest message from service
        matching = [m for m in messages if service_name.lower() in m.get("from", {}).get("address", "").lower() or service_name.lower() in m.get("subject", "").lower()]
        
        if not matching:
            return f"No messages found from {service_name}."
            
        latest = matching[0]
        body = latest.get("body", "")
        # Search for 4-8 digit codes
        code_match = re.search(r'\b\d{4,8}\b', body)
        if code_match:
            return f"Found verification code from {service_name}: {code_match.group(0)}"
        return f"Found message from {service_name}, but no clear verification code detected. Subject: {latest.get('subject')}"
    except Exception as e:
        return f"Error extracting code: {str(e)}"

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Missing action"}))
        return

    payload = sys.argv[1]
    action = "get_email"
    service_name = None

    if payload.startswith("{"):
        try:
            data = json.loads(payload)
            action = data.get("action", "get_email")
            service_name = data.get("service_name")
        except Exception:
            pass
    else:
        action = payload

    if action == "get_email":
        msg = f"My autonomous email address is: {get_active_email()}"
    elif action == "read_inbox":
        msg = read_inbox(service_name)
    elif action == "get_verification_code":
        if not service_name:
            msg = "Error: service_name is required to find a verification code."
        else:
            msg = get_verification_code(service_name)
    else:
        msg = f"Unknown action: {action}"

    print(json.dumps({
        "status": "ok",
        "message": msg,
        "data": {"action": action, "service": service_name}
    }))

if __name__ == "__main__":
    main()
