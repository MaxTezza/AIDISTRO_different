## 2026-06-01 - Python SQLite N+1 Bottleneck in Local RAG

**Learning:** When evaluating performance in Python scripts interacting with an SQLite database (like in `tools/agent/conversation_memory.py`), be highly suspicious of database access within nested loops (such as iterating through terms for TF-IDF calculations across multiple documents). This structure commonly results in severe N+1 query performance degradation. In testing with 500 records, the difference was massive (from 0.26 seconds to 0.03 seconds) once the N+1 issue was patched.

**Action:** Whenever implementing or debugging data retrieval loops referencing SQLite, fetch reference data in aggregate (e.g., pulling document frequencies and total document count) and store it in a local Python dictionary `cache` *before* the loop starts.

## 2026-06-13 - TF-IDF Vectorization Disjoint Set Optimization
**Learning:** When computing cosine similarity between a sparse query vector (TF-IDF) and a large corpus of documents (like in `tools/agent/conversation_memory.py`), fully vectorizing every document before determining if they share any terms is computationally wasteful. Documents with zero overlapping terms will always have a cosine similarity of 0.
**Action:** Always add a fast, built-in set intersection check (e.g., `set(query_tokens).isdisjoint(doc_tokens)`) to short-circuit the scoring loop. This simple check reduces computational overhead by ~30% in Python by skipping expensive TF-IDF calculations entirely for non-matching documents.
## 2023-10-27 - Pre-calculate loop invariant to avoid O(N) redundant mathematical overhead
**Learning:** Found that vector magnitude for constant data (like a search query) in a similarity search loop was being repeatedly computed (sum and sqrt) for every evaluated document.
**Action:** When implementing semantic search or vector matching algorithms, always ensure to compute fixed invariants like `mag_q` (magnitude of the query vector) outside the O(N) evaluation loop to save mathematical operations per document.
## 2026-06-15 - TF-IDF Pre-calculation Optimization

**Learning:** When calculating vector similarities (like cosine similarity) against a large dataset inside a loop, computing loop invariants (e.g., the magnitude of a constant query vector) inside the loop introduces a massive redundant overhead (O(N) operations instead of O(1)).
**Action:** Always pre-calculate loop invariants outside the document scoring loop. In testing with 1000 records, pulling the query magnitude calculation outside the loop alongside the disjoint set check reduced search latency from ~0.74s to ~0.41s.
## 2026-06-25 - Python Local Variable Optimization in Inner Loops

**Learning:** When calculating values inside a Python loop that repeatedly calls a function, passing pre-calculated variables as optional arguments can avoid redundant computation, but it comes at the cost of some function overhead. However, when the logic involves simple array manipulations inside a hot loop, manually unrolling or inlining small utility methods (like cosine similarity calculations) does not inherently offer better performance than the standard C-optimized math module functions, unless a significant redundant loop traversal is removed. In fact, attempting to optimize by computing variables and injecting them into a function is often best accomplished by simply avoiding `O(N)` loop processing inside that function. I discovered that calculating the magnitude of the query vector `mag_q` once before looping over thousands of documents and passing it to the cosine similarity function prevents it from being redundantly recalculated every time, reducing search latency by ~10%.

**Action:** Identify loop invariants—values that do not change during the execution of a loop, especially mathematically expensive ones like sums or square roots of constant arrays. Calculate them once before the loop begins and pass them directly to whatever inner functions need them, to avoid redundant `O(N)` calculation penalties.
