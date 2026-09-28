from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from apps.live_control_server.routes import live
from apps.live_control_server.services.world_container_registry import create_world_container


def test_managed_world_plan_context_v2_is_exact_and_non_authoritative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = create_world_container(tmp_path, name="Plan Contract World")
    monkeypatch.setattr(live, "repo_root", lambda: tmp_path)

    response = live.get_live_plan_view(world_id=world.world_id, scope_mode="world")

    assert response["schema_version"] == "dmb_managed_world_plan_context_v2"
    assert response["scope_mode"] == "world"
    assert response["world_id"] == world.world_id
    assert response["campaign_id"] is None
    assert response["session"] is None
    assert response["authoritative"] is False
    assert response["derived_from"] == ["managed_world_container"]
    assert response["timeline"] == []


def test_legacy_managed_plan_context_remains_v1_compatibility_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = create_world_container(tmp_path, name="Plan Contract World")
    monkeypatch.setattr(live, "repo_root", lambda: tmp_path)

    response = live.get_live_plan_view(world_id=world.world_id)

    assert response["schema_version"] == "dmb_managed_world_plan_context_v1"
    assert response["campaign_id"] == world.world_id
    assert response["session"] == 0


def test_world_context_requires_exact_world_id() -> None:
    with pytest.raises(HTTPException) as error:
        live.get_live_plan_view(world_id=None, scope_mode="world")
    assert error.value.status_code == 422

