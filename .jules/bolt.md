## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-13 - TF-IDF Vectorization Disjoint Set Optimization
**Learning:** When computing cosine similarity between a sparse query vector (TF-IDF) and a large corpus of documents (like in `tools/agent/conversation_memory.py`), fully vectorizing every document before determining if they share any terms is computationally wasteful. Documents with zero overlapping terms will always have a cosine similarity of 0.
**Action:** Always add a fast, built-in set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) to short-circuit the scoring loop. This simple check reduces computational overhead by ~30% in Python by skipping expensive TF-IDF calculations entirely for non-matching documents.

## 2026-06-18 - Two-Pass Vocabulary Fetching Optimization for SQLite
**Learning:** When retrieving document frequencies from an SQLite table in a TF-IDF implementation (e.g., in `tools/agent/conversation_memory.py`), pulling the entire vocabulary into memory causes a significant performance bottleneck and memory overhead as the dataset grows. Fetching frequencies individually in a loop (N+1 queries) is also slow.
**Action:** Always implement a two-pass strategy: first, filter the documents to find those sharing terms with the query and aggregate their unique terms; second, fetch the document frequencies only for this specific subset of terms using batched `IN (...)` queries (chunked by 999 to respect SQLite limits). This reduced recall time from ~0.35s to < 0.001s.
