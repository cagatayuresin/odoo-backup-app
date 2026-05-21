"""Retention policy engine with a mandatory safety net.

Rules (per spec §6.4):
  - keep_last_n : keep the N most-recent successful/verified backups; delete the rest.
  - older_than_days : delete backups whose started_at is more than N days ago.

Safety net: if the computed deletion set would leave zero backups for the instance,
deletion is *skipped* entirely — the function returns an empty list and the caller
is responsible for emitting a warning / audit entry.

The "force delete" path (including the latest) is handled by a separate function
that bypasses the safety net and is gated in the API behind a typed confirmation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def compute_deletions_keep_last_n(
    run_ids_oldest_first: list[tuple[int, datetime]],
    keep_n: int,
) -> list[int]:
    """Compute which run IDs to delete under the keep-last-N rule.

    Args:
        run_ids_oldest_first: List of (run_id, started_at) tuples, oldest first.
        keep_n: Number of most-recent backups to retain.

    Returns:
        A list of run IDs that should be deleted, respecting the safety net.
        Returns an empty list if the rule would delete all backups.
    """
    if keep_n <= 0:
        msg = "keep_n must be a positive integer"
        raise ValueError(msg)

    total = len(run_ids_oldest_first)
    if total == 0:
        return []

    # Safety net: always keep at least one
    effective_keep = max(keep_n, 1)
    to_delete_count = max(0, total - effective_keep)

    if to_delete_count == 0:
        return []

    # Would we be deleting everything?
    if to_delete_count >= total:
        logger.warning(
            "Retention keep_last_%d would delete all %d backups — skipping to preserve the most recent.",
            keep_n,
            total,
        )
        return []

    return [run_id for run_id, _ in run_ids_oldest_first[:to_delete_count]]


def compute_deletions_older_than_days(
    run_ids_oldest_first: list[tuple[int, datetime]],
    max_age_days: int,
) -> list[int]:
    """Compute which run IDs to delete under the older-than-N-days rule.

    Args:
        run_ids_oldest_first: List of (run_id, started_at) tuples, oldest first.
        max_age_days: Backups older than this many days are candidates for deletion.

    Returns:
        A list of run IDs to delete, respecting the safety net.
        Returns an empty list if the rule would delete all backups.
    """
    if max_age_days <= 0:
        msg = "max_age_days must be a positive integer"
        raise ValueError(msg)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)

    candidates = [
        run_id
        for run_id, started_at in run_ids_oldest_first
        if started_at.replace(tzinfo=timezone.utc) < cutoff
    ]

    if not candidates:
        return []

    # Safety net: if ALL backups are older than the cutoff, preserve the most recent one
    if len(candidates) >= len(run_ids_oldest_first):
        logger.warning(
            "Retention older_than_%d_days would delete all %d backups — skipping to preserve the most recent.",
            max_age_days,
            len(run_ids_oldest_first),
        )
        return []

    return candidates


def compute_deletions(
    run_ids_oldest_first: list[tuple[int, datetime]],
    mode: str,
    value: int,
) -> tuple[list[int], bool]:
    """Unified retention computation.

    Args:
        run_ids_oldest_first: (run_id, started_at) pairs ordered oldest-first.
        mode: ``"keep_last_n"`` or ``"older_than_days"``.
        value: Policy parameter (N).

    Returns:
        A ``(deletion_ids, safety_net_triggered)`` tuple.  If the safety net
        prevented all deletions, *safety_net_triggered* is True and the caller
        should emit a warning.
    """
    total = len(run_ids_oldest_first)

    if mode == "keep_last_n":
        deletions = compute_deletions_keep_last_n(run_ids_oldest_first, value)
        # Safety net was triggered if there were excess backups but we returned nothing
        safety_triggered = total > value and len(deletions) == 0
    elif mode == "older_than_days":
        deletions = compute_deletions_older_than_days(run_ids_oldest_first, value)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=value)
        all_old = all(
            started.replace(tzinfo=timezone.utc) < cutoff
            for _, started in run_ids_oldest_first
        )
        safety_triggered = bool(run_ids_oldest_first) and all_old and len(deletions) == 0
    else:
        msg = f"Unknown retention mode: {mode!r}"
        raise ValueError(msg)

    return deletions, safety_triggered
