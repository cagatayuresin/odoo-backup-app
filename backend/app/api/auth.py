"""Authentication endpoints: login, logout, forced password change, password reset."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import (
    generate_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    UserRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserRead)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> User:
    """Authenticate the user and establish a session."""
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    request.session["user_id"] = user.id
    logger.info("User %s logged in", user.username)
    return user


@router.post("/logout")
def logout(request: Request, _: User = Depends(get_current_user)) -> dict[str, str]:
    """Invalidate the current session."""
    request.session.clear()
    return {"detail": "Logged out"}


@router.post("/change-password", response_model=UserRead)
def change_password(
    body: PasswordChange,
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Change the authenticated user's password.

    Works for both the forced first-time change and subsequent voluntary changes.
    The user must supply their current password to prevent CSRF escalation.
    """
    user_id: int | None = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    db.commit()
    db.refresh(user)

    logger.info("User %s changed password", user.username)
    return user


@router.post("/request-reset")
def request_password_reset(
    body: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Send a password reset email if recovery is configured for the user.

    Always returns 200 to avoid username enumeration.
    """
    user = db.query(User).filter(User.username == body.username).first()

    if user and user.password_reset_enabled and user.recovery_email and user.recovery_channel_id:
        token, token_hash = generate_reset_token()
        user.reset_token_hash = token_hash
        user.reset_token_expires_at = datetime.now(UTC) + timedelta(minutes=15)
        db.commit()

        # Dispatch reset email (imported here to avoid circular import)
        try:
            from app.services.notify.smtp import send_password_reset_email

            send_password_reset_email(user, token, db)
        except Exception:
            logger.exception("Failed to send password reset email for user %s", user.username)

    return {"detail": "If recovery is configured, a reset email has been sent."}


@router.post("/reset-password")
def reset_password(
    body: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Set a new password using a valid reset token."""
    token_hash = hash_token(body.token)
    user = db.query(User).filter(User.reset_token_hash == token_hash).first()

    now = datetime.now(UTC)
    if (
        user is None
        or user.reset_token_expires_at is None
        or user.reset_token_expires_at.replace(tzinfo=UTC) < now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.commit()

    request.session.clear()
    logger.info("Password reset completed for user %s", user.username)
    return {"detail": "Password has been reset. Please log in."}
