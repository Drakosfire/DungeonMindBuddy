"""Correction admission follows the saved recap producer's capabilities."""
import asyncio
import copy
import json

import httpx
import pytest

from apps.live_control_server.services import recap_semantic_candidate_correction as owner
from apps.live_control_server.services.extract_promote import _assert_and_project_candidate_evidence
from src.graph_memory.predicate_catalog import RECAP_SOURCE_ORDER, source_precedence_endpoints_admitted
from graph_memory.source_span import build_source_span_index_for_text, source_span_index_to_dict, source_span_index_from_dict
from tests.test_recap_semantic_candidate_correction import _fixture, _split_http_app, _candidate_path


def _source_order_fixture(monkeypatch, root, *, second_kind='event', profile='recap_category_v2@2.0'):
    source = 'Mira investigated the gate. Then Mira left the gate.\n'
    parent, raw, runs = _fixture(monkeypatch, root, source_text=source)
    payload = json.loads(raw)
    index = source_span_index_to_dict(build_source_span_index_for_text(
        source_artifact_id=parent.source_artifact_id, content_sha256=owner._sha(source.encode()), text=source))
    span = index['spans'][0]
    prototype = payload['nodes'][0]
    ref = copy.deepcopy(prototype['evidence_refs'][0])
    ref.update(source_span_ref_id=span['source_span_id'], source_ref_id=index['source_ref_id'],
               anchor_quotes=[source.strip()])
    first = {**copy.deepcopy(prototype), 'node_id': 'first', 'node_type': 'thread',
             'label': 'Investigation', 'description': 'Mira investigated the gate.', 'evidence_refs': [ref]}
    second = {**copy.deepcopy(prototype), 'node_id': 'second', 'node_type': second_kind,
              'label': 'Departure', 'description': 'Then Mira left the gate.', 'evidence_refs': [copy.deepcopy(ref)]}
    payload['nodes'] = [first, second]
    payload['edges'] = [{'edge_id': 'order', 'from_node_id': 'first', 'to_node_id': 'second',
                         'relationship_type': 'precedes', 'label': 'Investigation preceded departure.',
                         'evidence_refs': [copy.deepcopy(ref)], 'semantic_state': prototype['semantic_state'],
                         'proposed_action': 'create', 'confidence': 'medium'}]
    _assert_and_project_candidate_evidence(candidate_payload=payload, source_prose=source,
        source_artifact_id=parent.source_artifact_id, span_index=source_span_index_from_dict(index))
    raw = owner._canonical_bytes(payload)
    spans = owner._canonical_bytes(index)
    (root/'parent.json').write_bytes(raw)
    (root/'spans.json').write_bytes(spans)
    components = dict(parent.components)
    components['candidate_graph'] = components['candidate_graph'].model_copy(update={'sha256': owner._sha(raw)})
    components['source_span_index'] = components['source_span_index'].model_copy(update={'sha256': owner._sha(spans)})
    parent = parent.model_copy(update={'components': components, 'profile_id': profile})
    runs['parent'] = parent
    old_resolve = owner.resolve_promotable_ingest_run
    def resolve(*args, **kwargs):
        result = old_resolve(*args, **kwargs)
        result.extraction_profile = profile
        return result
    monkeypatch.setattr(owner, 'resolve_promotable_ingest_run', resolve)
    from apps.live_control_server.services import extract_promote
    monkeypatch.setattr(extract_promote, 'resolve_promotable_ingest_run', resolve)
    monkeypatch.setattr(extract_promote, '_load_frozen_span_index_for_resolved_run',
                        lambda resolved: source_span_index_from_dict(index))
    request = {'schema': 'dmb_recap_candidate_correction_request_v8', 'parent_run_id': 'parent',
               'expected_parent_revision': parent.revision, 'parent_candidate_sha256': owner._sha(raw),
               'source_revision_sha256': owner._sha(source.encode()), 'span_index_sha256': owner._sha(spans),
               'profile_id': profile, 'node_type_replacements': [
                   {'node_id': 'first', 'expected_node_type': 'thread', 'replacement_node_type': 'event'}]}
    return parent, raw, runs, request


def test_v8_source_order_type_only_child_is_held_and_exact(monkeypatch, tmp_path):
    parent, raw, runs, request = _source_order_fixture(monkeypatch, tmp_path)
    app = _split_http_app(monkeypatch)
    async def invoke():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            return await client.post('/api/live/extract-promote/runs/parent/recap-candidate-corrections', json=request)
    response = asyncio.run(invoke())
    assert response.status_code == 200, response.text
    child = runs[response.json()['runId']]
    assert response.json()['semanticState'] == 'held'
    assert owner.verify_child_replay(child, parent, tmp_path)
    actual = json.loads(_candidate_path(tmp_path, child).read_bytes())
    expected = json.loads(raw)
    expected['nodes'][0]['node_type'] = 'event'
    assert actual == expected
    assert (tmp_path/'parent.json').read_bytes() == raw
    assert runs['parent'] == parent


@pytest.mark.parametrize('profile,second', [('recap_category_v1@1.0','event'), ('recap_category_v2@2.0','thread'), ('recap_category_v2@2.0','item')])
def test_v8_unadopted_or_non_event_order_creates_no_child(monkeypatch, tmp_path, profile, second):
    parent, raw, runs, request = _source_order_fixture(monkeypatch, tmp_path, profile=profile, second_kind=second)
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV8
    with pytest.raises(Exception, match='final candidate tuple'):
        owner.correct_recap_candidate(RecapCandidateCorrectionRequestV8.model_validate(request))
    assert runs == {'parent': parent}
    assert (tmp_path/'parent.json').read_bytes() == raw
    assert not (tmp_path/'out/graph_memory/derived_candidates').exists()


def test_tuple_planner_uses_projected_types_and_keeps_incident_order_checked():
    parent = {'nodes': [{'node_id':'a','node_type':'thread'}, {'node_id':'b','node_type':'event'}, {'node_id':'c','node_type':'event'}],
              'edges': [{'edge_id':'edit','from_node_id':'a','to_node_id':'b','relationship_type':'precedes','label':'A before B'},
                        {'edge_id':'retained','from_node_id':'a','to_node_id':'c','relationship_type':'precedes','label':'A before C'}]}
    old = {k:parent['edges'][0][k] for k in owner.EDGE_TUPLE_FIELDS}
    ops = [{'edge_id':'edit','expected_tuple':old,'replacement_tuple':{**old,'label':'Investigation before departure'}}]
    plan = owner._plan_edge_tuple_replacements(parent, ops, projected_node_types={'a':'event'}, predicate_capabilities=(RECAP_SOURCE_ORDER,))
    assert plan['edit']['relationship_type'] == 'precedes'
    with pytest.raises(Exception):
        owner._plan_edge_tuple_replacements(parent, ops, projected_node_types={'a':'event'})
    parent['nodes'][2]['node_type'] = 'thread'
    with pytest.raises(Exception, match='unchanged incident edge'):
        owner._plan_edge_tuple_replacements(parent, ops, projected_node_types={'a':'event'}, predicate_capabilities=(RECAP_SOURCE_ORDER,))


def test_exact_profile_capability_and_shared_endpoint_rule():
    assert owner._correction_predicate_capabilities('recap_category_v1@1.0') == ()
    assert RECAP_SOURCE_ORDER in owner._correction_predicate_capabilities('recap_category_v2@2.0')
    for profile in ('unknown@1', 'worldbuilding_plumbing@1.0', 'recap_category_v2@missing'):
        with pytest.raises(Exception):
            owner._correction_predicate_capabilities(profile)
    assert source_precedence_endpoints_admitted('event', 'event')
    assert not source_precedence_endpoints_admitted('thread', 'event')
    assert not source_precedence_endpoints_admitted('event', 'character')


def test_v7_edited_tuple_uses_same_profile_capability(monkeypatch, tmp_path):
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV7
    parent, raw, runs, v8 = _source_order_fixture(monkeypatch, tmp_path)
    payload = json.loads(raw)
    payload['nodes'][0]['node_type'] = 'event'
    raw = owner._canonical_bytes(payload)
    (tmp_path/'parent.json').write_bytes(raw)
    components = dict(parent.components)
    components['candidate_graph'] = components['candidate_graph'].model_copy(update={'sha256': owner._sha(raw)})
    parent = parent.model_copy(update={'components': components})
    runs['parent'] = parent
    old = {k:payload['edges'][0][k] for k in owner.EDGE_TUPLE_FIELDS}
    body = {k:v8[k] for k in ('parent_run_id','source_revision_sha256','span_index_sha256','profile_id')}
    body.update(schema='dmb_recap_candidate_correction_request_v7', parent_candidate_sha256=owner._sha(raw),
                edge_tuple_replacements=[{'edge_id':'order','expected_tuple':old,
                                          'replacement_tuple':{**old,'label':'Investigation occurred before departure.'}}])
    result = owner.correct_recap_candidate(RecapCandidateCorrectionRequestV7.model_validate(body))
    child = runs[result.run_id]
    assert child.lineage['semantic_disposition']['state'] == 'held'
    assert owner.verify_child_replay(child, parent, tmp_path)
    assert (tmp_path/'parent.json').read_bytes() == raw
