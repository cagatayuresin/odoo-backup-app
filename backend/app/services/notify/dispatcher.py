"""Notification dispatcher — routes backup run outcomes to configured channels."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.backup import BackupRun, BackupStatus
from app.models.notify import ChannelType, InstanceNotificationBinding, SmtpChannel, TelegramChannel

logger = logging.getLogger(__name__)

_SUCCESS_STATUSES = {BackupStatus.success, BackupStatus.verified}
_FAILURE_STATUSES = {BackupStatus.failed, BackupStatus.verify_failed}


def _is_success(run: BackupRun) -> bool:
    return run.status in _SUCCESS_STATUSES


def _is_failure(run: BackupRun) -> bool:
    return run.status in _FAILURE_STATUSES


def dispatch(run: BackupRun, db: Session) -> None:
    """Dispatch notifications for a finished backup run.

    Respects ``instance.notifications_enabled`` and per-binding
    ``on_success`` / ``on_failure`` toggles.
    """
    instance = run.instance
    if instance is None or not instance.notifications_enabled:
        return

    bindings: list[InstanceNotificationBinding] = (
        db.query(InstanceNotificationBinding)
        .filter(InstanceNotificationBinding.instance_id == run.instance_id)
        .all()
    )

    is_success = _is_success(run)
    is_failure = _is_failure(run)

    if not is_success and not is_failure:
        return  # still running or unknown — skip

    for binding in bindings:
        if is_success and not binding.on_success:
            continue
        if is_failure and not binding.on_failure:
            continue

        try:
            _deliver(run, binding, db)
        except Exception:
            logger.exception(
                "Notification delivery failed for binding %d (run %d)",
                binding.id,
                run.id,
            )


def _deliver(run: BackupRun, binding: InstanceNotificationBinding, db: Session) -> None:
    """Deliver a notification via the channel specified in *binding*."""
    if binding.channel_type == ChannelType.smtp:
        smtp_channel = db.get(SmtpChannel, binding.channel_id)
        if smtp_channel is None or not smtp_channel.enabled:
            logger.debug("SMTP channel %d not found or disabled — skipping", binding.channel_id)
            return

        to_address = smtp_channel.from_address
        from app.services.notify.smtp import notify_backup_run as smtp_notify

        smtp_notify(run, smtp_channel, to_address)

    elif binding.channel_type == ChannelType.telegram:
        tg_channel = db.get(TelegramChannel, binding.channel_id)
        if tg_channel is None or not tg_channel.enabled:
            logger.debug("Telegram channel %d not found or disabled — skipping", binding.channel_id)
            return

        from app.services.notify.telegram import notify_backup_run as telegram_notify

        telegram_notify(run, tg_channel)
