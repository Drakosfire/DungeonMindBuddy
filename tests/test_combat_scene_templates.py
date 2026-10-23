"""Real HTTP and APP ownership tests for Plan scene preparation."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from application_state.content.service import create_world_plan,commit_plan,autosave_plan
from application_state.combat_encounters import scene_templates as service
from application_state.combat_encounters.scene_template_types import CreateSceneTemplateRequest
from application_state.combat_encounters.service import get_encounter,save_encounter
from application_state.combat_encounters.types import SaveCombatEncounterRequest
from application_state.errors import ApplicationStateConflictError,ApplicationStateIntegrityError
from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN

pytest_plugins=['tests.application_state.conftest']

@pytest.fixture
def scene_case(application_state_dsn,monkeypatch):
    from apps.live_control_server.routes import combat_scene_templates as routes
    from apps.live_control_server.services.agent_graph_auth import authenticate_native_graph_principal,NativeGraphPrincipal
    obj=create_world_plan(title='Synthetic road encounter',world_id='elderwyld')
    obj,rev=commit_plan(str(obj.work_object_id),V2_SOURCE_MARKDOWN,expected_world_id='elderwyld',expected_revision=obj.object_revision)
    body=dict(schema_version='dmb_scene_template_create_v1',operation_id=str(uuid4()),pin=dict(document_id=str(obj.work_object_id),scene_id='scene:gate',revision_n=rev.revision_n,work_revision_id=str(rev.work_revision_id),content_sha256=rev.content_sha256),encounter={'title':'Gate guardians'})
    app=FastAPI();app.include_router(routes.router)
    app.dependency_overrides[authenticate_native_graph_principal]=lambda:NativeGraphPrincipal('test-gm','gm','local_session')
    monkeypatch.setattr(routes,'_verified_world',lambda world_id:world_id)
    return SimpleNamespace(obj=obj,rev=rev,body=body,client=TestClient(app),app=app,base='/api/live/combat/scene-templates',dsn=application_state_dsn)

def create(p,body=None):return p.client.post(p.base+'?world_id=elderwyld',json=body or p.body)
def read(p,world='elderwyld'):return p.client.get(p.base+f'/{p.obj.work_object_id}/scenes/scene:gate?world_id={world}')

def test_exact_create_replay_save_history_and_orphan_recovery(scene_case):
    p=scene_case;assert read(p).json() is None
    r=create(p);assert r.status_code==200,r.text
    v=r.json();assert create(p).json()==v
    before=v['encounter'];draft=deepcopy(before['draft']);draft['entities']=[dict(id='guard',name='Gate guard',order=1,hp=12,max_hp=12,notes='Retained preparation')]
    saved=save_encounter(world_id='elderwyld',encounter_id=before['encounter_id'],request=SaveCombatEncounterRequest(expected_revision=1,draft=draft))
    got=read(p).json();assert [x['revision'] for x in got['versions']]==[2,1]
    old=p.client.get(p.base+f'/{p.obj.work_object_id}/scenes/scene:gate/versions/1?world_id=elderwyld')
    assert old.status_code==200 and old.json()==before
    assert service.read_version(world_id='elderwyld',document_id=p.obj.work_object_id,scene_id='scene:gate',revision=2)==saved
    # Replay precedes current Plan admission; removal does not discard work/history.
    commit_plan(str(p.obj.work_object_id),V2_SOURCE_MARKDOWN.replace('scene:gate','scene:other'),expected_world_id='elderwyld',expected_revision=p.obj.object_revision)
    assert read(p).json()['scene_present'] is False
    assert create(p).json()['encounter']==saved.model_dump(mode='json',by_alias=True)
    assert service.read_version(world_id='elderwyld',document_id=p.obj.work_object_id,scene_id='scene:gate',revision=1).model_dump(mode='json',by_alias=True)==before

@pytest.mark.parametrize('damage',['sha','revision','work_revision','scene','world','kind'])
def test_foreign_stale_and_missing_identity_cannot_create(scene_case,damage):
    p=scene_case;body=deepcopy(p.body);world='elderwyld'
    if damage=='sha':body['pin']['content_sha256']='a'*64
    if damage=='revision':body['pin']['revision_n']+=1
    if damage=='work_revision':body['pin']['work_revision_id']=str(uuid4())
    if damage=='scene':body['pin']['scene_id']='scene:absent'
    if damage=='world':world='other-world'
    if damage=='kind':
        from application_state.content.service import create_world_runbook,commit_runbook
        obj=create_world_runbook(title='Other kind',world_id='elderwyld');obj,rev=commit_runbook(str(obj.work_object_id),V2_SOURCE_MARKDOWN,expected_revision=obj.object_revision)
        body['pin'].update(document_id=str(obj.work_object_id),revision_n=rev.revision_n,work_revision_id=str(rev.work_revision_id),content_sha256=rev.content_sha256)
    result=p.client.post(p.base+f'?world_id={world}',json=body)
    assert result.status_code in (404,409),result.text
    assert read(p).json() is None


def test_dirty_plan_refused_and_same_key_changed_body_conflicts(scene_case):
    p=scene_case;assert create(p).status_code==200
    body=deepcopy(p.body);body['encounter']['title']='Changed intent';assert create(p,body).status_code==409
    body['operation_id']=str(uuid4());assert create(p,body).status_code==409
    autosave_plan(str(p.obj.work_object_id),V2_SOURCE_MARKDOWN+'\nUnsaved change',expected_world_id='elderwyld',expected_revision=p.obj.object_revision)
    # Existing receipt still recoverable with exact original intent.
    assert create(p).status_code==200
    body=deepcopy(p.body);body['operation_id']=str(uuid4());assert create(p,body).status_code==409


def test_same_key_concurrent_creation_is_one_binding(scene_case):
    p=scene_case;request=CreateSceneTemplateRequest.model_validate(p.body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:service.create(world_id='elderwyld',request=request),range(2)))
    assert results[0]==results[1]
    assert len(results[0].versions)==1


def test_different_key_concurrent_creation_conflicts(scene_case):
    p=scene_case
    def run(_):
        body=deepcopy(p.body);body['operation_id']=str(uuid4())
        try:return service.create(world_id='elderwyld',request=CreateSceneTemplateRequest.model_validate(body)).binding.encounter_id
        except ApplicationStateConflictError:return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,range(2)))
    assert results.count('conflict')==1


def test_atomic_history_failure_rolls_back_creation_and_save(scene_case,monkeypatch):
    p=scene_case;original=service.append_version
    def fail(*args):raise RuntimeError('History storage unavailable')
    monkeypatch.setattr(service,'append_version',fail)
    with pytest.raises(RuntimeError,match='History storage'):create(p)
    assert read(p).json() is None
    monkeypatch.setattr(service,'append_version',original);record=create(p).json()['encounter']
    monkeypatch.setattr(service,'append_version',fail)
    draft=deepcopy(record['draft']);draft['title']='Must rollback'
    with pytest.raises(RuntimeError,match='History storage'):
        save_encounter(world_id='elderwyld',encounter_id=record['encounter_id'],request=SaveCombatEncounterRequest(expected_revision=1,draft=draft))
    assert get_encounter(world_id='elderwyld',encounter_id=record['encounter_id']).model_dump(mode='json',by_alias=True)==record


def test_player_and_foreign_world_cannot_read_or_create(scene_case):
    p=scene_case;assert create(p).status_code==200;assert read(p,'other-world').json() is None
    from apps.live_control_server.services.agent_graph_auth import authenticate_native_graph_principal,NativeGraphPrincipal
    p.app.dependency_overrides[authenticate_native_graph_principal]=lambda:NativeGraphPrincipal('test-player','player','local_session')
    assert read(p).status_code==403;assert create(p).status_code==403
    assert p.client.get(p.base+'/operations/'+p.body['operation_id']+'?world_id=elderwyld').status_code==403
    assert p.client.post(p.base+'/cancel?world_id=elderwyld',json=p.body).status_code==403
    assert p.client.get(p.base+f'/{p.obj.work_object_id}/scenes/scene:gate/versions/1?world_id=elderwyld').status_code==403


def test_creation_inspection_is_world_scoped_and_historical_digest_is_checked(scene_case):
    p=scene_case;record=create(p).json()['encounter']
    path=p.base+'/operations/'+p.body['operation_id']
    assert p.client.get(path+'?world_id=elderwyld').json()['encounter']==record
    assert p.client.get(path+'?world_id=other-world').json() is None
    import psycopg
    with psycopg.connect(p.dsn) as conn:conn.execute("UPDATE combat.scene_template_version SET digest=%s",('sha256:'+'0'*64,))
    with pytest.raises(ApplicationStateIntegrityError,match='digest'):
        service.read_version(world_id='elderwyld',document_id=p.obj.work_object_id,scene_id='scene:gate',revision=1)

def test_bound_templates_are_not_offered_as_standalone_world_fights(scene_case):
    from application_state.combat_encounters.service import list_encounters
    p=scene_case;record=create(p).json()['encounter']
    assert all(str(item.encounter_id)!=record['encounter_id'] for item in list_encounters(world_id='elderwyld'))

@pytest.mark.parametrize('markdown',[V2_SOURCE_MARKDOWN.replace('<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->','<!-- HTML\n<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->'),V2_SOURCE_MARKDOWN+'\n<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->\n### Duplicate'])
def test_noncanonical_or_duplicate_scene_markup_cannot_create(scene_case,markdown):
    p=scene_case;obj,rev=commit_plan(str(p.obj.work_object_id),markdown,expected_world_id='elderwyld',expected_revision=p.obj.object_revision)
    body=deepcopy(p.body);body['pin'].update(revision_n=rev.revision_n,work_revision_id=str(rev.work_revision_id),content_sha256=rev.content_sha256)
    result=create(p,body);assert result.status_code in (409,422),result.text
