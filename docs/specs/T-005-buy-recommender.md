# T-005: Monthly buy recommender (Phase 02)

**Created**: 2026-05-05
**Risk**: High
**Status**: Backlog

## 1. Overview
Given a monthly budget, compute which ETFs to buy and in what amounts to move the portfolio
toward the target allocation (VWCE 65% / VEUR 15% / AGGH 15% / XEON 5%).
Underweight-first logic with oversold scoring (SMA200/RSI/52w-drawdown) from price history.
LLM (Claude Sonnet) generates a one-paragraph rationale per ticker.
Results stored in `recommendations` table; UI at `/recommend`.

## 2. Objectives
- [ ] Target allocations stored in `Config` table, editable via Settings page
- [ ] Monthly budget stored in Config (`budget_usd`), editable via Settings
- [ ] `app/services/recommender.py` — generate_buy_plan(db, budget) → list[RecommendationRow]
- [ ] Allocation deviation: current market_value per ticker / total × 100 vs target %
- [ ] Underweight-first: sort by (target_pct - current_pct) DESC
- [ ] Oversold scoring: SMA200 ratio + RSI14 + 52w-drawdown from `prices` table
- [ ] DCA split: 50% week 1, 50% week 3
- [ ] LLM rationale: Claude Sonnet call per ticker (fallback: "Allocation-driven purchase" if API fails)
- [ ] Upsert into `recommendations` table (idempotent per month+ticker)
- [ ] Web UI at GET/POST `/recommend`: budget input form → table of buy plan
- [ ] Mark as executed: checkbox per row (POST /recommend/execute)

## 3. Prerequisites
- T-004 (prices in DB) — required for scoring
- `ANTHROPIC_API_KEY` in `.env`

## 4. Scope
**In scope**:
- `app/services/recommender.py` — allocation + scoring + LLM rationale
- `app/services/settings_service.py` — read/write Config table
- `app/routers/recommend.py` — implement stub
- `app/routers/settings.py` — target allocation + budget edit form
- `app/templates/recommend.html` — buy plan table
- `app/templates/settings.html` — allocation + budget form

**Out of scope**:
- Course PDF context injection (Phase 01 items 6-8 not yet done — use fallback)
- Channel signal context (Phase 01 item 8 not yet done — use fallback)
- Telegram notification (Phase 04)
- IBKR/Freedom API auto-execution

## 5. Technical Approach

### Allocation deviation
```python
# Current allocation: sum market_value_usd by ticker (latest snapshot)
# Target allocation: read from Config keys "allocation.VWCE" etc.
# Tickers in positions but NOT in target → show as "unmanaged" (e.g. AAPL.US)
# Deviation = target_pct - current_pct (positive = underweight)
```

### Oversold scoring (from prices table)
```python
def _score_ticker(prices: list[Price]) -> float:
    closes = [p.close for p in prices if p.close]
    if len(closes) < 20:
        return 0.0
    sma200 = mean(closes[-200:]) if len(closes) >= 200 else mean(closes)
    current = closes[-1]
    sma_score = max(0, (sma200 - current) / sma200)  # higher = more oversold vs SMA200
    high_52w = max(closes[-252:] if len(closes) >= 252 else closes)
    drawdown_score = max(0, (high_52w - current) / high_52w)
    # RSI14
    rsi = _calc_rsi(closes[-15:])
    rsi_score = max(0, (30 - rsi) / 30) if rsi < 30 else 0.0
    return (sma_score + drawdown_score + rsi_score) / 3
```

### Allocation split
```python
# Underweight-first: sort by deviation DESC
# Distribute budget proportional to deviation × (1 + oversold_score)
# DCA: week_of_month = 1 for first half, 3 for second half
```

### LLM rationale
```python
prompt = f"""
You are an investment advisor. Recommend buying {ticker} for {amount:.0f} USD this month.
Current portfolio weight: {current_pct:.1f}%. Target weight: {target_pct:.1f}%.
Price vs SMA200: {sma_ratio:.1%}. 52w drawdown: {drawdown:.1%}.
Write one concise sentence explaining why this purchase makes sense.
"""
# claude-sonnet-4-6, max_tokens=100, timeout=30s
# On error: fallback = "Allocation-driven purchase (target: {target_pct:.0f}%)"
```

### Recommend route
```
GET /recommend → form (budget pre-filled from Config)
POST /recommend → generate plan, upsert to DB, render table
POST /recommend/execute → mark ticker+month as executed
```

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/services/recommender.py` | Allocation calc + scoring + LLM |
| `app/services/settings_service.py` | Config table read/write |
| `app/routers/recommend.py` | Implement recommend routes |
| `app/routers/settings.py` | Implement settings routes |
| `app/templates/recommend.html` | Buy plan table with execute checkboxes |
| `app/templates/settings.html` | Allocation % + budget form |

## 7. Success Criteria
- POST /recommend with budget=500: returns table with ≥1 row for underweight ETFs
- Tickers not in target (AAPL.US) shown separately as "unmanaged positions"
- Re-submit same month: same rows updated, not duplicated
- LLM timeout: fallback rationale used, no 500 error
- Settings: save allocation changes → affects next recommendation
- Execute checkbox: marks row as executed in DB

## 8. Implementation Notes & BQC Risks
| Risk | Notes | Mitigation |
|------|-------|------------|
| LLM timeout | Anthropic API slow | 30s timeout + fallback rationale string |
| LLM API key missing | KeyError or auth error | Check key at startup, catch AnthropicError |
| Prices missing | Not synced yet | Score = 0.0 for tickers with no price data |
| Division by zero | Total portfolio = 0 | Guard: if total == 0, treat all as 0% current |
| Duplicate trigger | POST /recommend twice | ON CONFLICT DO UPDATE on (month, ticker) |
| Config missing | First run, no allocation in DB | Seed defaults on first access |

Security:
- Config keys are free-form strings — validate that allocation values are numeric 0-100
- LLM prompt must not include user PII or secrets
- login_required on all routes

Security-reviewed: no external user input beyond budget (numeric), LLM prompt uses only local DB data, no SSRF risk. No critical threats.

## 9. Testing Strategy
- Unit: allocation deviation calc with mock positions (underweight → top of list)
- Unit: oversold score with mock price series (SMA200 below price → score=0)
- Unit: LLM fallback when anthropic raises timeout
- Unit: budget distribution — sum of amounts ≤ budget
- E2e: POST /recommend with seeded positions+prices → 302 + recommendations in DB
- QA: POST /recommend twice same month → count stays same

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Service | high | `app/services/recommender.py` (new) |
| Service | medium | `app/services/settings_service.py` (new) |
| Routes | high | `app/routers/recommend.py`, `app/routers/settings.py` |
| Templates | high | `app/templates/recommend.html`, `app/templates/settings.html` |
| DB | low | `recommendations`, `config` tables (already exist) |
| Tests | high | `tests/test_recommender.py` |

## 11. Red Flags
- AAPL.US is in current portfolio but NOT in target allocation. Recommender must not try to buy it. Display as "unmanaged" clearly so user understands.
- If total portfolio value = 0 (no prices synced), division by zero in allocation calc.
- LLM rationale cost: 4 tickers × ~100 tokens × monthly = cheap (~$0.004/month). Fine.
- Config table seeding: first run needs default target allocations. Missing seed = ZeroDivisionError.

## 12. Dependencies
- `anthropic>=0.30` (already in pyproject.toml)
- T-004 (prices) — required for scoring; service must handle missing prices gracefully
- T-001 (positions in DB)
