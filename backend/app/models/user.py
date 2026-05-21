"""User ORM model — single-row enforced at the application layer."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """Application administrator account (single row)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default="admin")
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    recovery_email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    recovery_channel_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("smtp_channels.id", ondelete="SET NULL"),
        nullable=True,
    )
    password_reset_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # One-time reset token (hashed with sha256, 15-min TTL handled in service layer)
    reset_token_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    recovery_channel: Mapped[SmtpChannel | None] = relationship(
        "SmtpChannel", foreign_keys=[recovery_channel_id]
    )


# Avoid circular import — SmtpChannel imported lazily via string reference above
from app.models.notify import SmtpChannel  # noqa: E402
