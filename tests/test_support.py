import os
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from fastapi.testclient import TestClient

TEST_DB_PATH = Path(gettempdir()) / f"ai_bot_platform_{uuid4().hex}.db"

os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["BOT_TOKEN"] = "test-bot-token"
os.environ["BACKEND_HOST"] = "127.0.0.1"
os.environ["BACKEND_PORT"] = "8000"
os.environ["BACKEND_BASE_URL"] = "http://127.0.0.1:8000"
os.environ["MINIAPP_URL"] = "http://localhost:3000"
os.environ["POSTGRES_URL"] = f"sqlite+pysqlite:///{TEST_DB_PATH}"
os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/0"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DEFAULT_LANGUAGE"] = "ru"
os.environ["CARDS_PROVIDER_SECRET"] = "cards-secret"
os.environ["PAYME_SECRET_KEY"] = "payme-secret"
os.environ["CLICK_SECRET_KEY"] = "click-secret"
os.environ["AI_MOCK_MODE"] = "true"
os.environ["GENERATION_PROCESS_NOW"] = "true"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from backend.main import app


def create_client() -> TestClient:
    return TestClient(app)
