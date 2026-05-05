import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.models import ProgressSnapshot
from app.services import analytics

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def dashboard(request: Request, db: Session = Depends(get_db)):
    data = analytics.compute_dashboard_data(db)

    snapshots = (
        db.query(ProgressSnapshot)
        .order_by(ProgressSnapshot.month)
        .all()
    )
    gc = analytics.build_goal_chart_data(
        data["total_capital"],
        data["budget_usd"],
        data["assumed_return"],
        data["goal_usd"],
        snapshots,
    )

    return templates.TemplateResponse(request, "dashboard.html", {
        **data,
        **gc,
        "donut_labels_json": json.dumps(data["donut_labels"]),
        "donut_current_json": json.dumps([round(v, 2) for v in data["donut_current"]]),
        "donut_target_json": json.dumps([round(v, 2) for v in data["donut_target"]]),
        "gc_labels_json": json.dumps(gc["gc_labels"]),
        "gc_expected_json": json.dumps(gc["gc_expected"]),
        "gc_actual_json": json.dumps(list(zip(gc["gc_actual_labels"], gc["gc_actual_values"]))),
    })


@router.get("/health")
async def health():
    return {"status": "ok"}
