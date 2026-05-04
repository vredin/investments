# Session Handoff — 2026-05-04

## Completed This Session
- phase01-session01-broker-sync: всі 21 задач виконані (коміт 45859bb)
  - broker.py: PositionRow/TransactionRow DTOs, upsert з ON CONFLICT DO UPDATE
  - ibkr.py: parse_flex_xml, import_flex_xml, sync_ibkr_positions → BrokerSyncError
  - freedom.py: прямий HTTP + HMAC-SHA256 (tradernet SDK порожній), 30s timeout, 2 retry
  - sync.py: GET/POST /sync/ibkr, POST /sync/freedom з flash messages
  - sync_ibkr.html, base.html nav links, 38 unit тестів, fixture XML
  - Задеплоєно на VPS (money.semishan.pro), app running

## In Progress (не завершено)
- **КРИТИЧНА ПРОБЛЕМА**: ADMIN_PASSWORD_HASH на VPS = фейковий тестовий хеш
  - При `scp .env vps3:/opt/Investments/.env` я перезаписав реальний .env на сервері
  - Локальний .env (який пішов на сервер) мав `$2b$12$dummyhashforlocaltesting...`
  - Зараз **логін на money.semishan.pro НЕ ПРАЦЮЄ**
  - Freedom Finance ключі є в локальному .env але не перевірялись

## Next Session Should
1. **ПЕРШОЧЕРГОВО** — відновити ADMIN_PASSWORD_HASH:
   - Дізнатись admin пароль у юзера
   - `python -c "import bcrypt; print(bcrypt.hashpw(b'ПАРОЛЬ', bcrypt.gensalt()).decode())"`
   - `ssh vps3 "nano /opt/Investments/.env"` — вставити справжній хеш
   - `ssh vps3 "cd /opt/Investments && docker compose restart app"`
   - Перевірити логін на money.semishan.pro
2. Перевірити Freedom Finance: після логіну → "Sync Freedom" → flash з кількістю або clear BrokerSyncError (не 500)
3. Завантажити реальний IBKR Flex XML: Activity Statement з IBKR Portal → /sync/ibkr → перевірити DB

## Context That Would Be Lost
- tradernet 0.1.3 має НЕ importable source — тільки dist-info. Freedom адаптер = прямі HTTP requests з HMAC-SHA256. Методи API: `getPortfolio`, `getTransactionHistory` — можуть потребувати уточнення.
- Position PK = (snapshot_date, ticker), upsert по ньому. В spec було написано (instrument_id, broker) — це неправильно, модель така.
- uv pip install pytest потрібен окремо бо `uv sync --dev` не ставить pytest в venv локально (баг в конфігурації проекту).
- .gitignore мав `specs/` (без /) — виправлено на `/specs/` щоб не блокувати .spec_system/specs/
- `docker compose exec app uv run python` створює новий venv в контейнері — краще `docker compose exec app python`

## User's Last Unanswered Question
Я запитав: "Який варіант відновити ADMIN_PASSWORD_HASH: (1) згенерувати новий з паролю або (2) знайти старий?" — відповідь НЕ ОТРИМАНА. Почни наступну сесію з цього питання.
