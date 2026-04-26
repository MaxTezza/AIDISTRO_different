#!/usr/bin/env python3
"""
Bayesian Preference Engine for AI Distro.

Uses Beta-Binomial conjugate priors to model user preferences across multiple
dimensions: time-of-day, day-of-week, app context, and action chains. The engine
learns from every user interaction and can predict what the user likely wants
at any given moment.

Architecture:
  - Each (context, action) pair gets a Beta(α, β) distribution
  - α increments on positive interaction, β on rejection/ignore
  - Posterior predictive = α / (α + β)
  - Decay factor applies to old data so the system stays responsive to change
"""
import json
import math
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.path.expanduser("~/.cache/ai-distro/bayesian.db"))
DECAY_HALF_LIFE_DAYS = 14  # How fast old habits lose weight
MIN_OBSERVATIONS = 3  # Minimum interactions before making predictions
CONFIDENCE_THRESHOLD = 0.65  # Minimum posterior to suggest an action


class BayesianEngine:
    """Bayesian preference tracker using Beta-Binomial conjugate priors."""

    def __init__(self, db_path=None):
        self.db_path = str(db_path or DB_PATH)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Core beliefs table: Beta(alpha, beta) per context-action pair
        c.execute("""CREATE TABLE IF NOT EXISTS beliefs (
            context_key TEXT NOT NULL,
            action TEXT NOT NULL,
            alpha REAL DEFAULT 1.0,
            beta REAL DEFAULT 1.0,
            last_updated REAL DEFAULT 0,
            total_observations INTEGER DEFAULT 0,
            UNIQUE(context_key, action)
        )""")

        # Interaction log for audit and decay computation
        c.execute("""CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            context_key TEXT NOT NULL,
            action TEXT NOT NULL,
            outcome TEXT NOT NULL,
            metadata TEXT
        )""")

        # User preference profiles (learned over time)
        c.execute("""CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            last_updated REAL DEFAULT 0
        )""")

        # Action chains: sequences of actions the user commonly performs
        c.execute("""CREATE TABLE IF NOT EXISTS action_chains (
            prev_action TEXT NOT NULL,
            next_action TEXT NOT NULL,
            alpha REAL DEFAULT 1.0,
            beta REAL DEFAULT 1.0,
            count INTEGER DEFAULT 0,
            UNIQUE(prev_action, next_action)
        )""")

        conn.commit()
        conn.close()

    def _decay_factor(self, last_updated):
        """Exponential decay: recent data matters more than old data."""
        if last_updated == 0:
            return 1.0
        age_days = (time.time() - last_updated) / 86400
        return math.exp(-0.693 * age_days / DECAY_HALF_LIFE_DAYS)

    def _context_key(self, hour=None, dow=None, app_context=None):
        """Build a hierarchical context key."""
        now = datetime.now()
        h = hour if hour is not None else now.hour
        d = dow if dow is not None else now.weekday()
        # Time buckets: early_morning(5-8), morning(9-11), afternoon(12-16),
        # evening(17-20), night(21-4)
        if 5 <= h <= 8:
            time_bucket = "early_morning"
        elif 9 <= h <= 11:
            time_bucket = "morning"
        elif 12 <= h <= 16:
            time_bucket = "afternoon"
        elif 17 <= h <= 20:
            time_bucket = "evening"
        else:
            time_bucket = "night"

        day_type = "weekday" if d < 5 else "weekend"
        parts = [time_bucket, day_type]
        if app_context:
            parts.append(app_context)
        return "|".join(parts)

    def observe(self, action, outcome="positive", app_context=None, metadata=None):
        """
        Record an observation. This is the main learning entry point.

        outcome: "positive" (user did/accepted), "negative" (user rejected/ignored)
        """
        ctx = self._context_key(app_context=app_context)
        now = time.time()

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Update Beta distribution
        c.execute(
            "SELECT alpha, beta, last_updated FROM beliefs WHERE context_key = ? AND action = ?",
            (ctx, action),
        )
        row = c.fetchone()

        if row:
            alpha, beta_val, last_upd = row
            # Apply decay to existing parameters
            decay = self._decay_factor(last_upd)
            alpha = max(1.0, alpha * decay)
            beta_val = max(1.0, beta_val * decay)

            if outcome == "positive":
                alpha += 1.0
            else:
                beta_val += 1.0

            c.execute(
                """UPDATE beliefs SET alpha = ?, beta = ?, last_updated = ?,
                   total_observations = total_observations + 1
                   WHERE context_key = ? AND action = ?""",
                (alpha, beta_val, now, ctx, action),
            )
        else:
            alpha = 2.0 if outcome == "positive" else 1.0
            beta_val = 1.0 if outcome == "positive" else 2.0
            c.execute(
                """INSERT INTO beliefs (context_key, action, alpha, beta, last_updated, total_observations)
                   VALUES (?, ?, ?, ?, ?, 1)""",
                (ctx, action, alpha, beta_val, now),
            )

        # Log interaction
        c.execute(
            "INSERT INTO interactions (timestamp, context_key, action, outcome, metadata) VALUES (?, ?, ?, ?, ?)",
            (now, ctx, action, outcome, json.dumps(metadata) if metadata else None),
        )

        conn.commit()
        conn.close()

    def observe_chain(self, prev_action, next_action):
        """Record a sequential action chain (A → B)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """INSERT INTO action_chains (prev_action, next_action, alpha, count)
               VALUES (?, ?, 2.0, 1)
               ON CONFLICT(prev_action, next_action)
               DO UPDATE SET alpha = alpha + 1.0, count = count + 1""",
            (prev_action, next_action),
        )
        conn.commit()
        conn.close()

    def predict(self, app_context=None, top_k=3):
        """
        Predict what the user likely wants right now.

        Returns: list of (action, probability, confidence) tuples
        """
        ctx = self._context_key(app_context=app_context)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Get all beliefs for current context
        c.execute(
            "SELECT action, alpha, beta, last_updated, total_observations FROM beliefs WHERE context_key = ?",
            (ctx,),
        )
        rows = c.fetchall()
        conn.close()

        predictions = []
        for action, alpha, beta_val, last_upd, total_obs in rows:
            if total_obs < MIN_OBSERVATIONS:
                continue

            # Apply decay
            decay = self._decay_factor(last_upd)
            a = max(1.0, alpha * decay)
            b = max(1.0, beta_val * decay)

            # Posterior predictive (mean of Beta distribution)
            posterior = a / (a + b)

            # Confidence: how much data we have (entropy-based)
            confidence = 1.0 - (1.0 / math.log2(total_obs + 2))

            if posterior >= CONFIDENCE_THRESHOLD:
                predictions.append(
                    {
                        "action": action,
                        "probability": round(posterior, 3),
                        "confidence": round(confidence, 3),
                        "observations": total_obs,
                    }
                )

        # Sort by probability * confidence
        predictions.sort(key=lambda x: x["probability"] * x["confidence"], reverse=True)
        return predictions[:top_k]

    def predict_next(self, last_action, top_k=3):
        """Predict the next action based on action chains."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT next_action, alpha, beta, count FROM action_chains WHERE prev_action = ? ORDER BY alpha DESC LIMIT ?",
            (last_action, top_k),
        )
        rows = c.fetchall()
        conn.close()

        results = []
        for next_act, alpha, beta_val, count in rows:
            if count < 2:
                continue
            prob = alpha / (alpha + beta_val)
            results.append(
                {"action": next_act, "probability": round(prob, 3), "chain_count": count}
            )
        return results

    def set_preference(self, key, value, confidence=0.8):
        """Explicitly set a user preference (e.g., 'theme' → 'dark')."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """INSERT INTO preferences (key, value, confidence, last_updated)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = ?, confidence = ?, last_updated = ?""",
            (key, value, confidence, time.time(), value, confidence, time.time()),
        )
        conn.commit()
        conn.close()

    def get_preference(self, key, default=None):
        """Get a learned or explicit preference."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT value, confidence FROM preferences WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        if row:
            return {"value": row[0], "confidence": row[1]}
        return {"value": default, "confidence": 0.0}

    def get_user_profile(self):
        """Generate a complete user behavior profile for the AI system prompt."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Top actions overall
        c.execute(
            """SELECT action, SUM(total_observations) as total
               FROM beliefs GROUP BY action ORDER BY total DESC LIMIT 10"""
        )
        top_actions = [{"action": r[0], "count": r[1]} for r in c.fetchall()]

        # Time-of-day patterns
        c.execute(
            """SELECT context_key, action, alpha, beta, total_observations
               FROM beliefs WHERE total_observations >= 3
               ORDER BY (alpha / (alpha + beta)) DESC LIMIT 20"""
        )
        patterns = []
        for ctx, action, alpha, beta_val, count in c.fetchall():
            prob = alpha / (alpha + beta_val)
            patterns.append(
                {"context": ctx, "action": action, "probability": round(prob, 3), "count": count}
            )

        # All explicit preferences
        c.execute("SELECT key, value, confidence FROM preferences")
        prefs = {r[0]: {"value": r[1], "confidence": r[2]} for r in c.fetchall()}

        conn.close()

        return {
            "top_actions": top_actions,
            "behavioral_patterns": patterns,
            "preferences": prefs,
        }

    def get_adaptive_prompt_context(self):
        """Generate context string for injection into the AI system prompt."""
        profile = self.get_user_profile()
        predictions = self.predict(top_k=5)

        lines = []

        if profile["preferences"]:
            lines.append("USER PREFERENCES:")
            for k, v in profile["preferences"].items():
                lines.append(f"  - {k}: {v['value']} (confidence: {v['confidence']:.0%})")

        if predictions:
            lines.append("\nPREDICTED USER INTENT (right now):")
            for p in predictions:
                lines.append(
                    f"  - {p['action']}: {p['probability']:.0%} likely ({p['observations']} observations)"
                )

        if profile["behavioral_patterns"][:5]:
            lines.append("\nLEARNED BEHAVIORAL PATTERNS:")
            for bp in profile["behavioral_patterns"][:5]:
                lines.append(
                    f"  - During {bp['context']}: {bp['action']} ({bp['probability']:.0%}, n={bp['count']})"
                )

        return "\n".join(lines) if lines else ""


def main():
    engine = BayesianEngine()

    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: bayesian_engine.py <command> [args]"}))
        return

    cmd = sys.argv[1]

    if cmd == "observe":
        # observe <action> [outcome] [app_context]
        action = sys.argv[2] if len(sys.argv) > 2 else "unknown"
        outcome = sys.argv[3] if len(sys.argv) > 3 else "positive"
        app_ctx = sys.argv[4] if len(sys.argv) > 4 else None
        engine.observe(action, outcome, app_ctx)
        print(json.dumps({"status": "ok", "message": f"Observed: {action} ({outcome})"}))

    elif cmd == "observe_chain":
        prev = sys.argv[2] if len(sys.argv) > 2 else ""
        nxt = sys.argv[3] if len(sys.argv) > 3 else ""
        if prev and nxt:
            engine.observe_chain(prev, nxt)
            print(json.dumps({"status": "ok", "message": f"Chain: {prev} → {nxt}"}))

    elif cmd == "predict":
        app_ctx = sys.argv[2] if len(sys.argv) > 2 else None
        results = engine.predict(app_context=app_ctx)
        print(json.dumps(results, indent=2))

    elif cmd == "predict_next":
        last = sys.argv[2] if len(sys.argv) > 2 else ""
        results = engine.predict_next(last)
        print(json.dumps(results, indent=2))

    elif cmd == "set_preference":
        key = sys.argv[2] if len(sys.argv) > 2 else ""
        val = sys.argv[3] if len(sys.argv) > 3 else ""
        if key and val:
            engine.set_preference(key, val)
            print(json.dumps({"status": "ok", "message": f"Preference set: {key} = {val}"}))

    elif cmd == "get_preference":
        key = sys.argv[2] if len(sys.argv) > 2 else ""
        result = engine.get_preference(key)
        print(json.dumps(result))

    elif cmd == "profile":
        profile = engine.get_user_profile()
        print(json.dumps(profile, indent=2))

    elif cmd == "prompt_context":
        ctx = engine.get_adaptive_prompt_context()
        print(ctx)

    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))


if __name__ == "__main__":
    main()
