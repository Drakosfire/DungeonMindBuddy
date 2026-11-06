import copy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from uuid import UUID

import pytest

from ingestion_evaluation.runner import Runner, digest, tooling_identity, verify_manifest
from ingestion_evaluation.source_authority import (
    AUTHORITY, HEAD, SourceAuthorityBackend, SourceAuthorityRunner, conserve_source_rows,
)


class Backend:
    def __init__(self):
        self.data = {'unchanged': True}
        self.inputs = {'operation': 'extend_support', 'context': {'source_epoch': 19}}
        self.calls = 0
        self.did_commit = False
        self.transport_error = False
        self.verification_error = False

    @contextmanager
    def lease(self):
        yield

    def snapshot(self):
        return copy.deepcopy(self.data)

    def preflight(self):
        return copy.deepcopy(self.inputs)

    def dispatch(self):
        self.calls += 1
        self.did_commit = True
        if self.transport_error:
            raise RuntimeError('transport failed after commit')
        return {'status': 200, 'body_base64': 'e30='}

    def verify(self, qualified, after):
        if self.verification_error or not self.did_commit:
            raise ValueError('source proof unavailable')
        return {'exact_source_opened': True}

    def committed(self, prepared):
        return self.did_commit

    def redact(self, error):
        return error


@pytest.fixture
def lane(tmp_path):
    manifest = {'mode': 'source_authority_v1', '_output': str(tmp_path)}
    backend = Backend()
    return SourceAuthorityRunner(manifest, 'manifest-pin', backend), backend


def test_once_execution_and_committed_transport_error_recovery(lane):
    runner, backend = lane
    q = runner.qualify()['qualification_sha256']
    backend.transport_error = True
    backend.verification_error = True
    assert runner.execute(q)['state'] == 'committed_unverified'
    assert (runner.output / 'source-dispatch-error.json').exists()
    assert (runner.output / 'source-outcome.json.snapshot.json').exists()
    with pytest.raises(ValueError, match='Already dispatched'):
        runner.execute(q)
    backend.verification_error = False
    assert runner.inspect()['state'] == 'verified'
    report = runner.report()
    assert report['state'] == 'verified'
    assert report['outcome']['state'] == 'committed_unverified'
    assert report['latest_assessment']['state'] == 'verified'
    assert backend.calls == 1


def test_process_interruption_marker_never_allows_redispatch(lane):
    runner, backend = lane
    q = runner.qualify()['qualification_sha256']
    runner.record('source-execution.json', {'manifest_sha256': runner.sha,
                                         'qualification_sha256': q, 'operation': 'extend_support'})
    reconstructed = SourceAuthorityRunner(runner.manifest, runner.sha, backend)
    assert reconstructed.report()['state'] == 'outcome_unknown'
    with pytest.raises(ValueError, match='Already dispatched'):
        reconstructed.execute(q)
    assert reconstructed.inspect()['state'] == 'outcome_unknown'
    assert backend.calls == 0


@pytest.mark.parametrize('drift', ['inputs', 'snapshot'])
def test_pre_dispatch_drift_has_no_effect(lane, drift):
    runner, backend = lane
    q = runner.qualify()['qualification_sha256']
    if drift == 'inputs':
        backend.inputs['context']['source_epoch'] = 20
    else:
        backend.data['foreign_writer'] = True
    with pytest.raises(ValueError, match='drift'):
        runner.execute(q)
    assert backend.calls == 0
    assert not (runner.output / 'source-execution.json').exists()


def test_qualification_and_manifest_pins_are_not_advisory(lane):
    runner, backend = lane
    q = runner.qualify()['qualification_sha256']
    with pytest.raises(ValueError, match='pin mismatch'):
        runner.execute('bad-pin')
    other = SourceAuthorityRunner(runner.manifest, 'different-manifest', backend)
    with pytest.raises(ValueError, match='differs'):
        other.execute(q)
    assert backend.calls == 0


def test_inspection_cannot_rebase_qualification_after_execution(lane):
    runner, backend = lane
    runner.execute(runner.qualify()['qualification_sha256'])
    path = runner.output / 'source-qualification.json'
    data = json.loads(path.read_bytes())
    data['snapshot']['unexpected_change'] = True
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='pins differ'):
        runner.inspect()
    assert backend.calls == 1


def test_private_output_and_explicit_qualification_are_required(lane, tmp_path):
    runner, backend = lane
    runner.qualify()
    with pytest.raises(ValueError, match='SHA is required'):
        runner.execute(None)
    public = tmp_path / 'public'
    public.mkdir(mode=0o755)
    with pytest.raises(ValueError, match='must be private'):
        SourceAuthorityRunner({**runner.manifest, '_output': str(public)}, runner.sha, backend)
    assert backend.calls == 0


def rows(operation='extend_support'):
    before = {'app': {'ingest.run': [['old-run', 1]], 'source.revision': [['source', 1]]},
              'native': {HEAD: [['our-old', 1], ['other-world', 1]], AUTHORITY: [['epoch-old', 1]],
                         'dungeonmind.knowledge_revisions': [['old-revision', 1]]}}
    after = copy.deepcopy(before)
    after['native'][HEAD] = [['our-new', 1], ['other-world', 1]]
    after['native'][AUTHORITY] = [['epoch-new', 1]]
    after['native']['dungeonmind.knowledge_revisions'].append(['new-revision', 1])
    if operation == 'admit_context':
        after['app']['ingest.run'].append(['new-intent', 1])
    old = {HEAD: {'hash': 'our-old'}, AUTHORITY: {'hash': 'epoch-old'}}
    new = {HEAD: {'hash': 'our-new'}, AUTHORITY: {'hash': 'epoch-new'}}
    return before, after, old, new


@pytest.mark.parametrize('operation', ['admit_context', 'extend_support'])
def test_source_conservation_permits_only_selected_head_replacements(operation):
    before, after, old, new = rows(operation)
    conserve_source_rows(before, after, operation, old, new)
    changed = copy.deepcopy(after)
    changed['native'][HEAD][1][0] = 'changed-other-world'
    with pytest.raises(ValueError, match='Another World'):
        conserve_source_rows(before, changed, operation, old, new)


@pytest.mark.parametrize('damage', ['source', 'old-row', 'extra-intent', 'unknown-table'])
def test_source_conservation_rejects_unowned_or_unexplained_effects(damage):
    before, after, old, new = rows()
    if damage == 'source':
        after['app']['source.revision'] = [['different-source', 1]]
    elif damage == 'old-row':
        after['native']['dungeonmind.knowledge_revisions'] = [['new-revision', 1]]
    elif damage == 'extra-intent':
        after['app']['ingest.run'].append(['unwanted-intent', 1])
    else:
        after['native']['unknown.table'] = []
    with pytest.raises(ValueError):
        conserve_source_rows(before, after, 'extend_support', old, new)


def source_backend(operation='extend_support'):
    backend = object.__new__(SourceAuthorityBackend)
    body = 'Example source.\n'
    source = SimpleNamespace(markdown=body, source_artifact_id='app:source',
                             source_revision_id=UUID('00000000-0000-0000-0000-000000000001'),
                             content_sha256=digest(body.encode()))
    bound = {'native_world_id': 'world', 'managed_world_id': 'world', 'binding_version': 3}
    context = {'revision_id': 'parent', 'source_epoch': 7}
    backend.operation = operation
    backend.manifest = {'world_id': 'world', 'native_context': context}
    backend.item = {'campaign_id': 'campaign', 'session_id': 'session-9'}
    backend._source = lambda: (source, bound)
    backend._core = lambda: (SimpleNamespace(get_native_source_evidence_extension_receipt=lambda *a: None),
                            context, SimpleNamespace(parsed=SimpleNamespace(evidence_by_id={})), {})
    admitted = SimpleNamespace(state='admitted', opening=SimpleNamespace(state='verified'),
                               admission_id='admission', source_artifact_id='src:test', source_revision_id='srev:test')
    backend._admission = lambda *a: admitted if operation == 'extend_support' else None
    backend._mutable = lambda *a: {AUTHORITY: {'data': {'epoch': 7}}}
    if operation == 'extend_support':
        backend.request = {'managed_world_id': 'world', 'extension_id': 'extension',
                           'original_admission_id': 'admission', 'source_artifact_id': 'src:test',
                           'source_revision_id': 'srev:test', 'expected_body_sha256': source.content_sha256,
                           'expected_parent_revision_id': 'parent', 'expected_source_authority_epoch': 7,
                           'created_at': '2026-11-06T00:00:00Z', 'spans': [
                               {'client_ref': 'clause', 'evidence_role': 'support', 'start_byte': 0,
                                'end_byte': len(body.encode()), 'expected_slice_sha256': source.content_sha256}]}
    else:
        backend.request = {'operation': 'build_graph_preview_bundle', 'managed_world_id': 'world',
                           'campaign_id': 'campaign', 'session': 9, 'include_graph_extraction': False,
                           'native_recap_source': {'source_artifact_id': source.source_artifact_id,
                                                   'source_revision_id': str(source.source_revision_id),
                                                   'content_sha256': source.content_sha256}}
    return backend


@pytest.mark.parametrize('damage', ['role', 'bytes', 'parent', 'world'])
def test_extension_request_must_be_exact_source_only(damage):
    backend = source_backend()
    if damage == 'role':
        backend.request['spans'][0]['evidence_role'] = 'contradiction'
    elif damage == 'bytes':
        backend.request['spans'][0]['expected_slice_sha256'] = '0' * 64
    elif damage == 'parent':
        backend.request['expected_parent_revision_id'] = 'different-parent'
    else:
        backend.request['managed_world_id'] = 'other-world'
    with pytest.raises(ValueError):
        backend.preflight()


def test_source_interval_cannot_split_a_utf8_character():
    backend = source_backend()
    source, bound = backend._source()
    source.markdown = 'Mira’s lantern.'
    source.content_sha256 = digest(source.markdown.encode())
    backend.request['expected_body_sha256'] = source.content_sha256
    backend.request['spans'][0].update(end_byte=5,
        expected_slice_sha256=digest(source.markdown.encode()[:5]))
    with pytest.raises(UnicodeDecodeError):
        backend.preflight()


@pytest.mark.parametrize('field,value', [('include_graph_extraction', True), ('raw_text', 'arbitrary text'),
                                       ('force_graph_run', True), ('graph_model_id', 'another-model')])
def test_source_admission_cannot_smuggle_an_extraction_request(field, value):
    backend = source_backend('admit_context')
    backend.request[field] = value
    with pytest.raises(ValueError):
        backend.preflight()


def test_source_admission_reuses_owning_topology_gate(monkeypatch):
    from apps.live_control_server.services.native_recap_source_admission import NativeRecapError
    backend = source_backend('admit_context')
    monkeypatch.setenv('DMB_NATIVE_RECAP_EXECUTION_SCOPE', 'unsupported-distributed-mode')
    with pytest.raises(NativeRecapError):
        backend.preflight()


def test_schema_probe_failure_is_before_dispatch(lane):
    runner, backend = lane
    def absent_table():
        raise ValueError('Unknown actual mutable table name')
    backend.preflight = absent_table
    with pytest.raises(ValueError, match='mutable table'):
        runner.qualify()
    assert backend.calls == 0
    assert not (runner.output / 'source-qualification.json').exists()


def test_source_manifest_cannot_enter_ordinary_capture(lane):
    runner, backend = lane
    with pytest.raises(ValueError, match='cannot run the capture'):
        Runner(runner.manifest, runner.sha, backend)


def test_source_manifest_needs_no_source_file_and_cli_cannot_dispatch_capture(tmp_path):
    runtime = tmp_path / 'runtime.json'
    runtime.write_text(json.dumps({'root': str(tmp_path), 'files': []}))
    request, review = tmp_path / 'request.json', tmp_path / 'review.json'
    request.write_text('{}')
    review.write_text('{}')
    def pin(p):
        return {'path': str(p), 'sha256': digest(p.read_bytes())}
    manifest = {'schema': 'dmb_ingestion_evaluation_v1', 'mode': 'source_authority_v1',
                'tooling_sha256': tooling_identity(), 'runtime': pin(runtime),
                'output': str(tmp_path / 'records'), 'app_append_tables': [],
                'source_authority': {'operation': 'extend_support', 'review_pins': [pin(review)]},
                'items': [{'id': 'source', 'retained_run_id': 'existing-run',
                           'expected_run_revision': 5, 'request': pin(request)}]}
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(manifest))
    verified, _ = verify_manifest(path)
    assert 'source' not in verified['items'][0]
    script = Path(__file__).resolve().parents[1] / 'scripts/evaluate_ingestion.py'
    result = subprocess.run([sys.executable, str(script), 'capture', '--manifest', str(path)], capture_output=True, text=True)
    assert result.returncode != 0 and 'own explicit manifest mode' in result.stderr
    result = subprocess.run([sys.executable, str(script), 'source-report', '--manifest', str(path)], capture_output=True, text=True)
    assert result.returncode == 0 and json.loads(result.stdout)['state'] == 'not_dispatched'


def test_lost_http_copy_does_not_become_source_authority(lane):
    runner, backend = lane
    runner.execute(runner.qualify()['qualification_sha256'])
    (runner.output / 'source-http.json').unlink()
    assert runner.inspect()['state'] == 'verified'
    assert backend.calls == 1


def test_mutable_schema_is_probed_before_source_dispatch():
    backend = object.__new__(SourceAuthorityBackend)
    @contextmanager
    def connection(role):
        def execute(query, values):
            data = ({'space_id': 'world', 'head_revision_id': 'head', 'updated_at': 'now', 'schema_version': 1}
                    if values == ('world',) else {'singleton_id': 1, 'epoch': 19, 'unreviewed_column': 'new'})
            return SimpleNamespace(fetchall=lambda: [('hash', data)])
        yield SimpleNamespace(execute=execute)
    backend.buddy = SimpleNamespace(connection=connection)
    with pytest.raises(ValueError, match='Unsupported mutable'):
        backend._mutable('world')


@pytest.mark.parametrize('fail', [False, True])
def test_exact_route_window_restores_readonly_and_forbids_external_http(monkeypatch, fail):
    import httpx
    import fastapi.testclient
    backend = source_backend()
    backend.manifest['operator_token_env'] = 'TEST_SOURCE_TOKEN'
    monkeypatch.setenv('TEST_SOURCE_TOKEN', 'test-only')
    monkeypatch.setenv('DMB_AGENT_GRAPH_SESSION_STORE', 'test-auth')
    monkeypatch.setenv('TEST_SOURCE_APP_DSN', 'initial')
    monkeypatch.setenv('TEST_SOURCE_NATIVE_DSN', 'initial')
    monkeypatch.delenv('DMB_AGENT_GRAPH_LOCAL_PROFILE', raising=False)
    class Buddy:
        auth_path = 'test-auth'
        db = {'app': {'product_env': 'TEST_SOURCE_APP_DSN'}, 'native': {'product_env': 'TEST_SOURCE_NATIVE_DSN'}}
        def _dsn(self, role, *, write=False):
            if role == 'native' and write:
                raise ValueError('Native writes prohibited')
            return f'postgresql://test@localhost:1/{role}?options=-c%20default_transaction_read_only=' + ('off' if write else 'on')
        def _bind(self, *, read_only):
            for role in self.db:
                os.environ[self.db[role]['product_env']] = self._dsn(role, write=role == 'app' and not read_only)
    backend.buddy = Buddy()
    backend.buddy._bind(read_only=True)
    original = httpx.HTTPTransport.handle_request
    calls = []
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, route, json):
            calls.append(route)
            assert 'options=-c%20' in os.environ['TEST_SOURCE_NATIVE_DSN']
            with pytest.raises(AssertionError, match='External HTTP'):
                httpx.HTTPTransport.handle_request(None, None)
            if fail:
                raise RuntimeError('owned route failure')
            return SimpleNamespace(status_code=200, content=b'{}')
    monkeypatch.setattr(fastapi.testclient, 'TestClient', Client)
    if fail:
        with pytest.raises(RuntimeError, match='owned route'):
            backend.dispatch()
    else:
        assert backend.dispatch()['status'] == 200
    assert calls == ['/api/live/source-statements/extend-evidence']
    assert os.environ['TEST_SOURCE_NATIVE_DSN'] == backend.buddy._dsn('native')
    assert os.environ['TEST_SOURCE_APP_DSN'] == backend.buddy._dsn('app')
    assert httpx.HTTPTransport.handle_request is original
