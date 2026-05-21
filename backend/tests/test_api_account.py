from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_me(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/account/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["must_change_password"] is False


def test_update_me_timezone(authed_client: TestClient) -> None:
    resp = authed_client.patch("/api/account/me", json={"timezone": "Europe/Istanbul"})
    assert resp.status_code == 200
    assert resp.json()["timezone"] == "Europe/Istanbul"


def test_update_me_invalid_timezone(authed_client: TestClient) -> None:
    resp = authed_client.patch("/api/account/me", json={"timezone": "Invalid/Zone"})
    assert resp.status_code == 422


def test_update_me_recovery_email(authed_client: TestClient) -> None:
    resp = authed_client.patch("/api/account/me", json={"recovery_email": "admin@example.com"})
    assert resp.status_code == 200
    assert resp.json()["recovery_email"] == "admin@example.com"


def test_change_password_success(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/api/account/change-password",
        json={"current_password": "TestPass123", "new_password": "NewPass456!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"


def test_change_password_wrong_current(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/api/account/change-password",
        json={"current_password": "WrongPassword", "new_password": "NewPass456!"},
    )
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()


def test_change_password_too_short(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/api/account/change-password",
        json={"current_password": "TestPass123", "new_password": "short"},
    )
    assert resp.status_code == 422


def test_get_me_unauthenticated(client: TestClient) -> None:
    resp = client.get("/api/account/me")
    assert resp.status_code in (401, 403)
