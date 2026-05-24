
## 2026-05-24 - [Avoid N+1 Queries in Local RAG Semantic Searches]
**Learning:** In locally implemented semantic retrieval functions (like `conversation_memory.py` utilizing basic TF-IDF on SQLite data), calculating similarities inside large query iterations without prior bulk caching invokes huge N+1 queries. Specifically, running `SELECT count FROM doc_freq WHERE term = ?` and `SELECT COUNT(*) FROM conversations` per term per document scored during RAG similarity comparisons kills search performance.
**Action:** Always extract document counts and term frequencies into memory caching via single bulk fetches (`SELECT term, count FROM doc_freq`) outside loops before running semantic RAG distance calculations over SQLite records.
