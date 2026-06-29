"""Tests for taxonomy-backed edge extraction prompt and comparison diagnostics."""

from __future__ import annotations

from evals.graph_memory_layer.live_vs_gold_compare import compare_parts
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    render_category_pass_prompts,
)
from src.graph_memory.party_context import build_party_context_for_campaign


def test_edge_pass_prompt_includes_predicate_catalog():
    party_ctx = build_party_context_for_campaign("longmont-c2", 23)
    prompts = render_category_pass_prompts([], party_ctx=party_ctx)
    edge_prompt = prompts["edge_pass.md"]
    assert "Controlled edge predicates" in edge_prompt
    assert "`predicate_family`" in edge_prompt
    assert "`parent_of`" in edge_prompt
    assert "Do not invent verbs" in edge_prompt


def test_compare_parts_reports_edge_miss_diagnostics():
    gold_parts = {
        "nodes": [
            {"node_id": "g_a", "label": "Grobnok", "node_type": "character"},
            {"node_id": "g_b", "label": "Sara", "node_type": "character"},
        ],
        "edges": [
            {
                "edge_id": "e_gold",
                "from_node_id": "g_a",
                "to_node_id": "g_b",
                "label": "parent",
                "relationship_type": "parent_of",
            }
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
    }
    live_parts = {
        "nodes": [
            {"node_id": "c_a", "label": "Grobnok", "node_type": "character"},
            {"node_id": "c_b", "label": "Sara", "node_type": "character"},
        ],
        "edges": [
            {
                "edge_id": "e_live",
                "from_node_id": "c_a",
                "to_node_id": "c_b",
                "label": "recognizes",
                "relationship_type": "recognizes",
            }
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
    }
    report = compare_parts(live_parts, gold_parts, gold_fixture_id="test-fixture")
    assert report["coverage"]["matched_edges"] == []
    edge_diag = report["diagnostics"]["edge_miss_diagnostics"]["e_gold"]
    assert edge_diag["reason"] == "family_mismatch"
    assert edge_diag["live_relationship_type"] == "recognizes"
    assert edge_diag["gold_relationship_type"] == "parent_of"

    live_parts["edges"] = [
        {
            "edge_id": "e_live",
            "from_node_id": "c_a",
            "to_node_id": "c_wrong",
            "label": "recognizes",
            "relationship_type": "recognizes",
        }
    ]
    report = compare_parts(live_parts, gold_parts, gold_fixture_id="test-fixture")
    missing = report["coverage"]["missing_gold_edges"]
    assert missing
    edge_diag = report["diagnostics"]["edge_miss_diagnostics"]["e_gold"]
    assert edge_diag["reason"] in {
        "endpoint_score_below_threshold",
        "endpoint_missing",
        "family_mismatch",
        "no_comparable_live_edge",
    }
