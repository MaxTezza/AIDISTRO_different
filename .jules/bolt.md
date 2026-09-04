## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG
**Learning:** When evaluating performance in Python scripts interacting with an SQLite database, be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation.
**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-13 - TF-IDF Vectorization Disjoint Set Optimization
**Learning:** When computing cosine similarity between a sparse query vector (TF-IDF) and a large corpus of documents, fully vectorizing every document before determining if they share any terms is computationally wasteful.
**Action:** Always add a fast, built-in set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) to short-circuit the scoring loop.

## 2023-10-27 - Pre-calculate loop invariant to avoid O(N) redundant mathematical overhead
**Learning:** Vector magnitude for constant data (like a search query) in a similarity search loop was being repeatedly computed (sum and sqrt) for every evaluated document.
**Action:** When implementing semantic search or vector matching algorithms, always ensure to compute fixed invariants like `mag_q` outside the O(N) evaluation loop.

## 2026-06-15 - TF-IDF Pre-calculation Optimization
**Learning:** When calculating vector similarities against a large dataset inside a loop, computing loop invariants inside the loop introduces a massive redundant overhead.
**Action:** Always pre-calculate loop invariants outside the document scoring loop.

## 2024-05-18 - SQLite N+1 Table Scan Bypass for Local RAG TF-IDF Search
**Learning:** Fetching document frequencies for ALL terms in the vocabulary via `SELECT term, count FROM doc_freq` causes massive full table scans that cripple performance when the vocabulary size scales. In our test with 50K terms, a simple search took ~0.74s because it had to load and iterate over the entire term dictionary.
**Action:** Only fetch document frequencies for terms that actually appear in matching documents. Use a two-pass approach: 1) filter candidate documents using a set disjoint check, 2) collect all unique terms from those candidates, and 3) fetch only those specific document frequencies using batched `IN (...)` SQLite clauses. This reduced search time from 0.74s to 0.08s (an 89% improvement).
