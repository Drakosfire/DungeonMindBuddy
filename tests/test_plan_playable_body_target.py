"""Server side of the shared Plan Playable body codec vectors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.services.plan_playable_body_target import (
    PlayableBodyTargetError,
    PlayableTarget,
    resolve_playable_body_target,
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
