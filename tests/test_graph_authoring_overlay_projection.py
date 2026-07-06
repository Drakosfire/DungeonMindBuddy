"""Tests for authored overlay projection into graph review payloads."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.models.graph_authoring_overlay import (
    create_empty_authored_graph_overlay,
)
from apps.live_control_server.services.graph_authoring_overlay_projection import (
    apply_authored_overlay_to_graph_review_projection,
    authored_manual_node_id,
    authored_object_node_id,
    build_authored_projection_node_views,
    enrich_projection_payload_with_authored_overlay,
    load_authored_overlay_for_review,
)
from apps.live_control_server.services.graph_authoring_overlay_store import GraphAuthoringOverlayStore
from graph_memory.projection.focus_overlay import GraphFocusOverlay
from graph_memory.projection.node_view import GraphProjectionNodeView
from graph_memory.projection.recap_projection import RecapGraphProjection
from tests.test_graph_authoring_overlay_models import (
    CAMPAIGN_ID,
    STAMP,
    link_existing_assertion,
    object_assertion,
    relationship_assertion,
)

TEST_CAMPAIGN_REL = "Test Campaign/A6"


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    return tmp_path / "corpus"


@pytest.fixture
def store(corpus_root: Path) -> GraphAuthoringOverlayStore:
    return GraphAuthoringOverlayStore(corpus_root)


def _empty_projection() -> RecapGraphProjection:
    return RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-1",
        graph_id="graph-1",
        markdown="# Recap",
        focus=GraphFocusOverlay(focus_session_id="session-1"),
        node_views={
            "pc_bonogo": GraphProjectionNodeView(
                node_id="pc_bonogo",
                label="Bonogo",
                kind="pc",
                role="candidate",
                aliases=[],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            )
        },
        mentions=[],
        source_spans=[],
    )


def test_missing_overlay_is_safe(store: GraphAuthoringOverlayStore) -> None:
    overlay, summary = load_authored_overlay_for_review(
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    assert overlay is None
    assert summary.loaded is False
    assert any(item.code == "authored_overlay_missing" for item in summary.diagnostics)


def test_object_assertion_becomes_node_view(store: GraphAuthoringOverlayStore) -> None:
    assertion = object_assertion(
        assertion_id="assert-qc",
        object_ref={
            "ref_kind": "local_proposal",
            "local_proposal_id": "local-qc",
            "label": "Questionable Company",
            "kind": "party",
            "role": "authored",
        },
        aliases=["gang"],
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [assertion]}
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)

    projection = _empty_projection()
    loaded, summary = load_authored_overlay_for_review(
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    assert loaded is not None
    assert summary.loaded is True
    enriched, overlay_summary = apply_authored_overlay_to_graph_review_projection(
        projection,
        loaded,
        summary=summary,
    )
    node_id = authored_object_node_id("assert-qc")
    assert node_id in enriched.node_views
    node = enriched.node_views[node_id]
    assert node.label == "Questionable Company"
    assert node.kind == "party"
    assert "gang" in node.aliases
    assert node.source_domains == ["authored_overlay"]
    assert getattr(node, "authored") is True
    assert overlay_summary.projected_node_count >= 1


def test_retracted_assertion_not_projected(store: GraphAuthoringOverlayStore) -> None:
    active = object_assertion(assertion_id="assert-active")
    retracted = object_assertion(
        assertion_id="assert-retracted",
        status="retracted",
        object_ref={
            "ref_kind": "local_proposal",
            "local_proposal_id": "local-hidden",
            "label": "Hidden Object",
            "kind": "entity",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [active, retracted]}
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    loaded, _ = load_authored_overlay_for_review(
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        _empty_projection(),
        loaded,
    )
    assert authored_object_node_id("assert-active") in enriched.node_views
    assert authored_object_node_id("assert-retracted") not in enriched.node_views
    assert summary.assertion_count == 1


def test_link_existing_attaches_alias_to_existing_node(store: GraphAuthoringOverlayStore) -> None:
    link = link_existing_assertion(
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "pc_bonogo",
            "label": "Bonogo",
            "kind": "pc",
        },
        alias_text="Bono",
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    node_views = build_authored_projection_node_views(
        overlay,
        base_node_views=_empty_projection().node_views,
        existing_node_ids=set(_empty_projection().node_views.keys()),
    )
    assert "pc_bonogo" in node_views
    assert "Bono" in node_views["pc_bonogo"].aliases
    assert "authored_overlay" in node_views["pc_bonogo"].source_domains


def test_manual_link_existing_becomes_authored_manual_node() -> None:
    link = link_existing_assertion(
        existing_object_ref={
            "ref_kind": "manual_ref",
            "label": "Mystery Group",
            "kind": "party",
        }
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    node_views = build_authored_projection_node_views(overlay)
    manual_id = authored_manual_node_id("Mystery Group", "party")
    assert manual_id in node_views
    assert node_views[manual_id].label == "Mystery Group"


def test_relationship_assertion_adds_adjacency(store: GraphAuthoringOverlayStore) -> None:
    object_a = object_assertion(
        assertion_id="assert-qc",
        object_ref={
            "ref_kind": "local_proposal",
            "local_proposal_id": "local-qc",
            "label": "Questionable Company",
            "kind": "party",
        },
    )
    rel = relationship_assertion(
        source_object_ref={
            "ref_kind": "local_proposal",
            "local_proposal_id": "local-qc",
            "label": "Questionable Company",
            "kind": "party",
        },
        target_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "pc_bonogo",
            "label": "Bonogo",
            "kind": "pc",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [object_a, rel]}
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    payload = enrich_projection_payload_with_authored_overlay(
        _empty_projection().model_dump(mode="json"),
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    source_id = authored_object_node_id("assert-qc")
    source_node = payload["node_views"][source_id]
    assert source_node["adjacency"]
    assert source_node["adjacency"][0]["node_id"] == "pc_bonogo"
    assert source_node["adjacency"][0]["predicate"] == "has_member"
    assert payload["authored_overlay"]["projected_relationship_count"] == 1


def test_existing_extracted_nodes_preserved(store: GraphAuthoringOverlayStore) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [object_assertion(assertion_id="assert-new")]}
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    payload = enrich_projection_payload_with_authored_overlay(
        _empty_projection().model_dump(mode="json"),
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    assert "pc_bonogo" in payload["node_views"]
    assert payload["node_views"]["pc_bonogo"]["label"] == "Bonogo"


def test_authored_node_ids_are_stable() -> None:
    assertion = object_assertion(assertion_id="assert-stable-id")
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [assertion]}
    )
    first = build_authored_projection_node_views(overlay)
    second = build_authored_projection_node_views(overlay)
    assert list(first.keys()) == list(second.keys()) == [authored_object_node_id("assert-stable-id")]
