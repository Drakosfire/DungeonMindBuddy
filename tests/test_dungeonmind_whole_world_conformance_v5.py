"""Thin proofs for CURRENT_V5_TARGET vs HISTORICAL_V4_TARGET parameterization."""

from __future__ import annotations

import inspect

import pytest

from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
    HISTORICAL_V4_TARGET,
    _BUDDY_TO_DM_KIND,
    _BUDDY_TO_DM_KIND_V5,
    _DUNGEONMIND_DEPENDENCY_REF_V4,
    _DUNGEONMIND_DEPENDENCY_REF_V5,
    analyze_exact_buddy_world_revision_v4,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v5 import (
    analyze_exact_buddy_world_revision_v5,
)
from dungeonmind_dnd.application.world_object_vocabulary import (
    builtin_world_object_v4_vocabulary_ref,
    builtin_world_object_v5_vocabulary_ref,
)
from dungeonmind_dnd.application.world_property_vocabulary import (
    builtin_world_property_v2_vocabulary_ref,
    builtin_world_property_v3_vocabulary_ref,
    validate_world_property_assignment_v2,
    validate_world_property_assignment_v3,
)


def test_current_v5_target_digests() -> None:
    object_ref = CURRENT_V5_TARGET.world_object_ref_loader()
    property_ref = CURRENT_V5_TARGET.world_property_ref_loader()
    assert CURRENT_V5_TARGET.dungeonmind_dependency_ref == (
        "be76acc997c5fbcb8ceaa090969ec051afa6051d"
    )
    assert CURRENT_V5_TARGET.dungeonmind_dependency_ref == _DUNGEONMIND_DEPENDENCY_REF_V5
    assert CURRENT_V5_TARGET.world_object_revision_label == "world-object-v5"
    assert CURRENT_V5_TARGET.world_property_revision_label == "world-property-v3"
    assert object_ref.vocabulary_revision == "world-object-v5"
    assert object_ref.catalog_sha256 == (
        "f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8"
    )
    assert property_ref.vocabulary_revision == "world-property-v3"
    assert property_ref.catalog_sha256 == (
        "aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4"
    )
    # Cross-check against the same loaders the target pins.
    assert object_ref.catalog_sha256 == builtin_world_object_v5_vocabulary_ref().catalog_sha256
    assert property_ref.catalog_sha256 == builtin_world_property_v3_vocabulary_ref().catalog_sha256


def test_historical_v4_target_digests_unchanged() -> None:
    object_ref = HISTORICAL_V4_TARGET.world_object_ref_loader()
    property_ref = HISTORICAL_V4_TARGET.world_property_ref_loader()
    assert HISTORICAL_V4_TARGET.dungeonmind_dependency_ref == (
        "2e4fdc51f91c5c2a428500f7c2ece0d6742d04b4"
    )
    assert HISTORICAL_V4_TARGET.dungeonmind_dependency_ref == (
        _DUNGEONMIND_DEPENDENCY_REF_V4
    )
    assert HISTORICAL_V4_TARGET.world_object_revision_label == "world-object-v4"
    assert HISTORICAL_V4_TARGET.world_property_revision_label == "world-property-v2"
    assert object_ref.vocabulary_revision == "world-object-v4"
    assert object_ref.catalog_sha256 == (
        "552c59a3fa9a20e437294d1a77974c05e37b69ec95e5ea03337a7d010e4d287b"
    )
    assert property_ref.vocabulary_revision == "world-property-v2"
    assert property_ref.catalog_sha256 == (
        "8ad4c223e83ce48cf5cd33a33e10f5be5d48a80ad742784d7c561470b450ab73"
    )
    assert object_ref.catalog_sha256 == builtin_world_object_v4_vocabulary_ref().catalog_sha256
    assert property_ref.catalog_sha256 == builtin_world_property_v2_vocabulary_ref().catalog_sha256


def test_kind_map_delta_is_only_thread() -> None:
    assert "thread" not in HISTORICAL_V4_TARGET.buddy_to_dm_kind
    assert "thread" not in _BUDDY_TO_DM_KIND
    assert CURRENT_V5_TARGET.buddy_to_dm_kind["thread"] == "dnd5e:thread"
    assert _BUDDY_TO_DM_KIND_V5["thread"] == "dnd5e:thread"
    historical = dict(HISTORICAL_V4_TARGET.buddy_to_dm_kind)
    current = dict(CURRENT_V5_TARGET.buddy_to_dm_kind)
    assert {k: current[k] for k in current if k not in historical} == {
        "thread": "dnd5e:thread"
    }
    assert {k: historical[k] for k in historical} == {
        k: current[k] for k in historical
    }


def test_v5_role_validator_is_v3() -> None:
    assert CURRENT_V5_TARGET.role_validator is validate_world_property_assignment_v3
    assert HISTORICAL_V4_TARGET.role_validator is validate_world_property_assignment_v2


def test_analyze_exact_buddy_world_revision_v5_uses_be76acc_and_world_object_v5(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Entrypoint must request CURRENT_V5_TARGET explicitly (no latest inference)."""
    captured: dict[str, object] = {}

    def _fake_load(*, root, world_id, revision_id):  # noqa: ANN001
        captured["load"] = (root, world_id, revision_id)
        return ("manifest", "store")

    def _fake_analyze(**kwargs):  # noqa: ANN003
        captured["analyze"] = kwargs
        return "report"

    monkeypatch.setattr(
        "apps.live_control_server.integrations.dungeonmind_kernel."
        "whole_world_conformance_v5._load_exact_buddy_revision",
        _fake_load,
    )
    monkeypatch.setattr(
        "apps.live_control_server.integrations.dungeonmind_kernel."
        "whole_world_conformance_v5._analyze_loaded_buddy_world_store_v4",
        _fake_analyze,
    )
    result = analyze_exact_buddy_world_revision_v5(
        root="/tmp",
        world_id="eldyrwild",
        revision_id="rev:example",
    )
    assert result == "report"
    assert captured["analyze"]["target"] is CURRENT_V5_TARGET
    assert captured["analyze"]["target"].dungeonmind_dependency_ref == (
        "be76acc997c5fbcb8ceaa090969ec051afa6051d"
    )
    assert captured["analyze"]["target"].world_object_revision_label == "world-object-v5"

    # Default historical loaded-store helper still defaults to HISTORICAL_V4_TARGET.
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
        _analyze_loaded_buddy_world_store_v4,
    )

    default_target = inspect.signature(
        _analyze_loaded_buddy_world_store_v4
    ).parameters["target"].default
    assert default_target is HISTORICAL_V4_TARGET
    # Keep historical public entrypoint import referenced for discoverability.
    assert callable(analyze_exact_buddy_world_revision_v4)