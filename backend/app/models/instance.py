"""Instance ORM model."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BackupMethod(StrEnum):
    """Strategy for backing up this instance."""

    odoo_endpoint = "odoo_endpoint"
    pg_dump = "pg_dump"


class DbSelectionMode(StrEnum):
    """Which databases to back up."""

    single = "single"
    selected = "selected"
    all = "all"


class RetentionMode(StrEnum):
    """How to expire old backups."""

    keep_last_n = "keep_last_n"
    older_than_days = "older_than_days"


class Instance(Base):
    """An Odoo installation to be backed up."""

    __tablename__ = "instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    # URL storage — raw as entered + parsed components
    raw_url: Mapped[str] = mapped_column(String(512), nullable=False)
    parsed_scheme: Mapped[str] = mapped_column(String(8), nullable=False, default="https")
    parsed_host: Mapped[str] = mapped_column(String(253), nullable=False)
    parsed_port: Mapped[int] = mapped_column(Integer, nullable=False, default=443)

    # Backup strategy
    backup_method: Mapped[BackupMethod] = mapped_column(
        Enum(BackupMethod), nullable=False, default=BackupMethod.odoo_endpoint
    )

    # odoo_endpoint fields
    master_password_enc: Mapped[str | None] = mapped_column(Text, nullable=True)

    # pg_dump fields
    db_host: Mapped[str | None] = mapped_column(String(253), nullable=True)
    db_port: Mapped[int | None] = mapped_column(Integer, nullable=True, default=5432)
    db_user: Mapped[str | None] = mapped_column(String(128), nullable=True)
    db_password_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    filestore_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Database selection
    db_selection_mode: Mapped[DbSelectionMode] = mapped_column(
        Enum(DbSelectionMode), nullable=False, default=DbSelectionMode.single
    )
    db_names: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list

    include_filestore: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Retention
    retention_mode: Mapped[RetentionMode] = mapped_column(
        Enum(RetentionMode), nullable=False, default=RetentionMode.keep_last_n
    )
    retention_value: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    # Notifications
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    jobs: Mapped[list[Job]] = relationship(
        "Job", back_populates="instance", cascade="all, delete-orphan"
    )
    backup_runs: Mapped[list[BackupRun]] = relationship(
        "BackupRun", back_populates="instance", cascade="all, delete-orphan"
    )
    notification_bindings: Mapped[list[InstanceNotificationBinding]] = relationship(
        "InstanceNotificationBinding", back_populates="instance", cascade="all, delete-orphan"
    )
    cloud_bindings: Mapped[list[InstanceCloudBinding]] = relationship(
        "InstanceCloudBinding", back_populates="instance", cascade="all, delete-orphan"
    )


from app.models.backup import BackupRun  # noqa: E402
from app.models.cloud import InstanceCloudBinding  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.notify import InstanceNotificationBinding  # noqa: E402
