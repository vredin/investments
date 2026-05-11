---
workflow_progress:
  step_1_grill_me: complete
  step_2_5_prior_knowledge: complete — BTD threshold already in settings (btd_threshold_pct=-10), BTD service exists in recommender.py
  step_3_research: complete — -10% standard correction threshold per Faber 2007 + industry practice; reuse existing setting
  step_4_spec: complete
  step_4_5_security: complete — no new user input, no file ops, LLM cost cap via 50-ticker limit
  step_5_diablo: PROCEED_WITH_CAUTION
  step_6_github_issue: https://github.com/vredin/investments/issues/21
---

# T-022: Dip Scanner — LLM-оценка просадок в watchlist

**Created**: 2026-05-11
**Risk**: Low
**Status**: Backlog

## 1. Overview
Кнопка «Скан просадок» на `/watchlist` запускает проверку всех тикеров в watchlist: те, у кого `drawdown_from_peak <= btd_threshold_pct` (дефолт -10%), отправляются на LLM-оценку. LLM возвращает verdict (STRONG BUY / BUY / HOLD / SKIP) + 2-3 предложения обоснования по техническим индикаторам. Результаты рендерятся на отдельной странице `/watchlist/scan`.

## 2. Objectives
- [ ] `GET /watchlist/scan` — запускает сканирование watchlist, рендерит результаты
- [ ] Фильтрация: тикеры с `drawdown_from_peak <= btd_threshold_pct`
- [ ] LLM-оценка каждого отфильтрованного тикера: verdict + rationale (2-3 предложения)
- [ ] Результаты отсортированы по drawdown (наибольшая просадка первой)
- [ ] Кнопка «Скан просадок» на `/watchlist`
- [ ] Если ни один тикер не попадает под порог → информативное сообщение

## 3. Prerequisites
- `WatchlistItem.drawdown_from_peak` — уже заполняется при `refresh_prices`
- `WatchlistItem.chart_data_json` — содержит RSI данные (последнее значение = текущий RSI)
- `btd_threshold_pct` в settings (значение = -10.0 по умолчанию, уже настроено)
- `app/services/llm._client()` + `MODEL_FAST` — централизованный OpenRouter клиент
- `app/auth.login_required` — auth decorator
- `samesite=strict` на сессионной куке (T-021 DA-fix ✓)

## 4. Scope
**In scope**:
- Service `app/services/dip_scanner.py` — scan + LLM evaluation
- Endpoint `GET /watchlist/scan` в `app/routers/watchlist.py`
- Template `app/templates/watchlist_scan.html`
- Кнопка «Скан просадок» в `watchlist.html`

**Out of scope**:
- Уведомления (email/telegram) при появлении сигнала
- Хранение истории сканирований в БД
- Тикеры вне watchlist (отдельный universe)
- Автоматический scheduled scan (on-demand only)
- Кастомизация порога через UI (используем `btd_threshold_pct` из settings)

## 5. Technical Approach

### 5.1 Service: `app/services/dip_scanner.py`

```python
MAX_SCAN_TICKERS = 15  # hard cap per scan; LLM cost + latency control

@dataclass
class DipScanResult:
    ticker: str
    name: str | None
    current_price: float | None
    drawdown_pct: float   # e.g. -15.3
    rsi_current: float | None
    ytd_return_pct: float | None
    verdict: str          # "STRONG BUY" | "BUY" | "HOLD" | "SKIP" | "ERROR"
    rationale: str
    llm_ok: bool          # False when LLM call failed (shown as badge in UI)

def scan_dips(db: Session, threshold_pct: float = -10.0) -> list[DipScanResult]:
    """Scan watchlist for tickers in drawdown, evaluate each via LLM.
    Capped at MAX_SCAN_TICKERS worst drawdowns. Parallel LLM calls via ThreadPoolExecutor."""
```

**F1-fix: Параллельные LLM-вызовы с cap + per-call timeout:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout

MAX_SCAN_TICKERS = 15
LLM_CALL_TIMEOUT_S = 12  # per-ticker LLM budget

def scan_dips(db, threshold_pct=-10.0):
    items = db.query(WatchlistItem).filter(
        WatchlistItem.drawdown_from_peak <= threshold_pct,
        WatchlistItem.sync_status == "ok",
    ).order_by(WatchlistItem.drawdown_from_peak.asc()).limit(MAX_SCAN_TICKERS).all()

    results = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_eval_ticker, item): item for item in items}
        for future in as_completed(futures, timeout=60):
            try:
                results.append(future.result(timeout=LLM_CALL_TIMEOUT_S))
            except Exception:
                item = futures[future]
                results.append(DipScanResult(
                    ticker=item.ticker, ..., verdict="ERROR",
                    rationale="Оценка временно недоступна", llm_ok=False
                ))
    results.sort(key=lambda r: r.drawdown_pct)
    return results
```
Max latency: `LLM_CALL_TIMEOUT_S = 12s` (worst case single-threaded), parallel → ~12s total for 15 tickers.

**Фильтрация:**
```python
items = db.query(WatchlistItem).filter(
    WatchlistItem.drawdown_from_peak <= threshold_pct,
    WatchlistItem.sync_status == "ok",  # только актуальные данные
).order_by(WatchlistItem.drawdown_from_peak.asc()).all()  # наибольшая просадка первой
```

**Извлечение текущего RSI** из `chart_data_json`:
```python
def _extract_rsi(chart_data_json: str | None) -> float | None:
    if not chart_data_json:
        return None
    try:
        data = json.loads(chart_data_json)
        rsi_list = [v for v in data.get("rsi", []) if v is not None]
        return rsi_list[-1] if rsi_list else None
    except (json.JSONDecodeError, KeyError, IndexError):
        return None
```

**LLM-оценка** (одна для каждого тикера, бесплатная с MODEL_FAST):
```
Prompt: "Оцени тикер {ticker} ({name}) как инвестиционную возможность для покупки на просадке.
Текущие данные: цена {price} {currency}, просадка от 52w max: {drawdown}%,
RSI-14: {rsi}, YTD: {ytd}%, волатильность: {vol}%.

Дай:
1. Verdict: STRONG BUY / BUY / HOLD / SKIP (одно слово/фраза)
2. Обоснование (2-3 предложения на русском): что говорят индикаторы о текущей точке входа.

Формат ответа:
VERDICT: <слово>
RATIONALE: <текст>"
```

**Parsing verdict из LLM-ответа:**
```python
def _parse_verdict(text: str) -> tuple[str, str]:
    verdict = "HOLD"  # default
    rationale = text
    for line in text.splitlines():
        if line.upper().startswith("VERDICT:"):
            v = line.split(":", 1)[1].strip().upper()
            if any(kw in v for kw in ["STRONG", "BUY", "HOLD", "SKIP"]):
                verdict = "STRONG BUY" if "STRONG" in v else ("BUY" if "BUY" in v else ("SKIP" if "SKIP" in v else "HOLD"))
        elif line.upper().startswith("RATIONALE:"):
            rationale = line.split(":", 1)[1].strip()
    return verdict, rationale
```

**F2-fix: LLM error ≠ HOLD:**
- LLM-вызов упал (Exception / timeout) → `verdict="ERROR"`, `llm_ok=False`, `rationale="Оценка временно недоступна"`
- LLM вернул пустую строку → `verdict="ERROR"`, `llm_ok=False`
- LLM вернул текст без VERDICT: → `verdict="HOLD"`, `llm_ok=True` (модель ответила, но нестандартно)
- В UI: ERROR показывается серым badge, не зелёным/жёлтым — пользователь видит разницу

### 5.2 Router endpoint

```python
@router.get("/scan", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def watchlist_scan(request: Request, db: Session = Depends(get_db)):
    threshold = settings_service.get_float(db, "btd_threshold_pct") or -10.0
    results = scan_dips(db, threshold_pct=threshold)
    return templates.TemplateResponse(request, "watchlist_scan.html", {
        "results": results,
        "threshold": threshold,
        "total_watchlist": db.query(WatchlistItem).count(),
    })
```

**Важно:** маршрут `/watchlist/scan` должен быть зарегистрирован ДО `/watchlist/{ticker}`, иначе FastAPI попытается матчить "scan" как `{ticker}`. Проверить порядок в роутере.

### 5.3 Template: `watchlist_scan.html`

- Хедер: «Скан просадок (порог: {threshold}%)» + «{len(results)} тикеров ниже порога»
- Если results пусто: блок «Все тикеры в watchlist выше порога {threshold}% — просадок не обнаружено»
- Cards с verdict-badge (цвет по verdict):
  - STRONG BUY → зелёный (#16a34a)
  - BUY → светло-зелёный (#4ade80)
  - HOLD → жёлтый (#f59e0b)
  - SKIP → красный (#dc2626)
- Каждая карточка: тикер | просадка% | RSI | YTD% | rationale
- Ссылка «← Мониторинг»

### 5.4 Button в `watchlist.html`

```html
<a href="/watchlist/scan" class="scan-btn">📊 Скан просадок</a>
```
Рядом с заголовком страницы, справа от «+ Добавить».

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/services/dip_scanner.py` | scan_dips + LLM evaluation |
| `app/routers/watchlist.py` | Добавить GET /watchlist/scan (перед {ticker}) |
| `app/templates/watchlist_scan.html` | Результаты сканирования |
| `app/templates/watchlist.html` | Кнопка «Скан просадок» |

## 7. Success Criteria
- Functional:
  - `/watchlist/scan` → список тикеров с drawdown ≤ -10% + verdict + rationale
  - Тикеры с `sync_status != "ok"` исключены (устаревшие данные)
  - Если нет кандидатов → «просадок не обнаружено» (не 500)
  - Verdict корректно парсится из LLM-ответа
  - LLM-ошибка для одного тикера → verdict="SKIP", scan продолжается
- Tests:
  - `test_extract_rsi_from_json` — корректное извлечение последнего RSI
  - `test_extract_rsi_empty_json` — None при пустом/null JSON
  - `test_parse_verdict_strong_buy` — парсинг "VERDICT: STRONG BUY"
  - `test_parse_verdict_default_hold` — дефолт HOLD при нераспознанном ответе
  - `test_scan_dips_filters_by_threshold` — mock DB, 3 тикера: 2 ниже порога, 1 выше → 2 результата
  - `test_scan_dips_excludes_failed_status` — тикеры с sync_status="failed" исключены
  - `test_scan_dips_llm_error_returns_skip` — LLM упал → verdict="SKIP", другие тикеры не затронуты

## 8. Implementation Notes & BQC Risks
| Risk | Mitigation |
|------|------------|
| LLM cost amplification (50 тикеров × 50 вызовов) | Макс 50 тикеров в watchlist (уже ограничено); MODEL_FAST (~$0.01 total) |
| Порядок маршрутов FastAPI | `/scan` должен быть ДО `/{ticker}` в роутере |
| LLM-ответ не в ожидаемом формате | Robust parsing с дефолтом HOLD + полный текст как rationale |
| `chart_data_json` не заполнен (новый тикер) | `_extract_rsi` возвращает None → LLM получит RSI=N/A |
| sync_status="failed" с устаревшим drawdown | Фильтр `sync_status == "ok"` исключает ненадёжные данные |
| Scan занимает >30s при 50 тикерах (LLM timeout) | MODEL_FAST быстрый (~1s/call); 50 вызовов ~50s — но они НЕ последовательные в том смысле, что FastAPI не async-блокируется (да, run_in_threadpool нужен?) |

**S1-fix**: LLM-вызовы синхронные в async endpoint — нужен `run_in_executor` или сделать endpoint sync. Поскольку FastAPI + sync `Session` уже используется в других роутерах — использовать sync def endpoint (FastAPI автоматически запускает в threadpool).

Security-reviewed: нет нового пользовательского ввода. Все данные из БД (watchlist, settings). LLM cost capped by 50-ticker limit.

## 9. Testing Strategy

- Unit (pure logic):
  - `test_extract_rsi_from_json` — corr extraction
  - `test_extract_rsi_empty_json` — null/empty handling
  - `test_parse_verdict_*` — 4 cases (strong buy, buy, hold, skip + default)
  - `test_scan_dips_filters_by_threshold` — mock DB + mock LLM
  - `test_scan_dips_excludes_failed_status`
  - `test_scan_dips_llm_error_returns_skip`

- QA Hacker:
  - GET /watchlist/scan без авторизации → 302
  - Watchlist пустой → 200 + «просадок не обнаружено»
  - Все тикеры выше порога → 200 + «просадок не обнаружено»
  - LLM возвращает пустую строку → verdict=HOLD, scan не падает
  - 50 тикеров все в просадке → все оцениваются, страница рендерится

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Service | high | `app/services/dip_scanner.py` (новый) |
| Router | low | `app/routers/watchlist.py` (1 endpoint) |
| Templates | medium | `watchlist_scan.html` (новый), `watchlist.html` (кнопка) |
| DB Models | none | — |
| Tests | high | `tests/test_dip_scanner.py` (новый) |

## 11. Red Flags
- **Порядок маршрутов**: `/watchlist/scan` vs `/watchlist/{ticker}` — FastAPI жадно матчит `{ticker}="scan"` если `/{ticker}` стоит первым. Обязательно проверить + тест.
- **S1-DA: partial results on timeout** — если `as_completed(timeout=60)` истекает, собрать завершённые futures, остальные пометить `verdict="TIMEOUT"`. Не бросать исключение.
- **S2-DA: HTTP-level timeout** — `future.result(timeout=12)` не убивает HTTP-вызов. Передать `timeout=10` в `_client(timeout=10)` чтобы OpenAI клиент сам прерывал HTTP.
- **MODEL_FAST (Gemini Flash)** — иногда игнорирует формат. Robust parsing с HOLD дефолтом обязателен.
- **btd_threshold_pct** хранится как строка в БД → `settings_service.get_float()` конвертирует. Проверить что возвращает отрицательное число (e.g. -10.0, не 10.0).

## 12. Dependencies
- `app/services/llm._client()` + `MODEL_FAST` — уже есть
- `app/services/settings_service.get_float()` — уже есть
- Нет новых pip-зависимостей
