"""Dynamic Celery Beat scheduler that re-reads Job rows from the DB every 30s.

Uses celery-redbeat so schedules survive Beat restarts without losing state.
Beat's max_loop_interval=30 (set in celery_app.py) causes it to call
this refresh regularly.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="app.tasks.scheduler.refresh_schedules")
def refresh_schedules() -> dict[str, object]:
    """Synchronise redbeat entries with the current set of enabled jobs.

    This task is itself scheduled via an ordinary redbeat entry created on
    app startup (see bootstrap_beat_schedule in main.py). Each invocation
    reconciles the set of per-job redbeat entries with the DB.
    """
    from redbeat import RedBeatSchedulerEntry

    from app.db import SessionLocal
    from app.models.job import Job
    from app.tasks.celery_app import celery_app

    with SessionLocal() as db:
        jobs = db.query(Job).all()

    for job in jobs:
        entry_key = f"job:{job.id}"
        try:
            if job.enabled:
                entry = RedBeatSchedulerEntry(
                    name=entry_key,
                    task="app.tasks.backup_tasks.run_backup_job",
                    schedule=_cron_schedule(job.cron_expression),
                    args=[job.id],
                    app=celery_app,
                )
                entry.save()
            else:
                # Remove the entry if the job is disabled
                try:
                    existing = RedBeatSchedulerEntry.from_key(
                        f"redbeat:{entry_key}", app=celery_app
                    )
                    existing.delete()
                except Exception:
                    pass
        except Exception:
            logger.exception("Failed to sync schedule for job %d", job.id)

    logger.debug("Beat schedule refreshed — %d jobs processed", len(jobs))
    return {"synced": len(jobs)}


def _cron_schedule(expression: str) -> object:
    """Convert a 5-field cron string to a celery crontab schedule."""
    from celery.schedules import crontab

    parts = expression.split()
    if len(parts) != 5:  # noqa: PLR2004
        msg = f"Expected 5-field cron, got: {expression!r}"
        raise ValueError(msg)
    minute, hour, day_of_month, month_of_year, day_of_week = parts
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
    )


def bootstrap_beat_schedule() -> None:
    """Register the schedule-refresh task itself in redbeat on first boot.

    Called from ``app.main.create_app`` so Beat always knows to run the
    refresh task even before the first UI interaction.
    """
    try:
        from redbeat import RedBeatSchedulerEntry
        from celery.schedules import crontab

        from app.tasks.celery_app import celery_app

        entry = RedBeatSchedulerEntry(
            name="scheduler:refresh",
            task="app.tasks.scheduler.refresh_schedules",
            schedule=crontab(minute="*/1"),  # every minute
            app=celery_app,
        )
        entry.save()
        logger.info("Beat schedule refresh entry registered")
    except Exception:
        logger.warning("Could not register beat schedule refresh (Redis may not be running)", exc_info=True)
