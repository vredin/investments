# Session Specification

**Session ID**: `phase02-session01-telegram-llm`
**Phase**: 02 - Recommender (Subsystem A)
**Status**: Not Started
**Created**: 2026-05-08

---

## 1. Session Overview

The recommender core (allocation calc, buy plan, DCA, web UI, mark-executed, DB storage) was
completed in Phase 01. This session finishes the remaining Phase 02 deliverables: Telegram
delivery of buy plans and a centralized LLM rationale service.

The current `recommender._llm_rationale()` is an inline function that bypasses the project's
`llm.py` adapter. This session refactors it to use `llm.generate_rationale()`, which enables
future RAG context injection (Phase 02 Session 02) without touching the recommender logic.

Telegram delivery (`send_message` raises `NotImplementedError`) is the last unshipped PRD
objective for Subsystem A. This session implements it via direct Telegram Bot REST API calls
(httpx), adds a re-send button to the UI, and wires an APScheduler monthly job so the buy plan
is delivered automatically on the first business day of each month.

---

## 2. Objectives

1. Implement `telegram.send_message()` and `telegram.send_recommendation()` via Telegram Bot API
2. Centralize LLM rationale in `llm.generate_rationale()`; remove inline OpenAI client from recommender
3. Wire Telegram notification into the recommend POST flow (non-blocking on Telegram error)
4. Add APScheduler monthly job that auto-generates and delivers the buy plan
5. Add re-send endpoint + UI button for manual Telegram re-delivery

---

## 3. Prerequisites

### Required Sessions
- [x] `phase00-session01-skeleton` - FastAPI app, models, auth, scheduler wired
- [x] `phase01-session01-broker-sync` - positions + transactions populated; recommender core done

### Required Tools/Knowledge
- `python-telegram-bot>=20.0` already in pyproject.toml (use httpx directly for simplicity)
- `httpx>=0.27` already in pyproject.toml
- TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID in .env (currently CHANGE_ME placeholder)
- OPENROUTER_API_KEY in .env

### Environment Requirements
- `llm.chat()` must reach OpenRouter (OPENROUTER_API_KEY set in .env)
- Telegram bot must be created and TOKEN + CHAT_ID must be filled in .env before testing delivery

---

## 4. Scope

### In Scope (MVP)
- `telegram.send_message(text)` via httpx POST to Bot API — PRD objective 7
- `telegram.format_buy_plan(month, rows) -> str` — readable HTML message with disclaimer
- `telegram.send_recommendation(month, rows)` — compose + send, non-fatal on error
- `llm.generate_rationale(ticker, target_pct, current_pct) -> str` — centralized, MODEL_FAST
- `llm.ask_rag_question(question, context_chunks) -> str` — stub with graceful empty-context
- Refactor `recommender._llm_rationale` to call `llm.generate_rationale()`
- POST /recommend wires Telegram send after upsert (Telegram error does NOT abort save)
- POST /recommend/send/{month} re-send endpoint with login_required
- "Send to Telegram" button in recommend.html
- APScheduler monthly job: first business day, auto-generate + send

### Out of Scope (Deferred)
- RAG context in LLM rationale (course rules + channel signals) — *Phase 02 Session 02*
- Course PDF ingestion, channel HTML ingestion — *Phase 02 Session 02 prerequisites*
- Telegram report delivery (send_report) — *Phase 03*

---

## 5. Technical Approach

### Architecture
Telegram delivery uses direct httpx calls to `https://api.telegram.org/bot{TOKEN}/sendMessage`
rather than the python-telegram-bot async API. This keeps the service synchronous and avoids
`asyncio.run()` nesting issues in APScheduler callbacks.

The LLM service (`llm.py`) becomes the single point for all OpenRouter calls. Recommender
imports only `llm.generate_rationale()`; the OpenAI client is never instantiated outside llm.py.

### Design Patterns
- **Graceful degradation**: Telegram errors logged, never propagated to the recommendation save path
- **Single responsibility**: telegram.py for delivery; llm.py for generation; recommender.py for algorithm
- **Non-blocking Telegram**: POST /recommend saves to DB first, sends to Telegram second

### Technology Stack
- Python 3.12 / FastAPI / APScheduler 3.x
- httpx for Telegram Bot API calls
- OpenRouter via openai SDK (existing llm.py pattern)

---

## 6. Deliverables

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `app/services/telegram.py` | Implement send_message, format_buy_plan, send_recommendation | ~60 |
| `app/services/llm.py` | Implement generate_rationale, ask_rag_question | ~30 |
| `app/services/recommender.py` | Refactor _llm_rationale to use llm.generate_rationale | ~10 |
| `app/routers/recommend.py` | Wire Telegram send, add /send/{month} endpoint | ~25 |
| `app/scheduler.py` | Add monthly_recommendation_job | ~30 |
| `app/main.py` | Register monthly job in lifespan | ~5 |
| `app/templates/recommend.html` | Add Send to Telegram button | ~15 |

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `tests/test_telegram.py` | Unit tests for telegram service | ~60 |
| `tests/test_llm_service.py` | Unit tests for llm service | ~50 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] POST /recommend saves recommendation AND attempts Telegram send
- [ ] Telegram error (wrong token, network issue) logs warning but does NOT break the save
- [ ] POST /recommend/send/{month} requires login; sends saved recs to Telegram
- [ ] llm.generate_rationale() returns a string containing the disclaimer
- [ ] recommender.py imports nothing from `openai` directly
- [ ] APScheduler monthly job registered and fires on first business day of month

### Testing Requirements
- [ ] test_telegram.py: send_message (mocked httpx), format_buy_plan, send_recommendation
- [ ] test_llm_service.py: generate_rationale (mocked chat), ask_rag_question
- [ ] All existing tests still pass

### Non-Functional Requirements
- [ ] Telegram error never surfaces as HTTP 500 to the user
- [ ] No raw API payloads or secrets logged

### Quality Gates
- [ ] ruff check passes
- [ ] No inline `OpenAI()` client outside llm.py
- [ ] DISCLAIMER constant from llm.py included in all user-visible LLM output

---

## 8. Implementation Notes

### Key Considerations
- TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID may be empty in .env during development.
  `send_message` must short-circuit gracefully when either is empty (log warning, return).
- `llm.generate_rationale()` must not call `chat()` if OPENROUTER_API_KEY is empty —
  return a static fallback string.
- APScheduler "first business day of month" = first Mon-Fri of the month.
  Use a CronTrigger with `day='1-7', day_of_week='0-4'` (APScheduler 3.x syntax).

### Potential Challenges
- APScheduler + FastAPI lifespan: scheduler is started in `@asynccontextmanager lifespan`;
  ensure `add_job` is called after `scheduler.start()`.
- httpx sync vs async: recommend router is sync-safe; APScheduler callbacks run in thread pool.
  Both contexts work with `httpx.post()` (sync).

### Relevant Considerations
- [LLM via OpenRouter] Use `openai` SDK with `base_url="https://openrouter.ai/api/v1"`.
  MODEL_FAST = `google/gemini-flash-1.5`. Never use `anthropic.Anthropic()`.
- [Broker API responses] Never log raw responses. Telegram payload = formatted text only.
- [Every LLM output] Must include DISCLAIMER = "Not investment advice. For informational purposes only."
- [Secrets in .env only] Never log BOT_TOKEN or API keys.

### Behavioral Quality Focus
Checklist active: Yes
Top behavioral risks for this session:
- Telegram error propagates up and breaks the recommendation save flow
- LLM rationale called with empty OPENROUTER_API_KEY, raises uncaught exception
- APScheduler job crashes silently if DB session is not properly scoped

---

## 9. Testing Strategy

### Unit Tests
- `test_telegram.py::test_send_message_success` — mock httpx.post, verify URL + payload shape
- `test_telegram.py::test_send_message_skips_when_unconfigured` — empty BOT_TOKEN = no HTTP call
- `test_telegram.py::test_format_buy_plan_includes_disclaimer` — assert DISCLAIMER in output
- `test_llm_service.py::test_generate_rationale_calls_chat` — mock llm.chat, verify prompt content
- `test_llm_service.py::test_generate_rationale_fallback_no_api_key` — empty key = static string

### Integration Tests
- Manual: POST /recommend with valid budget -> check flash message + check DB row created
- Manual: POST /recommend/send/{month} -> check Telegram message received in personal chat

### Edge Cases
- Empty positions table (no sync yet) -> generate_buy_plan returns empty list; send_recommendation sends "no recommendations"
- Telegram network timeout -> logged, recommendation saved normally
- OPENROUTER_API_KEY missing -> fallback rationale string returned, no exception

---

## 10. Dependencies

### External Libraries
- httpx>=0.27 (already in deps)
- openai>=1.0 (already in deps, used in llm.py)
- apscheduler>=3.10 (already in deps)

### Other Sessions
- **Depends on**: phase00-session01-skeleton, phase01-session01-broker-sync
- **Depended by**: phase02-session02-rag-context (needs llm.generate_rationale with context_chunks param)

---

## Next Steps

Run `/implement` to begin AI-led implementation.
