from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_timezones(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/settings/timezones")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert "UTC" in data
    assert "Europe/Istanbul" in data


def test_cron_preview_valid(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/settings/cron/preview?expr=0+2+*+*+*")
    assert resp.status_code == 200
    data = resp.json()
    assert "next_runs" in data
    assert len(data["next_runs"]) == 5


def test_cron_preview_custom_count(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/settings/cron/preview?expr=0+2+*+*+*&count=3")
    assert resp.status_code == 200
    assert len(resp.json()["next_runs"]) == 3


def test_cron_preview_with_timezone(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/settings/cron/preview?expr=0+2+*+*+*&tz=Europe/Istanbul")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["next_runs"]) == 5


def test_cron_preview_invalid_expression(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/settings/cron/preview?expr=not-a-cron")
    assert resp.status_code == 422


def test_cron_preview_missing_expr(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/settings/cron/preview")
    assert resp.status_code == 422
