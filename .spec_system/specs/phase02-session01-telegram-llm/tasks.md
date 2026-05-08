# Task Checklist

**Session ID**: `phase02-session01-telegram-llm`
**Total Tasks**: 18
**Estimated Duration**: 3-3.5 hours
**Created**: 2026-05-08

---

## Legend

- `[x]` = Completed
- `[ ]` = Pending
- `[P]` = Parallelizable (can run with other [P] tasks)
- `[S0201]` = Session reference (phase 02, session 01)
- `TNNN` = Task ID

---

## Progress Summary

| Category | Total | Done | Remaining |
|----------|-------|------|-----------|
| Setup | 3 | 0 | 3 |
| Foundation | 5 | 0 | 5 |
| Implementation | 7 | 0 | 7 |
| Testing | 3 | 0 | 3 |
| **Total** | **18** | **0** | **18** |

---

## Setup (3 tasks)

Verify environment and dependencies before writing any code.

- [ ] T001 [S0201] Verify TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, OPENROUTER_API_KEY present in `app/config.py` Settings and `app/.env.example`; note which are still CHANGE_ME in local .env
- [ ] T002 [S0201] Confirm httpx is importable in container: `docker compose exec app python -c "import httpx; print(httpx.__version__)"`; note version
- [ ] T003 [S0201] Confirm `app/services/llm.py::chat()` reaches OpenRouter: run `docker compose exec app python -c "from app.services.llm import chat; print(chat('ping'))"` on VPS; document result in implementation-notes.md

---

## Foundation (5 tasks)

Core service implementations before wiring.

- [ ] T004 [S0201] Implement `telegram.send_message(text: str) -> None` in `app/services/telegram.py` using `httpx.post()` to Bot API `/sendMessage` endpoint; short-circuits silently when BOT_TOKEN or CHAT_ID empty (logs warning, no exception); raises `TelegramDeliveryError` only on non-2xx HTTP response with failure-path handling
- [ ] T005 [S0201] Add `telegram.format_buy_plan(month: str, rows: list) -> str` to `app/services/telegram.py` -- formats rows as readable Telegram HTML with week, ticker, amount, rationale bullets; appends DISCLAIMER from `llm.DISCLAIMER`; handles empty rows case ("no recommendations for {month}")
- [ ] T006 [S0201] Implement `llm.generate_rationale(ticker: str, target_pct: float, current_pct: float) -> str` in `app/services/llm.py` using `chat()` with MODEL_FAST; prompt must include ticker, target_pct, current_pct, and instruction to be one sentence; returns fallback static string when OPENROUTER_API_KEY empty; output always includes DISCLAIMER
- [ ] T007 [S0201] Implement `llm.ask_rag_question(question: str, context_chunks: list[str]) -> str` in `app/services/llm.py` -- if context_chunks empty returns "No course material available to answer this question."; otherwise builds prompt with numbered chunks and calls `chat()` with MODEL_FAST; output includes DISCLAIMER
- [ ] T008 [S0201] Refactor `recommender._llm_rationale(ticker, target_pct, current_pct)` in `app/services/recommender.py` to call `llm.generate_rationale()` instead of instantiating OpenAI client inline; remove the inline `from openai import OpenAI` and `from app.config import get_settings` imports from that function

---

## Implementation (7 tasks)

Wire delivery into routes, UI, and scheduler.

- [ ] T009 [S0201] Add `telegram.send_recommendation(month: str, rows: list) -> None` to `app/services/telegram.py` -- calls `format_buy_plan()` then `send_message()`; catches `TelegramDeliveryError` and `Exception`, logs warning, never re-raises (caller must not be interrupted)
- [ ] T010 [S0201] Wire `telegram.send_recommendation(month, rows)` into `app/routers/recommend.py` POST /recommend after successful `upsert_recommendations()` + `db.commit()`; wrap in try/except so Telegram failure logs warning but does NOT prevent the 200 response with failure-path handling
- [ ] T011 [S0201] Add `POST /recommend/send/{month}` endpoint in `app/routers/recommend.py` -- loads saved Recommendation rows for that month, calls `telegram.send_recommendation()`, returns JSON `{"status": "sent", "month": month}`; with authorization enforced at boundary (login_required)
- [ ] T012 [S0201] Add "Send to Telegram" button in `app/templates/recommend.html` for the generated recommendations section -- POST form to `/recommend/send/{month}`; with duplicate-trigger prevention while in-flight (disable button on click)
- [ ] T013 [S0201] Add `monthly_recommendation_job(budget_usd: float)` in `app/scheduler.py` -- creates its own DB session, calls `rec_service.generate_buy_plan(budget_usd, db)`, upserts, calls `telegram.send_recommendation()`; logs success with row count; with failure-path handling (exception logged, not re-raised)
- [ ] T014 [S0201] Wire `monthly_recommendation_job` into `app/main.py` lifespan: register with APScheduler CronTrigger `day='1-7', day_of_week='0-4'` (first Mon-Fri of month); pass budget from `settings_service.get_float(db, "budget_usd")`
- [ ] T015 [S0201] Add log statement in `monthly_recommendation_job` that logs month, budget, and row count at INFO level; never log rationale text (may contain LLM output) or API keys

---

## Testing (3 tasks)

- [ ] T016 [S0201] [P] Write `tests/test_telegram.py` -- test `send_message` (mock httpx.post, verify URL shape and chat_id in payload), `send_message` skips when BOT_TOKEN empty, `format_buy_plan` includes DISCLAIMER, `format_buy_plan` handles empty rows; with schema-validated input and explicit error mapping
- [ ] T017 [S0201] [P] Write `tests/test_llm_service.py` -- test `generate_rationale` (mock `llm.chat`, verify prompt contains ticker and pct values, verify DISCLAIMER in output), `generate_rationale` returns fallback when API key empty, `ask_rag_question` returns no-material message when chunks empty
- [ ] T018 [S0201] Run `uv run pytest tests/ -q` -- all tests must pass; run `uv run ruff check .` -- zero violations; fix any failures before marking session complete

---

## Completion Checklist

Before marking session complete:

- [ ] All tasks marked `[x]`
- [ ] All tests passing (`uv run pytest tests/ -q`)
- [ ] `ruff check .` zero violations
- [ ] No inline `OpenAI()` client outside `app/services/llm.py`
- [ ] `TelegramDeliveryError` never propagates to HTTP 500
- [ ] implementation-notes.md updated with any gotchas
- [ ] Ready for `/validate`

---

## Next Steps

Run `/implement` to begin AI-led implementation.
