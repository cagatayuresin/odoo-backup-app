from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.security import encrypt_secret
from app.models.backup import BackupRun
from app.models.cloud import CloudAccount, CloudProvider, InstanceCloudBinding


def _make_account(provider: str = "gdrive") -> CloudAccount:
    account = CloudAccount(
        id=1,
        provider=CloudProvider(provider),
        name=f"Test {provider}",
        credentials_enc=encrypt_secret(json.dumps({"token": "abc"})),
        enabled=True,
    )
    return account


def _make_binding(
    account_id: int = 1, remote_folder: str = "/backups", apply_retention: bool = False
) -> InstanceCloudBinding:
    binding = InstanceCloudBinding(
        id=1,
        instance_id=1,
        cloud_account_id=account_id,
        remote_folder=remote_folder,
        enabled=True,
        apply_retention_remotely=apply_retention,
    )
    return binding


def _make_run(file_path: str | None = None) -> MagicMock:
    run = MagicMock(spec=BackupRun)
    run.id = 1
    run.instance_id = 1
    run.file_path = file_path
    run.cloud_sync_status = None
    run.instance = MagicMock()
    run.instance.slug = "test"
    run.instance.retention_mode = MagicMock()
    run.instance.retention_mode.value = "keep_last_n"
    run.instance.retention_value = 3
    return run


def test_sync_run_no_file() -> None:
    from app.services.cloud.sync import sync_run

    run = _make_run(file_path=None)
    mock_db = MagicMock()

    sync_run(run, mock_db)
    mock_db.query.assert_not_called()


def test_sync_run_file_missing_on_disk(tmp_path: Path) -> None:
    from app.services.cloud.sync import sync_run

    run = _make_run(file_path="/nonexistent/backup.dump")
    mock_db = MagicMock()

    sync_run(run, mock_db)
    mock_db.query.assert_not_called()


def test_sync_run_no_bindings(tmp_path: Path) -> None:
    from app.services.cloud.sync import sync_run

    f = tmp_path / "backup.dump"
    f.write_bytes(b"data")
    run = _make_run(file_path=str(f))
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    sync_run(run, mock_db)
    mock_db.commit.assert_called_once()


def test_sync_run_account_not_found(tmp_path: Path) -> None:
    from app.services.cloud.sync import sync_run

    f = tmp_path / "backup.dump"
    f.write_bytes(b"data")
    run = _make_run(file_path=str(f))

    binding = _make_binding()
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [binding]
    mock_db.get.return_value = None

    sync_run(run, mock_db)
    mock_db.commit.assert_called_once()


def test_sync_run_account_disabled(tmp_path: Path) -> None:
    from app.services.cloud.sync import sync_run

    f = tmp_path / "backup.dump"
    f.write_bytes(b"data")
    run = _make_run(file_path=str(f))

    binding = _make_binding()
    account = _make_account()
    account.enabled = False
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [binding]
    mock_db.get.return_value = account

    sync_run(run, mock_db)
    mock_db.commit.assert_called_once()


def test_sync_run_upload_success(tmp_path: Path) -> None:
    from app.services.cloud.sync import sync_run

    f = tmp_path / "backup.dump"
    f.write_bytes(b"data")
    run = _make_run(file_path=str(f))

    binding = _make_binding()
    account = _make_account("gdrive")
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [binding]
    mock_db.get.return_value = account

    mock_provider = MagicMock()
    mock_provider.upload.return_value = "remote-file-id"

    with patch("app.services.cloud.sync._build_provider", return_value=mock_provider):
        sync_run(run, mock_db)

    mock_provider.upload.assert_called_once()
    assert json.loads(run.cloud_sync_status)["gdrive"] == "uploaded"


def test_sync_run_upload_failure(tmp_path: Path) -> None:
    from app.services.cloud.sync import sync_run

    f = tmp_path / "backup.dump"
    f.write_bytes(b"data")
    run = _make_run(file_path=str(f))

    binding = _make_binding()
    account = _make_account("dropbox")
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [binding]
    mock_db.get.return_value = account

    with patch(
        "app.services.cloud.sync._build_provider", side_effect=RuntimeError("upload failed")
    ):
        sync_run(run, mock_db)

    assert json.loads(run.cloud_sync_status)["dropbox"] == "failed"


def test_sync_run_with_retention(tmp_path: Path) -> None:
    from app.services.cloud.sync import sync_run

    f = tmp_path / "backup.dump"
    f.write_bytes(b"data")
    run = _make_run(file_path=str(f))

    binding = _make_binding(apply_retention=True)
    account = _make_account("gdrive")
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [binding]
    mock_db.get.return_value = account

    mock_provider = MagicMock()
    mock_provider.upload.return_value = "remote-id"
    mock_provider.list_files.return_value = []

    with patch("app.services.cloud.sync._build_provider", return_value=mock_provider):
        sync_run(run, mock_db)

    mock_provider.list_files.assert_called_once()


def test_build_provider_gdrive() -> None:
    from app.services.cloud.sync import _build_provider

    account = _make_account("gdrive")
    with patch("app.services.cloud.drive.build_provider", return_value=MagicMock()) as mock_build:
        _build_provider(account)
        mock_build.assert_called_once()


def test_build_provider_dropbox() -> None:
    from app.services.cloud.sync import _build_provider

    account = _make_account("dropbox")
    with patch(
        "app.services.cloud.dropbox_provider.build_provider", return_value=MagicMock()
    ) as mock_build:
        _build_provider(account)
        mock_build.assert_called_once()


def test_build_provider_onedrive() -> None:
    from app.services.cloud.sync import _build_provider

    account = _make_account("onedrive")
    with patch(
        "app.services.cloud.onedrive.build_provider", return_value=MagicMock()
    ) as mock_build:
        _build_provider(account)
        mock_build.assert_called_once()


def test_apply_remote_retention_with_deletions(tmp_path: Path) -> None:
    from app.services.cloud.base import RemoteFile
    from app.services.cloud.sync import _apply_remote_retention

    f = tmp_path / "backup.dump"
    f.write_bytes(b"data")
    run = _make_run(file_path=str(f))

    binding = _make_binding(apply_retention=True)
    mock_db = MagicMock()

    remote_files = [
        RemoteFile(
            remote_id=f"id{i}",
            name=f"file{i}.dump",
            size_bytes=100,
            modified_at=datetime(2026, 1, i + 1, tzinfo=UTC),
        )
        for i in range(5)
    ]

    mock_provider = MagicMock()
    mock_provider.list_files.return_value = remote_files

    _apply_remote_retention(run, binding, mock_provider, mock_db)
    mock_provider.list_files.assert_called_once_with("/backups")


def test_apply_remote_retention_no_instance() -> None:
    from app.services.cloud.sync import _apply_remote_retention

    run = MagicMock()
    run.instance = None
    binding = _make_binding()
    mock_provider = MagicMock()
    mock_db = MagicMock()

    _apply_remote_retention(run, binding, mock_provider, mock_db)
    mock_provider.list_files.assert_not_called()
