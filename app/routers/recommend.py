from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import login_required

router = APIRouter(prefix="/recommend", tags=["recommend"], dependencies=[Depends(login_required)])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def recommend_page(request: Request):
    # Phase 02: render recommendation form
    return templates.TemplateResponse(request, "recommend.html")


@router.post("")
async def recommend_submit(request: Request):
    # Phase 02: call recommender.generate_buy_plan() and render result
    return templates.TemplateResponse(request, "recommend.html")
