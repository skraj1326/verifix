"""Celery application for async task execution."""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "astrixcore",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,
    task_time_limit=900,
    task_routes={
        "app.tasks.simulation.*": {"queue": "simulation"},
        "app.tasks.ai.*": {"queue": "ai"},
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
