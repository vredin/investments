"""Ticker analysis: yfinance market data + LLM narrative via OpenRouter."""

import logging
import re

import yfinance as yf

logger = logging.getLogger(__name__)

_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,20}$")


def validate_ticker(ticker: str) -> str | None:
    """Return cleaned ticker or None if invalid."""
    t = ticker.strip().upper()
    if _TICKER_RE.match(t):
        return t
    return None


def get_ticker_data(ticker: str) -> dict | None:
    """Return price stats dict or None if ticker not found / yfinance unavailable."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if hist.empty:
            return None
        info = t.info
        current = float(hist["Close"].iloc[-1])
        peak_52w = float(hist["Close"].max())
        trough_52w = float(hist["Close"].min())
        ytd_return = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100
        volatility = hist["Close"].pct_change().std() * (252 ** 0.5) * 100
        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker),
            "current_price": round(current, 2),
            "currency": info.get("currency", "USD"),
            "peak_52w": round(peak_52w, 2),
            "trough_52w": round(trough_52w, 2),
            "drawdown_from_peak": round((current - peak_52w) / peak_52w * 100, 1),
            "ytd_return_pct": round(float(ytd_return), 1),
            "volatility_pct": round(float(volatility), 1),
            "expense_ratio": info.get("annualReportExpenseRatio"),
        }
    except Exception as exc:
        logger.warning("get_ticker_data failed for %s: %s", ticker, exc)
        return None


def llm_analyze_ticker(ticker_data: dict, portfolio_tickers: list[str]) -> str:
    """LLM analysis in Russian via OpenRouter. Returns empty string on failure."""
    try:
        from openai import OpenAI

        from app.config import get_settings

        settings = get_settings()
        if not settings.OPENROUTER_API_KEY:
            return ""
        client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            timeout=30,
        )
        portfolio_str = ", ".join(portfolio_tickers) if portfolio_tickers else "пока пустой"
        prompt = (
            f"Проанализируй инвестиционный инструмент на русском языке (макс 200 слов).\n"
            f"Тикер: {ticker_data['ticker']} ({ticker_data['name']})\n"
            f"Текущая цена: {ticker_data['current_price']} {ticker_data['currency']}\n"
            f"52-недельный диапазон: {ticker_data['trough_52w']} — {ticker_data['peak_52w']}\n"
            f"Доходность за год: {ticker_data['ytd_return_pct']}%\n"
            f"Волатильность (годовая): {ticker_data['volatility_pct']}%\n"
            f"Текущий портфель пользователя: {portfolio_str}\n\n"
            f"Ответь: 1) Что это за инструмент (1-2 предложения). "
            f"2) Уровень риска и для кого подходит. "
            f"3) Подходит ли к существующему портфелю или дублирует его."
        )
        resp = client.chat.completions.create(
            model="anthropic/claude-sonnet-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("llm_analyze_ticker failed for %s: %s", ticker_data.get("ticker"), exc)
        return ""
