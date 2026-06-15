## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-13 - TF-IDF Vectorization Disjoint Set Optimization
**Learning:** When computing cosine similarity between a sparse query vector (TF-IDF) and a large corpus of documents (like in `tools/agent/conversation_memory.py`), fully vectorizing every document before determining if they share any terms is computationally wasteful. Documents with zero overlapping terms will always have a cosine similarity of 0.
**Action:** Always add a fast, built-in set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) to short-circuit the scoring loop. This simple check reduces computational overhead by ~30% in Python by skipping expensive TF-IDF calculations entirely for non-matching documents.
## 2023-10-25 - [Cache document frequencies only for relevant documents]
**Learning:** In the Local RAG semantic search architecture using TF-IDF (`conversation_memory.py`), querying a SQLite database for document frequency metrics `doc_freq` can be extremely memory-intensive and slow if all rows are fetched. A massive query dictionary can consume a significant amount of RAM as memory accumulates.
**Action:** Use a two-pass approach. First filter and aggregate unique tokens strictly from the matched documents (`query_terms.isdisjoint(doc_tokens)`) and only request chunked term frequencies for the required terms from the database (`WHERE term IN (...)`).
