# T-020: Centralize OpenRouter client initialization

**Created**: 2026-05-09
**Risk**: Low
**Status**: Backlog

## 1. Overview
`analytics.py:202-215` и `recommender.py:72-85` содержат идентичный 13-строчный блок инициализации OpenRouter клиента внутри `try:`. `app/services/llm.py` уже имеет `_client()`, но без `timeout=30` и без проверки пустого API ключа. Дубликат обнаружен pylint R0801.

## 2. Objectives
- [ ] `llm._client()` добавляет `timeout=30` и поднимает `ValueError` если `OPENROUTER_API_KEY` не задан
- [ ] `analytics.llm_report_narrative()` использует `from app.services import llm; client = llm._client()`
- [ ] `recommender._llm_rationale()` аналогично
- [ ] `pylint --disable=all --enable=duplicate-code app/` возвращает 0 (нет R0801)

## 3. Prerequisites
- None

## 4. Scope
**In scope**: `app/services/llm.py` (обновить `_client()`), `app/services/analytics.py:202-215`, `app/services/recommender.py:72-85`  
**Out of scope**: логика промптов, моделей, timeout для `chat()`

## 5. Technical Approach

### llm.py — обновить `_client()`
```python
def _client(timeout: int = 30) -> OpenAI:
    settings = get_settings()
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
        timeout=timeout,
    )
```

### analytics.py — заменить inline блок
```python
# было: try: from openai import OpenAI; from app.config import ...; client = OpenAI(...)
# стало:
from app.services import llm as _llm
client = _llm._client()
```

### recommender.py — аналогично

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/services/llm.py` | Добавить timeout + key check в `_client()` |
| `app/services/analytics.py` | Убрать inline OpenAI init, использовать `llm._client()` |
| `app/services/recommender.py` | То же самое |

## 7. Success Criteria
- `uv run pylint --disable=all --enable=duplicate-code app/` — нет R0801
- `uv run ruff check app/ && uv run mypy app/ --ignore-missing-imports` — чисто
- `uv run pytest tests/ -q` — все тесты проходят

## 8. Implementation Notes & BQC Risks
| Risk | Mitigation |
|------|------------|
| `_client()` — приватный по соглашению | Документировать: "callable from sibling services" в docstring |
| `chat()` не использует timeout → `_client()` создаёт клиент без таймаута сейчас | Добавить `timeout=30` default, `chat()` работает без изменений |

Security-reviewed: no threats identified.

## 9. Testing Strategy
- Unit: мокировать `get_settings()`, проверить ValueError при пустом ключе
- Integration: существующие тесты recommender/analytics не должны упасть
- QA: убедиться что `ValueError("OPENROUTER_API_KEY not set")` появляется в логах при отсутствии ключа (не silent fail)

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| LLM adapter | medium | `app/services/llm.py` |
| Analytics service | low | `app/services/analytics.py` |
| Recommender service | low | `app/services/recommender.py` |
| Tests | low | `tests/` (существующие, не падают) |

## 11. Red Flags
- `_client()` используется внутри `try:` блоков в analytics/recommender — ValueError пробрасывается наверх корректно (это желаемое поведение, не баг)
- Импорт `llm` в analytics/recommender создаёт circular import риск — проверить заранее (`from app.services import llm` vs `from app.services.llm import _client`)

## 12. Dependencies
- None
