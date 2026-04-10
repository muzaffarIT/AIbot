import os
import logging
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.main_router import api_router
from backend.core.config import settings
from backend.db.init_db import init_db

os.makedirs("logs", exist_ok=True)
file_handler = RotatingFileHandler("logs/errors.log", maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logging.getLogger().addHandler(file_handler)

app = FastAPI(title="AI Bot Backend")


def _build_cors_origins() -> list[str]:
    origins = {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }
    if settings.miniapp_url:
        origins.add(settings.miniapp_url.rstrip("/"))
    return sorted(origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/health/worker")
async def health_worker() -> dict:
    """Check that Celery worker is alive by sending a ping task."""
    try:
        from worker.celery_app import celery_app
        result = celery_app.control.ping(timeout=3)
        if result:
            return {"status": "ok", "workers": len(result)}
        return {"status": "degraded", "detail": "No workers responded"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


app.include_router(api_router, prefix="/api")
