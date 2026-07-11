"""
Orchestrator Agent (LangGraph state machine).

Per zone, per cycle:
  1. hard_rules_node   -- statutory threshold check, NON-OVERRIDABLE. If any
                           sensor is already past its statutory threshold,
                           this escalates to critical immediately regardless
                           of what any other agent says. This is the floor;
                           nothing downstream can suppress it.
  2. gather_signals_node -- runs the Compound Risk Agent and Permit
                           Intelligence Agent (and, once available, the
                           Incident-RAG/Compliance agent) and collects their
                           findings for this zone.
  3. arbitrate_node    -- false-positive suppression: requires >=2
                           corroborating signals across
                           {compound_risk.triggered, permit violation
                           (severity="critical"), any future agent} before
                           escalating to "critical". A single signal alone
                           produces an "advisory" (visible, not paged).
  4. dispatch_node     -- on escalation, calls the injected `alert_service`
                           (Member 1's alert-creation service, called as a
                           direct in-process function -- not over HTTP --
                           per the architecture) with the full graph_path.

Run per-zone via `run_zone(zone_id)`, or `run_all()` to sweep every zone
in one enrichment cycle.
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from .shared_blackboard import Blackboard
from .compound_risk_agent import CompoundRiskAgent, CompoundRiskFinding
from .permit_intelligence_agent import PermitIntelligenceAgent, PermitViolation
from simulator.zones import STATUTORY_THRESHOLDS

MIN_CORROBORATING_SIGNALS = 2


class OrchestratorState(TypedDict, total=False):
    zone_id: str
    hard_rule_violation: Optional[dict]
    compound_finding: Optional[CompoundRiskFinding]
    permit_violations: List[PermitViolation]
    corroborating_signals: List[str]
    decision: str  # "critical" | "advisory" | "clear"
    graph_path: dict
    dispatched: bool


@dataclass
class AlertDecision:
    zone_id: str
    decision: str
    corroborating_signals: List[str]
    graph_path: dict


class OrchestratorAgent:
    def __init__(self, blackboard: Blackboard,
                 compound_risk_agent: Optional[CompoundRiskAgent] = None,
                 permit_intelligence_agent: Optional[PermitIntelligenceAgent] = None,
                 alert_service: Optional[Callable[[AlertDecision], None]] = None,
                 min_corroborating_signals: int = MIN_CORROBORATING_SIGNALS):
        self.bb = blackboard
        self.compound_risk_agent = compound_risk_agent or CompoundRiskAgent(blackboard)
        self.permit_intelligence_agent = permit_intelligence_agent or PermitIntelligenceAgent(blackboard)
        self.alert_service = alert_service
        self.min_corroborating_signals = min_corroborating_signals
        self.graph = self._build_graph()

    # ---- LangGraph nodes ----

    def _hard_rules_node(self, state: OrchestratorState) -> OrchestratorState:
        snap = self.bb.snapshot(state["zone_id"])
        for sensor_type, threshold in STATUTORY_THRESHOLDS.items():
            value = snap.sensor_value(sensor_type)
            if value is not None and value >= threshold:
                state["hard_rule_violation"] = {
                    "sensor_type": sensor_type, "value": value, "threshold": threshold,
                }
                return state
        state["hard_rule_violation"] = None
        return state

    def _gather_signals_node(self, state: OrchestratorState) -> OrchestratorState:
        zone_id = state["zone_id"]
        findings = self.compound_risk_agent.run()
        state["compound_finding"] = next((f for f in findings if f.zone_id == zone_id), None)
        all_permit_violations = self.permit_intelligence_agent.revalidate_all()
        state["permit_violations"] = [v for v in all_permit_violations if v.zone_id == zone_id]
        return state

    def _arbitrate_node(self, state: OrchestratorState) -> OrchestratorState:
        # Hard-rules floor is non-overridable: if it fired, we're already
        # "critical" -- this node still runs (for signal bookkeeping/audit
        # trail) but cannot downgrade the decision.
        if state.get("hard_rule_violation") is not None:
            state["decision"] = "critical"
            state["corroborating_signals"] = ["statutory_threshold_breach"]
            return state

        signals = []
        cf = state.get("compound_finding")
        if cf is not None and cf.triggered:
            signals.append("compound_risk_pattern_match")
        if any(v.severity == "critical" for v in state.get("permit_violations", [])):
            signals.append("permit_critical_violation")
        elif any(v.severity == "warning" for v in state.get("permit_violations", [])):
            signals.append("permit_warning")

        state["corroborating_signals"] = signals

        if len(signals) >= self.min_corroborating_signals:
            state["decision"] = "critical"
        elif len(signals) == 1:
            state["decision"] = "advisory"
        else:
            state["decision"] = "clear"
        return state

    def _dispatch_node(self, state: OrchestratorState) -> OrchestratorState:
        zone_id = state["zone_id"]
        snap = self.bb.snapshot(zone_id)
        graph_path = {
            "zone_id": zone_id,
            "zone_properties": snap.properties,
            "active_permits": [p.__dict__ for p in snap.active_permits],
            "hard_rule_violation": state.get("hard_rule_violation"),
            "compound_finding_reasons": (state["compound_finding"].reasons
                                          if state.get("compound_finding") else []),
            "permit_violations": [v.__dict__ for v in state.get("permit_violations", [])],
        }
        state["graph_path"] = graph_path

        if state["decision"] == "critical" and self.alert_service is not None:
            decision = AlertDecision(
                zone_id=zone_id, decision=state["decision"],
                corroborating_signals=state["corroborating_signals"],
                graph_path=graph_path,
            )
            self.alert_service(decision)
            state["dispatched"] = True
        else:
            state["dispatched"] = False
        return state

    def _build_graph(self):
        g = StateGraph(OrchestratorState)
        g.add_node("hard_rules", self._hard_rules_node)
        g.add_node("gather_signals", self._gather_signals_node)
        g.add_node("arbitrate", self._arbitrate_node)
        g.add_node("dispatch", self._dispatch_node)

        g.set_entry_point("hard_rules")
        g.add_edge("hard_rules", "gather_signals")
        g.add_edge("gather_signals", "arbitrate")
        g.add_edge("arbitrate", "dispatch")
        g.add_edge("dispatch", END)
        return g.compile()

    # ---- public entrypoints ----

    def run_zone(self, zone_id: str) -> OrchestratorState:
        return self.graph.invoke({"zone_id": zone_id})

    def run_all(self) -> List[OrchestratorState]:
        return [self.run_zone(zone_id) for zone_id in self.bb.all_zone_ids()]
