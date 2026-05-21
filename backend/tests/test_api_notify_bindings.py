from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import encrypt_secret
from app.models.notify import SmtpChannel, TelegramChannel


def _create_instance(
    client: TestClient, name: str = "Notify Test Instance", url: str = "https://notify.example.com"
) -> dict:
    resp = client.post(
        "/api/instances/",
        json={
            "name": name,
            "raw_url": url,
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


def _create_smtp_channel(db: Session) -> SmtpChannel:
    ch = SmtpChannel(
        name="Test SMTP",
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password_enc=encrypt_secret("secret"),
        from_address="noreply@example.com",
        use_tls=True,
        use_ssl=False,
        enabled=True,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return ch


def _create_telegram_channel(db: Session) -> TelegramChannel:
    ch = TelegramChannel(
        name="Test Telegram",
        bot_token_enc=encrypt_secret("bot-token"),
        chat_id="-100123",
        enabled=True,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return ch


def test_list_bindings_empty(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.get(f"/api/instances/{inst['id']}/notification-bindings/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_bindings_instance_not_found(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/instances/99999/notification-bindings/")
    assert resp.status_code == 404


def test_create_binding_smtp(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    ch = _create_smtp_channel(db)
    resp = authed_client.post(
        f"/api/instances/{inst['id']}/notification-bindings/",
        json={"channel_type": "smtp", "channel_id": ch.id, "on_success": True, "on_failure": True},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["channel_type"] == "smtp"
    assert data["channel_id"] == ch.id
    assert data["instance_id"] == inst["id"]


def test_create_binding_telegram(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    ch = _create_telegram_channel(db)
    resp = authed_client.post(
        f"/api/instances/{inst['id']}/notification-bindings/",
        json={
            "channel_type": "telegram",
            "channel_id": ch.id,
            "on_success": False,
            "on_failure": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["channel_type"] == "telegram"
    assert data["on_success"] is False
    assert data["on_failure"] is True


def test_create_binding_instance_not_found(authed_client: TestClient, db: Session) -> None:
    ch = _create_smtp_channel(db)
    resp = authed_client.post(
        "/api/instances/99999/notification-bindings/",
        json={"channel_type": "smtp", "channel_id": ch.id},
    )
    assert resp.status_code == 404


def test_list_bindings_after_create(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    ch = _create_smtp_channel(db)
    authed_client.post(
        f"/api/instances/{inst['id']}/notification-bindings/",
        json={"channel_type": "smtp", "channel_id": ch.id},
    )
    resp = authed_client.get(f"/api/instances/{inst['id']}/notification-bindings/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_delete_binding(authed_client: TestClient, db: Session) -> None:
    inst = _create_instance(authed_client)
    ch = _create_smtp_channel(db)
    create_resp = authed_client.post(
        f"/api/instances/{inst['id']}/notification-bindings/",
        json={"channel_type": "smtp", "channel_id": ch.id},
    )
    binding_id = create_resp.json()["id"]
    resp = authed_client.delete(f"/api/instances/{inst['id']}/notification-bindings/{binding_id}")
    assert resp.status_code == 204


def test_delete_binding_not_found(authed_client: TestClient) -> None:
    inst = _create_instance(authed_client)
    resp = authed_client.delete(f"/api/instances/{inst['id']}/notification-bindings/99999")
    assert resp.status_code == 404


def test_delete_binding_wrong_instance(authed_client: TestClient, db: Session) -> None:
    inst1 = _create_instance(authed_client, "Inst1", "https://inst1.example.com")
    inst2 = _create_instance(authed_client, "Inst2", "https://inst2.example.com")
    ch = _create_smtp_channel(db)
    create_resp = authed_client.post(
        f"/api/instances/{inst1['id']}/notification-bindings/",
        json={"channel_type": "smtp", "channel_id": ch.id},
    )
    binding_id = create_resp.json()["id"]
    resp = authed_client.delete(f"/api/instances/{inst2['id']}/notification-bindings/{binding_id}")
    assert resp.status_code == 404
