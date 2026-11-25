import json
import hashlib

from application_state.index_graph import guest_apprentice_plan as seed


class Cursor:
    def __init__(self, rows): self.rows = rows
    def fetchall(self): return self.rows


class Connection:
    def __init__(self, bundle): self.values = {'guest_document_seed': json.dumps({'bundle_sha256': bundle})}; self.writes = []
    def execute(self, sql, args):
        if sql.startswith('SELECT'):
            return Cursor(list(self.values.items()))
        self.writes.append(args)
        self.values[args[1]] = args[2]
        return Cursor([])


def test_plan_seed_is_transactional_per_world_and_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAN_ENABLED', '1')
    bundle = tmp_path / 'bundle.json'
    bundle.write_text(json.dumps({'documents': [{'title': "Sizzek's Apprentice", 'markdown': 'source'}]}))
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE', str(bundle))
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', digest)
    monkeypatch.setattr(seed, '_SOURCE_SHA256', hashlib.sha256(b'source').hexdigest())
    created, committed = [], []
    monkeypatch.setattr(seed.repository, 'insert_work_object', lambda conn, obj: created.append(obj))
    monkeypatch.setattr(seed.service, '_commit_in_connection', lambda *args, **kwargs: committed.append((args, kwargs)))
    first, other = Connection(digest), Connection(digest)
    for _ in range(2): seed.seed_guest_apprentice_plan(first, session_id='one', world_id='guest-one')
    seed.seed_guest_apprentice_plan(other, session_id='two', world_id='guest-two')
    assert len(created) == len(committed) == 2
    assert created[0].world_id == 'guest-one' and created[1].world_id == 'guest-two'
    assert created[0].work_object_id != created[1].work_object_id
    assert 'scene:trap-room' in committed[0][0][2]
    assert len(first.writes) == len(other.writes) == 1


def test_other_bundle_and_disabled_plan_do_not_seed(monkeypatch, tmp_path):
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAN_ENABLED', '1')
    bundle = tmp_path / 'bundle.json'
    bundle.write_text(json.dumps({'documents': [{'title': "Sizzek's Apprentice", 'markdown': 'source'}]}))
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE', str(bundle))
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', digest)
    monkeypatch.setattr(seed, '_SOURCE_SHA256', hashlib.sha256(b'source').hexdigest())
    other = Connection('different')
    seed.seed_guest_apprentice_plan(other, session_id='one', world_id='guest-one')
    assert not other.writes
    monkeypatch.setattr(seed, '_SOURCE_SHA256', '0' * 64)
    mismatch = Connection(digest)
    seed.seed_guest_apprentice_plan(mismatch, session_id='one', world_id='guest-one')
    assert not mismatch.writes
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAN_ENABLED', '0')
    seed.seed_guest_apprentice_plan(Connection(digest), session_id='one', world_id='guest-one')


def test_prepared_plan_has_playable_scenes_and_confrontation_choice():
    from apps.live_control_server.services.play_run_edition_structure import structure_signature
    markdown = seed.Path(seed.__file__).with_name('sizzek_apprentice_plan.md').read_text(encoding='utf-8')
    structure = structure_signature(markdown)
    scenes = {scene['scene_id'] for scene in structure['membership']['scenes']}
    assert {'scene:contract', 'scene:mirrors', 'scene:trap-room', 'scene:return'} <= scenes
    assert 'choice:confrontation' in markdown
    assert 'six skeletons' in markdown and 'five feet each round' in markdown


def test_malformed_duplicate_and_tampered_bundles_do_not_seed(monkeypatch, tmp_path):
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAN_ENABLED', '1')
    monkeypatch.setattr(seed, '_SOURCE_SHA256', hashlib.sha256(b'source').hexdigest())
    bundle = tmp_path / 'bundle.json'
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE', str(bundle))
    for raw, tamper in [(b'{', False), (json.dumps({'documents': [{'title': "Sizzek's Apprentice", 'markdown': 'source'}] * 2}).encode(), False), (b'{}', True)]:
        bundle.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', digest)
        if tamper: bundle.write_bytes(b'changed')
        conn = Connection(digest)
        seed.seed_guest_apprentice_plan(conn, session_id='one', world_id='guest-one')
        assert not conn.writes
