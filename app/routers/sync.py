from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.services.ingestion import freedom, ibkr
from app.services.ingestion.broker import BrokerSyncError

router = APIRouter(prefix="/sync", tags=["sync"], dependencies=[Depends(login_required)])
templates = Jinja2Templates(directory="app/templates")

_XML_MIME_TYPES = {"application/xml", "text/xml", "application/octet-stream"}


@router.get("/ibkr", response_class=HTMLResponse)
async def sync_ibkr_form(request: Request):
    return templates.TemplateResponse(request, "sync_ibkr.html")


@router.post("/ibkr")
async def sync_ibkr(
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    # Validate file is XML by content_type or filename extension
    is_xml = (file.content_type or "") in _XML_MIME_TYPES or (
        file.filename or ""
    ).lower().endswith(".xml")
    if not is_xml:
        request.session["flash"] = {
            "type": "error",
            "msg": "Please upload a valid XML file (.xml). Download Activity Statement from IBKR Portal.",
        }
        return RedirectResponse(url="/sync/ibkr", status_code=302)

    try:
        content = await file.read()
        if not content:
            raise BrokerSyncError("Uploaded file is empty")
        result = ibkr.import_flex_xml(content, db)
        db.commit()
        request.session["flash"] = {
            "type": "success",
            "msg": f"Synced {result['positions']} positions, {result['transactions']} transactions from IBKR",
        }
    except BrokerSyncError as exc:
        db.rollback()
        request.session["flash"] = {"type": "error", "msg": f"IBKR import failed: {exc}"}
    except Exception as exc:
        db.rollback()
        request.session["flash"] = {"type": "error", "msg": "IBKR import failed: unexpected error"}
        # Log full exception internally but do not expose to user
        import logging
        logging.getLogger(__name__).exception("Unexpected IBKR import error: %s", exc)

    return RedirectResponse(url="/", status_code=302)


@router.post("/freedom")
async def sync_freedom(
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        pos_count = freedom.sync_freedom_positions(db)
        txn_count = freedom.sync_freedom_transactions(db)
        db.commit()
        request.session["flash"] = {
            "type": "success",
            "msg": f"Synced {pos_count} positions, {txn_count} transactions from Freedom Finance",
        }
    except BrokerSyncError as exc:
        db.rollback()
        request.session["flash"] = {"type": "error", "msg": f"Freedom Finance sync failed: {exc}"}
    except Exception as exc:
        db.rollback()
        request.session["flash"] = {"type": "error", "msg": "Freedom Finance sync failed: unexpected error"}
        import logging
        logging.getLogger(__name__).exception("Unexpected Freedom sync error: %s", exc)

    return RedirectResponse(url="/", status_code=302)


@router.post("/prices")
async def sync_prices(request: Request):
    # Phase 01 Session 02: call services.prices.sync_prices()
    request.session["flash"] = {"type": "info", "msg": "Price sync not implemented yet"}
    return RedirectResponse(url="/", status_code=302)
