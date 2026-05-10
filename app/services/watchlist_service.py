"""Watchlist CRUD + price/LLM refresh logic."""

import json
import logging
import time
from datetime import date, datetime

import pandas as pd
import yfinance as yf
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import WatchlistItem
from app.services.llm import MODEL_FAST, _client
from app.services.ticker_analysis import get_ticker_data, validate_ticker

logger = logging.getLogger(__name__)


def _ytd_return(hist_1y: pd.DataFrame) -> float | None:
    """Compute YTD return from already-fetched 1Y history. Avoids extra yfinance call."""
    jan1 = pd.Timestamp(date.today().year, 1, 1, tz="UTC")
    if hist_1y.index.tz is None:
        jan1 = jan1.tz_localize(None)
    ytd = hist_1y[hist_1y.index >= jan1]
    if ytd.empty:
        return None
    return round((float(ytd["Close"].iloc[-1]) / float(ytd["Close"].iloc[0]) - 1) * 100, 1)


def _compute_chart_data(hist: pd.DataFrame) -> dict:
    """Compute chart JSON from yfinance history DataFrame."""
    import pandas_ta as ta

    closes = hist["Close"].tolist()
    n = len(closes)
    dates = [str(d.date()) if hasattr(d, "date") else str(d) for d in hist.index]

    close_series = pd.Series(closes)

    sma_series = ta.sma(close_series, length=200)
    rsi_series = ta.rsi(close_series, length=14)

    def _to_list(series: pd.Series) -> list:
        return [None if pd.isna(v) else round(float(v), 4) for v in series]

    sma = _to_list(sma_series) if sma_series is not None else [None] * n
    rsi = _to_list(rsi_series) if rsi_series is not None else [None] * n

    # Wilder's RSI requires length price changes for initialization.
    # Force first (length-1) entries to None regardless of pandas_ta behavior.
    for i in range(min(13, len(rsi))):
        rsi[i] = None

    return {
        "dates": dates,
        "closes": [round(float(c), 4) for c in closes],
        "sma200": sma,
        "rsi": rsi,
    }


def add_ticker(ticker: str, db: Session) -> WatchlistItem | None:
    """Add ticker to watchlist. Returns existing item if duplicate. None if not found."""
    clean = validate_ticker(ticker)
    if not clean:
        return None

    existing = db.query(WatchlistItem).filter(WatchlistItem.ticker == clean).first()
    if existing:
        return existing

    if db.query(WatchlistItem).count() >= 50:
        raise HTTPException(status_code=400, detail="Watchlist limit: max 50 tickers")

    data = get_ticker_data(clean)
    if data is None:
        return None

    hist = yf.Ticker(clean).history(period="1y")
    chart_data = _compute_chart_data(hist) if not hist.empty else {"dates": [], "closes": [], "sma200": [], "rsi": []}
    ytd = _ytd_return(hist) if not hist.empty else None

    item = WatchlistItem(
        ticker=clean,
        name=data.get("name"),
        currency=data.get("currency", "USD"),
        added_at=datetime.utcnow(),
        last_synced_at=datetime.utcnow(),
        sync_status="ok",
        current_price=data.get("current_price"),
        ytd_return_pct=ytd if ytd is not None else data.get("ytd_return_pct"),
        drawdown_from_peak=data.get("drawdown_from_peak"),
        volatility_pct=data.get("volatility_pct"),
        chart_data_json=json.dumps(chart_data),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_ticker(ticker: str, db: Session) -> bool:
    """Remove ticker from watchlist. Returns False if not found (idempotent)."""
    item = db.query(WatchlistItem).filter(WatchlistItem.ticker == ticker.upper()).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def refresh_prices(db: Session) -> int:
    """Refresh prices + chart data for all watchlist tickers. Returns success count."""
    items = db.query(WatchlistItem).all()
    success = 0

    for item in items:
        t0 = time.monotonic()
        data = get_ticker_data(item.ticker)
        if data is None:
            item.sync_status = "failed"
            item.last_synced_at = datetime.utcnow()
            db.commit()
            status = "failed"
            ms = int((time.monotonic() - t0) * 1000)
            logger.info("watchlist_refresh ticker=%s status=%s duration_ms=%d", item.ticker, status, ms)
            time.sleep(0.5)
            continue

        hist = yf.Ticker(item.ticker).history(period="1y")
        if not hist.empty:
            chart_data = _compute_chart_data(hist)
            item.chart_data_json = json.dumps(chart_data)
            ytd = _ytd_return(hist)
        else:
            ytd = None

        item.current_price = data.get("current_price")
        item.ytd_return_pct = ytd if ytd is not None else data.get("ytd_return_pct")
        item.drawdown_from_peak = data.get("drawdown_from_peak")
        item.volatility_pct = data.get("volatility_pct")
        item.sync_status = "ok"
        item.last_synced_at = datetime.utcnow()
        db.commit()
        success += 1

        ms = int((time.monotonic() - t0) * 1000)
        logger.info("watchlist_refresh ticker=%s status=ok duration_ms=%d", item.ticker, ms)
        time.sleep(0.5)

    return success


def refresh_llm(ticker: str, db: Session) -> str:
    """Run LLM analysis for a watchlist ticker. Returns new text or '' on error."""
    item = db.query(WatchlistItem).filter(WatchlistItem.ticker == ticker.upper()).first()
    if not item:
        return ""

    try:
        data = get_ticker_data(item.ticker)
        if not data:
            return ""

        prompt = (
            f"Проанализируй инвестиционный инструмент на русском языке (макс 200 слов).\n"
            f"Тикер: {item.ticker} ({item.name or item.ticker})\n"
            f"Текущая цена: {item.current_price} {item.currency}\n"
            f"Доходность за год: {item.ytd_return_pct}%\n"
            f"Просадка от максимума: {item.drawdown_from_peak}%\n"
            f"Волатильность (годовая): {item.volatility_pct}%\n\n"
            f"Ответь: 1) Что это за инструмент (1-2 предложения). "
            f"2) Уровень риска и для кого подходит. "
            f"3) Текущий технический сигнал (тренд, поддержка/сопротивление)."
        )
        client = _client()
        resp = client.chat.completions.create(
            model=MODEL_FAST,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return ""
        item.llm_analysis = text
        item.llm_analyzed_at = datetime.utcnow()
        db.commit()
        return text

    except Exception as exc:
        logger.warning("refresh_llm failed for %s: %s", ticker, exc)
        return ""
