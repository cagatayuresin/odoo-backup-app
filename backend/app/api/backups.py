"""BackupRun listing, download, deletion, re-verify, and re-upload endpoints."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_password_changed
from app.models.backup import BackupRun, BackupStatus
from app.models.user import User
from app.schemas.backup import BackupRunRead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backups", tags=["backups"])


@router.get("/", response_model=list[BackupRunRead])
def list_backups(
    instance_id: int | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> list[BackupRun]:
    """List backup runs, optionally filtered by instance."""
    q = db.query(BackupRun).order_by(BackupRun.started_at.desc())
    if instance_id is not None:
        q = q.filter(BackupRun.instance_id == instance_id)
    return q.offset(offset).limit(limit).all()


@router.get("/{run_id}", response_model=BackupRunRead)
def get_backup(
    run_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> BackupRun:
    """Return a single backup run."""
    run = db.get(BackupRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")
    return run


@router.get("/{run_id}/download")
def download_backup(
    run_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream the backup file to the client."""
    run = db.get(BackupRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")
    if not run.file_path or not Path(run.file_path).is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Backup file not found on disk"
        )

    return FileResponse(
        path=run.file_path,
        filename=os.path.basename(run.file_path),
        media_type="application/octet-stream",
    )


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backup(
    run_id: int,
    force: bool = Query(False, description="Bypass safety net (force delete)"),
    confirmation: str = Query("", description="Must be 'DELETE' when force=true"),
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> None:
    """Delete a backup run and its file.

    When *force=false* (default), the safety net prevents deleting the only
    remaining successful backup for the instance.
    """
    run = db.get(BackupRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")

    if force:
        if confirmation != "DELETE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Type DELETE in the confirmation field to force-delete",
            )
    else:
        # Safety net: check if this is the last successful backup
        successful_count = (
            db.query(BackupRun)
            .filter(
                BackupRun.instance_id == run.instance_id,
                BackupRun.status.in_([BackupStatus.success, BackupStatus.verified]),
            )
            .count()
        )
        if successful_count <= 1 and run.status in (BackupStatus.success, BackupStatus.verified):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Cannot delete the last successful backup. "
                    "Use force=true with confirmation='DELETE' to override."
                ),
            )

    # Delete the file from disk
    if run.file_path:
        try:
            Path(run.file_path).unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not delete file %s", run.file_path)

    db.delete(run)
    db.commit()


@router.post("/{run_id}/verify", status_code=status.HTTP_202_ACCEPTED)
def re_verify_backup(
    run_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Enqueue a re-verification of an existing backup file."""
    run = db.get(BackupRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")
    if not run.file_path or not Path(run.file_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file not on disk")

    from app.tasks.backup_tasks import verify_backup_run

    task = verify_backup_run.delay(run_id)
    return {"task_id": task.id, "detail": "Re-verification enqueued"}


@router.post("/{run_id}/reupload", status_code=status.HTTP_202_ACCEPTED)
def re_upload_backup(
    run_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Enqueue a re-upload of a backup to all configured cloud destinations."""
    run = db.get(BackupRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")
    if not run.file_path or not Path(run.file_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file not on disk")

    from app.tasks.cloud_tasks import sync_backup_to_cloud

    task = sync_backup_to_cloud.delay(run_id)
    return {"task_id": task.id, "detail": "Cloud re-upload enqueued"}
