from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch


def _make_run(status: str = "success") -> MagicMock:
    run = MagicMock()
    from app.models.backup import BackupStatus, VerificationStatus

    run.id = 42
    run.instance_id = 1
    run.db_name = "testdb"
    run.started_at = datetime(2026, 5, 21, 10, 0, 0, tzinfo=UTC)
    run.finished_at = datetime(2026, 5, 21, 10, 2, 0, tzinfo=UTC)
    run.status = BackupStatus(status)
    run.verification_status = VerificationStatus.passed
    run.file_size_bytes = 512 * 1024
    run.error_message = None
    run.instance = MagicMock()
    run.instance.name = "Dispatcher Test Instance"
    run.instance.notifications_enabled = True
    return run


def test_dispatch_no_instance() -> None:
    from app.services.notify.dispatcher import dispatch

    mock_db = MagicMock()
    run = _make_run("success")
    run.instance = None

    with patch("app.services.notify.dispatcher._deliver") as mock_deliver:
        dispatch(run, mock_db)
        mock_deliver.assert_not_called()


def test_dispatch_running_status_skipped() -> None:
    from app.services.notify.dispatcher import dispatch

    mock_db = MagicMock()
    run = _make_run("running")
    mock_db.query.return_value.filter.return_value.all.return_value = []

    with patch("app.services.notify.dispatcher._deliver") as mock_deliver:
        dispatch(run, mock_db)
        mock_deliver.assert_not_called()


def test_dispatch_verified_status_triggers() -> None:
    from app.models.notify import ChannelType
    from app.services.notify.dispatcher import dispatch

    mock_db = MagicMock()
    run = _make_run("verified")

    binding = MagicMock()
    binding.id = 1
    binding.channel_type = ChannelType.smtp
    binding.channel_id = 1
    binding.on_success = True
    binding.on_failure = False

    mock_db.query.return_value.filter.return_value.all.return_value = [binding]

    with patch("app.services.notify.dispatcher._deliver") as mock_deliver:
        dispatch(run, mock_db)
        mock_deliver.assert_called_once()


def test_dispatch_verify_failed_triggers_failure_binding() -> None:
    from app.models.notify import ChannelType
    from app.services.notify.dispatcher import dispatch

    mock_db = MagicMock()
    run = _make_run("verify_failed")

    binding = MagicMock()
    binding.id = 1
    binding.channel_type = ChannelType.smtp
    binding.channel_id = 1
    binding.on_success = False
    binding.on_failure = True

    mock_db.query.return_value.filter.return_value.all.return_value = [binding]

    with patch("app.services.notify.dispatcher._deliver") as mock_deliver:
        dispatch(run, mock_db)
        mock_deliver.assert_called_once()


def test_deliver_telegram_success() -> None:
    from app.models.notify import ChannelType
    from app.services.notify.dispatcher import _deliver

    mock_db = MagicMock()
    run = _make_run("success")

    binding = MagicMock()
    binding.channel_type = ChannelType.telegram
    binding.channel_id = 5

    tg_channel = MagicMock()
    tg_channel.enabled = True
    mock_db.get.return_value = tg_channel

    with patch("app.services.notify.telegram.notify_backup_run") as mock_notify:
        _deliver(run, binding, mock_db)
        mock_notify.assert_called_once_with(run, tg_channel)


def test_deliver_telegram_channel_not_found() -> None:
    from app.models.notify import ChannelType
    from app.services.notify.dispatcher import _deliver

    mock_db = MagicMock()
    run = _make_run("success")

    binding = MagicMock()
    binding.channel_type = ChannelType.telegram
    binding.channel_id = 999

    mock_db.get.return_value = None

    with patch("app.services.notify.telegram.notify_backup_run") as mock_notify:
        _deliver(run, binding, mock_db)
        mock_notify.assert_not_called()


def test_deliver_telegram_channel_disabled() -> None:
    from app.models.notify import ChannelType
    from app.services.notify.dispatcher import _deliver

    mock_db = MagicMock()
    run = _make_run("success")

    binding = MagicMock()
    binding.channel_type = ChannelType.telegram
    binding.channel_id = 5

    tg_channel = MagicMock()
    tg_channel.enabled = False
    mock_db.get.return_value = tg_channel

    with patch("app.services.notify.telegram.notify_backup_run") as mock_notify:
        _deliver(run, binding, mock_db)
        mock_notify.assert_not_called()


def test_deliver_smtp_channel_not_found() -> None:
    from app.models.notify import ChannelType
    from app.services.notify.dispatcher import _deliver

    mock_db = MagicMock()
    run = _make_run("success")

    binding = MagicMock()
    binding.channel_type = ChannelType.smtp
    binding.channel_id = 999

    mock_db.get.return_value = None

    with patch("app.services.notify.smtp.notify_backup_run") as mock_notify:
        _deliver(run, binding, mock_db)
        mock_notify.assert_not_called()


def test_deliver_smtp_channel_disabled() -> None:
    from app.models.notify import ChannelType
    from app.services.notify.dispatcher import _deliver

    mock_db = MagicMock()
    run = _make_run("success")

    binding = MagicMock()
    binding.channel_type = ChannelType.smtp
    binding.channel_id = 1

    smtp_channel = MagicMock()
    smtp_channel.enabled = False
    mock_db.get.return_value = smtp_channel

    with patch("app.services.notify.smtp.notify_backup_run") as mock_notify:
        _deliver(run, binding, mock_db)
        mock_notify.assert_not_called()


def test_dispatch_delivery_exception_logged() -> None:
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

    with patch("app.services.notify.dispatcher._deliver", side_effect=RuntimeError("send failed")):
        dispatch(run, mock_db)
