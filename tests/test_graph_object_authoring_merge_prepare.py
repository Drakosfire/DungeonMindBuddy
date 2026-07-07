"""Tests for merge_objects prepare behavior."""

from __future__ import annotations

import pytest

from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringError,
    GraphObjectAuthoringPrepareRequest,
    build_assertions_from_proposals,
    prepare_graph_object_authoring_write,
)
from tests.test_graph_object_authoring_prepare import (
    _provenance,
    _visibility,
    prepare_request,
)


def merge_proposal(**overrides) -> dict[str, object]:
    payload = {
        "localProposalId": "local-merge-1",
        "proposalKind": "merge_objects",
        "status": "staged_local",
        "survivorObjectRef": {
            "refKind": "existing_graph_node",
            "nodeId": "survivor-node",
            "label": "Tripod Null-Calf",
            "kind": "threat",
        },
        "mergedObjectRefs": [
            {
                "refKind": "existing_graph_node",
                "nodeId": "merged-node",
                "label": "Tripod Null Calf",
                "kind": "threat",
            }
        ],
        "mergeReason": "Exact normalized label match",
        "matchedFeatures": ["Exact normalized label match"],
        "aliasPolicy": "preserve_all_aliases",
        "relationshipPolicy": "preserve_all_relationships",
        "evidencePolicy": "preserve_all_evidence",
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }
    payload.update(overrides)
    return payload


def test_builds_merge_assertion_from_proposal() -> None:
    request = GraphObjectAuthoringPrepareRequest.model_validate(
        prepare_request(proposals=[merge_proposal()])
    )
    assertions, diagnostics = build_assertions_from_proposals(request)
    assert diagnostics == []
    assert len(assertions) == 1
    assert assertions[0].assertion_kind == "merge_objects"
    assert assertions[0].survivor_object_ref.node_id == "survivor-node"


def test_prepare_blocks_manual_ref_merge() -> None:
    request = GraphObjectAuthoringPrepareRequest.model_validate(
        prepare_request(
            proposals=[
                merge_proposal(
                    mergedObjectRefs=[
                        {
                            "refKind": "manual_ref",
                            "label": "Manual only",
                        }
                    ]
                )
            ]
        )
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(request)
    assert exc.value.code in {"unsupported_merge_ref", "invalid_proposal"}


def test_prepare_warns_on_kind_mismatch() -> None:
    request = GraphObjectAuthoringPrepareRequest.model_validate(
        prepare_request(
            proposals=[
                merge_proposal(
                    mergedObjectRefs=[
                        {
                            "refKind": "existing_graph_node",
                            "nodeId": "merged-node",
                            "label": "Tripod Null Calf",
                            "kind": "location",
                        }
                    ]
                )
            ]
        )
    )
    assertions, diagnostics = build_assertions_from_proposals(request)
    assert len(assertions) == 1
    assert any(item.code == "merge_kind_role_conflict" for item in diagnostics)


def test_prepare_succeeds_with_kind_mismatch_warning() -> None:
    request = GraphObjectAuthoringPrepareRequest.model_validate(
        prepare_request(
            proposals=[
                merge_proposal(
                    survivorObjectRef={
                        "refKind": "existing_graph_node",
                        "nodeId": "edge-a",
                        "label": "Edge",
                        "kind": "location",
                    },
                    mergedObjectRefs=[
                        {
                            "refKind": "existing_graph_node",
                            "nodeId": "edge-b",
                            "label": "Edge",
                            "kind": "organization",
                        }
                    ],
                )
            ]
        )
    )
    response = prepare_graph_object_authoring_write(request)
    assert response.assertion_count == 1
    assert any(
        item.code == "merge_kind_role_conflict" and item.severity == "warning"
        for item in response.diagnostics
    )
    assert response.confirm_token


def test_prepare_normalizes_recap_graph_scope_alias() -> None:
    request = GraphObjectAuthoringPrepareRequest.model_validate(
        prepare_request(
            proposals=[
                merge_proposal(
                    survivorObjectRef={
                        "refKind": "existing_graph_node",
                        "nodeId": "edge-a",
                        "label": "Edge",
                        "kind": "location",
                        "graphScope": "recap",
                    },
                    mergedObjectRefs=[
                        {
                            "refKind": "existing_graph_node",
                            "nodeId": "edge-b",
                            "label": "the Edge",
                            "kind": "location",
                            "graphScope": "recap",
                        }
                    ],
                )
            ]
        )
    )
    assertions, diagnostics = build_assertions_from_proposals(request)
    assert diagnostics == []
    assert len(assertions) == 1
    assert assertions[0].survivor_object_ref.candidate_graph_scope == "current_recap_projection"
    assert assertions[0].merged_object_refs[0].candidate_graph_scope == "current_recap_projection"
