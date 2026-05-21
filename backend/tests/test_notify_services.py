from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import encrypt_secret
from app.models.backup import BackupRun, BackupStatus, VerificationStatus
from app.models.notify import SmtpChannel, TelegramChannel


def _make_run(status: str = "success", error_message: str | None = None) -> MagicMock:
    run = MagicMock(spec=BackupRun)
    run.id = 1
    run.instance_id = 1
    run.db_name = "testdb"
    run.started_at = datetime(2026, 5, 21, 10, 0, 0, tzinfo=UTC)
    run.finished_at = datetime(2026, 5, 21, 10, 2, 0, tzinfo=UTC)
    run.status = BackupStatus(status)
    run.verification_status = VerificationStatus.passed
    run.file_size_bytes = 1024 * 512
    run.error_message = error_message
    run.instance = MagicMock()
    run.instance.name = "Test Instance"
    return run


def _make_smtp_channel() -> SmtpChannel:
    return SmtpChannel(
        id=1,
        name="Test SMTP",
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password_enc=encrypt_secret("mypassword"),
        from_address="noreply@example.com",
        use_tls=True,
        use_ssl=False,
        enabled=True,
    )


def _make_telegram_channel() -> TelegramChannel:
    return TelegramChannel(
        id=1,
        name="Test Telegram",
        bot_token_enc=encrypt_secret("123456:fake-token"),
        chat_id="-100123456",
        enabled=True,
    )


# ─── SMTP service ─────────────────────────────────────────────────────────────


def test_render_backup_email_success() -> None:
    from app.services.notify.smtp import _render_backup_email

    run = _make_run("success")
    html = _render_backup_email(run)
    assert "SUCCESS" in html
    assert "testdb" in html
    assert "#28a745" in html


def test_render_backup_email_failed() -> None:
    from app.services.notify.smtp import _render_backup_email

    run = _make_run("failed", error_message="Connection refused")
    html = _render_backup_email(run)
    assert "FAILED" in html
    assert "Connection refused" in html
    assert "#D9534F" in html


def test_render_backup_email_no_duration() -> None:
    from app.services.notify.smtp import _render_backup_email

    run = _make_run("success")
    run.finished_at = None
    html = _render_backup_email(run)
    assert "N/A" in html


def test_render_backup_email_no_instance() -> None:
    from app.services.notify.smtp import _render_backup_email

    run = _make_run("success")
    run.instance = None
    html = _render_backup_email(run)
    assert html is not None


def test_notify_backup_run_smtp() -> None:
    from app.services.notify.smtp import notify_backup_run

    run = _make_run("success")
    channel = _make_smtp_channel()

    with patch("app.services.notify.smtp._send_sync") as mock_send:
        notify_backup_run(run, channel, "dest@example.com")
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert args[1] == "dest@example.com"
        assert "BACKUP SUCCESS" in args[2] or "Backup SUCCESS" in args[2] or "SUCCESS" in args[2]


def test_notify_backup_run_smtp_raises() -> None:
    from app.services.notify.smtp import notify_backup_run

    run = _make_run("success")
    channel = _make_smtp_channel()

    with (
        patch("app.services.notify.smtp._send_sync", side_effect=RuntimeError("SMTP error")),
        pytest.raises(RuntimeError, match="SMTP error"),
    ):
        notify_backup_run(run, channel, "dest@example.com")


def test_send_test_email() -> None:
    from app.services.notify.smtp import send_test_email

    channel = _make_smtp_channel()
    with patch("app.services.notify.smtp._send_sync") as mock_send:
        send_test_email(channel)
        mock_send.assert_called_once()


def test_send_password_reset_email_no_config() -> None:
    from app.services.notify.smtp import send_password_reset_email

    user = MagicMock()
    user.recovery_channel_id = None
    user.recovery_email = None
    user.username = "admin"
    mock_db = MagicMock()

    send_password_reset_email(user, "token123", mock_db)
    mock_db.get.assert_not_called()


def test_send_password_reset_email_channel_not_found() -> None:
    from app.services.notify.smtp import send_password_reset_email

    user = MagicMock()
    user.recovery_channel_id = 99
    user.recovery_email = "admin@example.com"
    user.username = "admin"
    mock_db = MagicMock()
    mock_db.get.return_value = None

    send_password_reset_email(user, "token123", mock_db)
    # Should log warning and return without sending


def test_send_password_reset_email_success() -> None:
    from app.services.notify.smtp import send_password_reset_email

    user = MagicMock()
    user.recovery_channel_id = 1
    user.recovery_email = "admin@example.com"
    user.username = "admin"
    channel = _make_smtp_channel()
    mock_db = MagicMock()
    mock_db.get.return_value = channel

    with patch("app.services.notify.smtp._send_sync") as mock_send:
        send_password_reset_email(user, "token123", mock_db)
        mock_send.assert_called_once()


def test_send_async_uses_channel_config() -> None:
    from app.services.notify.smtp import _send_async

    channel = _make_smtp_channel()

    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        import asyncio

        asyncio.run(_send_async(channel, "to@example.com", "Subject", "<html>body</html>"))
        mock_send.assert_called_once()
        kwargs = mock_send.call_args[1]
        assert kwargs["hostname"] == "smtp.example.com"
        assert kwargs["port"] == 587


# ─── Telegram service ─────────────────────────────────────────────────────────


def test_format_backup_message_success() -> None:
    from app.services.notify.telegram import _format_backup_message

    run = _make_run("success")
    msg = _format_backup_message(run)
    assert "SUCCESS" in msg
    assert "testdb" in msg
    assert "✅" in msg


def test_format_backup_message_failed_with_error() -> None:
    from app.services.notify.telegram import _format_backup_message

    run = _make_run("failed", error_message="DB connection failed")
    msg = _format_backup_message(run)
    assert "❌" in msg
    assert "DB connection failed" in msg


def test_format_backup_message_no_instance() -> None:
    from app.services.notify.telegram import _format_backup_message

    run = _make_run("success")
    run.instance = None
    msg = _format_backup_message(run)
    assert msg is not None


def test_format_backup_message_no_file_size() -> None:
    from app.services.notify.telegram import _format_backup_message

    run = _make_run("success")
    run.file_size_bytes = None
    msg = _format_backup_message(run)
    assert "MB" not in msg


def test_format_backup_message_verification_not_run() -> None:
    from app.services.notify.telegram import _format_backup_message

    run = _make_run("success")
    run.verification_status = VerificationStatus.not_run
    msg = _format_backup_message(run)
    assert "Verification" not in msg


def test_notify_backup_run_telegram() -> None:
    from app.services.notify.telegram import notify_backup_run

    run = _make_run("success")
    channel = _make_telegram_channel()

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        notify_backup_run(run, channel)
        mock_client.post.assert_called_once()


def test_notify_backup_run_telegram_raises() -> None:
    from app.services.notify.telegram import notify_backup_run

    run = _make_run("success")
    channel = _make_telegram_channel()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = Exception("network error")
        mock_client_cls.return_value = mock_client

        with pytest.raises(Exception, match="network error"):
            notify_backup_run(run, channel)


def test_send_test_message_telegram() -> None:
    from app.services.notify.telegram import send_test_message

    channel = _make_telegram_channel()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        send_test_message(channel)
        mock_client.post.assert_called_once()


# ─── Dispatcher full SMTP delivery path ──────────────────────────────────────


def test_dispatcher_delivers_smtp_notification() -> None:
    from app.models.notify import ChannelType
    from app.services.notify.dispatcher import _deliver

    mock_db = MagicMock()
    run = MagicMock()
    run.id = 1
    run.status = BackupStatus.success

    binding = MagicMock()
    binding.channel_type = ChannelType.smtp
    binding.channel_id = 1

    smtp_channel = MagicMock()
    smtp_channel.enabled = True
    smtp_channel.from_address = "noreply@example.com"
    mock_db.get.return_value = smtp_channel

    with patch("app.services.notify.smtp.notify_backup_run") as mock_notify:
        _deliver(run, binding, mock_db)
        mock_notify.assert_called_once_with(run, smtp_channel, "noreply@example.com")
