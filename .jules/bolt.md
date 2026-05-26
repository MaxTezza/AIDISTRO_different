## 2024-05-26 - N+1 SQLite queries in Python Scripts
**Learning:** Found N+1 query bottlenecks in `conversation_memory.py` and `file_intelligence.py` during search calculations looping through terms.
**Action:** Use a local dictionary cache to lookup term frequencies rather than querying DB every time.
