#!/usr/bin/env python3
"""
AI Distro — Conversation Memory (Local RAG)

Stores, indexes, and semantically retrieves past conversations so the AI
remembers what you've talked about. Uses TF-IDF for zero-dependency semantic
search with SQLite persistence.

Architecture:
  - Every AI interaction is stored with timestamp and context
  - TF-IDF vectorization enables semantic similarity search
  - Retrieval returns the most relevant past conversations
  - Memory is injected into the AI system prompt for continuity

Usage:
  python3 conversation_memory.py store "user said X" "ai said Y"
  python3 conversation_memory.py recall "that thing about taxes"
  python3 conversation_memory.py recent [n]
  python3 conversation_memory.py stats
  python3 conversation_memory.py clear
"""
import json
import math
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.path.expanduser("~/.cache/ai-distro/memory.db"))
MAX_CONTEXT_TOKENS = 2000  # Approximate limit for prompt injection
STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could i me my we our you your he she it they them "
    "this that these those am to in for on with at by from of and but or not no "
    "so if then else than too very just about also how what when where which who "
    "all each every both few more most other some such".split()
)


class ConversationMemory:
    """Local conversation memory with TF-IDF semantic search."""

    def __init__(self, db_path=None):
        self.db_path = str(db_path or DB_PATH)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            context TEXT,
            tokens TEXT,
            importance REAL DEFAULT 1.0
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            content TEXT NOT NULL,
            tokens TEXT,
            source TEXT DEFAULT 'user'
        )""")
        # Document frequency table for IDF
        c.execute("""CREATE TABLE IF NOT EXISTS doc_freq (
            term TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )""")
        conn.commit()
        conn.close()

    def _tokenize(self, text):
        """Simple tokenizer: lowercase, split, remove stop words and short tokens."""
        text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        return [w for w in text.split() if w not in STOP_WORDS and len(w) > 2]

    def _update_doc_freq(self, tokens, conn):
        """Update document frequency for IDF computation."""
        unique_terms = set(tokens)
        for term in unique_terms:
            conn.execute(
                "INSERT INTO doc_freq (term, count) VALUES (?, 1) "
                "ON CONFLICT(term) DO UPDATE SET count = count + 1",
                (term,)
            )

    def _compute_tfidf(self, tokens, conn, doc_freq_cache=None, num_docs=None):
        """Compute TF-IDF vector for a set of tokens."""
        tf = Counter(tokens)
        total = len(tokens) or 1

        if num_docs is None:
            # Get total document count
            row = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()
            num_docs = max(row[0], 1)

        vector = {}
        for term, count in tf.items():
            # TF: normalized by document length
            term_freq = count / total

            # IDF: log(N / df)
            if doc_freq_cache is not None and term in doc_freq_cache:
                doc_freq = doc_freq_cache[term]
            else:
                df_row = conn.execute(
                    "SELECT count FROM doc_freq WHERE term = ?", (term,)
                ).fetchone()
                doc_freq = df_row[0] if df_row else 1
                if doc_freq_cache is not None:
                    doc_freq_cache[term] = doc_freq

            idf = math.log(num_docs / doc_freq) + 1.0
            vector[term] = term_freq * idf
        return vector

    def _cosine_similarity(self, vec_a, vec_b):
        """Compute cosine similarity between two sparse vectors (dicts)."""
        common = set(vec_a.keys()) & set(vec_b.keys())
        if not common:
            return 0.0
        dot = sum(vec_a[k] * vec_b[k] for k in common)
        mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    # ── Public API ──────────────────────────────────────────────

    def store(self, user_message, ai_response, context=None, importance=1.0):
        """Store a conversation turn."""
        combined = f"{user_message} {ai_response}"
        tokens = self._tokenize(combined)
        now = datetime.now().timestamp()

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO conversations (timestamp, user_message, ai_response, context, tokens, importance) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (now, user_message, ai_response, context, json.dumps(tokens), importance)
        )
        self._update_doc_freq(tokens, conn)
        conn.commit()
        conn.close()

        return {"status": "ok", "tokens": len(tokens)}

    def store_note(self, content, source="user"):
        """Store a standalone note/fact for later recall."""
        tokens = self._tokenize(content)
        now = datetime.now().timestamp()

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO notes (timestamp, content, tokens, source) VALUES (?, ?, ?, ?)",
            (now, content, json.dumps(tokens), source)
        )
        conn.commit()
        conn.close()
        return {"status": "ok"}

    def recall(self, query, top_k=5):
        """Semantic search: find conversations most similar to query."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        conn = sqlite3.connect(self.db_path)

        row = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()
        num_docs = max(row[0], 1)

        # First read all tokens to allow bulk fetching of document frequencies
        rows = conn.execute(
            "SELECT id, timestamp, user_message, ai_response, context, tokens, importance "
            "FROM conversations ORDER BY timestamp DESC LIMIT 500"
        ).fetchall()

        notes = conn.execute(
            "SELECT id, timestamp, content, tokens FROM notes ORDER BY timestamp DESC LIMIT 200"
        ).fetchall()

        # Keep track of parsed tokens for each doc and collect all terms
        parsed_docs = []
        all_terms = set(query_tokens)

        for r in rows:
            t = json.loads(r[5]) if r[5] else []
            if t:
                all_terms.update(t)
                parsed_docs.append(('conv', r, t))

        for n in notes:
            t = json.loads(n[3]) if n[3] else []
            if t:
                all_terms.update(t)
                parsed_docs.append(('note', n, t))

        # Bulk fetch document frequencies for all required terms
        doc_freq_cache = {}
        if all_terms:
            terms_list = list(all_terms)
            batch_size = 900 # SQLite limits variables in IN clause
            for i in range(0, len(terms_list), batch_size):
                batch = terms_list[i:i+batch_size]
                placeholders = ','.join(['?'] * len(batch))
                cursor = conn.execute(
                    f"SELECT term, count FROM doc_freq WHERE term IN ({placeholders})", batch
                )
                for term, count in cursor.fetchall():
                    doc_freq_cache[term] = count

        query_vec = self._compute_tfidf(query_tokens, conn, doc_freq_cache, num_docs)

        scored = []
        for doc_type, data, doc_tokens in parsed_docs:
            doc_vec = self._compute_tfidf(doc_tokens, conn, doc_freq_cache, num_docs)
            sim = self._cosine_similarity(query_vec, doc_vec)

            if doc_type == 'conv':
                # Boost by importance
                sim *= data[6]

            if sim > 0.05:
                scored.append({
                    "id": data[0] if doc_type == 'conv' else f"note-{data[0]}",
                    "time": data[1],
                    "user": data[2],
                    "ai": data[3] if doc_type == 'conv' else "(stored note)",
                    "context": data[4] if doc_type == 'conv' else None,
                    "similarity": round(sim, 4),
                })
                # Remove context from notes for structure match
                if doc_type == 'note':
                    del scored[-1]["context"]

        conn.close()

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        top_scored = scored[:top_k]

        for item in top_scored:
             item["time"] = datetime.fromtimestamp(item["time"]).strftime("%Y-%m-%d %H:%M")

        return top_scored

    def recent(self, n=10):
        """Get the N most recent conversations."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT id, timestamp, user_message, ai_response, context "
            "FROM conversations ORDER BY timestamp DESC LIMIT ?", (n,)
        ).fetchall()
        conn.close()
        return [{
            "id": r[0],
            "time": datetime.fromtimestamp(r[1]).strftime("%Y-%m-%d %H:%M"),
            "user": r[2], "ai": r[3], "context": r[4],
        } for r in rows]

    def get_prompt_context(self, current_query=None, max_chars=MAX_CONTEXT_TOKENS * 4):
        """
        Build a memory context block for injection into the AI system prompt.
        Includes recent history + relevant recalled memories.
        """
        lines = []

        # Recent conversations (last 3)
        recents = self.recent(3)
        if recents:
            lines.append("RECENT CONVERSATION HISTORY:")
            for r in reversed(recents):
                lines.append(f"  [{r['time']}] User: {r['user'][:100]}")
                lines.append(f"  [{r['time']}] AI: {r['ai'][:100]}")

        # Semantic recall if we have a query
        if current_query:
            recalled = self.recall(current_query, top_k=3)
            if recalled:
                lines.append("\nRELEVANT PAST CONVERSATIONS:")
                for r in recalled:
                    lines.append(f"  [{r['time']}] (similarity: {r['similarity']}) User: {r['user'][:100]}")
                    if r['ai'] != "(stored note)":
                        lines.append(f"  [{r['time']}] AI: {r['ai'][:100]}")

        result = "\n".join(lines)
        return result[:max_chars]

    def stats(self):
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        convos = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        notes_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        terms = conn.execute("SELECT COUNT(*) FROM doc_freq").fetchone()[0]
        oldest = conn.execute("SELECT MIN(timestamp) FROM conversations").fetchone()[0]
        newest = conn.execute("SELECT MAX(timestamp) FROM conversations").fetchone()[0]
        conn.close()
        return {
            "conversations": convos,
            "notes": notes_count,
            "unique_terms": terms,
            "since": datetime.fromtimestamp(oldest).isoformat() if oldest else None,
            "latest": datetime.fromtimestamp(newest).isoformat() if newest else None,
        }

    def clear(self):
        """Wipe all conversation memory."""
        conn = sqlite3.connect(self.db_path)
        for table in ["conversations", "notes", "doc_freq"]:
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.close()
        return {"status": "ok", "message": "All memory cleared"}


def main():
    mem = ConversationMemory()

    if len(sys.argv) < 2:
        print("Usage: conversation_memory.py <store|recall|recent|stats|clear>")
        return

    cmd = sys.argv[1]

    if cmd == "store":
        user_msg = sys.argv[2] if len(sys.argv) > 2 else ""
        ai_msg = sys.argv[3] if len(sys.argv) > 3 else ""
        print(json.dumps(mem.store(user_msg, ai_msg), indent=2))

    elif cmd == "note":
        content = " ".join(sys.argv[2:])
        print(json.dumps(mem.store_note(content), indent=2))

    elif cmd == "recall":
        query = " ".join(sys.argv[2:])
        results = mem.recall(query)
        print(json.dumps(results, indent=2))

    elif cmd == "recent":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(json.dumps(mem.recent(n), indent=2))

    elif cmd == "context":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
        print(mem.get_prompt_context(query))

    elif cmd == "stats":
        print(json.dumps(mem.stats(), indent=2))

    elif cmd == "clear":
        print(json.dumps(mem.clear(), indent=2))

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
