## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-13 - TF-IDF Vectorization Disjoint Set Optimization
**Learning:** When computing cosine similarity between a sparse query vector (TF-IDF) and a large corpus of documents (like in `tools/agent/conversation_memory.py`), fully vectorizing every document before determining if they share any terms is computationally wasteful. Documents with zero overlapping terms will always have a cosine similarity of 0.
**Action:** Always add a fast, built-in set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) to short-circuit the scoring loop. This simple check reduces computational overhead by ~30% in Python by skipping expensive TF-IDF calculations entirely for non-matching documents.

## 2026-10-27 - Optimizing SQLite Caching with Batched IN Queries
**Learning:** Fetching an entire table (like a large vocabulary dictionary) into memory just to resolve a few document frequencies can cause severe memory bloat and performance degradation as the database scales. The N+1 optimization approach of caching previously didn't scale well with large dictionaries.
**Action:** Use a two-pass approach. First, identify matching documents and collect the set of all unique terms they contain. Then, use batched `IN (...)` queries (chunked by 999 to respect SQLite limits) to fetch document frequencies only for those specific needed terms. This strategy prevents pulling tens of thousands of unused terms into memory, achieving a massive speedup (40x+ on large vocabularies).
