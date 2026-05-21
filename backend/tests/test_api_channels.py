from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

_SMTP_PAYLOAD = {
    "name": "Test SMTP",
    "host": "smtp.example.com",
    "port": 587,
    "username": "user@example.com",
    "password": "secret123",
    "from_address": "noreply@example.com",
    "use_tls": True,
    "use_ssl": False,
    "enabled": True,
}

_TELEGRAM_PAYLOAD = {
    "name": "Test Telegram",
    "bot_token": "123456:ABC-token",
    "chat_id": "-100123456",
    "enabled": True,
}


# ─── SMTP ─────────────────────────────────────────────────────────────────────


def test_list_smtp_empty(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/channels/smtp")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_smtp(authed_client: TestClient) -> None:
    resp = authed_client.post("/api/channels/smtp", json=_SMTP_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test SMTP"
    assert data["host"] == "smtp.example.com"
    assert "password" not in data


def test_list_smtp_after_create(authed_client: TestClient) -> None:
    authed_client.post("/api/channels/smtp", json=_SMTP_PAYLOAD)
    resp = authed_client.get("/api/channels/smtp")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_smtp(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/smtp", json=_SMTP_PAYLOAD)
    channel_id = create_resp.json()["id"]
    resp = authed_client.get(f"/api/channels/smtp/{channel_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == channel_id


def test_get_smtp_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/channels/smtp/99999")
    assert resp.status_code == 404


def test_update_smtp(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/smtp", json=_SMTP_PAYLOAD)
    channel_id = create_resp.json()["id"]
    resp = authed_client.patch(
        f"/api/channels/smtp/{channel_id}",
        json={"name": "Updated SMTP", "enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated SMTP"
    assert data["enabled"] is False


def test_update_smtp_password(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/smtp", json=_SMTP_PAYLOAD)
    channel_id = create_resp.json()["id"]
    resp = authed_client.patch(
        f"/api/channels/smtp/{channel_id}",
        json={"password": "newpassword123"},
    )
    assert resp.status_code == 200


def test_update_smtp_not_found(authed_client: TestClient) -> None:
    resp = authed_client.patch("/api/channels/smtp/99999", json={"name": "Ghost"})
    assert resp.status_code == 404


def test_delete_smtp(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/smtp", json=_SMTP_PAYLOAD)
    channel_id = create_resp.json()["id"]
    resp = authed_client.delete(f"/api/channels/smtp/{channel_id}")
    assert resp.status_code == 204
    get_resp = authed_client.get(f"/api/channels/smtp/{channel_id}")
    assert get_resp.status_code == 404


def test_delete_smtp_not_found(authed_client: TestClient) -> None:
    resp = authed_client.delete("/api/channels/smtp/99999")
    assert resp.status_code == 404


def test_test_smtp_success(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/smtp", json=_SMTP_PAYLOAD)
    channel_id = create_resp.json()["id"]
    with patch("app.services.notify.smtp.send_test_email") as mock_send:
        mock_send.return_value = None
        resp = authed_client.post(f"/api/channels/smtp/{channel_id}/test")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Test email sent"


def test_test_smtp_failure(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/smtp", json=_SMTP_PAYLOAD)
    channel_id = create_resp.json()["id"]
    with patch(
        "app.services.notify.smtp.send_test_email", side_effect=Exception("Connection refused")
    ):
        resp = authed_client.post(f"/api/channels/smtp/{channel_id}/test")
    assert resp.status_code == 502
    assert "Connection refused" in resp.json()["detail"]


def test_test_smtp_not_found(authed_client: TestClient) -> None:
    resp = authed_client.post("/api/channels/smtp/99999/test")
    assert resp.status_code == 404


# ─── Telegram ─────────────────────────────────────────────────────────────────


def test_list_telegram_empty(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/channels/telegram")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_telegram(authed_client: TestClient) -> None:
    resp = authed_client.post("/api/channels/telegram", json=_TELEGRAM_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Telegram"
    assert data["chat_id"] == "-100123456"
    assert "bot_token" not in data


def test_list_telegram_after_create(authed_client: TestClient) -> None:
    authed_client.post("/api/channels/telegram", json=_TELEGRAM_PAYLOAD)
    resp = authed_client.get("/api/channels/telegram")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_telegram(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/telegram", json=_TELEGRAM_PAYLOAD)
    channel_id = create_resp.json()["id"]
    resp = authed_client.get(f"/api/channels/telegram/{channel_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == channel_id


def test_get_telegram_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/channels/telegram/99999")
    assert resp.status_code == 404


def test_update_telegram(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/telegram", json=_TELEGRAM_PAYLOAD)
    channel_id = create_resp.json()["id"]
    resp = authed_client.patch(
        f"/api/channels/telegram/{channel_id}",
        json={"name": "Updated Telegram", "enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Telegram"
    assert data["enabled"] is False


def test_update_telegram_token(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/telegram", json=_TELEGRAM_PAYLOAD)
    channel_id = create_resp.json()["id"]
    resp = authed_client.patch(
        f"/api/channels/telegram/{channel_id}",
        json={"bot_token": "new-token-999"},
    )
    assert resp.status_code == 200


def test_update_telegram_not_found(authed_client: TestClient) -> None:
    resp = authed_client.patch("/api/channels/telegram/99999", json={"name": "Ghost"})
    assert resp.status_code == 404


def test_delete_telegram(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/telegram", json=_TELEGRAM_PAYLOAD)
    channel_id = create_resp.json()["id"]
    resp = authed_client.delete(f"/api/channels/telegram/{channel_id}")
    assert resp.status_code == 204
    get_resp = authed_client.get(f"/api/channels/telegram/{channel_id}")
    assert get_resp.status_code == 404


def test_delete_telegram_not_found(authed_client: TestClient) -> None:
    resp = authed_client.delete("/api/channels/telegram/99999")
    assert resp.status_code == 404


def test_test_telegram_success(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/telegram", json=_TELEGRAM_PAYLOAD)
    channel_id = create_resp.json()["id"]
    with patch("app.services.notify.telegram.send_test_message") as mock_send:
        mock_send.return_value = None
        resp = authed_client.post(f"/api/channels/telegram/{channel_id}/test")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Test message sent"


def test_test_telegram_failure(authed_client: TestClient) -> None:
    create_resp = authed_client.post("/api/channels/telegram", json=_TELEGRAM_PAYLOAD)
    channel_id = create_resp.json()["id"]
    with patch(
        "app.services.notify.telegram.send_test_message", side_effect=Exception("Bot token invalid")
    ):
        resp = authed_client.post(f"/api/channels/telegram/{channel_id}/test")
    assert resp.status_code == 502
    assert "Bot token invalid" in resp.json()["detail"]


def test_test_telegram_not_found(authed_client: TestClient) -> None:
    resp = authed_client.post("/api/channels/telegram/99999/test")
    assert resp.status_code == 404
