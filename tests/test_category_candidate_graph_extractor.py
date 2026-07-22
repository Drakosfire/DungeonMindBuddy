from __future__ import annotations

from typing import Any

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    extract_category_candidate_graph,
)
from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE
from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
    WORLDBUILDING_PLUMBING_PROFILE,
)


class RecordingClient:
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
        if pass_name == "edge_pass":
            return {
                "parsed": {
                    "observation_edges": [
                        {
                            "edge_id": "e1",
                            "from_node_id": "n1",
                            "to_node_id": "n2",
                            "label": "in",
                            "relationship_type": "located_in",
                            "predicate_family": "spatial",
                            "evidence_refs": [
                                {
                                    "source_span_ref_id": "span-1",
                                    "anchor_quotes": ["Mirathorn"],
                                }
                            ],
                        }
                    ]
                },
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "r-edge",
            }
        if pass_name == "beat_pass":
            return {
                "parsed": {"observation_beats": []},
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "r-beat",
            }
        return {
            "parsed": {
                "observation_nodes": [
                    {
                        "node_id": "n1" if pass_name == "actor_pass" else "n2",
                        "label": "Mirathorn Guard" if pass_name == "actor_pass" else "Mirathorn",
                        "node_type": "character" if pass_name == "actor_pass" else "location",
                        "description": "fixture",
                        "importance": "medium",
                        "evidence_refs": [
                            {
                                "source_span_ref_id": "span-1",
                                "anchor_quotes": ["Mirathorn"],
                            }
                        ],
                    }
                ]
            },
            "cost_usd": 0.0,
            "usage": {},
            "elapsed_ms": 1,
            "response_id": f"r-{pass_name}",
        }


def _span_index(*, session_id: str | None) -> dict[str, Any]:
    return {
        "schema": "dmb_source_span_index_v0",
        "version": "0.1",
        "campaign_id": "eldyrwild",
        "session_id": session_id,
        "source_artifact_id": "artifact:test",
        "source_ref_id": "artifact:test:text",
        "spans": [
            {
                "span_id": "span-1",
                "source_span_ref_id": "span-1",
                "source_artifact_id": "artifact:test",
                "kind": "paragraph",
                "text": "Mirathorn is a river city.",
            }
        ],
    }


def test_extractor_uses_profile_selected_passes() -> None:
    client = RecordingClient()
    result = extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id="eldyrwild",
            session_id=None,
            session_number=None,
            source_span_index=_span_index(session_id=None),
            profile=WORLDBUILDING_PLUMBING_PROFILE,
        ),
        client=client,
    )
    assert "actor_pass" in client.passes
    assert "location_pass" in client.passes
    assert "object_pass" in client.passes
    assert "collective_pass" not in client.passes
    assert "beat_pass" not in client.passes
    assert "edge_pass" in client.passes
    assert result.candidate_graph["nodes"]
    for node in result.candidate_graph["nodes"]:
        assert node.get("evidence_refs")


def test_recap_profile_still_runs_full_pass_set() -> None:
    client = RecordingClient()
    extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            session_number=24,
            source_span_index=_span_index(session_id="session-24"),
            profile=RECAP_EXTRACTION_PROFILE,
        ),
        client=client,
    )
    assert client.passes[:5] == [
        "actor_pass",
        "location_pass",
        "collective_pass",
        "object_pass",
        "thread_pass",
    ]
    assert "beat_pass" in client.passes
    assert client.passes[-1] == "edge_pass"
