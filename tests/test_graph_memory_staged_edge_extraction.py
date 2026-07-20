"""Tests for staged edge extraction (observe → bind → normalize → assemble)."""

from __future__ import annotations

from src.graph_memory.extraction.staged_edge_extraction import (
    assemble_staged_edges,
    bind_phrase_to_node,
    bind_relation_candidate,
    normalize_bound_candidate,
    normalize_raw_relation,
    normalize_relation_candidate,
    relation_observation_json_schema,
    relation_observation_text_format,
    render_relation_observation_prompt,
)


def test_relation_observation_schema_is_strict_json_schema():
    fmt = relation_observation_text_format()
    assert fmt["format"]["type"] == "json_schema"
    assert fmt["format"]["strict"] is True
    schema = relation_observation_json_schema()
    assert "relation_candidates" in schema["required"]


def test_normalize_relation_candidate_shape():
    raw = {
        "candidate_id": "rc_1",
        "subject_phrase": "Brin Holloway",
        "raw_relation": "leads",
        "object_phrase": "Edge survivors",
        "source_span_ref_id": "session-23:recap:paragraph:006",
        "anchor_quotes": ["A clear leader of the group steps forward, Brin Holloway"],
        "rationale": None,
    }
    out = normalize_relation_candidate(raw)
    assert out["candidate_id"] == "rc_1"
    assert out["subject_phrase"] == "Brin Holloway"
    assert out["anchor_quotes"]


def test_bind_phrase_prefers_edge_refugees_alias():
    nodes = [
        {"node_id": "group_edge_survivors", "label": "Edge Survivors", "node_type": "group"},
        {"node_id": "loc_edge", "label": "Edge", "node_type": "location"},
    ]
    bound = bind_phrase_to_node("Edge refugees", nodes)
    assert bound["node_id"] == "group_edge_survivors"
    assert bound["binding_status"] == "bound"
    assert bound["score"] >= 0.55


def test_bind_relation_candidate_marks_unbound_subject():
    nodes = [{"node_id": "n1", "label": "Mireward Reach", "node_type": "location"}]
    candidate = normalize_relation_candidate(
        {
            "candidate_id": "rc_x",
            "subject_phrase": "Totally Unknown Actor",
            "raw_relation": "governs",
            "object_phrase": "Mireward Reach",
            "source_span_ref_id": "sp1",
            "anchor_quotes": ["governs"],
            "rationale": None,
        }
    )
    bound = bind_relation_candidate(candidate, nodes)
    assert bound["binding_status"] == "unbound_subject"
    assert bound["to_node_id"] == "n1"


def test_normalize_raw_relation_maps_phrases_to_catalog():
    pred = normalize_raw_relation("is mayor of")
    assert pred["relationship_type"] == "governs"
    assert pred["predicate_status"] == "mapped_from_phrase"
    assert pred["issues"] == []

    unknown = normalize_raw_relation("recognizes her father")
    assert unknown["predicate_status"] == "unknown_predicate"


def test_assemble_staged_edges_emits_bound_candidate_and_drops_unbound():
    normalized = [
        normalize_bound_candidate(
            bind_relation_candidate(
                normalize_relation_candidate(
                    {
                        "candidate_id": "rc_ok",
                        "subject_phrase": "Brin Holloway",
                        "raw_relation": "leads",
                        "object_phrase": "Edge Survivors",
                        "source_span_ref_id": "sp1",
                        "anchor_quotes": ["leader"],
                        "rationale": None,
                    }
                ),
                [
                    {"node_id": "npc_brin", "label": "Brin Holloway", "node_type": "character"},
                    {"node_id": "group_edge_survivors", "label": "Edge Survivors", "node_type": "group"},
                ],
            )
        ),
        normalize_bound_candidate(
            bind_relation_candidate(
                normalize_relation_candidate(
                    {
                        "candidate_id": "rc_bad",
                        "subject_phrase": "Unknown",
                        "raw_relation": "leads",
                        "object_phrase": "Edge Survivors",
                        "source_span_ref_id": "sp2",
                        "anchor_quotes": ["leader"],
                        "rationale": None,
                    }
                ),
                [
                    {"node_id": "group_edge_survivors", "label": "Edge Survivors", "node_type": "group"},
                ],
            )
        ),
    ]
    edges, diag = assemble_staged_edges(
        normalized,
        allowed_span_refs={"sp1", "sp2"},
        node_ids={"npc_brin", "group_edge_survivors"},
    )
    assert len(edges) == 1
    assert edges[0]["relationship_type"] == "leads"
    assert edges[0]["semantic_state"] == {
        "canon_state": "played_canon",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "system_derived",
        "visibility_state": "gm_private",
    }
    assert "canon_status" not in edges[0]["semantic_state"]
    assert diag["assembled_edge_count"] == 1
    assert diag["drop_counts_by_reason"].get("unbound_subject") == 1


def test_render_relation_observation_prompt_includes_graph_context_and_source():
    prompt = render_relation_observation_prompt(
        [
            {
                "source_span_ref_id": "session-23:recap:paragraph:001",
                "source_unit_id": "paragraph:001",
                "line_start": 1,
                "line_end": 3,
                "text": "Mayor Orik Tane governs Mireward.",
            }
        ],
        nodes=[{"node_id": "npc_orik", "label": "Orik Tane", "node_type": "character"}],
        beats=[{"beat_id": "b1", "order": 1, "title": "Arrival", "summary": "Arrive", "involved_node_ids": []}],
    )
    assert "relation_candidates" in prompt
    assert "## Source Packet" in prompt
    assert "Graph context" in prompt
    assert "Consolidated nodes" in prompt
    assert "Mayor Orik Tane governs Mireward" in prompt
