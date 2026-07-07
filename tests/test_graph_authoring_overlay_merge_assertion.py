"""Tests for merge_objects authored graph overlay assertions."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.test_graph_authoring_overlay_models import (
    CAMPAIGN_ID,
    object_ref,
    provenance,
)


def merge_objects_assertion(**overrides):
    data = {
        "assertion_id": "assert-merge-1",
        "assertion_kind": "merge_objects",
        "operation": "merge",
        "campaign_id": CAMPAIGN_ID,
        "session_id": "session-1",
        "provenance": provenance().model_dump(),
        "survivor_object_ref": object_ref(
            node_id="survivor-1",
            label="Tripod Null-Calf",
        ).model_dump(),
        "merged_object_refs": [
            object_ref(node_id="merged-1", label="Tripod Null Calf").model_dump(),
        ],
        "merge_reason": "Exact normalized label match",
        "matched_features": ["Exact normalized label match"],
    }
    data.update(overrides)
    from apps.live_control_server.models.graph_authoring_overlay import (
        AuthoredGraphMergeObjectsAssertion,
    )

    return AuthoredGraphMergeObjectsAssertion.model_validate(data)


def test_builds_merge_objects_assertion() -> None:
    assertion = merge_objects_assertion()
    assert assertion.assertion_kind == "merge_objects"
    assert assertion.survivor_object_ref.label == "Tripod Null-Calf"
    assert len(assertion.merged_object_refs) == 1


def test_rejects_self_merge() -> None:
    ref = object_ref(node_id="same-node", label="Bonogo").model_dump()
    with pytest.raises(ValidationError):
        merge_objects_assertion(
            survivor_object_ref=ref,
            merged_object_refs=[ref],
        )


def test_rejects_manual_ref_for_merge_mvp() -> None:
    manual = object_ref(ref_kind="manual_ref", label="Manual", node_id=None).model_dump()
    with pytest.raises(ValidationError):
        merge_objects_assertion(merged_object_refs=[manual])
