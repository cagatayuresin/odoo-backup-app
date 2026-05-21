"""Telegram Bot API notification service (synchronous via httpx)."""

from __future__ import annotations

import logging

import httpx

from app.core.security import decrypt_secret
from app.models.backup import BackupRun, BackupStatus
from app.models.notify import TelegramChannel

logger = logging.getLogger(__name__)

_BOT_API = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT = httpx.Timeout(30.0)

_STATUS_EMOJI = {
    BackupStatus.success: "✅",
    BackupStatus.verified: "✅",
    BackupStatus.failed: "❌",
    BackupStatus.verify_failed: "⚠️",
    BackupStatus.running: "🔄",
}


def _format_backup_message(run: BackupRun) -> str:
    """Build the Telegram Markdown notification message."""
    emoji = _STATUS_EMOJI.get(run.status, "ℹ️")
    instance_name = run.instance.name if run.instance else str(run.instance_id)
    started = run.started_at.strftime("%Y-%m-%d %H:%M UTC")

    duration_str = ""
    if run.finished_at and run.started_at:
        delta = run.finished_at - run.started_at
        duration_str = f"{int(delta.total_seconds())}s"

    size_str = ""
    if run.file_size_bytes:
        mb = run.file_size_bytes / 1_048_576
        size_str = f"{mb:.1f} MB"

    lines = [
        f"{emoji} *Backup {run.status.value.upper()}*",
        f"📦 Instance: `{instance_name}`",
        f"🗄️ DB: `{run.db_name}`",
        f"🕐 Started: {started}",
    ]
    if duration_str:
        lines.append(f"⏱️ Duration: {duration_str}")
    if size_str:
        lines.append(f"💾 Size: {size_str}")
    if run.verification_status.value != "not_run":
        lines.append(f"🔍 Verification: {run.verification_status.value}")
    if run.error_message:
        snippet = run.error_message[:200].replace("`", "'")
        lines.append(f"🔴 Error: `{snippet}`")

    return "\n".join(lines)


def notify_backup_run(run: BackupRun, channel: TelegramChannel) -> None:
    """Send a backup run notification to *channel*."""
    token = decrypt_secret(channel.bot_token_enc)
    text = _format_backup_message(run)
    url = _BOT_API.format(token=token)

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                url,
                json={"chat_id": channel.chat_id, "text": text, "parse_mode": "Markdown"},
            )
            resp.raise_for_status()
        logger.info("Telegram notification sent for run %d via channel %d", run.id, channel.id)
    except Exception:
        logger.exception("Failed to send Telegram notification for run %d", run.id)
        raise


def send_test_message(channel: TelegramChannel) -> None:
    """Send a test message to verify the Telegram channel configuration."""
    token = decrypt_secret(channel.bot_token_enc)
    url = _BOT_API.format(token=token)
    text = "✅ This is a test message from *Odoo Backup Orchestrator*\\. Channel is configured correctly\\."

    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(
            url,
            json={"chat_id": channel.chat_id, "text": text, "parse_mode": "MarkdownV2"},
        )
        resp.raise_for_status()
