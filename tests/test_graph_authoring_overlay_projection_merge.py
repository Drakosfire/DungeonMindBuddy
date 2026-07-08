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


def test_overlay_local_merge_still_applies_without_durable_redirect(
    store: GraphAuthoringOverlayStore,
) -> None:
    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        _projection_with_duplicates(),
        create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
            update={"assertions": [merge_assertion()]}
        ),
    )
    assert "merged-node" not in enriched.node_views
    assert "survivor-node" in enriched.node_views
    assert summary.projected_merge_objects_count >= 1


def test_durable_redirect_prevents_duplicate_overlay_merge(
    store: GraphAuthoringOverlayStore,
) -> None:
    from graph_memory.projection.recap_projection import build_recap_graph_projection
    from tests.test_graph_memory_union_projection_identity_redirects import (
        _lysandra_applied_store,
    )

    durable_projection = build_recap_graph_projection(
        _lysandra_applied_store(),
        session_id="session-23",
        markdown="[Lysandra](dmb-node:node:lysandra) traveled.",
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                AuthoredGraphMergeObjectsAssertion.model_validate(
                    {
                        "assertion_id": "assert-merge-lysandra",
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
                    }
                )
            ]
        }
    )

    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        durable_projection,
        overlay,
    )

    assert "node:lysandra" not in enriched.node_views
    assert "party:captain_lysandra_ironveil" in enriched.node_views
    assert any(
        d.code == "union_identity_overlay_merge_skipped_durable"
        for d in summary.diagnostics
    )
    survivor = enriched.node_views["party:captain_lysandra_ironveil"]
    assert len(survivor.aliases) == len(
        set(durable_projection.node_views["party:captain_lysandra_ironveil"].aliases)
    )


def test_relationship_resolves_merged_away_target_through_durable_redirect() -> None:
    projection = RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-23",
        graph_id="graph-1",
        markdown="[the wall](dmb-node:location_the_wall) near Mireward Reach.",
        focus=GraphFocusOverlay(focus_session_id="session-23"),
        node_views={
            "location_the_wall": GraphProjectionNodeView(
                node_id="location_the_wall",
                label="the wall",
                kind="location",
                role="location",
                aliases=[],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            ),
            "location_mireward_reach": GraphProjectionNodeView(
                node_id="location_mireward_reach",
                label="Mireward Reach",
                kind="location",
                role="location",
                aliases=[],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
                merged_away_ids=["node:mireward-reach"],
            ),
        },
        mentions=[],
        source_spans=[],
        union_identity_applied_assertion_ids=["assert-merge-mireward"],
    )
    from tests.test_graph_authoring_overlay_models import relationship_assertion

    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                relationship_assertion(
                    assertion_id="assert-wall-located-in",
                    source_object_ref={
                        "ref_kind": "existing_graph_node",
                        "node_id": "location_the_wall",
                        "label": "the wall",
                        "kind": "location",
                    },
                    target_object_ref={
                        "ref_kind": "existing_graph_node",
                        "node_id": "node:mireward-reach",
                        "label": "Mireward Reach",
                        "kind": "location",
                    },
                    relationship_type="located_in",
                )
            ]
        }
    )

    enriched, summary = apply_authored_overlay_to_graph_review_projection(projection, overlay)
    wall = enriched.node_views["location_the_wall"]
    assert any(
        edge.predicate == "located_in" and edge.node_id == "location_mireward_reach"
        for edge in wall.adjacency
    )
    assert not any(
        d.code == "authored_overlay_assertion_unresolved_ref"
        and "node:mireward-reach" in d.message
        for d in summary.diagnostics
    )


def test_alias_seed_resolves_merged_away_link_existing_through_durable_redirect() -> None:
    projection = RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-23",
        graph_id="graph-1",
        markdown="Lysandra is surprised. Later Lysandra returns.",
        focus=GraphFocusOverlay(focus_session_id="session-23"),
        node_views={
            "character_captain_lysandra_ironveil": GraphProjectionNodeView(
                node_id="character_captain_lysandra_ironveil",
                label="Captain Lysandra Ironveil",
                kind="pc",
                role="pc",
                aliases=["Captain Lysandra Ironveil"],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
                merged_away_ids=["node:lysandra"],
            ),
        },
        mentions=[],
        source_spans=[],
        union_identity_applied_assertion_ids=["assert-merge-lysandra"],
    )
    from tests.test_graph_authoring_overlay_models import link_existing_assertion

    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                link_existing_assertion(
                    assertion_id="assert-lysandra-link",
                    selected_text="Lysandra",
                    normalized_selected_text="Lysandra",
                    existing_object_ref={
                        "ref_kind": "existing_graph_node",
                        "node_id": "node:lysandra",
                        "label": "Lysandra",
                        "kind": "character",
                    },
                    source_anchor={
                        "anchor_kind": "text_span",
                        "selected_text": "Lysandra",
                        "normalized_selected_text": "Lysandra",
                        "surrounding_text_before": "",
                        "surrounding_text_after": " is surprised.",
                    },
                )
            ]
        }
    )

    enriched, summary = apply_authored_overlay_to_graph_review_projection(projection, overlay)
    assert enriched.markdown.count("dmb-node:character_captain_lysandra_ironveil") == 2
    assert not any(
        d.code == "authored_overlay_assertion_unresolved_ref"
        and "node:lysandra" in d.message
        for d in summary.diagnostics
    )
    assert not any(d.code == "authored_alias_seed_unresolved_target" for d in summary.diagnostics)
