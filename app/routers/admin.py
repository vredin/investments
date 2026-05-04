from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.auth import login_required

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(login_required)])


@router.post("/ingest-course")
async def ingest_course(request: Request):
    # Phase 01: accept PDF upload, call ingestion.course.ingest_course_pdf()
    request.session["flash"] = {"type": "info", "msg": "Course ingestion not implemented yet"}
    return RedirectResponse(url="/", status_code=302)


@router.post("/ingest-channels")
async def ingest_channels(request: Request):
    # Phase 01: accept HTML export, call ingestion.channels.ingest_channel_export()
    request.session["flash"] = {"type": "info", "msg": "Channel ingestion not implemented yet"}
    return RedirectResponse(url="/", status_code=302)
