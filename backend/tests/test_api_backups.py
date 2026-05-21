from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.backup import BackupRun, BackupStatus


def _create_instance(client: TestClient) -> dict:
    resp = client.post(
        "/api/instances/",
        json={
            "name": "Backup Test Instance",
            "raw_url": "https://backup.example.com",
            "backup_method": "odoo_endpoint",
            "db_selection_mode": "single",
            "db_names": ["testdb"],
            "retention_mode": "keep_last_n",
            "retention_value": 7,
            "notifications_enabled": True,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _add_backup_run(
    db: Session,
    instance_id: int,
    status: BackupStatus = BackupStatus.success,
    file_path: str | None = None,
) -> BackupRun:
    run = BackupRun(
        instance_id=instance_id,
        status=status,
        db_name="testdb",
        file_path=file_path,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def test_list_backups_empty(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/backups/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_backups_with_instance_filter(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    _add_backup_run(db, inst["id"])
    resp = authed_client.get(f"/api/backups/?instance_id={inst['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_backups_no_filter(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    _add_backup_run(db, inst["id"])
    _add_backup_run(db, inst["id"], BackupStatus.failed)
    resp = authed_client.get("/api/backups/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_list_backups_pagination(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    for _ in range(3):
        _add_backup_run(db, inst["id"])
    resp = authed_client.get(f"/api/backups/?instance_id={inst['id']}&limit=2&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_backup(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run = _add_backup_run(db, inst["id"])
    resp = authed_client.get(f"/api/backups/{run.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run.id


def test_get_backup_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/backups/99999")
    assert resp.status_code == 404


def test_download_backup_no_file(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run = _add_backup_run(db, inst["id"], file_path=None)
    resp = authed_client.get(f"/api/backups/{run.id}/download")
    assert resp.status_code == 404


def test_download_backup_file_missing_on_disk(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run = _add_backup_run(db, inst["id"], file_path="/nonexistent/path/backup.dump")
    resp = authed_client.get(f"/api/backups/{run.id}/download")
    assert resp.status_code == 404


def test_download_backup_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/backups/99999/download")
    assert resp.status_code == 404


def test_download_backup_success(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as f:
        f.write(b"fake backup data")
        tmp_path = f.name
    try:
        run = _add_backup_run(db, inst["id"], file_path=tmp_path)
        resp = authed_client.get(f"/api/backups/{run.id}/download")
        assert resp.status_code == 200
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_delete_backup_not_found(authed_client: TestClient) -> None:
    resp = authed_client.delete("/api/backups/99999")
    assert resp.status_code == 404


def test_delete_backup_last_successful_blocked(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run = _add_backup_run(db, inst["id"], status=BackupStatus.success)
    resp = authed_client.delete(f"/api/backups/{run.id}")
    assert resp.status_code == 409


def test_delete_backup_force_without_confirmation(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run = _add_backup_run(db, inst["id"], status=BackupStatus.success)
    resp = authed_client.delete(f"/api/backups/{run.id}?force=true&confirmation=WRONG")
    assert resp.status_code == 400


def test_delete_backup_force_with_confirmation(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run = _add_backup_run(db, inst["id"], status=BackupStatus.success)
    resp = authed_client.delete(f"/api/backups/{run.id}?force=true&confirmation=DELETE")
    assert resp.status_code == 204


def test_delete_backup_non_last_success(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run1 = _add_backup_run(db, inst["id"], status=BackupStatus.success)
    _add_backup_run(db, inst["id"], status=BackupStatus.success)
    resp = authed_client.delete(f"/api/backups/{run1.id}")
    assert resp.status_code == 204


def test_delete_backup_failed_run(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run = _add_backup_run(db, inst["id"], status=BackupStatus.failed)
    resp = authed_client.delete(f"/api/backups/{run.id}")
    assert resp.status_code == 204


def test_delete_backup_with_file_on_disk(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as f:
        f.write(b"data")
        tmp_path = f.name
    _add_backup_run(db, inst["id"], status=BackupStatus.success)
    run2 = _add_backup_run(db, inst["id"], status=BackupStatus.success, file_path=tmp_path)
    resp = authed_client.delete(f"/api/backups/{run2.id}")
    assert resp.status_code == 204
    assert not Path(tmp_path).exists()


def test_re_verify_backup_not_found(authed_client: TestClient) -> None:
    resp = authed_client.post("/api/backups/99999/verify")
    assert resp.status_code == 404


def test_re_verify_backup_no_file(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run = _add_backup_run(db, inst["id"], file_path=None)
    resp = authed_client.post(f"/api/backups/{run.id}/verify")
    assert resp.status_code == 404


def test_re_verify_backup_file_missing(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run = _add_backup_run(db, inst["id"], file_path="/nonexistent/backup.dump")
    resp = authed_client.post(f"/api/backups/{run.id}/verify")
    assert resp.status_code == 404


def test_re_verify_backup_success(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as f:
        f.write(b"data")
        tmp_path = f.name
    try:
        run = _add_backup_run(db, inst["id"], file_path=tmp_path)
        mock_task = MagicMock()
        mock_task.id = "verify-task-id"
        with patch("app.tasks.backup_tasks.verify_backup_run") as mock_vr:
            mock_vr.delay.return_value = mock_task
            resp = authed_client.post(f"/api/backups/{run.id}/verify")
        assert resp.status_code == 202
        assert resp.json()["task_id"] == "verify-task-id"
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_re_upload_backup_not_found(authed_client: TestClient) -> None:
    resp = authed_client.post("/api/backups/99999/reupload")
    assert resp.status_code == 404


def test_re_upload_backup_no_file(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    run = _add_backup_run(db, inst["id"], file_path=None)
    resp = authed_client.post(f"/api/backups/{run.id}/reupload")
    assert resp.status_code == 404


def test_re_upload_backup_success(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as f:
        f.write(b"data")
        tmp_path = f.name
    try:
        run = _add_backup_run(db, inst["id"], file_path=tmp_path)
        mock_task = MagicMock()
        mock_task.id = "reupload-task-id"
        with patch("app.tasks.cloud_tasks.sync_backup_to_cloud") as mock_ct:
            mock_ct.delay.return_value = mock_task
            resp = authed_client.post(f"/api/backups/{run.id}/reupload")
        assert resp.status_code == 202
        assert resp.json()["task_id"] == "reupload-task-id"
    finally:
        Path(tmp_path).unlink(missing_ok=True)
