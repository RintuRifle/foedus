"""
Foedus — Celery Application Configuration
Async task queue for running evaluations in the background.
"""

try:
    from celery import Celery
    _CELERY_AVAILABLE = True
except ImportError:
    # Slim prod image (TASK_RUNNER=inline) — celery not installed
    Celery = None
    _CELERY_AVAILABLE = False

from app.config import settings
from app.utils.tracing import configure_langsmith

# Enable LangSmith tracing in the worker process (no-op if disabled)
configure_langsmith()

celery_app = None
if _CELERY_AVAILABLE:
    celery_app = Celery(
        "foedus",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )

if celery_app:
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
if celery_app:
    celery_app.autodiscover_tasks(["app.tasks"])
from app.tasks.evaluation_task import evaluate_tender_task
