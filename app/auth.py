import bcrypt
from fastapi import Cookie, HTTPException
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from starlette.responses import Response

from app.config import get_settings

_COOKIE_NAME = "auth_token"


def _get_signer() -> TimestampSigner:
    return TimestampSigner(get_settings().SECRET_KEY)


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_session_cookie(response: Response) -> None:
    token = _get_signer().sign("authenticated").decode()
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=get_settings().SESSION_MAX_AGE,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=_COOKIE_NAME)


def login_required(session: str | None = Cookie(default=None, alias=_COOKIE_NAME)) -> None:
    if session is None:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    try:
        _get_signer().unsign(session, max_age=get_settings().SESSION_MAX_AGE)
    except (SignatureExpired, BadSignature):
        raise HTTPException(status_code=302, headers={"Location": "/login"})
