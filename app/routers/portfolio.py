from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.models import Position, Transaction

router = APIRouter(prefix="/portfolio", tags=["portfolio"], dependencies=[Depends(login_required)])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def portfolio_page(request: Request, db: Session = Depends(get_db)):
    last_sync = db.query(func.max(Position.snapshot_date)).scalar()

    positions = []
    if last_sync:
        positions = (
            db.query(Position)
            .filter(Position.snapshot_date == last_sync)
            .order_by(Position.market_value_usd.desc().nullslast())
            .all()
        )

    transactions = (
        db.query(Transaction)
        .order_by(Transaction.trade_date.desc())
        .limit(50)
        .all()
    )

    return templates.TemplateResponse(request, "portfolio.html", {
        "positions": positions,
        "transactions": transactions,
        "last_sync": last_sync,
    })
