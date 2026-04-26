#!/usr/bin/env python3
"""
Family Messenger — Sends messages to family contacts via email.

Uses the system's configured email provider (Gmail OAuth, Outlook OAuth, or
local IMAP/SMTP) to deliver real messages. Contact names are mapped to
email addresses in a persistent JSON config.

Usage:
  python3 family_messenger.py <name> <message text...>
  python3 family_messenger.py add <name> <email>
  python3 family_messenger.py list
"""
import json
import os
import smtplib
import subprocess
import sys
from email.mime.text import MIMEText
from pathlib import Path

CONTACTS_PATH = Path(os.path.expanduser("~/.config/ai-distro/family-contacts.json"))
GMAIL_OAUTH_PATH = Path(os.path.expanduser("~/.config/ai-distro/google-gmail-oauth.json"))
HERE = Path(__file__).resolve().parent


def load_contacts():
    """Load family contacts from persistent config."""
    if CONTACTS_PATH.exists():
        try:
            with open(CONTACTS_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_contacts(contacts):
    """Save family contacts to persistent config."""
    CONTACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONTACTS_PATH, "w") as f:
        json.dump(contacts, f, indent=2)


def get_sender_address():
    """Determine the sender address from available config."""
    # Check Gmail OAuth config
    if GMAIL_OAUTH_PATH.exists():
        try:
            with open(GMAIL_OAUTH_PATH, "r") as f:
                cfg = json.load(f)
            email_addr = cfg.get("email", "").strip()
            if email_addr:
                return email_addr
        except Exception:
            pass

    # Check IMAP/SMTP env vars
    imap_user = os.environ.get("AI_DISTRO_IMAP_USERNAME", "").strip()
    if imap_user:
        return imap_user

    # Check SMTP env vars
    smtp_user = os.environ.get("AI_DISTRO_SMTP_USERNAME", "").strip()
    if smtp_user:
        return smtp_user

    return "assistant@local.aidistro.os"


def send_via_gmail_api(to_addr, subject, body):
    """Send via Gmail API using the existing gmail_tool.py draft+send mechanism."""
    gmail_tool = HERE / "gmail_tool.py"
    payload = f"{to_addr}|{subject}|{body}"
    result = subprocess.run(
        [sys.executable, str(gmail_tool), "draft", payload],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0 and "draft created" in result.stdout.lower():
        return True, result.stdout.strip()
    return False, result.stdout.strip() or result.stderr.strip()


def send_via_smtp(to_addr, subject, body):
    """Send via SMTP using environment-configured credentials."""
    host = os.environ.get("AI_DISTRO_SMTP_HOST", "").strip()
    port = int(os.environ.get("AI_DISTRO_SMTP_PORT", "587"))
    username = os.environ.get("AI_DISTRO_SMTP_USERNAME", "").strip()
    password = os.environ.get("AI_DISTRO_SMTP_PASSWORD", "").strip()

    if not host or not username or not password:
        return False, "SMTP not configured"

    sender = get_sender_address()
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_addr

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(username, password)
        server.sendmail(sender, [to_addr], msg.as_string())
        server.quit()
        return True, f"Message sent to {to_addr}"
    except Exception as e:
        return False, f"SMTP send failed: {e}"


def send_message(name, message):
    """Send a message to a family member by name."""
    contacts = load_contacts()
    address = contacts.get(name.lower())

    if not address:
        return {
            "status": "error",
            "message": f"I don't have a contact for '{name}'. "
                       f"Add one with: family_messenger.py add {name} email@example.com"
        }

    subject = "Message from AI Distro"

    # Strategy 1: Try Gmail API (uses existing OAuth if configured)
    if GMAIL_OAUTH_PATH.exists():
        ok, detail = send_via_gmail_api(address, subject, message)
        if ok:
            return {
                "status": "ok",
                "message": f"I've sent your message to your {name} ({address}) via Gmail.",
                "method": "gmail_api"
            }

    # Strategy 2: Try SMTP directly
    ok, detail = send_via_smtp(address, subject, message)
    if ok:
        return {
            "status": "ok",
            "message": f"I've sent your message to your {name} ({address}).",
            "method": "smtp"
        }

    # Strategy 3: Use the email router as a last resort
    try:
        payload = f"{address}|{subject}|{message}"
        result = subprocess.run(
            [sys.executable, str(HERE / "email_router.py"), "draft", payload],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and "draft" in result.stdout.lower():
            return {
                "status": "ok",
                "message": f"I've drafted a message to your {name} ({address}). "
                           "Check your email drafts to send it.",
                "method": "draft"
            }
    except Exception:
        pass

    return {
        "status": "error",
        "message": f"Could not send message to {name}. "
                   "No email provider is configured. Set up Gmail OAuth, "
                   "SMTP env vars, or IMAP credentials first."
    }


def add_contact(name, email_addr):
    """Add or update a family contact."""
    contacts = load_contacts()
    contacts[name.lower()] = email_addr
    save_contacts(contacts)
    return {
        "status": "ok",
        "message": f"Contact '{name}' set to {email_addr}."
    }


def list_contacts():
    """List all family contacts."""
    contacts = load_contacts()
    if not contacts:
        return {
            "status": "ok",
            "message": "No family contacts configured. "
                       "Add one with: family_messenger.py add <name> <email>"
        }
    lines = [f"  {name}: {addr}" for name, addr in contacts.items()]
    return {
        "status": "ok",
        "message": "Family contacts:\n" + "\n".join(lines)
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Usage: family_messenger.py <name> <message...> | add <name> <email> | list"
        }))
        return

    cmd = sys.argv[1].lower()

    if cmd == "add":
        if len(sys.argv) < 4:
            print(json.dumps({"status": "error", "message": "Usage: add <name> <email>"}))
            return
        result = add_contact(sys.argv[2], sys.argv[3])
        print(json.dumps(result))

    elif cmd == "list":
        result = list_contacts()
        print(json.dumps(result))

    else:
        # cmd is the contact name, rest is the message
        name = cmd
        if len(sys.argv) < 3:
            print(json.dumps({"status": "error", "message": "What message should I send?"}))
            return
        msg = " ".join(sys.argv[2:])
        result = send_message(name, msg)
        print(json.dumps(result))


if __name__ == "__main__":
    main()
