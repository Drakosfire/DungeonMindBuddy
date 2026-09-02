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
from tests._cutover_d3a_blocker_safe_fixtures import TEST_DSN_ENV, require_test_dsn


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

    import psycopg

    with psycopg.connect(cutover_test_dsn) as conn:
        before_worlds = conn.execute(
            "SELECT count(*) FROM dungeonmind.world_graph_heads"
        ).fetchone()[0]

    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    assert report.status in {"READY", "NOT READY"}

    world = next(check for check in report.checks if check.id == "dungeonmind_world")
    assert world.status in {"READY", "EMPTY", "INTEGRITY_ERROR", "NOT_READY", "UNAVAILABLE"}

    with psycopg.connect(cutover_test_dsn) as conn:
        after_worlds = conn.execute(
            "SELECT count(*) FROM dungeonmind.world_graph_heads"
        ).fetchone()[0]
    assert after_worlds == before_worlds


def test_require_world_missing_on_fresh_database(
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

    report = run_runtime_preflight(
        repo_root=tmp_path,
        require_world="eldyrwild",
        load_env=False,
    )
    world = next(check for check in report.checks if check.id == "dungeonmind_world")
    if world.status == "READY" and "eldyrwild" in str(world.details.get("worlds", "")):
        pytest.skip("eldyrwild already present in configured test database")
    assert report.status == "NOT READY"
    assert world.status == "NOT_READY"


def test_cutover_dsn_fixture_guard() -> None:
    dsn = os.environ.get(TEST_DSN_ENV, "").strip()
    if not dsn:
        pytest.skip(f"{TEST_DSN_ENV} not set")
    assert require_test_dsn() == dsn
