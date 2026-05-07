from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(login_required)])
templates = Jinja2Templates(directory="app/templates")

_ALLOCATION_KEYS = [f"allocation.{t}" for t in settings_service.TARGET_TICKERS]
_NUMERIC_KEYS = _ALLOCATION_KEYS + ["budget_usd", "assumed_return_pct", "goal_usd", "btd_threshold_pct", "btd_extra_budget_usd"]


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    cfg = settings_service.get_all(db)
    return templates.TemplateResponse(request, "settings.html", {"cfg": cfg, "tickers": settings_service.TARGET_TICKERS})


@router.post("", response_class=HTMLResponse)
async def settings_submit(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    updates: dict[str, str] = {}
    errors: list[str] = []

    for key in _NUMERIC_KEYS:
        val = form.get(key, "").strip()
        if not val:
            continue
        try:
            parsed = float(val)
            if key.startswith("allocation.") and not (0 <= parsed <= 100):
                errors.append(f"{key}: must be 0–100")
                continue
            if key == "btd_threshold_pct" and parsed >= 0:
                errors.append("btd_threshold_pct: должно быть отрицательным (например, -10)")
                continue
            updates[key] = str(parsed)
        except ValueError:
            errors.append(f"{key}: must be a number")

    if errors:
        cfg = settings_service.get_all(db)
        request.session["flash"] = {"type": "error", "msg": "; ".join(errors)}
        return templates.TemplateResponse(request, "settings.html", {"cfg": cfg, "tickers": settings_service.TARGET_TICKERS})

    settings_service.save(db, updates)
    db.commit()
    request.session["flash"] = {"type": "success", "msg": "Сохранено"}
    return RedirectResponse(url="/settings", status_code=302)
