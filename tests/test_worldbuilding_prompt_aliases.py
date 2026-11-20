"""Worldbuilding source and review handles are model-local, never host identity."""

import json
import re
from dataclasses import replace

import pytest

from graph_memory.extraction.worldbuilding_prompt_aliases import WorldbuildingPromptAliases


def rows():
    return [{"source_span_ref_id": "host-artifact-document:span-1", "source_unit_id": "host-unit",
             "line_start": 2, "line_end": 2, "text": "The keeper opens the gate."}]


def test_source_and_graph_projections_preserve_content_but_not_host_identity():
    aliases = WorldbuildingPromptAliases(rows(), nonce="testnamespace")
    source = aliases.source_rows()
    assert source == [{"source_span_ref_id": "Stestnamespace_1", "line_start": 2,
                       "line_end": 2, "text": "The keeper opens the gate."}]
    ref = {"source_span_ref_id": "host-artifact-document:span-1", "anchor_quotes": ["keeper opens"],
           "source_artifact_id": "host-artifact-document", "source_ref_id": "host-document"}
    graph = {"nodes": [{"node_id": "host-node-1", "label": "Keeper", "node_type": "character",
                        "description": "A keeper.", "evidence_refs": [ref]},
                       {"node_id": "host-node-2", "label": "Gate", "node_type": "location"}],
             "edges": [{"edge_id": "host-edge", "from_node_id": "host-node-1", "to_node_id": "host-node-2",
                        "label": "opens", "relationship_type": "opens", "semantic_state": {"certainty": "possible"},
                        "evidence_refs": [ref]}]}
    safe = aliases.review_graph(graph)
    payload = json.dumps({"source": source, "graph": safe})
    assert all(value not in payload for value in ("host-artifact", "host-document", "host-unit", "host-node", "host-edge"))
    assert "The keeper opens the gate." in payload and "possible" in payload and "keeper opens" in payload
    assert aliases.resolve_review({"retained_edge_ids": ["Rtestnamespace_1"]}) == {"retained_edge_ids": ["host-edge"]}
    restored = aliases.resolve_output({"observation_edges": [{"from_node_id": "Ntestnamespace_1",
              "to_node_id": "Ntestnamespace_2", "evidence_refs": [{"source_span_ref_id": "Stestnamespace_1",
              "anchor_quotes": ["keeper opens"]}]}]}, endpoints=True)
    edge = restored["observation_edges"][0]
    assert edge["from_node_id"] == "host-node-1" and edge["to_node_id"] == "host-node-2"
    assert edge["evidence_refs"] == [{"source_span_ref_id": "host-artifact-document:span-1", "anchor_quotes": ["keeper opens"]}]


@pytest.mark.parametrize("handle", ["host-artifact-document:span-1", "Sother_1", "Stestnamespace_2", "", 1])
def test_unrecognized_source_handles_fail_closed(handle):
    aliases = WorldbuildingPromptAliases(rows(), nonce="testnamespace")
    with pytest.raises(ValueError, match="unknown source evidence"):
        aliases.resolve_output({"evidence_refs": [{"source_span_ref_id": handle}]})


def test_review_handles_are_request_local_and_duplicates_fail_closed():
    one = WorldbuildingPromptAliases(rows(), nonce="first")
    two = WorldbuildingPromptAliases(rows(), nonce="second")
    graph = {"nodes": [{"node_id": "n1"}, {"node_id": "n2"}],
             "edges": [{"edge_id": "e", "from_node_id": "n1", "to_node_id": "n2", "evidence_refs": []}]}
    one.review_graph(graph)
    two.review_graph(graph)
    for bad in (["Rfirst_1", "Rfirst_1"], ["e"], ["Rsecond_1"]):
        with pytest.raises(ValueError):
            one.resolve_review({"retained_edge_ids": bad})


def test_all_worldbuilding_passes_use_local_handles_and_preserve_evidence():
    from graph_memory.extraction.bounded_recap_execution import BoundedRecapPassClient, RecapExecutionLimits
    from graph_memory.extraction.category_candidate_graph_extractor import CategoryGraphExtractionOptions, run_category_pipeline
    from graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    from graph_memory.extraction.worldbuilding_gazetteer_profile import GAZETTEER_CONSTRAINED_REVIEW_PROFILE

    source = "Mayor Elara leads the Council."
    host_span = "host-artifact-document:span-1"

    class Client(BoundedRecapPassClient):
        def __init__(self):
            super().__init__(RecapExecutionLimits(provider="openrouter", model="test-model", max_calls=8))
            self.requests = []

        def run_pass(self, name, **kwargs):
            prompt = kwargs["user_content"]
            schema = schema_for_pass_spec(kwargs["pass_spec"])
            self.requests.append((name, prompt, json.dumps(schema)))
            self.calls.append({"pass_name": name, "observation": None})
            assert all(secret not in prompt + json.dumps(schema) for secret in
                       ("host-artifact-document", "host-unit", "actor:elara", "group:council", "edge:leads"))
            if name == "edge_review_pass":
                review = json.loads(prompt)
                assert review["source_packet"][0]["text"] == source
                assert review["allowed_edge_ids"] == [review["edge_proposals"][0]["edge_id"]]
                parsed = {"retained_edge_ids": review["allowed_edge_ids"]}
            else:
                match = re.search(r"### (S[a-f0-9]+_1) / lines", prompt)
                assert match and source in prompt
                ref = {"source_span_ref_id": match.group(1), "anchor_quotes": [source]}
                if name == "actor_pass":
                    parsed = {"observation_nodes": [{"node_id": "actor:elara", "label": "Mayor Elara",
                              "node_type": "character", "description": "Mayor Elara leads the Council.", "evidence_refs": [ref]}]}
                elif name == "collective_pass":
                    parsed = {"observation_nodes": [{"node_id": "group:council", "label": "Council",
                              "node_type": "faction", "description": "The Council.", "evidence_refs": [ref]}]}
                elif name == "edge_pass":
                    handles = re.findall(r'"node_id":\s*"(N[a-f0-9]+_\d+)"', prompt)
                    assert len(handles) == 2
                    parsed = {"observation_edges": [{"edge_id": "edge:leads", "from_node_id": handles[0],
                              "to_node_id": handles[1], "relationship_type": "leads", "label": "leads", "evidence_refs": [ref]}]}
                else:
                    parsed = {"observation_nodes": []}
            return {"parsed": parsed, "raw_text": json.dumps(parsed), "usage": None,
                    "cost_usd": None, "elapsed_ms": 1, "response_id": None}

    client = Client()
    options = CategoryGraphExtractionOptions(campaign_id="synthetic", session_id=None, session_number=None,
        source_text=source, source_artifact_id="host-artifact-document", model_id="test-model",
        source_span_index={"source_artifact_id": "host-artifact-document", "spans": [
            {"source_span_ref_id": host_span, "span_id": "host-unit", "text": source, "line_start": 1, "line_end": 1}]},
        profile=GAZETTEER_CONSTRAINED_REVIEW_PROFILE)
    result = run_category_pipeline(client, options)
    assert [name for name, _, _ in client.requests][-2:] == ["edge_pass", "edge_review_pass"]
    assert len(result.candidate_graph["edges"]) == 1
    ref = result.candidate_graph["edges"][0]["evidence_refs"][0]
    assert ref["source_span_ref_id"] == host_span and ref["anchor_quotes"] == [source]
    assert result.candidate_graph["edges"][0]["edge_id"] == "edge:leads"

@pytest.mark.parametrize("target", ["node", "edge"])
def test_unresolved_vocabulary_caution_fails_before_provider_dispatch(target):
    from graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions,
        FixtureCategoryGraphPassClient, run_category_pipeline,
    )
    from graph_memory.extraction.worldbuilding_gazetteer_profile import GAZETTEER_PROFILE
    from graph_memory.vocabulary.model import ContextVocabularyPacket, DoNotMergeDecision

    packet = ContextVocabularyPacket(
        packet_id="private-packet", scope="world", known_names=["Keeper"],
        entry_labels={"private-known-id": "Keeper"},
        do_not_merge_hints=[DoNotMergeDecision(
            decision_id="private-decision", left_vocab_id="private-known-id",
            right_vocab_id="private-unresolved-id", reason="Distinct people")],
    )
    class Client(FixtureCategoryGraphPassClient):
        def __init__(self):
            super().__init__({})
            self.calls = []

        def run_pass(self, name, **kwargs):
            self.calls.append(name)
            return super().run_pass(name, **kwargs)

    client = Client()
    source = rows()
    options = CategoryGraphExtractionOptions(
        campaign_id="synthetic", session_id=None, session_number=None,
        source_text=source[0]["text"], source_artifact_id="host-artifact-document",
        source_span_index={"source_artifact_id": "host-artifact-document", "spans": source},
        model_id="test-model", profile=GAZETTEER_PROFILE,
        enable_node_vocabulary_packet=target == "node", node_vocabulary_packet=packet if target == "node" else None,
        enable_edge_vocabulary_packet=target == "edge", edge_vocabulary_packet=packet if target == "edge" else None,
    )
    with pytest.raises(ValueError, match="lacks a resolved label"):
        run_category_pipeline(client, options)
    assert client.calls == []
