# T-007: Playwright E2E тесты — QA hacker approach

**Created**: 2026-05-06
**Risk**: Low
**Status**: Backlog

## 1. Overview
Полный набор E2E тестов через `pytest-playwright` (Python, соответствует текущему pytest-стеку).
Тестируется реальный браузер + FastAPI сервер локально. QA hacker approach: помимо happy path —
auth bypass, IDOR, XSS, injection, граничные значения, race conditions.

## 2. Objectives
- [ ] pytest-playwright установлен, браузер Chromium скачан
- [ ] Тестовый сервер поднимается как subprocess в conftest (uvicorn)
- [ ] Auth-фикстура: создаёт валидный cookie через Python (не через UI-форму)
- [ ] Happy path: все 7 страниц рендерятся без ошибок для авторизованного пользователя
- [ ] Auth tests: все защищённые маршруты → 302/redirect к /login без cookie
- [ ] Form tests: рекомендации, настройки — submit + проверка flash-сообщений
- [ ] QA hacker tests: 10+ adversarial сценариев (список в §9)
- [ ] LLM-вызовы замокированы — тесты не зависят от OpenRouter

## 3. Prerequisites
- `pytest-playwright` + `playwright` в dev-зависимостях
- `TEST_DATABASE_URL` доступен (уже есть в conftest.py)
- `TEST_ADMIN_PASSWORD` env var для тестового bcrypt-хэша
- Локальный PostgreSQL для тестов (уже используется)

## 4. Scope
**In scope**:
- `tests/conftest_playwright.py` — фикстуры: сервер, авторизованный контекст, анонимный контекст
- `tests/e2e/test_auth.py` — login/logout/auth bypass
- `tests/e2e/test_dashboard.py` — главная страница
- `tests/e2e/test_portfolio.py` — страница портфеля
- `tests/e2e/test_recommend.py` — рекомендации (get, post, execute)
- `tests/e2e/test_settings.py` — настройки (get, post, валидация)
- `tests/e2e/test_report.py` — отчёт
- `tests/e2e/test_hacker.py` — все adversarial сценарии
- `Makefile` или скрипт `scripts/test-e2e.sh` для запуска

**Out of scope**:
- Тесты на мобильных viewport (деferred)
- Visual regression (screenshots diff)
- Тесты /sync/freedom (требует реальный XLSX — deferred)
- Тесты /sync/prices (требует yfinance — мокается или пропускается)

## 5. Technical Approach

### Запуск сервера
```python
# conftest_playwright.py
import subprocess, time, pytest

@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    # Запуск uvicorn на случайном порту с TEST_DATABASE_URL
    proc = subprocess.Popen(["uvicorn", "app.main:app", "--port", "18765", ...])
    time.sleep(2)  # дать время на старт
    yield "http://localhost:18765"
    proc.terminate()
```

### Auth-фикстура (без UI)
```python
from itsdangerous import TimestampSigner

@pytest.fixture
def auth_cookie(settings):
    token = TimestampSigner(settings.SECRET_KEY).sign("authenticated").decode()
    return {"name": "auth_token", "value": token, "domain": "localhost", ...}

@pytest.fixture
def auth_page(page, auth_cookie, live_server):
    page.context.add_cookies([auth_cookie])
    return page
```

### Мокирование LLM
```python
# Патчим перед запуском сервера через monkeypatch или env var
# OPENROUTER_API_KEY="" → _llm_rationale упадёт в except → вернёт статику
# Достаточно не ставить ключ в тестовой конфигурации
```

### Структура тестов
```
tests/
  e2e/
    __init__.py
    conftest.py          # server + auth fixtures (scope=session)
    test_auth.py
    test_dashboard.py
    test_portfolio.py
    test_recommend.py
    test_settings.py
    test_report.py
    test_hacker.py
```

## 6. Deliverables
| File | Purpose |
|------|---------|
| `tests/e2e/conftest.py` | Фикстуры: live_server, auth_page, anon_page |
| `tests/e2e/test_auth.py` | Login/logout/session тесты |
| `tests/e2e/test_dashboard.py` | Главная страница |
| `tests/e2e/test_portfolio.py` | Портфель |
| `tests/e2e/test_recommend.py` | Рекомендации |
| `tests/e2e/test_settings.py` | Настройки |
| `tests/e2e/test_report.py` | Отчёт |
| `tests/e2e/test_hacker.py` | Все adversarial сценарии |

## 7. Success Criteria
- Functional: `uv run pytest tests/e2e/ -v` — все тесты зелёные на чистой тест-БД
- Auth: ни один protected endpoint не доступен без валидного cookie
- QA hacker: все adversarial тесты — либо 4xx/redirect, либо безопасная ошибка (нет 500, нет утечки данных)
- Независимость: тесты не зависят от OpenRouter API

## 8. Implementation Notes & BQC Risks
| Risk | Mitigation |
|------|------------|
| Сервер не поднялся к моменту теста | healthcheck loop в фикстуре (retry 10× с sleep 0.5s) |
| БД dirty state между тестами | каждый тест-класс truncate relevant tables в setup |
| LLM вызов зависает | OPENROUTER_API_KEY="" в тестовом окружении → instant fallback |
| Port conflict | рандомный порт + env var для передачи в app |
| Playwright timeout | default 5s → raise с четким сообщением |
| `/sync/prices` запускает yfinance | пропускать через `@pytest.mark.skip` или мокировать |

Security-reviewed: тесты не добавляют attack surface. Adversarial тесты верифицируют существующие защиты.

## 9. Testing Strategy

### Happy path (по странице)
- `GET /login` → форма видна, заголовок содержит "Вход"
- `POST /login` valid → redirect на `/`, cookie установлен
- `GET /` auth → 200, содержит "Портфель всего" или "Позиций не найдено"
- `GET /portfolio` auth → 200, таблица "Позиции" видна
- `GET /recommend` auth → 200, форма бюджета видна
- `POST /recommend` budget=200 → flash-сообщение успеха ИЛИ пустой план (БД пустая)
- `GET /settings` auth → 200, поля VWCE/VEUR/AGGH/XEON видны
- `POST /settings` valid → flash "Сохранено"
- `GET /report/2026-05` auth → 200, содержит "2026-05"

### Auth tests
- `GET /` без cookie → Location: /login
- `GET /portfolio` без cookie → /login
- `GET /recommend` без cookie → /login
- `GET /settings` без cookie → /login
- `GET /report/2026-05` без cookie → /login
- `POST /logout` → cookie удалён, старый cookie больше не работает

### QA Hacker cases (test_hacker.py)
1. **Auth bypass cookie forgery**: подделать cookie с неверным SECRET_KEY → 302
2. **Expired session**: cookie подписан правильно но older than SESSION_MAX_AGE → 302
3. **IDOR execute без auth**: `POST /recommend/execute/2026-05/VWCE` без cookie → redirect /login
4. **XSS в budget**: `POST /recommend` budget=`<script>alert(1)</script>` → 422 или "введите число"
5. **SQL injection в settings**: allocation.VWCE=`'; DROP TABLE config; --` → 422 или валидация
6. **Отрицательный бюджет**: `POST /recommend` budget=-500 → либо empty plan, либо ошибка (не 500)
7. **Аллокация > 100**: `/settings` VWCE=200 → flash error "must be 0–100"
8. **Path traversal в /report/**: `GET /report/../../etc/passwd` → 404 или 422 (FastAPI path validation)
9. **Дублирующий execute**: `POST /recommend/execute/2026-05/VWCE` дважды → идемпотентно, нет 500
10. **Пустой month в report**: `GET /report/` → 404
11. **Очень длинное значение в settings**: goal_usd=`9` × 20 → валидируется без 500
12. **POST /settings без CSRF**: просто POST без referer → должно работать (нет CSRF-защиты — это known limitation)

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Tests | high | `tests/e2e/` (8 новых файлов) |
| Config | low | `pyproject.toml` — добавить playwright в dev deps |
| CI | medium | `.github/workflows/` если есть — deferred |
| App code | none | Тесты только читают, не меняют prod код |

## 11. Red Flags
- Сессии через `itsdangerous.TimestampSigner` — auth-cookie фикстура должна использовать тот же SECRET_KEY что и тестовый сервер; если ключи разные — все тесты упадут с 302
- `/sync/prices` запускает реальный yfinance HTTP-запрос — нужно либо мокировать, либо явно скипать, иначе тесты зависят от интернета
- `APScheduler` стартует при подъёме приложения через lifespan — может мешать teardown сервера; нужно `scheduler.shutdown()` или флаг `TESTING=1`
- Тест-БД должна иметь pgvector extension — уже обрабатывается в conftest.py основном
- Playwright по умолчанию headless=True — подходит для CI

## 12. Dependencies
- `pytest-playwright>=0.5` (Python binding)
- `playwright` browsers: только `chromium` (достаточно, --no-sandbox для CI)
- Зависит от: T-001...T-006 (весь текущий функционал реализован)
