import time
import os
from tools.agent.conversation_memory import ConversationMemory

def run_benchmark():
    db_path = "./test_memory.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    mem = ConversationMemory(db_path)

    print("Inserting 500 records...")
    for i in range(500):
        mem.store(f"user message {i} with some extra words to make it long enough to be somewhat realistic",
                 f"ai response {i} with some other words that are also quite long to increase unique tokens")

    print("Running recall...")
    start = time.time()
    mem.recall("user message extra words realistic")
    end = time.time()
    print(f"Recall took: {end - start:.4f} seconds")

if __name__ == '__main__':
    run_benchmark()
