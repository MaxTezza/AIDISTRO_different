#!/usr/bin/env python3
import time
import json
import socket
import os
import psutil
import subprocess
from datetime import datetime
import sys
import sqlite3

# Paths
DB_PATH = os.path.expanduser("~/.cache/ai-distro/habits.db")
DAY_PLANNER_SCRIPT = os.path.join(os.path.dirname(__file__), "day_planner.py")
AGENT_SOCKET = os.environ.get("AI_DISTRO_IPC_SOCKET", "/run/ai-distro/agent.sock")
CHECK_INTERVAL = 60  # seconds

class Curator:
    def __init__(self):
        self.last_battery_alert = 100
        self.sent_morning_briefing = False
        self.init_db()

    def init_db(self):
        """Initializes the Bayesian/Habit database."""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS habits 
                     (hour INTEGER, day_of_week INTEGER, action TEXT, count INTEGER, 
                      UNIQUE(hour, day_of_week, action))''')
        conn.commit()
        conn.close()

    def log_habit(self, action):
        """Logs an action for Bayesian learning."""
        now = datetime.now()
        hour = now.hour
        dow = now.weekday()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO habits (hour, day_of_week, action, count) 
                     VALUES (?, ?, ?, 1)
                     ON CONFLICT(hour, day_of_week, action) 
                     DO UPDATE SET count = count + 1''', (hour, dow, action))
        conn.commit()
        conn.close()

    def get_proactive_suggestion(self):
        """Simple Bayesian-like inference: what does the user usually do now?"""
        now = datetime.now()
        hour = now.hour
        dow = now.weekday()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT action FROM habits 
                     WHERE hour = ? AND day_of_week = ? AND count > 5
                     ORDER BY count DESC LIMIT 1''', (hour, dow))
        row = c.fetchone()
        conn.close()
        if row:
            return f"You usually use '{row[0]}' around this time. Shall I set that up for you?"
        return None

    def send_proactive_request(self, trigger, message):
        request = {
            "version": 1,
            "name": "proactive_suggestion",
            "payload": json.dumps({"trigger": trigger, "message": message})
        }
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(5.0)
                client.connect(AGENT_SOCKET)
                client.sendall(json.dumps(request).encode('utf-8') + b"\n")
        except Exception as e:
            print(f"Curator IPC Error: {e}")

    def run(self):
        print("Curator Engine (The Intuition with Bayesian Habits) started.")
        while True:
            try:
                # 1. System Health
                battery = psutil.sensors_battery()
                if battery and battery.percent <= 15 and self.last_battery_alert > 15:
                    self.send_proactive_request("low_battery", f"Battery is at {battery.percent}%. Enable power saving?")
                    self.last_battery_alert = 15
                
                # 2. Habit Learning
                habit_suggestion = self.get_proactive_suggestion()
                if habit_suggestion:
                    self.send_proactive_request("habit_insight", habit_suggestion)

                # 3. Morning Briefing
                now = datetime.now()
                if 7 <= now.hour <= 10 and not self.sent_morning_briefing:
                    res = subprocess.run([sys.executable, DAY_PLANNER_SCRIPT, "today"], capture_output=True, text=True)
                    self.send_proactive_request("morning_briefing", res.stdout.strip() or "Good morning!")
                    self.sent_morning_briefing = True
            
            except Exception as e:
                print(f"Curator error: {e}")
            
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    curator = Curator()
    if len(sys.argv) > 2 and sys.argv[1] == "log_habit":
        curator.log_habit(sys.argv[2])
    else:
        curator.run()
