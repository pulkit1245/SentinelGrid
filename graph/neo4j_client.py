import os
import logging
from typing import Dict, Any, List
from neo4j import GraphDatabase

class Neo4jClient:
    """
    Official Neo4j Client for SentinelGrid.
    Replaces the networkx_fallback during Member 4's integration phase.
    """
    def __init__(self):
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "password")
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            logging.info("Connected to Neo4j successfully.")
        except Exception as e:
            logging.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def add_zone_node(self, zone_id: str, name: str, hazard_class: str, current_risk_score: int):
        query = """
        MERGE (z:Zone {id: $zone_id})
        SET z.name = $name, 
            z.hazard_class = $hazard_class, 
            z.current_risk_score = $current_risk_score
        """
        with self.driver.session() as session:
            session.run(query, zone_id=zone_id, name=name, hazard_class=hazard_class, current_risk_score=current_risk_score)

    def add_sensor_node(self, sensor_id: str, zone_id: str, sensor_type: str):
        query = """
        MERGE (s:Sensor {id: $sensor_id})
        SET s.sensor_type = $sensor_type
        WITH s
        MATCH (z:Zone {id: $zone_id})
        MERGE (s)-[:LOCATED_IN]->(z)
        """
        with self.driver.session() as session:
            session.run(query, sensor_id=sensor_id, zone_id=zone_id, sensor_type=sensor_type)

    def add_permit_edge(self, permit_id: str, zone_id: str, permit_type: str, status: str, valid_from: str, valid_to: str):
        query = """
        MERGE (p:Permit {id: $permit_id})
        SET p.permit_type = $permit_type,
            p.status = $status,
            p.valid_from = $valid_from,
            p.valid_to = $valid_to
        WITH p
        MATCH (z:Zone {id: $zone_id})
        MERGE (p)-[:OVERLAPS_WITH]->(z)
        """
        with self.driver.session() as session:
            session.run(query, permit_id=permit_id, zone_id=zone_id, permit_type=permit_type, status=status, valid_from=valid_from, valid_to=valid_to)

    def update_zone_risk(self, zone_id: str, new_score: int, additional_features: Dict[str, Any] = None):
        query = """
        MATCH (z:Zone {id: $zone_id})
        SET z.current_risk_score = $new_score
        """
        with self.driver.session() as session:
            session.run(query, zone_id=zone_id, new_score=new_score)
            if additional_features:
                # Setting dynamic properties
                for k, v in additional_features.items():
                    session.run(f"MATCH (z:Zone {{id: $zone_id}}) SET z.`{k}` = $val", zone_id=zone_id, val=v)

    def add_historical_correlation(self, zone_id: str, incident_id: str, weight: float, incident_details: Dict[str, Any]):
        query = """
        MERGE (i:Incident {id: $incident_id})
        SET i += $incident_details
        WITH i
        MATCH (z:Zone {id: $zone_id})
        MERGE (z)-[r:HISTORICALLY_CORRELATED_WITH]->(i)
        SET r.weight = $weight
        """
        with self.driver.session() as session:
            session.run(query, zone_id=zone_id, incident_id=incident_id, weight=weight, incident_details=incident_details)

    def query_compound_patterns(self, zone_id: str) -> Dict[str, Any]:
        """
        Queries Neo4j for overlapping risk patterns.
        """
        query = """
        MATCH (z:Zone {id: $zone_id})
        OPTIONAL MATCH (p:Permit)-[:OVERLAPS_WITH]->(z) WHERE p.status = 'active'
        OPTIONAL MATCH (s:Sensor)-[:LOCATED_IN]->(z)
        RETURN z, collect(DISTINCT p) as active_permits, collect(DISTINCT s) as sensors
        """
        with self.driver.session() as session:
            result = session.run(query, zone_id=zone_id).single()
            if not result:
                return {"error": "Zone not found"}
            
            return {
                "zone": dict(result["z"]),
                "active_permits": [dict(p) for p in result["active_permits"] if p],
                "sensors": [dict(s) for s in result["sensors"] if s]
            }

    def get_path_for_alert(self, zone_id: str) -> Dict[str, Any]:
        query = """
        MATCH path = (n)-[r]-(z:Zone {id: $zone_id})
        RETURN path
        """
        nodes = {}
        edges = []
        with self.driver.session() as session:
            for record in session.run(query, zone_id=zone_id):
                path = record["path"]
                for node in path.nodes:
                    if node.element_id not in nodes:
                        nodes[node.element_id] = {"id": node.get("id"), "labels": list(node.labels), **dict(node)}
                for rel in path.relationships:
                    edges.append({
                        "source": rel.start_node.get("id"),
                        "target": rel.end_node.get("id"),
                        "type": rel.type
                    })
        
        return {"nodes": list(nodes.values()), "edges": edges}

# Singleton instance
neo4j_client = Neo4jClient()
