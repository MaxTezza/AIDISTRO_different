## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.
## 2024-06-11 - Disjoint Set Check Optimization in Search

**Learning:** When evaluating documents against a query in TF-IDF based search (like `tools/agent/file_intelligence.py`), iterating over all indexed terms and doing TF-IDF calculations for all documents is slow. Because many documents might not even contain any search terms, using a quick set `.isdisjoint()` check to compare `query_terms_set` against `doc_tokens` provides a huge performance win by avoiding math on zero-overlap records. It drops time for 50 search iterations on 1000 records from ~1.95s to ~0.05s.

**Action:** Add an early fast-path check `query_terms_set.isdisjoint(doc_tokens)` to skip completely disjoint documents in text matching and search scoring loops.
