import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.models import ProgressSnapshot
from app.services import analytics

router = APIRouter(prefix="/report", tags=["report"], dependencies=[Depends(login_required)])
templates = Jinja2Templates(directory="app/templates")

_MONTH_RE = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")


@router.get("/{month}", response_class=HTMLResponse)
async def report_page(request: Request, month: str, db: Session = Depends(get_db)):
    if not _MONTH_RE.match(month):
        from datetime import date
        return RedirectResponse(url=f"/report/{date.today().strftime('%Y-%m')}", status_code=302)

    data = analytics.compute_dashboard_data(db)
    snapshot = analytics.upsert_snapshot(db, month, data)
    narrative = analytics.llm_report_narrative(month, data)

    snapshots = (
        db.query(ProgressSnapshot)
        .order_by(ProgressSnapshot.month.desc())
        .limit(12)
        .all()
    )

    return templates.TemplateResponse(request, "report.html", {
        "month": month,
        "snapshot": snapshot,
        "narrative": narrative,
        "snapshots": snapshots,
        **data,
    })
