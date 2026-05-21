"""Pydantic schemas for User CRUD and auth."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserRead(BaseModel):
    """Public representation of the admin user (no password)."""

    id: int
    username: str
    must_change_password: bool
    timezone: str
    recovery_email: str | None
    recovery_channel_id: int | None
    password_reset_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Fields the admin can update on the account page."""

    timezone: str | None = None
    recovery_email: EmailStr | None = None
    recovery_channel_id: int | None = None
    password_reset_enabled: bool | None = None

    @field_validator("timezone")
    @classmethod
    def validate_tz(cls, v: str | None) -> str | None:
        """Ensure the timezone is a valid IANA name."""
        if v is None:
            return v
        from app.core.timezone import is_valid_timezone

        if not is_valid_timezone(v):
            msg = f"Unknown timezone: {v!r}"
            raise ValueError(msg)
        return v


class PasswordChange(BaseModel):
    """Request body for changing the admin password."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_strength(cls, v: str) -> str:
        """Enforce a minimum password length."""
        if len(v) < 8:
            msg = "Password must be at least 8 characters"
            raise ValueError(msg)
        return v


class LoginRequest(BaseModel):
    """Login form body."""

    username: str
    password: str


class PasswordResetRequest(BaseModel):
    """Request a password reset email."""

    username: str


class PasswordResetConfirm(BaseModel):
    """Set a new password using a reset token."""

    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_strength(cls, v: str) -> str:
        """Enforce a minimum password length."""
        if len(v) < 8:
            msg = "Password must be at least 8 characters"
            raise ValueError(msg)
        return v
