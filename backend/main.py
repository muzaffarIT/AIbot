from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.main_router import api_router
from backend.core.config import settings
from backend.db.init_db import init_db

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


app.include_router(api_router, prefix="/api")
