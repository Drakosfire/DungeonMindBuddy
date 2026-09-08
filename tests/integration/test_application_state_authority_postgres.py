"""Real-PostgreSQL integration proof for the durable APP-STATE authority.

Owns the CLI/PostgreSQL boundary: external custom-format backup, restore into
a second clean target, and fingerprint parity — including the adversarial case
that a schema-only empty target is NOT_READY against a populated authority.

Uses disposable logical databases on the test admin server, never the operator
database. Requires pg_dump/pg_restore on PATH and a reachable test server
(DMB_APPLICATION_STATE_TEST_DATABASE_URL or the local dev default).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest
from psycopg import sql

from application_state.authority import (
    backup_authority,
    database_has_app_state_schema,
    restore_authority,
    verify_parity,
)
from application_state.cli import upgrade_to_head
from application_state.config import APPLICATION_STATE_DSN_ENV, TEST_ADMIN_DSN_ENV
from application_state.content.service import create_plan
from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateIsolationError,
)
from application_state.naming import assert_safe_application_state_database_name
from application_state.source.service import persist_source_markdown

_DEFAULT_ADMIN_DSN = "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/postgres"


def _admin_dsn() -> str:
    return os.environ.get(TEST_ADMIN_DSN_ENV, "").strip() or _DEFAULT_ADMIN_DSN


def _replace_database(dsn: str, database: str) -> str:
    parsed = urlparse(dsn)
    return urlunparse(parsed._replace(path=f"/{database}"))


def _create_database(admin_dsn: str, name: str) -> None:
    assert_safe_application_state_database_name(name)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def _drop_database(admin_dsn: str, name: str) -> None:
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
            (name,),
        )
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name)))


@pytest.fixture
def disposable_db() -> Iterator[str]:
    admin = _admin_dsn()
    name = f"dungeonbuddy_app_state_test_{uuid.uuid4().hex[:12]}"
    try:
        _create_database(admin, name)
    except Exception as exc:
        pytest.fail(
            "authority integration tests require real disposable PostgreSQL; "
            f"could not create {name}: {exc}"
        )
    try:
        yield _replace_database(admin, name)
    finally:
        _drop_database(admin, name)


def _populate(dsn: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate through public service seams only (no fixture SQL inserts)."""
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
    create_plan(
        title="Authority witness plan",
        campaign_id="eldyrwild",
        target_session=27,
        target_relpath="Plans/Session 27 - Plan.md",
    )
    persist_source_markdown(
        source_artifact_id="src:authority-witness",
        source_domain="session_recap",
        campaign_id="eldyrwild",
        session_id="session-26",
        world_id=None,
        markdown="# Witness\n\nAuthority parity body.\n",
    )


def test_backup_restore_into_second_clean_target_parity(
    disposable_db: str, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    source_dsn = disposable_db
    upgrade_to_head(dsn=source_dsn)
    _populate(source_dsn, monkeypatch)
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)

    record = backup_authority(
        source_dsn=source_dsn, out_path=tmp_path / "authority.dump"
    )
    assert record.backup_sha256
    assert (tmp_path / "authority.dump.sha256").exists()
    assert (tmp_path / "authority.dump.fingerprint.json").exists()

    admin = _admin_dsn()
    target_name = f"dungeonbuddy_app_state_test_{uuid.uuid4().hex[:12]}"
    _create_database(admin, target_name)
    target_dsn = _replace_database(admin, target_name)
    try:
        report = restore_authority(
            target_dsn=target_dsn,
            backup_path=record.backup_path,
            source_dsn=source_dsn,
        )
        assert report.ready, f"mismatches: {report.mismatches}"
        ready, mismatches, _, _ = verify_parity(
            source_dsn=source_dsn, target_dsn=target_dsn
        )
        assert ready, f"mismatches: {mismatches}"
    finally:
        _drop_database(admin, target_name)


def test_restore_rejects_mutated_dump_bytes(
    disposable_db: str, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    source_dsn = disposable_db
    upgrade_to_head(dsn=source_dsn)
    _populate(source_dsn, monkeypatch)
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    record = backup_authority(
        source_dsn=source_dsn, out_path=tmp_path / "authority.dump"
    )
    dump = tmp_path / "authority.dump"
    dump.write_bytes(dump.read_bytes() + b"\x00tamper")

    admin = _admin_dsn()
    target_name = f"dungeonbuddy_app_state_test_{uuid.uuid4().hex[:12]}"
    _create_database(admin, target_name)
    target_dsn = _replace_database(admin, target_name)
    try:
        with pytest.raises(ApplicationStateIntegrityError, match="SHA-256 mismatch"):
            restore_authority(
                target_dsn=target_dsn,
                backup_path=record.backup_path,
                source_dsn=source_dsn,
            )
        assert not database_has_app_state_schema(target_dsn)
    finally:
        _drop_database(admin, target_name)


def test_schema_only_empty_target_is_not_ready(
    disposable_db: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_dsn = disposable_db
    upgrade_to_head(dsn=source_dsn)
    _populate(source_dsn, monkeypatch)
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)

    admin = _admin_dsn()
    target_name = f"dungeonbuddy_app_state_test_{uuid.uuid4().hex[:12]}"
    _create_database(admin, target_name)
    target_dsn = _replace_database(admin, target_name)
    try:
        upgrade_to_head(dsn=target_dsn)  # schema at head, zero domain rows
        ready, mismatches, _, _ = verify_parity(
            source_dsn=source_dsn, target_dsn=target_dsn
        )
        assert not ready
        assert any("content.work_object" in m for m in mismatches)
        assert any("source.revision" in m for m in mismatches)
    finally:
        _drop_database(admin, target_name)


def test_restore_rejects_non_empty_target(
    disposable_db: str, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    source_dsn = disposable_db
    upgrade_to_head(dsn=source_dsn)
    _populate(source_dsn, monkeypatch)
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    record = backup_authority(
        source_dsn=source_dsn, out_path=tmp_path / "authority.dump"
    )
    with pytest.raises(ApplicationStateIntegrityError, match="clean target"):
        restore_authority(target_dsn=source_dsn, backup_path=record.backup_path)


def test_world_authority_dsn_is_blocked_before_any_restore(tmp_path) -> None:
    world = "postgresql://dungeonmind:x@127.0.0.1:54330/dungeonmind_cutover_live"
    with pytest.raises(ApplicationStateIsolationError):
        restore_authority(
            target_dsn=world,
            backup_path=tmp_path / "irrelevant.dump",
        )
