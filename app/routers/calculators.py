"""Calculators page — GET /calculators (static, login required)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import login_required

router = APIRouter(tags=["calculators"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/calculators", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def calculators_page(request: Request):
    return templates.TemplateResponse(request, "calculators.html", {})
