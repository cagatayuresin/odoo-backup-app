"""Cloud provider ORM models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CloudProvider(StrEnum):
    """Supported cloud storage providers."""

    gdrive = "gdrive"
    dropbox = "dropbox"
    onedrive = "onedrive"


class CloudAccount(Base):
    """OAuth credentials for a cloud storage provider account."""

    __tablename__ = "cloud_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[CloudProvider] = mapped_column(Enum(CloudProvider), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    credentials_enc: Mapped[str] = mapped_column(Text, nullable=False)  # JSON, Fernet-encrypted
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    instance_bindings: Mapped[list[InstanceCloudBinding]] = relationship(
        "InstanceCloudBinding", back_populates="cloud_account", cascade="all, delete-orphan"
    )


class InstanceCloudBinding(Base):
    """Links an Instance to a CloudAccount for post-backup sync."""

    __tablename__ = "instance_cloud_bindings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False
    )
    cloud_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cloud_accounts.id", ondelete="CASCADE"), nullable=False
    )
    remote_folder: Mapped[str] = mapped_column(String(512), nullable=False, default="/odoo-backups")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    apply_retention_remotely: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    instance: Mapped[Instance] = relationship("Instance", back_populates="cloud_bindings")
    cloud_account: Mapped[CloudAccount] = relationship(
        "CloudAccount", back_populates="instance_bindings"
    )


from app.models.instance import Instance  # noqa: E402
