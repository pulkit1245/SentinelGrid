import os
import sys

# Ensure the parent directory is in the path so we can import 'rag'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.hybrid_retriever import HybridRetriever
from rag.reranker import ContextReranker

def run_test():
    print("\n--- Initializing Local RAG Components ---")
    print("(This uses local HuggingFace models, NO API key required)\n")
    
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    
    try:
        retriever = HybridRetriever(qdrant_url=qdrant_url)
        reranker = ContextReranker()
    except Exception as e:
        print(f"Failed to initialize. Make sure you ran 'reindex.py' first! Error: {e}")
        return

    while True:
        query = input("\nEnter a test question (or 'q' to quit): ")
        if query.lower() == 'q':
            break
            
        print("\nSearching...")
        
        # 1. Retrieve candidates
        try:
            candidates = retriever.search(query, top_k=8)
        except Exception as e:
            print("Warning: Dense search failed (is Qdrant running?). Falling back to sparse index only.")
            candidates = retriever.sparse_retriever.search(query, limit=8)

        if not candidates:
            print("No matching text found in the PDF.")
            continue
            
        # 2. Rerank
        top_3 = reranker.rerank(query, candidates, top_k=3)
        
        print("\n=== TOP 3 RETRIEVED CONTEXT BLOCKS ===")
        for i, doc in enumerate(top_3):
            print(f"\n[{i+1}] Confidence Score: {doc['cross_score']:.2f}")
            print(f"Source: {doc['payload'].get('document_id')}")
            print(f"Text snippet: {doc['payload']['text'][:200]}...")

if __name__ == "__main__":
    run_test()
