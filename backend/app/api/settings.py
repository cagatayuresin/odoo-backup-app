"""App-wide settings endpoint and cron preview helper."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_password_changed
from app.core.cron import next_runs, validate_cron
from app.core.timezone import all_timezones
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/timezones")
def get_timezones(
    _: User = Depends(require_password_changed),
) -> list[str]:
    """Return all IANA timezone names."""
    return all_timezones()


@router.get("/cron/preview")
def preview_cron(
    expr: str = Query(..., description="Cron expression to preview"),
    tz: str = Query("UTC", description="IANA timezone for display"),
    count: int = Query(5, ge=1, le=20),
    _: User = Depends(require_password_changed),
) -> dict[str, list[str]]:
    """Return the next N fire times for a cron expression in a given timezone."""
    try:
        validate_cron(expr)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        times = next_runs(expr, count=count, tz=tz)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return {"next_runs": [dt.isoformat() for dt in times]}
