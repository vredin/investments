from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import login_required
from app.db import get_db
from app.services import prices as prices_service
from app.services.ingestion import freedom, ibkr
from app.services.ingestion.broker import BrokerSyncError
from app.services.ingestion.freedom import _MAX_XLSX_BYTES

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


@router.get("/freedom", response_class=HTMLResponse)
async def sync_freedom_form(request: Request):
    return templates.TemplateResponse(request, "sync_freedom.html")


@router.post("/freedom/portfolio")
async def sync_freedom_portfolio(
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".xlsx"):
        request.session["flash"] = {
            "type": "error",
            "msg": "Please upload an .xlsx file (Freedom24 → Профіль → Портфель → Експорт в Excel)",
        }
        return RedirectResponse(url="/sync/freedom", status_code=302)
    try:
        content = await file.read(_MAX_XLSX_BYTES + 1)
        if not content:
            raise BrokerSyncError("Uploaded file is empty")
        count = freedom.import_freedom_portfolio_xlsx(content, db)
        db.commit()
        request.session["flash"] = {
            "type": "success",
            "msg": f"Imported {count} positions from Freedom Finance portfolio",
        }
    except BrokerSyncError as exc:
        db.rollback()
        request.session["flash"] = {"type": "error", "msg": f"Freedom portfolio import failed: {exc}"}
    except Exception as exc:
        db.rollback()
        request.session["flash"] = {"type": "error", "msg": "Freedom portfolio import failed: unexpected error"}
        import logging
        logging.getLogger(__name__).exception("Unexpected Freedom portfolio import error: %s", exc)
    return RedirectResponse(url="/sync/freedom", status_code=302)


@router.post("/freedom/trades")
async def sync_freedom_trades(
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".xlsx"):
        request.session["flash"] = {
            "type": "error",
            "msg": "Please upload an .xlsx file (Freedom24 → Профіль → Угоди → Експорт в Excel)",
        }
        return RedirectResponse(url="/sync/freedom", status_code=302)
    try:
        content = await file.read(_MAX_XLSX_BYTES + 1)
        if not content:
            raise BrokerSyncError("Uploaded file is empty")
        count = freedom.import_freedom_trades_xlsx(content, db)
        db.commit()
        request.session["flash"] = {
            "type": "success",
            "msg": f"Imported {count} transactions from Freedom Finance trades",
        }
    except BrokerSyncError as exc:
        db.rollback()
        request.session["flash"] = {"type": "error", "msg": f"Freedom trades import failed: {exc}"}
    except Exception as exc:
        db.rollback()
        request.session["flash"] = {"type": "error", "msg": "Freedom trades import failed: unexpected error"}
        import logging
        logging.getLogger(__name__).exception("Unexpected Freedom trades import error: %s", exc)
    return RedirectResponse(url="/sync/freedom", status_code=302)


@router.post("/prices")
async def sync_prices(request: Request, db: Session = Depends(get_db)):
    try:
        result = prices_service.sync_prices(db)
        db.commit()
        msg = f"Synced {result['rows']} price rows for {result['tickers']} tickers"
        if result["failed"]:
            msg += f" (failed: {', '.join(result['failed'])})"
            request.session["flash"] = {"type": "info", "msg": msg}
        else:
            request.session["flash"] = {"type": "success", "msg": msg}
    except Exception as exc:
        db.rollback()
        request.session["flash"] = {"type": "error", "msg": "Price sync failed: unexpected error"}
        import logging
        logging.getLogger(__name__).exception("Unexpected price sync error: %s", exc)
    return RedirectResponse(url="/", status_code=302)
