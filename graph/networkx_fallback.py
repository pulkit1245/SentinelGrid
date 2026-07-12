"""
Backward-compatible graph fallback module.

Delegates to the shared in-memory graph client in agents/graph_client.py so
Member 2 enrichment/agents and Member 3 RAG/compliance agents read the same graph.
"""

from agents.graph_client import NetworkXGraphClient, get_shared_graph_client

# Alias retained for Member 3 imports
NetworkXFallbackClient = NetworkXGraphClient
fallback_graph = get_shared_graph_client()
