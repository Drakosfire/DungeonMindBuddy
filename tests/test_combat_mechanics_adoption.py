"""Real HTTP/APP transactions and immutable journals; synthetic producer boundary."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier,Event
from types import SimpleNamespace
from uuid import uuid4
import pytest
from tests.test_world_mechanics_associations import prepared
from tests.test_statblock_saved_revisions import revision_case
from apps.live_control_server.services import combat_mechanics as mechanics


@pytest.fixture
def adoption_case(revision_case,monkeypatch):
    p=revision_case
    from apps.live_control_server.routes import combat_encounters as routes
    monkeypatch.setattr(routes,'resolve_managed_world_binding',lambda world,**kw:SimpleNamespace(managed_world_id=world))
    monkeypatch.setattr(mechanics,'build_statblock_v1_client',lambda:p.manual)
    original=p.client.post('/api/live/combat/encounters/accepted-mechanics/preview?world_id=elderwyld',
        json={'draft_id':p.draft.draft_id,'draft_version':p.draft.version})
    assert original.status_code==200,original.text
    p.original=original.json()
    p.request['definition']['defenses']['armor_classes'][0]['value']=20
    p.request['definition']['vitality']['hit_points']={'method':'fixed','fixed_value':28,'formula':None,'displayed_average':28}
    saved=p.client.post(p.url,json=p.request);assert saved.status_code==200,saved.text
    p.locator=saved.json()['result']
    created=p.client.post('/api/live/combat/encounters?world_id=elderwyld',json={'title':'Exact actor override'})
    assert created.status_code==200,created.text
    p.encounter=created.json();draft=deepcopy(p.encounter['draft'])
    draft.update(round=3,active_turn_entity_id='actor-a',round_start_entity_id='actor-a')
    draft['entities']=[dict(id='actor-'+suffix,name='Keeper '+suffix,order=i+1,init=17-i,ac=12,hp=35,max_hp=40,temp_hp=7,
        conditions=['Prone'],notes='Retained tracker note',mechanics_snapshot=p.original,defeated=i==1) for i,suffix in enumerate(['a','b'])]
    draft['groups']=[{'group_key':'keepers','label':'Keepers','statblock_path':None,'member_ids':['actor-a','actor-b'],'collapsed':True}]
    p.encounter_url=f"/api/live/combat/encounters/{p.encounter['encounter_id']}?world_id=elderwyld"
    result=p.client.put(p.encounter_url,json={'expected_revision':1,'draft':draft});assert result.status_code==200,result.text
    p.before=result.json()
    p.adopt_url=f"/api/live/combat/encounters/{p.encounter['encounter_id']}/mechanics-adoptions?world_id=elderwyld"
    p.cancel_url=p.adopt_url.replace('mechanics-adoptions?','mechanics-adoptions:cancel?')
    p.intent=dict(schema='dmb_combat_mechanics_adoption_request_v1',operation_id=str(uuid4()),expected_revision=2,draft_id=p.draft.draft_id,
        locator=p.locator,actors=[dict(actor_id='actor-a',expected_snapshot_digest=p.original['snapshot_digest'],ac_policy='keep',hp_policy='keep')])
    return p


def apply(p,body=None):return p.client.post(p.adopt_url,json=body or p.intent)


def test_selected_subset_exact_reopen_generic_guard_and_offline_replay(adoption_case,monkeypatch):
    p=adoption_case;r=apply(p);assert r.status_code==200,r.text
    result=r.json();after=result['encounter'];assert after['revision']==3
    actor=after['draft']['entities'][0];before=p.before['draft']['entities'][0]
    assert actor['mechanics_snapshot']['origin']=='buddy_saved_mechanics_override_v1'
    assert actor['mechanics_snapshot']['locator']==p.locator
    assert {k:v for k,v in actor.items() if k!='mechanics_snapshot'}=={k:v for k,v in before.items() if k!='mechanics_snapshot'}
    assert after['draft']['entities'][1]==p.before['draft']['entities'][1]
    assert {k:v for k,v in after['draft'].items() if k!='entities'}=={k:v for k,v in p.before['draft'].items() if k!='entities'}
    draft=deepcopy(after['draft']);draft['entities'][0]['hp']=11
    tracked=p.client.put(p.encounter_url,json={'expected_revision':3,'draft':draft});assert tracked.status_code==200,tracked.text
    monkeypatch.setattr(mechanics,'prepare_saved_override',lambda **kw:pytest.fail('Replay must not read producer or sources'))
    replay=apply(p);assert replay.status_code==200,replay.text
    assert replay.json()['receipt']==result['receipt'] and replay.json()['advanced_since_apply'] is True
    assert replay.json()['encounter']['draft']['entities'][0]['hp']==11
    canceled=p.client.post(p.cancel_url,json=p.intent);assert canceled.status_code==200 and canceled.json()['receipt']['state']=='applied'
    forged=deepcopy(tracked.json()['draft']);forged['entities'][0]['mechanics_snapshot']=p.original
    assert p.client.put(p.encounter_url,json={'expected_revision':4,'draft':forged}).status_code==422
    forged=deepcopy(tracked.json()['draft']);forged['entities'].append(dict(forged['entities'][0],id='forged-copy',order=3))
    assert p.client.put(p.encounter_url,json={'expected_revision':4,'draft':forged}).status_code==422
    assert p.client.get(p.encounter_url).json()==tracked.json()


@pytest.mark.parametrize('policy,current,expected', [('keep',35,(35,40)),('preserve_current',35,(35,28)),('clamp_current',35,(28,28)),('reset_full',4,(28,28)),('preserve_current',None,(None,28)),('keep','wounded',('wounded',40)),('preserve_current','wounded',('wounded',28))])
def test_tracker_choices_preserve_temp_conditions_defeated_and_siblings(adoption_case,policy,current,expected):
    p=adoption_case;draft=deepcopy(p.before['draft']);draft['entities'][0].update(hp=current,defeated=True)
    r=p.client.put(p.encounter_url,json={'expected_revision':2,'draft':draft});assert r.status_code==200,r.text
    p.intent['expected_revision']=3;p.intent['actors'][0].update(hp_policy=policy,ac_policy='use_saved')
    r=apply(p);assert r.status_code==200,r.text
    actor=r.json()['encounter']['draft']['entities'][0]
    assert (actor['hp'],actor['max_hp'])==expected and actor['ac']==20
    assert actor['temp_hp']==7 and actor['conditions']==['Prone'] and actor['defeated'] is True and actor['notes']=='Retained tracker note'
    assert r.json()['encounter']['draft']['entities'][1]==p.before['draft']['entities'][1]


@pytest.mark.parametrize('change',['actor_digest','actor_id','statblock','draft','world','uncommitted','clamp_null'])
def test_invalid_or_foreign_selection_never_changes_encounter(adoption_case,change,application_state_dsn):
    p=adoption_case
    if change=='actor_digest':p.intent['actors'][0]['expected_snapshot_digest']='sha256:'+'0'*64
    elif change=='actor_id':p.intent['actors'][0]['actor_id']='absent'
    elif change=='statblock':p.intent['locator']['statblock_id']='sb_other'
    elif change=='draft':p.intent['draft_id']=str(uuid4())
    elif change=='world':p.adopt_url=p.adopt_url.replace('world_id=elderwyld','world_id=other')
    elif change=='uncommitted':
        import psycopg
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE mechanics_revision.operation SET state='outcome_unknown',payload=jsonb_set(jsonb_set(payload,'{state}','\"outcome_unknown\"'),'{result}','null')")
    elif change=='clamp_null':
        draft=deepcopy(p.before['draft']);draft['entities'][0]['hp']=None
        updated=p.client.put(p.encounter_url,json={'expected_revision':2,'draft':draft});assert updated.status_code==200
        p.before=updated.json();p.intent['expected_revision']=3;p.intent['actors'][0]['hp_policy']='clamp_current'
    result=apply(p);assert result.status_code in (404,409,422),result.text
    assert p.client.get(p.encounter_url).json()==p.before


def test_cancel_fences_paused_preflight_and_changed_key_conflicts(adoption_case,monkeypatch):
    p=adoption_case;started=Event();release=Event();prepare=mechanics.prepare_saved_override
    def pause(**kw):
        result=prepare(**kw);started.set();assert release.wait(10);return result
    monkeypatch.setattr(mechanics,'prepare_saved_override',pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(apply,p);assert started.wait(10)
        canceled=p.client.post(p.cancel_url,json=p.intent);assert canceled.status_code==200,canceled.text
        assert canceled.json()['receipt']['state']=='canceled';release.set()
        result=future.result(timeout=10);assert result.status_code==200,result.text
        assert result.json()['receipt']==canceled.json()['receipt']
    assert p.client.get(p.encounter_url).json()==p.before
    changed=deepcopy(p.intent);changed['actors'][0]['hp_policy']='reset_full'
    assert apply(p,changed).status_code==409
    assert p.client.get(p.adopt_url.replace('mechanics-adoptions?',f"mechanics-adoptions/{p.intent['operation_id']}?")).json()['receipt']['state']=='canceled'


@pytest.mark.parametrize('same_key',[True,False])
def test_separate_transaction_races_are_atomic(adoption_case,monkeypatch,same_key):
    p=adoption_case;barrier=Barrier(2);prepare=mechanics.prepare_saved_override
    def pause(**kw):
        result=prepare(**kw);barrier.wait(timeout=10);return result
    monkeypatch.setattr(mechanics,'prepare_saved_override',pause)
    other=deepcopy(p.intent)
    if not same_key:other['operation_id']=str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(apply,p,body) for body in [p.intent,other]]
        responses=[f.result(timeout=15) for f in futures]
    assert sorted(r.status_code for r in responses)==([200,200] if same_key else [200,409])
    assert p.client.get(p.encounter_url).json()['revision']==3
    if same_key:assert responses[0].json()['receipt']==responses[1].json()['receipt']


def test_historical_association_survives_new_slot_and_graph_head(adoption_case,monkeypatch):
    p=adoption_case
    from tests.test_world_mechanics_associations import post
    from apps.live_control_server.services import world_mechanics_associations as association_service
    monkeypatch.setattr(association_service,'build_statblock_v1_client',lambda:p.manual)
    from apps.live_control_server.services import managed_world_graph_projection as graph
    monkeypatch.setattr(graph,'project_managed_world_graph',lambda *a:p.view)
    monkeypatch.setattr(mechanics,'project_managed_world_graph',lambda *a:p.view)
    monkeypatch.setattr(mechanics,'resolve_managed_world_binding',lambda *a:p.binding)
    first=post(p);assert first.status_code==200,first.text
    selection=dict(association_id=first.json()['association']['association_id'],association_version=1,target=p.body['target'])
    snapshot=p.client.post('/api/live/combat/encounters/world-mechanics/preview?world_id=elderwyld',json=selection)
    assert snapshot.status_code==200,snapshot.text
    created=p.client.post('/api/live/combat/encounters?world_id=elderwyld',json={'title':'Historical association actor'}).json()
    p.encounter_url=f"/api/live/combat/encounters/{created['encounter_id']}?world_id=elderwyld"
    draft=deepcopy(p.before['draft'])
    for actor in draft['entities']:actor.update(world_identity=p.body['target'],mechanics_snapshot=snapshot.json())
    saved=p.client.put(p.encounter_url,json={'expected_revision':1,'draft':draft});assert saved.status_code==200,saved.text
    p.before=saved.json();p.adopt_url=f"/api/live/combat/encounters/{created['encounter_id']}/mechanics-adoptions?world_id=elderwyld"
    p.intent['actors'][0]['expected_snapshot_digest']=snapshot.json()['snapshot_digest']
    later=deepcopy(p.body);later.update(request_id=str(uuid4()),expected_version=1)
    p.view.projection.snapshot.revision_id='rev:advanced';later['target']['graph_revision_id']='rev:advanced'
    second=post(p,later);assert second.status_code==200,second.text
    monkeypatch.setattr(graph,'project_managed_world_graph',lambda *a:pytest.fail('Adoption must not resolve current Graph'))
    monkeypatch.setattr(association_service,'project_managed_world_graph',lambda *a:pytest.fail('Adoption must not resolve current Graph'))
    monkeypatch.setattr(mechanics,'project_managed_world_graph',lambda *a:pytest.fail('Adoption must not resolve current Graph'))
    result=apply(p);assert result.status_code==200,result.text
    actor=result.json()['encounter']['draft']['entities'][0]
    assert actor['world_identity']==p.body['target'] and actor['mechanics_snapshot']['locator']==p.locator
    assert p.client.get('/api/live/world-mechanics/associations?world_id=elderwyld').json()==[second.json()['association']]


def test_large_multi_actor_adoption_refuses_atomically(adoption_case):
    p=adoption_case
    body=deepcopy(p.request);body.update(operation_id=str(uuid4()),base=p.locator)
    body['definition']['rule_elements'][0]['rules_text']='Large synthetic rule. '*10000
    source=p.client.post(p.url,json=body);assert source.status_code==200,source.text
    p.intent['locator']=source.json()['result']
    p.intent['actors'].append(dict(p.intent['actors'][0],actor_id='actor-b'))
    result=apply(p);assert result.status_code==422,result.text
    assert p.client.get(p.encounter_url).json()==p.before


def test_same_key_different_body_race_refuses_loser(adoption_case,monkeypatch):
    p=adoption_case;barrier=Barrier(2);prepare=mechanics.prepare_saved_override
    def pause(**kw):
        result=prepare(**kw);barrier.wait(timeout=10);return result
    monkeypatch.setattr(mechanics,'prepare_saved_override',pause)
    other=deepcopy(p.intent);other['actors'][0]['hp_policy']='reset_full'
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(apply,p,body) for body in [p.intent,other]]
        results=[future.result(timeout=15) for future in futures]
    assert sorted(r.status_code for r in results)==[200,409]
    assert p.client.get(p.encounter_url).json()['revision']==3


@pytest.mark.parametrize('damage',['content','invalid_receipt'])
def test_corrupted_producer_result_never_applies(adoption_case,damage):
    p=adoption_case;exact=p.manual.versions[p.locator['revision_id']]
    if damage=='content':
        definition=exact.definition.model_copy(deep=True);definition.identity.name='Forged name'
        p.manual.versions[exact.revision_id]=exact.model_copy(update={'definition':definition})
    else:
        receipt=exact.validation_receipt.model_copy(update={'status':'invalid'})
        p.manual.versions[exact.revision_id]=exact.model_copy(update={'validation_receipt':receipt})
    result=apply(p);assert result.status_code in (500,503),result.text
    assert p.client.get(p.encounter_url).json()==p.before


def test_adoption_routes_require_native_gm(adoption_case):
    from apps.live_control_server.services.agent_graph_auth import authenticate_native_graph_principal,NativeGraphPrincipal
    p=adoption_case;p.app.dependency_overrides.clear()
    p.app.dependency_overrides[authenticate_native_graph_principal]=lambda:NativeGraphPrincipal('player-test','player','local_session')
    assert apply(p).status_code==403
    assert p.client.post(p.cancel_url,json=p.intent).status_code==403


def test_multi_actor_adoption_reads_exact_source_once_and_replay_reads_none(adoption_case,monkeypatch):
    p=adoption_case;calls=[];read=p.manual.get_exact_revision
    monkeypatch.setattr(p.manual,'get_exact_revision',lambda *args:(calls.append(args) or read(*args)))
    p.intent['actors'].append(dict(p.intent['actors'][0],actor_id='actor-b'))
    result=apply(p);assert result.status_code==200,result.text
    assert len(result.json()['receipt']['transitions'])==2 and len(calls)==1
    assert apply(p).status_code==200 and len(calls)==1
