## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-01 - Avoid Expensive Vector Operations for Completely Disjoint Sets in NLP

**Learning:** When evaluating textual documents against a query using TF-IDF and Cosine Similarity, computing document vectors for records that share no common tokens with the search query is a waste of processing time (because dot product will always be 0).
**Action:** Always pre-compute a set of query terms (`query_terms_set = set(query_tokens)`) before scanning over documents, and use `.isdisjoint()` against document token lists to short-circuit the processing loop (`if query_terms_set.isdisjoint(doc_tokens): continue`), avoiding expensive vector construction entirely.
