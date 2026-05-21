from __future__ import annotations

from fastapi.testclient import TestClient

_ACCOUNT_PAYLOAD = {
    "provider": "gdrive",
    "name": "My Google Drive",
    "credentials": {"access_token": "tok123", "refresh_token": "ref456"},
    "enabled": True,
}


def _create_instance(client: TestClient) -> dict:
    resp = client.post(
        "/api/instances/",
        json={
            "name": "Cloud Test Instance",
            "raw_url": "https://cloud.example.com",
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


# ─── Cloud Accounts ───────────────────────────────────────────────────────────


def test_list_accounts_empty(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/cloud/accounts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_account(authed_client: TestClient) -> None:
    resp = authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Google Drive"
    assert data["provider"] == "gdrive"
    assert "credentials" not in data


def test_list_accounts_after_create(authed_client: TestClient) -> None:
    authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    resp = authed_client.get("/api/cloud/accounts")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_account(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    account_id = create_resp.json()["id"]
    resp = authed_client.get(f"/api/cloud/accounts/{account_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == account_id


def test_get_account_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/cloud/accounts/99999")
    assert resp.status_code == 404


def test_update_account(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    account_id = create_resp.json()["id"]
    resp = authed_client.patch(
        f"/api/cloud/accounts/{account_id}",
        json={"name": "Updated Drive", "enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Drive"
    assert data["enabled"] is False


def test_update_account_credentials(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    account_id = create_resp.json()["id"]
    resp = authed_client.patch(
        f"/api/cloud/accounts/{account_id}",
        json={"credentials": {"access_token": "new-token"}},
    )
    assert resp.status_code == 200


def test_update_account_not_found(authed_client: TestClient) -> None:
    resp = authed_client.patch("/api/cloud/accounts/99999", json={"name": "Ghost"})
    assert resp.status_code == 404


def test_delete_account(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    account_id = create_resp.json()["id"]
    resp = authed_client.delete(f"/api/cloud/accounts/{account_id}")
    assert resp.status_code == 204
    get_resp = authed_client.get(f"/api/cloud/accounts/{account_id}")
    assert get_resp.status_code == 404


def test_delete_account_not_found(authed_client: TestClient) -> None:
    resp = authed_client.delete("/api/cloud/accounts/99999")
    assert resp.status_code == 404


# ─── Instance Cloud Bindings ──────────────────────────────────────────────────


def test_list_bindings_empty(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.get(f"/api/cloud/instances/{inst['id']}/bindings")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_bindings_instance_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/cloud/instances/99999/bindings")
    assert resp.status_code == 404


def test_create_binding(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    acc_resp = authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    account_id = acc_resp.json()["id"]
    resp = authed_client.post(
        f"/api/cloud/instances/{inst['id']}/bindings",
        json={"cloud_account_id": account_id, "remote_folder": "/backups", "enabled": True},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["instance_id"] == inst["id"]
    assert data["cloud_account_id"] == account_id
    assert data["remote_folder"] == "/backups"


def test_create_binding_instance_not_found(authed_client: TestClient) -> None:
    acc_resp = authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    account_id = acc_resp.json()["id"]
    resp = authed_client.post(
        "/api/cloud/instances/99999/bindings",
        json={"cloud_account_id": account_id},
    )
    assert resp.status_code == 404


def test_update_binding(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    acc_resp = authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    account_id = acc_resp.json()["id"]
    create_resp = authed_client.post(
        f"/api/cloud/instances/{inst['id']}/bindings",
        json={"cloud_account_id": account_id},
    )
    binding_id = create_resp.json()["id"]
    resp = authed_client.patch(
        f"/api/cloud/instances/{inst['id']}/bindings/{binding_id}",
        json={"enabled": False, "remote_folder": "/new-path"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["remote_folder"] == "/new-path"


def test_update_binding_not_found(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.patch(
        f"/api/cloud/instances/{inst['id']}/bindings/99999",
        json={"enabled": False},
    )
    assert resp.status_code == 404


def test_delete_binding(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    acc_resp = authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    account_id = acc_resp.json()["id"]
    create_resp = authed_client.post(
        f"/api/cloud/instances/{inst['id']}/bindings",
        json={"cloud_account_id": account_id},
    )
    binding_id = create_resp.json()["id"]
    resp = authed_client.delete(f"/api/cloud/instances/{inst['id']}/bindings/{binding_id}")
    assert resp.status_code == 204


def test_delete_binding_not_found(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.delete(f"/api/cloud/instances/{inst['id']}/bindings/99999")
    assert resp.status_code == 404


def test_delete_binding_wrong_instance(authed_client: TestClient) -> None:
    inst1 = _create_instance(authed_client)
    inst2_resp = authed_client.post(
        "/api/instances/",
        json={
            "name": "Other Cloud Instance",
            "raw_url": "https://cloud2.example.com",
            "backup_method": "odoo_endpoint",
            "db_selection_mode": "single",
            "db_names": ["db2"],
            "retention_mode": "keep_last_n",
            "retention_value": 7,
            "notifications_enabled": True,
        },
    )
    inst2 = inst2_resp.json()
    acc_resp = authed_client.post("/api/cloud/accounts", json=_ACCOUNT_PAYLOAD)
    account_id = acc_resp.json()["id"]
    create_resp = authed_client.post(
        f"/api/cloud/instances/{inst1['id']}/bindings",
        json={"cloud_account_id": account_id},
    )
    binding_id = create_resp.json()["id"]
    resp = authed_client.delete(f"/api/cloud/instances/{inst2['id']}/bindings/{binding_id}")
    assert resp.status_code == 404
