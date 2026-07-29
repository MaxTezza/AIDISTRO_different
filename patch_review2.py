with open('tools/agent/conversation_memory.py', 'r') as f:
    content = f.read()

content = content.replace(
    'if not doc_tokens or (query_terms and query_terms.isdisjoint(doc_tokens) if query_terms else False):',
    'if not doc_tokens or query_terms.isdisjoint(doc_tokens):'
)

with open('tools/agent/conversation_memory.py', 'w') as f:
    f.write(content)
