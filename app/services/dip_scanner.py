"""Dip Scanner — LLM evaluation of watchlist tickers in drawdown."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import WatchlistItem
from app.services.llm import MODEL_FAST, _client

logger = logging.getLogger(__name__)

MAX_SCAN_TICKERS = 15
LLM_CALL_TIMEOUT_S = 12


@dataclass
class DipScanResult:
    ticker: str
    name: str | None
    current_price: float | None
    currency: str | None
    drawdown_pct: float
    rsi_current: float | None
    ytd_return_pct: float | None
    volatility_pct: float | None
    verdict: str   # STRONG BUY | BUY | HOLD | SKIP | ERROR
    rationale: str
    llm_ok: bool


def _extract_rsi(chart_data_json: str | None) -> float | None:
    if not chart_data_json:
        return None
    try:
        data = json.loads(chart_data_json)
        rsi_list = [v for v in data.get("rsi", []) if v is not None]
        return round(float(rsi_list[-1]), 1) if rsi_list else None
    except (json.JSONDecodeError, KeyError, IndexError, ValueError, TypeError):
        return None


def _parse_verdict(text: str) -> tuple[str, str]:
    """Parse LLM response into (verdict, rationale). Defaults to HOLD on unrecognized format."""
    verdict = "HOLD"
    rationale = text.strip()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        upper = line.upper()
        if upper.startswith("VERDICT:"):
            # Normalize: uppercase, strip trailing punctuation
            v = line.split(":", 1)[1].strip().upper().rstrip(".,:;!?")
            if v in {"STRONG BUY", "BUY", "HOLD", "SKIP"}:
                verdict = v
        elif upper.startswith("RATIONALE:"):
            first = line.split(":", 1)[1].strip()
            # Capture all non-empty continuation lines (handles blank lines between sentences)
            rest = " ".join(ln.strip() for ln in lines[i + 1:] if ln.strip())
            rationale = (first + " " + rest).strip() if rest else first
    return verdict, rationale


def _eval_ticker(item: WatchlistItem) -> DipScanResult:
    """Call LLM for one ticker. Returns ERROR result on any failure."""
    rsi = _extract_rsi(item.chart_data_json)
    rsi_str = f"{rsi:.1f}" if rsi is not None else "N/A"
    ytd_str = f"{item.ytd_return_pct:.1f}%" if item.ytd_return_pct is not None else "N/A"
    vol_str = f"{item.volatility_pct:.1f}%" if item.volatility_pct is not None else "N/A"
    price_str = f"{item.current_price:.2f} {item.currency or 'USD'}" if item.current_price else "N/A"

    prompt = (
        f"Оцени тикер {item.ticker} ({item.name or item.ticker}) "
        f"как инвестиционную возможность для покупки на просадке.\n"
        f"Текущие данные: цена {price_str}, "
        f"просадка от 52w max: {item.drawdown_from_peak:.1f}%, "
        f"RSI-14: {rsi_str}, YTD: {ytd_str}, волатильность: {vol_str}.\n\n"
        f"Дай:\n"
        f"1. Verdict: STRONG BUY / BUY / HOLD / SKIP\n"
        f"2. Обоснование (2-3 предложения на русском): что говорят индикаторы о текущей точке входа.\n\n"
        f"Формат ответа:\n"
        f"VERDICT: <слово>\n"
        f"RATIONALE: <текст>"
    )
    try:
        client = _client(timeout=LLM_CALL_TIMEOUT_S)
        resp = client.chat.completions.create(
            model=MODEL_FAST,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return DipScanResult(
                ticker=item.ticker, name=item.name,
                current_price=item.current_price, currency=item.currency,
                drawdown_pct=item.drawdown_from_peak or 0.0,
                rsi_current=rsi, ytd_return_pct=item.ytd_return_pct,
                volatility_pct=item.volatility_pct,
                verdict="ERROR", rationale="LLM вернул пустой ответ", llm_ok=False,
            )
        verdict, rationale = _parse_verdict(text)
        return DipScanResult(
            ticker=item.ticker, name=item.name,
            current_price=item.current_price, currency=item.currency,
            drawdown_pct=item.drawdown_from_peak or 0.0,
            rsi_current=rsi, ytd_return_pct=item.ytd_return_pct,
            volatility_pct=item.volatility_pct,
            verdict=verdict, rationale=rationale, llm_ok=True,
        )
    except Exception as exc:
        logger.warning("dip_scanner LLM failed for %s: %s", item.ticker, exc)
        return DipScanResult(
            ticker=item.ticker, name=item.name,
            current_price=item.current_price, currency=item.currency,
            drawdown_pct=item.drawdown_from_peak or 0.0,
            rsi_current=rsi, ytd_return_pct=item.ytd_return_pct,
            volatility_pct=item.volatility_pct,
            verdict="ERROR", rationale="Оценка временно недоступна", llm_ok=False,
        )


def scan_dips(db: Session, threshold_pct: float = -10.0) -> list[DipScanResult]:
    """Scan watchlist for tickers in drawdown, evaluate each via LLM in parallel.
    Capped at MAX_SCAN_TICKERS (worst drawdown first). Max latency ~LLM_CALL_TIMEOUT_S seconds."""
    items = (
        db.query(WatchlistItem)
        .filter(
            WatchlistItem.drawdown_from_peak <= threshold_pct,
            WatchlistItem.sync_status == "ok",
        )
        .order_by(WatchlistItem.drawdown_from_peak.asc())
        .limit(MAX_SCAN_TICKERS)
        .all()
    )

    if not items:
        return []

    results: list[DipScanResult] = []
    futures: dict = {}

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_eval_ticker, item): item for item in items}
        try:
            for future in as_completed(futures, timeout=60):
                try:
                    results.append(future.result(timeout=LLM_CALL_TIMEOUT_S))
                except Exception as exc:
                    item = futures[future]
                    logger.warning("dip_scanner future failed for %s: %s", item.ticker, exc)
                    results.append(DipScanResult(
                        ticker=item.ticker, name=item.name,
                        current_price=item.current_price, currency=item.currency,
                        drawdown_pct=item.drawdown_from_peak or 0.0,
                        rsi_current=_extract_rsi(item.chart_data_json),
                        ytd_return_pct=item.ytd_return_pct,
                        volatility_pct=item.volatility_pct,
                        verdict="ERROR", rationale="Оценка временно недоступна", llm_ok=False,
                    ))
        except TimeoutError:
            # Collect partial results; mark remaining as TIMEOUT
            completed_tickers = {r.ticker for r in results}
            for item in items:
                if item.ticker not in completed_tickers:
                    results.append(DipScanResult(
                        ticker=item.ticker, name=item.name,
                        current_price=item.current_price, currency=item.currency,
                        drawdown_pct=item.drawdown_from_peak or 0.0,
                        rsi_current=_extract_rsi(item.chart_data_json),
                        ytd_return_pct=item.ytd_return_pct,
                        volatility_pct=item.volatility_pct,
                        verdict="ERROR", rationale="Превышен лимит времени", llm_ok=False,
                    ))

    results.sort(key=lambda r: r.drawdown_pct)
    return results
