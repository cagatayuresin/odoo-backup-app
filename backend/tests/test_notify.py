"""Tests for notification dispatcher — mocked SMTP and Telegram."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


def _make_run(status: str = "success") -> MagicMock:
    """Create a mock BackupRun."""
    run = MagicMock()
    from app.models.backup import BackupStatus, VerificationStatus

    run.id = 1
    run.instance_id = 1
    run.db_name = "mydb"
    run.started_at = datetime(2026, 5, 21, 10, 0, 0, tzinfo=timezone.utc)
    run.finished_at = datetime(2026, 5, 21, 10, 1, 30, tzinfo=timezone.utc)
    run.status = BackupStatus(status)
    run.verification_status = VerificationStatus.passed
    run.file_size_bytes = 1024 * 1024
    run.error_message = None

    run.instance = MagicMock()
    run.instance.name = "My Odoo Instance"
    run.instance.notifications_enabled = True

    return run


def test_dispatcher_success_triggers_success_channel() -> None:
    """on_success=True binding receives dispatch on successful run."""
    from app.models.notify import ChannelType
    from app.services.notify.dispatcher import dispatch

    mock_db = MagicMock()
    run = _make_run("success")

    binding = MagicMock()
    binding.id = 1
    binding.channel_type = ChannelType.smtp
    binding.channel_id = 1
    binding.on_success = True
    binding.on_failure = False

    mock_db.query.return_value.filter.return_value.all.return_value = [binding]

    smtp_channel = MagicMock()
    smtp_channel.enabled = True
    smtp_channel.from_address = "backup@example.com"
    mock_db.get.return_value = smtp_channel

    with patch("app.services.notify.dispatcher._deliver") as mock_deliver:
        dispatch(run, mock_db)
        mock_deliver.assert_called_once()


def test_dispatcher_failure_skips_success_only_channel() -> None:
    """on_failure=False binding should not receive dispatch for a failed run."""
    from app.models.notify import ChannelType
    from app.services.notify.dispatcher import dispatch

    mock_db = MagicMock()
    run = _make_run("failed")

    binding = MagicMock()
    binding.channel_type = ChannelType.smtp
    binding.channel_id = 1
    binding.on_success = True
    binding.on_failure = False

    mock_db.query.return_value.filter.return_value.all.return_value = [binding]

    with patch("app.services.notify.dispatcher._deliver") as mock_deliver:
        dispatch(run, mock_db)
        mock_deliver.assert_not_called()


def test_dispatcher_notifications_disabled() -> None:
    """When notifications_enabled=False, dispatch should do nothing."""
    from app.services.notify.dispatcher import dispatch

    mock_db = MagicMock()
    run = _make_run("success")
    run.instance.notifications_enabled = False

    with patch("app.services.notify.dispatcher._deliver") as mock_deliver:
        dispatch(run, mock_db)
        mock_deliver.assert_not_called()
