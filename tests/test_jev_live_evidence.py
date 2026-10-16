import asyncio
from copy import deepcopy
import json

import pytest

from evals.graph_memory_layer.jev_evidence_loop import run_loop
from evals.graph_memory_layer.jev_live_evidence import LiveSourceReader, writer_request, write_once
from tests.test_jev_evidence_loop import fixture, decisions


def live_fixture():
    original = fixture()
    catalog = deepcopy(original)
    for u in catalog['units'].values():
        if u['id'] != 'u3':
            for key in ('text', 'provenance', 'content_sha256'):
                u.pop(key)
            u['unretrieved'] = True
    return original, catalog


def test_live_only_selected_actions_read_before_decision(tmp_path):
    original, catalog = live_fixture()
    reads, calls = [], []
    async def retrieve(action):
        reads.append(action['id'])
        return [original['units'][uid] for uid in action['unit_ids']]
    async def evaluate(request):
        calls.append(request)
        assert 'unretrieved' not in json.dumps(request)
        return decisions(request)
    result = asyncio.run(run_loop(catalog, evaluate, output=tmp_path/'run', retrieve=retrieve))
    assert reads == ['a1', 'a2']
    assert result['mode'] == 'live_revision_bound_source_acquisition'
    assert result['status'] == 'provisionally_supported'
    assert {u['id'] for u in calls[0]['state']['evidence']} == {'u1'}
    assert all(e['retrieval_seconds'] >= 0 for e in result['retrieval_events'])


@pytest.mark.parametrize('bad', ['scope', 'body', 'identity', 'unavailable'])
def test_bad_live_read_prevents_decision_and_writer(tmp_path, bad):
    original, catalog = live_fixture()
    calls = []
    async def retrieve(action):
        u = deepcopy(original['units']['u1'])
        if bad == 'scope':
            u['scope']['world_id'] = 'other'
        elif bad == 'body':
            u['text'] = 'tampered'
        elif bad == 'identity':
            u['id'] = 'unknown'
        else:
            raise TimeoutError()
        return [u]
    async def evaluate(request):
        calls.append(request)
    result = asyncio.run(run_loop(catalog, evaluate, output=tmp_path/'run', retrieve=retrieve))
    assert not calls
    assert result['status'] == 'retrieval_unavailable_or_invalid'
    with pytest.raises(ValueError):
        writer_request(result, 'question')


def test_writer_one_tool_free_call_and_no_uncertain_replay(tmp_path):
    result = {'status': 'provisionally_supported', 'unresolved_requirements': [],
              'selected_evidence': [fixture()['units']['u1']]}
    calls = []
    async def invoke(request):
        calls.append(request)
        assert 'tools' not in request
        assert 'previous_response_id' not in request
        assert json.loads(request['input'])['evidence'][0]['text'] == 'Aster leads the assembly.'
        raise TimeoutError()
    answer = asyncio.run(write_once(result, 'question', invoke, tmp_path))
    assert answer['status'] == 'uncertain_do_not_replay'
    with pytest.raises(FileExistsError):
        asyncio.run(write_once(result, 'question', invoke, tmp_path))
    assert len(calls) == 1


def test_packet_deduplicates_exact_opened_text_preserving_qualifications():
    unit = fixture()['units']['u1']
    unit.update(observation_text='Aster does not know about the plot.',
        opened_passages=[{'start_line': 1, 'end_line': 1, 'text': 'Aster leads the assembly.'}],
        epistemic_kind='source_derived_candidate')
    second = {**unit, 'id': 'u2'}
    request = writer_request({'status':'provisionally_supported', 'unresolved_requirements': [],
                             'selected_evidence': [unit, second]}, 'question')
    packet = json.loads(request['input'])
    assert len(packet['passages']) == 1
    assert len(packet['evidence']) == 2
    assert all(e['observation'] == 'Aster does not know about the plot.' for e in packet['evidence'])


def test_incomplete_source_catalog_rejected():
    with pytest.raises(ValueError, match='Incomplete'):
        LiveSourceReader(None, None, {}, '', {'status':'partial', 'next_page_token':None})
