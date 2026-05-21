"""First-boot initialisation: directory creation, Alembic migrations, admin seeding."""

from __future__ import annotations

import logging
import subprocess
import sys

from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password
from app.db import Base, SessionLocal, engine

logger = logging.getLogger(__name__)


def _ensure_directories() -> None:
    """Create persistent data directories if they do not exist."""
    for path in (settings.db_dir, settings.backups_dir, settings.logs_dir):
        path.mkdir(parents=True, exist_ok=True)
    logger.info("Data directories verified at %s", settings.data_dir)


def _run_migrations() -> None:
    """Run Alembic migrations to bring the schema up to date."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error("Alembic migration failed:\n%s", result.stderr)
        # Fall back to create_all so the app can at least start
        Base.metadata.create_all(bind=engine)
    else:
        logger.info("Database migrations applied successfully")


def _seed_admin(db: Session) -> None:
    """Insert the default admin user if no users exist yet."""
    from app.models.user import User

    if db.query(User).count() > 0:
        return

    admin = User(
        username="admin",
        password_hash=hash_password("admin"),
        must_change_password=True,
        timezone="UTC",
    )
    db.add(admin)
    db.commit()
    logger.info("Default admin user seeded (must change password on first login)")


def run_startup() -> None:
    """Execute all first-boot initialisation steps."""
    _ensure_directories()
    _run_migrations()

    with SessionLocal() as db:
        _seed_admin(db)

    logger.info("Startup sequence complete")

    # Register the Beat schedule-refresh task in redbeat (best-effort — Redis may not be up yet)
    try:
        from app.tasks.scheduler import bootstrap_beat_schedule

        bootstrap_beat_schedule()
    except Exception:
        logger.warning("Could not bootstrap beat schedule (Redis may be unavailable)")
