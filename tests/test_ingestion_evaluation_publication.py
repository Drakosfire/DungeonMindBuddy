import base64
import copy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from ingestion_evaluation.publication import PublicationBackend, PublicationRunner, conserve_publication
from ingestion_evaluation import authority
from ingestion_evaluation.runner import digest, tooling_identity, verify_manifest
from tests.test_native_recap_preparation import lane as native_lane


class Backend:
    def __init__(self):
        self.data = {'stable': True}
        self.inputs = {'context': {'revision': 'parent', 'source_epoch': 22}}
        self.calls = 0
        self.preparations = 0
        self.did_commit = False
        self.transport_error = self.verify_error = self.config_error = False

    @contextmanager
    def lease(self):
        yield

    def snapshot(self):
        return copy.deepcopy(self.data)

    def prepare_preflight(self):
        if self.config_error:
            raise ValueError('Signing key unavailable')

    def prepare(self):
        self.preparations += 1
        return {'status': 200, 'body_base64': base64.b64encode(b'{"packet":"exact"}').decode()}

    def check_packet(self, packet):
        assert packet == {'packet': 'exact'}

    def preflight(self, packet):
        self.check_packet(packet)
        return copy.deepcopy(self.inputs)

    def confirm(self, packet):
        self.calls += 1
        self.did_commit = True
        if self.transport_error:
            raise RuntimeError('reply lost after commit')
        return {'status': 200, 'body_base64': 'e30='}

    def window(self):
        return {'snapshot': self.snapshot()}

    def verify(self, packet):
        if self.verify_error or not self.did_commit:
            raise ValueError('Core receipt proof unavailable')
        return {'receipt': {'published_revision_id': 'child'}, 'new_objects': 2, 'new_assertions': 3}

    def verify_window(self, q, window, proof):
        if self.verify_error:
            raise ValueError('Execution window unavailable')

    def committed(self, packet):
        return self.did_commit

    def redact(self, error):
        return error


@pytest.fixture
def lane(tmp_path):
    manifest = {'mode': 'reviewed_publication_v1', '_output': str(tmp_path),
                'publication': {}, 'items': [{}]}
    backend = Backend()
    return PublicationRunner(manifest, 'manifest-pin', backend), backend


def ready(runner):
    sha = runner.prepare()['packet_sha256']
    runner.manifest['publication']['reviewed_packet_sha256'] = sha
    return runner.qualify()['qualification_sha256']


def test_prepare_checks_signing_configuration_before_route(lane):
    runner, backend = lane
    backend.config_error = True
    with pytest.raises(ValueError, match='Signing key'):
        runner.prepare()
    assert backend.preparations == backend.calls == 0
    assert not (runner.output / 'publication-prepare-intent.json').exists()


def test_existing_product_signing_guard_has_no_generated_fallback(monkeypatch):
    monkeypatch.delenv('DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY', raising=False)
    backend = object.__new__(PublicationBackend)
    with pytest.raises(Exception, match='not configured'):
        backend._configuration()


def test_run_artifact_is_not_mistaken_for_app_source_revision(monkeypatch):
    from apps.live_control_server.services import graph_run_registry
    data = SimpleNamespace(run=SimpleNamespace(revision=5, campaign_id='campaign', session_id='session-1'),
                           source_artifact=SimpleNamespace(source_artifact_id='artifact'),
                           source_bytes=b'source', candidate_bytes=b'candidate')
    monkeypatch.setattr(graph_run_registry, 'load_reviewable_extraction_data', lambda *args: data)
    backend = object.__new__(PublicationBackend)
    backend.manifest = {'world_id': 'world'}
    backend.item = {'retained_run_id': 'run', 'expected_run_revision': 5, 'campaign_id': 'campaign',
                    'session_id': 'session-1', 'source_artifact_id': 'artifact',
                    'effective_sha256': digest(b'source'), 'source_revision_id': 'APP-owned-revision'}
    backend.request = SimpleNamespace(managed_world_id='world', run_id='run', expected_run_revision=5,
                                     candidate_sha256=digest(b'candidate'))
    assert backend._data() is data  # APP revision is checked on the source owner's result instead.


@pytest.fixture
def owning_publication(native_lane, monkeypatch):
    from apps.live_control_server.services import graph_run_registry
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from apps.live_control_server.models.native_recap_preparation import NativeRecapPrepareRequest
    monkeypatch.setattr(graph_run_registry, 'load_reviewable_extraction_data', lambda *args: native_lane.data)
    monkeypatch.setattr(native, 'read_repository', lambda: native_lane.repo)
    backend = object.__new__(PublicationBackend)
    backend.buddy = SimpleNamespace()
    backend.request = NativeRecapPrepareRequest.model_validate(native_lane.body)
    backend.manifest = {'world_id': 'managed', 'publication': {'principal': 'local_operator'},
                        'operator_token_env': 'DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN'}
    backend.item = {'retained_run_id': native_lane.run.run_id, 'expected_run_revision': 5,
                    'campaign_id': native_lane.run.campaign_id, 'session_id': native_lane.run.session_id,
                    'source_artifact_id': native_lane.source.source_artifact_id,
                    'source_revision_id': str(native_lane.source.source_revision_id),
                    'effective_sha256': digest(native_lane.data.source_bytes)}
    response = native_lane.post()
    assert response.status_code == 200
    packet = response.json()
    return SimpleNamespace(backend=backend, packet=packet, lane=native_lane, native=native)


@pytest.mark.parametrize('change', ['token', 'prepared', 'request'])
def test_real_owner_signed_packet_refuses_tampering(owning_publication, change):
    state = owning_publication
    state.backend.check_packet(state.packet)
    bad = copy.deepcopy(state.packet)
    if change == 'token':
        bad['token'] += 'tampered'
    elif change == 'prepared':
        bad['prepared']['unexpected'] = True
    else:
        bad['envelope']['review']['candidate_sha256'] = '0' * 64
    with pytest.raises(Exception):
        state.backend.check_packet(bad)


def commit_memory_publication(state):
    from tests.test_native_recap_preparation import TOKEN
    response = state.lane.client.post('/api/live/extract-promote/native-confirm',
        json={k: state.packet[k] for k in ('envelope', 'prepared', 'token')},
        headers={'Authorization': 'Bearer ' + TOKEN})
    assert response.status_code == 200, response.text


def test_actual_owner_commit_and_exact_core_inspection(owning_publication):
    state = owning_publication
    commit_memory_publication(state)
    proof = state.backend.verify(state.packet)
    assert proof['new_objects'] == 2
    assert proof['new_assertions'] == 6
    assert proof['prior_graph_payloads_preserved']


def test_core_result_cannot_turn_expected_claim_into_bare_entity(owning_publication, monkeypatch):
    state = owning_publication
    commit_memory_publication(state)
    repo = state.lane.repo
    original = repo.get_prospective_publication
    def wrong_kind(*args):
        publication = original(*args)
        result = publication.prospective_result
        rows = list(result.results)
        index = next(i for i, r in enumerate(rows) if r.result_kind == 'assertion')
        rows[index] = rows[index].model_copy(update={'result_kind': 'entity'})
        return SimpleNamespace(publication_receipt=publication.publication_receipt,
                               prospective_result=result.model_copy(update={'results': rows}))
    monkeypatch.setattr(repo, 'get_prospective_publication', wrong_kind)
    with pytest.raises(ValueError, match='result kind differs'):
        state.backend.verify(state.packet)


@pytest.mark.parametrize('change', ['value', 'metadata'])
def test_real_core_claim_must_match_value_and_metadata_not_only_counts(owning_publication, monkeypatch, change):
    state = owning_publication
    commit_memory_publication(state)
    publication = state.lane.repo.get_prospective_publication(
        state.packet['envelope']['binding']['native_world_id'], state.packet['envelope']['prepared_change_id'])
    target = next(r.durable_id for r in publication.prospective_result.results if r.result_kind == 'assertion')
    original = state.native.assertion_contract
    def counterfeit(parsed):
        row = original(parsed)
        if row.assertion_id == target:
            if change == 'metadata':
                return row.model_copy(update={'metadata': row.metadata.model_copy(update={'evidence_ref_ids': []})})
            return row.model_copy(update={'predicate': 'wrong:predicate'})
        return row
    monkeypatch.setattr(state.native, 'assertion_contract', counterfeit)
    with pytest.raises(ValueError, match='value/metadata/endpoint'):
        state.backend.verify(state.packet)


def advance_memory_head(state):
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
    from datetime import datetime, timezone
    repo = state.lane.repo
    space = state.packet['envelope']['binding']['native_world_id']
    snapshot = repo.get_revision(space, repo.get_head(space).head_revision_id)
    repo.publish_revision(PublishKnowledgeRevisionCommand(
        space_id=space, expected_parent_revision_id=snapshot.revision.revision_id,
        parent_revision_id=snapshot.revision.revision_id,
        operation_ids=['separate-later-operation'], graph_schema=snapshot.revision.graph_schema,
        graph_payload=snapshot.graph_payload, domain_contract_ref=snapshot.revision.domain_contract_ref,
        semantic_profile_ref=snapshot.revision.semantic_profile_ref, created_at=datetime.now(timezone.utc)))


def test_later_head_does_not_replace_exact_receipted_child_proof(owning_publication):
    state = owning_publication
    commit_memory_publication(state)
    advance_memory_head(state)
    proof = state.backend.verify(state.packet)
    assert proof['receipt']['published_revision_id'] != proof['current_context']['revision_id']
    assert proof['new_assertions'] == 6


def test_stale_parent_stops_before_mutable_probe_or_confirmation(owning_publication):
    state = owning_publication
    advance_memory_head(state)
    with pytest.raises(ValueError, match='parent/epoch drift'):
        state.backend.preflight(state.packet)


def test_expired_signed_packet_stops_before_confirmation(owning_publication, monkeypatch):
    from ingestion_evaluation import publication
    from datetime import datetime, timedelta
    state = owning_publication
    expiry = datetime.fromisoformat(state.packet['envelope']['expires_at'].replace('Z', '+00:00'))
    monkeypatch.setattr(publication, 'datetime', SimpleNamespace(now=lambda tz: expiry + timedelta(seconds=1)))
    with pytest.raises(ValueError, match='expiry'):
        state.backend.preflight(state.packet)


def test_configuration_pins_operator_rotation_and_local_identity(owning_publication, monkeypatch):
    backend = owning_publication.backend
    before = backend._configuration()
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN', 'rotated-synthetic-operator-token')
    assert backend._configuration() != before
    backend.manifest['publication']['principal'] = 'another-principal'
    with pytest.raises(ValueError, match='local operator'):
        backend._configuration()


def test_private_packet_and_exact_independent_review_pin(lane):
    runner, backend = lane
    runner.prepare()
    packet = runner.output / 'publication-packet.json'
    assert packet.stat().st_mode & 0o077 == 0
    with pytest.raises(ValueError, match='independently reviewed'):
        runner.qualify()
    packet.chmod(0o644)
    with pytest.raises(ValueError, match='must be private'):
        runner.packet()
    assert backend.calls == 0


def test_owning_all_held_result_never_becomes_a_confirmation(lane):
    runner, backend = lane
    backend.prepare = lambda: {'status': 200, 'body_base64': base64.b64encode(b'{"status":"held"}').decode()}
    assert runner.prepare()['state'] == 'held'
    assert runner.report()['state'] == 'held'
    assert not (runner.output / 'publication-packet.json').exists()
    assert backend.calls == 0


def test_lost_reply_and_postcommit_verifier_failure_never_reconfirm(lane):
    runner, backend = lane
    q = ready(runner)
    backend.transport_error = backend.verify_error = True
    assert runner.execute(q)['state'] == 'committed_unverified'
    assert (runner.output / 'publication-window.json').exists()
    with pytest.raises(ValueError, match='Already dispatched'):
        runner.execute(q)
    backend.verify_error = False
    assert runner.inspect()['state'] == 'verified'
    report = runner.report()
    assert report['state'] == 'verified'
    assert report['original_outcome']['state'] == 'committed_unverified'
    assert backend.calls == 1


def test_interruption_marker_and_unknown_core_outcome(lane):
    runner, backend = lane
    q = ready(runner)
    runner.record('publication-execution.json', {'manifest_sha256': runner.sha,
                                              'qualification_sha256': q})
    assert runner.report()['state'] == 'outcome_unknown'
    assert runner.inspect()['state'] == 'outcome_unknown'
    with pytest.raises(ValueError, match='Already dispatched'):
        runner.execute(q)
    assert backend.calls == 0


@pytest.mark.parametrize('what', ['snapshot', 'inputs', 'packet', 'qualification'])
def test_drift_stops_before_native_window(lane, what):
    runner, backend = lane
    q = ready(runner)
    if what == 'snapshot':
        backend.data['foreign_writer'] = True
    elif what == 'inputs':
        backend.inputs['context']['source_epoch'] = 23
    else:
        path = runner.output / ('publication-packet.json' if what == 'packet' else 'publication-qualification.json')
        path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError):
        runner.execute(q)
    assert backend.calls == 0
    assert not (runner.output / 'publication-execution.json').exists()


def test_retained_packet_inspection_has_no_write_or_historical_window_claim(lane):
    runner, backend = lane
    sha = runner.prepare()['packet_sha256']
    runner.manifest['items'][0]['retained_packet'] = {'path': str(runner.output / 'publication-packet.json'), 'sha256': sha}
    backend.did_commit = True
    for method in (runner.prepare, runner.qualify, lambda: runner.execute('anything')):
        with pytest.raises(ValueError, match='inspect-only'):
            method()
    assert runner.inspect()['state'] == 'verified_core'
    proof = next(p for p in runner.output.glob('publication-inspection-*.proof.json') if '.core.' not in p.name)
    assert json.loads(proof.read_bytes())['execution_window_verified'] is False
    assert runner.report()['original_outcome'] is None
    assert backend.calls == 0


def test_missing_window_preserves_core_proof_without_claiming_full_verification(lane):
    runner, backend = lane
    runner.execute(ready(runner))
    (runner.output / 'publication-window.json').unlink()
    result = runner.inspect()
    assert result['state'] == 'committed_unverified'
    assert result['core_proof_sha256']
    assert result['observation_sha256']
    assert backend.calls == 1


def snapshots():
    before = {'app': {'app.table': [['old', 1]]}, 'native': {
        authority.HEAD: [['our-old', 1], ['other-world', 1]], authority.AUTHORITY: [['epoch', 1]],
        'source.table': [['source', 1]]}}
    for name in ('knowledge_head_events', 'knowledge_prospective_publication_results',
                 'knowledge_publication_receipts', 'knowledge_revisions'):
        before['native']['dungeonmind.' + name] = [['old', 1]]
    after = copy.deepcopy(before)
    after['native'][authority.HEAD] = [['our-new', 1], ['other-world', 1]]
    for name in set(before['native']) - {authority.HEAD, authority.AUTHORITY, 'source.table'}:
        after['native'][name].append(['new', 1])
    return before, after


@pytest.mark.parametrize('damage', [None, 'APP', 'source', 'epoch', 'old-row', 'other-head', 'extra-row'])
def test_publication_exact_conservation(damage):
    before, after = snapshots()
    if damage == 'APP':
        after['app']['app.table'].append(['new', 1])
    elif damage == 'source':
        after['native']['source.table'] = []
    elif damage == 'epoch':
        after['native'][authority.AUTHORITY] = [['changed', 1]]
    elif damage == 'old-row':
        after['native']['dungeonmind.knowledge_revisions'] = [['new', 2]]
    elif damage == 'other-head':
        after['native'][authority.HEAD][1][0] = 'wrong-world'
    elif damage == 'extra-row':
        after['native']['dungeonmind.knowledge_revisions'].append(['extra', 1])
    call = lambda: conserve_publication(before, after, {'hash': 'our-old'}, {'hash': 'our-new'})
    if damage:
        with pytest.raises(ValueError):
            call()
    else:
        call()


def test_manifest_and_cli_isolate_publication_from_capture_and_sources(tmp_path):
    def pin(path):
        return {'path': str(path), 'sha256': digest(path.read_bytes())}
    runtime = tmp_path / 'runtime.json'
    runtime.write_text(json.dumps({'root': str(tmp_path), 'files': []}))
    request, review = tmp_path / 'request.json', tmp_path / 'review.json'
    request.write_text('{}'); review.write_text('{}')
    m = {'schema': 'dmb_ingestion_evaluation_v1', 'mode': 'reviewed_publication_v1',
         'tooling_sha256': tooling_identity(), 'runtime': pin(runtime), 'app_append_tables': [],
         'publication': {'principal': 'local_operator', 'review_pins': [pin(review)]},
         'items': [{'id': 'publication', 'retained_run_id': 'run', 'expected_run_revision': 5,
                    'request': pin(request)}], 'output': str(tmp_path / 'output')}
    path = tmp_path / 'manifest.json'; path.write_text(json.dumps(m))
    verify_manifest(path)
    script = Path(__file__).resolve().parents[1] / 'scripts/evaluate_ingestion.py'
    for command in ('capture', 'source-execute', 'publication-execute'):
        result = subprocess.run([sys.executable, str(script), command, '--manifest', str(path)], capture_output=True, text=True)
        assert result.returncode != 0
        assert ('own explicit manifest mode' in result.stderr or '--qualification-sha' in result.stderr)
    result = subprocess.run([sys.executable, str(script), 'publication-report', '--manifest', str(path)], capture_output=True, text=True)
    assert result.returncode == 0 and json.loads(result.stdout)['state'] == 'not_dispatched'


@pytest.mark.parametrize('operation', ['publication_prepare', 'publication_confirm'])
@pytest.mark.parametrize('fail', [False, True])
def test_publication_route_window_always_keeps_app_readonly(monkeypatch, operation, fail):
    import httpx
    import fastapi.testclient
    class Buddy:
        auth_path = 'auth'
        db = {'app': {'product_env': 'TEST_PUB_APP'}, 'native': {'product_env': 'TEST_PUB_NATIVE'}}
        def _dsn(self, role, *, write=False):
            if role == 'native' and write:
                raise ValueError('Ordinary native-write ban')
            return f'postgresql://local@localhost:1/{role}?options=-c%20default_transaction_read_only=' + ('off' if write else 'on')
        def _bind(self, *, read_only):
            for role in self.db:
                os.environ[self.db[role]['product_env']] = self._dsn(role, write=role == 'app' and not read_only)
    buddy = Buddy(); buddy._bind(read_only=True)
    monkeypatch.setenv('TEST_PUB_TOKEN', 'token')
    monkeypatch.setenv('DMB_AGENT_GRAPH_SESSION_STORE', 'auth')
    monkeypatch.delenv('DMB_AGENT_GRAPH_LOCAL_PROFILE', raising=False)
    old = httpx.HTTPTransport.handle_request
    calls = []
    class Client:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, route, json):
            calls.append(route)
            assert os.environ['TEST_PUB_APP'] == buddy._dsn('app')
            assert os.environ['TEST_PUB_NATIVE'].endswith('off' if operation == 'publication_confirm' else 'on')
            with pytest.raises(AssertionError, match='External HTTP'):
                httpx.HTTPTransport.handle_request(None, None)
            if fail:
                raise RuntimeError('local failure')
            return SimpleNamespace(status_code=200, content=b'{}')
    monkeypatch.setattr(fastapi.testclient, 'TestClient', Client)
    if fail:
        with pytest.raises(RuntimeError):
            authority.local_route(buddy, operation, {}, 'TEST_PUB_TOKEN')
    else:
        authority.local_route(buddy, operation, {}, 'TEST_PUB_TOKEN')
    assert len(calls) == 1
    assert os.environ['TEST_PUB_NATIVE'] == buddy._dsn('native')
    assert os.environ['TEST_PUB_APP'] == buddy._dsn('app')
    assert httpx.HTTPTransport.handle_request is old
