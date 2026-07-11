"""
Plant Risk Graph client.

Two implementations behind the same interface:
  - Neo4jGraphClient: talks to a real Neo4j instance (production/demo).
  - NetworkXGraphClient: in-memory fallback for local dev/tests when no
    Neo4j instance is running -- same method signatures, so agents never
    need to know which one they're talking to.

Graph shape: Zone nodes (properties updated by the enrichment worker),
Permit nodes (issued/closed against a Zone), and generic Event nodes for
anything else (shift boundaries, CV detections) that agents may want to
correlate against. Edges: (Permit)-[:ISSUED_IN]->(Zone),
(Event)-[:OCCURRED_IN]->(Zone) where applicable.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import networkx as nx


@dataclass
class Permit:
    permit_id: str
    permit_type: str
    zone_id: str
    status: str  # "active" | "closed"
    issued_sim_time_s: float
    closed_sim_time_s: Optional[float] = None


class GraphClientBase:
    """Interface every graph_client implementation satisfies."""

    def update_zone_properties(self, zone_id: str, properties: dict):
        raise NotImplementedError

    def get_zone_properties(self, zone_id: str) -> dict:
        raise NotImplementedError

    def record_event(self, event: dict):
        raise NotImplementedError

    def active_permits(self, zone_id: Optional[str] = None) -> List[Permit]:
        raise NotImplementedError

    def zone_ids(self) -> List[str]:
        raise NotImplementedError


class NetworkXGraphClient(GraphClientBase):
    """
    In-memory fallback. Uses a networkx MultiDiGraph where node IDs are
    prefixed by type ("zone:zone-01-degassing", "permit:PMT-001", etc.) to
    keep a single graph object simple to reason about and inspect.
    """

    def __init__(self):
        self.g = nx.MultiDiGraph()
        self._permits: Dict[str, Permit] = {}
        self._recent_events: List[dict] = []  # bounded log for zone-less events (shift boundaries etc.)

    def _zone_node(self, zone_id: str) -> str:
        node = f"zone:{zone_id}"
        if node not in self.g:
            self.g.add_node(node, type="Zone", zone_id=zone_id, properties={})
        return node

    def update_zone_properties(self, zone_id: str, properties: dict):
        node = self._zone_node(zone_id)
        self.g.nodes[node]["properties"].update(properties)

    def get_zone_properties(self, zone_id: str) -> dict:
        node = self._zone_node(zone_id)
        return dict(self.g.nodes[node]["properties"])

    def zone_ids(self) -> List[str]:
        return [d["zone_id"] for n, d in self.g.nodes(data=True) if d.get("type") == "Zone"]

    def record_event(self, event: dict):
        et = event.get("event_type")
        zone_id = event.get("zone_id")

        if et == "permit_issued":
            permit = Permit(
                permit_id=event["permit_id"],
                permit_type=event.get("permit_type", "unknown"),
                zone_id=zone_id,
                status="active",
                issued_sim_time_s=event["sim_time_s"],
            )
            self._permits[permit.permit_id] = permit
            node = self._zone_node(zone_id)
            permit_node = f"permit:{permit.permit_id}"
            self.g.add_node(permit_node, type="Permit", **permit.__dict__)
            self.g.add_edge(permit_node, node, relation="ISSUED_IN")
            return

        if et == "permit_closed":
            permit_id = event["permit_id"]
            if permit_id in self._permits:
                self._permits[permit_id].status = "closed"
                self._permits[permit_id].closed_sim_time_s = event["sim_time_s"]
                permit_node = f"permit:{permit_id}"
                if permit_node in self.g:
                    self.g.nodes[permit_node]["status"] = "closed"
            return

        # everything else (shift_boundary, changeover_window_start, cv detections
        # without an explicit permit relationship) -- keep a bounded recent log,
        # attached to the zone node if one is present.
        self._recent_events.append(event)
        if len(self._recent_events) > 10_000:
            self._recent_events = self._recent_events[-10_000:]
        if zone_id:
            self._zone_node(zone_id)

    def active_permits(self, zone_id: Optional[str] = None) -> List[Permit]:
        permits = [p for p in self._permits.values() if p.status == "active"]
        if zone_id is not None:
            permits = [p for p in permits if p.zone_id == zone_id]
        return permits

    def recent_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[dict]:
        events = self._recent_events
        if event_type is not None:
            events = [e for e in events if e.get("event_type") == event_type]
        return events[-limit:]


class Neo4jGraphClient(GraphClientBase):
    """
    Real Neo4j-backed implementation. Constructed lazily so importing this
    module never requires the neo4j driver to be installed unless you
    actually instantiate this class (NetworkXGraphClient has no such
    dependency, so local dev/tests work without Neo4j at all).
    """

    def __init__(self, uri: str, user: str, password: str):
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise ImportError(
                "neo4j driver required for Neo4jGraphClient: "
                "pip install neo4j --break-system-packages"
            ) from exc
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def update_zone_properties(self, zone_id: str, properties: dict):
        with self._driver.session() as session:
            session.run(
                "MERGE (z:Zone {zone_id: $zone_id}) SET z += $properties",
                zone_id=zone_id, properties=properties,
            )

    def get_zone_properties(self, zone_id: str) -> dict:
        with self._driver.session() as session:
            result = session.run(
                "MATCH (z:Zone {zone_id: $zone_id}) RETURN properties(z) AS props",
                zone_id=zone_id,
            ).single()
            return dict(result["props"]) if result else {}

    def zone_ids(self) -> List[str]:
        with self._driver.session() as session:
            result = session.run("MATCH (z:Zone) RETURN z.zone_id AS zone_id")
            return [r["zone_id"] for r in result]

    def record_event(self, event: dict):
        et = event.get("event_type")
        zone_id = event.get("zone_id")
        with self._driver.session() as session:
            if et == "permit_issued":
                session.run(
                    "MERGE (p:Permit {permit_id: $permit_id}) "
                    "SET p.permit_type = $permit_type, p.status = 'active', "
                    "    p.issued_sim_time_s = $sim_time_s "
                    "MERGE (z:Zone {zone_id: $zone_id}) "
                    "MERGE (p)-[:ISSUED_IN]->(z)",
                    permit_id=event["permit_id"], permit_type=event.get("permit_type", "unknown"),
                    sim_time_s=event["sim_time_s"], zone_id=zone_id,
                )
            elif et == "permit_closed":
                session.run(
                    "MATCH (p:Permit {permit_id: $permit_id}) "
                    "SET p.status = 'closed', p.closed_sim_time_s = $sim_time_s",
                    permit_id=event["permit_id"], sim_time_s=event["sim_time_s"],
                )
            else:
                session.run(
                    "CREATE (e:Event) SET e += $props "
                    + ("MERGE (z:Zone {zone_id: $zone_id}) CREATE (e)-[:OCCURRED_IN]->(z)"
                       if zone_id else ""),
                    props=event, zone_id=zone_id,
                )

    def active_permits(self, zone_id: Optional[str] = None) -> List[Permit]:
        query = "MATCH (p:Permit)-[:ISSUED_IN]->(z:Zone) WHERE p.status = 'active'"
        params = {}
        if zone_id is not None:
            query += " AND z.zone_id = $zone_id"
            params["zone_id"] = zone_id
        query += " RETURN p, z.zone_id AS zone_id"
        with self._driver.session() as session:
            result = session.run(query, **params)
            return [
                Permit(
                    permit_id=r["p"]["permit_id"], permit_type=r["p"]["permit_type"],
                    zone_id=r["zone_id"], status=r["p"]["status"],
                    issued_sim_time_s=r["p"]["issued_sim_time_s"],
                    closed_sim_time_s=r["p"].get("closed_sim_time_s"),
                )
                for r in result
            ]


def build_default_client(neo4j_uri: Optional[str] = None, neo4j_user: Optional[str] = None,
                          neo4j_password: Optional[str] = None) -> GraphClientBase:
    """Convenience factory: use Neo4j if credentials are given, else in-memory fallback."""
    if neo4j_uri and neo4j_user and neo4j_password:
        return Neo4jGraphClient(neo4j_uri, neo4j_user, neo4j_password)
    return NetworkXGraphClient()
