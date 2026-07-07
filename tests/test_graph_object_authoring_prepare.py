"""Tests for graph object authoring prepare service."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.services.graph_authoring_overlay_store import (
    BACKUPS_DIR,
    EVENTS_DIR,
    OVERLAYS_DIR,
    GraphAuthoringOverlayStore,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringError,
    GraphObjectAuthoringPrepareRequest,
    build_assertions_from_proposals,
    build_confirm_token,
    prepare_graph_object_authoring_write,
    stable_json_digest,
)

CAMPAIGN_ID = "longmont-c1"
TEST_CAMPAIGN_REL = "Test Campaign/A5"
STAMP = "1970-01-01T00:00:00Z"


def _visibility() -> dict[str, object]:
    return {"visibility": "gm_private", "revealState": "unrevealed"}


def _provenance() -> dict[str, object]:
    return {
        "origin": "human_authored",
        "authoringSurface": "memory_ingest_graph_authoring",
        "sourceGraphId": "graph-c1s2",
    }


def _selection() -> dict[str, object]:
    return {
        "selectionKind": "text_span",
        "selectedText": "gang",
        "normalizedSelectedText": "gang",
        "paragraphOrdinal": 0,
        "tiptapFrom": 0,
        "tiptapTo": 4,
    }


def object_proposal(**overrides) -> dict[str, object]:
    payload = {
        "localProposalId": "local-object-1",
        "proposalKind": "object",
        "status": "staged_local",
        "selection": _selection(),
        "objectRef": {
            "label": "Questionable Company",
            "kind": "party",
            "role": None,
            "aliases": ["gang"],
            "summary": "Mercenary company",
        },
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }
    payload.update(overrides)
    return payload


def link_existing_proposal(**overrides) -> dict[str, object]:
    payload = {
        "localProposalId": "local-link-1",
        "proposalKind": "link_existing",
        "status": "staged_local",
        "selection": _selection(),
        "selectedText": "gang",
        "normalizedSelectedText": "gang",
        "existingObjectRef": {
            "refKind": "manual_ref",
            "label": "Questionable Company",
        },
        "operation": "alias",
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }
    payload.update(overrides)
    return payload


def relationship_proposal(**overrides) -> dict[str, object]:
    payload = {
        "localProposalId": "local-rel-1",
        "proposalKind": "relationship",
        "status": "staged_local",
        "sourceObjectRef": {
            "refKind": "manual_ref",
            "label": "Questionable Company",
        },
        "targetObjectRef": {
            "refKind": "existing_graph_node",
            "nodeId": "pc_bonogo",
            "label": "Bonogo",
            "kind": "pc",
        },
        "relationshipType": "has_member",
        "direction": "directed",
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }
    payload.update(overrides)
    return payload


def prepare_request(**overrides) -> GraphObjectAuthoringPrepareRequest:
    payload = {
        "campaignId": CAMPAIGN_ID,
        "campaignRel": TEST_CAMPAIGN_REL,
        "sessionId": "session-2",
        "proposals": [object_proposal()],
    }
    payload.update(overrides)
    return GraphObjectAuthoringPrepareRequest.model_validate(payload)


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    return tmp_path / "corpus"


@pytest.fixture
def store(corpus_root: Path) -> GraphAuthoringOverlayStore:
    return GraphAuthoringOverlayStore(corpus_root)


def test_prepare_with_empty_proposals_fails() -> None:
    request = GraphObjectAuthoringPrepareRequest.model_validate(
        {"campaignId": CAMPAIGN_ID, "proposals": []},
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(request, corpus_root=Path("/tmp/unused"))
    assert exc.value.code == "empty_proposals"


def test_prepare_object_proposal_returns_object_assertion_preview(store: GraphAuthoringOverlayStore) -> None:
    response = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    assert response.assertion_count == 1
    assert response.assertions_preview[0].assertion_kind == "object"
    assert "Questionable Company" in response.assertions_preview[0].summary


def test_prepare_link_existing_proposal_returns_link_existing_preview(
    store: GraphAuthoringOverlayStore,
) -> None:
    response = prepare_graph_object_authoring_write(
        prepare_request(proposals=[link_existing_proposal()]),
        corpus_root=store.corpus_root,
    )
    assert response.overlay_summary.link_existing_count == 1


def test_prepare_relationship_proposal_returns_relationship_preview(
    store: GraphAuthoringOverlayStore,
) -> None:
    response = prepare_graph_object_authoring_write(
        prepare_request(proposals=[relationship_proposal()]),
        corpus_root=store.corpus_root,
    )
    assert response.overlay_summary.relationship_count == 1


def test_prepare_accepts_cross_scope_object_ref_metadata(store: GraphAuthoringOverlayStore) -> None:
    response = prepare_graph_object_authoring_write(
        prepare_request(
            proposals=[
                link_existing_proposal(
                    existingObjectRef={
                        "refKind": "existing_graph_node",
                        "nodeId": "party:bonogo",
                        "label": "Bonogo",
                        "kind": "pc",
                        "graphScope": "party_pc",
                        "sourceLabel": "Party / PCs",
                        "sourceGraphId": "longmont-c2:party",
                        "sourcePath": "_party_registry.json",
                        "visibility": "table_known",
                    }
                ),
                relationship_proposal(
                    targetObjectRef={
                        "refKind": "existing_graph_node",
                        "nodeId": "loc_mirathorn",
                        "label": "Mirathorn",
                        "kind": "location",
                        "graphScope": "worldbuilding",
                        "sourceLabel": "Worldbuilding",
                    }
                ),
            ]
        ),
        corpus_root=store.corpus_root,
    )
    assert response.prepared is True
    assert response.overlay_summary.link_existing_count == 1
    assert response.overlay_summary.relationship_count == 1


def test_build_object_ref_persists_cross_scope_source_metadata() -> None:
    request = prepare_request(
        proposals=[
            link_existing_proposal(
                existingObjectRef={
                    "refKind": "existing_graph_node",
                    "nodeId": "party:bonogo",
                    "label": "Bonogo",
                    "kind": "pc",
                    "graphScope": "party_pc",
                    "sourceLabel": "Party / PCs",
                    "sourceGraphId": "longmont-c2:party",
                    "sourcePath": "_party_registry.json",
                    "visibility": "table_known",
                }
            ),
            relationship_proposal(
                targetObjectRef={
                    "refKind": "existing_graph_node",
                    "nodeId": "loc_mirathorn",
                    "label": "Mirathorn",
                    "kind": "location",
                    "graphScope": "worldbuilding",
                    "sourceLabel": "Worldbuilding",
                }
            ),
        ]
    )
    assertions, diagnostics = build_assertions_from_proposals(request)
    assert not diagnostics
    link_ref = assertions[0].existing_object_ref
    assert link_ref.candidate_graph_scope == "party_pc"
    assert link_ref.source_label == "Party / PCs"
    assert link_ref.source_graph_id == "longmont-c2:party"
    assert link_ref.source_path == "_party_registry.json"
    assert link_ref.source_visibility == "table_known"

    target_ref = assertions[1].target_object_ref
    assert target_ref.candidate_graph_scope == "worldbuilding"
    assert target_ref.source_label == "Worldbuilding"
    assert target_ref.source_graph_id is None
    assert target_ref.source_path is None
    assert target_ref.source_visibility is None


def test_commit_persists_cross_scope_object_ref_metadata(store: GraphAuthoringOverlayStore) -> None:
    from apps.live_control_server.services.graph_object_authoring_commit import (
        GraphObjectAuthoringCommitRequest,
        commit_graph_object_authoring_write,
    )

    prepare_response = prepare_graph_object_authoring_write(
        prepare_request(
            proposals=[
                link_existing_proposal(
                    existingObjectRef={
                        "refKind": "existing_graph_node",
                        "nodeId": "party:bonogo",
                        "label": "Bonogo",
                        "kind": "pc",
                        "graphScope": "party_pc",
                        "sourceLabel": "Party / PCs",
                    }
                )
            ]
        ),
        corpus_root=store.corpus_root,
    )
    commit_response = commit_graph_object_authoring_write(
        GraphObjectAuthoringCommitRequest.model_validate(
            {
                "campaignId": CAMPAIGN_ID,
                "campaignRel": TEST_CAMPAIGN_REL,
                "sessionId": "session-2",
                "proposals": [
                    link_existing_proposal(
                        existingObjectRef={
                            "refKind": "existing_graph_node",
                            "nodeId": "party:bonogo",
                            "label": "Bonogo",
                            "kind": "pc",
                            "graphScope": "party_pc",
                            "sourceLabel": "Party / PCs",
                        }
                    )
                ],
                "confirmToken": prepare_response.confirm_token,
                "currentOverlayToken": prepare_response.current_overlay_token,
            }
        ),
        corpus_root=store.corpus_root,
    )
    assert commit_response.committed is True

    overlay = store.load_overlay(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    link_assertion = next(
        item for item in overlay.assertions if item.assertion_kind == "link_existing"
    )
    ref = link_assertion.existing_object_ref
    assert ref.candidate_graph_scope == "party_pc"
    assert ref.source_label == "Party / PCs"


def test_prepare_writes_nothing(store: GraphAuthoringOverlayStore) -> None:
    campaign_dir = store.corpus_root / TEST_CAMPAIGN_REL
    prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    authoring_root = campaign_dir / "_graph_authoring"
    assert not (authoring_root / OVERLAYS_DIR).exists()
    assert not (authoring_root / EVENTS_DIR).exists()
    assert not (authoring_root / BACKUPS_DIR).exists()


def test_prepare_returns_proposed_assertions_digest(store: GraphAuthoringOverlayStore) -> None:
    response = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    assert len(response.proposed_assertions_digest) == 64
    assert response.proposed_assertions_digest != response.current_overlay_token


def test_prepare_returns_confirm_token(store: GraphAuthoringOverlayStore) -> None:
    response = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    assert len(response.confirm_token) == 64


def test_prepare_token_is_deterministic(store: GraphAuthoringOverlayStore) -> None:
    first = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    second = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    assert first.confirm_token == second.confirm_token
    assert first.current_overlay_token == second.current_overlay_token
    assert first.proposed_assertions_digest == second.proposed_assertions_digest
    assert first.assertions_preview[0].assertion_id == second.assertions_preview[0].assertion_id


def test_build_assertions_preserves_zero_source_anchor_offsets() -> None:
    request = prepare_request(
        proposals=[
            object_proposal(
                selection={
                    "selectionKind": "text_span",
                    "selectedText": "x",
                    "normalizedSelectedText": "x",
                    "paragraphOrdinal": 0,
                    "tiptapFrom": 0,
                    "tiptapTo": 0,
                }
            )
        ]
    )
    assertions, diagnostics = build_assertions_from_proposals(request)
    assert not diagnostics
    anchor = assertions[0].source_anchor
    assert anchor is not None
    assert anchor.paragraph_ordinal == 0
    assert anchor.tiptap_from == 0
    assert anchor.tiptap_to == 0


def test_prepare_rejects_blank_relationship_type(store: GraphAuthoringOverlayStore) -> None:
    request = prepare_request(proposals=[relationship_proposal(relationshipType="   ")])
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(request, corpus_root=store.corpus_root)
    assert exc.value.code == "invalid_relationship_type"


def test_prepare_rejects_blank_object_ref_label(store: GraphAuthoringOverlayStore) -> None:
    request = prepare_request(
        proposals=[
            object_proposal(
                objectRef={
                    "label": "   ",
                    "kind": "party",
                    "aliases": [],
                }
            )
        ]
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(request, corpus_root=store.corpus_root)
    assert exc.value.code == "invalid_proposal"


def test_prepare_response_includes_no_mutation_guarantees(store: GraphAuthoringOverlayStore) -> None:
    response = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    assert "Prepare wrote nothing." in response.no_mutation_guarantees
    assert any("graph gold" in item.lower() for item in response.no_mutation_guarantees)


def test_confirm_token_uses_stable_json_digest() -> None:
    assert stable_json_digest({"a": 1}) == stable_json_digest({"a": 1})
    assert stable_json_digest({"a": 1}) != stable_json_digest({"a": 2})


def test_build_confirm_token_changes_when_assertions_change() -> None:
    request_a = prepare_request(proposals=[object_proposal()])
    request_b = prepare_request(proposals=[object_proposal(localProposalId="local-object-2")])
    assertions_a, _ = build_assertions_from_proposals(request_a)
    assertions_b, _ = build_assertions_from_proposals(request_b)
    token_a = build_confirm_token(
        campaign_id=CAMPAIGN_ID,
        overlay_path="/tmp/overlay.json",
        current_overlay_token="abc",
        assertions=assertions_a,
    )
    token_b = build_confirm_token(
        campaign_id=CAMPAIGN_ID,
        overlay_path="/tmp/overlay.json",
        current_overlay_token="abc",
        assertions=assertions_b,
    )
    assert token_a != token_b
