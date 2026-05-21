"""Timezone helpers."""

from __future__ import annotations

import pytz


def all_timezones() -> list[str]:
    """Return the full list of IANA timezone names sorted alphabetically."""
    return sorted(pytz.all_timezones)


def is_valid_timezone(tz: str) -> bool:
    """Return True if *tz* is a recognised IANA timezone name."""
    return tz in pytz.all_timezones_set
