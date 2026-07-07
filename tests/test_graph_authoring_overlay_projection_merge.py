"""Tests for merge overlay projection behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphMergeObjectsAssertion,
    create_empty_authored_graph_overlay,
)
from apps.live_control_server.services.graph_authoring_overlay_projection import (
    apply_authored_overlay_to_graph_review_projection,
)
from apps.live_control_server.services.graph_authoring_overlay_store import GraphAuthoringOverlayStore
from graph_memory.projection.focus_overlay import GraphFocusOverlay
from graph_memory.projection.node_view import GraphProjectionNodeView
from graph_memory.projection.recap_projection import RecapGraphProjection
from tests.test_graph_authoring_overlay_models import CAMPAIGN_ID, STAMP, object_ref, provenance

TEST_CAMPAIGN_REL = "Test Campaign/A10i"


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    return tmp_path / "corpus"


@pytest.fixture
def store(corpus_root: Path) -> GraphAuthoringOverlayStore:
    return GraphAuthoringOverlayStore(corpus_root)


def _projection_with_duplicates() -> RecapGraphProjection:
    return RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-1",
        graph_id="graph-1",
        markdown="[Tripod Null Calf](dmb-node:merged-node) watched the gate.",
        focus=GraphFocusOverlay(focus_session_id="session-1"),
        node_views={
            "survivor-node": GraphProjectionNodeView(
                node_id="survivor-node",
                label="Tripod Null-Calf",
                kind="threat",
                role="candidate",
                aliases=["Null-Calf"],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            ),
            "merged-node": GraphProjectionNodeView(
                node_id="merged-node",
                label="Tripod Null Calf",
                kind="threat",
                role="candidate",
                aliases=[],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            ),
        },
        mentions=[],
        source_spans=[],
    )


def merge_assertion() -> AuthoredGraphMergeObjectsAssertion:
    return AuthoredGraphMergeObjectsAssertion.model_validate(
        {
            "assertion_id": "assert-merge-proj",
            "assertion_kind": "merge_objects",
            "operation": "merge",
            "campaign_id": CAMPAIGN_ID,
            "session_id": "session-1",
            "provenance": provenance().model_dump(),
            "survivor_object_ref": object_ref(
                node_id="survivor-node",
                label="Tripod Null-Calf",
                kind="threat",
            ).model_dump(),
            "merged_object_refs": [
                object_ref(
                    node_id="merged-node",
                    label="Tripod Null Calf",
                    kind="threat",
                ).model_dump()
            ],
            "matched_features": ["Exact normalized label match"],
        }
    )


def test_merge_assertion_collapses_duplicate_node_views(store: GraphAuthoringOverlayStore) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [merge_assertion()]}
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    loaded = store.load_overlay(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)

    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        _projection_with_duplicates(),
        loaded,
    )
    assert "merged-node" not in enriched.node_views
    assert "survivor-node" in enriched.node_views
    assert "Tripod Null Calf" in enriched.node_views["survivor-node"].aliases
    assert "dmb-node:survivor-node" in enriched.markdown
    assert summary.projected_merge_objects_count >= 1
