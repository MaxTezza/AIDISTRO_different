import time
import os
import sqlite3
import json
import math
from collections import Counter
from tools.agent.conversation_memory import ConversationMemory

class OptimizedConversationMemory(ConversationMemory):
    def _compute_tfidf(self, tokens, conn=None, num_docs=None, doc_freqs=None):
        tf = Counter(tokens)
        total = len(tokens) or 1

        if num_docs is None and conn is not None:
            row = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()
            num_docs = max(row[0], 1)
        elif num_docs is None:
            num_docs = 1

        vector = {}
        for term, count in tf.items():
            term_freq = count / total
            if doc_freqs is not None:
                doc_freq = doc_freqs.get(term, 1)
            elif conn is not None:
                df_row = conn.execute("SELECT count FROM doc_freq WHERE term = ?", (term,)).fetchone()
                doc_freq = df_row[0] if df_row else 1
            else:
                doc_freq = 1

            idf = math.log(num_docs / doc_freq) + 1.0
            vector[term] = term_freq * idf
        return vector

    def recall(self, query, top_k=5):
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        conn = sqlite3.connect(self.db_path)

        row = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()
        num_docs = max(row[0], 1)
        doc_freqs = {r[0]: r[1] for r in conn.execute("SELECT term, count FROM doc_freq").fetchall()}

        query_vec = self._compute_tfidf(query_tokens, num_docs=num_docs, doc_freqs=doc_freqs)

        rows = conn.execute(
            "SELECT id, timestamp, user_message, ai_response, context, tokens, importance "
            "FROM conversations ORDER BY timestamp DESC LIMIT 500"
        ).fetchall()

        scored = []
        for row in rows:
            doc_tokens = json.loads(row[5]) if row[5] else []
            if not doc_tokens:
                continue
            doc_vec = self._compute_tfidf(doc_tokens, num_docs=num_docs, doc_freqs=doc_freqs)
            sim = self._cosine_similarity(query_vec, doc_vec)
            sim *= row[6]
            if sim > 0.05:
                scored.append({"id": row[0], "similarity": round(sim, 4)})

        notes = conn.execute(
            "SELECT id, timestamp, content, tokens FROM notes ORDER BY timestamp DESC LIMIT 200"
        ).fetchall()
        for note in notes:
            doc_tokens = json.loads(note[3]) if note[3] else []
            if not doc_tokens:
                continue
            doc_vec = self._compute_tfidf(doc_tokens, num_docs=num_docs, doc_freqs=doc_freqs)
            sim = self._cosine_similarity(query_vec, doc_vec)
            if sim > 0.05:
                scored.append({"id": f"note-{note[0]}", "similarity": round(sim, 4)})

        conn.close()

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]

def run_benchmark():
    db_path = "./test_memory.db"

    # Existing setup from previous bench
    mem_old = ConversationMemory(db_path)
    mem_new = OptimizedConversationMemory(db_path)

    print("Running recall with old...")
    start = time.time()
    mem_old.recall("user message extra words realistic")
    end = time.time()
    print(f"Old recall took: {end - start:.4f} seconds")

    print("Running recall with new...")
    start = time.time()
    mem_new.recall("user message extra words realistic")
    end = time.time()
    print(f"New recall took: {end - start:.4f} seconds")

if __name__ == '__main__':
    run_benchmark()
