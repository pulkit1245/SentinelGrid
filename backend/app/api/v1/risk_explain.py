"""
risk_explain.py  –  NEW FILE (no existing files modified)
──────────────────────────────────────────────────────────
POST /api/v1/risk/explain

Translates a numerical risk score into a clear, human-readable
explanation using the same Gemini LLM already wired into the RAG
pipeline.  The frontend can call this endpoint after fetching zone
data and display the explanation next to the score.

Registration:  add the following two lines to backend/app/main.py
(inside create_app, with the other include_router calls):

    from app.api.v1 import risk_explain
    app.include_router(risk_explain.router, prefix=prefix, tags=["risk-explain"])

Nothing in the existing codebase is changed by this file.
"""
from __future__ import annotations

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.middlewares.auth_middleware import get_current_user
from app.schemas.auth_schema import UserInToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["risk-explain"])

# ──────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────────────────────────────────────

class ActiveAlert(BaseModel):
    severity: str
    title: str
    description: str | None = None


class ActivePermit(BaseModel):
    permit_type: str
    valid_from: str
    valid_to: str


class RiskExplainRequest(BaseModel):
    zone_name: str = Field(..., description="Human-readable zone name, e.g. 'Zone 4 – Compressor Bay'")
    hazard_class: str = Field(..., description="Hazard classification, e.g. 'gas', 'thermal'")
    risk_score: int = Field(..., ge=0, le=100, description="Current risk score 0-100")
    active_alerts: list[ActiveAlert] = Field(default_factory=list)
    active_permits: list[ActivePermit] = Field(default_factory=list)
    sensor_trend_note: str | None = Field(
        None,
        description="Optional free-text sensor trend summary, e.g. 'Gas sensor has been rising for 18 minutes'",
    )
    shift_change_in_minutes: int | None = Field(
        None,
        description="If a shift handover is imminent, minutes until it occurs",
    )


class RiskExplainResponse(BaseModel):
    explanation: str
    risk_level: str          # "low" | "watch" | "warning" | "critical"
    score: int
    generated_by: str        # "llm" | "rule_based"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "warning"
    if score >= 40:
        return "watch"
    return "low"


def _rule_based_explanation(req: RiskExplainRequest) -> str:
    """
    Deterministic fallback when no LLM API key is configured.
    Produces a grammatically correct sentence from the structured data.
    """
    parts: list[str] = []

    score = req.risk_score
    level = _risk_level(score)
    zone = req.zone_name

    # Opening clause
    if level == "critical":
        opener = f"Risk in {zone} is at a critical level ({score}/100)"
    elif level == "warning":
        opener = f"Risk in {zone} is elevated ({score}/100)"
    elif level == "watch":
        opener = f"Risk in {zone} is being monitored ({score}/100)"
    else:
        opener = f"Risk in {zone} is currently low ({score}/100)"

    # Active permits
    for permit in req.active_permits:
        ptype = permit.permit_type.replace("_", "-")
        parts.append(f"a {ptype} permit is currently active")

    # Active alerts
    critical_alerts = [a for a in req.active_alerts if a.severity == "critical"]
    warning_alerts  = [a for a in req.active_alerts if a.severity in ("warning", "watch")]

    for alert in critical_alerts[:2]:
        parts.append(f'a critical alert has been raised: "{alert.title}"')
    for alert in warning_alerts[:1]:
        parts.append(f'there is a warning alert: "{alert.title}"')

    # Sensor trend
    if req.sensor_trend_note:
        parts.append(req.sensor_trend_note.rstrip(".").lower())

    # Shift change
    if req.shift_change_in_minutes is not None:
        parts.append(
            f"a shift change is scheduled in the next {req.shift_change_in_minutes} minute"
            + ("s" if req.shift_change_in_minutes != 1 else "")
        )

    # Hazard class context
    if not parts:
        parts.append(f"the zone is classified as a {req.hazard_class.replace('_', ' ')} hazard area")

    # Assemble
    if len(parts) == 1:
        reason_clause = parts[0]
    elif len(parts) == 2:
        reason_clause = f"{parts[0]} and {parts[1]}"
    else:
        reason_clause = ", ".join(parts[:-1]) + f", and {parts[-1]}"

    return f"{opener} because {reason_clause}."


_SYSTEM_PROMPT = (
    "You are SentinelGrid's AI safety advisor. "
    "Your role is to translate raw risk-score data into a single, clear, "
    "concise paragraph (2-3 sentences) that a non-technical safety manager "
    "can immediately understand. "
    "Always begin by stating the zone name and the numerical score. "
    "Then explain the primary reasons driving the score using the supplied "
    "context. Be specific and factual — do not hallucinate details not in the "
    "context. Use plain language, avoid jargon, and keep the response under "
    "80 words."
)


def _build_llm_prompt(req: RiskExplainRequest) -> str:
    lines: list[str] = [
        f"Zone: {req.zone_name}",
        f"Hazard class: {req.hazard_class}",
        f"Risk score: {req.risk_score}/100  (level: {_risk_level(req.risk_score)})",
    ]

    if req.active_permits:
        permit_strs = [
            f"  • {p.permit_type.replace('_', '-')} (valid {p.valid_from[:10]} → {p.valid_to[:10]})"
            for p in req.active_permits
        ]
        lines.append("Active permits:\n" + "\n".join(permit_strs))

    if req.active_alerts:
        alert_strs = [
            f"  • [{a.severity.upper()}] {a.title}" + (f": {a.description}" if a.description else "")
            for a in req.active_alerts
        ]
        lines.append("Active alerts:\n" + "\n".join(alert_strs))

    if req.sensor_trend_note:
        lines.append(f"Sensor trend: {req.sensor_trend_note}")

    if req.shift_change_in_minutes is not None:
        lines.append(f"Shift change in: {req.shift_change_in_minutes} minutes")

    lines.append(
        "\nWrite a concise human-readable explanation for the risk score above."
    )
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/explain", response_model=RiskExplainResponse)
async def explain_risk(
    body: RiskExplainRequest,
    current_user: Annotated[UserInToken, Depends(get_current_user)],
) -> RiskExplainResponse:
    """
    Translate a zone's numerical risk score into a human-readable explanation.

    The endpoint tries to use the Gemini LLM (same key as the RAG pipeline).
    If no API key is configured it falls back to a deterministic rule-based
    explanation so the feature always returns a useful response.
    """
    api_key: str | None = os.environ.get("OPENAI_API_KEY") or settings.LLM_API_KEY or None

    if api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash-8b",
                google_api_key=api_key,
                temperature=0.3,
                max_output_tokens=200,
            )
            prompt = _build_llm_prompt(body)
            response = llm.invoke([
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            explanation = str(response.content).strip()
            generated_by = "llm"
            logger.info(
                "Risk explanation generated via LLM",
                extra={"zone": body.zone_name, "score": body.risk_score},
            )
        except Exception as exc:
            logger.warning(
                "LLM call failed for risk explanation, using rule-based fallback: %s", exc
            )
            explanation = _rule_based_explanation(body)
            generated_by = "rule_based"
    else:
        logger.debug("No LLM API key — using rule-based risk explanation")
        explanation = _rule_based_explanation(body)
        generated_by = "rule_based"

    return RiskExplainResponse(
        explanation=explanation,
        risk_level=_risk_level(body.risk_score),
        score=body.risk_score,
        generated_by=generated_by,
    )
