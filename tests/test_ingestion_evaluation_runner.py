"""Evaluation orchestration invariants; actual ingestion semantics remain product-owned."""
import copy
from contextlib import contextmanager
import json
from pathlib import Path

import pytest

from ingestion_evaluation.runner import Runner, conserve, digest, encoded, tooling_identity, verify_manifest


class Backend:
    def __init__(self, state='reviewable'):
        self.data = {'app': {'ingest.run': []}, 'native': {}}
        self.state = state
        self.calls = []
        self.on_capture = lambda *_: None

    @contextmanager
    def capture_lease(self):
        if getattr(self, 'leased', False):
            raise ValueError('Another evaluator capture owns the database lease')
        self.leased = True
        try:
            yield
        finally:
            self.leased = False

    def snapshot(self):
        return copy.deepcopy(self.data)

    def qualify(self, item):
        return {'id': item['id'], 'source': 'pin', 'prior_runs': []}

    def capture(self, item, qualified, prefix):
        self.calls.append(item['id'])
        self.data['app']['ingest.run'].append([item['id'], 1])
        self.on_capture(item, prefix)
        return {'state': self.state}

    def check_conservation(self, before):
        assert self.data['native'] == before['native']
        conserve(before['app'], self.data['app'], {'ingest.run'})

    def observe(self, item):
        return {'id': item['id'], 'state': 'actual'}

    def audit(self, item, qualified, output):
        return {'failed_boundary': None if self.state == 'reviewable' else 'capture',
                'accounting': None, 'missing_accounting_is_not_zero': True}


@pytest.fixture
def setup(tmp_path):
    manifest = {'_output': str(tmp_path), 'items': [{'id': 'one', 'request': {}}, {'id': 'two', 'request': {}}]}
    backend = Backend()
    return Runner(manifest, 'manifest', backend), backend


def test_one_qualification_and_capture_stop_replay(setup):
    runner, backend = setup
    sha = runner.qualify()
    assert runner.capture(sha)['state'] == 'completed'
    assert backend.calls == ['one', 'two']
    with pytest.raises(ValueError, match='already dispatched'):
        runner.capture(sha)
    runner.audit()
    assert runner.report()['next_unproven_boundary'] == 'independent_semantic_assessment'
    assert runner.report()['publication'] == 'unproven'


def test_pause_between_items_does_not_dispatch_next_item(setup):
    runner, backend = setup
    backend.on_capture = lambda item, prefix: (prefix.parent / 'PAUSE').touch()
    assert runner.capture(runner.qualify())['state'] == 'paused'
    assert backend.calls == ['one']
    assert not (runner.output / 'two.dispatch.json').exists()


def test_failed_capture_stops_and_missing_cost_is_not_zero(setup):
    runner, backend = setup
    backend.state = 'failed'
    assert runner.capture(runner.qualify())['state'] == 'stopped_at_capture_boundary'
    assert backend.calls == ['one']
    runner.audit()
    report = runner.report()
    assert report['next_unproven_boundary'] == 'capture'
    assert report['audit']['items'][0]['accounting'] is None


def test_interrupted_dispatch_is_not_replayed_or_audited_as_terminal(setup):
    runner, backend = setup
    def interrupt(*_):
        raise RuntimeError('Interrupted after intent, outcome unknown')
    backend.on_capture = interrupt
    sha = runner.qualify()
    with pytest.raises(RuntimeError):
        runner.capture(sha)
    assert (runner.output / 'one.dispatch.json').exists()
    assert not (runner.output / 'terminal.json').exists()
    with pytest.raises(ValueError, match='already dispatched'):
        runner.capture(sha)
    with pytest.raises(ValueError, match='Terminal evidence missing'):
        runner.audit()


def test_manifest_and_snapshot_drift_stop_before_dispatch(setup):
    runner, backend = setup
    sha = runner.qualify()
    with pytest.raises(ValueError, match='pin mismatch'):
        runner.capture('badpin')
    backend.data['native']['changed'] = []
    with pytest.raises(ValueError, match='Database drift'):
        runner.capture(sha)
    assert backend.calls == []


def test_conservation_rejects_deletion_and_unowned_mutation():
    before = {'ingest.run': [['old', 1]], 'other': []}
    conserve(before, {'ingest.run': [['old', 1], ['new', 1]], 'other': []}, {'ingest.run'})
    with pytest.raises(ValueError, match='Prior rows changed'):
        conserve(before, {'ingest.run': [], 'other': []}, {'ingest.run'})
    with pytest.raises(ValueError, match='Unpermitted'):
        conserve(before, {'ingest.run': [['old', 1]], 'other': [['x', 1]]}, {'ingest.run'})


def test_runtime_and_source_pins_checked(tmp_path):
    runtime = tmp_path / 'runtime'; runtime.mkdir()
    member = runtime / 'module.py'; member.write_text('original')
    runtime_manifest = tmp_path / 'runtime.json'
    runtime_manifest.write_bytes(encoded({'root': str(runtime), 'files': [{'path': 'module.py', 'sha256': digest(member.read_bytes())}]}))
    source = tmp_path / 'source.md'; source.write_text('source')
    request = tmp_path / 'request.json'; request.write_text('{}')
    pin = lambda p: {'path': str(p), 'sha256': digest(p.read_bytes())}
    manifest = tmp_path / 'manifest.json'
    manifest.write_bytes(encoded({'schema': 'dmb_ingestion_evaluation_v1', 'tooling_sha256': tooling_identity(), 'runtime': pin(runtime_manifest),
        'output': str(tmp_path / 'out'), 'items': [{'id': 'one', 'source': pin(source), 'request': pin(request)}]}))
    verify_manifest(manifest)
    member.write_text('drift')
    with pytest.raises(ValueError, match='Runtime drift'):
        verify_manifest(manifest)


def test_paused_report_keeps_undispatched_capture_unproven(setup):
    runner, backend = setup
    backend.on_capture = lambda item, prefix: (prefix.parent / 'PAUSE').touch()
    runner.capture(runner.qualify())
    runner.audit()
    assert runner.report()['next_unproven_boundary'] == 'capture_remaining_items'


def test_audit_report_reject_rebound_manifest(setup):
    runner, backend = setup
    runner.capture(runner.qualify())
    runner.manifest_sha = 'changed'
    with pytest.raises(ValueError, match='Manifest differs'):
        runner.audit()
    with pytest.raises(ValueError, match='Manifest differs'):
        runner.report()


def test_retained_evidence_manifest_can_never_dispatch(setup):
    runner, backend = setup
    runner.manifest['items'][0]['retained_run_id'] = 'actual-run'
    with pytest.raises(ValueError, match='read-only'):
        runner.capture('anything')
    assert backend.calls == []


@pytest.mark.parametrize('failure', ['http500', 'exception', 'startup_redirect', 'success'])
def test_buddy_adapter_stops_on_transport_failure_even_if_run_is_reviewable(tmp_path, monkeypatch, failure):
    import os
    import sys
    from types import SimpleNamespace
    from fastapi import FastAPI
    from contextlib import asynccontextmanager
    from ingestion_evaluation.buddy import Buddy

    calls = []
    @asynccontextmanager
    async def lifespan(app):
        if failure == 'startup_redirect':
            os.environ['APP_TEST_BINDING'] = 'unexpected'
        yield
    app = FastAPI(lifespan=lifespan)
    @app.post('/api/live/recap-ingest')
    def ordinary_route():
        calls.append('ordinary')
        if failure == 'exception':
            raise RuntimeError('Synthetic ASGI failure')
        from fastapi.responses import Response
        return Response(content=b'{"retained":"exact"}', status_code=500 if failure == 'http500' else 200)
    monkeypatch.setitem(sys.modules, 'apps.live_control_server.main', SimpleNamespace(create_app=lambda: app))
    monkeypatch.setitem(sys.modules, 'application_state.ingest.components', SimpleNamespace(get_component_bytes=lambda **_: b'{}'))
    request = tmp_path / 'request.json'; request.write_bytes(b'{"operation":"generate_recap_memory"}')
    item = {'id': 'one', 'request': {'path': str(request), 'sha256': digest(request.read_bytes())}}
    adapter = object.__new__(Buddy)
    adapter.manifest = {'operator_token_env': 'EVALUATOR_TEST_TOKEN'}
    monkeypatch.setenv('EVALUATOR_TEST_TOKEN', 'synthetic-secret')
    adapter.auth_path = str(tmp_path / 'auth.json')
    monkeypatch.setenv('DMB_AGENT_GRAPH_SESSION_STORE', adapter.auth_path)
    monkeypatch.delenv('DMB_AGENT_GRAPH_LOCAL_PROFILE', raising=False)
    adapter.db = {'app': {'product_env': 'APP_TEST_BINDING'}, 'native': {'product_env': 'NATIVE_TEST_BINDING'}}
    adapter.dsns = {}
    adapter._dsn = lambda role, **_: 'isolated-' + role
    def bind(**_):
        for role, spec in adapter.db.items():
            monkeypatch.setenv(spec['product_env'], 'isolated-' + role)
    adapter._bind = bind
    adapter.snapshot = lambda: {}
    adapter._assert_no_active_transactions = lambda: None
    adapter.check_conservation = lambda _: None
    adapter._runs = lambda _: [SimpleNamespace(run_id='actual-new-run', status='reviewable', components={}, model_dump=lambda **_: {'status': 'reviewable'})]
    result = adapter.capture(item, {'prior_runs': {}}, tmp_path / 'one')
    if failure == 'success':
        assert result['state'] == 'reviewable'
    else:
        assert result['state'] != 'reviewable'
    if failure == 'startup_redirect':
        assert calls == []
    else:
        import base64
        receipt = json.loads((tmp_path / 'one.http.json').read_bytes())
        raw = base64.b64decode(receipt['body_base64'])
        assert digest(raw) == receipt['body_sha256']
    if failure == 'exception':
        assert 'Synthetic ASGI failure' in (tmp_path / 'one.asgi-errors.json').read_text()


def test_ambient_local_profile_rejected_before_product_import(tmp_path, monkeypatch):
    from ingestion_evaluation.buddy import Buddy
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_PROFILE', '/unreviewed/profile')
    with pytest.raises(ValueError, match='Implicit local profile'):
        Buddy({'_runtime_root': str(tmp_path), 'environment': {}})


def test_database_options_are_percent_encoded_and_native_cannot_write():
    from ingestion_evaluation.buddy import Buddy
    adapter = object.__new__(Buddy)
    adapter.dsns = {'native': 'postgresql://synthetic@127.0.0.1:5555/example'}
    adapter.db = {'native': {'host': '127.0.0.1', 'port': 5555, 'database': 'example'}}
    uri = adapter._dsn('native')
    assert '%20' in uri and '+' not in uri
    with pytest.raises(ValueError, match='Native writes'):
        adapter._dsn('native', write=True)


def test_independent_receipts_reject_forged_coordinates_and_raw_rows():
    from ingestion_evaluation.evidence import inspect_quotes
    source = 'One claim.  \n\nAnother claim.'
    ix = {'spans': [{'source_span_id': 's1', 'start_line': 1, 'end_line': 1},
                    {'source_span_id': 's2', 'start_line': 3, 'end_line': 3}], 'content_sha256': digest(source.encode())}
    graph = {'nodes': [{'evidence_refs': [{'source_span_ref_id': 's1', 'anchor_quotes': ['One claim.'],
        'anchor_quote_matches': [{'char_start': 0, 'char_end': 10, 'match_text': 'One claim.', 'quote': 'One claim.'}]}]}]}
    diag = {'compact_evidence_context': {'entries': [
        {'source_span_ref_id': 's1', 'text': 'One claim.  ', 'text_sha256': digest(b'One claim.  ')},
        {'source_span_ref_id': 's2', 'text': 'Another claim.', 'text_sha256': digest(b'Another claim.')}]},
        'canonical_quote_bindings': [{'quote': 'One claim.', 'canonical_span_ref_id': 's1',
            'nominated_span_ref_id': 's2', 'source_sha256': ix['content_sha256'], 'pass_name': 'synthetic'}]}
    assert not inspect_quotes(graph, ix, source, diag, {'synthetic'})['issues']
    bad_graph = copy.deepcopy(graph)
    bad_graph['nodes'][0]['evidence_refs'][0]['anchor_quote_matches'][0]['char_start'] = 1
    assert inspect_quotes(bad_graph, ix, source, diag, {'synthetic'})['issues']
    forged = copy.deepcopy(diag)
    forged['compact_evidence_context']['entries'][0]['text'] = 'One claim.'
    forged['compact_evidence_context']['entries'][0]['text_sha256'] = digest(b'One claim.')
    assert inspect_quotes(graph, ix, source, forged, {'synthetic'})['issues']


def test_audit_rejects_mixed_database_interval(setup):
    runner, backend = setup
    runner.capture(runner.qualify())
    original = backend.audit
    def drift(*args):
        result = original(*args)
        backend.data['native']['drift'] = []
        return result
    backend.audit = drift
    with pytest.raises(ValueError, match='State changed during audit'):
        runner.audit()


def test_unknown_prior_source_blocks_new_output_directory(setup):
    runner, backend = setup
    original = backend.qualify
    backend.qualify = lambda item: {**original(item), 'unresolved_prior_runs': ['existing-unknown']}
    with pytest.raises(ValueError, match='unresolved prior execution'):
        runner.capture(runner.qualify())
    assert backend.calls == []


def test_capture_lease_blocks_concurrent_output_directories(setup, tmp_path):
    runner, backend = setup
    with backend.capture_lease():
        with pytest.raises(ValueError, match='database lease'):
            runner.capture(runner.qualify())
    assert backend.calls == []


def test_real_disposable_evaluator_lease_is_global_and_read_only(application_state_dsn):
    import psycopg
    from urllib.parse import urlsplit
    from ingestion_evaluation.buddy import Buddy
    parsed = urlsplit(application_state_dsn)
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        database, oid, cluster = conn.execute('SELECT current_database(), (SELECT oid FROM pg_database WHERE datname=current_database()), system_identifier::text FROM pg_control_system()').fetchone()
    adapter = object.__new__(Buddy)
    adapter.dsns = {'app': application_state_dsn}
    adapter.db = {'app': {'host': parsed.hostname, 'port': parsed.port, 'database': database, 'oid': oid, 'cluster': cluster},
                  'native': {'database': 'unused-disposable-native-name'}}
    with adapter.capture_lease():
        with adapter.connection('app') as conn:
            assert conn.execute('SHOW transaction_read_only').fetchone() == ('on',)
        with pytest.raises(ValueError, match='database lease'):
            with adapter.capture_lease():
                pytest.fail('A second client obtained the same evaluator lease')
    with adapter.capture_lease():
        pass
