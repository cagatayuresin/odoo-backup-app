from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_dispatch_notification_run_not_found() -> None:
    from app.tasks.notify_tasks import dispatch_notification

    mock_db = MagicMock()
    mock_db.__enter__ = lambda s: mock_db
    mock_db.__exit__ = MagicMock(return_value=False)
    mock_db.get.return_value = None

    with patch("app.tasks.notify_tasks.SessionLocal", return_value=mock_db):
        result = dispatch_notification(99999)

    assert result["status"] == "skipped"


def test_dispatch_notification_success() -> None:
    from app.models.backup import BackupRun
    from app.tasks.notify_tasks import dispatch_notification

    mock_run = MagicMock(spec=BackupRun)
    mock_run.id = 1

    mock_db = MagicMock()
    mock_db.__enter__ = lambda s: mock_db
    mock_db.__exit__ = MagicMock(return_value=False)
    mock_db.get.return_value = mock_run

    with (
        patch("app.tasks.notify_tasks.SessionLocal", return_value=mock_db),
        patch("app.services.notify.dispatcher.dispatch") as mock_dispatch,
    ):
        result = dispatch_notification(1)

    assert result["status"] == "dispatched"
    mock_dispatch.assert_called_once_with(mock_run, mock_db)


def test_dispatch_notification_error() -> None:
    from app.models.backup import BackupRun
    from app.tasks.notify_tasks import dispatch_notification

    mock_run = MagicMock(spec=BackupRun)
    mock_run.id = 1

    mock_db = MagicMock()
    mock_db.__enter__ = lambda s: mock_db
    mock_db.__exit__ = MagicMock(return_value=False)
    mock_db.get.return_value = mock_run

    with (
        patch("app.tasks.notify_tasks.SessionLocal", return_value=mock_db),
        patch(
            "app.services.notify.dispatcher.dispatch", side_effect=RuntimeError("dispatch failed")
        ),
    ):
        result = dispatch_notification(1)

    assert result["status"] == "error"
