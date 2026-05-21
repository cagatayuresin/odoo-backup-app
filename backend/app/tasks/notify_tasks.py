"""Celery task for dispatching backup run notifications."""

from __future__ import annotations

import logging

from celery import shared_task

from app.db import SessionLocal

logger = logging.getLogger(__name__)


@shared_task(name="app.tasks.notify_tasks.dispatch_notification")  # type: ignore[untyped-decorator]
def dispatch_notification(run_id: int) -> dict[str, object]:
    """Dispatch notifications for a finished backup run."""
    with SessionLocal() as db:
        from app.models.backup import BackupRun

        run = db.get(BackupRun, run_id)
        if run is None:
            logger.warning("BackupRun %d not found — skipping notification", run_id)
            return {"status": "skipped"}

        from app.services.notify.dispatcher import dispatch

        try:
            dispatch(run, db)
            return {"status": "dispatched"}
        except Exception:
            logger.exception("Notification dispatch failed for run %d", run_id)
            return {"status": "error"}
