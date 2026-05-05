from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.models import Position

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def dashboard(request: Request, db: Session = Depends(get_db)):
    last_sync = db.query(func.max(Position.snapshot_date)).scalar()

    positions = []
    if last_sync:
        positions = (
            db.query(Position)
            .filter(Position.snapshot_date == last_sync)
            .all()
        )

    total_value = sum(p.market_value_usd or 0.0 for p in positions)

    by_broker: dict[str, float] = {}
    for p in positions:
        key = p.broker or "unknown"
        by_broker[key] = by_broker.get(key, 0.0) + (p.market_value_usd or 0.0)

    return templates.TemplateResponse(request, "dashboard.html", {
        "total_value": total_value,
        "positions_count": len(positions),
        "by_broker": by_broker,
        "last_sync": last_sync,
    })


@router.get("/health")
async def health():
    return {"status": "ok"}
