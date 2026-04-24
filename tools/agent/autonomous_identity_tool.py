#!/usr/bin/env python3
import sys
import os
import json
import mailbox
from email import policy
from email.parser import BytesParser

IDENTITY_DIR = os.path.expanduser("~/.cache/ai-distro/identity")
MBOX_PATH = os.path.join(IDENTITY_DIR, "mailbox.mbox")
ADDRESS_FILE = os.path.join(IDENTITY_DIR, "address.txt")

def ensure_identity():
    os.makedirs(IDENTITY_DIR, exist_ok=True)
    if not os.path.exists(ADDRESS_FILE):
        # In a real setup, this would be a real domain/forwarder
        # For the demo, we generate a persistent local identity
        with open(ADDRESS_FILE, "w") as f:
            f.write("assistant@local.aidistro.os")

def get_address():
    ensure_identity()
    with open(ADDRESS_FILE, "r") as f:
        return f.read().strip()

def poll_messages():
    ensure_identity()
    messages = []
    if not os.path.exists(MBOX_PATH):
        return []
    
    mbox = mailbox.mbox(MBOX_PATH, factory=lambda f: BytesParser(policy=policy.default).parse(f))
    for msg in mbox:
        messages.append({
            "subject": msg['subject'],
            "from": msg['from'],
            "date": str(msg['date']),
            "body": msg.get_body(preferencelist=('plain')).get_content() if msg.get_body() else ""
        })
    return messages

def main():
    if len(sys.argv) < 2:
        return

    cmd = sys.argv[1]
    if cmd == "get_address":
        print(json.dumps({"address": get_address()}))
    elif cmd == "poll":
        msgs = poll_messages()
        print(json.dumps(msgs))
    elif cmd == "simulate_receive":
        # For testing: simulate an incoming verification email
        os.makedirs(IDENTITY_DIR, exist_ok=True)
        mbox = mailbox.mbox(MBOX_PATH)
        msg = mailbox.mboxMessage()
        msg['Subject'] = "Your Free Trial Code"
        msg['From'] = "services@provider.com"
        msg.set_payload("Your code is 123456. Use it to start your trial!")
        mbox.add(msg)
        mbox.flush()
        print("Simulated message received.")

if __name__ == "__main__":
    main()
