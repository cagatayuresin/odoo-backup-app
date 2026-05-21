"""FastAPI dependency utilities: session extraction, DB, current user."""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User

logger = logging.getLogger(__name__)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated User or raise 401.

    Reads the ``user_id`` key from the signed session cookie.
    """
    user_id: int | None = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = db.get(User, user_id)
    if user is None:
        # Session references a deleted user — clear it
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return user


def require_password_changed(
    user: User = Depends(get_current_user),
) -> User:
    """Block access if the user has not yet changed the default password."""
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required before accessing this resource",
        )
    return user
