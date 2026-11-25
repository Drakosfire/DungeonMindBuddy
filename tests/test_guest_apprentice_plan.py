import json

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


def test_plan_seed_is_transactional_per_world_and_idempotent(monkeypatch):
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAN_ENABLED', '1')
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', seed._BUNDLE_SHA256)
    created, committed = [], []
    monkeypatch.setattr(seed.repository, 'insert_work_object', lambda conn, obj: created.append(obj))
    monkeypatch.setattr(seed.service, '_commit_in_connection', lambda *args, **kwargs: committed.append((args, kwargs)))
    first, other = Connection(seed._BUNDLE_SHA256), Connection(seed._BUNDLE_SHA256)
    for _ in range(2): seed.seed_guest_apprentice_plan(first, session_id='one', world_id='guest-one')
    seed.seed_guest_apprentice_plan(other, session_id='two', world_id='guest-two')
    assert len(created) == len(committed) == 2
    assert created[0].world_id == 'guest-one' and created[1].world_id == 'guest-two'
    assert created[0].work_object_id != created[1].work_object_id
    assert 'scene:trap-room' in committed[0][0][2]
    assert len(first.writes) == len(other.writes) == 1


def test_other_bundle_and_disabled_plan_do_not_seed(monkeypatch):
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAN_ENABLED', '1')
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', seed._BUNDLE_SHA256)
    other = Connection('different')
    seed.seed_guest_apprentice_plan(other, session_id='one', world_id='guest-one')
    assert not other.writes
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAN_ENABLED', '0')
    seed.seed_guest_apprentice_plan(Connection(seed._BUNDLE_SHA256), session_id='one', world_id='guest-one')


def test_prepared_plan_has_playable_scenes_and_confrontation_choice():
    from apps.live_control_server.services.play_run_edition_structure import structure_signature
    markdown = seed.Path(seed.__file__).with_name('sizzek_apprentice_plan.md').read_text(encoding='utf-8')
    structure = structure_signature(markdown)
    scenes = {scene['scene_id'] for scene in structure['membership']['scenes']}
    assert {'scene:contract', 'scene:mirrors', 'scene:trap-room', 'scene:return'} <= scenes
    assert 'choice:confrontation' in markdown
    assert 'six skeletons' in markdown and 'five feet each round' in markdown
