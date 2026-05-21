"""Celery tasks for backup execution and verification."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from celery import shared_task

from app.db import SessionLocal
from app.models.backup import BackupRun, BackupStatus, VerificationStatus
from app.models.instance import DbSelectionMode, Instance

logger = logging.getLogger(__name__)


def _get_db_names(instance: Instance) -> list[str]:
    """Resolve which database names to back up for *instance*."""
    from app.models.instance import BackupMethod

    if instance.db_selection_mode == DbSelectionMode.single:
        names_raw = json.loads(instance.db_names or "[]")
        return [names_raw[0]] if names_raw else []

    if instance.db_selection_mode == DbSelectionMode.selected:
        return json.loads(instance.db_names or "[]")

    # all — discover
    if instance.backup_method == BackupMethod.odoo_endpoint:
        from app.services.backup import odoo_endpoint

        return odoo_endpoint.discover_databases(instance)
    else:
        from app.services.backup import pg_dump

        return pg_dump.discover_databases(instance)


@shared_task(bind=True, name="app.tasks.backup_tasks.run_backup_job", max_retries=2)
def run_backup_job(self: object, job_id: int) -> dict[str, object]:
    """Execute all database backups for the given job."""
    from app.models.job import Job

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.warning("Job %d not found — skipping", job_id)
            return {"status": "skipped", "reason": "job_not_found"}

        instance = db.get(Instance, job.instance_id)
        if instance is None:
            logger.warning("Instance %d not found for job %d", job.instance_id, job_id)
            return {"status": "skipped", "reason": "instance_not_found"}

        db_names = _get_db_names(instance)
        if not db_names:
            logger.warning("No databases found for job %d instance %s", job_id, instance.slug)
            return {"status": "skipped", "reason": "no_databases"}

        run_ids = []
        for db_name in db_names:
            run = BackupRun(
                job_id=job_id,
                instance_id=instance.id,
                started_at=datetime.now(timezone.utc),
                status=BackupStatus.running,
                db_name=db_name,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            run_ids.append(run.id)

            _execute_single_backup.delay(run.id)

        # Update job timestamps
        job.last_run_at = datetime.now(timezone.utc)
        from app.core.cron import next_run_utc

        job.next_run_at = next_run_utc(job.cron_expression)
        db.commit()

    return {"status": "enqueued", "run_ids": run_ids}


@shared_task(bind=True, name="app.tasks.backup_tasks.execute_single_backup", max_retries=1)
def _execute_single_backup(self: object, run_id: int) -> dict[str, object]:
    """Run a single database backup and update the BackupRun record."""
    from app.models.instance import BackupMethod

    with SessionLocal() as db:
        run = db.get(BackupRun, run_id)
        if run is None:
            return {"status": "skipped"}

        instance = db.get(Instance, run.instance_id)
        if instance is None:
            run.status = BackupStatus.failed
            run.error_message = "Instance not found"
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "failed"}

        # Choose strategy
        if instance.backup_method == BackupMethod.odoo_endpoint:
            from app.services.backup.odoo_endpoint import run as do_backup
        else:
            from app.services.backup.pg_dump import run as do_backup

        result = do_backup(instance, run.db_name)

        run.finished_at = datetime.now(timezone.utc)
        if result.success and result.file_path:
            run.file_path = str(result.file_path)
            run.file_size_bytes = result.file_size_bytes
            run.status = BackupStatus.success
        else:
            run.status = BackupStatus.failed
            run.error_message = result.error_message
            db.commit()

            # Notify on failure
            from app.tasks.notify_tasks import dispatch_notification

            dispatch_notification.delay(run_id)
            return {"status": "failed", "error": result.error_message}

        db.commit()

    # Verify and then apply retention + cloud sync
    verify_backup_run.delay(run_id)
    return {"status": "success", "run_id": run_id}


@shared_task(name="app.tasks.backup_tasks.verify_backup_run")
def verify_backup_run(run_id: int) -> dict[str, object]:
    """Verify the integrity of a backup file and update the run record."""
    with SessionLocal() as db:
        run = db.get(BackupRun, run_id)
        if run is None:
            return {"status": "skipped"}

        if not run.file_path:
            run.verification_status = VerificationStatus.failed
            run.status = BackupStatus.verify_failed
            db.commit()
            return {"status": "no_file"}

        from app.services.backup.verify import verify_backup

        passed, error = verify_backup(run.file_path)

        if passed:
            run.verification_status = VerificationStatus.passed
            run.status = BackupStatus.verified
        else:
            run.verification_status = VerificationStatus.failed
            run.status = BackupStatus.verify_failed
            run.error_message = error

        db.commit()

    # Apply local retention then cloud sync (even on verify_failed — file is kept but flagged)
    from app.tasks.backup_tasks import apply_retention
    from app.tasks.cloud_tasks import sync_backup_to_cloud
    from app.tasks.notify_tasks import dispatch_notification

    apply_retention.delay(run_id)
    dispatch_notification.delay(run_id)

    if passed:
        sync_backup_to_cloud.delay(run_id)

    return {"status": "verified" if passed else "verify_failed"}


@shared_task(name="app.tasks.backup_tasks.apply_retention")
def apply_retention(run_id: int) -> dict[str, object]:
    """Apply the instance's retention policy after a backup completes."""
    with SessionLocal() as db:
        run = db.get(BackupRun, run_id)
        if run is None:
            return {"status": "skipped"}

        instance = db.get(Instance, run.instance_id)
        if instance is None:
            return {"status": "skipped"}

        from app.models.backup import BackupStatus as BS

        all_runs = (
            db.query(BackupRun)
            .filter(
                BackupRun.instance_id == instance.id,
                BackupRun.status.in_([BS.success, BS.verified]),
            )
            .order_by(BackupRun.started_at.asc())
            .all()
        )

        run_pairs = [(r.id, r.started_at) for r in all_runs]

        from app.core.retention import compute_deletions

        deletions, safety_triggered = compute_deletions(
            run_pairs,
            instance.retention_mode.value,
            instance.retention_value,
        )

        if safety_triggered:
            logger.warning(
                "Retention for instance %s would delete all backups — skipped",
                instance.slug,
            )
            from app.models.audit import AuditLog

            db.add(
                AuditLog(
                    actor="system",
                    event="retention_safety_net",
                    details=json.dumps({"instance_id": instance.id, "instance_slug": instance.slug}),
                )
            )
            db.commit()
            return {"status": "safety_net_triggered"}

        import os
        from pathlib import Path

        for run_id_to_delete in deletions:
            old_run = db.get(BackupRun, run_id_to_delete)
            if old_run:
                if old_run.file_path:
                    try:
                        Path(old_run.file_path).unlink(missing_ok=True)
                    except OSError:
                        logger.warning("Could not delete file %s", old_run.file_path)
                db.delete(old_run)

        if deletions:
            db.commit()
            logger.info(
                "Retention deleted %d backup(s) for instance %s",
                len(deletions),
                instance.slug,
            )

    return {"status": "ok", "deleted": len(deletions)}
