import os
from typing import List, Dict, Any
import json

from rag.embeddings import VectorDatabaseBuilder
from rag.scripts.reindex import BM25SparseIndexer

class HybridRetriever:
    """
    Combines dense vector scoring with BM25 sparse token indices using Reciprocal Rank Fusion (RRF).
    """
    def __init__(self, qdrant_url: str = "http://localhost:6333", qdrant_path: str | None = None):
        self.dense_retriever = VectorDatabaseBuilder(qdrant_url=qdrant_url, qdrant_path=qdrant_path)
        self.sparse_retriever = BM25SparseIndexer()
        
        # Load the mock BM25 index built by reindex.py
        bm25_store = os.path.join(os.path.dirname(__file__), "scripts", "bm25_store.json")
        if os.path.exists(bm25_store):
            with open(bm25_store, 'r') as f:
                chunks = json.load(f)
            self.sparse_retriever.build_index(chunks)
        else:
            print("Warning: bm25_store.json not found. Sparse index will be empty.")

    def _rrf(self, dense_results: List[Dict], sparse_results: List[Dict], k: int = 60) -> List[Dict]:
        """
        Reciprocal Rank Fusion formula: 1 / (k + rank)
        """
        rrf_scores = {}
        payloads = {}
        
        # Rank dense
        for rank, res in enumerate(dense_results):
            text = res["payload"]["text"]
            if text not in rrf_scores:
                rrf_scores[text] = 0
                payloads[text] = res["payload"]
            rrf_scores[text] += 1.0 / (k + rank + 1)
            
        # Rank sparse
        for rank, res in enumerate(sparse_results):
            text = res["payload"]["text"]
            if text not in rrf_scores:
                rrf_scores[text] = 0
                payloads[text] = res["payload"]
            rrf_scores[text] += 1.0 / (k + rank + 1)
            
        # Sort by RRF score
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [{"score": score, "payload": payloads[text]} for text, score in sorted_results]

    def search(self, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        # Get top 8 candidates from each stream
        dense_candidates = []
        try:
            dense_candidates = self.dense_retriever.search(query, limit=8)
        except Exception as e:
            print(f"Dense search failed: {e}")
            
        sparse_candidates = self.sparse_retriever.search(query, limit=8)
        
        # Unify with RRF
        fused = self._rrf(dense_candidates, sparse_candidates)
        
        return fused[:top_k]
