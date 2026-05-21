"""SMTP notification service."""

from __future__ import annotations

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from sqlalchemy.orm import Session

from app.core.security import decrypt_secret
from app.models.backup import BackupRun, BackupStatus
from app.models.notify import SmtpChannel
from app.models.user import User

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _render_backup_email(run: BackupRun) -> str:
    """Generate the HTML body for a backup run notification."""
    status_color = {
        BackupStatus.success: "#28a745",
        BackupStatus.verified: "#28a745",
        BackupStatus.failed: "#D9534F",
        BackupStatus.verify_failed: "#F0AD4E",
        BackupStatus.running: "#6B7280",
    }.get(run.status, "#6B7280")

    duration_str = ""
    if run.finished_at and run.started_at:
        delta = run.finished_at - run.started_at
        duration_str = f"{int(delta.total_seconds())}s"

    size_str = ""
    if run.file_size_bytes:
        mb = run.file_size_bytes / 1_048_576
        size_str = f"{mb:.1f} MB"

    error_row = ""
    if run.error_message:
        escaped = run.error_message[:512].replace("<", "&lt;").replace(">", "&gt;")
        error_row = f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #E5E7EB;font-weight:600;">Error</td>
          <td style="padding:8px;border-bottom:1px solid #E5E7EB;font-family:monospace;color:#D9534F;">{escaped}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#F7F7F8;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:32px auto;">
    <tr>
      <td style="background:#714B67;padding:20px 28px;border-radius:8px 8px 0 0;">
        <span style="color:#fff;font-size:18px;font-weight:600;">Odoo Backup Orchestrator</span>
      </td>
    </tr>
    <tr>
      <td style="background:#fff;padding:28px;border:1px solid #E5E7EB;border-top:none;border-radius:0 0 8px 8px;">
        <p style="margin:0 0 16px;">Backup run completed for instance
          <strong>{run.instance.name if run.instance else run.instance_id}</strong>
        </p>
        <span style="display:inline-block;padding:4px 12px;border-radius:4px;background:{status_color};color:#fff;font-size:14px;font-weight:600;margin-bottom:20px;">
          {run.status.value.upper()}
        </span>
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:14px;">
          <tr>
            <td style="padding:8px;border-bottom:1px solid #E5E7EB;font-weight:600;">Database</td>
            <td style="padding:8px;border-bottom:1px solid #E5E7EB;">{run.db_name}</td>
          </tr>
          <tr>
            <td style="padding:8px;border-bottom:1px solid #E5E7EB;font-weight:600;">Started</td>
            <td style="padding:8px;border-bottom:1px solid #E5E7EB;">{run.started_at.strftime("%Y-%m-%d %H:%M:%S UTC")}</td>
          </tr>
          <tr>
            <td style="padding:8px;border-bottom:1px solid #E5E7EB;font-weight:600;">Duration</td>
            <td style="padding:8px;border-bottom:1px solid #E5E7EB;">{duration_str or "N/A"}</td>
          </tr>
          <tr>
            <td style="padding:8px;border-bottom:1px solid #E5E7EB;font-weight:600;">File Size</td>
            <td style="padding:8px;border-bottom:1px solid #E5E7EB;">{size_str or "N/A"}</td>
          </tr>
          <tr>
            <td style="padding:8px;border-bottom:1px solid #E5E7EB;font-weight:600;">Verification</td>
            <td style="padding:8px;border-bottom:1px solid #E5E7EB;">{run.verification_status.value}</td>
          </tr>
          {error_row}
        </table>
        <p style="margin:24px 0 0;font-size:12px;color:#6B7280;">
          Odoo Backup Orchestrator &mdash; self-hosted backup for Odoo
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""


async def _send_async(
    channel: SmtpChannel,
    to_address: str,
    subject: str,
    html_body: str,
) -> None:
    """Send an email asynchronously via aiosmtplib."""
    password = decrypt_secret(channel.password_enc)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = channel.from_address
    msg["To"] = to_address
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=channel.host,
        port=channel.port,
        username=channel.username,
        password=password,
        use_tls=channel.use_ssl,
        start_tls=channel.use_tls,
        timeout=30,
    )


def _send_sync(channel: SmtpChannel, to_address: str, subject: str, html_body: str) -> None:
    """Synchronous wrapper around the async send function."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(_send_async(channel, to_address, subject, html_body))


def notify_backup_run(run: BackupRun, channel: SmtpChannel, to_address: str) -> None:
    """Send a backup run result notification via *channel* to *to_address*."""
    status_label = run.status.value.upper()
    db_label = run.db_name or "unknown"
    subject = f"[Backup {status_label}] {db_label}"

    html = _render_backup_email(run)
    try:
        _send_sync(channel, to_address, subject, html)
        logger.info("Notification email sent to %s for run %d", to_address, run.id)
    except Exception:
        logger.exception("Failed to send notification email to %s", to_address)
        raise


def send_test_email(channel: SmtpChannel) -> None:
    """Send a test email to verify the channel configuration."""
    html = """<html><body>
    <p>This is a test email from <strong>Odoo Backup Orchestrator</strong>.</p>
    <p>If you received this, your SMTP channel is configured correctly.</p>
    </body></html>"""
    _send_sync(channel, channel.from_address, "[Test] Odoo Backup Orchestrator", html)


def send_password_reset_email(user: User, token: str, db: Session) -> None:
    """Send a password reset email to the user's configured recovery address."""
    from app.models.notify import SmtpChannel as SmtpChannelModel

    if not user.recovery_channel_id or not user.recovery_email:
        logger.warning(
            "Password reset requested but recovery not configured for user %s", user.username
        )
        return

    channel = db.get(SmtpChannelModel, user.recovery_channel_id)
    if channel is None:
        logger.warning("Recovery channel %d not found", user.recovery_channel_id)
        return

    reset_link = f"http://localhost:8080/reset-password?token={token}"
    html = f"""<html><body>
    <p>A password reset was requested for your <strong>Odoo Backup Orchestrator</strong> account.</p>
    <p><a href="{reset_link}">Click here to reset your password</a> (valid for 15 minutes).</p>
    <p>If you did not request this, you can safely ignore this email.</p>
    </body></html>"""

    _send_sync(channel, user.recovery_email, "Password Reset — Odoo Backup Orchestrator", html)
