## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-13 - TF-IDF Vectorization Disjoint Set Optimization
**Learning:** When computing cosine similarity between a sparse query vector (TF-IDF) and a large corpus of documents (like in `tools/agent/conversation_memory.py`), fully vectorizing every document before determining if they share any terms is computationally wasteful. Documents with zero overlapping terms will always have a cosine similarity of 0.
**Action:** Always add a fast, built-in set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) to short-circuit the scoring loop. This simple check reduces computational overhead by ~30% in Python by skipping expensive TF-IDF calculations entirely for non-matching documents.

## 2026-06-13 - TF-IDF Vectorization: O(N) Document Frequency Lookup Bottleneck
**Learning:** In the `tools/agent/conversation_memory.py` implementation of TF-IDF, querying the entire `doc_freq` SQLite table on every search query creates a massive performance bottleneck as the vocabulary grows, turning an ostensibly indexed search into an O(N) operation over the total vocabulary size rather than scaling with document length.
**Action:** When pre-fetching values from SQLite into a Python cache (like `df_cache`), filter the query to strictly include only the values needed for the matching documents using batched `WHERE IN (...)` clauses (respecting SQLite's 999 parameter limit), rather than executing unbounded `SELECT` statements.
