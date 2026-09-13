from __future__ import annotations

import pytest

from src.graph_memory.extraction.stage4j_rehearsal_guards import (
    Stage4JRehearsalGuardError,
    assert_rehearsal_world_db_url,
)


def test_refuses_live_cutover_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DMB_STAGE4J_ALLOW_LIVE_WORLD", raising=False)
    with pytest.raises(Stage4JRehearsalGuardError, match="54330"):
        assert_rehearsal_world_db_url(
            "postgresql://dungeonmind@127.0.0.1:54330/dungeonmind_cutover_live"
        )


def test_allows_rehearsal_db(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DMB_STAGE4J_ALLOW_LIVE_WORLD", raising=False)
    assert_rehearsal_world_db_url(
        "postgresql://dungeonmind@127.0.0.1:54329/dungeonmind_stage4j_rehearsal"
    )


def test_live_override_requires_explicit_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DMB_STAGE4J_ALLOW_LIVE_WORLD", "1")
    assert_rehearsal_world_db_url(
        "postgresql://dungeonmind@127.0.0.1:54330/dungeonmind_cutover_live"
    )
