"""Authenticated current session/encounter HTTP boundary, with synthetic retained data."""
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from tests.test_combat_scene_templates import scene_case
from tests.application_state.test_run_scene_encounters_postgres import request_for,materialization_case
from apps.live_control_server.services.agent_graph_auth import authenticate_native_graph_principal,NativeGraphPrincipal


def client_for(p,monkeypatch):
    from apps.live_control_server.routes import play_runs,combat_run_encounters,combat_encounters
    app=FastAPI();app.include_router(play_runs.router);app.include_router(combat_run_encounters.router);app.include_router(combat_encounters.router)
    app.dependency_overrides[authenticate_native_graph_principal]=lambda:NativeGraphPrincipal('test-gm','gm','local_session')
    monkeypatch.setattr(play_runs,'_verified_world',lambda world_id:world_id)
    monkeypatch.setattr(combat_run_encounters,'_verified_world',lambda world_id:world_id)
    monkeypatch.setattr(combat_encounters,'_verified_world',lambda world_id:world_id)
    return TestClient(app),app


def test_versioned_create_receipt_and_old_body_refusal(scene_case,monkeypatch):
    p=scene_case;client,app=client_for(p,monkeypatch);request=request_for(p);run_id=uuid4()
    path=f'/api/live/world-play-runs/v2/{run_id}?world_id=elderwyld'
    result=client.put(path,json=request.model_dump(mode='json'))
    assert result.status_code==200,result.text
    body=result.json();assert body['state']=='applied' and body['run']['run_id']==str(run_id)
    assert body['receipt']['request']==request.model_dump(mode='json')
    assert body['manifest']['schema_version']=='dmb_play_run_reference_manifest_v2'
    assert client.put(f'/api/live/world-play-runs/v2/{run_id}/reference-manifest?world_id=elderwyld').status_code==405
    assert client.get(f'/api/live/world-play-runs/v2/{run_id}/creation?world_id=elderwyld').json()==body
    old={key:value for key,value in request.model_dump(mode='json').items() if key in ('playable_artifact_id','expected_playable_revision','expected_playable_content_sha256')}
    assert client.put(f'/api/live/world-play-runs/v2/{uuid4()}?world_id=elderwyld',json=old).status_code==422
    app.dependency_overrides[authenticate_native_graph_principal]=lambda:NativeGraphPrincipal('player','player','local_session')
    assert client.put(path,json=request.model_dump(mode='json')).status_code==403
    assert client.get(f'/api/live/world-play-runs/v2/{run_id}/creation?world_id=elderwyld').status_code==403


def test_scoped_http_save_and_world_bypass_fences(scene_case,monkeypatch):
    p=scene_case;client,_=client_for(p,monkeypatch);run_id,request,template=materialization_case(p)
    path=f'/api/live/combat/run-encounters/{run_id}/scenes/scene:gate'
    result=client.post(path+'?world_id=elderwyld',json=request.model_dump(mode='json'))
    assert result.status_code==200,result.text
    fight=result.json()['encounter'];encounter_id=fight['encounter_id']
    assert client.get(path+'?world_id=elderwyld').json()==result.json()
    world_path=f'/api/live/combat/encounters/{encounter_id}'
    assert client.get(world_path+'?world_id=elderwyld').status_code==409
    assert client.put(world_path+'?world_id=elderwyld',json={'expected_revision':1,'draft':fight['draft']}).status_code==409
    assert client.get(world_path+f'/mechanics-adoptions/{uuid4()}?world_id=elderwyld').status_code==409
    assert client.get(path+f'/encounters/{encounter_id}?world_id=another-world').status_code==404
    assert client.get(path.replace('scene:gate','scene:absent')+f'/encounters/{encounter_id}?world_id=elderwyld').status_code==404
    draft=fight['draft'];draft['entities'][0]['hp']=9
    updated=client.put(path+f'/encounters/{encounter_id}?world_id=elderwyld',json={'expected_revision':1,'draft':draft})
    assert updated.status_code==200,updated.text
    assert updated.json()['revision']==2 and updated.json()['draft']['entities'][0]['hp']==9
    assert client.post(path+'?world_id=elderwyld',json=request.model_dump(mode='json')).json()['encounter']==updated.json()


from tests.test_combat_mechanics_adoption import adoption_case
from tests.test_statblock_saved_revisions import revision_case
from tests.test_world_mechanics_associations import prepared


def test_run_scoped_exact_adoption_reuses_existing_writer_and_offline_receipt(adoption_case,monkeypatch):
    from application_state.content.service import create_world_plan,commit_plan
    from application_state.combat_encounters import scene_templates
    from application_state.combat_encounters.scene_template_types import CreateSceneTemplateRequest
    from application_state.combat_encounters.service import save_encounter
    from application_state.combat_encounters.types import SaveCombatEncounterRequest,AcceptedCombatMechanicsSnapshot
    from application_state.play import session_encounters as sessions
    from application_state.play.session_encounter_types import MaterializeSceneEncounterRequest
    from tests.application_state.session_encounter_helpers import session_request
    from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN
    from apps.live_control_server.services import combat_mechanics
    p=adoption_case;obj=create_world_plan(title='Scoped adoption source',world_id='elderwyld')
    obj,revision=commit_plan(str(obj.work_object_id),V2_SOURCE_MARKDOWN,expected_world_id='elderwyld',expected_revision=obj.object_revision)
    prepared=scene_templates.create(world_id='elderwyld',request=CreateSceneTemplateRequest(operation_id=uuid4(),pin=dict(document_id=obj.work_object_id,scene_id='scene:gate',revision_n=revision.revision_n,work_revision_id=revision.work_revision_id,content_sha256=revision.content_sha256),encounter={'title':'Run adoption source'}))
    snapshot=AcceptedCombatMechanicsSnapshot.model_validate(p.original)
    saved=save_encounter(world_id='elderwyld',encounter_id=prepared.encounter.encounter_id,request=SaveCombatEncounterRequest(expected_revision=1,draft=p.before['draft']),verified_mechanics_snapshots={actor['id']:snapshot for actor in p.before['draft']['entities']})
    view=scene_templates.read(world_id='elderwyld',document_id=obj.work_object_id,scene_id='scene:gate')
    request=session_request(world_id='elderwyld',playable_artifact_id=obj.work_object_id,expected_playable_revision=revision.revision_n,expected_playable_content_sha256=revision.content_sha256).model_dump(mode='json')
    request['encounters'][0]['template']={'encounter_id':str(saved.encounter_id),'revision':saved.revision,'digest':view.versions[0].digest}
    from application_state.play.session_encounter_types import WorldSessionCreateRequest
    run_id=uuid4();sessions.create_session(world_id='elderwyld',run_id=run_id,request=WorldSessionCreateRequest.model_validate(request))
    preview=sessions.preview_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate')
    materialize=MaterializeSceneEncounterRequest(schema_version='dmb_scene_encounter_materialize_v1',operation_id=uuid4(),expected_preparation_digest=preview['preparation_digest'],template=preview['template'],initialization_policy='dmb_fresh_scene_encounter_v1',preview_digest=preview['preview_digest'])
    fight=sessions.materialize_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=materialize)['encounter']
    intent={**p.intent,'operation_id':str(uuid4()),'expected_revision':1,'actors':[{**p.intent['actors'][0],'actor_id':fight.draft.entities[0].id}]}
    path=f'/api/live/combat/run-encounters/{run_id}/scenes/scene:gate/encounters/{fight.encounter_id}/mechanics-adoptions?world_id=elderwyld'
    applied=p.client.post(path,json=intent);assert applied.status_code==200,applied.text
    after=applied.json()['encounter'];assert after['revision']==2
    assert after['draft']['entities'][1]==fight.draft.entities[1].model_dump(mode='json')
    assert after['draft']['groups']==[group.model_dump(mode='json') for group in fight.draft.groups]
    assert after['draft']['entities'][0]['id']==fight.draft.entities[0].id
    assert after['draft']['entities'][0]['mechanics_snapshot']['locator']==p.locator
    monkeypatch.setattr(combat_mechanics,'prepare_saved_override',lambda **kw:(_ for _ in ()).throw(AssertionError('Receipt replay must not reread producer')))
    assert p.client.post(path,json=intent).json()==applied.json()
    assert p.client.get(f'/api/live/combat/encounters/{fight.encounter_id}/mechanics-adoptions/{intent["operation_id"]}?world_id=elderwyld').status_code==409
    assert scene_templates.read_version(world_id='elderwyld',document_id=obj.work_object_id,scene_id='scene:gate',revision=2)==saved


@pytest.mark.parametrize('field', ['scene_id', 'operation_id', 'receipt_template', 'request_digest'])
def test_corrupt_binding_is_refused_by_http_reads_and_recovery(scene_case, monkeypatch, field):
    import psycopg
    p = scene_case
    client, _ = client_for(p, monkeypatch)
    run_id, request, _ = materialization_case(p)
    path = f'/api/live/combat/run-encounters/{run_id}/scenes/scene:gate'
    applied = client.post(path+'?world_id=elderwyld', json=request.model_dump(mode='json'))
    assert applied.status_code == 200, applied.text
    encounter_id = applied.json()['encounter']['encounter_id']
    values = {'scene_id': 'scene:forged', 'operation_id': uuid4(), 'template_revision': 999,
              'request_digest': 'sha256:'+'0'*64}
    with psycopg.connect(p.dsn) as conn:
        if field == 'receipt_template':
            from psycopg.types.json import Jsonb
            payload = applied.json()['receipt']
            payload['intent']['request']['template']['revision'] = 999
            conn.execute('UPDATE combat.run_scene_encounter SET payload=%s WHERE encounter_id=%s', (Jsonb(payload), encounter_id))
        else:
            conn.execute('UPDATE combat.run_scene_encounter SET '+field+'=%s WHERE encounter_id=%s',
                         (values[field], encounter_id))
    scoped = path.replace('scene:gate', 'scene:forged') if field == 'scene_id' else path
    assert client.get(scoped+'?world_id=elderwyld').status_code == 500
    assert client.get(scoped+f'/encounters/{encounter_id}?world_id=elderwyld').status_code == 500
    if field != 'operation_id':
        for suffix in ('', '/cancel', '/inspect'):
            assert client.post(path+suffix+'?world_id=elderwyld', json=request.model_dump(mode='json')).status_code == 500
