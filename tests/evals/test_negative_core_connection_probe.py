from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from evals.negative_retrieval import core_connection_probe as probe
from evals.negative_retrieval.source_window import _scope

EXPECTED = {'host': '127.0.0.1', 'port': 32769}


@pytest.fixture
def owners(monkeypatch):
    from dungeonmind.infrastructure.postgres.database import PostgresDatabase, _ScopedReadTransactions

    baseline = ('core', '123', '456', 'reader', 'reader', True)
    monkeypatch.setattr(probe, '_baseline', lambda *_: baseline)

    class Connection:
        closed = False

        def __init__(self):
            self.identity = baseline
            self.events = []
            self.info = SimpleNamespace(host='127.0.0.1', port=32769)

        @contextmanager
        def transaction(self):
            self.events.append('begin')
            try:
                yield self
            except BaseException:
                self.events.append('rollback')
                raise
            else:
                self.events.append('commit')

    monkeypatch.setattr(probe, '_identity', lambda connection: connection.identity)
    connection = Connection()
    original_connect = PostgresDatabase.connect
    monkeypatch.setattr(PostgresDatabase, 'connect', lambda self: connection)
    return PostgresDatabase, _ScopedReadTransactions, connection, baseline, original_connect


def test_known_reused_transaction_is_checked_and_hooks_restored(owners):
    database, scoped, connection, baseline, _ = owners
    before = (database.connect, database.transaction, scoped.transaction)
    turn = object()
    scope_ref = [turn]
    token = _scope.set(turn)
    try:
        with probe.observe_core_connections('unused', EXPECTED, scope_ref=scope_ref) as state:
            # A connection created before observation is still checked at admission.
            with scoped(connection).transaction() as actual:
                assert actual is connection
            assert state['transactions']['scoped'] == 1
            assert state['verified']['scoped'] == 1
            assert state['connections']['scoped'] == 0
        assert state['status'] == 'observed'
        assert state['pending_at_close'] == 0
        assert connection.events == ['begin', 'commit']
        assert (database.connect, database.transaction, scoped.transaction) == before
        assert state['coverage'] == 'partial'
    finally:
        _scope.reset(token)


@pytest.mark.parametrize('identity', [
    ('other', '123', '456', 'reader', 'reader', True),
    ('core', '999', '456', 'reader', 'reader', True),
    ('core', '123', 'different', 'reader', 'reader', True),
    ('core', '123', '456', 'other', 'reader', True),
    ('core', '123', '456', 'reader', 'reader', False),
    None,
])
def test_wrong_identity_or_writable_transaction_rolls_back(owners, identity):
    _, scoped, connection, _, _ = owners
    connection.identity = identity
    with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
        with pytest.raises(ValueError, match='differs'):
            with scoped(connection).transaction():
                pytest.fail('Product must not receive the mismatched transaction')
    assert connection.events == ['begin', 'rollback']
    assert state['mismatches'] == 1 and state['status'] == 'uncertain'
    assert state['verified']['unscoped'] == 0


def test_check_failure_and_product_failure_preserve_original_errors(owners, monkeypatch):
    _, scoped, connection, _, _ = owners
    def failed_check(_):
        raise OSError('check failed')
    monkeypatch.setattr(probe, '_identity', failed_check)
    with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
        with pytest.raises(OSError, match='check failed'):
            with scoped(connection).transaction():
                pass
    assert state['errors'] == 1 and state['status'] == 'uncertain'
    assert connection.events == ['begin', 'rollback']


def test_wrong_endpoint_is_rejected_even_when_database_identity_matches(owners):
    _, scoped, connection, _, _ = owners
    connection.info.port = 1111
    with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
        with pytest.raises(ValueError, match='differs'):
            with scoped(connection).transaction():
                pytest.fail('Product must not receive a connection to the wrong endpoint')
    assert state['mismatches'] == 1
    assert connection.events == ['begin', 'rollback']


def test_open_connection_is_counted_but_never_proves_a_transaction(owners):
    database, _, connection, _, _ = owners
    with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
        assert database('unused').connect() is connection
    assert state['connections']['unscoped'] == 1
    assert state['transactions']['unscoped'] == state['verified']['unscoped'] == 0


def test_witness_queries_are_not_counted_as_product_sql():
    from pathlib import Path
    from evals.negative_retrieval.sql_window import observe_sql_window

    class Cursor:
        def execute(self):
            return None

    cursor = Cursor()
    with observe_sql_window(owners={Cursor.execute.__code__: 'execute'},
                            roots=[Path(__file__).resolve().parents[2]], endpoints={}) as state:
        cursor.execute()
        token = probe._witness_sql.set(True)
        try:
            cursor.execute()
        finally:
            probe._witness_sql.reset(token)
        cursor.execute()
    assert state['started'] == state['returned'] == 2
    assert state['resumed_unknown'] == 0


def test_artifact_never_infers_complete_or_accepts_invalid_counts():
    row = {'schema': 'dmb_negative_retrieval_core_connection_v1', 'case_id': 'example',
           'window': 'turn_post_v1', 'coverage': 'partial', 'status': 'observed',
           'connections': {'scoped': 0, 'unscoped': 0},
           'transactions': {'scoped': 0, 'unscoped': 0},
           'verified': {'scoped': 0, 'unscoped': 0}, 'mismatches': 0, 'errors': 0,
           'pending_at_close': 0, 'owner_source_sha256': 'a' * 64}
    assert probe.validate_artifact(row, 'example')['coverage'] == 'partial'
    for change in ({'case_id': 'other'}, {'coverage': 'complete'}, {'errors': 1},
                   {'verified': {'scoped': 1, 'unscoped': 0}}, {'extra': True}):
        with pytest.raises(ValueError):
            probe.validate_artifact(row | change, 'example')


def test_tampered_hook_poisoned_and_original_error_preserved(owners, monkeypatch):
    database, _, _, _, _ = owners
    monkeypatch.setattr(probe, '_poisoned', False)
    with pytest.raises(ValueError, match='original failure') as error:
        with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]):
            monkeypatch.setattr(database, 'connect', lambda self: None)
            raise ValueError('original failure')
    assert any('could not be restored' in note for note in error.value.__notes__)
    with pytest.raises(RuntimeError, match='fresh process'):
        with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]):
            pass


def test_capture_retains_unavailable_witness_if_setup_fails(tmp_path, monkeypatch):
    import json
    from hashlib import sha256
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module

    @contextmanager
    def failed_setup(*args, **kwargs):
        raise OSError('Core connection preflight failed')
        yield

    class Client:
        def post(self, *args, **kwargs):
            pytest.fail('A failed preflight must not dispatch')

    manifest = tmp_path / 'manifest.json'
    manifest.write_text('{}')
    out = tmp_path / 'capture'
    monkeypatch.setenv('DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL', 'unused')
    monkeypatch.setattr(module, 'checked_owned_dsn', lambda: 'unused')
    monkeypatch.setattr(module, 'observe_core_connections', failed_setup)
    monkeypatch.setattr(workflow, 'load_manifest', lambda *args, **kwargs:
                        ({'conversation_mode': 'build_sequence', 'isolation': {'native': {}}}, tmp_path))
    monkeypatch.setattr(workflow, 'capture_case', lambda client, *args, **kwargs:
                        client.post('/api/live/agent/turn'))
    monkeypatch.setattr(workflow, 'capture', lambda manifest, output, *, cohort_manifest_sha256, clone_app=False:
                        workflow.capture_case(Client(), 'world', {}, {'id': 'case1'}, output))
    with pytest.raises(OSError, match='preflight failed'):
        module.capture(manifest, out, expected_manifest_sha256=sha256(manifest.read_bytes()).hexdigest(),
                       observe_core=True)
    row = json.loads((out / 'core-connection-probe.json').read_bytes())
    assert probe.validate_artifact(row, 'case1')['status'] == 'unavailable'
