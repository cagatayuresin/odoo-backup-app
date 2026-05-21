"""Celery application factory with celery-redbeat for dynamic scheduling."""

from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "odoo_backup",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.backup_tasks",
        "app.tasks.cloud_tasks",
        "app.tasks.notify_tasks",
        "app.tasks.scheduler",
    ],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Result expiry — 7 days
    result_expires=604800,
    # Queues
    task_routes={
        "app.tasks.backup_tasks.*": {"queue": "backups"},
        "app.tasks.cloud_tasks.*": {"queue": "cloud"},
        "app.tasks.notify_tasks.*": {"queue": "notifications"},
        "app.tasks.scheduler.*": {"queue": "default"},
    },
    task_default_queue="default",
    # Retry behaviour
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # redbeat — re-scan the DB for new/updated jobs every 30s
    redbeat_redis_url=settings.redis_url,
    redbeat_key_prefix="redbeat",
    beat_scheduler="redbeat.RedBeatScheduler",
    beat_max_loop_interval=30,
)
