## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.
## 2026-06-04 - Python SQLite N+1 Bottleneck in Indexing (Inserts)
**Learning:** Executing database inserts or updates inside a nested `for` loop (e.g., iterating through TF-IDF document frequencies during document indexing) causes a significant N+1 performance bottleneck due to query parsing and round-trip execution for every single token.
**Action:** Use SQLite batch operations like `executemany` with a list comprehension instead of a `for` loop with individual `execute` calls whenever inserting or updating bulk properties like document frequency terms.
