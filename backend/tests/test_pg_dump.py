from __future__ import annotations

import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.security import encrypt_secret
from app.models.instance import Instance
from app.services.backup import pg_dump


def _make_instance(
    include_filestore: bool = False,
    db_password: str | None = None,
    filestore_path: str | None = None,
) -> Instance:
    inst = Instance(
        name="Test Instance",
        slug="test-instance",
        raw_url="https://test.example.com",
        parsed_scheme="https",
        parsed_host="test.example.com",
        parsed_port=443,
        db_host="localhost",
        db_port=5432,
        db_user="odoo",
        db_password_enc=encrypt_secret(db_password) if db_password else None,
        include_filestore=include_filestore,
        filestore_path=filestore_path,
    )
    return inst


def _mock_result(returncode: int = 0, stderr: str = "", stdout: str = "TOC") -> MagicMock:
    r = MagicMock()
    r.returncode = returncode
    r.stderr = stderr
    r.stdout = stdout
    return r


def _side_effect_create_file(dest_arg_index: int):
    """Returns a side_effect that creates a file at the path in the given cmd arg."""
    call_count = [0]

    def side_effect(cmd, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            dest_path = Path(cmd[dest_arg_index])
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(b"fake pg_dump content")
        return _mock_result(0)

    return side_effect


def test_run_dump_only_success(tmp_path: Path) -> None:
    inst = _make_instance()

    def subprocess_side_effect(cmd, **kwargs):
        if "pg_dump" in cmd[0]:
            dest = Path(cmd[cmd.index("-f") + 1])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"fake dump")
        return _mock_result(0)

    with (
        patch.object(
            type(pg_dump.settings),
            "backups_dir",
            new_callable=lambda: property(lambda self: tmp_path),
        ),
        patch("subprocess.run", side_effect=subprocess_side_effect),
    ):
        result = pg_dump.run(inst, "mydb")

    assert result.success is True
    assert result.file_path is not None
    assert result.file_path.suffix == ".dump"


def test_run_dump_only_pg_dump_fails(tmp_path: Path) -> None:
    inst = _make_instance()

    with (
        patch.object(
            type(pg_dump.settings),
            "backups_dir",
            new_callable=lambda: property(lambda self: tmp_path),
        ),
        patch("subprocess.run", return_value=_mock_result(1, stderr="connection refused")),
    ):
        result = pg_dump.run(inst, "mydb")

    assert result.success is False
    assert "pg_dump failed" in result.error_message
    assert "connection refused" in result.error_message


def test_run_dump_only_verify_fails(tmp_path: Path) -> None:
    inst = _make_instance()
    call_count = [0]

    def subprocess_side_effect(cmd, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            dest = Path(cmd[cmd.index("-f") + 1])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"fake dump")
            return _mock_result(0)
        return _mock_result(1)

    with (
        patch.object(
            type(pg_dump.settings),
            "backups_dir",
            new_callable=lambda: property(lambda self: tmp_path),
        ),
        patch("subprocess.run", side_effect=subprocess_side_effect),
    ):
        result = pg_dump.run(inst, "mydb")

    assert result.success is False
    assert "verification failed" in result.error_message


def test_run_dump_with_password(tmp_path: Path) -> None:
    inst = _make_instance(db_password="mypassword")

    captured_envs = []

    def subprocess_side_effect(cmd, **kwargs):
        captured_envs.append(kwargs.get("env", {}))
        if "pg_dump" in cmd[0]:
            dest = Path(cmd[cmd.index("-f") + 1])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"fake dump")
        return _mock_result(0)

    with (
        patch.object(
            type(pg_dump.settings),
            "backups_dir",
            new_callable=lambda: property(lambda self: tmp_path),
        ),
        patch("subprocess.run", side_effect=subprocess_side_effect),
    ):
        result = pg_dump.run(inst, "mydb")

    assert result.success is True
    assert captured_envs[0]["PGPASSWORD"] == "mypassword"


def test_run_with_filestore_success(tmp_path: Path) -> None:
    filestore_dir = tmp_path / "filestore"
    filestore_dir.mkdir()
    (filestore_dir / "file1.dat").write_bytes(b"filestore data")

    inst = _make_instance(include_filestore=True, filestore_path=str(filestore_dir))

    def subprocess_side_effect(cmd, **kwargs):
        dest = Path(cmd[cmd.index("-f") + 1])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake dump")
        return _mock_result(0)

    with (
        patch.object(
            type(pg_dump.settings),
            "backups_dir",
            new_callable=lambda: property(lambda self: tmp_path),
        ),
        patch("subprocess.run", side_effect=subprocess_side_effect),
    ):
        result = pg_dump.run(inst, "mydb")

    assert result.success is True
    assert result.file_path is not None
    assert result.file_path.name.endswith(".tar.gz")

    with tarfile.open(result.file_path, "r:gz") as tar:
        names = tar.getnames()
    assert "db.dump" in names


def test_run_with_filestore_pg_dump_fails(tmp_path: Path) -> None:
    inst = _make_instance(include_filestore=True)

    with (
        patch.object(
            type(pg_dump.settings),
            "backups_dir",
            new_callable=lambda: property(lambda self: tmp_path),
        ),
        patch("subprocess.run", return_value=_mock_result(1, stderr="auth failed")),
    ):
        result = pg_dump.run(inst, "mydb")

    assert result.success is False
    assert "pg_dump failed" in result.error_message


def test_run_with_filestore_missing_filestore_path(tmp_path: Path) -> None:
    inst = _make_instance(include_filestore=True, filestore_path="/nonexistent/filestore")

    def subprocess_side_effect(cmd, **kwargs):
        dest = Path(cmd[cmd.index("-f") + 1])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake dump")
        return _mock_result(0)

    with (
        patch.object(
            type(pg_dump.settings),
            "backups_dir",
            new_callable=lambda: property(lambda self: tmp_path),
        ),
        patch("subprocess.run", side_effect=subprocess_side_effect),
    ):
        result = pg_dump.run(inst, "mydb")

    assert result.success is True


def test_run_with_encrypted_password_decrypt_error(tmp_path: Path) -> None:
    inst = _make_instance()
    inst.db_password_enc = "invalid-encrypted-value"

    with patch.object(
        type(pg_dump.settings), "backups_dir", new_callable=lambda: property(lambda self: tmp_path)
    ):
        result = pg_dump.run(inst, "mydb")

    assert result.success is False
    assert "decrypt" in result.error_message.lower()


def test_discover_databases_success() -> None:
    inst = _make_instance()
    mock_result = _mock_result(0, stdout=" mydb\n anotherdb\n ")

    with patch("subprocess.run", return_value=mock_result):
        dbs = pg_dump.discover_databases(inst)

    assert "mydb" in dbs
    assert "anotherdb" in dbs


def test_discover_databases_failure() -> None:
    inst = _make_instance()
    mock_result = _mock_result(1, stderr="connection refused")

    with patch("subprocess.run", return_value=mock_result):
        dbs = pg_dump.discover_databases(inst)

    assert dbs == []


def test_discover_databases_decrypt_error() -> None:
    inst = _make_instance()
    inst.db_password_enc = "bad-encrypted-value"

    dbs = pg_dump.discover_databases(inst)
    assert dbs == []
