## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-13 - TF-IDF Vectorization Disjoint Set Optimization
**Learning:** When computing cosine similarity between a sparse query vector (TF-IDF) and a large corpus of documents (like in `tools/agent/conversation_memory.py`), fully vectorizing every document before determining if they share any terms is computationally wasteful. Documents with zero overlapping terms will always have a cosine similarity of 0.
**Action:** Always add a fast, built-in set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) to short-circuit the scoring loop. This simple check reduces computational overhead by ~30% in Python by skipping expensive TF-IDF calculations entirely for non-matching documents.

## 2026-06-25 - Massive Vocabulary Memory Overhead in Local RAG

**Learning:** When retrieving TF-IDF reference data (like document frequencies) from SQLite, caching the entire table into memory before a loop solves the N+1 problem, but introduces a severe memory and time bottleneck if the vocabulary grows large (e.g., thousands of unique terms). In testing `tools/agent/conversation_memory.py`, fetching 50,000 terms on every `recall` slowed the search down to ~2.7s.

**Action:** When pre-fetching reference data from SQLite for scoring loops, only fetch data for the specific IDs/terms that exist within the filtered subset of matched documents. Identify matched documents first, aggregate their unique terms, and use a batched `IN (...)` query (chunked by 999) to build a much smaller, precisely scoped cache.
