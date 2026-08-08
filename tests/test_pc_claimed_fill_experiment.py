"""Unit tests for claimed-PC fill experiment helpers (no live LLM)."""

from __future__ import annotations

from evals.graph_memory_layer.pc_claimed_fill_experiment import (
    STUB_DESCRIPTION,
    apply_fill_to_candidate_graph,
    build_claims_from_mentions,
    build_claim_packet,
    score_baseline_stubs,
    score_fill,
)


def test_build_claims_from_mentions_groups_pc_and_companion() -> None:
    payload = {
        "mentions": [
            {
                "canonical_entity_id": "node:ephanna",
                "display_name": "Ephanna",
                "entity_kind": "pc",
                "entity_slug": "ephanna",
                "source_span_ref_id": "span:a",
                "surface_text": "Ephanna",
            },
            {
                "canonical_entity_id": "node:ephanna",
                "display_name": "Ephanna",
                "entity_kind": "pc",
                "entity_slug": "ephanna",
                "source_span_ref_id": "span:b",
                "surface_text": "Ephanna",
            },
            {
                "canonical_entity_id": "node:thrin-branchborn",
                "display_name": "Thrin",
                "entity_kind": "companion",
                "entity_slug": "thrin-branchborn",
                "source_span_ref_id": "span:a",
                "surface_text": "Thrin",
            },
            {
                "canonical_entity_id": "node:orik",
                "display_name": "Orik",
                "entity_kind": "npc",
                "entity_slug": "orik",
                "source_span_ref_id": "span:a",
                "surface_text": "Orik",
            },
        ]
    }
    claims = build_claims_from_mentions(payload)
    assert [c.node_id for c in claims] == ["node:ephanna", "node:thrin-branchborn"]
    assert claims[0].mention_count == 2
    assert claims[0].source_span_ref_ids == ("span:a", "span:b")


def test_score_fill_pass_gates_and_apply() -> None:
    mentions = {
        "mentions": [
            {
                "canonical_entity_id": "node:ephanna",
                "display_name": "Ephanna",
                "entity_kind": "pc",
                "entity_slug": "ephanna",
                "source_span_ref_id": "span:1",
                "surface_text": "Ephanna",
            }
        ]
    }
    candidate = {
        "nodes": [
            {
                "node_id": "node:ephanna",
                "label": "Ephanna",
                "description": STUB_DESCRIPTION,
                "proposed_action": "anchor",
                "context_anchor": True,
                "evidence_refs": [
                    {"source_span_ref_id": "span:1", "anchor_quotes": ["Ephanna"]}
                ],
            },
            {
                "node_id": "node:orik",
                "label": "Orik",
                "description": "Mayor",
                "proposed_action": "create",
                "evidence_refs": [],
            },
        ],
        "edges": [],
    }
    span_index = {
        "spans": [
            {
                "kind": "paragraph",
                "source_span_ref_id": "span:1",
                "line_start": 1,
                "line_end": 1,
                "text": "Ephanna hurls a bolt at the hybrid.",
            }
        ]
    }
    packet = build_claim_packet(
        mentions_payload=mentions,
        candidate_graph=candidate,
        span_index=span_index,
        source_text="Ephanna hurls a bolt at the hybrid.\n",
    )
    baseline = score_baseline_stubs(packet)
    assert baseline["stub_description_count"] == 1
    assert baseline["action_evidence_refs"] == 0

    parsed = {
        "filled_nodes": [
            {
                "node_id": "node:ephanna",
                "label": "Ephanna",
                "node_type": "character",
                "description": "Ephanna hurls a bolt at the hybrid during the gate fight.",
                "importance": "high",
                "session_actions": ["hurls a bolt at the hybrid"],
                "evidence_refs": [
                    {
                        "source_span_ref_id": "span:1",
                        "anchor_quotes": ["Ephanna hurls a bolt at the hybrid"],
                    }
                ],
            }
        ],
        "participation_edges": [
            {
                "edge_id": "edge:ephanna-orik",
                "from_node_id": "node:ephanna",
                "to_node_id": "node:orik",
                "predicate": "allied_with",
                "description": None,
                "evidence_refs": [
                    {
                        "source_span_ref_id": "span:1",
                        "anchor_quotes": ["Ephanna hurls a bolt at the hybrid"],
                    }
                ],
            }
        ],
    }
    score = score_fill(packet=packet, parsed=parsed)
    assert score.verdict == "PASS"
    assert score.session_description_count == 1
    assert score.action_evidence_refs == 1
    assert score.invented_node_ids == []

    enriched = apply_fill_to_candidate_graph(
        candidate, parsed=parsed, claimed_ids={"node:ephanna"}
    )
    eph = next(n for n in enriched["nodes"] if n["node_id"] == "node:ephanna")
    assert "hurls a bolt" in eph["description"]
    assert eph["enriched_by"] == "pc_claimed_fill_pass"
    assert len(enriched["edges"]) == 1


def test_score_open_extract_against_claims_coverage() -> None:
    from evals.graph_memory_layer.pc_claimed_fill_experiment import (
        ClaimedEntity,
        score_open_extract_against_claims,
    )

    claims = [
        ClaimedEntity(
            node_id="node:ephanna",
            label="Ephanna",
            entity_kind="pc",
            entity_slug="ephanna",
            mention_count=1,
            source_span_ref_ids=("span:1",),
            surface_texts=("Ephanna",),
        )
    ]
    nodes = [
        {
            "node_id": "npc_ephanna",
            "label": "Ephanna",
            "description": "Casts Eldritch Blast at the hybrid.",
            "evidence_refs": [
                {
                    "source_span_ref_id": "span:1",
                    "anchor_quotes": ["Ephanna uses Eldritch Blast"],
                }
            ],
        }
    ]
    rows = [
        {
            "source_span_ref_id": "span:1",
            "text": "Ephanna uses Eldritch Blast on the monster.",
        }
    ]
    score = score_open_extract_against_claims(
        claims=claims, observation_nodes=nodes, source_rows=rows
    )
    assert score["verdict"] == "PASS"
    assert score["roster_covered_count"] == 1
    assert score["missing_claim_ids"] == []
