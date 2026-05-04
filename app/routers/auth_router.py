from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import (
    clear_session_cookie,
    create_session_cookie,
    verify_password,
)
from app.config import get_settings

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

_COOKIE_NAME = "auth_token"


def _is_authenticated(session: str | None) -> bool:
    if session is None:
        return False
    from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

    try:
        TimestampSigner(get_settings().SECRET_KEY).unsign(
            session, max_age=get_settings().SESSION_MAX_AGE
        )
        return True
    except (SignatureExpired, BadSignature):
        return False


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    session: str | None = Cookie(default=None, alias=_COOKIE_NAME),
):
    if _is_authenticated(session):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login_submit(
    request: Request,
    password: str = Form(...),
    session: str | None = Cookie(default=None, alias=_COOKIE_NAME),
):
    if _is_authenticated(session):
        return RedirectResponse(url="/", status_code=302)

    settings = get_settings()
    if verify_password(password, settings.ADMIN_PASSWORD_HASH):
        response = RedirectResponse(url="/", status_code=302)
        create_session_cookie(response)
        return response

    return templates.TemplateResponse(
        request, "login.html", {"error": "Invalid password"}, status_code=401
    )


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    clear_session_cookie(response)
    return response
