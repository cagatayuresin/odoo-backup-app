"""pg_dump backup strategy."""

from __future__ import annotations

import logging
import os
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.core.security import decrypt_secret
from app.models.instance import Instance
from app.services.backup.base import BackupResult

logger = logging.getLogger(__name__)


def _backup_path(instance: Instance, db_name: str, include_filestore: bool) -> Path:
    """Compute the destination path for a backup file."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest_dir = settings.backups_dir / instance.slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = ".tar.gz" if include_filestore else ".dump"
    return dest_dir / f"{ts}_{db_name}{ext}"


def run(instance: Instance, db_name: str) -> BackupResult:
    """Create a pg_dump backup, optionally bundled with the filestore.

    If ``instance.include_filestore`` is True, produces a ``.tar.gz`` containing
    ``db.dump`` (custom format) and ``filestore/``.
    Otherwise produces a bare ``.dump`` file (custom format).
    """
    db_host = instance.db_host or "localhost"
    db_port = instance.db_port or 5432
    db_user = instance.db_user or "odoo"
    db_password = ""
    if instance.db_password_enc:
        try:
            db_password = decrypt_secret(instance.db_password_enc)
        except ValueError as exc:
            return BackupResult(success=False, error_message=f"Cannot decrypt db_password: {exc}")

    dest = _backup_path(instance, db_name, instance.include_filestore)
    env = {**os.environ, "PGPASSWORD": db_password}

    if instance.include_filestore:
        return _run_with_filestore(
            instance, db_name, db_host, db_port, db_user, env, dest
        )

    return _run_dump_only(db_name, db_host, db_port, db_user, env, dest)


def _run_dump_only(
    db_name: str,
    db_host: str,
    db_port: int,
    db_user: str,
    env: dict[str, str],
    dest: Path,
) -> BackupResult:
    """Run pg_dump and write a custom-format .dump file."""
    cmd = [
        "pg_dump",
        "-h", db_host,
        "-p", str(db_port),
        "-U", db_user,
        "-F", "c",
        "-f", str(dest),
        db_name,
    ]
    result = subprocess.run(  # noqa: S603
        cmd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=3600,
    )
    if result.returncode != 0:
        dest.unlink(missing_ok=True)
        return BackupResult(
            success=False,
            error_message=f"pg_dump failed (exit {result.returncode}): {result.stderr[:512]}",
        )

    # Verify with pg_restore --list
    verify = subprocess.run(  # noqa: S603
        ["pg_restore", "--list", str(dest)],
        capture_output=True,
        check=False,
        timeout=120,
    )
    if verify.returncode != 0:
        return BackupResult(
            success=False,
            file_path=dest,
            file_size_bytes=dest.stat().st_size,
            error_message="pg_restore --list verification failed",
        )

    return BackupResult(success=True, file_path=dest, file_size_bytes=dest.stat().st_size)


def _run_with_filestore(
    instance: Instance,
    db_name: str,
    db_host: str,
    db_port: int,
    db_user: str,
    env: dict[str, str],
    dest: Path,
) -> BackupResult:
    """Run pg_dump and bundle it with the filestore into a .tar.gz archive."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        dump_path = tmp / "db.dump"

        cmd = [
            "pg_dump",
            "-h", db_host,
            "-p", str(db_port),
            "-U", db_user,
            "-F", "c",
            "-f", str(dump_path),
            db_name,
        ]
        result = subprocess.run(  # noqa: S603
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=3600,
        )
        if result.returncode != 0:
            return BackupResult(
                success=False,
                error_message=f"pg_dump failed (exit {result.returncode}): {result.stderr[:512]}",
            )

        with tarfile.open(dest, "w:gz") as tar:
            tar.add(dump_path, arcname="db.dump")
            if instance.filestore_path:
                fs_path = Path(instance.filestore_path)
                if fs_path.exists():
                    tar.add(fs_path, arcname="filestore")
                else:
                    logger.warning(
                        "Filestore path does not exist: %s — skipping filestore archive",
                        fs_path,
                    )

    return BackupResult(success=True, file_path=dest, file_size_bytes=dest.stat().st_size)


def discover_databases(instance: Instance) -> list[str]:
    """Discover non-template, non-postgres databases via psql."""
    db_host = instance.db_host or "localhost"
    db_port = instance.db_port or 5432
    db_user = instance.db_user or "odoo"
    db_password = ""
    if instance.db_password_enc:
        try:
            db_password = decrypt_secret(instance.db_password_enc)
        except ValueError:
            return []

    env = {**os.environ, "PGPASSWORD": db_password}
    sql = (
        "SELECT datname FROM pg_database "
        "WHERE datistemplate = false AND datname NOT IN ('postgres');"
    )
    cmd = [
        "psql",
        "-h", db_host,
        "-p", str(db_port),
        "-U", db_user,
        "-t", "-c", sql,
        "postgres",
    ]
    result = subprocess.run(  # noqa: S603
        cmd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        logger.warning("Cannot discover databases for %s: %s", instance.slug, result.stderr)
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
