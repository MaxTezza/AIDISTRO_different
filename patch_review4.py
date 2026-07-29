with open('tools/agent/conversation_memory.py', 'r') as f:
    content = f.read()

content = content.replace(
'''        if not matched_rows and not matched_notes:
            conn.close()
            return []''',
'''        if not matched_rows and not matched_notes:
            conn.close()
            return []'''
)

with open('tools/agent/conversation_memory.py', 'w') as f:
    f.write(content)
