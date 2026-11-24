"""Real-PostgreSQL integration proof for the durable APP-STATE authority.

Owns the CLI/PostgreSQL boundary: external custom-format backup, restore into
the same owned clean target from an offline backup, and fingerprint parity — including the adversarial case
that a schema-only empty target is NOT_READY against a populated authority.

Uses the explicitly assigned App workstream, never an operator database.
Requires pg_dump/pg_restore on PATH and the pinned CI owner receipt.
"""

from __future__ import annotations


import pytest

from application_state.authority import (
    backup_authority,
    database_has_app_state_schema,
    restore_authority,
    compute_fingerprint,
    compare_fingerprints,
)
from application_state.cli import upgrade_to_head
from application_state.config import APPLICATION_STATE_DSN_ENV
from application_state.content.service import create_plan
from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateIsolationError,
)
from application_state.source.service import persist_source_markdown

from tests.application_state.conftest import empty_app_state


@pytest.fixture
def disposable_db(application_state_dsn):
    return application_state_dsn


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


def test_backup_restore_into_same_owned_clean_target_parity(
    disposable_db: str, application_state_database, monkeypatch: pytest.MonkeyPatch, tmp_path
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

    expected = compute_fingerprint(source_dsn)
    with empty_app_state(application_state_database) as target_dsn:
        report = restore_authority(
            target_dsn=target_dsn,
            backup_path=record.backup_path,
            source_dsn=None,
        )
        assert report.ready, f"mismatches: {report.mismatches}"
        mismatches = compare_fingerprints(expected, compute_fingerprint(target_dsn))
        assert not mismatches, f"mismatches: {mismatches}"



def test_restore_rejects_mutated_dump_bytes(
    disposable_db: str, application_state_database, monkeypatch: pytest.MonkeyPatch, tmp_path
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

    with empty_app_state(application_state_database) as target_dsn:
        with pytest.raises(ApplicationStateIntegrityError, match="SHA-256 mismatch"):
            restore_authority(
                target_dsn=target_dsn,
                backup_path=record.backup_path,
                source_dsn=None,
            )
        assert not database_has_app_state_schema(target_dsn)



def test_schema_only_empty_target_is_not_ready(
    disposable_db: str, application_state_database, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_dsn = disposable_db
    upgrade_to_head(dsn=source_dsn)
    _populate(source_dsn, monkeypatch)
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)

    expected = compute_fingerprint(source_dsn)
    with empty_app_state(application_state_database) as target_dsn:
        upgrade_to_head(dsn=target_dsn)  # schema at head, zero domain rows
        mismatches = compare_fingerprints(expected, compute_fingerprint(target_dsn))
        assert mismatches
        assert any("content.work_object" in m for m in mismatches)
        assert any("source.revision" in m for m in mismatches)



def test_restore_rejects_non_empty_target(
    disposable_db: str, application_state_database, monkeypatch: pytest.MonkeyPatch, tmp_path
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
