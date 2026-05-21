"""Tests for core/retention.py — every safety-net edge case."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.retention import (
    compute_deletions,
    compute_deletions_keep_last_n,
    compute_deletions_older_than_days,
)

_NOW = datetime(2026, 5, 21, 12, 0, 0, tzinfo=UTC)


def _make_runs(
    count: int,
    base_dt: datetime = _NOW,
    step_hours: int = 24,
) -> list[tuple[int, datetime]]:
    """Generate (run_id, started_at) pairs oldest-first."""
    return [(i + 1, base_dt - timedelta(hours=step_hours * (count - 1 - i))) for i in range(count)]


# ─── keep_last_n ──────────────────────────────────────────────────────────────


def test_keep_last_n_basic() -> None:
    """Keep 3 of 5 → delete the 2 oldest."""
    runs = _make_runs(5)
    result = compute_deletions_keep_last_n(runs, keep_n=3)
    assert result == [1, 2]


def test_keep_last_n_exactly_n() -> None:
    """Exactly N backups → nothing to delete."""
    runs = _make_runs(3)
    assert compute_deletions_keep_last_n(runs, keep_n=3) == []


def test_keep_last_n_fewer_than_n() -> None:
    """Fewer than N backups → nothing to delete."""
    runs = _make_runs(2)
    assert compute_deletions_keep_last_n(runs, keep_n=5) == []


def test_keep_last_n_safety_net_preserves_last() -> None:
    """keep_last_1 on 1 backup → safety net fires, nothing deleted."""
    runs = _make_runs(1)
    result = compute_deletions_keep_last_n(runs, keep_n=1)
    assert result == []


def test_keep_last_n_zero_raises() -> None:
    """keep_n=0 must raise ValueError."""
    with pytest.raises(ValueError):
        compute_deletions_keep_last_n([], keep_n=0)


def test_keep_last_n_empty_runs() -> None:
    """No runs → nothing to delete."""
    assert compute_deletions_keep_last_n([], keep_n=5) == []


# ─── older_than_days ──────────────────────────────────────────────────────────


def test_older_than_days_basic() -> None:
    """Runs older than 7 days should be in the deletion set."""
    old = _NOW - timedelta(days=10)
    recent = _NOW - timedelta(days=2)
    runs = [(1, old), (2, recent)]
    result = compute_deletions_older_than_days(runs, max_age_days=7)
    assert result == [1]


def test_older_than_days_nothing_old() -> None:
    """No runs older than the cutoff → empty deletion set."""
    runs = [(1, _NOW - timedelta(days=2)), (2, _NOW - timedelta(days=1))]
    assert compute_deletions_older_than_days(runs, max_age_days=7) == []


def test_older_than_days_safety_net() -> None:
    """All backups older than cutoff → safety net fires, nothing deleted."""
    runs = [(1, _NOW - timedelta(days=30)), (2, _NOW - timedelta(days=20))]
    result = compute_deletions_older_than_days(runs, max_age_days=7)
    assert result == []


def test_older_than_days_empty_runs() -> None:
    """No runs → nothing to delete."""
    assert compute_deletions_older_than_days([], max_age_days=7) == []


def test_older_than_days_zero_raises() -> None:
    """max_age_days=0 must raise ValueError."""
    with pytest.raises(ValueError):
        compute_deletions_older_than_days([], max_age_days=0)


# ─── compute_deletions (unified) ──────────────────────────────────────────────


def test_unified_keep_last_n() -> None:
    """Unified interface delegates correctly to keep_last_n."""
    runs = _make_runs(5)
    deletions, safety = compute_deletions(runs, "keep_last_n", 3)
    assert deletions == [1, 2]
    assert not safety


def test_unified_safety_net_triggered() -> None:
    """Returns safety_triggered=True when all backups would be deleted."""
    runs = [(1, _NOW - timedelta(days=30))]
    deletions, safety = compute_deletions(runs, "older_than_days", 7)
    assert deletions == []
    assert safety


def test_unified_unknown_mode_raises() -> None:
    """Unknown retention mode must raise ValueError."""
    with pytest.raises(ValueError):
        compute_deletions([], "monthly", 5)
