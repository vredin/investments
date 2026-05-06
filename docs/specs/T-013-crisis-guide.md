# T-013: Гайд "Что делать при просадке рынка"

**Created**: 2026-05-06
**Risk**: Low
**Status**: Backlog

## 1. Overview
Рынок упал на 20% — новичок в панике. Система молчит.
Добавить секцию на дашборде с текущей просадкой VWCE от ATH + статичный FAQ
"Это нормально, вот что делать". Психологическая поддержка важнее инструкций.

## 2. Objectives
- [ ] Показывать текущую просадку VWCE от 52-недельного максимума (через yfinance)
- [ ] При просадке > 10% — показывать баннер "Рынок просел X%. Это нормально. Читать →"
- [ ] Статичная страница /crisis с объяснением DCA-во-время-кризиса, историческими примерами
- [ ] Ссылка из дашборда и из рекомендаций

## 3. Scope
**In scope**:
- `app/services/analytics.py`: функция `get_market_drawdown()` — yfinance 52w max vs current VWCE
- `dashboard.html`: баннер при drawdown > threshold (по умолчанию 10%)
- `app/templates/crisis.html`: статичная информационная страница
- `app/routers/`: новый маршрут GET /crisis

**Out of scope**: push-уведомления при просадке (это в Telegram боте), исторические графики просадок

## 5. Technical Approach

```python
# analytics.py
import yfinance as yf

def get_market_drawdown(ticker: str = "VWCE.AS") -> float:
    """Current drawdown from 52-week high. Returns negative float e.g. -0.15 for -15%."""
    hist = yf.Ticker(ticker).history(period="1y")
    if hist.empty:
        return 0.0
    peak = hist["Close"].max()
    current = hist["Close"].iloc[-1]
    return (current - peak) / peak  # negative value
```

В роутере дашборда: добавить `drawdown = analytics.get_market_drawdown()` в контекст.
В шаблоне: `{% if drawdown < -0.10 %}` → показать баннер.

Страница /crisis — полностью статичный HTML без данных из БД.
Содержание:
- "Почему рынок падает" (бизнес-циклы)
- "Что происходит с ETF при падении" (цена падает, но фонд не банкротится)
- "DCA во время кризиса — ваше преимущество" (покупаете дешевле)
- "Исторические данные": 2008 (-57%), восстановление за 5 лет; COVID 2020 (-34%), восстановление за 5 мес.
- "Золотое правило: не продавать в кризис"

## 6. Deliverables
| File | Changes |
|------|---------|
| `app/services/analytics.py` | `get_market_drawdown()` |
| `app/routers/dashboard.py` | drawdown в контекст |
| `app/templates/dashboard.html` | баннер при drawdown > 10% |
| `app/templates/crisis.html` | статичная страница |
| `app/routers/` | GET /crisis маршрут (можно в dashboard.py) |

## 7. Success Criteria
- `get_market_drawdown()` возвращает float без краша при недоступности yfinance
- Баннер появляется при drawdown < -0.10
- /crisis доступна без авторизации (информационная) или с авторизацией — ок оба варианта

## 8. BQC Risks
| Risk | Mitigation |
|------|------------|
| yfinance timeout / недоступность | try/except → return 0.0, баннер не показывается |
| VWCE.AS wrong ticker | Конфигурируемый тикер через settings или константа |

Security-reviewed: no threats (read-only, no user input).

## 9. Testing Strategy
- Unit: mock yfinance → drawdown -0.20 → проверить что функция возвращает -0.20
- Unit: yfinance exception → возвращает 0.0

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Service | low | analytics.py |
| Router | low | dashboard.py |
| Templates | low | dashboard.html + crisis.html |
