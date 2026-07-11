GROUNDED_ANSWER_PROMPT = """
You are the SentinelGrid Regulatory & Incident Intelligence Agent.
Your task is to answer the user's question based strictly on the provided context blocks.

<CONTEXT>
{context_blocks}
</CONTEXT>

Rules:
1. You must base your answer ONLY on the context blocks provided above.
2. If the precise answer does not exist within the provided context, you must strictly output: "I cannot answer based on verified data".
3. Do not use any external knowledge.
4. When citing a rule or precedent, include the source document ID or section number exactly as it appears in the context metadata.

User Question: {question}

Grounded Answer:
"""

def build_prompt(question: str, top_chunks: list) -> str:
    context_str = ""
    for idx, chunk in enumerate(top_chunks):
        text = chunk["payload"]["text"]
        doc_id = chunk["payload"].get("document_id", "Unknown")
        context_str += f"--- Context Block {idx + 1} (Source: {doc_id}) ---\n{text}\n\n"
        
    return GROUNDED_ANSWER_PROMPT.format(context_blocks=context_str, question=question)
