"""Celery task for syncing backups to cloud storage."""

from __future__ import annotations

import logging

from celery import shared_task

from app.db import SessionLocal

logger = logging.getLogger(__name__)


@shared_task(name="app.tasks.cloud_tasks.sync_backup_to_cloud")
def sync_backup_to_cloud(run_id: int) -> dict[str, object]:
    """Upload a backup run to all configured cloud destinations."""
    with SessionLocal() as db:
        from app.models.backup import BackupRun

        run = db.get(BackupRun, run_id)
        if run is None:
            return {"status": "skipped"}

        from app.services.cloud.sync import sync_run

        try:
            sync_run(run, db)
            return {"status": "ok"}
        except Exception:
            logger.exception("Cloud sync failed for run %d", run_id)
            return {"status": "error"}
