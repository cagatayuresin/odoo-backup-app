"""SMTP and Telegram channel CRUD + test endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_password_changed
from app.core.security import encrypt_secret
from app.models.notify import SmtpChannel, TelegramChannel
from app.models.user import User
from app.schemas.notify import (
    SmtpChannelCreate,
    SmtpChannelRead,
    SmtpChannelUpdate,
    TelegramChannelCreate,
    TelegramChannelRead,
    TelegramChannelUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/channels", tags=["channels"])


# ─── SMTP ─────────────────────────────────────────────────────────────────────

@router.get("/smtp", response_model=list[SmtpChannelRead])
def list_smtp(
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> list[SmtpChannel]:
    """List all SMTP channels."""
    return db.query(SmtpChannel).all()


@router.post("/smtp", response_model=SmtpChannelRead, status_code=status.HTTP_201_CREATED)
def create_smtp(
    body: SmtpChannelCreate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> SmtpChannel:
    """Create an SMTP channel."""
    channel = SmtpChannel(
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
        password_enc=encrypt_secret(body.password),
        from_address=body.from_address,
        use_tls=body.use_tls,
        use_ssl=body.use_ssl,
        enabled=body.enabled,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.get("/smtp/{channel_id}", response_model=SmtpChannelRead)
def get_smtp(
    channel_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> SmtpChannel:
    """Return a single SMTP channel."""
    channel = db.get(SmtpChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP channel not found")
    return channel


@router.patch("/smtp/{channel_id}", response_model=SmtpChannelRead)
def update_smtp(
    channel_id: int,
    body: SmtpChannelUpdate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> SmtpChannel:
    """Partially update an SMTP channel."""
    channel = db.get(SmtpChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP channel not found")

    update_data = body.model_dump(exclude_unset=True)
    if "password" in update_data:
        channel.password_enc = encrypt_secret(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(channel, field, value)
    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/smtp/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_smtp(
    channel_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> None:
    """Delete an SMTP channel."""
    channel = db.get(SmtpChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP channel not found")
    db.delete(channel)
    db.commit()


@router.post("/smtp/{channel_id}/test")
def test_smtp(
    channel_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Send a test email via the specified SMTP channel."""
    channel = db.get(SmtpChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP channel not found")

    from app.services.notify.smtp import send_test_email

    try:
        send_test_email(channel)
        return {"detail": "Test email sent"}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


# ─── Telegram ─────────────────────────────────────────────────────────────────

@router.get("/telegram", response_model=list[TelegramChannelRead])
def list_telegram(
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> list[TelegramChannel]:
    """List all Telegram channels."""
    return db.query(TelegramChannel).all()


@router.post("/telegram", response_model=TelegramChannelRead, status_code=status.HTTP_201_CREATED)
def create_telegram(
    body: TelegramChannelCreate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> TelegramChannel:
    """Create a Telegram channel."""
    channel = TelegramChannel(
        name=body.name,
        bot_token_enc=encrypt_secret(body.bot_token),
        chat_id=body.chat_id,
        enabled=body.enabled,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.get("/telegram/{channel_id}", response_model=TelegramChannelRead)
def get_telegram(
    channel_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> TelegramChannel:
    """Return a single Telegram channel."""
    channel = db.get(TelegramChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram channel not found")
    return channel


@router.patch("/telegram/{channel_id}", response_model=TelegramChannelRead)
def update_telegram(
    channel_id: int,
    body: TelegramChannelUpdate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> TelegramChannel:
    """Partially update a Telegram channel."""
    channel = db.get(TelegramChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram channel not found")

    update_data = body.model_dump(exclude_unset=True)
    if "bot_token" in update_data:
        channel.bot_token_enc = encrypt_secret(update_data.pop("bot_token"))
    for field, value in update_data.items():
        setattr(channel, field, value)
    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/telegram/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_telegram(
    channel_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> None:
    """Delete a Telegram channel."""
    channel = db.get(TelegramChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram channel not found")
    db.delete(channel)
    db.commit()


@router.post("/telegram/{channel_id}/test")
def test_telegram(
    channel_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Send a test Telegram message."""
    channel = db.get(TelegramChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram channel not found")

    from app.services.notify.telegram import send_test_message

    try:
        send_test_message(channel)
        return {"detail": "Test message sent"}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
