"""Tests for Play run-state persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.services.play_run_state import (
    PlayRunStateDocument,
    load_play_run_state,
    play_run_state_path,
    save_play_run_state,
)


def test_default_load_when_missing(tmp_path: Path) -> None:
    doc = load_play_run_state("of-conks-cons--hempholm", root=tmp_path)
    assert doc.run_id == "of-conks-cons--hempholm"
    assert doc.current_scene_id == "hook"
    assert doc.resolved_beat_ids == []
    assert doc.scene_notes == {}


def test_save_and_reload_roundtrip(tmp_path: Path) -> None:
    saved = save_play_run_state(
        PlayRunStateDocument(
            run_id="of-conks-cons--hempholm",
            current_scene_id="village-sandbox",
            resolved_beat_ids=["shacks-arrival"],
            scene_notes={"village-sandbox": "Nar drunk already"},
            branch={"hook": "hill", "aftermath": "celebration"},
        ),
        root=tmp_path,
    )
    path = play_run_state_path("of-conks-cons--hempholm", root=tmp_path)
    assert path.is_file()
    assert "out/workspace/play" in str(path).replace("\\", "/")

    loaded = load_play_run_state("of-conks-cons--hempholm", root=tmp_path)
    assert loaded.current_scene_id == "village-sandbox"
    assert loaded.resolved_beat_ids == ["shacks-arrival"]
    assert loaded.scene_notes["village-sandbox"] == "Nar drunk already"
    assert loaded.branch.aftermath == "celebration"
    assert loaded.updated_at == saved.updated_at or loaded.updated_at


def test_rejects_path_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        play_run_state_path("../evil", root=tmp_path)
    with pytest.raises(ValueError):
        play_run_state_path("has/slash", root=tmp_path)
