from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.backup.verify import verify_backup


def test_verify_nonexistent_file() -> None:
    ok, err = verify_backup("/nonexistent/path/backup.dump")
    assert ok is False
    assert "not found" in err.lower()


def test_verify_unrecognised_format(tmp_path: Path) -> None:
    f = tmp_path / "backup.bak"
    f.write_bytes(b"data")
    ok, err = verify_backup(f)
    assert ok is False
    assert "unrecognised" in err.lower()


def test_verify_valid_zip(tmp_path: Path) -> None:
    zf_path = tmp_path / "backup.zip"
    with zipfile.ZipFile(zf_path, "w") as zf:
        zf.writestr("db.sql", "SELECT 1;")
    ok, err = verify_backup(zf_path)
    assert ok is True
    assert err is None


def test_verify_corrupt_zip(tmp_path: Path) -> None:
    zf_path = tmp_path / "corrupt.zip"
    zf_path.write_bytes(b"not a zip file at all")
    ok, err = verify_backup(zf_path)
    assert ok is False
    assert err is not None


def test_verify_valid_tar_gz(tmp_path: Path) -> None:
    tgz_path = tmp_path / "backup.tar.gz"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        content = b"fake db dump content"
        info = tarfile.TarInfo(name="db.dump")
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    tgz_path.write_bytes(buf.getvalue())
    ok, err = verify_backup(tgz_path)
    assert ok is True
    assert err is None


def test_verify_corrupt_tar_gz(tmp_path: Path) -> None:
    tgz_path = tmp_path / "corrupt.tar.gz"
    tgz_path.write_bytes(b"not a valid tar.gz file")
    ok, err = verify_backup(tgz_path)
    assert ok is False
    assert err is not None


def test_verify_pg_dump_success(tmp_path: Path) -> None:
    dump_path = tmp_path / "backup.dump"
    dump_path.write_bytes(b"fake pg_dump content")
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("subprocess.run", return_value=mock_result):
        ok, err = verify_backup(dump_path)
    assert ok is True
    assert err is None


def test_verify_pg_dump_failure(tmp_path: Path) -> None:
    dump_path = tmp_path / "backup.dump"
    dump_path.write_bytes(b"corrupt dump")
    mock_result = MagicMock()
    mock_result.returncode = 1
    with patch("subprocess.run", return_value=mock_result):
        ok, err = verify_backup(dump_path)
    assert ok is False
    assert "pg_restore verification failed" in err
    assert "exit 1" in err


def test_verify_zip_with_bad_entry(tmp_path: Path) -> None:
    zf_path = tmp_path / "backup.zip"
    with zipfile.ZipFile(zf_path, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("file.txt", "hello")
    with patch("zipfile.ZipFile.testzip", return_value="file.txt"):
        ok, err = verify_backup(zf_path)
    assert ok is False
    assert "file.txt" in err
