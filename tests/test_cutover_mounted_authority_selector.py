"""CUTOVER D.3A: mounted World Graph authority selector / factory matrix."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server import config
from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
    DungeonMindWorldGraphAuthorityAdapter,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
    DungeonMindWorldGraphInitializationAdapter,
)
from apps.live_control_server.ports.world_graph_authority_access import (
    get_world_graph_authority,
)
from apps.live_control_server.ports.world_graph_initialization_access import (
    get_world_graph_initialization_authority,
)


def test_unset_authority_defaults_to_dungeonmind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.WORLD_GRAPH_AUTHORITY_ENV, raising=False)
    assert config.world_graph_authority_mode() == config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND


@pytest.mark.parametrize(
    "raw",
    [
        config.WORLD_GRAPH_AUTHORITY_BUDDY_FILES,
        config.WORLD_GRAPH_AUTHORITY_QUIESCED,
        "bogus",
    ],
)
def test_retired_or_unknown_authority_fails_closed(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.setenv(config.WORLD_GRAPH_AUTHORITY_ENV, raw)
    with pytest.raises(config.WorldGraphAuthorityConfigurationError):
        config.world_graph_authority_mode()


def test_factories_are_dungeonmind_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prod = tmp_path / "prod"
    prod.mkdir()
    monkeypatch.delenv(config.WORLD_GRAPH_AUTHORITY_ENV, raising=False)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(prod))
    authority = get_world_graph_authority()
    init = get_world_graph_initialization_authority()
    assert isinstance(authority, DungeonMindWorldGraphAuthorityAdapter)
    assert isinstance(init, DungeonMindWorldGraphInitializationAdapter)


def test_alternate_world_root_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prod = tmp_path / "prod"
    other = tmp_path / "other"
    prod.mkdir()
    other.mkdir()
    monkeypatch.setenv(
        config.WORLD_GRAPH_AUTHORITY_ENV, config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(prod))
    with pytest.raises(config.WorldGraphAuthorityConfigurationError, match="alternate"):
        get_world_graph_authority(world_root=other)
    with pytest.raises(config.WorldGraphAuthorityConfigurationError, match="alternate"):
        get_world_graph_initialization_authority(world_root=other)


def test_buddy_files_mode_cannot_select_factory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prod = tmp_path / "prod"
    prod.mkdir()
    monkeypatch.setenv(
        config.WORLD_GRAPH_AUTHORITY_ENV, config.WORLD_GRAPH_AUTHORITY_BUDDY_FILES
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(prod))
    with pytest.raises(config.WorldGraphAuthorityConfigurationError):
        get_world_graph_authority()
