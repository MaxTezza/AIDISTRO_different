## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.
## 2024-06-10 - [Short-circuit tf-idf vectorization]
**Learning:** [TF-IDF similarity loops can be significantly slowed down by vectorizing documents that have zero overlapping terms with the query. Python's built-in set operations are highly optimized.]
**Action:** [Use `set(query_terms).isdisjoint(doc_tokens)` as a fast short-circuit check before performing expensive `Counter` initializations or dictionary lookups in local semantic search implementations.]
