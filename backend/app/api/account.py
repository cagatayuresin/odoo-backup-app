"""Account management endpoints (current user profile)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_password_changed
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import PasswordChange, UserRead, UserUpdate

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/me", response_model=UserRead)
def get_me(user: User = Depends(require_password_changed)) -> User:
    """Return the currently authenticated user's profile."""
    return user


@router.patch("/me", response_model=UserRead)
def update_me(
    body: UserUpdate,
    user: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> User:
    """Update profile fields (timezone, recovery email, etc.)."""
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password", response_model=UserRead)
def change_password(
    body: PasswordChange,
    user: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> User:
    """Change password from the account page (user already authenticated and active)."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user.password_hash = hash_password(body.new_password)
    db.commit()
    db.refresh(user)
    return user
