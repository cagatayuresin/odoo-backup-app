"""Pydantic schemas for Instance CRUD."""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator

from app.models.instance import BackupMethod, DbSelectionMode, RetentionMode


class InstanceBase(BaseModel):
    """Fields shared across create / update / read."""

    name: str
    raw_url: str
    backup_method: BackupMethod = BackupMethod.odoo_endpoint
    master_password: str | None = None  # plaintext on write; not returned on read
    db_host: str | None = None
    db_port: int | None = 5432
    db_user: str | None = None
    db_password: str | None = None  # plaintext on write; not returned on read
    filestore_path: str | None = None
    db_selection_mode: DbSelectionMode = DbSelectionMode.single
    db_names: list[str] | None = None
    include_filestore: bool = False
    retention_mode: RetentionMode = RetentionMode.keep_last_n
    retention_value: int = 7
    notifications_enabled: bool = True

    @field_validator("retention_value")
    @classmethod
    def positive_retention(cls, v: int) -> int:
        """Ensure retention_value is positive."""
        if v <= 0:
            msg = "retention_value must be a positive integer"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def check_pg_fields(self) -> InstanceBase:
        """Require DB credentials when backup_method is pg_dump."""
        if self.backup_method == BackupMethod.pg_dump and (not self.db_host or not self.db_user):
            msg = "db_host and db_user are required for pg_dump backup method"
            raise ValueError(msg)
        return self


class InstanceCreate(InstanceBase):
    """Request body for creating a new instance."""


class InstanceUpdate(BaseModel):
    """Partial update — all fields optional."""

    name: str | None = None
    raw_url: str | None = None
    backup_method: BackupMethod | None = None
    master_password: str | None = None
    db_host: str | None = None
    db_port: int | None = None
    db_user: str | None = None
    db_password: str | None = None
    filestore_path: str | None = None
    db_selection_mode: DbSelectionMode | None = None
    db_names: list[str] | None = None
    include_filestore: bool | None = None
    retention_mode: RetentionMode | None = None
    retention_value: int | None = None
    notifications_enabled: bool | None = None


class InstanceRead(BaseModel):
    """Public representation of an Instance (no plaintext secrets)."""

    id: int
    name: str
    slug: str
    raw_url: str
    parsed_scheme: str
    parsed_host: str
    parsed_port: int
    backup_method: BackupMethod
    db_host: str | None
    db_port: int | None
    db_user: str | None
    filestore_path: str | None
    db_selection_mode: DbSelectionMode
    db_names: list[str] | None
    include_filestore: bool
    retention_mode: RetentionMode
    retention_value: int
    notifications_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("db_names", mode="before")
    @classmethod
    def parse_db_names(cls, v: str | list[str] | None) -> list[str] | None:
        """Deserialise the JSON-encoded db_names column."""
        if v is None:
            return None
        if isinstance(v, str):
            return json.loads(v)  # type: ignore[no-any-return]
        return v
