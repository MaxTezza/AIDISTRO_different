## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.
## 2024-05-19 - [Fix N+1 bottleneck in file_intelligence.py]
**Learning:** [The `search` function in `file_intelligence.py` had an N+1 query vulnerability when repeatedly fetching document frequencies (`doc_freq`) for each term inside inner loops over potentially up to 1000 returned documents, directly impacting search performance]
**Action:** [Use batched queries or dictionary caching logic when checking database properties inside search scoring loops within SQLite data-heavy features like `file_intelligence.py`]
