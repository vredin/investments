---
workflow_progress:
  step_1_grill_me: complete
  step_2_5_prior_knowledge: complete — no prior ADRs, fresh ground
  step_3_research: complete
  step_4_spec: complete
  step_4_5_security: complete
  step_5_diablo: PROCEED_WITH_CAUTION
  step_6_github_issue: https://github.com/vredin/investments/issues/20
---

# T-021: Watchlist — постоянный мониторинг тикеров

**Created**: 2026-05-10
**Risk**: Medium
**Status**: Backlog

## 1. Overview
После анализа тикера на `/analyze` пользователь может добавить его в watchlist (`/watchlist`). Система ежедневно обновляет цены через APScheduler, хранит историю в БД. Детальная страница каждого тикера показывает два Chart.js графика: цена + SMA200 и RSI за 1 год. LLM-анализ обновляется только вручную (кнопка).

## 2. Objectives
- [ ] Кнопка «Добавить в мониторинг» на `/analyze` после результата
- [ ] `GET /watchlist` — список всех отслеживаемых тикеров с текущими ценами
- [ ] `GET /watchlist/{ticker}` — детальная страница: два Chart.js графика + LLM-анализ
- [ ] Удаление тикера из watchlist одним кликом
- [ ] APScheduler daily job обновляет цены и chart_data_json для всех тикеров в watchlist
- [ ] LLM-анализ запускается вручную кнопкой «Обновить анализ» (1 вызов OpenRouter)

## 3. Prerequisites
- APScheduler уже настроен в `app/scheduler.py` (`sync_prices_daily` job, 23:00)
- Chart.js 4.4 уже в `base.html`
- `app/services/llm._client()` — централизованный OpenRouter клиент (T-020 ✓)
- `app/services/ticker_analysis.get_ticker_data()` + `validate_ticker()` — yfinance + validation
- Alembic настроен (1 migration: `0001_initial.py`)
- `app/auth.py:login_required` — Depends decorator для auth (подтверждено)
- `pandas_ta.rsi()`, `pandas_ta.sma()` — доступны в venv (подтверждено)
- Production: `uvicorn --workers 1` (APScheduler single-process requirement)

## 4. Scope
**In scope**:
- DB model `WatchlistItem` + migration 0002
- Service `app/services/watchlist_service.py` (CRUD + price refresh + LLM refresh)
- Router `app/routers/watchlist.py` (7 endpoints)
- Templates: `watchlist.html` (list) + `watchlist_detail.html` (detail + charts)
- Обновление `analyze.html`: кнопка «Добавить»
- Обновление `base.html`: nav link «Мониторинг»
- Обновление `scheduler.py`: вызов watchlist refresh

**Out of scope**:
- Уведомления (email/telegram) при изменении цены
- Экспорт watchlist
- Несколько пользователей (personal app, single user)

## 5. Technical Approach

### 5.1 DB Model
```python
class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)  # always UPPERCASE
    name = Column(String(200))
    currency = Column(String(10), default="USD")
    added_at = Column(DateTime, default=datetime.utcnow)
    last_synced_at = Column(DateTime)
    sync_status = Column(String(10), default="new")  # "ok" | "failed" | "stale" | "new"
    current_price = Column(Float)
    ytd_return_pct = Column(Float)
    drawdown_from_peak = Column(Float)
    volatility_pct = Column(Float)
    llm_analysis = Column(Text)
    llm_analyzed_at = Column(DateTime)
    chart_data_json = Column(Text)  # JSON: {dates, closes, sma200, rsi}
```

**F3-fix: Ticker normalization** — `add_ticker` calls `validate_ticker(ticker)` which does `.strip().upper()` + regex `^[A-Za-z0-9.\-]{1,20}$`. Ticker is stored as upper-case. Duplicate add of `aapl` after `AAPL` → returns existing row, no error.

**S1: Metric definitions (exact formulas)**:
- `ytd_return_pct`: **?5-fix** — fetch `yf.Ticker(t).history(period="ytd")` отдельно от `period="1y"`. `(close[-1] / close[0] - 1) × 100`. Если `period="ytd"` пустой (новый листинг) → `None`.
- `drawdown_from_peak`: `(current - max(close_1y)) / max(close_1y) × 100`. Window: 52 weeks из `period="1y"`. Always ≤ 0.
- `volatility_pct`: `stdev(pct_change(close_1y)) × sqrt(252) × 100`. Annualised, 1-year window.

**S3: Hard cap** — `add_ticker` raises `HTTPException(400, "Watchlist limit: max 50 tickers")` if `db.query(WatchlistItem).count() >= 50`.

### 5.2 Chart data structure (chart_data_json)
```json
{
  "dates": ["2025-05-09", ...],   // ~252 trading days
  "closes": [123.4, ...],
  "sma200": [118.2, null, ...],   // null for first 199 days
  "rsi": [52.1, ...]              // 14-day RSI
}
```
SMA200 и RSI вычисляются из yfinance `hist["Close"]` при refresh. RSI = Wilder's smoothed RSI (стандарт).

### 5.3 Service: `app/services/watchlist_service.py`
```python
def add_ticker(ticker: str, db: Session) -> WatchlistItem | None
def remove_ticker(ticker: str, db: Session) -> bool
def refresh_prices(db: Session) -> int  # returns count refreshed (success only)
def refresh_llm(ticker: str, db: Session) -> str  # returns new analysis
def _compute_chart_data(hist: pd.DataFrame) -> dict
```
**S2-fix: RSI через `pandas_ta.rsi()`** — НЕ ручная реализация. `_calc_rsi` удалена из API. `_compute_chart_data` вызывает `pandas_ta.rsi(pd.Series(closes), length=14)`. Совместимость подтверждена: `uv run python -c "import pandas_ta; import pandas as pd; print(pandas_ta.rsi(pd.Series([1.0]*20), length=14).tolist())"`.

`refresh_prices` вызывает `get_ticker_data()` для каждого тикера per-ticker commit:
- yfinance успех: обновить все поля + `sync_status="ok"`, commit
- yfinance пустой / ошибка: обновить `sync_status="failed"`, НЕ трогать price/chart, commit
- 0.5s delay между тикерами (rate limit)

### 5.4 Router endpoints (6 total)
| Method | Path | Action |
|--------|------|--------|
| GET | /watchlist | Список всех тикеров |
| POST | /watchlist/add | Добавить тикер (form: ticker) |
| POST | /watchlist/{ticker}/remove | Удалить (HTML форма, не DELETE) |
| GET | /watchlist/{ticker} | Детальная страница |
| GET | /watchlist/{ticker}/chart-data | JSON для Chart.js |
| POST | /watchlist/{ticker}/refresh-llm | Запустить LLM анализ |

> HTML-формы не поддерживают DELETE — используем POST /remove.

### 5.5 UI
**watchlist.html** — таблица: Тикер | Название | Цена | YTD% | Drawdown% | Последнее обновление | [Открыть] [Удалить]  
**watchlist_detail.html** — header с ключевыми метриками + два canvas (price+SMA200, RSI) + LLM анализ + кнопка «Обновить анализ».

Chart.js: два отдельных `<canvas>`. Данные через `fetch('/watchlist/{ticker}/chart-data')` при загрузке страницы.

### 5.6 Scheduler
**F1-fix**: `sync_prices_daily` (23:00) и watchlist refresh НЕ должны конкурировать. Watchlist refresh запускается в **06:00** (утро, до торгов) — EOD данные yfinance уже готовы с вечера, конфликта нет.

```python
def refresh_watchlist_daily() -> None:
    from app.db import SessionLocal
    from app.services.watchlist_service import refresh_prices
    with SessionLocal() as db:
        count = refresh_prices(db)
        logger.info("Watchlist refresh complete: %d ok, remaining with sync_status=failed visible in /watchlist", count)

scheduler.add_job(
    refresh_watchlist_daily,
    trigger="cron",
    hour=6, minute=0,
    id="refresh_watchlist_daily",
    replace_existing=True,
    max_instances=1,        # skip if previous run still active
    coalesce=True,          # if missed N times — run once on recovery
    misfire_grace_time=86400,  # S10-fix: catch up after server outage up to 24h
)
```

**S6: Наблюдаемость** — `refresh_prices` логирует структурированно каждый тикер:
```python
logger.info("watchlist_refresh ticker=%s status=%s duration_ms=%d", ticker, status, ms)
```
`/watchlist` список показывает `last_synced_at` + `sync_status` иконку (✓/⚠️/?) в таблице.

**F2-fix: Rolling window policy** — намеренно принято: `chart_data_json` перезаписывается целиком при каждом refresh из yfinance `period="1y"`. Данные могут retroactively измениться при сплитах/дивидендах. Для личного приложения это приемлемо. Документировано в §11.

**?3-fix**: APScheduler BackgroundScheduler работает in-process. Production запускается с `--workers 1`. Development: `uvicorn --reload` пересоздаёт scheduler при каждом изменении — acceptable.

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/models.py` | Добавить `WatchlistItem` |
| `migrations/versions/0002_watchlist.py` | Alembic migration |
| `app/services/watchlist_service.py` | CRUD + refresh логика |
| `app/routers/watchlist.py` | 6 endpoints |
| `app/templates/watchlist.html` | Список тикеров |
| `app/templates/watchlist_detail.html` | Детальная страница + Charts |
| `app/templates/analyze.html` | Кнопка «Добавить в мониторинг» |
| `app/templates/base.html` | Nav link «Мониторинг» |
| `app/scheduler.py` | Добавить refresh job |
| `app/main.py` | Подключить watchlist router |

## 7. Success Criteria
- Functional:
  - POST /analyze → результат показан → кнопка «Добавить в мониторинг» → тикер в watchlist
  - GET /watchlist → таблица с актуальными ценами
  - GET /watchlist/{ticker} → два Chart.js графика рендерятся с реальными данными
  - DELETE из watchlist → тикер исчезает из списка
  - Дублированное добавление одного тикера → idempotent (без 500)
- Tests:
  - `test_watchlist_add_remove`: добавить → проверить в БД → удалить → проверить отсутствие
  - `test_watchlist_refresh_updates_price`: mock yfinance, проверить обновление `current_price` + `sync_status="ok"`
  - `test_scheduler_max_instances` — mock job start, второй trigger → не запускается (max_instances=1)
  - `test_chart_data_structure`: RSI список той же длины что dates
  - `test_duplicate_add`: второй POST на тот же тикер → 200 (не 500)

## 8. Implementation Notes & BQC Risks
| Risk | Mitigation |
|------|------------|
| yfinance rate limit при обновлении многих тикеров | 0.5s delay между запросами в `refresh_prices` |
| Тикер удалён с биржи (hist.empty) | Обновить только `last_synced_at`, не обнулять данные |
| chart_data_json > 64KB при большой истории | Хранить только Close (не OHLCV). ~250 * 3 * 8B = 6KB — ок |
| LLM refresh занимает >30s | Async? Нет — форма POST, редирект, страница перезагружается. Timeout 30s в `_client()` достаточен |
| RSI < 14 дней данных (новый тикер) | `rsi = None` для первых 13 точек |
| Добавление тикера которого нет в yfinance | `add_ticker` возвращает None → flash error |
| Auth: `/watchlist` не защищён | Добавить `login_required` на все endpoints |

Security-reviewed: нет внешних данных от пользователя кроме тикера (валидируется через `validate_ticker()`). SQL injection невозможен (SQLAlchemy ORM). Auth через `login_required`.

## 9. Testing Strategy

**S4-fix: Error-path tests (обязательны)**:

- Unit:
  - `test_compute_chart_data_full_year` — pd.DataFrame с 252 строками, проверить lengths SMA/RSI
  - `test_compute_chart_data_short_history` — 10 строк (IPO), RSI первые 9 = NaN, не кидает
  - `test_add_ticker_not_found` — `get_ticker_data` returns None → `add_ticker` returns None, БД не изменена
  - `test_add_ticker_duplicate` — второй add того же тикера → возвращает existing, count=1
  - `test_add_ticker_limit_exceeded` — 50 тикеров в БД → `add_ticker` raises HTTPException 400
  - `test_refresh_prices_partial_failure` — mock 3 тикера: первый успех, второй yfinance пустой, третий успех → count=2, второй `sync_status="failed"`, price не обнулён
  - `test_refresh_prices_all_fail` — все тикеры пустые → count=0, `sync_status="failed"` для всех
  - `test_refresh_llm_openrouter_error` — `_client()` кидает → `refresh_llm` возвращает `""`, не перезаписывает `llm_analysis`

- Integration:
  - `test_watchlist_crud` — add → проверить в БД → remove → check отсутствие
  - `test_watchlist_refresh_updates_price` — mock `get_ticker_data`, проверить `current_price` + `sync_status="ok"`

- E2E (Playwright):
  - `test_analyze_add_to_watchlist.spec.ts` — POST /analyze → кнопка «Добавить» → /watchlist → тикер виден в таблице
  - `test_watchlist_remove.spec.ts` — кнопка Удалить → тикер исчезает из таблицы
  - `test_watchlist_detail_charts.spec.ts` — открыть `/watchlist/{ticker}` → два canvas существуют, не пустые (data-rendered=true)

- QA Hacker:
  - GET /watchlist без cookie → redirect 302 к /login (не 200)
  - POST /watchlist/add с тикером `'; DROP TABLE--` → validate_ticker отклоняет, 422
  - POST /watchlist/NONEXISTENT/remove → 200 (idempotent, не 404/500)
  - GET /watchlist/{ticker}/chart-data с corrupted chart_data_json → 200 + `{"error": "no data"}` (не 500)

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| DB Models | high | `app/models.py` |
| Migration | high | `migrations/versions/0002_*.py` |
| Service | high | `app/services/watchlist_service.py` (новый) |
| Router | high | `app/routers/watchlist.py` (новый) |
| Templates | medium | watchlist.html, watchlist_detail.html (новые) + analyze.html, base.html |
| Scheduler | low | `app/scheduler.py` |
| App init | low | `app/main.py` |
| Tests | high | `tests/test_watchlist.py` (новый) |

## 11. Red Flags
- **F2 (accepted)**: `chart_data_json` перезаписывается из `yfinance period="1y"` при каждом refresh. Retroactive mutation при сплитах/дивидендах приемлема для личного долгосрочного инвестора.
- `chart_data_json` как Text — для ≤50 тикеров (~6KB каждый) достаточно. `/watchlist` list view НЕ читает этот столбец (использовать `defer()` или `load_only()` в ORM query).
- RSI через `pandas_ta.rsi()` — подтверждено совместимость с venv. SMA через `pandas_ta.sma()` аналогично.
- `refresh_prices` — commit per-ticker (не per-batch). Частичное обновление при сбое: `sync_status="failed"` видно в UI. Приемлемо.
- HTML-DELETE через POST `/remove` — форма POST, не JavaScript DELETE. Проще, надёжнее для Jinja.
- **?4**: VPS timezone — проверить `docker-compose.yml` TZ или системный timezone. Если UTC — watchlist refresh 06:00 UTC = 08:00 CEST = до торгов, OK.
- **S7**: `validate_ticker` regex: `^[A-Za-z0-9.\-]{1,20}$` — та же функция что в `/analyze`. Цитировать в коде, не дублировать.
- **S8**: `login_required` уже существует в `app/auth.py:34`. Применять через `Depends(login_required)` на все router endpoints — как в `analyze.py`.
- **?6**: `pandas_ta.rsi()` возвращает `pd.Series` с `NaN` для первых 13 точек. JSON сериализация: `rsi_series.where(pd.notna(rsi_series), other=None).tolist()` — `NaN` → `null` → JavaScript `null`. Chart.js игнорирует `null` точки (не рисует gap). Проверить явно в `test_compute_chart_data_full_year`.

## 12. Dependencies
- `pandas_ta` уже в `pyproject.toml` — RSI через `pandas_ta.rsi()`
- `apscheduler` — уже в deps
- Нет новых зависимостей
