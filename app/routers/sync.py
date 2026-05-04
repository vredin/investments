from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.auth import login_required

router = APIRouter(prefix="/sync", tags=["sync"], dependencies=[Depends(login_required)])


@router.post("/ibkr")
async def sync_ibkr(request: Request):
    # Phase 01: call ingestion.ibkr.sync_ibkr_positions()
    request.session["flash"] = {"type": "info", "msg": "IBKR sync not implemented yet"}
    return RedirectResponse(url="/", status_code=302)


@router.post("/freedom")
async def sync_freedom(request: Request):
    # Phase 01: call ingestion.freedom.sync_freedom_positions()
    request.session["flash"] = {"type": "info", "msg": "Freedom sync not implemented yet"}
    return RedirectResponse(url="/", status_code=302)


@router.post("/prices")
async def sync_prices(request: Request):
    # Phase 01: call services.prices.sync_prices()
    request.session["flash"] = {"type": "info", "msg": "Price sync not implemented yet"}
    return RedirectResponse(url="/", status_code=302)
