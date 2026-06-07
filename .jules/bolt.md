## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2024-06-07 - TF-IDF Pre-Filtering with set.isdisjoint
**Learning:** When calculating cosine similarity across thousands of documents, many documents have exactly 0 overlap with the query. Running the full TF-IDF vectorization and dot product calculation on these documents is a massive waste of CPU.
**Action:** Always cast the query terms to a `set` and use `query_set.isdisjoint(doc_tokens)` to short-circuit the math when there is no overlap. This simple O(N) check can reduce search time by 40-50% in sparse search spaces.
