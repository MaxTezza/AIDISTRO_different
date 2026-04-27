#!/usr/bin/env python3
"""
Spirit Bridge — Telegram Remote Control for AI Distro

Allows controlling the OS from your phone via a Telegram bot.
Gracefully sleeps if telegram package or token is not available.
"""
import json
import os
import socket
import time

# Paths
AGENT_SOCKET = os.environ.get("AI_DISTRO_IPC_SOCKET", "/run/ai-distro/agent.sock")
CONFIG_PATH = os.path.expanduser("~/.config/ai-distro-spirit.json")


def load_token():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f).get("token")
    except Exception:
        return None


def send_to_agent(text):
    """Bridges phone message to OS Brain."""
    req = {"version": 1, "name": "natural_language", "payload": text}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(AGENT_SOCKET)
            client.sendall(json.dumps(req).encode('utf-8') + b"\n")
            resp = json.loads(client.recv(8192).decode('utf-8'))
            return resp.get("message", "Task complete.")
    except Exception as e:
        return f"Communication Error: {e}"


def main():
    # Phase 1: Wait for token
    token = load_token()
    if not token:
        print("Spirit Bridge: No token found in ~/.config/ai-distro-spirit.json")
        print("Spirit Bridge: Sleeping until configured. Set 'token' and restart.")
        while True:
            time.sleep(3600)
            token = load_token()
            if token:
                print("Spirit Bridge: Token found! Starting...")
                break

    # Phase 2: Wait for telegram package
    try:
        from telegram import Update
        from telegram.ext import (
            ApplicationBuilder, CommandHandler, MessageHandler,
            filters, ContextTypes
        )
    except ImportError:
        print("Spirit Bridge: python-telegram-bot not installed.")
        print("Spirit Bridge: Install with: pip install python-telegram-bot")
        print("Spirit Bridge: Sleeping until available...")
        while True:
            time.sleep(3600)
            try:
                from telegram import Update  # noqa: F811
                from telegram.ext import (  # noqa: F811
                    ApplicationBuilder, CommandHandler, MessageHandler,
                    filters, ContextTypes
                )
                print("Spirit Bridge: Package found! Starting...")
                break
            except ImportError:
                continue

    # Phase 3: Load config and run
    master_id = None
    try:
        with open(CONFIG_PATH) as f:
            master_id = json.load(f).get("master_id")
    except Exception:
        pass

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if master_id and str(update.effective_chat.id) != str(master_id):
            if update.message:
                await update.message.reply_text("Unauthorized.")
            return
        text = update.message.text if update.message else ""
        print(f"Spirit Bridge: Received from phone: {text}")
        response = send_to_agent(text)
        if update.message:
            await update.message.reply_text(f"[OS]: {response}")

    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text(
                f"Spirit Bridge Active. Your Chat ID is: {update.effective_chat.id}. "
                "Save this as 'master_id' in your config."
            )

    print("Spirit Bridge: Connecting to the cloud...")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
