"""Watchlist router — /watchlist endpoints."""

import json
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.models import WatchlistItem
from app.services import settings_service
from app.services.dip_scanner import scan_dips
from app.services.ticker_analysis import validate_ticker
from app.services.watchlist_service import add_ticker, refresh_llm, remove_ticker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/watchlist", tags=["watchlist"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def watchlist_list(request: Request, db: Session = Depends(get_db)):
    items = db.query(
        WatchlistItem.id,
        WatchlistItem.ticker,
        WatchlistItem.name,
        WatchlistItem.currency,
        WatchlistItem.current_price,
        WatchlistItem.ytd_return_pct,
        WatchlistItem.drawdown_from_peak,
        WatchlistItem.last_synced_at,
        WatchlistItem.sync_status,
    ).all()
    return templates.TemplateResponse(request, "watchlist.html", {"items": items})


@router.post("/add", dependencies=[Depends(login_required)])
async def watchlist_add(request: Request, ticker: str = Form(...), db: Session = Depends(get_db)):
    result = add_ticker(ticker, db)
    if result is None:
        request.session["flash"] = {"type": "error", "msg": f"Тикер «{ticker.upper()}» не найден в yfinance."}
    else:
        request.session["flash"] = {"type": "success", "msg": f"{result.ticker} добавлен в мониторинг."}
    return RedirectResponse(url="/watchlist", status_code=303)


@router.post("/{ticker}/remove", dependencies=[Depends(login_required)])
async def watchlist_remove(ticker: str, request: Request, db: Session = Depends(get_db)):
    clean = validate_ticker(ticker)
    if not clean:
        raise HTTPException(status_code=422, detail="invalid ticker")
    remove_ticker(clean, db)
    return RedirectResponse(url="/watchlist", status_code=303)


@router.get("/scan", response_class=HTMLResponse, dependencies=[Depends(login_required)])
def watchlist_scan(request: Request, db: Session = Depends(get_db)):
    threshold = settings_service.get_float(db, "btd_threshold_pct") or -10.0
    results = scan_dips(db, threshold_pct=threshold)
    total = db.query(WatchlistItem).count()
    return templates.TemplateResponse(request, "watchlist_scan.html", {
        "results": results,
        "threshold": threshold,
        "total_watchlist": total,
    })


@router.get("/{ticker}", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def watchlist_detail(ticker: str, request: Request, db: Session = Depends(get_db)):
    clean = validate_ticker(ticker)
    if not clean:
        raise HTTPException(status_code=422, detail="invalid ticker")
    item = db.query(WatchlistItem).filter(WatchlistItem.ticker == clean).first()
    if not item:
        request.session["flash"] = {"type": "error", "msg": f"Тикер {clean} не в watchlist."}
        return RedirectResponse(url="/watchlist", status_code=303)
    return templates.TemplateResponse(request, "watchlist_detail.html", {"item": item})


@router.get("/{ticker}/chart-data", dependencies=[Depends(login_required)])
async def watchlist_chart_data(ticker: str, db: Session = Depends(get_db)):
    clean = validate_ticker(ticker)
    if not clean:
        raise HTTPException(status_code=422, detail="invalid ticker")
    item = db.query(WatchlistItem.chart_data_json).filter(
        WatchlistItem.ticker == clean
    ).first()
    if not item or not item.chart_data_json:
        return JSONResponse({"error": "no data"})
    try:
        data = json.loads(item.chart_data_json)
        return JSONResponse(data)
    except (json.JSONDecodeError, ValueError):
        return JSONResponse({"error": "no data"})


@router.post("/{ticker}/refresh-llm", dependencies=[Depends(login_required)])
async def watchlist_refresh_llm(ticker: str, request: Request, db: Session = Depends(get_db)):
    clean = validate_ticker(ticker)
    if not clean:
        raise HTTPException(status_code=422, detail="invalid ticker")
    result = refresh_llm(clean, db)
    if result:
        request.session["flash"] = {"type": "success", "msg": "Анализ обновлён."}
    else:
        request.session["flash"] = {"type": "error", "msg": "Не удалось обновить анализ."}
    return RedirectResponse(url=f"/watchlist/{clean}", status_code=303)
