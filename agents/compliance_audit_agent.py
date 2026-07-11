from typing import Dict, Any, List
from graph.networkx_fallback import fallback_graph

class ComplianceAuditAgent:
    """
    Checks live plant operations against legal limits to generate corrective actions.
    """
    def __init__(self):
        self.graph_client = fallback_graph

    def audit_zone(self, zone_id: str) -> List[Dict[str, Any]]:
        """
        Generates structured corrective actions if rule violations are found.
        """
        graph_data = self.graph_client.query_compound_patterns(zone_id)
        if "error" in graph_data:
            return []
            
        zone = graph_data["zone"]
        active_permits = graph_data["active_permits"]
        sensors = graph_data["sensors"]
        
        violations = []
        
        # Rule 1: Hot work requires LEL 0% (Strict OISD rule)
        has_hot_work = any(p.get("permit_type") == "hot_work" for p in active_permits)
        if has_hot_work:
            for sensor in sensors:
                if sensor.get("sensor_type") == "gas":
                    # Mock check - assume we have a live reading attached to the sensor node
                    reading = sensor.get("last_reading", 0.0)
                    if reading > 0.0:
                        violations.append({
                            "rule": "OISD-STD-105 Section 4.2",
                            "violation": f"Gas reading > 0% ({reading}%) during active hot work.",
                            "corrective_action": "Immediately halt hot work and purge zone."
                        })
                        
        # Rule 2: Equipment maintenance overlap
        if has_hot_work and any(p.get("permit_type") == "degassing" for p in active_permits):
            violations.append({
                "rule": "OISD-STD-105 Section 4.4",
                "violation": "Hot work permitted within degassing zone.",
                "corrective_action": "Revoke hot work permit until degassing completes."
            })
            
        return violations
