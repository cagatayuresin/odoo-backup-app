"""Backup integrity verification helpers."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path


def verify_backup(file_path: str | Path) -> tuple[bool, str | None]:
    """Verify a backup file's integrity.

    Routes to the correct verifier based on file extension.

    Returns:
        (passed, error_message) — error_message is None on success.
    """
    path = Path(file_path)
    if not path.exists():
        return False, f"File not found: {path}"

    if path.suffix == ".zip":
        return _verify_zip(path)
    if path.suffix == ".dump":
        return _verify_pg_dump(path)
    if path.name.endswith(".tar.gz"):
        return _verify_tar_gz(path)

    return False, f"Unrecognised backup format: {path.suffix}"


def _verify_zip(path: Path) -> tuple[bool, str | None]:
    """Verify ZIP integrity via testzip()."""
    try:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad:
                return False, f"Corrupt file in ZIP: {bad}"
        return True, None
    except zipfile.BadZipFile as exc:
        return False, f"Bad ZIP file: {exc}"


def _verify_pg_dump(path: Path) -> tuple[bool, str | None]:
    """Verify a custom-format pg_dump with pg_restore --list."""
    result = subprocess.run(  # noqa: S603
        ["pg_restore", "--list", str(path)],
        capture_output=True,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        return False, f"pg_restore verification failed (exit {result.returncode})"
    return True, None


def _verify_tar_gz(path: Path) -> tuple[bool, str | None]:
    """Verify a tar.gz archive can be listed without errors."""
    import tarfile

    try:
        with tarfile.open(path, "r:gz") as tar:
            _ = tar.getmembers()
        return True, None
    except tarfile.TarError as exc:
        return False, f"Corrupt tar.gz archive: {exc}"
