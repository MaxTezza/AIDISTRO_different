## 2023-10-27 - Pre-calculate loop invariant to avoid O(N) redundant mathematical overhead
**Learning:** Found that vector magnitude for constant data (like a search query) in a similarity search loop was being repeatedly computed (sum and sqrt) for every evaluated document.
**Action:** When implementing semantic search or vector matching algorithms, always ensure to compute fixed invariants like `mag_q` (magnitude of the query vector) outside the O(N) evaluation loop to save mathematical operations per document.

## 2026-06-13 - TF-IDF Vectorization Disjoint Set Optimization
**Learning:** When computing cosine similarity between a sparse query vector (TF-IDF) and a large corpus of documents (like in `tools/agent/conversation_memory.py`), fully vectorizing every document before determining if they share any terms is computationally wasteful. Documents with zero overlapping terms will always have a cosine similarity of 0.
**Action:** Always add a fast, built-in set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) to short-circuit the scoring loop. This simple check reduces computational overhead by ~30% in Python by skipping expensive TF-IDF calculations entirely for non-matching documents.

## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-15 - TF-IDF Pre-calculation Optimization

**Learning:** When calculating vector similarities (like cosine similarity) against a large dataset inside a loop, computing loop invariants (e.g., the magnitude of a constant query vector) inside the loop introduces a massive redundant overhead (O(N) operations instead of O(1)).
**Action:** Always pre-calculate loop invariants outside the document scoring loop. In testing with 1000 records, pulling the query magnitude calculation outside the loop alongside the disjoint set check reduced search latency from ~0.74s to ~0.41s.

## 2026-06-16 - Pre-calculate TF-IDF IDF values for query to prevent inner-loop DB hits
**Learning:** In `tools/agent/file_intelligence.py`, calculating IDF (document frequency) inside a tight loop across matching document tokens (e.g. `doc_vec[term] = tf * term_idfs[term]`) can be much faster when we pre-calculate `term_idfs` during the query setup and use the pre-calculated dictionary directly, preventing multiple redundant accesses or repeated calculations inside the loop.
**Action:** Extract repeated calculations and pre-calculate IDF properties for documents/terms outside of tight document loops.

## 2026-06-17 - Optimize inner-loop DB execution using `executemany`
**Learning:** Calling `conn.execute` inside a loop inserting 1000s of tokens, as done for document frequencies in `tools/agent/file_intelligence.py`, represents an N+1 insertion bottleneck. Replacing this with `conn.executemany` batches the insertion, reducing overhead significantly. Benchmarking on 100 documents of 500 words each reduced indexing time from ~0.45s to ~0.33s.
**Action:** Use `executemany` for batch inserts or updates inside SQLite Python code instead of looping `execute`.
