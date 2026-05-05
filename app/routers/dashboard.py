import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.services import analytics

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def dashboard(request: Request, db: Session = Depends(get_db)):
    data = analytics.compute_dashboard_data(db)
    return templates.TemplateResponse(request, "dashboard.html", {
        **data,
        "donut_labels_json": json.dumps(data["donut_labels"]),
        "donut_current_json": json.dumps([round(v, 2) for v in data["donut_current"]]),
        "donut_target_json": json.dumps([round(v, 2) for v in data["donut_target"]]),
    })


@router.get("/health")
async def health():
    return {"status": "ok"}
