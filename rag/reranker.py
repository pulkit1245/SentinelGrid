from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

class ContextReranker:
    """
    Implements a secondary scoring pass to distill raw candidate texts.
    Uses a cross-encoder model to trim the pool down to the absolute top 3 most relevant entries.
    """
    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        # Using a small, fast cross-encoder for the hackathon MVP
        self.model = CrossEncoder(model_name, max_length=512)

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        if not candidates:
            return []
            
        # Prepare pairs of (query, document_text)
        pairs = [(query, cand["payload"]["text"]) for cand in candidates]
        
        # Predict scores
        scores = self.model.predict(pairs)
        
        # Combine scores with candidates
        scored_candidates = []
        for i, score in enumerate(scores):
            scored_candidates.append({
                "cross_score": float(score),
                "payload": candidates[i]["payload"],
                "rrf_score": candidates[i].get("score", 0)
            })
            
        # Sort by cross-encoder score descending
        scored_candidates.sort(key=lambda x: x["cross_score"], reverse=True)
        
        return scored_candidates[:top_k]
