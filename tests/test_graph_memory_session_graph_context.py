"""Tests for session graph context and party registry normalization."""

from __future__ import annotations

from src.graph_memory import party_context as pc
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    run_category_pipeline,
)
from src.graph_memory import identity_resolution as ir
from src.graph_memory.session_graph_context import (
    PARTY_COLLECTIVE_LABEL,
    PARTY_COLLECTIVE_NODE_ID,
    build_session_graph_context,
    merge_party_anchor_nodes,
    merge_party_collective,
    normalize_registry_view,
)
from tests.fixtures.graph_memory.category_extraction_helpers import (
    minimal_category_pass_outputs,
)


def test_normalize_registry_view_maps_v1_rosters_to_v2_shape():
    v1 = {
        "schema": "party_registry_v1",
        "campaign_id": "longmont-c2",
        "pc_party_names": ["Questionable Company"],
        "session_pc_rosters": {"22": ["stafl", "bonogo"]},
        "session_companion_rosters": {"22": ["captain_lysandra_ironveil"]},
    }
    view = normalize_registry_view(v1)
    assert view["schema"] == "party_registry_v1"
    assert view["party_names"] == ["Questionable Company"]
    assert view["session_rosters"]["22"]["pcs"] == ["stafl", "bonogo"]
    assert view["session_rosters"]["22"]["companions"] == ["captain_lysandra_ironveil"]


def test_unrostered_session_context_warns_missing_roster():
    # Session 99 has no registry roster (session 23 now does, post-dogfood);
    # the missing-roster warning path is exercised with a genuinely empty session.
    ctx = build_session_graph_context("longmont-c2", 99)
    assert ctx.session_number == 99
    assert ctx.session_id == "session-99"
    assert ctx.anchor_members == ()
    assert any("session_pc_rosters['99']" in w for w in ctx.warnings)


def test_session_22_context_includes_lysandra_anchor():
    ctx = build_session_graph_context("longmont-c2", 22)
    slugs = {member.slug for member in ctx.anchor_members}
    assert "captain_lysandra_ironveil" in slugs
    assert "thrin_branchborn" in slugs
    assert not ctx.warnings


def test_merge_party_anchor_nodes_inserts_missing_companion():
    party_ctx = pc.build_party_context_for_campaign("longmont-c2", 22)
    nodes = [{"node_id": "node:bonogo", "label": "Bonogo", "node_type": "character", "evidence_refs": []}]
    merged, diag = merge_party_anchor_nodes(
        nodes,
        party_ctx,
        default_semantic_state={"status": "unknown"},
    )
    merged_slugs = {n.get("corpus_ref", {}).get("ref_id") for n in merged if n.get("context_anchor")}
    assert "captain_lysandra_ironveil" in merged_slugs
    assert "captain_lysandra_ironveil" in diag["inserted_party_anchor_slugs"]


def test_merge_party_collective_seeds_node_and_member_edges():
    party_ctx = pc.build_party_context_for_campaign("longmont-c2", 22)
    # Member anchor nodes present (as they would be after merge_party_anchor_nodes).
    nodes = [
        {
            "node_id": f"node:{m.slug.replace('_', '-')}",
            "label": m.display_name,
            "node_type": "character",
            "corpus_ref": m.corpus_ref(),
            "context_anchor": True,
            "evidence_refs": [],
        }
        for m in party_ctx.members
    ]
    merged_nodes, merged_edges, diag = merge_party_collective(
        nodes,
        [],
        party_ctx,
        default_semantic_state={"status": "unknown"},
    )
    # Collective node inserted and matchable to the gold heroes/party node.
    collective = [n for n in merged_nodes if n["node_id"] == PARTY_COLLECTIVE_NODE_ID]
    assert len(collective) == 1
    assert collective[0]["label"] == PARTY_COLLECTIVE_LABEL
    assert collective[0]["context_anchor"] is True
    assert diag["party_collective_inserted"] is True

    # One member_of edge per anchored member, all pointing at the collective.
    member_edges = [e for e in merged_edges if e["relationship_type"] == "member_of"]
    assert len(member_edges) == len(party_ctx.members)
    for edge in member_edges:
        assert edge["to_node_id"] == PARTY_COLLECTIVE_NODE_ID
        assert edge["predicate_family"] == "membership"
        assert edge["context_anchor"] is True
        assert ir.predicate_family(edge["relationship_type"]) == "membership"
    assert set(diag["party_membership_edge_slugs"]) == {m.slug for m in party_ctx.members}


def test_merge_party_collective_noop_without_members():
    party_ctx = pc.build_party_context_for_campaign("longmont-c2", 99)  # no roster
    nodes, edges, diag = merge_party_collective(
        [], [], party_ctx, default_semantic_state={"status": "unknown"}
    )
    assert nodes == [] and edges == []
    assert diag["party_collective_inserted"] is False
    assert diag["party_membership_edge_slugs"] == []


def test_run_category_pipeline_injects_party_anchors_for_session_22():
    """Party registry injects anchors at consolidate; promote IR drops empty-evidence ones."""
    spref = "session-22:recap:paragraph:001"
    span_index = {
        "spans": [
            {
                "kind": "paragraph",
                "span_id": spref,
                "source_span_ref_id": spref,
                "line_start": 1,
                "line_end": 3,
                "text": "Bonogo scouts the Mireward road.",
            }
        ]
    }
    result = run_category_pipeline(
        FixtureCategoryGraphPassClient(minimal_category_pass_outputs(spref)),
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-22",
            session_number=22,
            source_span_index=span_index,
            model_id="gpt-5.4-mini",
        ),
    )
    diagnostics = result.consolidation_diagnostics
    assert "captain_lysandra_ironveil" in diagnostics["inserted_party_anchor_slugs"]
    assert "thrin_branchborn" in diagnostics["inserted_party_anchor_slugs"]
    assert diagnostics["session_graph_context_warnings"] == []
    # Promote projection strips empty-evidence standing context until partition owns it.
    assert not any(
        n.get("context_anchor") for n in result.candidate_graph.get("nodes", [])
    )
    assert "captain_lysandra_ironveil" not in {
        n.get("corpus_ref", {}).get("ref_id")
        for n in result.candidate_graph.get("nodes", [])
        if isinstance(n.get("corpus_ref"), dict)
    }
