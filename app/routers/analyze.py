"""Ticker analysis router — GET/POST /analyze."""

import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.models import Position
from app.services.ticker_analysis import get_ticker_data, llm_analyze_ticker, validate_ticker

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analyze"])
templates = Jinja2Templates(directory="app/templates")


def _portfolio_tickers(db: Session) -> list[str]:
    last_sync = db.query(func.max(Position.snapshot_date)).scalar()
    if not last_sync:
        return []
    rows = db.query(Position.ticker).filter(Position.snapshot_date == last_sync).all()
    return [r.ticker for r in rows]


@router.get("/analyze", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def analyze_get(request: Request):
    return templates.TemplateResponse(request, "analyze.html", {"ticker_data": None, "analysis": None, "error": None})


@router.post("/analyze", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def analyze_post(request: Request, ticker: str = Form(...), db: Session = Depends(get_db)):
    clean = validate_ticker(ticker)
    if not clean:
        return templates.TemplateResponse(request, "analyze.html", {
            "ticker_data": None, "analysis": None,
            "error": "Некорректный тикер. Используйте буквы, цифры, точку или дефис (макс. 20 символов).",
        })

    ticker_data = get_ticker_data(clean)
    if ticker_data is None:
        return templates.TemplateResponse(request, "analyze.html", {
            "ticker_data": None, "analysis": None,
            "error": f"Тикер «{clean}» не найден. Проверьте формат (например VWCE.AS для Амстердама).",
        })

    portfolio = _portfolio_tickers(db)
    analysis = llm_analyze_ticker(ticker_data, portfolio)

    return templates.TemplateResponse(request, "analyze.html", {
        "ticker_data": ticker_data,
        "analysis": analysis,
        "error": None,
        "submitted_ticker": clean,
    })
