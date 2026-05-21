"""Pydantic schemas for cloud accounts and instance bindings."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.cloud import CloudProvider


class CloudAccountCreate(BaseModel):
    """Request body for creating a cloud account."""

    provider: CloudProvider
    name: str
    credentials: dict[str, str]
    enabled: bool = True


class CloudAccountUpdate(BaseModel):
    """Partial cloud account update."""

    name: str | None = None
    credentials: dict[str, str] | None = None
    enabled: bool | None = None


class CloudAccountRead(BaseModel):
    """Public cloud account (no credentials)."""

    id: int
    provider: CloudProvider
    name: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CloudBindingCreate(BaseModel):
    """Bind a cloud account to an instance."""

    cloud_account_id: int
    remote_folder: str = "/odoo-backups"
    enabled: bool = True
    apply_retention_remotely: bool = False


class CloudBindingUpdate(BaseModel):
    """Partial cloud binding update."""

    remote_folder: str | None = None
    enabled: bool | None = None
    apply_retention_remotely: bool | None = None


class CloudBindingRead(BaseModel):
    """Public representation of an instance cloud binding."""

    id: int
    instance_id: int
    cloud_account_id: int
    remote_folder: str
    enabled: bool
    apply_retention_remotely: bool

    model_config = {"from_attributes": True}
