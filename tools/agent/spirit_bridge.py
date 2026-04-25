#!/usr/bin/env python3
import asyncio
import json
import os
import socket
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Paths
AGENT_SOCKET = os.environ.get("AI_DISTRO_IPC_SOCKET", "/run/ai-distro/agent.sock")
CONFIG_PATH = os.path.expanduser("~/.config/ai-distro-spirit.json")

def load_token():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f).get("token")
    except:
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Security check: only talk to the master
    config = {}
    try:
        with open(CONFIG_PATH, "r") as f: config = json.load(f)
    except: pass
    
    if str(update.effective_chat.id) != str(config.get("master_id")):
        await update.message.reply_text("Unauthorized. Please configure your Master ID.")
        return

    user_text = update.message.text
    print(f"Spirit Bridge: Received from phone: {user_text}")
    
    # Send to local OS agent
    response = send_to_agent(user_text)
    
    await update.message.reply_text(f"[OS]: {response}")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Spirit Bridge Active. Your Chat ID is: {update.effective_chat.id}. Save this as 'master_id' in your config.")

def main():
    token = load_token()
    if not token:
        print("Spirit Bridge: No token found in ~/.config/ai-distro-spirit.json")
        sys.exit(1)

    print("Spirit Bridge: Connecting to the cloud...")
    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    app.run_polling()

if __name__ == "__main__":
    main()
