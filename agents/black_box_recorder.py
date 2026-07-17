"""
Black Box Recorder.

Like an airplane's flight recorder: captures every agent's reasoning at
every orchestrator cycle, timestamped, so an incident can be replayed
after the fact -- "what did each agent believe, and when did the picture
change" -- instead of only ever seeing the system's CURRENT state.

Deliberately storage-only and dependency-free (no database) so it can sit
in front of Member 1's real persistence layer later without this module
needing to change -- just point `sink` at a different write function.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, List, Optional

DEFAULT_LOG_PATH = Path(__file__).resolve().parent / "_black_box_log.jsonl"


@dataclass
class BlackBoxEntry:
    sim_time_s: float
    zone_id: str
    hard_rule_violation: Optional[dict]
    compound_finding_summary: Optional[dict]  # {triggered, reasons, signal_count}
    permit_violations_summary: List[dict]     # [{reason, severity}, ...]
    corroborating_signals: List[str]
    decision: str  # "critical" | "advisory" | "clear"
    dispatched: bool


class BlackBoxRecorder:
    """
    Call `.record(sim_time_s, orchestrator_state)` once per orchestrator
    cycle (per zone, per tick). Entries are kept in-memory for replay AND
    optionally streamed to a sink (e.g. append-to-file, or a callback that
    writes to Member 1's real database once that exists).
    """

    def __init__(self, sink: Optional[Callable[[BlackBoxEntry], None]] = None):
        self.entries: List[BlackBoxEntry] = []
        self.sink = sink

    def record(self, sim_time_s: float, state: dict) -> BlackBoxEntry:
        cf = state.get("compound_finding")
        compound_summary = None
        if cf is not None:
            compound_summary = {
                "triggered": cf.triggered,
                "reasons": cf.reasons,
                "signal_count": cf.signal_count,
            }

        entry = BlackBoxEntry(
            sim_time_s=sim_time_s,
            zone_id=state["zone_id"],
            hard_rule_violation=state.get("hard_rule_violation"),
            compound_finding_summary=compound_summary,
            permit_violations_summary=[
                {"reason": v.reason, "severity": v.severity}
                for v in state.get("permit_violations", [])
            ],
            corroborating_signals=state.get("corroborating_signals", []),
            decision=state.get("decision", "clear"),
            dispatched=state.get("dispatched", False),
        )
        self.entries.append(entry)
        if self.sink is not None:
            self.sink(entry)
        return entry

    # ---- replay / scrub ----

    def timeline_for_zone(self, zone_id: str) -> List[BlackBoxEntry]:
        return [e for e in self.entries if e.zone_id == zone_id]

    def snapshot_at(self, zone_id: str, sim_time_s: float) -> Optional[BlackBoxEntry]:
        """The most recent entry at or before sim_time_s -- 'what did we know at this moment.'"""
        candidates = [e for e in self.timeline_for_zone(zone_id) if e.sim_time_s <= sim_time_s]
        return max(candidates, key=lambda e: e.sim_time_s) if candidates else None

    def decision_changes(self, zone_id: str) -> List[BlackBoxEntry]:
        """Only the moments the decision actually CHANGED -- the real 'story beats' of an incident."""
        timeline = self.timeline_for_zone(zone_id)
        changes = []
        last_decision = None
        for e in timeline:
            if e.decision != last_decision:
                changes.append(e)
                last_decision = e.decision
        return changes

    def save(self, path: Path = DEFAULT_LOG_PATH):
        with open(path, "w") as f:
            for e in self.entries:
                f.write(json.dumps(asdict(e)) + "\n")

    @classmethod
    def load(cls, path: Path = DEFAULT_LOG_PATH) -> "BlackBoxRecorder":
        recorder = cls()
        with open(path) as f:
            for line in f:
                if line.strip():
                    recorder.entries.append(BlackBoxEntry(**json.loads(line)))
        return recorder
