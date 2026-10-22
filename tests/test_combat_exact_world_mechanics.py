"""Exact snapshot admission through real HTTP and APP; only external IO mocked."""
import copy
from uuid import uuid4
from types import SimpleNamespace
import pytest
from tests.test_world_mechanics_associations import prepared, post
from application_state.world_mechanics import service as associations
from application_state.world_mechanics.types import AssociateWorldMechanicsRequest
from application_state.combat_encounters import service as state
from application_state.combat_encounters.types import CombatMechanicsSnapshot, SaveCombatEncounterRequest
from application_state.errors import ApplicationStateValidationError, ApplicationStateConflictError
from apps.live_control_server.services import combat_mechanics
from apps.live_control_server.services import managed_world_graph_projection as graph


@pytest.fixture
def combat(prepared,monkeypatch):
    p=prepared
    assert post(p).status_code==200
    record=associations.list_current(world_id='elderwyld')[0]
    monkeypatch.setattr(combat_mechanics,'project_managed_world_graph',lambda request:p.view)
    monkeypatch.setattr(combat_mechanics,'resolve_managed_world_binding',lambda world:p.binding)
    monkeypatch.setattr(combat_mechanics,'build_statblock_v1_client',lambda:p.dms)
    p.graph_reads=[]
    monkeypatch.setattr(graph,'project_managed_world_graph',lambda request:(p.graph_reads.append(request) or p.view))
    from apps.live_control_server.routes import combat_encounters as route
    monkeypatch.setattr(route,'resolve_managed_world_binding',lambda world,**kwargs:SimpleNamespace(managed_world_id=world))
    p.selection=dict(association_id=str(record.association_id),association_version=record.version,target=p.body['target'])
    p.record=record
    p.encounter=p.client.post('/api/live/combat/encounters?world_id=elderwyld',json={'title':'Snapshot rehearsal'}).json()
    p.url=f"/api/live/combat/encounters/{p.encounter['encounter_id']}?world_id=elderwyld"
    return p


def preview(p):
    return p.client.post('/api/live/combat/encounters/world-mechanics/preview?world_id=elderwyld',json=p.selection)


def body(p,snapshot,count=2):
    draft=copy.deepcopy(p.encounter['draft'])
    draft['entities']=[dict(id=str(uuid4()),name=f'Keeper {i}',order=i+1,world_identity=p.body['target'],mechanics_snapshot=snapshot) for i in range(count)]
    return dict(expected_revision=p.encounter['revision'],draft=draft)


def replace(p):
    request=AssociateWorldMechanicsRequest.model_validate({**p.body,'request_id':str(uuid4()),'expected_version':1})
    return associations.append_verified(request=request,proof=p.record.proof,actor='gm')


def test_preview_save_copies_offline_reopen_and_independent_tracking(combat,monkeypatch):
    p=combat;r=preview(p);assert r.status_code==200,r.text
    assert associations.list_current(world_id='elderwyld')==[p.record]
    request=body(p,r.json());p.dms.calls=0;p.graph_reads.clear()
    saved=p.client.put(p.url,json=request);assert saved.status_code==200,saved.text
    data=saved.json();assert p.dms.calls==1;assert len(p.graph_reads)==1
    assert data['draft']['entities'][0]['mechanics_snapshot']==data['draft']['entities'][1]['mechanics_snapshot']==r.json()
    assert all(e['hp'] is None and e['ac'] is None for e in data['draft']['entities'])
    replace(p)
    monkeypatch.setattr(combat_mechanics,'build_statblock_v1_client',lambda:pytest.fail('Offline saved actor must not read DMS'))
    monkeypatch.setattr(graph,'project_managed_world_graph',lambda request:pytest.fail('Offline saved actor must not read Graph'))
    reopened=p.client.get(p.url);assert reopened.status_code==200
    draft=reopened.json()['draft'];draft['entities'][0].update(hp=7,temp_hp=2,conditions=['Prone'],notes='Independent')
    updated=p.client.put(p.url,json={'expected_revision':data['revision'],'draft':draft});assert updated.status_code==200,updated.text
    assert updated.json()['draft']['entities'][1]['hp'] is None
    assert updated.json()['draft']['entities'][0]['mechanics_snapshot']==r.json()


@pytest.mark.parametrize('change',['head','mapping','missing','label','slot'])
def test_stale_preview_refuses_save_without_writing_any_actor(combat,change):
    p=combat;r=preview(p);assert r.status_code==200
    if change=='head':p.view.projection.snapshot.revision_id='rev:unrelated'
    elif change=='mapping':p.binding.binding_version+=1
    elif change=='missing':p.view.projection.nodes=[]
    elif change=='label':p.view.projection.nodes[0].label='Changed'
    else:replace(p)
    refused=p.client.put(p.url,json=body(p,r.json()));assert refused.status_code in (409,422),refused.text
    assert p.client.get(p.url).json()['draft']['entities']==[]


def test_full_resource_tamper_even_with_recomputed_snapshot_digest_refuses(combat):
    p=combat;r=preview(p);snapshot=r.json();snapshot['resource']['provenance']={'forged':'metadata'}
    snapshot['snapshot_digest']=CombatMechanicsSnapshot.digest_payload({k:v for k,v in snapshot.items() if k!='snapshot_digest'})
    refused=p.client.put(p.url,json=body(p,snapshot));assert refused.status_code==422,refused.text
    assert p.client.get(p.url).json()['revision']==1


def test_existing_snapshot_cannot_be_removed_or_replaced(combat):
    p=combat;r=preview(p);saved=p.client.put(p.url,json=body(p,r.json()));data=saved.json()
    draft=data['draft'];draft['entities'][0]['mechanics_snapshot']=None
    refused=p.client.put(p.url,json={'expected_revision':data['revision'],'draft':draft});assert refused.status_code==422


def test_app_rechecks_slot_after_external_verification(combat,monkeypatch):
    p=combat;snapshot=CombatMechanicsSnapshot.model_validate(preview(p).json());request=SaveCombatEncounterRequest.model_validate(body(p,snapshot.model_dump(mode='json')))
    replace(p)
    with pytest.raises(ApplicationStateConflictError):
        state.save_encounter(world_id='elderwyld',encounter_id=p.encounter['encounter_id'],request=request,
            verified_world_identities={e.id:e.world_identity for e in request.draft.entities},
            verified_mechanics_snapshots={e.id:snapshot for e in request.draft.entities})
    assert state.get_encounter(world_id='elderwyld',encounter_id=p.encounter['encounter_id']).revision==1


def test_direct_app_snapshot_injection_refused(combat):
    p=combat;request=SaveCombatEncounterRequest.model_validate(body(p,preview(p).json()))
    with pytest.raises(ApplicationStateValidationError):
        state.save_encounter(world_id='elderwyld',encounter_id=p.encounter['encounter_id'],request=request,
            verified_world_identities={e.id:e.world_identity for e in request.draft.entities})


def test_differing_snapshots_for_one_id_refuse_whole_save(combat):
    p=combat;request=body(p,preview(p).json());bad=request['draft']['entities'][1]['mechanics_snapshot']=copy.deepcopy(request['draft']['entities'][1]['mechanics_snapshot'])
    bad['resource']['provenance']={'forged':'second copy'};bad['snapshot_digest']=CombatMechanicsSnapshot.digest_payload({k:v for k,v in bad.items() if k!='snapshot_digest'})
    r=p.client.put(p.url,json=request);assert r.status_code==422,r.text
    assert p.client.get(p.url).json()['draft']['entities']==[]


def test_one_stale_slot_among_two_refuses_all_new_actors(combat):
    p=combat;first=preview(p).json()
    target={**p.body['target'],'node_id':'node:other','label':'Other Keeper'}
    request=AssociateWorldMechanicsRequest.model_validate({**p.body,'request_id':str(uuid4()),'target':target})
    second_record=associations.append_verified(request=request,proof=p.record.proof,actor='gm').association
    p.view.projection.nodes.append(SimpleNamespace(node_id=target['node_id'],label=target['label'],kind='npc',role='',campaign_scope=None))
    p.selection={'association_id':str(second_record.association_id),'association_version':1,'target':target}
    second=preview(p).json();request_body=body(p,first)
    request_body['draft']['entities'][1].update(world_identity=target,mechanics_snapshot=second)
    replaced=AssociateWorldMechanicsRequest.model_validate({**request.model_dump(mode='json'),'request_id':str(uuid4()),'expected_version':1})
    associations.append_verified(request=replaced,proof=p.record.proof,actor='gm')
    refused=p.client.put(p.url,json=request_body);assert refused.status_code==409,refused.text
    assert p.client.get(p.url).json()['draft']['entities']==[]


def test_unavailable_exact_mechanics_never_falls_back_or_writes(combat,monkeypatch):
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import downstream_unavailable
    p=combat;snapshot=preview(p).json()
    def unavailable(*args):raise downstream_unavailable('DMS offline')
    monkeypatch.setattr(p.dms,'get_exact_revision',unavailable)
    assert preview(p).status_code==503
    r=p.client.put(p.url,json=body(p,snapshot));assert r.status_code==503,r.text
    assert p.client.get(p.url).json()['revision']==1


@pytest.mark.parametrize('change',['canonical','definition','locator','receipt','digest'])
def test_snapshot_local_integrity_refuses_corruption(combat,change):
    from pydantic import ValidationError
    p=combat;snapshot=preview(p).json()
    if change=='canonical':snapshot['resource']['canonical_definition']+=' '
    elif change=='definition':snapshot['resource']['definition']['identity']['name']='Tampered'
    elif change=='locator':snapshot['locator']['revision_id']='rev_wrong'
    elif change=='receipt':snapshot['resource']['validation_receipt']['definition_digest']='sha256:'+'f'*64
    else:snapshot['snapshot_digest']='sha256:'+'f'*64
    if change!='digest':snapshot['snapshot_digest']=CombatMechanicsSnapshot.digest_payload({k:v for k,v in snapshot.items() if k!='snapshot_digest'})
    with pytest.raises(ValidationError):CombatMechanicsSnapshot.model_validate(snapshot)
