from __future__ import annotations

import pytest

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
        if pass_name not in {"actor_pass", "location_pass"}:
            return {
                "parsed": {"observation_nodes": []},
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": f"r-{pass_name}",
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


def test_beat_call_receives_source_local_inventory_and_keeps_source_associations():
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
                assert {n['node_id'] for n in inventory} == {'npc:miri', 'npc:duplicate'}
                assert inventory[0]['label'] == 'Miri'
                assert inventory[0]['evidence_ids'] == ['E1']
                assert '### E1 / lines 1-1' in prompt
                response['parsed'] = {'observation_beats': [
                    {'beat_id': f'beat:{n}', 'order': n, 'title': 'Source event',
                     'summary': 'Untrusted model summary', 'involved_node_ids': participants,
                     'evidence_refs': [{'source_span_ref_id': f'E{n}', 'anchor_quotes': [text]}]}
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
    assert {node['node_id'] for node in result.candidate_graph['nodes']} == {'npc:miri', 'npc:duplicate'}


class SourceLocalIdentityClient(RecordingClient):
    """Replay collision shapes without asking a provider to resolve identity."""

    source = (
        "Stone Bridge is a town with a bridge also called Stone Bridge. "
        "The Wizard's Tower Brewing Co company operates a brewery of the same name."
    )

    def __init__(self, *, duplicate_id=False):
        super().__init__()
        self.duplicate_id = duplicate_id
        self.ref = {"source_span_ref_id": "span-1", "anchor_quotes": [self.source]}
        self.inventory_ids = {"town", "bridge", "brewery", "company", "bridge-item"}

    def run_pass(self, pass_name, **kwargs):
        response = super().run_pass(pass_name, **kwargs)
        if pass_name == "location_pass":
            response["parsed"] = {"observation_nodes": [
                {"node_id": nid, "label": label, "node_type": "location",
                 "description": description, "evidence_refs": [self.ref]}
                for nid, label, description in (
                    ("town", "Stone Bridge", "The town."),
                    ("town" if self.duplicate_id else "bridge", "Stone Bridge", "The bridge."),
                    ("brewery", "The Wizard's Tower Brewing Co", "The premises."),
                )
            ]}
        elif pass_name in {"collective_pass", "object_pass"}:
            is_company = pass_name == "collective_pass"
            response["parsed"] = {"observation_nodes": [{
                "node_id": "company" if is_company else "bridge-item",
                "label": "The Wizard's Tower Brewing Co" if is_company else "Stone Bridge",
                "node_type": "organization" if is_company else "item",
                "description": "The company." if is_company else "The bridge object.",
                "evidence_refs": [self.ref],
            }]}
        elif pass_name in {"beat_pass", "edge_pass"}:
            if not self.duplicate_id:
                for nid in self.inventory_ids:
                    assert f'"node_id": "{nid}"' in kwargs["user_content"], (pass_name, nid)
            if pass_name == "beat_pass":
                response["parsed"] = {"observation_beats": []}
            else:
                response["parsed"] = {"observation_edges": [
                    {"edge_id": eid, "from_node_id": start, "to_node_id": end,
                     "label": label, "relationship_type": predicate,
                     "evidence_refs": [self.ref]}
                    for eid, start, end, predicate, label in (
                        ("bridge-town", "bridge", "town", "located_in", "Bridge in town"),
                        ("company-premises", "company", "brewery", "associated_with", "Company premises"),
                        ("bridge-object", "bridge-item", "bridge", "same_as", "Explicit producer proposal"),
                        ("unknown", "unknown:bridge", "town", "located_in", "Unknown endpoint"),
                    )
                ]}
        else:
            response["parsed"] = {"observation_nodes": []}
        return response


def _extract_source_local_identity(client):
    index = _span_index(session_id="session-1")
    index["spans"][0]["text"] = client.source
    return extract_category_candidate_graph(CategoryGraphExtractionOptions(
        campaign_id="synthetic-source-local", session_id="session-1", session_number=1,
        source_span_index=index, source_text=client.source,
        profile=RECAP_EXTRACTION_PROFILE,
    ), client=client)


def test_source_local_distinctions_reach_later_passes_and_keep_exact_edge_endpoints():
    client = SourceLocalIdentityClient()
    result = _extract_source_local_identity(client)
    nodes = result.candidate_graph["nodes"]
    assert {node["node_id"] for node in nodes} == client.inventory_ids
    assert next(node for node in nodes if node["node_id"] == "town")["description"] == "The town."
    assert next(node for node in nodes if node["node_id"] == "bridge")["description"] == "The bridge."
    edges = {edge["edge_id"]: edge for edge in result.candidate_graph["edges"]}
    assert set(edges) == {"bridge-town", "company-premises", "bridge-object"}
    assert {(eid, edge["from_node_id"], edge["to_node_id"]) for eid, edge in edges.items()} == {
        ("bridge-town", "bridge", "town"),
        ("company-premises", "company", "brewery"),
        ("bridge-object", "bridge-item", "bridge"),
    }
    # Only the explicit producer proposal survives; the host invents no same_as.
    assert [edge["edge_id"] for edge in edges.values() if edge["relationship_type"] == "same_as"] == ["bridge-object"]
    from src.graph_memory.candidate_graph_to_contribution import load_typed_candidate_graph

    load_typed_candidate_graph(result.candidate_graph)
    diag = result.consolidation_diagnostics
    assert diag["merged_nodes"] == diag["cross_class_merged_nodes"] == []
    assert diag["dropped_edges_missing_endpoints"] == [
        {"edge_id": "unknown", "from_node_id": "unknown:bridge", "to_node_id": "town"}
    ]


def test_duplicate_source_local_ids_are_exposed_to_existing_preview_validation():
    from src.graph_memory.candidate_graph_preview import (
        candidate_graph_preview_from_dict, validate_candidate_graph_preview,
    )

    result = _extract_source_local_identity(SourceLocalIdentityClient(duplicate_id=True))
    # Do not mask malformed provider identity reuse with label-based deduplication.
    assert sum(node["node_id"] == "town" for node in result.candidate_graph["nodes"]) == 2
    report = validate_candidate_graph_preview(candidate_graph_preview_from_dict(result.candidate_graph))
    assert any(issue.code == "duplicate_node_id" and issue.severity == "error" for issue in report.issues)
    import pytest
    from src.graph_memory.candidate_graph_to_contribution import (
        CandidateGraphMappingError, load_typed_candidate_graph,
    )

    with pytest.raises(CandidateGraphMappingError, match="duplicate_node_id"):
        load_typed_candidate_graph(result.candidate_graph)



def test_same_label_endpoints_do_not_collapse_separate_relationships():
    class ParallelEndpointsClient(SourceLocalIdentityClient):
        source = SourceLocalIdentityClient.source + " A sign stands near both the town and the bridge."

        def run_pass(self, pass_name, **kwargs):
            response = super().run_pass(pass_name, **kwargs)
            if pass_name == "object_pass":
                response["parsed"]["observation_nodes"].append({
                    "node_id": "sign", "label": "Sign", "node_type": "item",
                    "description": "A sign near both places.", "evidence_refs": [self.ref],
                })
            elif pass_name == "edge_pass":
                response["parsed"]["observation_edges"].extend([
                    {"edge_id": f"sign-{target}", "from_node_id": "sign", "to_node_id": target,
                     "relationship_type": "near", "label": "Near Stone Bridge",
                     "evidence_refs": [self.ref]}
                    for target in ("town", "bridge")
                ])
            return response

    result = _extract_source_local_identity(ParallelEndpointsClient())
    assert {edge["edge_id"]: (edge["from_node_id"], edge["to_node_id"])
            for edge in result.candidate_graph["edges"] if edge["edge_id"].startswith("sign-")} == {
        "sign-town": ("sign", "town"), "sign-bridge": ("sign", "bridge"),
    }
    assert result.consolidation_diagnostics["merged_edges"] == []



def test_duplicate_source_local_edge_ids_are_not_hidden_by_payload_deduplication():
    import pytest
    from src.graph_memory.candidate_graph_to_contribution import (
        CandidateGraphMappingError, load_typed_candidate_graph,
    )

    class DuplicateEdgeClient(SourceLocalIdentityClient):
        def run_pass(self, pass_name, **kwargs):
            response = super().run_pass(pass_name, **kwargs)
            if pass_name == "edge_pass":
                edges = response["parsed"]["observation_edges"]
                edges.append(dict(edges[0]))
            return response

    result = _extract_source_local_identity(DuplicateEdgeClient())
    assert sum(edge["edge_id"] == "bridge-town" for edge in result.candidate_graph["edges"]) == 2
    with pytest.raises(CandidateGraphMappingError, match="duplicate_edge_id"):
        load_typed_candidate_graph(result.candidate_graph)


@pytest.mark.parametrize('collection,id_key', [('nodes', 'node_id'), ('ignored_items', 'item_id'), ('deferred_items', 'item_id')])
def test_sanitizer_retains_rejected_node_nominations_and_warns_surviving_record(collection, id_key):
    from copy import deepcopy
    from src.graph_memory.extraction.category_candidate_graph_extractor import sanitize_parts
    valid = {'source_span_ref_id': 'paragraph:51-52', 'anchor_quotes': ['the rope was gone']}
    invalid = {'source_span_ref_id': 'paragraph:52-52', 'anchor_quotes': ['the rope was gone']}
    record = {id_key: 'rescue', 'description': 'An unchanged observed rescue.', 'evidence_refs': [valid, invalid]}
    original = deepcopy(record)
    output, diagnostics = sanitize_parts({collection: [record]}, {'paragraph:51-52'})
    saved = output[collection][0]
    assert saved['evidence_refs'] == [valid]
    assert saved['description'] == record['description']
    assert saved['warnings'] == ['evidence_ref_rejected:2']
    assert diagnostics['rejected_node_evidence_refs'] == [{
        'collection': collection, 'record_id': 'rescue', 'reference_ordinal': 2,
        'reason': 'unadvertised_or_invalid_span_ref', 'nominated_ref': invalid,
    }]
    assert record == original


def test_sanitizer_keeps_all_invalid_node_rejection_after_dropping_node():
    from src.graph_memory.extraction.category_candidate_graph_extractor import sanitize_parts
    invalid = {'source_span_ref_id': 'paragraph:45', 'anchor_quotes': ['accepted the ride']}
    output, diagnostics = sanitize_parts({'nodes': [{'node_id': 'ride', 'evidence_refs': [invalid]}]}, {'paragraph:45-45'})
    assert output['nodes'] == []
    assert diagnostics['dropped_no_valid_evidence'] == {'nodes': ['ride']}
    assert diagnostics['rejected_node_evidence_refs'][0]['nominated_ref'] == invalid
    output, diagnostics = sanitize_parts({'nodes': [{'node_id': 'ride', 'evidence_refs': [{'source_span_ref_id': 'paragraph:45-45', 'anchor_quotes': ['accepted the ride']}]}]}, {'paragraph:45-45'})
    assert 'warnings' not in output['nodes'][0]
    assert diagnostics['rejected_node_evidence_refs'] == []


def test_order_edges_cannot_inherit_occurrence_evidence_but_other_edges_still_can():
    import copy
    from src.graph_memory.predicate_catalog import RECAP_SOURCE_ORDER
    from src.graph_memory.extraction.category_candidate_graph_extractor import repair_edge_evidence_refs
    ref = {"source_span_ref_id": "span-order", "anchor_quotes": ["The arrival was before departure."]}
    for invalid in ([], [{"source_span_ref_id": "not-advertised", "anchor_quotes": ["invented"]}]):
        parts = {"nodes": [{"node_id": "a", "evidence_refs": [ref]},
                           {"node_id": "b", "evidence_refs": [ref]}],
                 "edges": [{"from_node_id": "a", "to_node_id": "b", "relationship_type": kind,
                            "evidence_refs": copy.deepcopy(invalid)}
                           for kind in ("precedes", "participates_in")]}
        repair_edge_evidence_refs(parts, {"span-order"}, predicate_capabilities=(RECAP_SOURCE_ORDER,))
        assert parts["edges"][0]["evidence_refs"] == []
        assert parts["edges"][1]["evidence_refs"] == [ref]
    parts["edges"][0]["evidence_refs"] = [ref]
    repair_edge_evidence_refs(parts, {"span-order"}, predicate_capabilities=(RECAP_SOURCE_ORDER,))
    assert parts["edges"][0]["evidence_refs"] == [ref]



def test_ordinary_producer_projects_two_direct_order_claims_without_inventing_a_total_order():
    import jsonschema
    from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    source = "An arrival happened. A discussion happened. Both preceded a departure; their relative order is unstated."
    ref = {"source_span_ref_id": "span-1", "anchor_quotes": [source]}
    class OrderClient:
        def run_pass(self, pass_name, *, model_id, instructions, user_content, pass_spec=None):
            if pass_name == "thread_pass":
                parsed = {"observation_nodes": [
                    {"node_id": name, "label": name, "node_type": "event", "description": f"The {name} occurred.",
                     "importance": "high", "evidence_refs": [ref]}
                    for name in ("arrival", "discussion", "departure")], "ignored_items": [], "deferred_items": []}
            elif pass_name == "edge_pass":
                assert "`precedes`" in user_content
                parsed = {"observation_edges": [
                    {"edge_id": name, "from_node_id": name, "to_node_id": "departure", "label": "earlier",
                     "relationship_type": "precedes", "predicate_family": "temporal_sequence", "evidence_refs": [ref]}
                    for name in ("arrival", "discussion")]}
                jsonschema.validate(parsed, schema_for_pass_spec(pass_spec))
            elif pass_name == "beat_pass":
                parsed = {"observation_beats": []}
            else:
                parsed = {"observation_nodes": [], "ignored_items": [], "deferred_items": []}
            return {"parsed": parsed, "cost_usd": 0, "usage": {}, "elapsed_ms": 1, "response_id": pass_name}
    index = _span_index(session_id="session-1")
    index["spans"][0]["text"] = source
    result = extract_category_candidate_graph(CategoryGraphExtractionOptions(
        campaign_id="synthetic", session_id="session-1", session_number=1,
        source_span_index=index, source_text=source, profile=RECAP_EXTRACTION_PROFILE,
    ), client=OrderClient())
    edges = result.candidate_graph["edges"]
    assert {(edge["from_node_id"], edge["to_node_id"], edge["relationship_type"]) for edge in edges} == {
        ("arrival", "departure", "precedes"), ("discussion", "departure", "precedes"),
    }
    assert all(not any("predicate_validation:" in warning for warning in edge.get("warnings", [])) for edge in edges)
