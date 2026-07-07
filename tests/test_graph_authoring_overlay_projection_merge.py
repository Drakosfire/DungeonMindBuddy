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
from graph_memory.projection.focus_overlay import GraphFocusOverlay, GraphProjectionEvidenceBadge
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


def test_merge_into_party_anchor_hydrates_rich_ingest_projection(
    store: GraphAuthoringOverlayStore,
) -> None:
    rich_evidence = GraphProjectionEvidenceBadge(
        evidence_ref_id="ev-lysandra-1",
        source_artifact_id="session-recap",
        source_domain="recap",
        evidence_role="mention",
        is_focus_session_evidence=True,
        can_open_source=True,
        can_highlight_span=True,
    )
    from graph_memory.projection.node_view import GraphProjectionAdjacencyCandidate

    projection = RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-23",
        graph_id="graph-1",
        markdown="[Lysandra](dmb-node:node:lysandra) led the charge.",
        focus=GraphFocusOverlay(focus_session_id="session-23"),
        node_views={
            "party:captain_lysandra_ironveil": GraphProjectionNodeView(
                node_id="party:captain_lysandra_ironveil",
                label="Captain Lysandra Ironveil",
                kind="companion",
                role="companion",
                aliases=["Lysandra"],
                source_domains=["party_pc"],
                evidence_badges=[],
                adjacency=[],
                summary="Deterministic party context anchor",
            ),
            "node:lysandra": GraphProjectionNodeView(
                node_id="node:lysandra",
                label="Lysandra",
                kind="character",
                role="source_evidence",
                aliases=["Lysandra"],
                source_domains=["live_projection", "recap"],
                evidence_badges=[rich_evidence],
                adjacency=[
                    GraphProjectionAdjacencyCandidate(
                        edge_id="edge-1",
                        node_id="location_mireward",
                        label="Mireward Reach",
                        kind="location",
                        predicate="travels_to",
                        direction="outgoing",
                        source_domains=["live_projection"],
                        evidence_ref_ids=["ev-lysandra-1"],
                    )
                ],
                summary="Led the charge at the wall and coordinated the party.",
            ),
        },
        mentions=[],
        source_spans=[],
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                AuthoredGraphMergeObjectsAssertion.model_validate(
                    {
                        "assertion_id": "assert-party-merge",
                        "assertion_kind": "merge_objects",
                        "operation": "merge",
                        "campaign_id": CAMPAIGN_ID,
                        "session_id": "session-23",
                        "provenance": provenance().model_dump(),
                        "survivor_object_ref": object_ref(
                            node_id="party:captain_lysandra_ironveil",
                            label="Captain Lysandra Ironveil",
                            kind="companion",
                            role="companion",
                        ).model_dump(),
                        "merged_object_refs": [
                            object_ref(
                                node_id="node:lysandra",
                                label="Lysandra",
                                kind="character",
                            ).model_dump()
                        ],
                        "matched_features": ["search_identity_workbench"],
                    }
                )
            ]
        }
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    loaded = store.load_overlay(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)

    enriched, _summary = apply_authored_overlay_to_graph_review_projection(
        projection,
        loaded,
    )

    survivor = enriched.node_views["party:captain_lysandra_ironveil"]
    assert "node:lysandra" not in enriched.node_views
    assert survivor.summary == "Led the charge at the wall and coordinated the party."
    assert len(survivor.evidence_badges) == 1
    assert len(survivor.adjacency) == 1
    assert "live_projection" in survivor.source_domains


def test_merge_resolves_legacy_node_ref_to_projection_node_id(
    store: GraphAuthoringOverlayStore,
) -> None:
    """Dogfood: overlay stores node:lysandra but projection uses character_lysandra."""
    rich_evidence = GraphProjectionEvidenceBadge(
        evidence_ref_id="ev-lysandra-1",
        source_artifact_id="session-recap",
        source_domain="recap",
        evidence_role="mention",
        is_focus_session_evidence=True,
        can_open_source=True,
        can_highlight_span=True,
    )
    projection = RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-23",
        graph_id="graph-1",
        markdown="[Lysandra](dmb-node:node:lysandra) at the wall.",
        focus=GraphFocusOverlay(focus_session_id="session-23"),
        node_views={
            "character_lysandra": GraphProjectionNodeView(
                node_id="character_lysandra",
                label="Lysandra",
                kind="character",
                role="source_evidence",
                aliases=["Lysandra"],
                source_domains=["recap", "live_projection"],
                evidence_badges=[rich_evidence],
                adjacency=[],
                summary="Ally from Mireward who recognizes her father.",
            ),
        },
        mentions=[],
        source_spans=[],
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                AuthoredGraphMergeObjectsAssertion.model_validate(
                    {
                        "assertion_id": "assert-legacy-id-merge",
                        "assertion_kind": "merge_objects",
                        "operation": "merge",
                        "campaign_id": CAMPAIGN_ID,
                        "session_id": "session-23",
                        "provenance": provenance().model_dump(),
                        "survivor_object_ref": object_ref(
                            node_id="party:captain_lysandra_ironveil",
                            label="Captain Lysandra Ironveil",
                            kind="companion",
                            role="companion",
                        ).model_dump(),
                        "merged_object_refs": [
                            object_ref(
                                node_id="node:lysandra",
                                label="Lysandra",
                                kind="character",
                            ).model_dump()
                        ],
                        "matched_features": ["search_identity_workbench"],
                    }
                )
            ]
        }
    )

    enriched, summary = apply_authored_overlay_to_graph_review_projection(projection, overlay)
    survivor = enriched.node_views["party:captain_lysandra_ironveil"]
    assert "character_lysandra" not in enriched.node_views
    assert len(survivor.evidence_badges) == 1
    assert survivor.summary == "Ally from Mireward who recognizes her father."
    assert "dmb-node:party:captain_lysandra_ironveil" in enriched.markdown
    assert not any(
        d.get("code") == "authored_overlay_assertion_unresolved_ref"
        and "node:lysandra" in d.get("message", "")
        for d in summary.diagnostics
    )
