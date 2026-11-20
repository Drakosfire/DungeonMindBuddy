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


@pytest.mark.parametrize('provider_status, text, expected', [
    ('completed', 'Useful answer.', 'completed'), ('completed', '', 'empty_completion'),
    ('incomplete', 'Truncated', 'incomplete'), ('failed', '', 'failed'),
    ('cancelled', '', 'cancelled'), ('queued', '', 'unknown_provider_status'),
    (None, 'Something', 'unknown_provider_status')])
def test_writer_terminal_status_preserves_raw_response(tmp_path, provider_status, text, expected):
    response = {'answer':text, 'data': {'status':provider_status, 'usage': {'input_tokens':12}}}
    calls = []
    async def invoke(request):
        calls.append(request)
        return response
    result = {'status':'provisionally_supported', 'unresolved_requirements':[],
              'selected_evidence':[fixture()['units']['u1']]}
    recorded = asyncio.run(write_once(result, 'question', invoke, tmp_path))
    assert recorded['status'] == expected
    assert recorded['response'] == response
    assert len(calls) == 1
    assert json.loads((tmp_path/'writer-citation-map.json').read_text())['u1']['scope']['world_id'] == 'synthetic'
    prompt = json.loads(calls[0]['input'])['evidence'][0]
    assert 'scope' not in prompt and 'provenance' not in prompt


def batch_reader(monkeypatch, count=2, *, bad=False):
    """Exercise the reader at its actual observation-selection/source-read seam."""
    from types import SimpleNamespace as N
    from pathlib import Path
    import hashlib
    from apps.live_control_server.integrations.dungeonmind import selected_observation_reads, world_graph_reads
    markdown = '# Town\nAster leads the assembly.\n'
    sha = hashlib.sha256(markdown.encode()).hexdigest()
    discovery = {'status': 'complete', 'next_page_token': None, 'eligible_count': count,
                 'source_artifact_id': 'artifact:test', 'source_revision_id': 'source:r1',
                 'entries': [{'subject_object_id': f'node:{i:02}', 'assertion_id': f'assertion:{i:02}',
                              'subject_label': f'Person {i}', 'excerpt': 'leads'} for i in range(count)]}
    spec = {'world_id': 'synthetic', 'graph_revision': 'rev:test', 'source_sha256': sha,
            'build_revision': 1, 'seed_patterns': ['Person'], 'question': 'Who leads?', 'requirements': []}
    reader = LiveSourceReader(None, Path('.'), spec, markdown, discovery)
    from contextlib import contextmanager
    from apps.live_control_server.integrations.dungeonmind import reviewed_source_wave
    bound = object()
    reader.wave_events = []
    @contextmanager
    def wave(services, request):
        assert services is None
        assert request.source_artifact_id == 'artifact:test'
        reader.wave_events.append('open')
        try:
            yield bound
        finally:
            reader.wave_events.append('closed')
    monkeypatch.setattr(reviewed_source_wave, 'reviewed_source_wave', wave)
    selections, reads = [], []
    def select(services, request):
        assert services is bound and reader.wave_events[-1] == 'open'
        ids = request.observation_ids
        selections.append(list(ids))
        # Deliberately shared evidence ref across distinct anchors/subjects.
        return N(result=N(snapshot=N(revision_id='rev:test'), source_anchors=[
                     N(anchor_id='anchor:' + key, supporting_assertion_ids=[key]) for key in ids]),
                 observation_gap_codes=(), observation_missing_ids=(),
                 reviewed_source_observations=[N(assertion_id=key, source_artifact_id='artifact:test',
                     source_revision_id='source:r1', evidence_ref_ids=['shared-ref'], text=key,
                     epistemic_kind='source_derived_candidate', temporal_scope='unspecified') for key in ids],
                 source_pins=[N(anchor_id='anchor:' + key, evidence_ref_id='shared-ref') for key in ids])
    def open_sources(services, requests, *, repo_root):
        assert services is bound and reader.wave_events[-1] == 'open'
        reads.append([r.anchor_id for r in requests])
        return tuple(N(graph_revision='rev:test', source_artifact_id='artifact:test',
                       source_revision_id='foreign' if bad else 'source:r1', evidence_ref_id='shared-ref',
                       source_revision_sha256=sha, result=N(outcome='enough', truncated=False,
                       line_start=i+1, line_end=i+1, content=r.anchor_id)) for i, r in enumerate(requests))
    monkeypatch.setattr(selected_observation_reads, 'select_observations_direct', select)
    monkeypatch.setattr(world_graph_reads, 'read_source_anchors_direct_v2', open_sources)
    return reader, selections, reads


def test_reader_combines_selected_actions_without_cross_subject_support(monkeypatch):
    reader, selections, reads = batch_reader(monkeypatch)
    actions = [a for a in reader.actions.values() if a['kind'] == 'graph_observations']
    result = asyncio.run(reader.retrieve_many(actions))
    assert len(selections) == len(reads) == 1
    assert len(selections[0]) == len(reads[0]) == 2
    for action in actions:
        unit = result[action['id']][0]
        assert [p['text'] for p in unit['opened_passages']] == ['anchor:' + unit['assertion_id']]
    again = asyncio.run(reader.retrieve_many(actions))
    assert again == result
    assert reader.wave_events == ['open', 'closed', 'open', 'closed']
    assert len(reads) == 1  # Same source pins are opened once per reader.


def test_reader_chunks_selection_at_existing_eight_id_boundary(monkeypatch):
    reader, selections, reads = batch_reader(monkeypatch, count=9)
    actions = [a for a in reader.actions.values() if a['kind'] == 'graph_observations']
    result = asyncio.run(reader.retrieve_many(actions))
    assert sorted(map(len, selections)) == [1, 8]
    assert len(reads) == 1 and len(reads[0]) == 9
    assert len(result) == 9


def test_reader_rejects_foreign_source_and_non_catalog_actions(monkeypatch):
    reader, _, _ = batch_reader(monkeypatch, bad=True)
    actions = [a for a in reader.actions.values() if a['kind'] == 'graph_observations']
    with pytest.raises(ValueError, match='Opened source proof'):
        asyncio.run(reader.retrieve_many(actions))
    assert not reader.trace
    assert reader.wave_events == ['open', 'closed']
    with pytest.raises(ValueError, match='catalog'):
        asyncio.run(reader.retrieve_many([{**actions[0], 'unit_ids': ['foreign']}]))


@pytest.mark.parametrize('failure', [None, 'partial', 'unavailable', 'bad_unit'])
def test_loop_batches_only_selected_wave_and_stops_before_decision_on_failure(tmp_path, failure):
    original, catalog = live_fixture()
    catalog['initial_actions'] = ['a1', 'a2']
    waves, calls = [], []
    async def acquire(actions):
        waves.append([a['id'] for a in actions])
        if failure == 'unavailable':
            raise TimeoutError()
        result = {a['id']: [deepcopy(original['units'][uid]) for uid in a['unit_ids']] for a in actions}
        if failure == 'partial':
            result.pop('a2')
        if failure == 'bad_unit':
            result['a2'][0]['text'] = 'tampered'
        return result
    async def evaluate(request):
        calls.append(request)
        return decisions(request)
    result = asyncio.run(run_loop(catalog, evaluate, output=tmp_path/'run', retrieve_many=acquire))
    assert waves == [['a1', 'a2']]
    assert result['status'] == ('retrieval_unavailable_or_invalid' if failure else 'provisionally_supported')
    assert len(calls) == (0 if failure else 1)
    if failure:
        with pytest.raises(ValueError):
            writer_request(result, 'question')


def test_batch_heading_continuation_waits_for_parent_read(tmp_path):
    snap = fixture()
    snap['initial_actions'] = ['a3']
    snap['actions']['a1']['kind'] = 'saved_build_section'
    snap['units']['u1']['provenance'] = [{'start_line': 2, 'end_line': 2}]
    snap['actions']['a3']['continuation_action_ids'] = ['a1']
    snap['units']['u3']['text'] = '# Assembly\n'
    import hashlib
    snap['units']['u3']['content_sha256'] = hashlib.sha256(b'# Assembly\n').hexdigest()
    waves = []
    async def acquire(actions):
        waves.append([a['id'] for a in actions])
        return {a['id']: [snap['units'][uid] for uid in a['unit_ids']] for a in actions}
    async def evaluate(request):
        return decisions(request)
    result = asyncio.run(run_loop(snap, evaluate, output=tmp_path/'run', retrieve_many=acquire))
    assert waves == [['a3'], ['a1'], ['a2']]
    assert result['status'] == 'provisionally_supported'
    assert [b['action_ids'] for b in result['acquisition_batches']] == waves
    assert all(b['elapsed_seconds'] >= 0 for b in result['acquisition_batches'])
