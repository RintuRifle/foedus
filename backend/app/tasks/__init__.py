"""
Foedus — Celery Application Configuration
Async task queue for running evaluations in the background.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "foedus",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,        # 5 min hard limit per task
    task_soft_time_limit=240,   # 4 min soft limit (raises SoftTimeLimitExceeded)
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Auto-discover tasks from app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])
from app.tasks.evaluation_task import evaluate_tender_task
