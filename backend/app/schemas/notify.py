"""Pydantic schemas for notification channels."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.notify import ChannelType


class SmtpChannelCreate(BaseModel):
    """Request body for creating an SMTP channel."""

    name: str
    host: str
    port: int = 587
    username: str
    password: str
    from_address: str
    use_tls: bool = True
    use_ssl: bool = False
    enabled: bool = True


class SmtpChannelUpdate(BaseModel):
    """Partial SMTP channel update."""

    name: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    from_address: str | None = None
    use_tls: bool | None = None
    use_ssl: bool | None = None
    enabled: bool | None = None


class SmtpChannelRead(BaseModel):
    """Public SMTP channel (no plaintext password)."""

    id: int
    name: str
    host: str
    port: int
    username: str
    from_address: str
    use_tls: bool
    use_ssl: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TelegramChannelCreate(BaseModel):
    """Request body for creating a Telegram channel."""

    name: str
    bot_token: str
    chat_id: str
    enabled: bool = True


class TelegramChannelUpdate(BaseModel):
    """Partial Telegram channel update."""

    name: str | None = None
    bot_token: str | None = None
    chat_id: str | None = None
    enabled: bool | None = None


class TelegramChannelRead(BaseModel):
    """Public Telegram channel (no plaintext token)."""

    id: int
    name: str
    chat_id: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationBindingCreate(BaseModel):
    """Bind a channel to an instance."""

    channel_type: ChannelType
    channel_id: int
    on_success: bool = True
    on_failure: bool = True


class NotificationBindingRead(BaseModel):
    """Public representation of a notification binding."""

    id: int
    instance_id: int
    channel_type: ChannelType
    channel_id: int
    on_success: bool
    on_failure: bool

    model_config = {"from_attributes": True}
