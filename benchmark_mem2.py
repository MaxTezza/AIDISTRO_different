import time
import os
import sqlite3
import random
import string
from tools.agent.conversation_memory import ConversationMemory

db_path = "./test_memory.db"
if os.path.exists(db_path):
    os.remove(db_path)

mem = ConversationMemory(db_path)

# populate doc_freq with huge amount of junk
conn = sqlite3.connect(db_path)
print("Inserting 500,000 dummy terms...")
conn.execute("BEGIN TRANSACTION")
for i in range(500000):
    term = ''.join(random.choices(string.ascii_lowercase, k=8))
    conn.execute("INSERT INTO doc_freq (term, count) VALUES (?, ?)", (term, random.randint(1, 100)))
conn.commit()

# add some conversations
for i in range(100):
    mem.store("taxes are bad and I hate paying them", "yes taxes are bad and you should pay them anyway")
for i in range(400):
    mem.store("other things are good", "yes other things")

start = time.time()
mem.recall("taxes")
end = time.time()
print("Recall time taken:", end - start)
