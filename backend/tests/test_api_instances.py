"""Integration tests for the instances API."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_and_list_instance(authed_client: TestClient) -> None:
    """Creating an instance should make it appear in the list."""
    payload = {
        "name": "My Odoo",
        "raw_url": "https://erp.mycompany.com",
        "backup_method": "odoo_endpoint",
        "master_password": "secret",
        "db_selection_mode": "single",
        "db_names": ["mydb"],
        "retention_mode": "keep_last_n",
        "retention_value": 7,
        "notifications_enabled": True,
    }
    resp = authed_client.post("/api/instances/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "my-odoo"
    assert data["parsed_host"] == "erp.mycompany.com"
    assert data["parsed_port"] == 443

    list_resp = authed_client.get("/api/instances/")
    assert list_resp.status_code == 200
    assert any(i["slug"] == "my-odoo" for i in list_resp.json())


def test_create_instance_invalid_url(authed_client: TestClient) -> None:
    """An invalid URL should return 422."""
    payload = {
        "name": "Bad Instance",
        "raw_url": "not a url !!",
        "backup_method": "odoo_endpoint",
        "db_selection_mode": "single",
        "db_names": ["mydb"],
        "retention_mode": "keep_last_n",
        "retention_value": 7,
        "notifications_enabled": True,
    }
    resp = authed_client.post("/api/instances/", json=payload)
    assert resp.status_code == 422


def test_get_nonexistent_instance_returns_404(authed_client: TestClient) -> None:
    """Fetching a non-existent instance ID returns 404."""
    resp = authed_client.get("/api/instances/99999")
    assert resp.status_code == 404


def test_update_instance(authed_client: TestClient) -> None:
    """PATCH should update only the specified fields."""
    create_resp = authed_client.post(
        "/api/instances/",
        json={
            "name": "Update Test",
            "raw_url": "https://test.example.com",
            "backup_method": "odoo_endpoint",
            "db_selection_mode": "single",
            "db_names": ["testdb"],
            "retention_mode": "keep_last_n",
            "retention_value": 5,
            "notifications_enabled": True,
        },
    )
    inst_id = create_resp.json()["id"]

    patch_resp = authed_client.patch(
        f"/api/instances/{inst_id}",
        json={"retention_value": 14},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["retention_value"] == 14


def test_delete_instance(authed_client: TestClient) -> None:
    """DELETE should remove the instance."""
    create_resp = authed_client.post(
        "/api/instances/",
        json={
            "name": "To Delete",
            "raw_url": "https://delete.example.com",
            "backup_method": "odoo_endpoint",
            "db_selection_mode": "single",
            "db_names": ["deldb"],
            "retention_mode": "keep_last_n",
            "retention_value": 3,
            "notifications_enabled": False,
        },
    )
    inst_id = create_resp.json()["id"]

    del_resp = authed_client.delete(f"/api/instances/{inst_id}")
    assert del_resp.status_code == 204

    get_resp = authed_client.get(f"/api/instances/{inst_id}")
    assert get_resp.status_code == 404
