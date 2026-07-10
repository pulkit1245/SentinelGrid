from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import HTMLResponse
from app.services.compliance_report_service import compliance_report_service

router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance"])

# Mock database for alerts
mock_alerts_db = {
    "test-alert-123": {
        "id": "test-alert-123",
        "zone_id": "zone-01-degassing",
        "severity": "critical",
        "status": "confirmed", # Must be confirmed to generate report
        "graph_path": {
            "nodes": [{"id": "zone-01-degassing", "current_risk_score": 85}],
            "edges": []
        }
    }
}

@router.get("/report/{alert_id}", response_class=HTMLResponse)
async def generate_compliance_report(alert_id: str = Path(...)):
    """
    Generates and returns an OISD/DGMS statutory submission report.
    Returns 404 if the alert hasn't been confirmed.
    """
    alert = mock_alerts_db.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
        
    if alert.get("status") != "confirmed":
        raise HTTPException(status_code=404, detail="Report generation requires a confirmed alert. Alert is not confirmed yet.")
        
    # Mock some audit violations that the Compliance Audit Agent would have found
    mock_violations = [
        {
            "rule": "OISD-STD-105 Section 4.2",
            "violation": "Gas reading positive during active hot work.",
            "corrective_action": "Immediately halt hot work and purge zone."
        }
    ]
    
    html_content = compliance_report_service.generate_report_html(alert_id, alert, mock_violations)
    
    return HTMLResponse(content=html_content)
