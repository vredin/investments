# T-004: Price sync via yfinance

**Created**: 2026-05-05
**Risk**: Medium
**Status**: Backlog

## 1. Overview
Neither the recommender nor the analytics dashboard can function without current prices.
This task implements `/sync/prices`: fetches 250 days of OHLCV data for all tickers
in the `positions` table plus the 4 target ETFs, stores in `prices` table.
Triggered manually; APScheduler daily job is Phase 04.

## 2. Objectives
- [ ] `app/services/prices.py` — sync_prices(db): fetch prices for all relevant tickers
- [ ] Ticker normalisation: `AAPL.US` → `AAPL`, Freedom `.US` suffix stripped
- [ ] Target ETF yfinance symbols hard-coded: VWCE.AS, VEUR.AS, AGGH.L, XEON.DE
- [ ] 250 calendar days of history (covers SMA200 + 52w drawdown for Phase 02)
- [ ] Upsert into `prices` table (no duplicates on re-sync)
- [ ] POST `/sync/prices` route wires to service, flash success/error
- [ ] Returns count of rows upserted

## 3. Prerequisites
- T-001 complete (positions in DB) ✓
- `yfinance` package installed (add to pyproject.toml)

## 4. Scope
**In scope**:
- `app/services/prices.py` — new module
- `app/routers/sync.py` — implement `/sync/prices` stub
- `pyproject.toml` — add yfinance dependency

**Out of scope**:
- APScheduler daily cron job (Phase 04)
- Adjusted-close split/dividend correction
- Crypto price feeds

## 5. Technical Approach
```python
# app/services/prices.py
import yfinance as yf

_TARGET_TICKERS = {"VWCE.AS": "VWCE", "VEUR.AS": "VEUR", "AGGH.L": "AGGH", "XEON.DE": "XEON"}
_FREEDOM_SUFFIX = ".US"

def _to_yf_ticker(ticker: str) -> str:
    """Map DB ticker to yfinance symbol."""
    # Reverse target map
    for yf_sym, db_sym in _TARGET_TICKERS.items():
        if ticker == db_sym:
            return yf_sym
    # Freedom .US suffix → standard
    if ticker.endswith(_FREEDOM_SUFFIX):
        return ticker[: -len(_FREEDOM_SUFFIX)]
    return ticker

def sync_prices(db) -> int:
    position_tickers = {row[0] for row in db.query(Position.ticker).distinct()}
    all_tickers = position_tickers | set(_TARGET_TICKERS.values())

    total = 0
    for db_ticker in all_tickers:
        yf_ticker = _to_yf_ticker(db_ticker)
        try:
            hist = yf.Ticker(yf_ticker).history(period="1y", interval="1d", auto_adjust=True)
            # upsert rows into prices table
            ...
            total += len(hist)
        except Exception as exc:
            logger.warning("Price fetch failed for %s: %s", yf_ticker, exc)
    return total
```

Upsert via `pg_insert(Price).on_conflict_do_update(index_elements=["ticker","date"], ...)`.
Store DB ticker (not yfinance ticker) in `prices.ticker` — consistent with rest of schema.

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/services/prices.py` | Price sync service |
| `app/routers/sync.py` | Implement `/sync/prices` stub |
| `pyproject.toml` | Add `yfinance>=0.2` dependency |

## 7. Success Criteria
- POST /sync/prices: fetches prices for VWCE, VEUR, AGGH, XEON + AAPL, stores in DB
- Re-sync: no duplicate rows
- Partial failure (1 ticker fails): other tickers still sync, flash shows warning
- `prices` table has close price for each ticker for last ~250 days

## 8. Implementation Notes & BQC Risks
| Risk | Notes | Mitigation |
|------|-------|------------|
| yfinance flaky | Rate limits, symbol not found | Per-ticker try/except, log warning, continue |
| yfinance timeout | No default timeout | `yf.Ticker.history(timeout=30)` |
| Wrong yfinance symbol | VWCE.AS vs VWCE | Test sync manually, log symbol used |
| Empty hist dataframe | Symbol delisted or wrong | Skip, warn |
| Duplicate upsert | Re-sync same day | ON CONFLICT DO UPDATE |

Security-reviewed: read-only external call (yfinance), no user input, login_required. No threats identified.

## 9. Testing Strategy
- Unit: mock yfinance, assert correct ticker mapping (AAPL.US→AAPL, VWCE→VWCE.AS)
- Unit: assert upsert doesn't create duplicates on second call
- E2e: POST /sync/prices → 302, prices table has rows (requires DB + network)
- Network tests skipped in CI (use `@pytest.mark.network`)

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Service | high | `app/services/prices.py` (new) |
| Routes | low | `app/routers/sync.py` |
| DB (read/write) | medium | `prices` table |
| Tests | medium | `tests/test_prices.py` |

## 11. Red Flags
- yfinance `auto_adjust=True` changes column names (Close → no adjustment needed). Double-check column name in returned DataFrame.
- European ETF symbols change by exchange: VWCE trades as VWCE.AS (Euronext Amsterdam). If user buys on Xetra it's VWCE.DE. For now hardcode .AS/.L/.DE.
- yfinance has no SLA — can break silently after package updates.

## 12. Dependencies
- `yfinance>=0.2` (new)
- T-001 (positions in DB for ticker discovery)
