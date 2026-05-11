"""Unit tests for dip_scanner service."""

import json
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _extract_rsi
# ---------------------------------------------------------------------------

def test_extract_rsi_from_json():
    from app.services.dip_scanner import _extract_rsi

    chart = json.dumps({"rsi": [None, None, 45.2, 48.7, 52.1]})
    assert _extract_rsi(chart) == 52.1


def test_extract_rsi_empty_json():
    from app.services.dip_scanner import _extract_rsi

    assert _extract_rsi(None) is None
    assert _extract_rsi("") is None
    assert _extract_rsi("{}") is None
    assert _extract_rsi(json.dumps({"rsi": []})) is None
    assert _extract_rsi(json.dumps({"rsi": [None, None]})) is None


def test_extract_rsi_malformed_json():
    from app.services.dip_scanner import _extract_rsi

    assert _extract_rsi("not-json") is None
    assert _extract_rsi(json.dumps({"dates": ["2025-01-01"]})) is None  # no rsi key


# ---------------------------------------------------------------------------
# _parse_verdict
# ---------------------------------------------------------------------------

def test_parse_verdict_strong_buy():
    from app.services.dip_scanner import _parse_verdict

    text = "VERDICT: STRONG BUY\nRATIONALE: Тикер глубоко перепродан по RSI."
    verdict, rationale = _parse_verdict(text)
    assert verdict == "STRONG BUY"
    assert "перепродан" in rationale


def test_parse_verdict_buy():
    from app.services.dip_scanner import _parse_verdict

    verdict, _ = _parse_verdict("VERDICT: BUY\nRATIONALE: Хороший уровень.")
    assert verdict == "BUY"


def test_parse_verdict_skip():
    from app.services.dip_scanner import _parse_verdict

    verdict, _ = _parse_verdict("VERDICT: SKIP\nRATIONALE: Нисходящий тренд.")
    assert verdict == "SKIP"


def test_parse_verdict_default_hold():
    from app.services.dip_scanner import _parse_verdict

    # LLM responded but without recognized format → default HOLD, llm_ok=True in caller
    verdict, rationale = _parse_verdict("Непонятный текст без тегов.")
    assert verdict == "HOLD"
    assert "Непонятный" in rationale


def test_parse_verdict_hold_explicit():
    from app.services.dip_scanner import _parse_verdict

    verdict, _ = _parse_verdict("VERDICT: HOLD\nRATIONALE: Ждать сигнала.")
    assert verdict == "HOLD"


def test_parse_verdict_multiline_rationale():
    """All RATIONALE lines must be captured, not just the first."""
    from app.services.dip_scanner import _parse_verdict

    text = (
        "VERDICT: BUY\n"
        "RATIONALE: RSI опустился ниже 35 — зона перепроданности.\n"
        "Цена у поддержки SMA200.\n"
        "Хорошая точка входа для долгосрочного портфеля."
    )
    verdict, rationale = _parse_verdict(text)
    assert verdict == "BUY"
    assert "RSI" in rationale
    assert "SMA200" in rationale
    assert "долгосрочного" in rationale


def test_parse_verdict_exact_match_only():
    """Substring match rejected — 'NO BUY' or 'STRONGER BUY' must NOT match BUY."""
    from app.services.dip_scanner import _parse_verdict

    verdict, _ = _parse_verdict("VERDICT: NO BUY\nRATIONALE: Нет.")
    assert verdict == "HOLD"  # unrecognized → default HOLD

    verdict2, _ = _parse_verdict("VERDICT: STRONGER BUY\nRATIONALE: Очень хорошо.")
    assert verdict2 == "HOLD"  # not in exact set


def test_parse_verdict_mixed_case_and_punctuation():
    """'Buy' (mixed case) and 'BUY.' (trailing dot) both normalize to BUY."""
    from app.services.dip_scanner import _parse_verdict

    v1, _ = _parse_verdict("VERDICT: Buy\nRATIONALE: ОК.")
    assert v1 == "BUY"

    v2, _ = _parse_verdict("VERDICT: BUY.\nRATIONALE: ОК.")
    assert v2 == "BUY"


def test_parse_verdict_blank_line_in_rationale():
    """LLM often puts blank line between RATIONALE label and text."""
    from app.services.dip_scanner import _parse_verdict

    text = "VERDICT: SKIP\nRATIONALE:\n\nТренд нисходящий.\nRSI выше 60."
    verdict, rationale = _parse_verdict(text)
    assert verdict == "SKIP"
    assert "нисходящий" in rationale
    assert "RSI" in rationale


# ---------------------------------------------------------------------------
# scan_dips — filtering
# ---------------------------------------------------------------------------

def _make_item(ticker, drawdown, sync_status="ok", chart_json=None):
    from app.models import WatchlistItem

    item = WatchlistItem()
    item.ticker = ticker
    item.name = f"{ticker} Inc"
    item.current_price = 100.0
    item.currency = "USD"
    item.drawdown_from_peak = drawdown
    item.ytd_return_pct = 5.0
    item.volatility_pct = 20.0
    item.sync_status = sync_status
    item.chart_data_json = chart_json or json.dumps({"rsi": [None] * 13 + [42.0, 40.0]})
    return item


def test_scan_dips_filters_by_threshold():
    """Only tickers with drawdown <= threshold and sync_status=ok qualify."""
    from app.services.dip_scanner import scan_dips

    item_below = _make_item("AAPL", -15.0)
    item_at = _make_item("MSFT", -10.0)
    item_above = _make_item("GOOG", -5.0)

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        item_below, item_at
    ]

    llm_text = "VERDICT: BUY\nRATIONALE: Хороший момент."

    with patch("app.services.dip_scanner._eval_ticker", side_effect=lambda item: __import__(
        "app.services.dip_scanner", fromlist=["DipScanResult"]
    ).DipScanResult(
        ticker=item.ticker, name=item.name, current_price=item.current_price,
        currency=item.currency, drawdown_pct=item.drawdown_from_peak,
        rsi_current=40.0, ytd_return_pct=item.ytd_return_pct,
        volatility_pct=item.volatility_pct,
        verdict="BUY", rationale="Хороший момент", llm_ok=True,
    )):
        results = scan_dips(db, threshold_pct=-10.0)

    assert len(results) == 2
    tickers = [r.ticker for r in results]
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert "GOOG" not in tickers


def test_scan_dips_excludes_failed_status():
    """Tickers with sync_status != ok are excluded at DB query level."""
    from app.services.dip_scanner import scan_dips

    db = MagicMock()
    # DB returns empty (failed tickers filtered by query)
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    results = scan_dips(db, threshold_pct=-10.0)
    assert results == []


def test_scan_dips_empty_watchlist():
    """Empty watchlist → empty results, no LLM calls."""
    from app.services.dip_scanner import scan_dips

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    results = scan_dips(db, threshold_pct=-10.0)
    assert results == []


def test_scan_dips_llm_error_returns_error_verdict():
    """LLM exception → verdict=ERROR, llm_ok=False. Other tickers not affected."""
    from app.services.dip_scanner import DipScanResult, scan_dips

    item1 = _make_item("VWCE", -12.0)
    item2 = _make_item("CSPX", -11.0)

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        item1, item2
    ]

    call_count = {"n": 0}

    def mock_eval(item):
        call_count["n"] += 1
        if item.ticker == "VWCE":
            raise RuntimeError("OpenRouter 503")
        return DipScanResult(
            ticker=item.ticker, name=item.name, current_price=item.current_price,
            currency=item.currency, drawdown_pct=item.drawdown_from_peak,
            rsi_current=38.0, ytd_return_pct=item.ytd_return_pct,
            volatility_pct=item.volatility_pct,
            verdict="BUY", rationale="OK", llm_ok=True,
        )

    with patch("app.services.dip_scanner._eval_ticker", side_effect=mock_eval):
        results = scan_dips(db, threshold_pct=-10.0)

    assert len(results) == 2
    vwce = next(r for r in results if r.ticker == "VWCE")
    cspx = next(r for r in results if r.ticker == "CSPX")
    assert vwce.verdict == "ERROR"
    assert vwce.llm_ok is False
    assert cspx.verdict == "BUY"
    assert cspx.llm_ok is True
