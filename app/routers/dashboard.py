from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import login_required

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@router.get("/health")
async def health():
    return {"status": "ok"}
