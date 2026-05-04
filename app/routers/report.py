from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import login_required

router = APIRouter(prefix="/report", tags=["report"], dependencies=[Depends(login_required)])
templates = Jinja2Templates(directory="app/templates")


@router.get("/{month}", response_class=HTMLResponse)
async def report_page(request: Request, month: str):
    # Phase 03: call monitor.generate_monthly_report(month, db)
    return templates.TemplateResponse(request, "report.html", {"month": month})
