from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.middlewares.auth_middleware import require_role
from app.models.base import get_db
from app.repositories.alert_repository import AlertRepository
from app.schemas.auth_schema import UserInToken
from app.services.compliance_report_service import compliance_report_service

router = APIRouter(prefix="/compliance", tags=["Compliance"])


@router.get("/report/{alert_id}", response_class=HTMLResponse)
async def generate_compliance_report(
    alert_id: uuid.UUID,
    current_user: Annotated[UserInToken, Depends(require_role("plant_admin", "auditor", "safety_officer"))],
    db: AsyncSession = Depends(get_db),
):
    """Generate an OISD/DGMS statutory submission report for a confirmed alert."""
    repo = AlertRepository(db)
    alert = await repo.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    if not alert.confirmed_by:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report generation requires a confirmed alert. Alert is not confirmed yet.",
        )

    violations: list[dict] = []
    try:
        from agents.compliance_audit_agent import ComplianceAuditAgent

        violations = ComplianceAuditAgent().audit_zone(str(alert.zone_id))
    except Exception:
        violations = [
            {
                "rule": "OISD-STD-105 Section 4.2",
                "violation": f"Compound risk alert confirmed in zone {alert.zone_id}.",
                "corrective_action": "Review zone conditions and complete statutory notification.",
            }
        ]

    alert_data = {
        "id": str(alert.id),
        "zone_id": str(alert.zone_id),
        "severity": alert.severity,
        "status": "confirmed",
        "graph_path": alert.graph_path,
        "title": alert.title,
        "description": alert.description,
    }
    html_content = compliance_report_service.generate_report_html(str(alert_id), alert_data, violations)
    return HTMLResponse(content=html_content)
