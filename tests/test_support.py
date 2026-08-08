import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from tempfile import gettempdir
from urllib.parse import urlencode
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


def make_tma_header(
    telegram_user_id: int,
    *,
    first_name: str = "Test",
    last_name: str = "User",
    username: str = "tester",
) -> dict:
    """Build a valid `Authorization: tma <init_data>` header pair.

    The backend's `verify_tma_auth` dependency validates the Telegram WebApp
    initData signature against BOT_TOKEN. Tests don't run inside Telegram, so
    we sign a well-formed initData ourselves with the same algorithm Telegram
    uses (HMAC-SHA256 over the sorted key=value pairs, keyed with the
    HMAC-SHA256 of "WebAppData" + bot token). This keeps the production auth
    path intact while letting tests reach the authenticated endpoints.
    """
    bot_token = os.environ["BOT_TOKEN"]
    user_obj = {
        "id": telegram_user_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
    }
    # auth_date must be present and recent enough; the backend currently
    # doesn't enforce freshness, but we keep it realistic.
    params = {
        "query_id": f"test_{telegram_user_id}",
        "user": json.dumps(user_obj, separators=(",", ":")),
        "auth_date": str(int(time.time())),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    params["hash"] = calculated_hash
    init_data = urlencode(params)
    return {"Authorization": f"tma {init_data}"}

