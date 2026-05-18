## 2024-05-18 - Optimize SQLite N+1 query in Local RAG TF-IDF
**Learning:** In python data processing scripts, querying document frequency directly from an SQLite database for every unique term during a loop (like computing TF-IDF over hundreds of conversations) causes severe N+1 bottlenecks.
**Action:** Always utilize a memory cache dictionary (`df_cache`) and pass it throughout the loop, significantly reducing the number of SQL queries and yielding 3-4x faster processing.
