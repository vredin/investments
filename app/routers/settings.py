from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import login_required

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(login_required)])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request):
    # Phase 03: load config rows and external balances form
    return templates.TemplateResponse(request, "settings.html")


@router.post("")
async def settings_submit(request: Request):
    # Phase 03: save config changes to Config table
    return templates.TemplateResponse(request, "settings.html")
