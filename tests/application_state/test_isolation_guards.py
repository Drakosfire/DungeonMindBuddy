from __future__ import annotations

import pytest

from application_state.errors import ApplicationStateIsolationError, ApplicationStateUnavailableError
from application_state.naming import (
    assert_dsn_is_not_world_graph,
    assert_safe_application_state_dsn,
    database_name_from_dsn,
)


def test_denylist_refuses_world_and_cutover_names() -> None:
    with pytest.raises(ApplicationStateIsolationError):
        assert_safe_application_state_dsn(
            "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind"
        )
    with pytest.raises(ApplicationStateIsolationError):
        assert_safe_application_state_dsn(
            "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind_cutover_live"
        )
    with pytest.raises(ApplicationStateIsolationError):
        assert_safe_application_state_dsn(
            "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/postgres"
        )


def test_world_graph_dsn_cannot_be_reused(monkeypatch: pytest.MonkeyPatch) -> None:
    world = "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind_cutover_live"
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", world)
    with pytest.raises(ApplicationStateIsolationError):
        assert_dsn_is_not_world_graph(
            world,
            world_dsns={"DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL": world},
        )


def test_runtime_loader_refuses_world_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    from application_state.config import load_runtime_dsn

    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind",
    )
    with pytest.raises(ApplicationStateUnavailableError):
        load_runtime_dsn()


def test_product_name_is_admitted() -> None:
    name = database_name_from_dsn(
        "postgresql://buddy@127.0.0.1:54329/dungeonbuddy_application_state"
    )
    assert name == "dungeonbuddy_application_state"
    assert_safe_application_state_dsn(
        "postgresql://buddy@127.0.0.1:54329/dungeonbuddy_application_state"
    )


def test_missing_runtime_dsn_is_named_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from application_state.config import load_runtime_dsn, plan_kind_uses_postgres

    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
    assert plan_kind_uses_postgres() is True
    with pytest.raises(ApplicationStateUnavailableError):
        load_runtime_dsn()
