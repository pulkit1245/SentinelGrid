import networkx as nx
import uuid
from typing import List, Dict, Any, Optional

class NetworkXFallbackClient:
    """
    In-memory pure-Python graph engine fallback for SentinelGrid.
    Duplicates the exact function signatures of the planned Neo4j client.
    """
    def __init__(self):
        # DiGraph allows directed edges, which matches Neo4j semantics
        self.graph = nx.DiGraph()

    def _ensure_node(self, node_id: str, label: str, properties: Dict[str, Any]):
        """Helper to safely add or update a node."""
        if self.graph.has_node(node_id):
            # Update properties
            for k, v in properties.items():
                self.graph.nodes[node_id][k] = v
        else:
            # Add new node with a reserved '_label' property for matching Neo4j labels
            props = properties.copy()
            props['_label'] = label
            self.graph.add_node(node_id, **props)

    def add_zone_node(self, zone_id: str, name: str, hazard_class: str, current_risk_score: int):
        self._ensure_node(zone_id, "Zone", {
            "name": name,
            "hazard_class": hazard_class,
            "current_risk_score": current_risk_score
        })

    def add_sensor_node(self, sensor_id: str, zone_id: str, sensor_type: str):
        self._ensure_node(sensor_id, "Sensor", {"sensor_type": sensor_type})
        # Automatically create the LOCATED_IN edge to its zone
        self.graph.add_edge(sensor_id, zone_id, type="LOCATED_IN")

    def add_permit_edge(self, permit_id: str, zone_id: str, permit_type: str, status: str, valid_from: str, valid_to: str):
        self._ensure_node(permit_id, "Permit", {
            "permit_type": permit_type,
            "status": status,
            "valid_from": valid_from,
            "valid_to": valid_to
        })
        self.graph.add_edge(permit_id, zone_id, type="OVERLAPS_WITH")

    def update_zone_risk(self, zone_id: str, new_score: int, additional_features: Dict[str, Any] = None):
        if self.graph.has_node(zone_id):
            self.graph.nodes[zone_id]["current_risk_score"] = new_score
            if additional_features:
                for k, v in additional_features.items():
                    self.graph.nodes[zone_id][k] = v

    def add_historical_correlation(self, zone_id: str, incident_id: str, weight: float, incident_details: Dict[str, Any]):
        self._ensure_node(incident_id, "Incident", incident_details)
        self.graph.add_edge(zone_id, incident_id, type="HISTORICALLY_CORRELATED_WITH", weight=weight)

    def query_compound_patterns(self, zone_id: str) -> Dict[str, Any]:
        """
        Queries the in-memory graph for compound risk patterns for a specific zone.
        Looks for overlaps like hot_work permits + gas sensors + shift boundary.
        """
        if not self.graph.has_node(zone_id):
            return {"error": "Zone not found"}
        
        # Collect connected permits
        active_permits = []
        for u, v, data in self.graph.in_edges(zone_id, data=True):
            if data.get("type") == "OVERLAPS_WITH" and self.graph.nodes[u].get("_label") == "Permit":
                if self.graph.nodes[u].get("status") == "active":
                    active_permits.append(self.graph.nodes[u])

        # Collect connected sensors
        sensors = []
        for u, v, data in self.graph.in_edges(zone_id, data=True):
            if data.get("type") == "LOCATED_IN" and self.graph.nodes[u].get("_label") == "Sensor":
                sensors.append(self.graph.nodes[u])

        return {
            "zone": self.graph.nodes[zone_id],
            "active_permits": active_permits,
            "sensors": sensors
        }

    def get_path_for_alert(self, zone_id: str) -> Dict[str, Any]:
        """
        Extracts the overlapping nodes responsible for an alert.
        Used for the 'Why' visual lineage route.
        """
        # For simplicity, returning a 1-hop neighborhood subgraph payload
        if not self.graph.has_node(zone_id):
            return {"nodes": [], "edges": []}
            
        nodes = [{"id": zone_id, **self.graph.nodes[zone_id]}]
        edges = []
        
        for u, v, data in self.graph.in_edges(zone_id, data=True):
            nodes.append({"id": u, **self.graph.nodes[u]})
            edges.append({"source": u, "target": v, "type": data.get("type")})
            
        for u, v, data in self.graph.out_edges(zone_id, data=True):
            nodes.append({"id": v, **self.graph.nodes[v]})
            edges.append({"source": u, "target": v, "type": data.get("type")})

        return {"nodes": nodes, "edges": edges}

# Singleton instance
fallback_graph = NetworkXFallbackClient()
