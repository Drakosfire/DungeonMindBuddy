"""Production party claimed-fill helpers and pipeline hook (no live LLM)."""

from __future__ import annotations


from src.graph_memory.extraction.category_candidate_graph_schema import (
    schema_for_pass,
    schema_for_pass_spec,
)
from src.graph_memory.extraction.extraction_profile import ExtractionPassSpec
from src.graph_memory.extraction.party_claimed_fill import (
    PASS_NAME,
    STUB_DESCRIPTION,
    apply_fill_to_nodes,
    build_claims_from_mentions,
    party_claimed_fill_json_schema,
)


def test_claimed_fill_schema_is_nodes_only() -> None:
    schema = party_claimed_fill_json_schema()
    assert set(schema["required"]) == {"filled_nodes"}
    assert "participation_edges" not in schema["properties"]
    filled_node = schema["properties"]["filled_nodes"]["items"]
    assert set(filled_node["properties"]) == {"node_id", "source_contexts"}
    assert "description" not in filled_node["properties"]
    assert "session_actions" not in filled_node["properties"]
    assert schema_for_pass(PASS_NAME)["required"] == ["filled_nodes"]
    assert (
        schema_for_pass_spec(
            ExtractionPassSpec(
                pass_id=PASS_NAME,
                default_node_type="character",
                instruction="fill",
                progress_label="fill",
                kind="claimed_fill",
            )
        )["required"]
        == ["filled_nodes"]
    )


def test_build_claims_and_apply_ignores_invented_ids() -> None:
    claims = build_claims_from_mentions(
        {
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
    )
    assert [c.node_id for c in claims] == ["node:ephanna"]
    nodes = [
        {
            "node_id": "node:ephanna",
            "label": "Ephanna",
            "description": STUB_DESCRIPTION,
            "warnings": ["context_anchor_no_session_evidence"],
        }
    ]
    filled, diag = apply_fill_to_nodes(
        nodes,
        parsed={
            "filled_nodes": [
                {
                    "node_id": "node:ephanna",
                    "label": "Ephanna",
                    "node_type": "character",
                    "description": "Ephanna held the south gate line.",
                    "importance": "high",
                    "evidence_refs": [
                        {
                            "source_span_ref_id": "span:1",
                            "anchor_quotes": ["held the south gate"],
                        }
                    ],
                    "session_actions": ["held the south gate"],
                },
                {
                    "node_id": "node:invented",
                    "label": "Nope",
                    "node_type": "character",
                    "description": "should not apply",
                    "importance": "low",
                    "evidence_refs": [],
                    "session_actions": [],
                },
            ]
        },
        claimed_ids={"node:ephanna"},
    )
    assert diag["filled_applied"] == 1
    assert diag["skipped_invented"] == 1
    assert nodes[0]["description"] == STUB_DESCRIPTION  # input not mutated
    assert filled[0]["description"] == "Ephanna held the south gate line."
    assert filled[0]["enriched_by"] == PASS_NAME
    assert "pc_claimed_fill" in filled[0]["warnings"]
    assert "context_anchor_no_session_evidence" not in filled[0]["warnings"]
