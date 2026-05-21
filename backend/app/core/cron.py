"""Cron expression validation and next-run preview using croniter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytz
from croniter import CroniterBadCronError, croniter


def is_valid_cron(expression: str) -> bool:
    """Return True if *expression* is a valid 5-field cron expression."""
    parts = expression.strip().split()
    if len(parts) != 5:
        return False
    return bool(croniter.is_valid(expression))


def validate_cron(expression: str) -> None:
    """Raise :exc:`ValueError` if *expression* is not a valid cron expression."""
    if not is_valid_cron(expression):
        msg = f"Invalid cron expression: {expression!r}"
        raise ValueError(msg)


def next_runs(expression: str, count: int = 5, tz: str = "UTC") -> list[datetime]:
    """Return the next *count* scheduled datetimes for *expression* in *tz*.

    Args:
        expression: A valid 5-field cron expression.
        count: How many future fire times to return.
        tz: IANA timezone name (e.g. ``"Europe/Istanbul"``).

    Returns:
        A list of timezone-aware :class:`datetime` objects in *tz*.

    Raises:
        ValueError: If the cron expression is invalid.
        pytz.exceptions.UnknownTimeZoneError: If *tz* is not a recognised IANA name.
    """
    validate_cron(expression)
    zone = pytz.timezone(tz)
    base = datetime.now(UTC)

    try:
        it = croniter(expression, base)
    except CroniterBadCronError as exc:
        msg = f"Invalid cron expression: {expression!r}"
        raise ValueError(msg) from exc

    results: list[datetime] = []
    for _ in range(count):
        next_dt: datetime = it.get_next(datetime)
        results.append(next_dt.astimezone(zone))

    return results


def next_run_utc(expression: str) -> datetime:
    """Return the single next scheduled UTC datetime for *expression*."""
    validate_cron(expression)
    base = datetime.now(UTC)
    it = croniter(expression, base)
    result: datetime = it.get_next(datetime)
    return result.replace(tzinfo=UTC)
