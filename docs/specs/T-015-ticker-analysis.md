# T-015: Анализ произвольного тикера через LLM + yfinance

**Created**: 2026-05-06
**Risk**: Medium
**Status**: Backlog

## 1. Overview
Пользователь хочет добавить в портфель MSFT, GLD или BTC-USD и понять: стоит ли?
Новая страница /analyze: вводишь тикер → система получает данные из yfinance →
LLM делает анализ на русском: что это, риск, корреляция с текущим портфелем, вывод.

## 2. Objectives
- [ ] Форма ввода тикера на странице /analyze
- [ ] yfinance: 1 год истории, текущая цена, 52w max/min, YTD доходность, волатильность
- [ ] LLM-анализ на русском (OpenRouter): что это за инструмент, риск, подходит ли к текущему портфелю
- [ ] Показать основные метрики + текст анализа
- [ ] Graceful error если тикер не найден в yfinance

## 3. Scope
**In scope**:
- `app/routers/analyze.py`: GET /analyze (форма) + POST /analyze (результат)
- `app/services/ticker_analysis.py`: `get_ticker_data(ticker)` + `llm_analyze_ticker(ticker, data, portfolio_summary)`
- `app/templates/analyze.html`: форма + результаты
- Подключить к nav в base.html ("Анализ тикера")

**Out of scope**: сохранение результатов анализа в БД, сравнение нескольких тикеров одновременно, добавление тикера в портфель прямо из формы

## 5. Technical Approach

```python
# ticker_analysis.py

def get_ticker_data(ticker: str) -> dict | None:
    """Returns dict with price stats or None if ticker not found."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if hist.empty:
            return None
        info = t.info
        current = hist["Close"].iloc[-1]
        peak_52w = hist["Close"].max()
        trough_52w = hist["Close"].min()
        ytd_return = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100
        volatility = hist["Close"].pct_change().std() * (252 ** 0.5) * 100  # annualized
        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker),
            "current_price": round(current, 2),
            "currency": info.get("currency", "USD"),
            "peak_52w": round(peak_52w, 2),
            "trough_52w": round(trough_52w, 2),
            "drawdown_from_peak": round((current - peak_52w) / peak_52w * 100, 1),
            "ytd_return_pct": round(ytd_return, 1),
            "volatility_pct": round(volatility, 1),
            "expense_ratio": info.get("annualReportExpenseRatio"),
        }
    except Exception:
        return None


def llm_analyze_ticker(ticker_data: dict, portfolio_tickers: list[str]) -> str:
    """LLM analysis: what is it, risk level, fit with current portfolio."""
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
    # OpenRouter call (same pattern as recommender.py)
    ...
```

Роутер POST /analyze → `get_ticker_data()` → если None → flash "Тикер не найден" →
иначе `llm_analyze_ticker()` → render analyze.html с данными.

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/routers/analyze.py` | GET + POST /analyze |
| `app/services/ticker_analysis.py` | yfinance data + LLM analysis |
| `app/templates/analyze.html` | Форма + метрики + LLM текст |
| `app/main.py` | Подключить router |
| `app/templates/base.html` | Добавить "Анализ" в nav |

## 7. Success Criteria
- POST /analyze с ticker="MSFT" возвращает данные и LLM-анализ
- Несуществующий тикер "XYZXYZ" → flash-сообщение "Тикер не найден", нет 500
- yfinance недоступен → graceful error, нет 500
- LLM недоступен → показывает только цифровые метрики, без анализа

## 8. BQC Risks
| Risk | Mitigation |
|------|------------|
| Injection через ticker input | yfinance принимает только строки, не SQL; LLM prompt hardcoded |
| yfinance rate limit | try/except → None → flash error |
| LLM timeout | timeout=30, except → "Анализ временно недоступен" |
| Очень длинный ticker (DoS) | Validate len(ticker) <= 20, strip() |

Security-reviewed: LOW risk — ticker input goes to yfinance (no SQL), not to DB as-is.
Input validation: max 20 chars, alphanumeric + dot/dash.

## 9. Testing Strategy
- Unit: `get_ticker_data` mock yfinance → проверить структуру возврата
- Unit: yfinance exception → None
- Unit: `llm_analyze_ticker` mock OpenAI → проверить промпт содержит ticker
- E2E: GET /analyze → форма есть, POST с "VWCE.AS" → 200 без 500

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Service | medium | ticker_analysis.py |
| Router | medium | analyze.py |
| Templates | medium | analyze.html, base.html |
| Tests | medium | test_ticker_analysis.py |

## 11. Red Flags
- yfinance иногда меняет API без предупреждения — тест должен мокировать
- LLM может не знать малоизвестные тикеры — в промпте есть числовые данные как контекст
- Тикеры на разных биржах: VWCE нужен как VWCE.AS (Амстердам) — пользователь должен знать правильный формат

## 12. Dependencies
- yfinance (уже в зависимостях)
- openai / OpenRouter (уже есть)
