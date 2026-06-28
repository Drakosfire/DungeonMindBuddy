from __future__ import annotations

from pathlib import Path

from graph_memory.projection import build_node_view, build_recap_graph_projection
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.union_supergraph.preview_import import (
    CandidateGraphInput,
    build_preview_union_supergraph,
)
from graph_memory.union_supergraph.validate import validate_union_supergraph_fixture

ROOT = Path(__file__).resolve().parents[1]
SESSION_22_RUN2 = (
    ROOT
    / "evals/graph_memory_layer/artifacts/category_graph_model_study/2026-06-26/anchor_quote_n3/session_22_gpt-5-4-mini_run2/candidate_output.json"
)
SESSION_22_RECAP = (
    ROOT
    / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md"
)
SESSION_23_GOLD = (
    ROOT / "evals/graph_memory_layer/examples/session_23_candidate_graph_gold/candidate_graph_gold.json"
)


def build_store_payload() -> dict:
    return build_preview_union_supergraph(
        [
            CandidateGraphInput(
                path=SESSION_22_RUN2,
                session_id="session-22",
                recap_path=SESSION_22_RECAP,
            ),
            CandidateGraphInput(path=SESSION_23_GOLD, session_id="session-23"),
        ],
        focus_session_id="session-23",
    )


def test_two_session_preview_union_supergraph_validates() -> None:
    payload = build_store_payload()
    report = validate_union_supergraph_fixture(payload)

    assert report["valid"] is True
    assert report["focus_session_ids"] == ["session-22", "session-23"]
    assert any(
        "session-23" in edge["session_ids"] for edge in payload["edges"].values()
    )
    assert any(
        "session-23" not in edge["session_ids"] for edge in payload["edges"].values()
    )
    assert report["multi_domain_node_count"] > 0
    assert payload["diagnostics"]["preview_import"] is True
    assert payload["diagnostics"]["canon_promotion"] is False
    assert payload["diagnostics"]["approved_memory_write"] is False


def test_anchor_quote_repair_preserves_verified_source_offsets() -> None:
    payload = build_store_payload()
    repaired = [
        match
        for evidence in payload["evidence"].values()
        for match in evidence.get("anchor_quote_matches", [])
        if match.get("repaired_from") == "the uniform of the Elderwild Reach"
    ]

    assert repaired
    assert repaired[0]["quote"] == "the soldier’s uniform of the Elderwild Reach"
    assert repaired[0]["match_text"] == "the soldier’s uniform of the Elderwild Reach"


def test_lysandro_accumulates_session_22_session_23_and_worldbuilding_evidence() -> None:
    payload = build_store_payload()
    store = UnionSupergraphStore.model_validate(payload)
    lysandro = build_node_view(store, "character_lysandro", focus_session_id="session-23")
    badges_by_session = {
        badge.evidence_ref_id: badge.is_focus_session_evidence
        for badge in lysandro.evidence_badges
    }

    assert lysandro.source_domains == ["recap", "worldbuilding"]
    assert any(":session-22:" in evidence_id for evidence_id in badges_by_session)
    assert any(":session-23:" in evidence_id for evidence_id in badges_by_session)
    assert any(not is_focus for is_focus in badges_by_session.values())
    assert any(is_focus for is_focus in badges_by_session.values())


def test_session_23_projection_marks_prior_session_edges_as_non_focus_context() -> None:
    payload = build_store_payload()
    store = UnionSupergraphStore.model_validate(payload)
    projection = build_recap_graph_projection(
        store,
        session_id="session-23",
        markdown="Lysandro and Lysandra face Mireward together.",
    )
    lysandro = projection.node_views["character_lysandro"]

    assert "[Lysandro](dmb-node:character_lysandro)" in (projection.markdown or "")
    assert lysandro.anchored_to_focus_session is True
    assert any(candidate.anchored_to_focus_session for candidate in lysandro.adjacency)
    assert any(not candidate.anchored_to_focus_session for candidate in lysandro.adjacency)
    assert all(
        "session-23" in store.edges[edge_id].session_ids
        for edge_id in projection.focus.focused_edge_ids
    )
