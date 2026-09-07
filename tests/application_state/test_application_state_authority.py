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
    redact_dsn,
    redact_secrets,
)
from application_state.config import TEST_ADMIN_DSN_ENV
from application_state.content.service import create_plan
from application_state.errors import (
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
