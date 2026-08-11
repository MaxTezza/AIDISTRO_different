import re

with open("tools/agent/conversation_memory.py", "r") as f:
    content = f.read()

search = """        # OPTIMIZATION: Cache document count and term frequencies to prevent N+1 query bottleneck
        num_docs_row = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()
        num_docs = max(num_docs_row[0], 1)

        # Load doc frequencies into memory
        df_rows = conn.execute("SELECT term, count FROM doc_freq").fetchall()
        df_cache = {row[0]: row[1] for row in df_rows}

        query_vec = self._compute_tfidf(query_tokens, conn, num_docs=num_docs, df_cache=df_cache)
        query_terms = set(query_tokens)

        # Score all conversations
        rows = conn.execute(
            "SELECT id, timestamp, user_message, ai_response, context, tokens, importance "
            "FROM conversations ORDER BY timestamp DESC LIMIT 500"
        ).fetchall()

        scored = []
        for row in rows:
            doc_tokens = json.loads(row[5]) if row[5] else []
            if not doc_tokens or query_terms.isdisjoint(doc_tokens):
                continue
            doc_vec = self._compute_tfidf(doc_tokens, conn, num_docs=num_docs, df_cache=df_cache)
            sim = self._cosine_similarity(query_vec, doc_vec)
            # Boost by importance
            sim *= row[6]
            if sim > 0.05:
                scored.append({
                    "id": row[0],
                    "time": datetime.fromtimestamp(row[1]).strftime("%Y-%m-%d %H:%M"),
                    "user": row[2],
                    "ai": row[3],
                    "context": row[4],
                    "similarity": round(sim, 4),
                })

        # Also search notes
        notes = conn.execute(
            "SELECT id, timestamp, content, tokens FROM notes ORDER BY timestamp DESC LIMIT 200"
        ).fetchall()
        for note in notes:
            doc_tokens = json.loads(note[3]) if note[3] else []
            if not doc_tokens or query_terms.isdisjoint(doc_tokens):
                continue
            doc_vec = self._compute_tfidf(doc_tokens, conn, num_docs=num_docs, df_cache=df_cache)
            sim = self._cosine_similarity(query_vec, doc_vec)
            if sim > 0.05:
                scored.append({
                    "id": f"note-{note[0]}",
                    "time": datetime.fromtimestamp(note[1]).strftime("%Y-%m-%d %H:%M"),
                    "user": note[2],
                    "ai": "(stored note)",
                    "similarity": round(sim, 4),
                })"""

replace = """        # OPTIMIZATION: Prevent N+1 query bottleneck and full table scan
        num_docs_row = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()
        num_docs = max(num_docs_row[0], 1)

        query_terms = set(query_tokens)

        # Fetch candidate conversations
        rows = conn.execute(
            "SELECT id, timestamp, user_message, ai_response, context, tokens, importance "
            "FROM conversations ORDER BY timestamp DESC LIMIT 500"
        ).fetchall()

        # Fetch candidate notes
        notes = conn.execute(
            "SELECT id, timestamp, content, tokens FROM notes ORDER BY timestamp DESC LIMIT 200"
        ).fetchall()

        # ⚡ Bolt: Two-pass approach to load document frequencies for relevant terms only
        needed_terms = set(query_terms)
        matching_rows = []
        matching_notes = []

        for row in rows:
            doc_tokens = json.loads(row[5]) if row[5] else []
            if doc_tokens and not query_terms.isdisjoint(doc_tokens):
                matching_rows.append((row, doc_tokens))
                needed_terms.update(doc_tokens)

        for note in notes:
            doc_tokens = json.loads(note[3]) if note[3] else []
            if doc_tokens and not query_terms.isdisjoint(doc_tokens):
                matching_notes.append((note, doc_tokens))
                needed_terms.update(doc_tokens)

        # Batch load frequencies for needed terms (chunked to respect SQLite limits)
        df_cache = {}
        needed_terms_list = list(needed_terms)
        for i in range(0, len(needed_terms_list), 999):
            chunk = needed_terms_list[i:i+999]
            placeholders = ",".join(["?"] * len(chunk))
            df_rows = conn.execute(f"SELECT term, count FROM doc_freq WHERE term IN ({placeholders})", chunk).fetchall()
            for r in df_rows:
                df_cache[r[0]] = r[1]

        query_vec = self._compute_tfidf(query_tokens, conn, num_docs=num_docs, df_cache=df_cache)

        scored = []
        for row, doc_tokens in matching_rows:
            doc_vec = self._compute_tfidf(doc_tokens, conn, num_docs=num_docs, df_cache=df_cache)
            sim = self._cosine_similarity(query_vec, doc_vec)
            # Boost by importance
            sim *= row[6]
            if sim > 0.05:
                scored.append({
                    "id": row[0],
                    "time": datetime.fromtimestamp(row[1]).strftime("%Y-%m-%d %H:%M"),
                    "user": row[2],
                    "ai": row[3],
                    "context": row[4],
                    "similarity": round(sim, 4),
                })

        for note, doc_tokens in matching_notes:
            doc_vec = self._compute_tfidf(doc_tokens, conn, num_docs=num_docs, df_cache=df_cache)
            sim = self._cosine_similarity(query_vec, doc_vec)
            if sim > 0.05:
                scored.append({
                    "id": f"note-{note[0]}",
                    "time": datetime.fromtimestamp(note[1]).strftime("%Y-%m-%d %H:%M"),
                    "user": note[2],
                    "ai": "(stored note)",
                    "similarity": round(sim, 4),
                })"""

if search in content:
    content = content.replace(search, replace)
    with open("tools/agent/conversation_memory.py", "w") as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Search string not found")
