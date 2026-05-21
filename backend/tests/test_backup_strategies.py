"""Tests for backup strategies — mocked HTTP and subprocess calls."""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_instance(
    slug: str = "test-instance",
    scheme: str = "https",
    host: str = "mycompany.com",
    port: int = 443,
    master_password: str = "secret",
    backup_method: str = "odoo_endpoint",
) -> MagicMock:
    """Build a mock Instance object."""
    inst = MagicMock()
    inst.slug = slug
    inst.parsed_scheme = scheme
    inst.parsed_host = host
    inst.parsed_port = port
    inst.backup_method = backup_method
    inst.include_filestore = False
    inst.filestore_path = None
    inst.db_host = "localhost"
    inst.db_port = 5432
    inst.db_user = "odoo"
    inst.db_password_enc = None

    from app.core.security import encrypt_secret

    inst.master_password_enc = encrypt_secret(master_password)
    return inst


# ─── odoo_endpoint strategy ───────────────────────────────────────────────────


def test_odoo_endpoint_success(tmp_path: Path) -> None:
    """A successful download + valid ZIP should return BackupResult(success=True)."""
    import io

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", '{"db": "mydb"}')
    buf.seek(0)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.iter_bytes = MagicMock(return_value=iter([buf.read()]))
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_response)
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.services.backup.odoo_endpoint.settings") as mock_settings:
        mock_settings.backups_dir = tmp_path

        with patch("httpx.Client", return_value=mock_client):
            from app.services.backup.odoo_endpoint import run

            inst = _make_instance()
            result = run(inst, "mydb")

    assert result.success
    assert result.file_path is not None
    assert result.file_size_bytes > 0


def test_odoo_endpoint_no_master_password() -> None:
    """Missing master password should return failure."""
    from app.services.backup.odoo_endpoint import run

    inst = _make_instance()
    inst.master_password_enc = None

    result = run(inst, "mydb")
    assert not result.success
    assert "master_password" in (result.error_message or "")


def test_odoo_endpoint_http_error(tmp_path: Path) -> None:
    """HTTP error from Odoo should return failure."""
    import httpx

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "403 Forbidden",
        request=MagicMock(),
        response=MagicMock(status_code=403, text="Forbidden"),
    )
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_response)
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.services.backup.odoo_endpoint.settings") as mock_settings:
        mock_settings.backups_dir = tmp_path
        with patch("httpx.Client", return_value=mock_client):
            from app.services.backup.odoo_endpoint import run

            result = run(_make_instance(), "mydb")

    assert not result.success
    assert "403" in (result.error_message or "")


# ─── verify module ────────────────────────────────────────────────────────────


def test_verify_valid_zip(tmp_path: Path) -> None:
    """A well-formed ZIP should pass verification."""
    zip_path = tmp_path / "backup.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("db.sql", "SELECT 1;")

    from app.services.backup.verify import verify_backup

    passed, error = verify_backup(zip_path)
    assert passed
    assert error is None


def test_verify_corrupt_zip(tmp_path: Path) -> None:
    """A corrupt file should fail verification."""
    bad_zip = tmp_path / "corrupt.zip"
    bad_zip.write_bytes(b"not a zip")

    from app.services.backup.verify import verify_backup

    passed, error = verify_backup(bad_zip)
    assert not passed
    assert error is not None


def test_verify_missing_file(tmp_path: Path) -> None:
    """Missing file should fail verification."""
    from app.services.backup.verify import verify_backup

    passed, error = verify_backup(tmp_path / "nonexistent.zip")
    assert not passed
    assert error is not None
