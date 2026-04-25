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
        self.last_suggestion_slot = None
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

    def check_system(self):
        # Battery check
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            if percent <= 15 and self.last_battery_alert > 15:
                self.send_proactive_request("low_battery", f"Battery is at {percent}%. Enable power saving?")
                self.last_battery_alert = 15
            elif percent > 15:
                self.last_battery_alert = percent

        # Disk space check
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
             self.send_proactive_request("low_disk", f"Your main drive is {disk.percent}% full. Want me to find files to archive?")

    def check_time_and_events(self):
        now = datetime.now()
        hour = now.hour

        # Morning Briefing (7 AM - 10 AM)
        if 7 <= hour <= 10 and not self.sent_morning_briefing:
            try:
                res = subprocess.run([sys.executable, DAY_PLANNER_SCRIPT, "today"], capture_output=True, text=True)
                briefing = res.stdout.strip() or "Good morning!"
                self.send_proactive_request("morning_briefing", briefing)
                self.sent_morning_briefing = True
            except Exception:
                pass
        elif hour > 10:
            self.sent_morning_briefing = False 

        # Habit Suggestion
        suggestion = self.get_proactive_suggestion()
        if suggestion:
            slot = (now.year, now.month, now.day, now.hour)
            if self.last_suggestion_slot != slot:
                self.send_proactive_request("habit_suggestion", suggestion)
                self.last_suggestion_slot = slot

    def check_health(self):
        """Checks for failed system services."""
        try:
            res = subprocess.run(["systemctl", "--failed", "--quiet"], capture_output=True)
            if res.returncode != 0:
                self.send_proactive_request("system_health", "I noticed some system services failed. Should I run a diagnostic?")
        except Exception:
            pass

    def check_health_reminders(self):
        """Sends periodic reminders for medication, hydration, or movement."""
        now = datetime.now()
        if now.minute == 0:
            if now.hour == 9:
                self.send_proactive_request("health_reminder", "Time for your morning medication.")
            elif now.hour == 13:
                self.send_proactive_request("health_reminder", "Don't forget to stay hydrated!")
            elif now.hour == 20:
                self.send_proactive_request("health_reminder", "Evening routine time.")

    def run(self):
        print("Curator Engine (The Intuition) started.")
        while True:
            try:
                self.check_system()
                self.check_time_and_events()
                self.check_health()
                self.check_health_reminders()
            except Exception as e:
                print(f"Curator loop error: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    curator = Curator()
    if len(sys.argv) > 2 and sys.argv[1] == "log_habit":
        curator.log_habit(sys.argv[2])
    else:
        curator.run()
