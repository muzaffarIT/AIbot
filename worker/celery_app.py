import os
from celery import Celery
from celery.signals import worker_process_init
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

from backend.core.config import settings
from backend.db.init_db import init_db

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=redis_url,
    backend=redis_url,
    include=["worker.tasks.generation_tasks", "worker.tasks.monitoring_tasks", "worker.tasks.notification_tasks"],
)

celery_app.conf.beat_schedule = {
    "financial-monitor-daily": {
        "task": "worker.tasks.monitoring_tasks.financial_monitor_task",
        "schedule": crontab(minute=0, hour=0),
    },
    # Run stale-job sweeper every 10 minutes (was daily at midnight). Picks
    # up jobs stuck in PENDING/PROCESSING > 15 min, marks them FAILED and
    # refunds credits. Critical for catching worker crashes or KIE hangs
    # before they sit on the user for hours.
    "cleanup-stale-jobs": {
        "task": "worker.tasks.generation_tasks.cleanup_stale_jobs_task",
        "schedule": crontab(minute="*/10"),
    },
    "daily-bonus-reminder": {
        "task": "worker.tasks.notification_tasks.daily_reminder_task",
        "schedule": crontab(minute=0, hour=0),
    },
    "lifecycle-notification": {
        "task": "worker.tasks.notification_tasks.lifecycle_notification_task",
        "schedule": crontab(minute=0, hour=0),
    },
    # Win-back dormant users once a day at 15:00 Tashkent (good send window).
    "winback-inactive": {
        "task": "worker.tasks.notification_tasks.winback_inactive_task",
        "schedule": crontab(minute=0, hour=15),
    },
    "daily-sheets-summary": {
        "task": "worker.tasks.monitoring_tasks.daily_sheets_summary",
        "schedule": crontab(hour=23, minute=59),
    },
}

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Tashkent",
    enable_utc=False,
    task_always_eager=settings.celery_task_always_eager,
)


@worker_process_init.connect
def prepare_worker_database(**_: object) -> None:
    init_db()
