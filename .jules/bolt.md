## 2026-05-31 - [SQLite N+1 Queries in TFIDF Calculation]
**Learning:** [In Local RAG architectures using SQLite for document frequencies, fetching term frequencies per-token within a loop for similarity scoring causes severe N+1 bottlenecks due to repeated SQLite queries]
**Action:** [Pre-fetch document frequencies and total document counts into memory (as a dictionary and variable, respectively) before running loop-based similarity scoring (cosine similarity) to drastically improve performance and avoid redundant database accesses]
