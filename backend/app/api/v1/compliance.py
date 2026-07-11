from fastapi import APIRouter, Response, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fpdf import FPDF
import uuid
from datetime import datetime

from app.models.base import get_db
from app.repositories.alert_repository import AlertRepository

router = APIRouter(prefix="/compliance")

class CompliancePDF(FPDF):
    def header(self):
        # Logo / Header Box
        self.set_fill_color(22, 27, 34) # Dark slate
        self.rect(0, 0, 210, 30, 'F')
        
        # Title
        self.set_y(10)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'SentinelGrid Compliance Report', align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-20)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.set_draw_color(200, 200, 200)
        self.line(10, 277, 200, 277)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}} | Generated automatically by SentinelGrid AI', align='C')

@router.get("/report/{alert_id}")
async def get_report(alert_id: str, db: AsyncSession = Depends(get_db)):
    repo = AlertRepository(db)
    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Alert ID")
        
    alert = await repo.get_alert(alert_uuid)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    pdf = CompliancePDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_y(40)
    
    # Report Header Info
    pdf.set_font("Helvetica", size=10, style='B')
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, text="OFFICIAL AUDIT CERTIFICATE", align='R')
    pdf.ln(10)
    
    def sanitize(text):
        if not text: return "N/A"
        return text.replace('—', '-').replace('–', '-').replace('“', '"').replace('”', '"').replace('’', "'")

    # Title Section
    pdf.set_font("Helvetica", size=18, style='B')
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, text=f"Incident: {sanitize(alert.title)}")
    pdf.ln(12)
    
    # Metadata Table
    pdf.set_fill_color(245, 245, 245)
    pdf.set_draw_color(200, 200, 200)
    
    def metadata_row(label, value):
        pdf.set_font("Helvetica", size=10, style='B')
        pdf.set_text_color(80, 80, 80)
        pdf.cell(50, 10, text=f"  {label}", border=1, fill=True)
        
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(140, 10, text=f"  {value}", border=1)
        pdf.ln(10)
        
    metadata_row("Incident ID", str(alert.id))
    metadata_row("Severity", str(alert.severity).upper())
    
    tz_fmt = "%Y-%m-%d %H:%M:%S UTC"
    triggered = alert.triggered_at.strftime(tz_fmt) if alert.triggered_at else "N/A"
    confirmed = alert.confirmed_at.strftime(tz_fmt) if alert.confirmed_at else "Pending"
    
    metadata_row("Triggered At", triggered)
    metadata_row("Confirmed At", confirmed)
    metadata_row("Confirmed By", str(alert.confirmed_by) if alert.confirmed_by else "System")
    metadata_row("Zone ID", str(alert.zone_id))
    
    pdf.ln(10)
    
    # Status Banner
    if alert.confirmed_by:
        pdf.set_fill_color(230, 255, 230) # Light green
        pdf.set_text_color(0, 100, 0)
        status_text = "AUDIT STATUS: CONFIRMED & LOGGED (COMPLIANT)"
    else:
        pdf.set_fill_color(255, 230, 230) # Light red
        pdf.set_text_color(150, 0, 0)
        status_text = "AUDIT STATUS: UNCONFIRMED / PENDING ACTION"
        
    pdf.set_font("Helvetica", size=12, style='B')
    pdf.cell(0, 12, text=status_text, align='C', fill=True, border=1)
    pdf.ln(20)
    
    # Body Text
    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(60, 60, 60)
    body = (
        "This official report certifies that the safety alert was evaluated by the "
        "authorized personnel. According to the regulatory safety frameworks "
        "(including OISD, DGMS, and the Factory Act), immediate remedial action "
        "and/or evacuation protocols have been verified against sensor telemetry.\n\n"
        
        "The underlying AI-detected graph path and localized evidence snapshots "
        "have been preserved in the system's immutable ledger.\n\n"
        
        "This document serves as an official record of compliance for future regulatory "
        "and internal safety audits."
    )
    pdf.multi_cell(0, 7, text=body)
    
    # Signatures
    pdf.ln(30)
    pdf.set_draw_color(150, 150, 150)
    
    y_sig = pdf.get_y()
    # Digital Signature Box
    pdf.line(20, y_sig, 80, y_sig)
    pdf.set_xy(20, y_sig + 2)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(60, 5, "Authorized Digital Signature", align='C')
    
    # System Signature Box
    pdf.line(130, y_sig, 190, y_sig)
    pdf.set_xy(130, y_sig + 2)
    pdf.cell(60, 5, "SentinelGrid System Timestamp", align='C')
    
    try:
        pdf_bytes = pdf.output()
        
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=compliance_report_{alert_id}.pdf"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
