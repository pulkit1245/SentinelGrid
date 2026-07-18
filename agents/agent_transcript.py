"""
Agent debate transcript.

Turns one orchestrator cycle's raw decision data into a readable
conversation between the agents -- "Compound Risk Agent: I see X. Permit
Intelligence Agent: I see Y. Orchestrator: N signals confirmed, escalating."

Purely a presentation layer: takes the SAME data the orchestrator already
produces (state["compound_finding"], state["permit_violations"],
state["corroborating_signals"]) and reformats it. No new reasoning happens
here -- this only makes existing reasoning visible to a non-technical
audience in seconds instead of requiring them to read a JSON blob.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class TranscriptLine:
    speaker: str
    message: str


def build_transcript(state: dict) -> List[TranscriptLine]:
    """
    `state` is an OrchestratorState (or the equivalent dict) as produced by
    OrchestratorAgent.run_zone(). Returns an ordered list of chat lines.
    """
    lines: List[TranscriptLine] = []
    zone_id = state["zone_id"]

    # 1. Hard-rules floor speaks first -- it's checked first and can't be overridden.
    hard_rule = state.get("hard_rule_violation")
    if hard_rule is not None:
        lines.append(TranscriptLine(
            "Hard-Rules Check",
            f"Statutory threshold breached in {zone_id}: "
            f"{hard_rule['sensor_type']}={hard_rule['value']:.2f} "
            f"(limit: {hard_rule['threshold']}). This is non-overridable.",
        ))
    else:
        lines.append(TranscriptLine(
            "Hard-Rules Check",
            f"No statutory threshold breaches in {zone_id}. Handing off to the agents.",
        ))

    # 2. Compound Risk Agent's findings.
    cf = state.get("compound_finding")
    if cf is not None and cf.reasons:
        reasons_str = "; ".join(cf.reasons)
        verdict = "This matches the full compound-risk pattern." if cf.triggered else \
                  f"Only {cf.signal_count}/3 conditions met so far -- not a full match yet."
        lines.append(TranscriptLine(
            "Compound Risk Agent",
            f"In {zone_id}, I see: {reasons_str}. {verdict}",
        ))
    else:
        lines.append(TranscriptLine(
            "Compound Risk Agent",
            f"Nothing notable in {zone_id} right now.",
        ))

    # 3. Permit Intelligence Agent's findings.
    permit_violations = state.get("permit_violations", [])
    if permit_violations:
        for v in permit_violations:
            tone = "This is now a critical concern." if v.severity == "critical" else \
                   "Worth flagging, not yet critical."
            lines.append(TranscriptLine(
                "Permit Intelligence Agent",
                f"{v.reason}. {tone}",
            ))
    else:
        lines.append(TranscriptLine(
            "Permit Intelligence Agent",
            f"All active permits in {zone_id} still check out against current conditions.",
        ))

    # 4. The Orchestrator's final call.
    signals = state.get("corroborating_signals", [])
    decision = state.get("decision", "clear")
    if decision == "critical":
        signal_list = ", ".join(signals)
        lines.append(TranscriptLine(
            "Orchestrator",
            f"{len(signals)} corroborating signal(s) confirmed ({signal_list}) -- "
            f"escalating {zone_id} to CRITICAL.",
        ))
    elif decision == "advisory":
        lines.append(TranscriptLine(
            "Orchestrator",
            f"Only 1 signal so far in {zone_id} -- logging as an advisory, not paging anyone yet. "
            f"Need at least one more corroborating signal before I escalate.",
        ))
    else:
        lines.append(TranscriptLine(
            "Orchestrator",
            f"No corroborating signals in {zone_id} -- all clear.",
        ))

    return lines


def format_transcript_text(state: dict) -> str:
    """Plain-text version for terminal/log output, e.g. during a live demo."""
    lines = build_transcript(state)
    return "\n".join(f"[{ln.speaker}] {ln.message}" for ln in lines)


def format_transcript_markdown(state: dict) -> str:
    """Chat-bubble-style markdown, for rendering in a UI or a report."""
    lines = build_transcript(state)
    out = []
    for ln in lines:
        out.append(f"**{ln.speaker}:** {ln.message}")
    return "\n\n".join(out)


def build_transcript_from_entry(entry) -> List[TranscriptLine]:
    """
    Same idea as build_transcript(), but reads from a BlackBoxEntry (plain,
    JSON-safe summarized fields) instead of a live OrchestratorState (which
    holds actual agent objects). Use this for replaying a saved/loaded
    black-box log, where the original objects no longer exist -- only the
    entry's already-summarized dicts/strings do.
    """
    lines: List[TranscriptLine] = []
    zone_id = entry.zone_id

    if entry.hard_rule_violation is not None:
        hr = entry.hard_rule_violation
        lines.append(TranscriptLine(
            "Hard-Rules Check",
            f"Statutory threshold breached in {zone_id}: "
            f"{hr['sensor_type']}={hr['value']:.2f} (limit: {hr['threshold']}). "
            f"This is non-overridable.",
        ))
    else:
        lines.append(TranscriptLine(
            "Hard-Rules Check",
            f"No statutory threshold breaches in {zone_id}. Handing off to the agents.",
        ))

    cf = entry.compound_finding_summary
    if cf is not None and cf.get("reasons"):
        reasons_str = "; ".join(cf["reasons"])
        verdict = "This matches the full compound-risk pattern." if cf["triggered"] else \
                  f"Only {cf['signal_count']}/3 conditions met so far -- not a full match yet."
        lines.append(TranscriptLine(
            "Compound Risk Agent",
            f"In {zone_id}, I see: {reasons_str}. {verdict}",
        ))
    else:
        lines.append(TranscriptLine(
            "Compound Risk Agent",
            f"Nothing notable in {zone_id} right now.",
        ))

    if entry.permit_violations_summary:
        for v in entry.permit_violations_summary:
            tone = "This is now a critical concern." if v["severity"] == "critical" else \
                   "Worth flagging, not yet critical."
            lines.append(TranscriptLine("Permit Intelligence Agent", f"{v['reason']}. {tone}"))
    else:
        lines.append(TranscriptLine(
            "Permit Intelligence Agent",
            f"All active permits in {zone_id} still check out against current conditions.",
        ))

    if entry.decision == "critical":
        signal_list = ", ".join(entry.corroborating_signals)
        lines.append(TranscriptLine(
            "Orchestrator",
            f"{len(entry.corroborating_signals)} corroborating signal(s) confirmed "
            f"({signal_list}) -- escalating {zone_id} to CRITICAL.",
        ))
    elif entry.decision == "advisory":
        lines.append(TranscriptLine(
            "Orchestrator",
            f"Only 1 signal so far in {zone_id} -- logging as an advisory, not paging anyone yet.",
        ))
    else:
        lines.append(TranscriptLine("Orchestrator", f"No corroborating signals in {zone_id} -- all clear."))

    return lines


def format_transcript_text_from_entry(entry) -> str:
    lines = build_transcript_from_entry(entry)
    return "\n".join(f"[{ln.speaker}] {ln.message}" for ln in lines)
