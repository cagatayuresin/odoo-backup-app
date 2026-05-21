"""Notification channel ORM models."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChannelType(str, enum.Enum):
    """Discriminator for the polymorphic notification binding."""

    smtp = "smtp"
    telegram = "telegram"


class SmtpChannel(Base):
    """SMTP email delivery configuration."""

    __tablename__ = "smtp_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    host: Mapped[str] = mapped_column(String(253), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=587)
    username: Mapped[str] = mapped_column(String(256), nullable=False)
    password_enc: Mapped[str] = mapped_column(Text, nullable=False)
    from_address: Mapped[str] = mapped_column(String(256), nullable=False)
    use_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    use_ssl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class TelegramChannel(Base):
    """Telegram Bot API delivery configuration."""

    __tablename__ = "telegram_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    bot_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class InstanceNotificationBinding(Base):
    """Links an Instance to a notification channel with event-level toggles."""

    __tablename__ = "instance_notification_bindings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False
    )
    channel_type: Mapped[ChannelType] = mapped_column(Enum(ChannelType), nullable=False)
    channel_id: Mapped[int] = mapped_column(Integer, nullable=False)
    on_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    on_failure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    instance: Mapped[Instance] = relationship(
        "Instance", back_populates="notification_bindings"
    )


from app.models.instance import Instance  # noqa: E402, F401
