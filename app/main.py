from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.routers import admin, auth_router, dashboard, recommend, report, settings, sync
from app.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Investment Assistant", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=get_settings().SECRET_KEY,
    max_age=get_settings().SESSION_MAX_AGE,
)

app.include_router(auth_router.router)
app.include_router(dashboard.router)
app.include_router(sync.router)
app.include_router(recommend.router)
app.include_router(report.router)
app.include_router(settings.router)
app.include_router(admin.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
