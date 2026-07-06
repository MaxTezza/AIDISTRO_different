## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-13 - TF-IDF Vectorization Disjoint Set Optimization
**Learning:** When computing cosine similarity between a sparse query vector (TF-IDF) and a large corpus of documents (like in `tools/agent/conversation_memory.py`), fully vectorizing every document before determining if they share any terms is computationally wasteful. Documents with zero overlapping terms will always have a cosine similarity of 0.
**Action:** Always add a fast, built-in set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) to short-circuit the scoring loop. This simple check reduces computational overhead by ~30% in Python by skipping expensive TF-IDF calculations entirely for non-matching documents.

## 2026-06-25 - Disjoint Set Optimization Empty Query Trap
**Learning:** When applying the `isdisjoint` optimization to skip documents with zero term overlap, an empty query string evaluates to an empty `query_terms_set`. In Python, `set().isdisjoint(...)` always returns `True`. This causes the optimization to unintentionally skip all documents for empty queries (e.g., when a user only wants to filter by metadata).
**Action:** When using `isdisjoint` for short-circuiting, always guard against empty sets: `if not doc_tokens or (query_terms_set and query_terms_set.isdisjoint(doc_tokens)):`.

## 2026-06-25 - SQLite NULL Columns and Python Math
**Learning:** In `file_intelligence.py`, SQLite metadata columns for indexed files (like `size` at `row[3]` or `modified` time at `row[4]`) can sometimes return `None` (NULL in SQL). Performing division (`row[3] / 1024`) or passing to `datetime.fromtimestamp(row[4])` without checking raises a `TypeError` and crashes the application.
**Action:** Always provide safe fallbacks for SQLite metadata columns before math or formatting operations, for example: `round((row[3] or 0) / 1024, 1)`.
