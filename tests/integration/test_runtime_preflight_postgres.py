from __future__ import annotations

import os
from pathlib import Path

import pytest

from apps.live_control_server.config import (
    WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV,
    WORLD_GRAPH_AUTHORITY_ENV,
)
from apps.live_control_server.services.runtime_preflight import run_runtime_preflight
from application_state.config import APPLICATION_STATE_DSN_ENV
from tests._cutover_d3a_blocker_safe_fixtures import (
    TEST_DSN_ENV,
    ensure_migrated,
    require_test_dsn,
    truncate_dungeonmind,
)


@pytest.fixture
def cutover_test_dsn() -> str | None:
    return os.environ.get(TEST_DSN_ENV, "").strip() or None


def _configure_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    app_state_dsn: str | None,
    world_dsn: str | None,
) -> None:
    monkeypatch.setenv(WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")
    if app_state_dsn:
        monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, app_state_dsn)
    else:
        monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    if world_dsn:
        monkeypatch.setenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, world_dsn)
    else:
        monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)


def _snapshot_dungeonmind_counters(dsn: str) -> dict[str, int]:
    import psycopg

    counters = (
        "SELECT count(*) FROM dungeonmind.world_graph_heads",
        "SELECT count(*) FROM dungeonmind.existing_world_adoptions",
        "SELECT count(*) FROM dungeonmind.reviewed_world_initializations",
    )
    with psycopg.connect(dsn) as conn:
        return {query: conn.execute(query).fetchone()[0] for query in counters}


def test_postgres_preflight_read_only_with_application_state(
    application_state_dsn: str,
    cutover_test_dsn: str | None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    if not cutover_test_dsn:
        pytest.skip(f"{TEST_DSN_ENV} not set")

    _configure_env(
        monkeypatch,
        app_state_dsn=application_state_dsn,
        world_dsn=cutover_test_dsn,
    )

    ingest_root = tmp_path / "out/graph_memory/runs"
    ingest_root.mkdir(parents=True)

    before = _snapshot_dungeonmind_counters(cutover_test_dsn)

    for _ in range(2):
        report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
        assert report.status in {"READY", "NOT READY"}

        world = next(check for check in report.checks if check.id == "dungeonmind_world")
        assert world.status in {
            "READY",
            "EMPTY",
            "INTEGRITY_ERROR",
            "NOT_READY",
            "NOT_CONFIGURED",
            "UNAVAILABLE",
        }

        after = _snapshot_dungeonmind_counters(cutover_test_dsn)
        assert after == before


def test_require_world_missing_on_fresh_database(
    application_state_dsn: str,
    cutover_test_dsn: str | None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fresh migrated DB + --require-world without mocking list_world_heads.

    With the post-#50 enumeration pin, world discovery succeeds on an empty
    database and reports ``NOT_READY`` with ``required_world=eldyrwild``.
    """
    if not cutover_test_dsn:
        pytest.skip(f"{TEST_DSN_ENV} not set")

    _configure_env(
        monkeypatch,
        app_state_dsn=application_state_dsn,
        world_dsn=cutover_test_dsn,
    )

    ingest_root = tmp_path / "out/graph_memory/runs"
    ingest_root.mkdir(parents=True)

    ensure_migrated(cutover_test_dsn)
    truncate_dungeonmind(cutover_test_dsn)

    report = run_runtime_preflight(
        repo_root=tmp_path,
        require_world="eldyrwild",
        load_env=False,
    )

    world = next(check for check in report.checks if check.id == "dungeonmind_world")
    assert report.status == "NOT READY"
    assert world.status == "NOT_READY"
    assert world.details.get("required_world") == "eldyrwild"


def test_dungeonmind_unavailable_dsn(
    application_state_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unreachable authority DSN maps to UNAVAILABLE through the full repository stack."""
    _configure_env(
        monkeypatch,
        app_state_dsn=application_state_dsn,
        world_dsn="postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:59999/dungeonmind",
    )

    ingest_root = tmp_path / "out/graph_memory/runs"
    ingest_root.mkdir(parents=True)

    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)

    world = next(check for check in report.checks if check.id == "dungeonmind_world")
    assert report.status == "NOT READY"
    assert world.status == "UNAVAILABLE"


def test_cutover_dsn_fixture_guard() -> None:
    dsn = os.environ.get(TEST_DSN_ENV, "").strip()
    if not dsn:
        pytest.skip(f"{TEST_DSN_ENV} not set")
    assert require_test_dsn() == dsn
