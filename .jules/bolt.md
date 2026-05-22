## 2024-05-24 - [TF-IDF Recall DB Query Optimization]
**Learning:** Python SQLite data processing in this repo can be vulnerable to N+1 query bottlenecks (e.g., fetching document frequencies and overall document counts in a loop for each recalled token).
**Action:** Use batched queries or local dictionary caching when querying a large number of components in a loop to mitigate these performance bottlenecks.
