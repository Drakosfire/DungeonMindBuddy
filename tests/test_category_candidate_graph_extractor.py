from __future__ import annotations

from typing import Any

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    extract_category_candidate_graph,
)
from src.graph_memory.extraction.known_entity_registry import KnownEntity
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


def test_custom_disposition_pass_id_prompts_and_retains_items() -> None:
    from src.graph_memory.extraction.extraction_profile import (
        ExtractionPassSpec,
        ExtractionProfile,
    )
    from src.graph_memory.extraction.recap_extraction_profile import (
        DEFAULT_SEMANTIC_STATE,
        EVIDENCE_RULE,
    )

    disposition_pass = ExtractionPassSpec(
        pass_id="mystery_disposition_pass",
        default_node_type="mystery",
        instruction="Extract mysteries and emit dispositions.",
        progress_label="Extracting mysteries with dispositions",
        include_dispositions=True,
    )
    edge_pass = ExtractionPassSpec(
        pass_id="edge_pass",
        default_node_type=None,
        instruction="Extract durable relationship edges.",
        progress_label="Extracting relationship edges",
        kind="edge",
    )
    profile = ExtractionProfile(
        profile_id="custom_disposition_v0",
        profile_version="0.1",
        admitted_source_domains=frozenset({"recap"}),
        admitted_document_classes=frozenset({"recap"}),
        node_passes=(disposition_pass,),
        beat_pass=None,
        encounter_job_pass=None,
        edge_pass=edge_pass,
        evidence_rule=EVIDENCE_RULE,
        default_semantic_state=DEFAULT_SEMANTIC_STATE,
        allow_null_session=False,
    )

    class DispositionClient:
        def __init__(self) -> None:
            self.user_contents: dict[str, str] = {}

        def run_pass(
            self,
            pass_name: str,
            *,
            model_id: str,
            instructions: str,
            user_content: str,
            pass_spec=None,
        ) -> dict[str, Any]:
            self.user_contents[pass_name] = user_content
            if pass_name == "edge_pass":
                return {
                    "parsed": {"observation_edges": []},
                    "cost_usd": 0.0,
                    "usage": {},
                    "elapsed_ms": 1,
                    "response_id": "edge",
                }
            return {
                "parsed": {
                    "observation_nodes": [
                        {
                            "node_id": "node:mystery",
                            "label": "River mystery",
                            "node_type": "mystery",
                            "description": "Something odd in the river.",
                            "importance": "medium",
                            "evidence_refs": [
                                {
                                    "source_span_ref_id": "span-1",
                                    "anchor_quotes": ["Mirathorn"],
                                }
                            ],
                        }
                    ],
                    "ignored_items": [
                        {
                            "item_id": "ignored:noise",
                            "label": "Background chatter",
                            "reason": "not durable",
                            "evidence_refs": [
                                {
                                    "source_span_ref_id": "span-1",
                                    "anchor_quotes": ["Mirathorn"],
                                }
                            ],
                        }
                    ],
                    "deferred_items": [
                        {
                            "item_id": "deferred:followup",
                            "label": "Follow the current",
                            "reason": "needs later pass",
                            "suggested_next_step": "revisit after session 25",
                            "evidence_refs": [
                                {
                                    "source_span_ref_id": "span-1",
                                    "anchor_quotes": ["Mirathorn"],
                                }
                            ],
                        }
                    ],
                },
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": pass_name,
            }

    client = DispositionClient()
    result = extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            session_number=24,
            source_span_index=_span_index(session_id="session-24"),
            source_artifact_id="artifact:recap:longmont-c2:session-24:testdigest",
            source_ref_id="artifact:recap:longmont-c2:session-24:testdigest:text",
            profile=profile,
        ),
        client=client,
    )
    prompt = client.user_contents["mystery_disposition_pass"]
    assert "ignored_items" in prompt
    assert "deferred_items" in prompt
    ignored_ids = {item["item_id"] for item in result.candidate_graph.get("ignored_items") or []}
    deferred_ids = {item["item_id"] for item in result.candidate_graph.get("deferred_items") or []}
    assert "ignored:noise" in ignored_ids
    assert "deferred:followup" in deferred_ids


class LedgerRecordingClient(RecordingClient):
    def __init__(self) -> None:
        super().__init__()
        self.user_contents: dict[str, str] = {}

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
        pass_spec=None,
    ) -> dict[str, Any]:
        self.user_contents[pass_name] = user_content
        return super().run_pass(
            pass_name,
            model_id=model_id,
            instructions=instructions,
            user_content=user_content,
            pass_spec=pass_spec,
        )


def _world_extra_entity() -> KnownEntity:
    return KnownEntity(
        slug="loc_mirathorn",
        kind="location",
        display_name="Mirathorn",
        canonical_entity_id="node:mirathorn",
        aliases=(),
        hub_rel_path="",
        hub_resolved=False,
        corpus_ref={
            "type": "location",
            "ref_id": "node:mirathorn",
            "resolution": "world_head",
        },
        match_terms=(("Mirathorn", "canonical"),),
    )


def test_extra_known_entities_feed_ledger_suppression_and_mentions() -> None:
    client = LedgerRecordingClient()
    result = extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            session_number=24,
            source_span_index=_span_index(session_id="session-24"),
            profile=RECAP_EXTRACTION_PROFILE,
            extra_known_entities=(_world_extra_entity(),),
        ),
        client=client,
    )
    # The world entity appears in the deterministic known-entity ledger shown
    # to every node pass.
    ledger = client.user_contents["actor_pass"]
    assert "Mirathorn" in ledger
    assert "node:mirathorn" in ledger
    # Deterministic mention matching covers the extra entity.
    mention_ids = {
        m["canonical_entity_id"]
        for m in result.known_entity_mentions["mentions"]
    }
    assert "node:mirathorn" in mention_ids
    # The LLM's duplicate "Mirathorn" location node is suppressed; the
    # non-colliding guard node survives.
    labels = {n.get("label") for n in result.candidate_graph["nodes"]}
    assert "Mirathorn" not in labels
    assert "Mirathorn Guard" in labels
