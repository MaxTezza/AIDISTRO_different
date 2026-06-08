## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-03 - Disjoint Checks in Local RAG Search Loops

**Learning:** In local TF-IDF semantic search systems processing thousands of documents, running vector space calculations or dictionary intersection loops blindly on every single document becomes a significant CPU bottleneck. Testing showed a 50% search performance improvement in Python by simply using native sets to short-circuit the math when the document has strictly zero overlapping terms with the query.

**Action:** Whenever iterating over documents to compute similarity scores (like in `tools/agent/conversation_memory.py` and `tools/agent/file_intelligence.py`), convert the query tokens to a set once, and check `query_set.isdisjoint(doc_tokens)` to early-return before doing any heavy arithmetic.
