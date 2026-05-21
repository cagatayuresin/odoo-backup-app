from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_token
from app.models.user import User


def _add_user(db: Session, username: str = "admin2", must_change: bool = True) -> User:
    user = User(
        username=username,
        password_hash=hash_password("Pass1234"),
        must_change_password=must_change,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_change_password_unauthenticated(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "Pass1234", "new_password": "NewPass99"},
    )
    assert resp.status_code == 401


def test_change_password_first_time(client: TestClient, db: Session) -> None:
    _add_user(db)
    client.post("/api/auth/login", json={"username": "admin2", "password": "Pass1234"})

    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "Pass1234", "new_password": "NewPass99!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["must_change_password"] is False


def test_change_password_wrong_current(client: TestClient, db: Session) -> None:
    _add_user(db)
    client.post("/api/auth/login", json={"username": "admin2", "password": "Pass1234"})

    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "WrongPass", "new_password": "NewPass99!"},
    )
    assert resp.status_code == 400


def test_request_password_reset_unknown_user(client: TestClient, db: Session) -> None:
    resp = client.post(
        "/api/auth/request-reset",
        json={"username": "nonexistent"},
    )
    assert resp.status_code == 200
    assert "reset email" in resp.json()["detail"]


def test_request_password_reset_no_recovery_config(client: TestClient, db: Session) -> None:
    user = _add_user(db, "reset_user", must_change=False)
    user.password_reset_enabled = False
    db.commit()

    resp = client.post(
        "/api/auth/request-reset",
        json={"username": "reset_user"},
    )
    assert resp.status_code == 200


def test_request_password_reset_sends_email(client: TestClient, db: Session) -> None:
    from app.core.security import encrypt_secret
    from app.models.notify import SmtpChannel

    ch = SmtpChannel(
        name="Recovery SMTP",
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password_enc=encrypt_secret("pass"),
        from_address="noreply@example.com",
        use_tls=True,
        use_ssl=False,
        enabled=True,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)

    user = _add_user(db, "reset_user2", must_change=False)
    user.password_reset_enabled = True
    user.recovery_email = "admin@example.com"
    user.recovery_channel_id = ch.id
    db.commit()

    with patch("app.services.notify.smtp.send_password_reset_email") as mock_send:
        resp = client.post(
            "/api/auth/request-reset",
            json={"username": "reset_user2"},
        )
    assert resp.status_code == 200
    mock_send.assert_called_once()


def test_reset_password_invalid_token(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": "invalid-token", "new_password": "NewPass99!"},
    )
    assert resp.status_code == 400
    assert "Invalid or expired" in resp.json()["detail"]


def test_reset_password_expired_token(client: TestClient, db: Session) -> None:
    user = _add_user(db, "expired_reset", must_change=False)
    token = "valid-token-format"
    user.reset_token_hash = hash_token(token)
    user.reset_token_expires_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()

    resp = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "NewPass99!"},
    )
    assert resp.status_code == 400


def test_reset_password_success(client: TestClient, db: Session) -> None:
    user = _add_user(db, "valid_reset", must_change=False)
    token = "valid-token-for-reset"
    user.reset_token_hash = hash_token(token)
    user.reset_token_expires_at = datetime.now(UTC) + timedelta(minutes=15)
    db.commit()

    resp = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "BrandNewPass99!"},
    )
    assert resp.status_code == 200
    assert "reset" in resp.json()["detail"].lower()


def test_logout_unauthenticated(client: TestClient) -> None:
    resp = client.post("/api/auth/logout")
    assert resp.status_code in (401, 403)
