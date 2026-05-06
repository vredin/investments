import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
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
    drawdown = analytics.get_market_drawdown()

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
        "drawdown": drawdown,
        "donut_labels_json": json.dumps(data["donut_labels"]),
        "donut_current_json": json.dumps([round(v, 2) for v in data["donut_current"]]),
        "donut_target_json": json.dumps([round(v, 2) for v in data["donut_target"]]),
        "gc_labels_json": json.dumps(gc["gc_labels"]),
        "gc_expected_json": json.dumps(gc["gc_expected"]),
        "gc_actual_json": json.dumps(list(zip(gc["gc_actual_labels"], gc["gc_actual_values"]))),
    })


@router.get("/api/scenario", dependencies=[Depends(login_required)])
async def scenario(
    db: Session = Depends(get_db),
    budget: float = Query(ge=0, le=100_000),
    return_pct: float = Query(ge=0, le=50),
    years: int = Query(ge=1, le=50),
):
    data = analytics.compute_dashboard_data(db)
    pv = data["total_capital"]
    goal = data["goal_usd"] or 1_300_000.0
    n_months = years * 12
    fv = analytics.fv_projection(pv, budget, return_pct, n_months)
    current_fv = analytics.fv_projection(pv, data["budget_usd"], data["assumed_return"], n_months)
    goal_pct = min(100.0, fv / goal * 100) if goal > 0 else 0.0
    return JSONResponse({
        "fv": round(fv),
        "delta": round(fv - current_fv),
        "goal_pct": round(goal_pct, 1),
    })


@router.get("/crisis", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def crisis(request: Request):
    return templates.TemplateResponse(request, "crisis.html", {})


@router.get("/health")
async def health():
    return {"status": "ok"}
