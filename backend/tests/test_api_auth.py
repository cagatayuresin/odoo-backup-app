"""Integration tests for the auth endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_login_invalid_credentials(client: TestClient, db: object) -> None:
    """Login with bad credentials returns 401."""
    resp = client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_valid_credentials(client: TestClient, db: object) -> None:
    """Seeded admin user can log in with default password."""
    from app.core.security import hash_password
    from app.models.user import User
    from sqlalchemy.orm import Session

    sess = db  # type: ignore[assignment]
    user = User(
        username="testadmin",
        password_hash=hash_password("MyPass123"),
        must_change_password=False,
    )
    sess.add(user)
    sess.commit()

    resp = client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "MyPass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testadmin"


def test_logout_clears_session(authed_client: TestClient) -> None:
    """Logging out should clear the session."""
    resp = authed_client.post("/api/auth/logout")
    assert resp.status_code == 200

    # Subsequent call to a protected endpoint should 401
    resp = authed_client.get("/api/account/me")
    assert resp.status_code == 401


def test_must_change_password_blocks_access(client: TestClient, db: object) -> None:
    """A user with must_change_password=True cannot access protected endpoints."""
    from app.core.security import hash_password
    from app.models.user import User
    from sqlalchemy.orm import Session

    sess = db  # type: ignore[assignment]
    user = User(
        username="forced",
        password_hash=hash_password("admin"),
        must_change_password=True,
    )
    sess.add(user)
    sess.commit()

    client.post("/api/auth/login", json={"username": "forced", "password": "admin"})

    resp = client.get("/api/instances/")
    assert resp.status_code == 403
