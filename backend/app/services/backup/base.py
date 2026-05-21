"""Shared types and the BackupStrategy Protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.models.instance import Instance


@dataclass
class BackupResult:
    """Outcome of a single database backup operation."""

    success: bool
    file_path: Path | None = None
    file_size_bytes: int = 0
    error_message: str | None = None


class BackupStrategy(Protocol):
    """Interface all backup strategies must satisfy."""

    def run(self, instance: Instance, db_name: str) -> BackupResult:
        """Execute the backup and return a result descriptor."""
        ...

    def discover_databases(self, instance: Instance) -> list[str]:
        """Return the list of databases to back up for this instance."""
        ...
