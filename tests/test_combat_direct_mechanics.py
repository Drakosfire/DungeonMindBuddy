"""Direct accepted mechanics through real journals, HTTP and APP persistence."""
import copy
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from tests.test_world_mechanics_associations import prepared
from application_state.combat_encounters import service as state
from application_state.combat_encounters.types import AcceptedCombatMechanicsSnapshot, SaveCombatEncounterRequest
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services import combat_mechanics as mechanics
from apps.live_control_server.services import managed_world_graph_projection as graph


@pytest.fixture
def direct(prepared, monkeypatch):
    p = prepared
    monkeypatch.setattr(mechanics, 'build_statblock_v1_client', lambda: p.dms)
    from apps.live_control_server.routes import combat_encounters as routes
    monkeypatch.setattr(routes, 'resolve_managed_world_binding', lambda world, **kw: SimpleNamespace(managed_world_id=world))
    monkeypatch.setattr(graph, 'project_managed_world_graph', lambda request: pytest.fail('Direct mechanics must not read Graph'))
    p.selection = {'draft_id': p.draft.draft_id, 'draft_version': p.draft.version}
    p.preview_url = '/api/live/combat/encounters/accepted-mechanics/preview?world_id=elderwyld'
    p.encounter = p.client.post('/api/live/combat/encounters?world_id=elderwyld', json={'title': 'Direct mechanics'}).json()
    p.url = f"/api/live/combat/encounters/{p.encounter['encounter_id']}?world_id=elderwyld"
    return p


def preview(p):
    response = p.client.post(p.preview_url, json=p.selection)
    assert response.status_code == 200, response.text
    return response.json()


def body(p, snapshot, count=2):
    draft = copy.deepcopy(p.encounter['draft'])
    draft['entities'] = [dict(id=str(uuid4()), name=f'Creature {i}', order=i+1, mechanics_snapshot=snapshot) for i in range(count)]
    return {'expected_revision': p.encounter['revision'], 'draft': draft}


def test_direct_no_node_copies_save_offline_reopen_and_independent_tracker(direct, monkeypatch):
    p = direct; snapshot = preview(p)
    assert snapshot['origin'] == 'world_accepted_mechanics_v1'
    assert 'target' not in snapshot and 'association_id' not in snapshot
    p.dms.calls = 0
    read = mechanics.list_acceptance_operations_for_draft
    reads = []
    monkeypatch.setattr(mechanics, 'list_acceptance_operations_for_draft', lambda *a, **kw: (reads.append(kw) or read(*a, **kw)))
    saved = p.client.put(p.url, json=body(p, snapshot))
    assert saved.status_code == 200, saved.text
    assert p.dms.calls == 1 and len(reads) == 1
    data = saved.json()
    assert all(e['world_identity'] is None and e['hp'] is None for e in data['draft']['entities'])
    assert all(e['mechanics_snapshot'] == snapshot for e in data['draft']['entities'])
    monkeypatch.setattr(mechanics, 'get_threat_draft', lambda *a: pytest.fail('Saved actor must reopen offline'))
    monkeypatch.setattr(mechanics, 'build_statblock_v1_client', lambda: pytest.fail('Saved actor must not resolve current DMS'))
    reopened = p.client.get(p.url); assert reopened.status_code == 200
    draft = reopened.json()['draft']; draft['entities'][0].update(hp=7, max_hp=15, conditions=['Prone'], notes='Independent')
    updated = p.client.put(p.url, json={'expected_revision': data['revision'], 'draft': draft})
    assert updated.status_code == 200, updated.text
    assert updated.json()['draft']['entities'][1]['hp'] is None
    assert updated.json()['draft']['entities'][0]['mechanics_snapshot'] == snapshot


@pytest.mark.parametrize('change', ['foreign', 'version', 'missing', 'duplicate', 'unattached', 'unreconciled', 'candidate', 'request', 'locator'])
def test_bad_acceptance_refuses_preview_and_whole_save(direct, monkeypatch, change):
    p = direct; snapshot = preview(p); read = mechanics.list_acceptance_operations_for_draft
    operations = read(p.root, draft_id=p.draft.draft_id)
    if change == 'foreign':
        original = mechanics.get_threat_draft
        monkeypatch.setattr(mechanics, 'get_threat_draft', lambda *a: original(*a).model_copy(update={'world_id': 'foreign'}))
    elif change == 'version': p.selection['draft_version'] += 1
    else:
        altered = copy.deepcopy(operations)
        if change == 'missing': altered = []
        elif change == 'duplicate': altered += copy.deepcopy(altered)
        elif change == 'unattached': altered[0].materialization.draft_ref = 'pending'
        elif change == 'unreconciled': altered[0].authority_state = 'unknown'
        elif change == 'candidate': altered[0].source_candidate_id = 'cand_other'
        elif change == 'request': altered[0].request_body['definition']['identity']['name'] = 'Forged'
        elif change == 'locator': altered[0].locator = altered[0].locator.model_copy(update={'revision_id': 'rev_other'})
        monkeypatch.setattr(mechanics, 'list_acceptance_operations_for_draft', lambda *a, **kw: altered)
    assert p.client.post(p.preview_url, json=p.selection).status_code in (409, 500)
    if change == 'version': snapshot['draft_version'] += 1; redigest(snapshot)
    refused = p.client.put(p.url, json=body(p, snapshot))
    assert refused.status_code in (409, 500), refused.text
    assert p.client.get(p.url).json()['revision'] == 1


def redigest(snapshot):
    snapshot['snapshot_digest'] = AcceptedCombatMechanicsSnapshot.digest_payload({k:v for k,v in snapshot.items() if k != 'snapshot_digest'})


@pytest.mark.parametrize('change', ['resource', 'operation', 'world', 'receipt', 'canonical', 'snapshot'])
def test_forged_snapshot_cannot_enter_app(direct, change):
    p = direct; snapshot = preview(p)
    if change == 'resource': snapshot['resource']['provenance'] = {'forged': True}
    elif change == 'operation': snapshot['acceptance_operation_id'] = str(uuid4())
    elif change == 'world': snapshot['managed_world_id'] = 'foreign'
    elif change == 'receipt': snapshot['resource']['validation_receipt']['definition_digest'] = 'sha256:'+'f'*64
    elif change == 'canonical': snapshot['resource']['canonical_definition'] += ' '
    else: snapshot['snapshot_digest'] = 'sha256:'+'f'*64
    if change != 'snapshot': redigest(snapshot)
    refused = p.client.put(p.url, json=body(p, snapshot))
    assert refused.status_code == 422, refused.text
    assert p.client.get(p.url).json()['revision'] == 1


def test_app_injection_and_saved_snapshot_change_refused(direct):
    p = direct; snapshot = preview(p); request = SaveCombatEncounterRequest.model_validate(body(p, snapshot))
    with pytest.raises(ApplicationStateValidationError):
        state.save_encounter(world_id='elderwyld', encounter_id=p.encounter['encounter_id'], request=request)
    saved = p.client.put(p.url, json=body(p, snapshot)).json()
    saved['draft']['entities'][0]['mechanics_snapshot'] = None
    refused = p.client.put(p.url, json={'expected_revision': saved['revision'], 'draft': saved['draft']})
    assert refused.status_code == 422


def test_final_draft_recheck_and_exact_provider_failure_leave_no_actor(direct, monkeypatch):
    p = direct; snapshot = preview(p); locked = mechanics.locked_threat_drafts
    @contextmanager
    def changed(*a):
        with locked(*a) as drafts: yield {key:draft.model_copy(update={'version': draft.version+1}) for key,draft in drafts.items()}
    monkeypatch.setattr(mechanics, 'locked_threat_drafts', changed)
    assert p.client.put(p.url, json=body(p, snapshot)).status_code == 409
    monkeypatch.setattr(mechanics, 'locked_threat_drafts', locked)
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import downstream_unavailable
    def fail(*a): raise downstream_unavailable('offline')
    monkeypatch.setattr(p.dms, 'get_exact_revision', fail)
    assert p.client.put(p.url, json=body(p, snapshot)).status_code == 503
    assert p.client.get(p.url).json()['revision'] == 1


def test_optional_world_identity_is_independently_verified(direct, monkeypatch):
    p = direct; snapshot = preview(p); reads = []
    monkeypatch.setattr(graph, 'project_managed_world_graph', lambda request: (reads.append(request) or p.view))
    request = body(p, snapshot, 1); request['draft']['entities'][0]['world_identity'] = p.body['target']
    saved = p.client.put(p.url, json=request)
    assert saved.status_code == 200, saved.text
    assert len(reads) == 1
    assert saved.json()['draft']['entities'][0]['world_identity'] == p.body['target']


def test_stale_encounter_cas_refuses_before_new_provider_reads(direct):
    p = direct; snapshot = preview(p)
    saved = p.client.put(p.url, json={'expected_revision':1, 'draft':p.encounter['draft']})
    assert saved.status_code == 200
    p.dms.calls = 0
    assert p.client.put(p.url, json=body(p, snapshot)).status_code == 409
    assert p.dms.calls == 0
    assert p.client.get(p.url).json()['draft']['entities'] == []


@pytest.mark.parametrize('change', ['missing', 'foreign'])
def test_optional_identity_failure_refuses_direct_snapshot_as_well(direct, monkeypatch, change):
    p = direct; request = body(p, preview(p), 1)
    identity = copy.deepcopy(p.body['target'])
    if change == 'foreign': identity['managed_world_id'] = 'foreign'
    else: identity['node_id'] = 'node:missing'
    monkeypatch.setattr(graph, 'project_managed_world_graph', lambda request:p.view)
    request['draft']['entities'][0]['world_identity'] = identity
    response = p.client.put(p.url, json=request)
    assert response.status_code == 422, response.text
    assert p.client.get(p.url).json()['revision'] == 1


def test_distinct_assets_use_one_final_store_lock_with_no_external_io(direct, monkeypatch):
    from apps.live_control_server.services import threat_draft_store as store
    from apps.live_control_server.models.threat_draft import CreateWorldThreatDraftRequest, ThreatDraftCandidateRefV1
    from apps.live_control_server.models.statblock_mechanics_acceptance import AcceptThreatDraftMechanicsRequestV1
    from apps.live_control_server.services.statblock_mechanics_acceptance import begin_or_resume_acceptance
    p = direct
    second = store.create_threat_draft(p.root, CreateWorldThreatDraftRequest(
        scope_mode='world', world_id='elderwyld', campaign_id=None, name='Second asset', description='Synthetic', threat_kind='creature',
        generation_intent={'ruleset':{'system':'dnd5e','edition':'2024'}}, graph_context_snapshot={'graph_revision_id':'rev:head'}, created_by='gm'))
    store.append_candidate_ref(p.root, draft_id=second.draft_id, expected_version=1, candidate_ref=ThreatDraftCandidateRefV1(
        candidate_id='cand_fixture2', generated_from_draft_version=1, request_id='generate2', created_at='2026-10-22T00:00:00Z'))
    begin_or_resume_acceptance(p.root, draft_id=second.draft_id, client=p.dms, request=AcceptThreatDraftMechanicsRequestV1(
        operation_id=str(uuid4()), expected_draft_version=1, definition=p.revision.definition.model_dump(mode='json'),
        validation_receipt=p.revision.validation_receipt, validation_definition_digest=p.revision.definition_digest,
        source_candidate_id='cand_fixture2', change_summary='Synthetic acceptance', actor='gm'))
    first = preview(p); p.selection = {'draft_id':second.draft_id,'draft_version':2}; second_snapshot = preview(p)
    request = body(p, first); request['draft']['entities'][1]['mechanics_snapshot'] = second_snapshot
    original_lock = store._store_lock; depth = 0; final_batches = []
    @contextmanager
    def checked_lock(root):
        nonlocal depth
        assert depth == 0, 'Store-wide file lock must not be nested'
        with original_lock(root):
            depth += 1
            try: yield
            finally: depth -= 1
    monkeypatch.setattr(store, '_store_lock', checked_lock)
    exact_read = p.dms.get_exact_revision
    def checked_read(*args):
        assert depth == 0, 'Provider IO must finish before the store lock'
        return exact_read(*args)
    monkeypatch.setattr(p.dms, 'get_exact_revision', checked_read)
    app_save = state.save_encounter
    def checked_save(**kwargs):
        assert depth == 1, 'Final draft CAS must stay locked through APP Save'
        final_batches.append(kwargs)
        return app_save(**kwargs)
    monkeypatch.setattr(state, 'save_encounter', checked_save)
    saved = p.client.put(p.url, json=request)
    assert saved.status_code == 200, saved.text
    assert len(final_batches) == 1
    assert len({e['mechanics_snapshot']['draft_id'] for e in saved.json()['draft']['entities']}) == 2
