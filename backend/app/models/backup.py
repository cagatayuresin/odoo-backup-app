"""BackupRun ORM model."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BackupStatus(StrEnum):
    """Overall lifecycle status of a backup run."""

    running = "running"
    success = "success"
    failed = "failed"
    verified = "verified"
    verify_failed = "verify_failed"


class VerificationStatus(StrEnum):
    """Result of the post-backup integrity check."""

    not_run = "not_run"
    passed = "passed"
    failed = "failed"


class BackupRun(Base):
    """Record of a single backup attempt for one database."""

    __tablename__ = "backup_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[BackupStatus] = mapped_column(
        Enum(BackupStatus), nullable=False, default=BackupStatus.running
    )
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    db_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), nullable=False, default=VerificationStatus.not_run
    )
    # JSON: {"gdrive": "uploaded", "dropbox": "pending", ...}
    cloud_sync_status: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[Job | None] = relationship("Job", back_populates="backup_runs")
    instance: Mapped[Instance] = relationship("Instance", back_populates="backup_runs")


from app.models.instance import Instance  # noqa: E402
from app.models.job import Job  # noqa: E402
