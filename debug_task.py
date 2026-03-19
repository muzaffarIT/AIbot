import os
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["BOT_TOKEN"] = "test-bot-token"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["AI_MOCK_MODE"] = "false"

from tests.test_support import create_client
from backend.core.config import settings

client = create_client()

telegram_user_id = 99999
client.post("/api/users/ensure", json={"telegram_user_id": telegram_user_id, "username": "queued_user", "first_name": "Queued", "language_code": "ru"})

plan = client.get("/api/plans/").json()[0]
order = client.post("/api/orders/", json={"telegram_user_id": telegram_user_id, "plan_code": plan["code"], "payment_method": "card"}).json()
payment = client.post("/api/payments/", json={"order_id": order["id"], "provider": "cards", "method": "card"}).json()
client.post(f"/api/payments/{payment['id']}/confirm")

print(">>> STARTING POST...")

from unittest.mock import patch, AsyncMock
with patch("worker.tasks.generation_tasks.requests.post") as mock_post, \
     patch("worker.tasks.generation_tasks.requests.get") as mock_get, \
     patch("worker.tasks.generation_tasks._notify_success", new_callable=AsyncMock) as mock_success, \
     patch("worker.tasks.generation_tasks._notify_failed", new_callable=AsyncMock) as mock_failed:
     
     mock_post.return_value.json.return_value = {"id": "mock_task_id", "status": "processing"}
     mock_get.return_value.json.return_value = {"status": "completed", "data": {"result": {"video_url": "https://mock.local/kling/vid.mp4"}}}
     
     settings.generation_process_now = False

     job_response = client.post(
         "/api/jobs/",
         json={
             "telegram_user_id": telegram_user_id,
             "provider": "kling",
             "prompt": "smooth cinematic motion through a neon alley",
         },
     )
     
     print(">>> POST DONE", job_response.status_code)
     print(">>> POST CONTENT", job_response.json())
     
     job = job_response.json()
     refreshed_job_response = client.get(f"/api/jobs/{job['id']}")
     print(">>> REFRESHED CONTENT", refreshed_job_response.json())
