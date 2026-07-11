from typing import Dict, Any, Optional
from graph.networkx_fallback import fallback_graph
from rag.hybrid_retriever import HybridRetriever
from rag.reranker import ContextReranker

class IncidentRagAgent:
    """
    Autonomous agent loop that links past events with current anomalies.
    Queries the RAG index and draws HISTORICALLY_CORRELATED_WITH edges.
    """
    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        try:
            self.retriever = HybridRetriever(qdrant_url=qdrant_url)
            self.reranker = ContextReranker()
        except Exception:
            self.retriever = None
            self.reranker = None
            
        self.graph_client = fallback_graph

    def evaluate_zone(self, zone_id: str, risk_score: int, anomaly_features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Called by the Orchestrator when a zone's risk score spikes.
        """
        if risk_score < 50 or not self.retriever or not self.reranker:
            return None
            
        # Formulate query based on anomaly signature
        query = f"Incident involving {anomaly_features.get('hazard_class', 'hazardous')} operations"
        if "hot_work" in anomaly_features.get("active_permits", []):
            query += " with hot work permit"
            
        # Retrieve similar incidents
        candidates = self.retriever.search(query, top_k=8)
        
        # Filter for incident documents only
        incident_candidates = [c for c in candidates if c["payload"].get("source_type") == "incident"]
        
        if not incident_candidates:
            return None
            
        # Rerank
        top_3 = self.reranker.rerank(query, incident_candidates, top_k=3)
        
        if top_3 and top_3[0]["cross_score"] > 0.5: # Confidence threshold
            best_match = top_3[0]
            incident_id = best_match["payload"].get("document_id")
            
            # Draw edge in graph
            self.graph_client.add_historical_correlation(
                zone_id=zone_id,
                incident_id=incident_id,
                weight=best_match["cross_score"],
                incident_details={"text_snippet": best_match["payload"]["text"]}
            )
            
            return {
                "matched_incident": incident_id,
                "confidence": best_match["cross_score"],
                "snippet": best_match["payload"]["text"]
            }
            
        return None
