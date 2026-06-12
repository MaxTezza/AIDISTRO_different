## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2024-05-18 - Fast-path rejection for TF-IDF Semantic Search
**Learning:** When evaluating text documents for TF-IDF and cosine similarity scores, mathematical constraints dictate that any document sharing absolutely no terms with the query will always result in a cosine similarity of 0. Performing full TF-IDF vectorization for these documents is a waste of CPU cycles.
**Action:** Always implement a fast-path set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) before vectorizing. This turns the search effectively from O(N) where N is total documents to O(M) where M is documents with matching terms.
