from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.services import recommender as rec_service
from app.services import settings_service

router = APIRouter(prefix="/recommend", tags=["recommend"], dependencies=[Depends(login_required)])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def recommend_page(request: Request, db: Session = Depends(get_db)):
    month = date.today().strftime("%Y-%m")
    budget = settings_service.get_float(db, "budget_usd")
    saved = rec_service.get_month_recommendations(db, month)
    return templates.TemplateResponse(request, "recommend.html", {
        "month": month,
        "budget": budget,
        "rows": saved,
        "generated": False,
    })


@router.post("", response_class=HTMLResponse)
async def recommend_submit(
    request: Request,
    budget: float = Form(...),
    db: Session = Depends(get_db),
):
    month = date.today().strftime("%Y-%m")
    try:
        rows = rec_service.generate_buy_plan(budget, db)
        rec_service.upsert_recommendations(db, month, rows)
        db.commit()
        request.session["flash"] = {
            "type": "success",
            "msg": f"Generated {len(rows)} recommendations for {month}",
        }
    except Exception as exc:
        db.rollback()
        import logging
        logging.getLogger(__name__).exception("Recommend error: %s", exc)
        request.session["flash"] = {"type": "error", "msg": "Failed to generate recommendations"}
        return RedirectResponse(url="/recommend", status_code=302)

    saved = rec_service.get_month_recommendations(db, month)
    return templates.TemplateResponse(request, "recommend.html", {
        "month": month,
        "budget": budget,
        "rows": saved,
        "generated": True,
    })


@router.post("/execute/{month}/{ticker}")
async def mark_executed(month: str, ticker: str, db: Session = Depends(get_db), request: Request = None):
    from app.models import Recommendation
    rec = db.query(Recommendation).filter_by(month=month, ticker=ticker).first()
    if rec:
        rec.executed = True
        db.commit()
    return RedirectResponse(url="/recommend", status_code=302)
