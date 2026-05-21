"""Pydantic schemas for Job CRUD."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from app.core.cron import validate_cron


class JobBase(BaseModel):
    """Shared job fields."""

    name: str
    cron_expression: str
    enabled: bool = True

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expr(cls, v: str) -> str:
        """Reject invalid cron expressions at the schema boundary."""
        validate_cron(v)
        return v


class JobCreate(JobBase):
    """Request body for creating a job (instance_id comes from the URL path)."""


class JobUpdate(BaseModel):
    """Partial job update."""

    name: str | None = None
    cron_expression: str | None = None
    enabled: bool | None = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expr(cls, v: str | None) -> str | None:
        """Validate cron expression if provided."""
        if v is not None:
            validate_cron(v)
        return v


class JobRead(BaseModel):
    """Public representation of a Job."""

    id: int
    instance_id: int
    name: str
    cron_expression: str
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
