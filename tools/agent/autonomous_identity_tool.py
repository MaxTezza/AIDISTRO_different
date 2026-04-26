#!/usr/bin/env python3
"""
Autonomous Identity Tool — Manages a local email identity and mailbox.

Provides the AI agent with a persistent local mailbox identity using
the standard Python mbox format. Mail can arrive via local SMTP relay,
fetchmail, or direct file delivery.

Usage:
  python3 autonomous_identity_tool.py get_address
  python3 autonomous_identity_tool.py poll
  python3 autonomous_identity_tool.py deliver <from> <subject> <body>
"""
import json
import mailbox
import os
import socket
import sys
from email import policy
from email.parser import BytesParser

IDENTITY_DIR = os.path.expanduser("~/.cache/ai-distro/identity")
MBOX_PATH = os.path.join(IDENTITY_DIR, "mailbox.mbox")
ADDRESS_FILE = os.path.join(IDENTITY_DIR, "address.txt")


def ensure_identity():
    """Create the identity directory and generate a persistent address."""
    os.makedirs(IDENTITY_DIR, exist_ok=True)
    if not os.path.exists(ADDRESS_FILE):
        hostname = socket.gethostname() or "localhost"
        username = os.environ.get("USER", "assistant")
        address = f"{username}@{hostname}.aidistro.local"
        with open(ADDRESS_FILE, "w") as f:
            f.write(address)


def get_address():
    """Return the agent's persistent email address."""
    ensure_identity()
    with open(ADDRESS_FILE, "r") as f:
        return f.read().strip()


def poll_messages():
    """Read all messages from the local mbox mailbox."""
    ensure_identity()
    messages = []
    if not os.path.exists(MBOX_PATH):
        return []

    mbox = mailbox.mbox(
        MBOX_PATH,
        factory=lambda f: BytesParser(policy=policy.default).parse(f),
    )
    for msg in mbox:
        body = ""
        body_part = msg.get_body(preferencelist=("plain",))
        if body_part:
            try:
                body = body_part.get_content()
            except Exception:
                body = str(body_part)

        messages.append({
            "subject": str(msg.get("subject", "(no subject)")),
            "from": str(msg.get("from", "unknown")),
            "date": str(msg.get("date", "")),
            "body": body[:2000],
        })
    return messages


def deliver_message(sender, subject, body_text):
    """Deliver a message into the local mbox mailbox.

    This is the programmatic delivery endpoint. External systems (fetchmail,
    procmail, or a local SMTP relay) can call this to deposit mail.
    """
    os.makedirs(IDENTITY_DIR, exist_ok=True)
    mbox = mailbox.mbox(MBOX_PATH)
    msg = mailbox.mboxMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = get_address()
    msg.set_payload(body_text)
    mbox.add(msg)
    mbox.flush()
    mbox.close()
    return {"status": "ok", "message": f"Delivered message from {sender}"}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Usage: autonomous_identity_tool.py <get_address|poll|deliver>"}))
        return

    cmd = sys.argv[1]

    if cmd == "get_address":
        print(json.dumps({"address": get_address()}))

    elif cmd == "poll":
        msgs = poll_messages()
        print(json.dumps(msgs))

    elif cmd == "deliver":
        if len(sys.argv) < 5:
            print(json.dumps({"status": "error", "message": "Usage: deliver <from> <subject> <body>"}))
            return
        sender = sys.argv[2]
        subject = sys.argv[3]
        body = " ".join(sys.argv[4:])
        result = deliver_message(sender, subject, body)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown command: {cmd}"}))


if __name__ == "__main__":
    main()
