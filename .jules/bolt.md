
## 2024-06-25 - Python SQLite N+1 Bottleneck in `conversation_memory.py`
**Learning:** Found a severe O(Docs × Terms) database query bottleneck where `_compute_tfidf` was hitting sqlite3 `SELECT count FROM doc_freq` for every single token in every single document sequentially during a semantic search.
**Action:** Always inspect loop bodies during data retrieval tasks for database calls. In Python/SQLite stacks, bulk load table dictionaries before iterating (e.g., `dict(conn.execute(...).fetchall())`) to reduce database I/O from N+1 to 1 query.
