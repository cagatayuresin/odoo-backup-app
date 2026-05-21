"""Odoo /web/database/backup strategy."""

from __future__ import annotations

import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import settings
from app.core.security import decrypt_secret
from app.models.instance import Instance
from app.services.backup.base import BackupResult

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=30.0, read=3600.0, write=30.0, pool=5.0)


def _backup_path(instance: Instance, db_name: str) -> Path:
    """Compute the destination path for a backup file."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest_dir = settings.backups_dir / instance.slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / f"{ts}_{db_name}.zip"


def run(instance: Instance, db_name: str) -> BackupResult:
    """Download a database backup via Odoo's built-in endpoint.

    POSTs to ``<base>/web/database/backup`` and streams the ZIP to disk,
    then validates ZIP integrity.
    """
    if not instance.master_password_enc:
        return BackupResult(success=False, error_message="master_password not configured")

    try:
        master_password = decrypt_secret(instance.master_password_enc)
    except ValueError as exc:
        return BackupResult(success=False, error_message=f"Cannot decrypt master password: {exc}")

    base_url = f"{instance.parsed_scheme}://{instance.parsed_host}:{instance.parsed_port}"
    url = f"{base_url}/web/database/backup"
    dest = _backup_path(instance, db_name)

    try:
        with httpx.Client(timeout=_TIMEOUT, verify=True) as client:
            with client.stream(
                "POST",
                url,
                data={
                    "master_pwd": master_password,
                    "name": db_name,
                    "backup_format": "zip",
                },
            ) as resp:
                resp.raise_for_status()
                with dest.open("wb") as fh:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        fh.write(chunk)
    except httpx.HTTPStatusError as exc:
        dest.unlink(missing_ok=True)
        return BackupResult(
            success=False,
            error_message=f"HTTP {exc.response.status_code}: {exc.response.text[:256]}",
        )
    except httpx.RequestError as exc:
        dest.unlink(missing_ok=True)
        return BackupResult(success=False, error_message=f"Network error: {exc}")

    file_size = dest.stat().st_size

    # Validate ZIP integrity
    try:
        with zipfile.ZipFile(dest) as zf:
            bad_file = zf.testzip()
            if bad_file is not None:
                dest.unlink(missing_ok=True)
                return BackupResult(
                    success=False,
                    error_message=f"ZIP integrity check failed at: {bad_file}",
                )
    except zipfile.BadZipFile as exc:
        dest.unlink(missing_ok=True)
        return BackupResult(success=False, error_message=f"Not a valid ZIP file: {exc}")

    logger.info(
        "Backup completed via odoo_endpoint: instance=%s db=%s size=%d path=%s",
        instance.slug,
        db_name,
        file_size,
        dest,
    )
    return BackupResult(success=True, file_path=dest, file_size_bytes=file_size)


def discover_databases(instance: Instance) -> list[str]:
    """Discover databases via ``/web/database/list``."""
    base_url = f"{instance.parsed_scheme}://{instance.parsed_host}:{instance.parsed_port}"
    url = f"{base_url}/web/database/list"

    try:
        with httpx.Client(timeout=httpx.Timeout(10.0), verify=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data: list[str] = resp.json()
            if isinstance(data, list):
                return [str(d) for d in data]
            return []
    except Exception as exc:
        logger.warning("Cannot discover databases for %s: %s", instance.slug, exc)
        return []
