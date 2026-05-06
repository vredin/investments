# T-008: Recommend page — Russian rationale + reset executed on re-generate

**Created**: 2026-05-06
**Risk**: Low
**Status**: Backlog

## 1. Overview
Two UX bugs on /recommend: LLM rationale returns English text (prompt doesn't request Russian),
and re-generating a plan for the same month shows all positions as "✓ Куплено" because
the ON CONFLICT upsert preserves the old `executed=True` flag.

## 2. Objectives
- [ ] LLM rationale responds in Russian (1 sentence, ≤25 words)
- [ ] Re-generating plan for same month resets `executed=False` for all rows
- [ ] Fallback string (no API key) also in Russian

## 3. Prerequisites
- OPENROUTER_API_KEY set in .env (already done)
- T-005 (recommender) merged (done)

## 4. Scope
**In scope**:
- `app/services/recommender.py`: add Russian instruction to `_llm_rationale` prompt
- `app/services/recommender.py`: add `executed: False` to `set_` dict in `upsert_recommendations`
- `app/services/recommender.py`: translate fallback string to Russian

**Out of scope**: changing the LLM model, redesigning the executed UX flow

## 5. Technical Approach

### Fix 1 — Russian prompt
```python
prompt = (
    f"Ты портфельный советник. Напиши ОДНО краткое предложение (макс. 25 слов) на русском языке, "
    f"объясняющее почему стоит купить {ticker} в этом месяце. "
    f"Текущая доля: {current_pct:.1f}%, целевая: {target_pct:.1f}%."
)
```

### Fix 2 — Reset executed on re-generate
In `upsert_recommendations`, add `executed` to the `set_` dict:
```python
set_={
    "amount_usd": stmt.excluded.amount_usd,
    "week_of_month": stmt.excluded.week_of_month,
    "rationale": stmt.excluded.rationale,
    "executed": stmt.excluded.executed,  # ADD THIS — resets to False on re-generate
}
```

### Fix 3 — Russian fallback
```python
return f"Покупка по распределению — цель {target_pct:.0f}%, факт {current_pct:.1f}%."
```

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/services/recommender.py` | 3 one-line changes |

## 7. Success Criteria
- LLM rationale is in Russian after regeneration
- After clicking "✓ Куплено" on all items, re-generating the plan resets all to unexecuted
- Fallback string (when no key) also in Russian
- Existing unit tests still pass

## 8. Implementation Notes & BQC Risks
| Risk | Mitigation |
|------|------------|
| LLM ignores Russian instruction | Acceptable — fallback is Russian anyway |
| Reset executed = user loses "already bought" tracking for current month | Intentional — re-generate = fresh plan |

Security-reviewed: no threats identified (no auth/payments/PII touched).

## 9. Testing Strategy
- Unit: existing `test_recommender.py` — check fallback string is in Russian after fix
- E2E: manual — generate plan, mark 2 as executed, re-generate, verify executed reset to unchecked

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Service | low | `app/services/recommender.py` |
| DB | none | — |
| Templates | none | — |
| Tests | low | `tests/test_recommender.py` |

## 11. Red Flags
- LLM models can still respond in English even when asked in Russian — fallback covers this
- Resetting executed may surprise users who intentionally bought and re-generate with different budget — acceptable tradeoff

## 12. Dependencies
- None
