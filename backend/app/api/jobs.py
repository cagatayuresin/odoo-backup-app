"""Job CRUD + manual trigger endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_password_changed
from app.core.cron import next_run_utc
from app.models.instance import Instance
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobRead, JobUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/instances/{instance_id}/jobs", tags=["jobs"])


def _get_instance_or_404(instance_id: int, db: Session) -> Instance:
    """Return Instance or raise 404."""
    inst = db.get(Instance, instance_id)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    return inst


@router.get("/", response_model=list[JobRead])
def list_jobs(
    instance_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> list[Job]:
    """List all jobs for an instance."""
    _get_instance_or_404(instance_id, db)
    return db.query(Job).filter(Job.instance_id == instance_id).all()


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    instance_id: int,
    body: JobCreate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> Job:
    """Create a new scheduled job for an instance."""
    _get_instance_or_404(instance_id, db)

    job = Job(
        instance_id=instance_id,
        name=body.name,
        cron_expression=body.cron_expression,
        enabled=body.enabled,
        next_run_at=next_run_utc(body.cron_expression),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    instance_id: int,
    job_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> Job:
    """Return a single job."""
    job = db.get(Job, job_id)
    if job is None or job.instance_id != instance_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    instance_id: int,
    job_id: int,
    body: JobUpdate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> Job:
    """Partially update a job."""
    job = db.get(Job, job_id)
    if job is None or job.instance_id != instance_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    if "cron_expression" in update_data:
        job.next_run_at = next_run_utc(update_data["cron_expression"])

    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    instance_id: int,
    job_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> None:
    """Delete a job."""
    job = db.get(Job, job_id)
    if job is None or job.instance_id != instance_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    db.delete(job)
    db.commit()


@router.post("/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
def run_job_now(
    instance_id: int,
    job_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Enqueue an immediate run of the job."""
    job = db.get(Job, job_id)
    if job is None or job.instance_id != instance_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    from app.tasks.backup_tasks import run_backup_job

    task = run_backup_job.delay(job_id)
    logger.info("Manual run enqueued for job %d, task_id=%s", job_id, task.id)
    return {"task_id": task.id, "detail": "Backup job enqueued"}
