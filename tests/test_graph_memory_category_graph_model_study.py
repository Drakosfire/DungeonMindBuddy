"""Tests for category-decomposed graph model study (no API calls)."""

from __future__ import annotations

import json

import pytest

from evals.graph_memory_layer.category_graph_model_study import (
    assemble_envelope,
    consolidate_category_outputs,
    compare_to_s22_gold,
    ensure_s22_run_bundle,
    parse_json_object,
    render_category_pass_prompts,
    sanitize_parts,
    s22_run_bundle_dir,
    verified_s22_source,
)
from evals.graph_memory_layer.reconcile_live_candidate import validate_live_candidate_output
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    repair_edge_evidence_refs,
)
from src.graph_memory.party_context import build_party_context


def test_render_category_pass_prompts_deterministic():
    verified = verified_s22_source()
    a = render_category_pass_prompts(verified, session=22)
    b = render_category_pass_prompts(verified, session=22)
    assert a == b
    assert "actor_pass.md" in a
    assert "beat_pass.md" in a
    assert "edge_pass.md" in a
    joined = "\n".join(a.values())
    assert "source_span_ref_id" in joined
    assert "anchor_quotes" in joined
    assert "thrin_branchborn" in joined or "Party anchors" in joined
    assert "Do NOT extract player characters" in joined


def test_parse_json_object_strips_fence():
    raw = '```json\n{"observation_nodes": []}\n```'
    assert parse_json_object(raw) == {"observation_nodes": []}


def test_consolidate_records_party_companion_context():
    pass_outputs = {
        "actor_pass": {
            "observation_nodes": [
                {
                    "node_id": "npc:grobnok",
                    "label": "Grobnok",
                    "node_type": "character",
                    "description": "operator",
                    "importance": "high",
                    "evidence_refs": [{"source_span_ref_id": "spref:session-22:p001"}],
                }
            ],
        },
        "location_pass": {"observation_nodes": []},
        "collective_pass": {"observation_nodes": []},
        "object_pass": {"observation_nodes": []},
        "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
        "beat_pass": {"observation_beats": []},
        "edge_pass": {"observation_edges": []},
    }
    out = consolidate_category_outputs(pass_outputs, session=22)
    assert out["consolidation_diagnostics"]["party_companion_slugs"] == [
        "thrin_branchborn",
        "captain_lysandra_ironveil",
    ]
    assert len(out["nodes"]) >= 1


def test_consolidate_drops_edges_with_missing_endpoints():
    pass_outputs = {
        "actor_pass": {"observation_nodes": []},
        "location_pass": {"observation_nodes": []},
        "collective_pass": {"observation_nodes": []},
        "object_pass": {"observation_nodes": []},
        "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
        "beat_pass": {"observation_beats": []},
        "edge_pass": {
            "observation_edges": [
                {
                    "edge_id": "e:bad",
                    "from_node_id": "missing_a",
                    "to_node_id": "missing_b",
                    "label": "bad edge",
                    "relationship_type": "knows_about",
                    "evidence_refs": [{"source_span_ref_id": "spref:session-22:p001"}],
                }
            ],
        },
    }
    out = consolidate_category_outputs(pass_outputs, session=22)
    assert out["edges"] == []
    assert len(out["consolidation_diagnostics"]["dropped_edges_missing_endpoints"]) == 1


def test_assemble_envelope_shape():
    consolidated = consolidate_category_outputs(
        {
            "actor_pass": {"observation_nodes": []},
            "location_pass": {"observation_nodes": []},
            "collective_pass": {"observation_nodes": []},
            "object_pass": {"observation_nodes": []},
            "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
            "beat_pass": {"observation_beats": []},
            "edge_pass": {"observation_edges": []},
        },
        session=22,
    )
    envelope = assemble_envelope(consolidated)
    assert envelope["schema"] == "dmb_live_extractor_candidate_envelope_v0"
    assert "candidate_graph" in envelope
    assert "review_sidecar" in envelope
    graph = envelope["candidate_graph"]
    assert graph["schema"] == "dmb_candidate_graph_preview_v0"
    assert isinstance(graph["nodes"], list)
    assert graph["diagnostics"]["llm_used"] is False
    assert graph["diagnostics"]["preview_only"] is True


def test_compare_to_s22_gold_returns_scores():
    consolidated = consolidate_category_outputs(
        {
            "actor_pass": {"observation_nodes": []},
            "location_pass": {"observation_nodes": []},
            "collective_pass": {"observation_nodes": []},
            "object_pass": {"observation_nodes": []},
            "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
            "beat_pass": {"observation_beats": []},
            "edge_pass": {"observation_edges": []},
        },
        session=22,
    )
    envelope = assemble_envelope(consolidated)
    report = compare_to_s22_gold(envelope)
    assert "scores" in report
    assert "node_recall" in report["scores"]
    assert report["gold_fixture_id"]


def test_compare_seeds_companion_nodes_into_recall():
    # An empty candidate graph still credits standing party companions (Thrin,
    # Lysandra) because party context supplies them deterministically; they are
    # real graph entities, not session-novel extractions the model must rediscover.
    empty = consolidate_category_outputs(
        {
            "actor_pass": {"observation_nodes": []},
            "location_pass": {"observation_nodes": []},
            "collective_pass": {"observation_nodes": []},
            "object_pass": {"observation_nodes": []},
            "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
            "beat_pass": {"observation_beats": []},
            "edge_pass": {"observation_edges": []},
        },
        session=22,
    )
    report = compare_to_s22_gold(assemble_envelope(empty))
    missing = {m["label"] for m in report["coverage"]["missing_gold_nodes"]}
    assert "Lysandra" not in missing
    assert "Thrin" not in missing


def test_compare_rescues_spref_divergent_node_over_gold_span():
    # A candidate node that cites the same source paragraph as a gold node (via a
    # spref line range, not the gold anchor id) and shares >=2 content tokens is
    # credited, even though its label phrasing diverges.
    from evals.graph_memory_layer.category_graph_model_study import s22_spref_line_map

    spref_at_23 = next(sp for sp, (s, _e) in s22_spref_line_map().items() if s == 23)
    consolidated = consolidate_category_outputs(
        {
            "actor_pass": {"observation_nodes": []},
            "location_pass": {"observation_nodes": []},
            "collective_pass": {"observation_nodes": []},
            "object_pass": {"observation_nodes": []},
            "thread_pass": {
                "observation_nodes": [
                    {
                        "node_id": "clue:puddles",
                        "label": "Roadside puddles show delayed reflections",
                        "node_type": "clue",
                        "evidence_refs": [{"source_span_ref_id": spref_at_23}],
                    }
                ],
                "ignored_items": [],
                "deferred_items": [],
            },
            "beat_pass": {"observation_beats": []},
            "edge_pass": {"observation_edges": []},
        },
        session=22,
    )
    report = compare_to_s22_gold(assemble_envelope(consolidated))
    missing = {m["label"] for m in report["coverage"]["missing_gold_nodes"]}
    assert "Delayed puddle reflections" not in missing


def test_normalize_evidence_refs_preserves_anchor_quotes():
    from evals.graph_memory_layer.category_graph_model_study import _normalize_evidence_refs

    allowed = {"spref:session-22:p004"}
    refs = _normalize_evidence_refs(
        [
            {
                "source_span_ref_id": "session-22:p004",
                "anchor_quotes": ["the reflections are somewhat delayed", ""],
            }
        ],
        allowed,
    )
    assert refs == [
        {
            "source_span_ref_id": "spref:session-22:p004",
            "anchor_quotes": ["the reflections are somewhat delayed"],
        }
    ]


def test_ensure_s22_run_bundle_writes_files():
    bundle_dir = ensure_s22_run_bundle(allow_overwrite=True)
    assert (bundle_dir / "run_manifest.json").is_file()
    assert (bundle_dir / "source_units.json").is_file()


def test_s22_envelope_passes_live_validation_with_evidence():
    consolidated = consolidate_category_outputs(
        {
            "actor_pass": {
                "observation_nodes": [
                    {
                        "node_id": "npc:grobnok",
                        "label": "Grobnok",
                        "node_type": "character",
                        "description": "operator",
                        "importance": "high",
                        "evidence_refs": [{"source_span_ref_id": "spref:session-22:p001"}],
                    }
                ],
            },
            "location_pass": {"observation_nodes": []},
            "collective_pass": {"observation_nodes": []},
            "object_pass": {"observation_nodes": []},
            "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
            "beat_pass": {"observation_beats": []},
            "edge_pass": {"observation_edges": []},
        },
        session=22,
    )
    envelope = assemble_envelope(consolidated)
    report = validate_live_candidate_output(
        envelope,
        run_bundle=s22_run_bundle_dir(),
        allowed_span_refs={"spref:session-22:p001"},
    )
    assert report["canonical_ir_valid"]
    node = report["reconciled_candidate_graph"]["nodes"][0]
    assert node["evidence_refs"][0]["can_highlight_span"]


def test_sanitize_normalizes_spref_prefix():
    allowed = {"spref:session-22:p001", "spref:session-22:p002"}
    parts = {
        "nodes": [
            {
                "node_id": "npc:grobnok",
                "label": "Grobnok",
                "evidence_refs": [{"source_span_ref_id": "session-22:p001"}],
            },
            {
                "node_id": "npc:bad",
                "label": "Bad",
                "evidence_refs": [{"source_span_ref_id": "spref_session22_invalid"}],
            },
        ],
        "edges": [],
        "beats": [],
    }
    sanitized, diag = sanitize_parts(parts, allowed)
    assert len(sanitized["nodes"]) == 1
    assert sanitized["nodes"][0]["evidence_refs"] == [{"source_span_ref_id": "spref:session-22:p001"}]
    assert "npc:bad" in diag["dropped_no_valid_evidence"]["nodes"]


def test_repair_edge_evidence_inherits_from_endpoint():
    allowed = {"spref:session-22:p001"}
    parts = {
        "nodes": [
            {
                "node_id": "npc:a",
                "label": "A",
                "evidence_refs": [{"source_span_ref_id": "session-22:p001"}],
            },
            {
                "node_id": "npc:b",
                "label": "B",
                "evidence_refs": [{"source_span_ref_id": "session-22:p001"}],
            },
        ],
        "edges": [
            {
                "edge_id": "e:1",
                "from_node_id": "npc:a",
                "to_node_id": "npc:b",
                "label": "knows",
                "relationship_type": "knows_about",
                "evidence_refs": [{"source_span_ref_id": "spref_session22_hallucinated"}],
            }
        ],
    }
    diag = repair_edge_evidence_refs(parts, allowed)
    assert diag["repaired_edge_evidence_refs"] == 1
    assert diag["edge_evidence_inheritance"] is True
    assert parts["edges"][0]["evidence_refs"] == [{"source_span_ref_id": "spref:session-22:p001"}]


def test_repair_edge_evidence_skips_inheritance_when_disabled():
    allowed = {"spref:session-22:p001"}
    parts = {
        "nodes": [
            {
                "node_id": "npc:a",
                "label": "A",
                "evidence_refs": [{"source_span_ref_id": "session-22:p001"}],
            },
            {
                "node_id": "npc:b",
                "label": "B",
                "evidence_refs": [{"source_span_ref_id": "session-22:p001"}],
            },
        ],
        "edges": [
            {
                "edge_id": "e:1",
                "from_node_id": "npc:a",
                "to_node_id": "npc:b",
                "label": "commands",
                "relationship_type": "commands",
                "evidence_refs": [],
            }
        ],
    }
    diag = repair_edge_evidence_refs(parts, allowed, inherit_from_endpoints=False)
    assert diag["repaired_edge_evidence_refs"] == 0
    assert diag["edge_evidence_inheritance"] is False
    assert parts["edges"][0]["evidence_refs"] == []
