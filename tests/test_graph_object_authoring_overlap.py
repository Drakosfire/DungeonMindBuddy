"""Tests for graph object authoring prepare overlap warnings."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.models.graph_authoring_overlay import (
    create_empty_authored_graph_overlay,
)
from apps.live_control_server.services.graph_authoring_overlay_store import GraphAuthoringOverlayStore
from apps.live_control_server.services.graph_object_authoring_overlap import (
    detect_prepare_overlap_warnings,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringPrepareRequest,
    GraphObjectAuthoringProposalPayload,
    GraphObjectAuthoringVisibilityPayload,
    prepare_graph_object_authoring_write,
)
from tests.test_graph_authoring_overlay_models import CAMPAIGN_ID, STAMP, object_assertion

TEST_CAMPAIGN_REL = "Test Campaign/A6.5"


def _visibility() -> GraphObjectAuthoringVisibilityPayload:
    return GraphObjectAuthoringVisibilityPayload(visibility="gm_private")


def _object_proposal(
    *,
    local_proposal_id: str = "local-object-1",
    label: str = "Questionable Company",
    aliases: list[str] | None = None,
    selected_text: str = "gang",
) -> GraphObjectAuthoringProposalPayload:
    return GraphObjectAuthoringProposalPayload(
        localProposalId=local_proposal_id,
        proposalKind="object",
        selection={
            "selectionKind": "text_span",
            "selectedText": selected_text,
            "normalizedSelectedText": selected_text,
        },
        objectRef={
            "label": label,
            "kind": "party",
            "role": None,
            "aliases": aliases or ["gang"],
            "summary": None,
        },
        visibility=_visibility(),
        provenancePreview={
            "origin": "human_authored",
            "authoringSurface": "memory_ingest_graph_authoring",
        },
    )


def _prepare_request(
    proposals: list[GraphObjectAuthoringProposalPayload],
) -> GraphObjectAuthoringPrepareRequest:
    return GraphObjectAuthoringPrepareRequest(
        campaignId=CAMPAIGN_ID,
        campaignRel=TEST_CAMPAIGN_REL,
        sessionId="session-1",
        proposals=proposals,
    )


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    return tmp_path / "corpus"


@pytest.fixture
def store(corpus_root: Path) -> GraphAuthoringOverlayStore:
    return GraphAuthoringOverlayStore(corpus_root)


def test_prepare_warns_on_duplicate_label(store: GraphAuthoringOverlayStore) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                object_assertion(
                    assertion_id="assert-existing",
                    object_ref={
                        "ref_kind": "local_proposal",
                        "local_proposal_id": "local-old",
                        "label": "Questionable Company",
                        "kind": "party",
                    },
                    aliases=["gang"],
                )
            ]
        }
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)

    request = _prepare_request([_object_proposal()])
    response = prepare_graph_object_authoring_write(request, corpus_root=store.corpus_root)

    assert response.prepared is True
    assert any(
        item.code == "authored_overlay_possible_duplicate_label"
        for item in response.diagnostics
    )


def test_prepare_warns_on_duplicate_alias(store: GraphAuthoringOverlayStore) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                object_assertion(
                    assertion_id="assert-existing",
                    object_ref={
                        "ref_kind": "local_proposal",
                        "local_proposal_id": "local-old",
                        "label": "Questionable Company",
                        "kind": "party",
                    },
                    aliases=["gang"],
                )
            ]
        }
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)

    request = _prepare_request(
        [
            _object_proposal(
                label="Another Name",
                aliases=["gang"],
            )
        ]
    )
    response = prepare_graph_object_authoring_write(request, corpus_root=store.corpus_root)

    assert any(
        item.code == "authored_overlay_possible_duplicate_alias"
        for item in response.diagnostics
    )


def test_prepare_warns_on_duplicate_source_anchor(store: GraphAuthoringOverlayStore) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                object_assertion(
                    assertion_id="assert-existing",
                    source_anchor={
                        "anchor_kind": "text_span",
                        "selected_text": "gang",
                        "normalized_selected_text": "gang",
                    },
                    object_ref={
                        "ref_kind": "local_proposal",
                        "local_proposal_id": "local-old",
                        "label": "Questionable Company",
                        "kind": "party",
                    },
                    aliases=["gang"],
                )
            ]
        }
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)

    request = _prepare_request([_object_proposal(selected_text="gang")])
    response = prepare_graph_object_authoring_write(request, corpus_root=store.corpus_root)

    assert any(
        item.code
        in {
            "authored_overlay_possible_duplicate_source_anchor",
            "authored_overlay_possible_duplicate_alias",
        }
        for item in response.diagnostics
    )


def test_prepare_warns_on_staged_batch_duplicate() -> None:
    request = _prepare_request(
        [
            _object_proposal(local_proposal_id="local-1"),
            _object_proposal(local_proposal_id="local-2"),
        ]
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP)
    warnings = detect_prepare_overlap_warnings(request, existing_overlay=overlay)

    assert any(item.code == "staged_proposal_possible_duplicate" for item in warnings)


def test_prepare_still_succeeds_with_overlap_warnings(store: GraphAuthoringOverlayStore) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [object_assertion(assertion_id="assert-existing")]}
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)

    response = prepare_graph_object_authoring_write(
        _prepare_request([_object_proposal()]),
        corpus_root=store.corpus_root,
    )

    assert response.prepared is True
    assert response.confirm_token
    assert response.diagnostics
