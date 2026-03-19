import os
from unittest.mock import patch, AsyncMock
import asyncio

os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["BOT_TOKEN"] = "test-bot-token"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["POSTGRES_URL"] = "sqlite+pysqlite:///:memory:"

from backend.db.session import SessionLocal, engine
from backend.db.base import Base
from backend.services.generation_service import GenerationService
from backend.models.user import User

Base.metadata.create_all(bind=engine)

db = SessionLocal()
user = User(telegram_user_id=888, username="test", first_name="test", language_code="en")
db.add(user)
db.commit()
db.refresh(user)

srv = GenerationService(db)
srv.balance_service.add_credits(user.id, 100)
db.commit()

job = srv.create_job_for_user(
    telegram_user_id=888,
    provider="kling",
    prompt="test",
    process_now=False
)
db.commit()
job_id = job.id
db.close()

from worker.tasks.generation_tasks import run_generation_job

with patch("worker.tasks.generation_tasks.requests.post") as mock_post, \
     patch("worker.tasks.generation_tasks.requests.get") as mock_get, \
     patch("worker.tasks.generation_tasks._notify_success", new_callable=AsyncMock) as mock_success, \
     patch("worker.tasks.generation_tasks._notify_failed", new_callable=AsyncMock) as mock_failed:
     
     mock_post.return_value.json.return_value = {"id": "mock_task_id", "status": "processing"}
     mock_get.return_value.json.return_value = {"status": "completed", "data": {"result": {"video_url": "https://mock.local/kling/vid.mp4"}}}
     
     print(">>> CALLING RUN_GENERATION_JOB MANUALLY")
     res = run_generation_job(job_id)
     print(">>> RETURNED:", res)

db = SessionLocal()
job2 = db.query(srv.repo.model).get(job_id)
print(">>> FINAL STATUS:", job2.status)
db.close()
