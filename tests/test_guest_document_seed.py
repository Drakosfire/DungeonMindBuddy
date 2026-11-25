import json
import hashlib

import pytest

from application_state.errors import ApplicationStateUnavailableError
from application_state.index_graph import guest_documents as seed


class Cursor:
    def __init__(self, value):
        self.value = value

    def fetchone(self):
        return self.value


class Connection:
    def __init__(self, snapshot, marker=None):
        self.snapshot, self.marker, self.insertions = snapshot, marker, []

    def execute(self, query, args):
        if query.startswith('INSERT'):
            self.insertions.append(args)
            self.marker = (args[2],)
            return Cursor(None)
        if query.startswith('SELECT count'):
            return Cursor((0, 0) if 'coalesce' in query else (0,))
        return Cursor(self.snapshot if "key = 'source_snapshot'" in query else self.marker)


def bundle(tmp_path, monkeypatch, *, revision='r1'):
    path = tmp_path / 'release.json'
    path.write_text(json.dumps({'version': 1, 'graph_space': 'space', 'graph_revision': revision,
                                'documents': [{'title': 'Apprentice', 'markdown': 'original'}]}))
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE', str(path))
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
    return path


def test_seed_once_and_retry_preserves_guest_edits(tmp_path, monkeypatch):
    bundle(tmp_path, monkeypatch)
    conn = Connection((json.dumps({'space_id': 'space', 'revision_id': 'r1'}),))
    created, committed = [], []
    monkeypatch.setattr(seed.pages, '_insert_page', lambda *args: created.append(args))
    monkeypatch.setattr(seed.content, '_commit_in_connection', lambda *args, **kwargs: committed.append((args, kwargs)))
    seed.seed_guest_documents(conn, session_id='00000000-0000-0000-0000-000000000001', world_id='guest-one')
    seed.seed_guest_documents(conn, session_id='00000000-0000-0000-0000-000000000001', world_id='guest-one')
    assert len(created) == len(committed) == len(conn.insertions) == 1
    assert created[0][2:5] == ('guest-one', 'Apprentice', 'guest-one')
    assert created[0][5].document_class == 'lore'
    assert committed[0][0][2] == 'original'
    receipt = json.loads(conn.insertions[0][2])
    assert receipt['entries'] == [{'ordinal': 0, 'document_id': str(created[0][1])}]


def test_rejects_bundle_from_other_graph_without_writes(tmp_path, monkeypatch):
    bundle(tmp_path, monkeypatch, revision='other')
    conn = Connection((json.dumps({'space_id': 'space', 'revision_id': 'r1'}),))
    with pytest.raises(ApplicationStateUnavailableError):
        seed.seed_guest_documents(conn, session_id='00000000-0000-0000-0000-000000000001', world_id='guest-one')
    assert conn.insertions == []


def test_rejects_changed_bundle_without_writes(tmp_path, monkeypatch):
    path = bundle(tmp_path, monkeypatch)
    path.write_text(path.read_text() + ' ')
    conn = Connection((json.dumps({'space_id': 'space', 'revision_id': 'r1'}),))
    with pytest.raises(ApplicationStateUnavailableError):
        seed.seed_guest_documents(conn, session_id='00000000-0000-0000-0000-000000000001', world_id='guest-one')
    assert conn.insertions == []


def test_existing_seed_repairs_only_missing_classes_in_its_world(tmp_path, monkeypatch):
    bundle(tmp_path, monkeypatch)
    receipt = {'entries': [{'ordinal': 0, 'document_id': '11111111-1111-4111-8111-111111111111'}]}
    class RepairConnection(Connection):
        def __init__(self):
            super().__init__(None, (json.dumps(receipt),))
            self.updates = []
        def execute(self, query, args):
            if query.startswith('UPDATE'):
                self.updates.append((query, args))
                return Cursor(None)
            return super().execute(query, args)
    conn = RepairConnection()
    seed.seed_guest_documents(conn, session_id='00000000-0000-0000-0000-000000000001', world_id='guest-one')
    assert len(conn.updates) == 1
    query, args = conn.updates[0]
    assert 'm.document_class IS NULL' in query and "w.kind = 'worldbuilding_source'" in query
    assert args[0] == 'guest-one' and str(args[1][0]) == receipt['entries'][0]['document_id']


def test_invalid_seed_receipt_does_not_repair(tmp_path, monkeypatch):
    bundle(tmp_path, monkeypatch)
    conn = Connection(None, (json.dumps({'entries': [{'document_id': 'not-a-uuid'}]}),))
    with pytest.raises(ApplicationStateUnavailableError, match='receipt'):
        seed.seed_guest_documents(conn, session_id='00000000-0000-0000-0000-000000000001', world_id='guest-one')
