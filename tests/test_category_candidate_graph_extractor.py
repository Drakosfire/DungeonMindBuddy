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
            self.raw_disposition_payload = {
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
                        "node_type": "mystery",
                        "evidence_refs": [
                            {
                                "source_span_ref_id": "span-1",
                                "anchor_quotes": ["Mirathorn"],
                            }
                        ],
                        "suggested_next_step": None,
                    }
                ],
                "deferred_items": [
                    {
                        "item_id": "deferred:followup",
                        "label": "Follow the current",
                        "reason": "needs later pass",
                        "node_type": "thread",
                        "suggested_next_step": "revisit after session 25",
                        "evidence_refs": [
                            {
                                "source_span_ref_id": "span-1",
                                "anchor_quotes": ["Mirathorn"],
                            }
                        ],
                    }
                ],
            }

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
                "parsed": self.raw_disposition_payload,
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
    ignored = next(item for item in result.candidate_graph["ignored_items"] if item["item_id"] == "ignored:noise")
    deferred = next(item for item in result.candidate_graph["deferred_items"] if item["item_id"] == "deferred:followup")
    assert "node_type" not in ignored
    assert "node_type" not in deferred
    assert ignored["label"] == "Background chatter"
    assert ignored["reason"] == "not durable"
    assert ignored["evidence_refs"]
    assert deferred["label"] == "Follow the current"
    assert deferred["reason"] == "needs later pass"
    assert deferred["evidence_refs"]
    assert deferred["suggested_next_step"] == "revisit after session 25"
    candidate_node_ids = {node["node_id"] for node in result.candidate_graph["nodes"]}
    assert "ignored:noise" not in candidate_node_ids
    assert "deferred:followup" not in candidate_node_ids
    assert client.raw_disposition_payload["ignored_items"][0]["node_type"] == "mystery"
    assert client.raw_disposition_payload["deferred_items"][0]["node_type"] == "thread"


def test_canonical_injected_clients_keep_source_evidence_contract():
    """A source-bearing recap still works with the existing canonical protocol."""
    client = RecordingClient()
    result = extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id='longmont-c2', session_id='session-24', session_number=24,
            source_span_index=_span_index(session_id='session-24'),
            source_text='Mirathorn is a river city.', profile=RECAP_EXTRACTION_PROFILE,
        ), client=client,
    )
    assert 'actor_pass' in client.passes
    assert result.pass_outputs['actor_pass']['observation_nodes'][0]['evidence_refs'][0]['source_span_ref_id'] == 'span-1'


def test_extraction_retains_distinct_predicates_with_same_endpoints():
    class DistinctEdgesClient(RecordingClient):
        def run_pass(self, pass_name, **kwargs):
            result = super().run_pass(pass_name, **kwargs)
            if pass_name == 'edge_pass':
                base = result['parsed']['observation_edges'][0]
                result['parsed']['observation_edges'] = [
                    dict(base, edge_id=predicate, relationship_type=predicate,
                         predicate_family='threat_relation', label='response')
                    for predicate in predicates
                ]
            return result

    for predicates in (('attacks', 'threatens'), ('threatens', 'attacks')):
        result = extract_category_candidate_graph(
            CategoryGraphExtractionOptions(campaign_id='eldyrwild', session_id=None,
                session_number=None, source_span_index=_span_index(session_id=None),
                profile=WORLDBUILDING_PLUMBING_PROFILE), client=DistinctEdgesClient())
        edges = {e['relationship_type']: e for e in result.candidate_graph['edges']}
        assert set(edges) == {'attacks', 'threatens'}
        assert all(edge['evidence_refs'] for edge in edges.values())


def test_beat_call_receives_consolidated_identity_inventory_and_keeps_source_associations():
    import hashlib
    import json

    source = 'Miri fed the captive.\n\nSomeone else performed the song.'
    index = _span_index(session_id=None)
    index['content_sha256'] = hashlib.sha256(source.encode()).hexdigest()
    first, second = source.split('\n\n')
    index['spans'] = [dict(index['spans'][0], text=text, span_id=f'span-{n}',
        source_span_ref_id=f'span-{n}', line_start=line, line_end=line,
        char_start=start, char_end=start+len(text))
        for n, text, line, start in ((1, first, 1, 0), (2, second, 3, len(first)+2))]

    class BeatClient(RecordingClient):
        def run_pass(self, pass_name, **kwargs):
            response = super().run_pass(pass_name, **kwargs)
            if pass_name == 'actor_pass':
                response['parsed'] = {'observation_nodes': [
                    {'node_id': nid, 'label': 'Miri', 'node_type': 'character',
                     'description': 'Generated descriptive claim must not become source authority',
                     'evidence_refs': [{'source_span_ref_id': 'span-1', 'anchor_quotes': ['Miri']}]}
                    for nid in ('npc:miri', 'npc:duplicate')]}
            elif pass_name == 'beat_pass':
                prompt = kwargs['user_content']
                assert first in prompt and second in prompt
                assert 'Generated descriptive claim' not in prompt
                inventory = json.JSONDecoder().raw_decode(
                    prompt.split('## Node identity inventory\n\n```json\n', 1)[1])[0]
                assert {n['node_id'] for n in inventory} == {'npc:miri'}
                assert inventory[0]['label'] == 'Miri'
                assert inventory[0]['evidence_refs']
                response['parsed'] = {'observation_beats': [
                    {'beat_id': f'beat:{n}', 'order': n, 'title': 'Source event',
                     'summary': 'Untrusted model summary', 'involved_node_ids': participants,
                     'evidence_refs': [{'source_span_ref_id': f'span-{n}', 'anchor_quotes': [text]}]}
                    for n, text, participants in ((1, first, ['npc:miri']), (2, second, []))]}
            elif pass_name == 'edge_pass':
                response['parsed'] = {'observation_edges': []}
            else:
                response['parsed'] = {'observation_nodes': []}
            return response

    client = BeatClient()
    result = extract_category_candidate_graph(CategoryGraphExtractionOptions(
        campaign_id='synthetic-beat-context', session_id=None, session_number=None,
        source_text=source, source_span_index=index, profile=RECAP_EXTRACTION_PROFILE), client=client)
    assert client.passes == ['actor_pass', 'location_pass', 'collective_pass',
        'object_pass', 'thread_pass', 'beat_pass', 'edge_pass']
    beats = result.candidate_graph['beats']
    assert [b['involved_node_ids'] for b in beats] == [['npc:miri'], []]
    assert [b['summary'] for b in beats] == [first, second]
    assert {node['node_id'] for node in result.candidate_graph['nodes']} == {'npc:miri'}
