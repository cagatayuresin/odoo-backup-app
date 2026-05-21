"""Pydantic schemas for BackupRun."""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.backup import BackupStatus, VerificationStatus


class BackupRunRead(BaseModel):
    """Public representation of a BackupRun."""

    id: int
    job_id: int | None
    instance_id: int
    started_at: datetime
    finished_at: datetime | None
    status: BackupStatus
    file_path: str | None
    file_size_bytes: int | None
    db_name: str
    error_message: str | None
    verification_status: VerificationStatus
    cloud_sync_status: dict[str, str] | None

    model_config = {"from_attributes": True}

    @field_validator("cloud_sync_status", mode="before")
    @classmethod
    def parse_cloud_status(cls, v: str | dict[str, str] | None) -> dict[str, str] | None:
        """Deserialise JSON column."""
        if v is None:
            return None
        if isinstance(v, str):
            return json.loads(v)  # type: ignore[no-any-return]
        return v
