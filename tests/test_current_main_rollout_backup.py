from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tarfile

import pytest


@pytest.fixture
def backup_module():
    path = (
        Path(__file__).resolve().parents[1] / "scripts/current_main_rollout_backup.py"
    )
    spec = importlib.util.spec_from_file_location("rollout_backup_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_schema_gate_and_private_archive_include_all_preservation_roots(
    backup_module, tmp_path, monkeypatch
):
    b = backup_module
    assert b.BUDDY_SCHEMA == "20261007_0018"
    assert b.CORE_SCHEMA == "0013_adopted_withdrawal_v1"
    monkeypatch.setattr(b, "STATE", tmp_path / "state")
    monkeypatch.setattr(b, "CONFIG", tmp_path / "config/buddy.env")
    monkeypatch.setattr(b, "SHARED_ENV", tmp_path / "config/shared.env.development")
    monkeypatch.setattr(b, "RUNTIME", tmp_path / "runtime")
    monkeypatch.setattr(b, "MANAGED_ROOT", tmp_path / "managed")
    monkeypatch.setattr(b, "DMS_ROOT", tmp_path / "dms")
    for source, _name in b._state_subjects():
        if source.suffix or source.name.startswith("."):
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("synthetic-preserved-bytes")
        else:
            source.mkdir(parents=True, exist_ok=True)
            (source / "fixture.txt").write_text("synthetic-preserved-bytes")
    archive = tmp_path / "preserved.tar"
    count = b._archive_state(archive)
    with tarfile.open(archive) as tar:
        names = tar.getnames()
        assert count == len(names)
        for _source, name in b._state_subjects():
            assert name in names
        for name in [
            "dms/.env.development",
            "dms/serviceAccountKey.json",
            "managed/out/registries/world_containers.json",
        ]:
            assert tar.extractfile(name).read() == b"synthetic-preserved-bytes"
    (b.DMS_ROOT / "serviceAccountKey.json").unlink()
    with pytest.raises(RuntimeError, match="absent"):
        b._archive_state(tmp_path / "incomplete.tar")


def test_backup_cli_rejects_wrong_source_head_before_destination(
    backup_module, tmp_path, monkeypatch
):
    b = backup_module
    identities = {
        label: {"host": "127.0.0.1", "port": port, "system_identifier": label}
        for label, port in [("buddy", "54331"), ("core", "54330")]
    }
    monkeypatch.setattr(b, "_expected_identities", lambda: identities)
    monkeypatch.setattr(b, "_configured_dsn", lambda *_args: "synthetic-dsn")

    def preflight(_dsn, _name, _table, expected, _identity):
        assert expected in {"20261007_0018", "0013_adopted_withdrawal_v1"}
        raise RuntimeError(
            "database identity or pre-migration schema differs from the lease"
        )

    monkeypatch.setattr(b, "_database_preflight", preflight)
    monkeypatch.setattr(
        b,
        "_private_root",
        lambda: pytest.fail("backup destination created before schema checks"),
    )
    monkeypatch.setattr(sys, "argv", ["backup", "--execute"])
    with pytest.raises(RuntimeError, match="pre-migration schema"):
        b.main()


@pytest.mark.parametrize(
    "actual_head", ["0007_reviewed_world_init", "0014_adopted_withdrawal_v2"]
)
def test_actual_preflight_rejects_outside_exact_core_source_pair(
    backup_module, monkeypatch, actual_head
):
    b = backup_module

    class Result:
        def __init__(self, value):
            self.value = value

        def fetchone(self):
            return (self.value,)

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def execute(self, statement):
            values = {
                "SELECT current_database()": "dungeonmind_cutover_live",
                "SELECT version_num FROM dungeonmind.alembic_version": actual_head,
                "SHOW server_version_num": "160011",
                "SELECT pg_database_size(current_database())": 1024,
                "SELECT system_identifier FROM pg_control_system()": "synthetic-cluster",
            }
            return Result(values[statement])

    monkeypatch.setattr(b.psycopg, "connect", lambda *_args, **_kwargs: Connection())
    with pytest.raises(RuntimeError, match="pre-migration schema"):
        b._database_preflight(
            "postgresql://synthetic@127.0.0.1:54330/dungeonmind_cutover_live",
            "dungeonmind_cutover_live",
            "dungeonmind.alembic_version",
            "0013_adopted_withdrawal_v1",
            {
                "host": "127.0.0.1",
                "port": "54330",
                "system_identifier": "synthetic-cluster",
            },
        )


def test_source_environment_snapshot_records_rollback_ref_and_link(
    backup_module, tmp_path, monkeypatch
):
    import subprocess

    b = backup_module
    for label in ["buddy", "dms"]:
        root = tmp_path / label
        root.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "fixture"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "fixture@example.test"],
            cwd=root,
            check=True,
        )
        (root / "pyproject.toml").write_text("synthetic package")
        (root / "uv.lock").write_text("synthetic lock")
        (root / ".gitignore").write_text(".venv\n.venv-stable/\n")
        (root / ".venv-stable").mkdir()
        (root / ".venv").symlink_to(".venv-stable")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        monkeypatch.setattr(b, "RUNTIME" if label == "buddy" else "DMS_ROOT", root)
    record = b._source_environment_snapshot()
    for value in record.values():
        assert value["branch"] == "fixture"
        assert value["head"] and value["tree"]
        assert value["venv_link"] == ".venv-stable"
        assert value["venv_resolved"].endswith("/.venv-stable")
    (b.RUNTIME / "pyproject.toml").write_text("unreviewed source")
    with pytest.raises(RuntimeError, match="dirty"):
        b._source_environment_snapshot()
