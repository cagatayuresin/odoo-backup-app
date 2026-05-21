"""Tests for core/cron.py."""

from __future__ import annotations

from datetime import UTC

import pytest

from app.core.cron import is_valid_cron, next_run_utc, next_runs, validate_cron


def test_valid_cron_expressions() -> None:
    """Standard cron expressions should pass validation."""
    valid = [
        "0 2 * * *",  # every day at 02:00
        "*/15 * * * *",  # every 15 minutes
        "0 0 1 * *",  # monthly
        "0 9 * * 1",  # every Monday at 09:00
        "30 6 * * 1-5",  # weekdays at 06:30
    ]
    for expr in valid:
        assert is_valid_cron(expr), f"Expected valid: {expr}"


def test_invalid_cron_expressions() -> None:
    """Malformed cron expressions should fail validation."""
    invalid = [
        "",
        "not a cron",
        "60 * * * *",  # minute out of range
        "* * * * * *",  # 6 fields
        "* * * *",  # 4 fields
    ]
    for expr in invalid:
        assert not is_valid_cron(expr), f"Expected invalid: {expr}"


def test_validate_cron_raises_on_invalid() -> None:
    """validate_cron() should raise ValueError for bad expressions."""
    with pytest.raises(ValueError):
        validate_cron("not a cron")


def test_next_runs_returns_five_datetimes() -> None:
    """next_runs should return exactly 5 timezone-aware datetimes."""
    runs = next_runs("0 2 * * *", count=5, tz="UTC")
    assert len(runs) == 5
    for dt in runs:
        assert dt.tzinfo is not None


def test_next_runs_in_target_timezone() -> None:
    """Returned datetimes should be in the requested timezone."""
    runs = next_runs("0 9 * * *", count=3, tz="Europe/Istanbul")
    for dt in runs:
        assert dt.tzinfo is not None
        # Offset should be +03:00 (or +0300 depending on DST)
        offset_hours = dt.utcoffset().total_seconds() / 3600  # type: ignore[union-attr]
        assert offset_hours in {3.0, 4.0}  # Istanbul is UTC+3 (no DST since 2016)


def test_next_run_utc_returns_utc_datetime() -> None:
    """next_run_utc should return a UTC-aware datetime."""

    dt = next_run_utc("*/5 * * * *")
    assert dt.tzinfo == UTC


def test_next_runs_invalid_expr_raises() -> None:
    """next_runs should raise ValueError for bad cron."""
    with pytest.raises(ValueError):
        next_runs("invalid cron", count=5)
