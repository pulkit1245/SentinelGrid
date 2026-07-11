from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.repositories.alert_repository import AlertRepository

logger = logging.getLogger(__name__)


class ComplianceReportService:
    """Generates auto-drafted OISD/DGMS-format incident reports for confirmed alerts."""

    def __init__(self, alert_repo: AlertRepository) -> None:
        self.alert_repo = alert_repo

    async def generate_report(self, alert_id: uuid.UUID) -> dict:
        alert = await self.alert_repo.get_alert(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        if not alert.confirmed_by:
            raise ValueError("Alert must be confirmed before generating a compliance report")

        # TODO(Member 3): LLM-filled template logic goes here
        # For now, return a structured draft that can be rendered as PDF
        report = {
            "report_type": "OISD-DGMS Incident Report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "alert_id": str(alert_id),
            "incident_details": {
                "severity": alert.severity,
                "triggered_at": alert.triggered_at.isoformat(),
                "confirmed_at": alert.confirmed_at.isoformat() if alert.confirmed_at else None,
                "description": alert.description or alert.title,
                "causal_chain": alert.graph_path,
            },
            "regulatory_references": [
                "OISD Standard 118 — Instrumentation",
                "DGMS Circular 2019-04 — Hot Work Safety",
                "Factories Act 1948, Section 41B",
            ],
            "corrective_actions": [
                "Suspend all hot-work operations in affected zone immediately",
                "Evacuate non-essential personnel per emergency plan",
                "Investigate gas drift source and isolate if possible",
                "Submit incident notification to DGMS within 24 hours",
            ],
            "status": "draft",
        }

        logger.info("Compliance report generated", extra={"alert_id": str(alert_id)})
        return report
