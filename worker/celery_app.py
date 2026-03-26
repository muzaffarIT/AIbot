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
    "cleanup-stale-jobs": {
        "task": "worker.tasks.generation_tasks.cleanup_stale_jobs_task",
        "schedule": crontab(minute=0, hour=0),
    },
    "daily-bonus-reminder": {
        "task": "worker.tasks.notification_tasks.daily_reminder_task",
        "schedule": crontab(minute=0, hour=0),
    },
    "lifecycle-notification": {
        "task": "worker.tasks.notification_tasks.lifecycle_notification_task",
        "schedule": crontab(minute=0, hour=0),
    }
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
