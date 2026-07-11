"""
Compound Risk Agent.

Runs the graph-pattern query every enrichment cycle:
    hot-work permit ACTIVE in zone
    AND zone's gas-trend slope POSITIVE (drifting up, not yet past threshold)
    AND shift boundary WITHIN 30 min

...plus the XGBoost compound-risk score (Module 5) once the model is
trained; falls back to a rule-only signal (score=None) until then so this
agent is independently usable before Module 5 lands.

This agent only *proposes* a finding -- it does not decide whether to
escalate. That arbitration (requiring >=2 corroborating signals) is the
Orchestrator's job, so this agent can be tested and reasoned about in
isolation.
"""

from dataclasses import dataclass
from typing import Optional

from .shared_blackboard import Blackboard, ZoneSnapshot

GAS_TREND_POSITIVE_THRESHOLD = 0.001  # ppm/s -- filters out pure sensor noise
SHIFT_BOUNDARY_WINDOW_S = 30 * 60


@dataclass
class CompoundRiskFinding:
    zone_id: str
    triggered: bool
    reasons: list
    hot_work_permit_active: bool
    gas_trend_positive: bool
    shift_boundary_imminent: bool
    xgboost_score: Optional[float] = None  # 0-100, populated once Module 5's model is loaded

    @property
    def signal_count(self) -> int:
        return sum([self.hot_work_permit_active, self.gas_trend_positive,
                    self.shift_boundary_imminent])


class CompoundRiskAgent:
    def __init__(self, blackboard: Blackboard, scorer=None,
                 gas_trend_threshold: float = GAS_TREND_POSITIVE_THRESHOLD,
                 shift_window_s: float = SHIFT_BOUNDARY_WINDOW_S):
        """
        scorer: optional callable(features: dict) -> float in [0, 100],
        satisfied by Module 5's infer.score(). Left None until that model
        exists; the agent still functions on rules alone.
        """
        self.bb = blackboard
        self.scorer = scorer
        self.gas_trend_threshold = gas_trend_threshold
        self.shift_window_s = shift_window_s

    def _check_zone(self, snap: ZoneSnapshot) -> CompoundRiskFinding:
        hot_work_active = snap.has_active_permit_type("hot_work")
        gas_slope = snap.trend_slope("gas_ppm", window="5min")
        gas_positive = gas_slope is not None and gas_slope > self.gas_trend_threshold

        next_boundary = self.bb.shift_state.get("next_boundary_s")
        shift_imminent = (next_boundary is not None
                           and 0 <= next_boundary <= self.shift_window_s)

        reasons = []
        if hot_work_active:
            reasons.append(f"hot-work permit active in {snap.zone_id}")
        if gas_positive:
            reasons.append(f"gas trend slope {gas_slope:.4f} ppm/s (positive drift)")
        if shift_imminent:
            reasons.append(f"shift boundary in {next_boundary / 60:.1f} min")

        finding = CompoundRiskFinding(
            zone_id=snap.zone_id,
            triggered=hot_work_active and gas_positive and shift_imminent,
            reasons=reasons,
            hot_work_permit_active=hot_work_active,
            gas_trend_positive=gas_positive,
            shift_boundary_imminent=shift_imminent,
        )

        if self.scorer is not None:
            features = {
                "gas_trend_slope": gas_slope or 0.0,
                "permit_zone_overlap_count": len(snap.active_permits),
                "shift_boundary_proximity_s": next_boundary if next_boundary is not None else 1e9,
                "gas_anomaly_score": snap.anomaly_score("gas_ppm"),
            }
            finding.xgboost_score = self.scorer(features)

        return finding

    def run(self) -> list:
        """Evaluates every zone; returns findings for zones with >=1 signal (not just fully-triggered)."""
        findings = []
        for zone_id in self.bb.all_zone_ids():
            snap = self.bb.snapshot(zone_id)
            finding = self._check_zone(snap)
            if finding.signal_count > 0:
                findings.append(finding)
        return findings
