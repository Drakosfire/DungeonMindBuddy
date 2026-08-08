"""Production party claimed-fill helpers and pipeline hook (no live LLM)."""

from __future__ import annotations

from typing import Any

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    extract_category_candidate_graph,
)
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
from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE


def test_recap_profile_enables_party_claimed_fill() -> None:
    assert RECAP_EXTRACTION_PROFILE.enable_party_claimed_fill is True


def test_claimed_fill_schema_is_nodes_only() -> None:
    schema = party_claimed_fill_json_schema()
    assert set(schema["required"]) == {"filled_nodes"}
    assert "participation_edges" not in schema["properties"]
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


class _FillRecordingClient:
    def __init__(self) -> None:
        self.passes: list[str] = []

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
        pass_spec=None,
    ) -> dict[str, Any]:
        self.passes.append(pass_name)
        if pass_name == PASS_NAME:
            assert "Owned / authored claims" in user_content
            assert "node:caelynn" in user_content
            return {
                "parsed": {
                    "filled_nodes": [
                        {
                            "node_id": "node:caelynn",
                            "label": "Caelynn",
                            "node_type": "character",
                            "description": "Caelynn struck the wall defenders with lightning.",
                            "importance": "high",
                            "evidence_refs": [
                                {
                                    "source_span_ref_id": "span-1",
                                    "anchor_quotes": ["Caelynn"],
                                }
                            ],
                            "session_actions": ["struck with lightning"],
                        }
                    ]
                },
                "cost_usd": 0.001,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "fill",
            }
        if pass_name == "edge_pass":
            return {
                "parsed": {"observation_edges": []},
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "edge",
            }
        if pass_name == "beat_pass":
            return {
                "parsed": {"observation_beats": []},
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "beat",
            }
        return {
            "parsed": {"observation_nodes": []},
            "cost_usd": 0.0,
            "usage": {},
            "elapsed_ms": 1,
            "response_id": pass_name,
        }


def test_pipeline_runs_claimed_fill_when_party_mentioned() -> None:
    client = _FillRecordingClient()
    result = extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            session_number=24,
            source_span_index={
                "schema": "dmb_source_span_index_v0",
                "version": "0.1",
                "campaign_id": "longmont-c2",
                "session_id": "session-24",
                "source_artifact_id": "artifact:test",
                "source_ref_id": "artifact:test:text",
                "spans": [
                    {
                        "span_id": "span-1",
                        "source_span_ref_id": "span-1",
                        "source_artifact_id": "artifact:test",
                        "kind": "paragraph",
                        "text": "Caelynn held the wall as the meat horde pressed Mireward Gate.",
                    }
                ],
            },
            profile=RECAP_EXTRACTION_PROFILE,
            enable_party_claimed_fill=True,
        ),
        client=client,
    )
    assert PASS_NAME in client.passes
    assert result.diagnostics["party_claimed_fill"]["filled_applied"] >= 1
    # Filled node may land in candidate or standing partition; search both.
    graphs = [result.candidate_graph]
    if result.registry_context_graph:
        graphs.append(result.registry_context_graph)
    descriptions = {
        n.get("node_id"): n.get("description")
        for g in graphs
        for n in (g.get("nodes") or [])
        if isinstance(n, dict)
    }
    assert descriptions.get("node:caelynn") == (
        "Caelynn struck the wall defenders with lightning."
    )


def test_pipeline_skips_claimed_fill_when_disabled() -> None:
    client = _FillRecordingClient()
    extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            session_number=24,
            source_span_index={
                "schema": "dmb_source_span_index_v0",
                "version": "0.1",
                "campaign_id": "longmont-c2",
                "session_id": "session-24",
                "source_artifact_id": "artifact:test",
                "source_ref_id": "artifact:test:text",
                "spans": [
                    {
                        "span_id": "span-1",
                        "source_span_ref_id": "span-1",
                        "kind": "paragraph",
                        "text": "Caelynn held the wall.",
                    }
                ],
            },
            profile=RECAP_EXTRACTION_PROFILE,
            enable_party_claimed_fill=False,
        ),
        client=client,
    )
    assert PASS_NAME not in client.passes
