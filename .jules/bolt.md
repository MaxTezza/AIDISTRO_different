## 2024-05-24 - [N+1 SQLite Queries in TF-IDF Implementation]
**Learning:** The TF-IDF implementation in `conversation_memory.py` was computing `IDF` by querying the `doc_freq` table for every single term in a document inside a loop. When scaling up to hundreds of documents during recall, this caused an N+1 query problem, taking ~11 seconds for 50 recalls.
**Action:** When calculating scores against many documents, batch-load required database counts into a memory dictionary once before the loop rather than executing individual `SELECT` statements per token.
