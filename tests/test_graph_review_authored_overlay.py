"""Integration tests for authored overlay in graph review projection payloads."""

from __future__ import annotations

from pathlib import Path

from apps.live_control_server.models.graph_authoring_overlay import (
    create_empty_authored_graph_overlay,
)
from apps.live_control_server.services.graph_authoring_overlay_projection import (
    authored_object_node_id,
    enrich_projection_payload_with_authored_overlay,
)
from apps.live_control_server.services.graph_authoring_overlay_store import GraphAuthoringOverlayStore
from graph_memory.projection.focus_overlay import GraphFocusOverlay
from graph_memory.projection.recap_projection import RecapGraphProjection
from tests.test_graph_authoring_overlay_models import CAMPAIGN_ID, STAMP, object_assertion

TEST_CAMPAIGN_REL = "Test Campaign/A6"


def test_enrich_projection_payload_adds_authored_overlay_block(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    store = GraphAuthoringOverlayStore(corpus_root)
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                object_assertion(
                    assertion_id="assert-qc",
                    object_ref={
                        "ref_kind": "local_proposal",
                        "local_proposal_id": "local-qc",
                        "label": "Questionable Company",
                        "kind": "party",
                    },
                    aliases=["gang"],
                )
            ]
        }
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)

    base_payload = RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-1",
        graph_id="graph-1",
        markdown="# Recap",
        focus=GraphFocusOverlay(focus_session_id="session-1"),
        node_views={},
        mentions=[],
        source_spans=[],
    ).model_dump(mode="json")

    payload = enrich_projection_payload_with_authored_overlay(
        base_payload,
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=corpus_root,
    )
    assert payload["authored_overlay"]["loaded"] is True
    assert payload["authored_overlay"]["assertion_count"] == 1
    node_id = authored_object_node_id("assert-qc")
    assert node_id in payload["node_views"]
    assert payload["node_views"][node_id]["label"] == "Questionable Company"
