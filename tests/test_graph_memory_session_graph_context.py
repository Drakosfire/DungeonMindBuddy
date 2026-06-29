"""Tests for session graph context and party registry normalization."""

from __future__ import annotations

from src.graph_memory import party_context as pc
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    run_category_pipeline,
)
from src.graph_memory.session_graph_context import (
    build_session_graph_context,
    merge_party_anchor_nodes,
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


def test_session_23_context_warns_missing_roster():
    ctx = build_session_graph_context("longmont-c2", 23)
    assert ctx.session_number == 23
    assert ctx.session_id == "session-23"
    assert ctx.anchor_members == ()
    assert any("session_pc_rosters['23']" in w for w in ctx.warnings)


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


def test_run_category_pipeline_injects_party_anchors_for_session_22():
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
    anchor_ids = {
        n.get("corpus_ref", {}).get("ref_id")
        for n in result.candidate_graph.get("nodes", [])
        if n.get("context_anchor")
    }
    assert "captain_lysandra_ironveil" in anchor_ids
    assert "thrin_branchborn" in anchor_ids
    diagnostics = result.consolidation_diagnostics
    assert diagnostics["inserted_party_anchor_slugs"]
    assert diagnostics["session_graph_context_warnings"] == []
