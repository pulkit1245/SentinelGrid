import asyncio
from typing import Dict, Any
from graph.networkx_fallback import fallback_graph

# In a production setup, this would toggle between Neo4j and NetworkX.
# For the hackathon MVP, we are using the NetworkX fallback as default.
FALLBACK_MODE = True

class GraphBuilderService:
    """
    Service layer that maps transaction state from PostgreSQL to the graph database.
    Listens to incoming events (simulated here via method calls) and updates the graph.
    """
    
    def __init__(self):
        self.client = fallback_graph
        
    async def handle_zone_created(self, payload: Dict[str, Any]):
        """Fired when a zone is created in Postgres."""
        self.client.add_zone_node(
            zone_id=payload["id"],
            name=payload["name"],
            hazard_class=payload.get("hazard_class", "general"),
            current_risk_score=payload.get("current_risk_score", 0)
        )
        
    async def handle_sensor_created(self, payload: Dict[str, Any]):
        """Fired when a sensor is registered."""
        self.client.add_sensor_node(
            sensor_id=payload["id"],
            zone_id=payload["zone_id"],
            sensor_type=payload["sensor_type"]
        )
        
    async def handle_permit_issued(self, payload: Dict[str, Any]):
        """Fired when a new PTW is issued."""
        self.client.add_permit_edge(
            permit_id=payload["id"],
            zone_id=payload["zone_id"],
            permit_type=payload["permit_type"],
            status=payload.get("status", "active"),
            valid_from=payload["valid_from"],
            valid_to=payload["valid_to"]
        )

    async def handle_permit_status_change(self, permit_id: str, new_status: str, zone_id: str):
        """Fired when permit is closed or revoked."""
        # The networkx fallback uses ensure_node logic, so we can just re-add with same ID
        # In a real app we'd fetch existing properties first, but for now:
        if self.client.graph.has_node(permit_id):
            self.client.graph.nodes[permit_id]["status"] = new_status
            
    async def handle_zone_risk_updated(self, zone_id: str, new_score: int, features: Dict[str, Any]):
        """Fired continuously by the enrichment worker / ML scorer."""
        self.client.update_zone_risk(zone_id, new_score, features)

graph_builder = GraphBuilderService()
