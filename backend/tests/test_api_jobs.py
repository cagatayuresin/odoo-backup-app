from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _create_instance(client: TestClient) -> dict:
    resp = client.post(
        "/api/instances/",
        json={
            "name": "Job Test Instance",
            "raw_url": "https://jobs.example.com",
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


def test_list_jobs_empty(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.get(f"/api/instances/{inst['id']}/jobs/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_jobs_instance_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/instances/99999/jobs/")
    assert resp.status_code == 404


def test_create_job(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.post(
        f"/api/instances/{inst['id']}/jobs/",
        json={"name": "Daily Backup", "cron_expression": "0 2 * * *", "enabled": True},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Daily Backup"
    assert data["instance_id"] == inst["id"]
    assert data["enabled"] is True


def test_create_job_invalid_cron(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.post(
        f"/api/instances/{inst['id']}/jobs/",
        json={"name": "Bad Job", "cron_expression": "not-a-cron", "enabled": True},
    )
    assert resp.status_code == 422


def test_create_job_instance_not_found(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/api/instances/99999/jobs/",
        json={"name": "Ghost Job", "cron_expression": "0 2 * * *", "enabled": True},
    )
    assert resp.status_code == 404


def test_get_job(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    create_resp = authed_client.post(
        f"/api/instances/{inst['id']}/jobs/",
        json={"name": "Get Test", "cron_expression": "0 3 * * *"},
    )
    job_id = create_resp.json()["id"]
    resp = authed_client.get(f"/api/instances/{inst['id']}/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


def test_get_job_not_found(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.get(f"/api/instances/{inst['id']}/jobs/99999")
    assert resp.status_code == 404


def test_get_job_wrong_instance(authed_client: TestClient) -> None:
    inst1 = _create_instance(authed_client)
    inst2_resp = authed_client.post(
        "/api/instances/",
        json={
            "name": "Other Instance",
            "raw_url": "https://other.example.com",
            "backup_method": "odoo_endpoint",
            "db_selection_mode": "single",
            "db_names": ["otherdb"],
            "retention_mode": "keep_last_n",
            "retention_value": 7,
            "notifications_enabled": True,
        },
    )
    inst2 = inst2_resp.json()
    create_resp = authed_client.post(
        f"/api/instances/{inst1['id']}/jobs/",
        json={"name": "Job on inst1", "cron_expression": "0 4 * * *"},
    )
    job_id = create_resp.json()["id"]
    resp = authed_client.get(f"/api/instances/{inst2['id']}/jobs/{job_id}")
    assert resp.status_code == 404


def test_update_job(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    create_resp = authed_client.post(
        f"/api/instances/{inst['id']}/jobs/",
        json={"name": "Old Name", "cron_expression": "0 2 * * *"},
    )
    job_id = create_resp.json()["id"]
    resp = authed_client.patch(
        f"/api/instances/{inst['id']}/jobs/{job_id}",
        json={"name": "New Name", "enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["enabled"] is False


def test_update_job_cron_expression(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    create_resp = authed_client.post(
        f"/api/instances/{inst['id']}/jobs/",
        json={"name": "Cron Update", "cron_expression": "0 2 * * *"},
    )
    job_id = create_resp.json()["id"]
    resp = authed_client.patch(
        f"/api/instances/{inst['id']}/jobs/{job_id}",
        json={"cron_expression": "0 5 * * 1"},
    )
    assert resp.status_code == 200
    assert resp.json()["cron_expression"] == "0 5 * * 1"


def test_update_job_not_found(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.patch(
        f"/api/instances/{inst['id']}/jobs/99999",
        json={"name": "Ghost"},
    )
    assert resp.status_code == 404


def test_delete_job(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    create_resp = authed_client.post(
        f"/api/instances/{inst['id']}/jobs/",
        json={"name": "Delete Me", "cron_expression": "0 6 * * *"},
    )
    job_id = create_resp.json()["id"]
    resp = authed_client.delete(f"/api/instances/{inst['id']}/jobs/{job_id}")
    assert resp.status_code == 204
    get_resp = authed_client.get(f"/api/instances/{inst['id']}/jobs/{job_id}")
    assert get_resp.status_code == 404


def test_delete_job_not_found(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.delete(f"/api/instances/{inst['id']}/jobs/99999")
    assert resp.status_code == 404


def test_run_job_now(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    create_resp = authed_client.post(
        f"/api/instances/{inst['id']}/jobs/",
        json={"name": "Run Now", "cron_expression": "0 7 * * *"},
    )
    job_id = create_resp.json()["id"]
    mock_task = MagicMock()
    mock_task.id = "test-task-id-123"
    with patch("app.tasks.backup_tasks.run_backup_job") as mock_rj:
        mock_rj.delay.return_value = mock_task
        resp = authed_client.post(f"/api/instances/{inst['id']}/jobs/{job_id}/run")
    assert resp.status_code == 202
    data = resp.json()
    assert data["task_id"] == "test-task-id-123"
    assert "enqueued" in data["detail"].lower()


def test_run_job_now_not_found(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.post(f"/api/instances/{inst['id']}/jobs/99999/run")
    assert resp.status_code == 404
