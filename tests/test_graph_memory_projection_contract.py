from __future__ import annotations

import pytest
from pydantic import ValidationError

from graph_memory.projection import (
    GraphProjectionEvidenceBadge,
    RecapGraphProjection,
    build_focus_overlay,
    build_node_view,
    build_recap_graph_projection,
)
from graph_memory.union_supergraph.load import load_union_supergraph_store
from graph_memory.union_supergraph.model import UnionSupergraphStore


@pytest.fixture
def store() -> UnionSupergraphStore:
    return load_union_supergraph_store()


def test_build_focus_overlay_uses_focus_session_id(store: UnionSupergraphStore) -> None:
    overlay = build_focus_overlay(store)

    assert overlay.focus_session_id == "session-23"


def test_focus_overlay_collects_focus_evidence_and_edges(
    store: UnionSupergraphStore,
) -> None:
    overlay = build_focus_overlay(store)

    assert overlay.focused_evidence_ref_ids == [
        "evidence:session-23:caelynn:recap-mention"
    ]
    assert overlay.focused_edge_ids == [
        "edge:pc_caelynn:participated_in:event_session_23_mireward_gate"
    ]
    assert "pc_caelynn" in overlay.focused_node_ids
    assert "event_session_23_mireward_gate" in overlay.focused_node_ids


def test_build_node_view_returns_global_caelynn_view(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn")

    assert node_view.node_id == "pc_caelynn"
    assert node_view.label == "Caelynn"
    assert node_view.kind == "pc"
    assert node_view.role == "pc"
    assert node_view.source_domains == ["recap", "worldbuilding"]


def test_node_view_includes_focus_and_non_focus_evidence_badges(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn", focus_session_id="session-23")

    badges = {badge.evidence_ref_id: badge for badge in node_view.evidence_badges}
    assert (
        badges["evidence:session-23:caelynn:recap-mention"].is_focus_session_evidence
        is True
    )
    assert (
        badges[
            "evidence:worldbuilding:caelynn:character-note"
        ].is_focus_session_evidence
        is False
    )
    assert {badge.source_domain for badge in node_view.evidence_badges} == {
        "recap",
        "worldbuilding",
    }


def test_node_view_marks_caelynn_as_focus_anchored_for_session_23(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn", focus_session_id="session-23")

    assert node_view.anchored_to_focus_session is True


def test_node_view_includes_focus_and_non_focus_adjacency_candidates(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn", focus_session_id="session-23")

    candidates = {candidate.node_id: candidate for candidate in node_view.adjacency}
    assert (
        candidates["event_session_23_mireward_gate"].anchored_to_focus_session is True
    )
    assert candidates["event_session_23_mireward_gate"].predicate == "participated_in"
    assert candidates["loc_mirathorn"].anchored_to_focus_session is False
    assert candidates["loc_mirathorn"].source_domains == ["worldbuilding"]


def test_build_recap_graph_projection_returns_backend_neutral_payload(
    store: UnionSupergraphStore,
) -> None:
    projection = build_recap_graph_projection(store, session_id="session-23")

    assert isinstance(projection, RecapGraphProjection)
    assert projection.campaign_id == "longmont-c2"
    assert projection.session_id == "session-23"
    assert projection.graph_id == "longmont-c2:union-supergraph"
    assert projection.mentions == []


def test_build_recap_graph_projection_projects_markdown_mentions(
    store: UnionSupergraphStore,
) -> None:
    projection = build_recap_graph_projection(
        store,
        session_id="session-23",
        markdown="Caelynn looked toward Mirathorn.",
    )

    assert "[Caelynn](dmb-node:pc_caelynn)" in (projection.markdown or "")
    assert "[Mirathorn](dmb-node:loc_mirathorn)" in (projection.markdown or "")
    assert [mention.node_id for mention in projection.mentions] == [
        "pc_caelynn",
        "loc_mirathorn",
    ]


def test_recap_projection_contains_global_pc_caelynn_node_view(
    store: UnionSupergraphStore,
) -> None:
    projection = build_recap_graph_projection(store, session_id="session-23")

    caelynn = projection.node_views["pc_caelynn"]
    assert caelynn.label == "Caelynn"
    assert caelynn.anchored_to_focus_session is True
    assert {candidate.node_id for candidate in caelynn.adjacency} == {
        "event_session_23_mireward_gate",
        "loc_mirathorn",
    }


def test_projection_models_reject_invalid_basic_types() -> None:
    with pytest.raises(ValidationError, match="can_open_source"):
        GraphProjectionEvidenceBadge.model_validate(
            {
                "evidence_ref_id": "evidence:1",
                "source_artifact_id": "artifact:1",
                "source_domain": "recap",
                "evidence_role": "recap_mention",
                "can_open_source": "true",
            }
        )
