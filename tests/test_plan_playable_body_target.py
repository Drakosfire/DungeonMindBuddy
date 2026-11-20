"""Server side of the shared Plan Playable body codec vectors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.services.plan_playable_body_target import (
    PlayableBodyTargetError,
    PlayableTarget,
    resolve_playable_body_target,
    selected_playable_source_for_read,
)


_VECTORS = Path(__file__).parent / "fixtures" / "plan_playable_body_codec_v1.json"


@pytest.mark.parametrize("vector", json.loads(_VECTORS.read_text(encoding="utf-8"))["vectors"], ids=lambda vector: vector["name"])
def test_shared_playable_body_codec_vectors(vector: dict[str, object]) -> None:
    target = vector["target"]
    expected = vector["expected"]
    assert isinstance(target, dict)
    assert isinstance(expected, dict)

    if not expected["available"]:
        with pytest.raises(PlayableBodyTargetError):
            resolve_playable_body_target(
                str(vector["draft_markdown"]),
                PlayableTarget(kind=str(target["kind"]), id=str(target["id"])),  # type: ignore[arg-type]
            )
        return

    resolved = resolve_playable_body_target(
        str(vector["draft_markdown"]),
        PlayableTarget(kind=str(target["kind"]), id=str(target["id"])),  # type: ignore[arg-type]
    )
    assert resolved.target_body_markdown == expected["body_markdown"]
    assert resolved.target_body_sha256 == expected["body_sha256"]


def test_read_only_source_range_keeps_ref_despite_editor_size_and_link_limits() -> None:
    markdown = (
        "# Plan\n<!-- dmb-playable-element:v1 kind=scene id=scene:first -->\n"
        "## First\n[External](https://example.com) [Tavern](dmb-node:obj:tavern)\n"
        + "A" * 8_001
        + "\n<!-- dmb-playable-element:v1 kind=scene id=scene:second -->\n"
        "## Second\n[Cellar](dmb-node:obj:cellar)\n"
    )
    first = PlayableTarget(kind="scene", id="scene:first")
    source = selected_playable_source_for_read(markdown, first)
    assert "dmb-node:obj:tavern" in source
    assert "dmb-node:obj:cellar" not in source
    with pytest.raises(PlayableBodyTargetError):
        resolve_playable_body_target(markdown, first)


@pytest.mark.parametrize("vector", [v for v in json.loads(_VECTORS.read_text())["vectors"] if v["name"].startswith("v2_scene_") and "table" in v["name"]], ids=lambda v:v["name"])
def test_named_table_read_source_ranges_agree_with_edit_owner(vector):
    source = selected_playable_source_for_read(vector["draft_markdown"], PlayableTarget(**vector["target"]))
    assert vector["expected"]["body_markdown"].strip() in source
    assert "Keep this scene" not in source
    if vector["name"] != "v2_scene_named_table_in_body":
        assert "Guard" not in source
    else:
        assert "After." in source and "Guard" in source
