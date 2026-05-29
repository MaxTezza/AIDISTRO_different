## 2024-05-24 - N+1 SQLite queries in TF-IDF scoring loop
**Learning:** The local RAG implementation in `conversation_memory.py` had an N+1 query bottleneck. During a semantic search `recall()`, it fetched the document frequency (`doc_freq`) for each individual token inside a nested loop over all past conversations. This resulted in thousands of tiny SQLite queries and degraded performance.
**Action:** Pre-fetch full tables into memory dictionaries (`df_cache`) before iterating over rows when scoring or computing TF-IDF vectors, effectively reducing queries from O(N*M) to O(1).
