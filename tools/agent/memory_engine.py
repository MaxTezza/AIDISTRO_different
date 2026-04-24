#!/usr/bin/env python3
import sys
import os
import json
import chromadb
from chromadb.utils import embedding_functions

MEMORY_DIR = os.path.expanduser("~/.cache/ai-distro/memory")
COLLECTION_NAME = "user_memories"

# Initialize Chroma client
client = chromadb.PersistentClient(path=MEMORY_DIR)
# Use a lightweight, local embedding function
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=embedding_func)

def remember(text):
    """Adds a new memory to the vector database."""
    import time
    memory_id = f"mem_{int(time.time())}"
    collection.add(
        documents=[text],
        ids=[memory_id],
        metadatas=[{"timestamp": time.time()}]
    )
    print(f"Stored memory: {text}")

def query(text, limit=3):
    """Searches for semantically similar memories."""
    results = collection.query(
        query_texts=[text],
        n_results=limit
    )
    # results['documents'] is a list of lists
    memories = results['documents'][0] if results['documents'] else []
    print(json.dumps(memories))

def main():
    if len(sys.argv) < 2:
        return

    cmd = sys.argv[1]
    if cmd == "remember" and len(sys.argv) > 2:
        remember(" ".join(sys.argv[2:]))
    elif cmd == "query" and len(sys.argv) > 2:
        query(" ".join(sys.argv[2:]))
    elif cmd == "list":
        # Just return the last few for context
        results = collection.get(limit=5)
        print(json.dumps(results['documents']))

if __name__ == "__main__":
    main()
