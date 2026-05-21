"""Cloud provider protocol and shared types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


@dataclass
class RemoteFile:
    """Metadata for a file stored in cloud storage."""

    remote_id: str
    name: str
    size_bytes: int
    modified_at: datetime


class CloudProvider(Protocol):
    """Interface every cloud storage provider implementation must satisfy."""

    def upload(self, local_path: Path, remote_folder: str) -> str:
        """Upload *local_path* to *remote_folder* and return the remote file ID."""
        ...

    def list_files(self, remote_folder: str) -> list[RemoteFile]:
        """Return files in *remote_folder*, most-recently-modified first."""
        ...

    def delete_file(self, remote_id: str) -> None:
        """Delete the file identified by *remote_id*."""
        ...
