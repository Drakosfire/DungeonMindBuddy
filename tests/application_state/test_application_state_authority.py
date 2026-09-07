"""Owning-boundary tests for the durable APP-STATE authority fingerprint.

These tests prove the fingerprint is deterministic, content-sensitive,
secret-free, and isolation-guarded. They use real disposable PostgreSQL
databases (the established application_state test pattern), never the
operator database.
"""

from __future__ import annotations

import pytest

from application_state.authority import (
    ApplicationStateFingerprint,
    DomainFingerprint,
    assert_authority_target_isolated,
    compare_fingerprints,
    compute_fingerprint,
    database_has_app_state_schema,
    parse_sha256_sidecar,
    redact_dsn,
    redact_secrets,
    restore_authority,
    verify_backup_digest,
)
from application_state.config import TEST_ADMIN_DSN_ENV
from application_state.content.service import create_plan
from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateIsolationError,
    ApplicationStateMigrationError,
)
from application_state.naming import assert_safe_application_state_database_name
from application_state.source.service import persist_source_markdown

_DEFAULT_ADMIN_DSN = "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/postgres"


def _admin_dsn() -> str:
    import os

    return os.environ.get(TEST_ADMIN_DSN_ENV, "").strip() or _DEFAULT_ADMIN_DSN


def _replace_database(dsn: str, database: str) -> str:
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(dsn)
    return urlunparse(parsed._replace(path=f"/{database}"))


def _create_database(admin_dsn: str, name: str) -> None:
    import psycopg
    from psycopg import sql

    assert_safe_application_state_database_name(name)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def _drop_database(admin_dsn: str, name: str) -> None:
    import psycopg
    from psycopg import sql

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
            (name,),
        )
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name)))


def _fingerprint(domains: dict[str, tuple[int, str]], digest: str = "combined") -> ApplicationStateFingerprint:
    return ApplicationStateFingerprint(
        schema="dmb_application_state_fingerprint_v1",
        alembic_current="head1",
        alembic_head="head1",
        domains=tuple(
            DomainFingerprint(name=name, row_count=rows, digest=dig)
            for name, (rows, dig) in domains.items()
        ),
        digest=digest,
    )


def test_redact_dsn_removes_password() -> None:
    dsn = "postgresql://buddy:supersecret@127.0.0.1:54331/dungeonbuddy_application_state"
    redacted = redact_dsn(dsn)
    assert "supersecret" not in redacted
    assert "127.0.0.1:54331" in redacted
    assert "dungeonbuddy_application_state" in redacted


def test_redact_secrets_scrubs_dsn_and_password() -> None:
    dsn = "postgresql://buddy:hunter2@127.0.0.1:54331/dungeonbuddy_application_state"
    text = f"failed connecting to {dsn}: auth error for hunter2"
    redacted = redact_secrets(text, dsn)
    assert "hunter2" not in redacted
    assert dsn not in redacted


def test_isolation_rejects_world_authority_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    world = "postgresql://dungeonmind:x@127.0.0.1:54330/dungeonmind_cutover_live"
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", world)
    with pytest.raises(ApplicationStateIsolationError):
        assert_authority_target_isolated(world)


def test_isolation_rejects_cutover_live_name_without_env() -> None:
    with pytest.raises(ApplicationStateIsolationError):
        assert_authority_target_isolated(
            "postgresql://buddy:x@127.0.0.1:54331/dungeonmind_cutover_live"
        )


def test_isolation_rejects_source_equals_target() -> None:
    dsn = "postgresql://buddy:x@127.0.0.1:54331/dungeonbuddy_application_state"
    with pytest.raises(ApplicationStateIsolationError, match="differ from the source"):
        assert_authority_target_isolated(dsn, source_dsn=dsn)


def test_isolation_allows_distinct_buddy_targets() -> None:
    source = "postgresql://buddy:x@127.0.0.1:54331/dungeonbuddy_application_state"
    target = "postgresql://buddy:x@127.0.0.1:54331/dungeonbuddy_application_state_witness"
    assert_authority_target_isolated(target, source_dsn=source)


def test_compare_fingerprints_reports_domain_mismatch() -> None:
    source = _fingerprint({"ingest.run": (53, "aaa"), "play.run": (2, "bbb")})
    target = _fingerprint({"ingest.run": (0, "ccc"), "play.run": (2, "bbb")})
    mismatches = compare_fingerprints(source, target)
    assert len(mismatches) == 1
    assert "ingest.run" in mismatches[0]
    assert "play.run" not in mismatches[0]


def test_compare_fingerprints_identical_is_empty() -> None:
    fp = _fingerprint({"ingest.run": (53, "aaa")})
    assert compare_fingerprints(fp, fp) == []


def test_fingerprint_json_round_trip() -> None:
    fp = _fingerprint({"ingest.run": (53, "aaa"), "play.run": (2, "bbb")})
    restored = ApplicationStateFingerprint.from_json_dict(fp.to_json_dict())
    assert restored == fp


def test_fingerprint_deterministic_on_empty_head(application_state_dsn: str) -> None:
    first = compute_fingerprint(application_state_dsn)
    second = compute_fingerprint(application_state_dsn)
    assert first.digest == second.digest
    assert first.alembic_current == first.alembic_head
    assert {d.name for d in first.domains} == {
        "content.work_object",
        "content.work_revision",
        "content.working_copy",
        "play.run",
        "play.run_manifest",
        "play.active_run",
        "ingest.run",
        "source.artifact",
        "source.revision",
    }
    assert all(d.row_count == 0 for d in first.domains)


def test_fingerprint_changes_with_content_and_source_rows(
    application_state_dsn: str,
) -> None:
    before = compute_fingerprint(application_state_dsn)
    create_plan(
        title="Fingerprint witness plan",
        campaign_id="eldyrwild",
        target_session=27,
        target_relpath="Plans/Session 27 - Plan.md",
    )
    persist_source_markdown(
        source_artifact_id="src:fingerprint-witness",
        source_domain="session_recap",
        campaign_id="eldyrwild",
        session_id="session-26",
        world_id=None,
        markdown="# Witness\n",
    )
    after = compute_fingerprint(application_state_dsn)
    assert after.digest != before.digest
    counts = {d.name: d.row_count for d in after.domains}
    assert counts["content.work_object"] == 1
    assert counts["source.artifact"] == 1
    assert counts["source.revision"] == 1


def test_fingerprint_stable_across_repeated_computation_with_rows(
    application_state_dsn: str,
) -> None:
    create_plan(title="Stable", campaign_id="eldyrwild")
    first = compute_fingerprint(application_state_dsn)
    second = compute_fingerprint(application_state_dsn)
    assert first == second


def test_fingerprint_requires_schema_at_head() -> None:
    admin = _admin_dsn()
    import uuid

    name = f"dungeonbuddy_app_state_test_{uuid.uuid4().hex[:12]}"
    _create_database(admin, name)
    dsn = _replace_database(admin, name)
    try:
        assert not database_has_app_state_schema(dsn)
        with pytest.raises(ApplicationStateMigrationError):
            compute_fingerprint(dsn)
    finally:
        _drop_database(admin, name)


def test_database_has_app_state_schema(application_state_dsn: str) -> None:
    assert database_has_app_state_schema(application_state_dsn)


def test_parse_sha256_sidecar_reads_sha256sum_format() -> None:
    digest = "a" * 64
    assert parse_sha256_sidecar(f"{digest}  authority.dump\n") == digest


def test_parse_sha256_sidecar_rejects_garbage() -> None:
    with pytest.raises(ApplicationStateIntegrityError, match="64-character"):
        parse_sha256_sidecar("not-a-digest")


def test_verify_backup_digest_rejects_missing_sidecar(tmp_path) -> None:
    dump = tmp_path / "authority.dump"
    dump.write_bytes(b"payload")
    with pytest.raises(ApplicationStateIntegrityError, match="sidecar missing"):
        verify_backup_digest(dump)


def test_verify_backup_digest_rejects_mutated_dump(tmp_path) -> None:
    dump = tmp_path / "authority.dump"
    dump.write_bytes(b"payload")
    sidecar = tmp_path / "authority.dump.sha256"
    sidecar.write_text(f"{'b' * 64}  authority.dump\n", encoding="utf-8")
    with pytest.raises(ApplicationStateIntegrityError, match="mismatch"):
        verify_backup_digest(dump)


def test_verify_backup_digest_accepts_matching_sidecar(tmp_path) -> None:
    import hashlib

    dump = tmp_path / "authority.dump"
    dump.write_bytes(b"payload")
    digest = hashlib.sha256(b"payload").hexdigest()
    (tmp_path / "authority.dump.sha256").write_text(f"{digest}  authority.dump\n")
    assert verify_backup_digest(dump) == digest


def test_verify_backup_digest_explicit_digest_must_match_bytes(tmp_path) -> None:
    dump = tmp_path / "authority.dump"
    dump.write_bytes(b"payload")
    import hashlib

    real = hashlib.sha256(b"payload").hexdigest()
    assert verify_backup_digest(dump, expected_sha256=real) == real
    with pytest.raises(ApplicationStateIntegrityError, match="mismatch"):
        verify_backup_digest(dump, expected_sha256="c" * 64)


def test_restore_refuses_unverified_dump_before_touching_target(
    application_state_dsn: str, tmp_path
) -> None:
    dump = tmp_path / "authority.dump"
    dump.write_bytes(b"not-a-real-dump")
    with pytest.raises(ApplicationStateIntegrityError, match="sidecar missing"):
        restore_authority(target_dsn=application_state_dsn, backup_path=dump)


def test_restore_refuses_missing_fingerprint_sidecar(
    application_state_dsn: str, tmp_path
) -> None:
    dump = tmp_path / "authority.dump"
    dump.write_bytes(b"payload")
    import hashlib

    digest = hashlib.sha256(b"payload").hexdigest()
    (tmp_path / "authority.dump.sha256").write_text(f"{digest}  authority.dump\n")
    with pytest.raises(ApplicationStateIntegrityError, match="fingerprint sidecar missing"):
        restore_authority(target_dsn=application_state_dsn, backup_path=dump)


def _load_authority_cli():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "application_state_authority.py"
    spec = importlib.util.spec_from_file_location("application_state_authority_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_without_expected_fingerprint_is_observed_never_ready(
    application_state_dsn: str, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = _load_authority_cli()
    code = cli.main(["check", "--dsn", application_state_dsn])
    captured = capsys.readouterr()
    assert code == 0
    assert "READY:" not in captured.out
    assert "OBSERVED:" in captured.out


def test_check_with_matching_fingerprint_is_ready(
    application_state_dsn: str, capsys: pytest.CaptureFixture[str], tmp_path
) -> None:
    fp = compute_fingerprint(application_state_dsn)
    expected = tmp_path / "expected.json"
    expected.write_text(fp.to_json(), encoding="utf-8")
    cli = _load_authority_cli()
    code = cli.main(
        ["check", "--dsn", application_state_dsn, "--expect-fingerprint", str(expected)]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "READY: live fingerprint matches expected" in captured.out


def test_check_with_stale_fingerprint_is_not_ready(
    application_state_dsn: str, capsys: pytest.CaptureFixture[str], tmp_path
) -> None:
    before = compute_fingerprint(application_state_dsn)
    expected = tmp_path / "expected.json"
    expected.write_text(before.to_json(), encoding="utf-8")
    create_plan(title="Post-fingerprint mutation", campaign_id="eldyrwild")
    cli = _load_authority_cli()
    code = cli.main(
        ["check", "--dsn", application_state_dsn, "--expect-fingerprint", str(expected)]
    )
    captured = capsys.readouterr()
    assert code == 2
    assert "NOT_READY:" in captured.err
    assert "READY:" not in captured.out
