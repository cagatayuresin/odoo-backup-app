"""pytest fixtures shared across the test suite."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Redirect data dir to a temp path so tests never touch /data
os.environ.setdefault("OB_DATA_DIR", str(Path(__file__).parent / "_test_data"))
os.environ.setdefault("OB_SECRET_KEY", "test-secret-key-for-unit-tests-!!")
os.environ.setdefault("OB_SESSION_SECRET", "test-session-secret-32chars-!!")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

from app.db import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def test_engine() -> object:
    """Create an in-memory SQLite engine for the test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db(test_engine: object) -> Generator[Session, None, None]:
    """Provide a test database session, rolling back after each test."""
    TestingSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """Provide a TestClient with the in-memory DB injected."""
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def authed_client(client: TestClient, db: Session) -> TestClient:
    """Return a client that is already logged in as admin (password already changed)."""
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        username="admin",
        password_hash=hash_password("TestPass123"),
        must_change_password=False,
    )
    db.add(user)
    db.commit()

    resp = client.post("/api/auth/login", json={"username": "admin", "password": "TestPass123"})
    assert resp.status_code == 200  # noqa: S101
    return client
