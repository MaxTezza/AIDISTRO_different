## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-13 - TF-IDF Vectorization Disjoint Set Optimization
**Learning:** When computing cosine similarity between a sparse query vector (TF-IDF) and a large corpus of documents (like in `tools/agent/conversation_memory.py`), fully vectorizing every document before determining if they share any terms is computationally wasteful. Documents with zero overlapping terms will always have a cosine similarity of 0.
**Action:** Always add a fast, built-in set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) to short-circuit the scoring loop. This simple check reduces computational overhead by ~30% in Python by skipping expensive TF-IDF calculations entirely for non-matching documents.

## 2026-06-25 - Python `Counter` Performance with Sparse Queries
**Learning:** When calculating term frequencies (TF) for a specific set of query terms against a large document (like in `tools/agent/file_intelligence.py`), instantiating a full `collections.Counter(doc_tokens)` is severely inefficient. The `Counter` iterates and hashes every token in the document (which could be 50k+ tokens), even though the query typically only contains 2-3 terms. Testing showed `Counter` taking ~0.64s for 50k tokens versus ~0.30s using `list.count()` for three query terms, yielding a 50% performance improvement in evaluation loops.
**Action:** When matching a small subset of known terms against a large list, use iterating over the query terms and `list.count(term)` instead of building a full frequency map of the entire list.
