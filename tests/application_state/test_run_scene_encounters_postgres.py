"""Run capture at the real APP transaction boundary, using synthetic sources."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

import psycopg
import pytest

from tests.test_combat_scene_templates import scene_case
from application_state.combat_encounters import scene_templates
from application_state.combat_encounters.scene_template_types import CreateSceneTemplateRequest
from application_state.combat_encounters.service import save_encounter
from application_state.combat_encounters.types import SaveCombatEncounterRequest
from application_state.content.service import commit_plan
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError
from application_state.play import session_encounters as service
from application_state.play.session_encounter_types import WorldSessionCreateRequest
from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN
from apps.live_control_server.services.play_run_edition_structure import structure_signature


def request_for(p, template=None):
    return WorldSessionCreateRequest.model_validate(dict(
        schema_version='dmb_world_session_create_v1', playable_artifact_id=p.obj.work_object_id,
        expected_playable_revision=p.rev.revision_n,
        expected_playable_work_revision_id=p.rev.work_revision_id,
        expected_playable_content_sha256=p.rev.content_sha256, entry_scene_id='scene:gate',
        encounters=[dict(scene_id=scene['scene_id'], template=template if scene['scene_id']=='scene:gate' else None)
                    for scene in structure_signature(V2_SOURCE_MARKDOWN)['membership']['scenes']]))


def template_for(p):
    view=scene_templates.create(world_id='elderwyld',request=CreateSceneTemplateRequest.model_validate(p.body))
    return dict(encounter_id=view.binding.encounter_id,revision=1,digest=view.versions[0].digest)


def test_capture_seeds_actual_scene_parent_and_replays_after_source_changes(scene_case):
    p=scene_case;request=request_for(p,template_for(p));run_id=uuid4()
    result=service.create_session(world_id='elderwyld',run_id=run_id,request=request)
    expected=next(s for s in structure_signature(V2_SOURCE_MARKDOWN)['membership']['scenes'] if s['scene_id']=='scene:gate')
    assert result.aggregate.run.progress['current_scene_id']=='scene:gate'
    assert result.aggregate.run.progress['current_beat_id']==expected['beat_id']
    commit_plan(str(p.obj.work_object_id),V2_SOURCE_MARKDOWN+'\nChanged source',expected_world_id='elderwyld',expected_revision=p.obj.object_revision)
    assert service.create_session(world_id='elderwyld',run_id=run_id,request=request)==result
    assert service.inspect_creation(world_id='elderwyld',run_id=run_id)==result
    assert service.cancel_creation(world_id='elderwyld',run_id=run_id,request=request)==result
    changed=request.model_copy(update={'entry_scene_id':None})
    with pytest.raises(ApplicationStateConflictError,match='different intent'):
        service.create_session(world_id='elderwyld',run_id=run_id,request=changed)


def test_cancel_is_terminal_and_same_key_concurrent_create_is_one_run(scene_case):
    p=scene_case;request=request_for(p);canceled_id=uuid4()
    canceled=service.cancel_creation(world_id='elderwyld',run_id=canceled_id,request=request)
    assert canceled['state']=='canceled'
    assert service.inspect_creation(world_id='elderwyld',run_id=canceled_id)==canceled
    with pytest.raises(ApplicationStateConflictError,match='canceled'):
        service.create_session(world_id='elderwyld',run_id=canceled_id,request=request)
    run_id=uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:service.create_session(world_id='elderwyld',run_id=run_id,request=request),range(2)))
    assert results[0]==results[1]
    with psycopg.connect(p.dsn) as conn:
        assert conn.execute('SELECT count(*) FROM play.session_preparation').fetchone()[0]==1
        assert conn.execute('SELECT count(*) FROM play.run').fetchone()[0]==1


@pytest.mark.parametrize('damage',['missing','extra','null_entry','wrong_entry','work_revision','stale_template','digest','world'])
def test_incomplete_or_stale_intent_is_atomic(scene_case,damage):
    p=scene_case;request=request_for(p,template_for(p));body=request.model_dump(mode='json');world='elderwyld'
    if damage=='missing':body['encounters']=[]
    if damage=='extra':body['encounters'].append(dict(scene_id='scene:absent',template=None))
    if damage=='null_entry':body['entry_scene_id']=None
    if damage=='wrong_entry':body['entry_scene_id']='scene:absent'
    if damage=='work_revision':body['expected_playable_work_revision_id']=str(uuid4())
    if damage=='digest':body['encounters'][0]['template']['digest']='sha256:'+'0'*64
    if damage=='world':world='other-world'
    if damage=='stale_template':
        pin=request.encounters[0].template
        before=scene_templates.read_version(world_id='elderwyld',document_id=p.obj.work_object_id,scene_id='scene:gate',revision=1)
        draft=before.draft.model_dump(mode='json');draft['title']='Newer template'
        save_encounter(world_id='elderwyld',encounter_id=pin.encounter_id,request=SaveCombatEncounterRequest(expected_revision=1,draft=draft))
    with pytest.raises((ApplicationStateConflictError,ApplicationStateIntegrityError)):
        service.create_session(world_id=world,run_id=uuid4(),request=WorldSessionCreateRequest.model_validate(body))
    with psycopg.connect(p.dsn) as conn:
        for table in ('play.run','play.run_manifest','play.session_preparation'):
            assert conn.execute('SELECT count(*) FROM '+table).fetchone()[0]==0


def test_receipt_failure_rolls_back_run_and_manifest(scene_case,monkeypatch):
    p=scene_case;request=request_for(p)
    original=service._result
    def failed(*args):raise RuntimeError('Receipt unavailable')
    monkeypatch.setattr(service,'_result',failed)
    with pytest.raises(RuntimeError,match='Receipt unavailable'):
        service.create_session(world_id='elderwyld',run_id=uuid4(),request=request)
    monkeypatch.setattr(service,'_result',original)
    with psycopg.connect(p.dsn) as conn:
        assert conn.execute('SELECT count(*) FROM play.run').fetchone()[0]==0
        assert conn.execute('SELECT count(*) FROM play.session_preparation').fetchone()[0]==0


def materialization_case(p):
    from application_state.play.session_encounter_types import MaterializeSceneEncounterRequest
    pin=template_for(p)
    source=scene_templates.read_version(world_id='elderwyld',document_id=p.obj.work_object_id,scene_id='scene:gate',revision=1)
    draft=source.draft.model_dump(mode='json')
    draft.update(round=4,active_turn_entity_id='guard',round_start_entity_id='guard',
        entities=[dict(id='guard',name='Gate guard',order=1,hp=3,max_hp=20,temp_hp=7,conditions=['Prone'],defeated=True,notes='Keep this note'),
                  dict(id='watcher',name='Watcher',order=2,hp='unknown',max_hp='30')],
        groups=[dict(group_key='guards',label='Gate guards',member_ids=['guard','watcher'])])
    saved=save_encounter(world_id='elderwyld',encounter_id=source.encounter_id,request=SaveCombatEncounterRequest(expected_revision=1,draft=draft))
    view=scene_templates.read(world_id='elderwyld',document_id=p.obj.work_object_id,scene_id='scene:gate')
    pin.update(revision=saved.revision,digest=view.versions[0].digest)
    run_id=uuid4();creation=request_for(p,pin)
    service.create_session(world_id='elderwyld',run_id=run_id,request=creation)
    preview=service.preview_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate')
    request=MaterializeSceneEncounterRequest(schema_version='dmb_scene_encounter_materialize_v1',operation_id=uuid4(),
        expected_preparation_digest=preview['preparation_digest'],template=pin,
        initialization_policy='dmb_fresh_scene_encounter_v1',preview_digest=preview['preview_digest'])
    return run_id,request,saved


def test_materialization_is_distinct_exact_and_scoped_with_current_replay(scene_case):
    from application_state.combat_encounters.service import get_encounter,list_encounters
    from application_state.play.session_encounter_types import RunEncounterScope
    p=scene_case;run_id,request,template=materialization_case(p)
    # Current Plan and template changes cannot change the captured source.
    draft=template.draft.model_dump(mode='json');draft['title']='Later preparation'
    save_encounter(world_id='elderwyld',encounter_id=template.encounter_id,request=SaveCombatEncounterRequest(expected_revision=2,draft=draft))
    commit_plan(str(p.obj.work_object_id),V2_SOURCE_MARKDOWN.replace('scene:gate','scene:other')+'\nLater Plan',expected_world_id='elderwyld',expected_revision=p.obj.object_revision)
    result=service.materialize_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)
    fight=result['encounter'];assert fight.encounter_id!=template.encounter_id
    assert fight.draft.title==template.draft.title
    first,second=fight.draft.entities
    assert first.id!='guard' and second.id!='watcher'
    assert (first.hp,first.max_hp,first.temp_hp,first.conditions,first.defeated,first.notes)==(20,20,0,[],False,'Keep this note')
    assert (second.hp,second.max_hp)==('unknown','30')
    assert fight.draft.groups[0].member_ids==[first.id,second.id]
    assert (fight.draft.round,fight.draft.active_turn_entity_id,fight.draft.round_start_entity_id)==(1,None,None)
    assert list_encounters(world_id='elderwyld')==[]
    with pytest.raises(ApplicationStateConflictError,match='owning session'):
        get_encounter(world_id='elderwyld',encounter_id=fight.encounter_id)
    with pytest.raises(ApplicationStateConflictError,match='owning session'):
        save_encounter(world_id='elderwyld',encounter_id=fight.encounter_id,request=SaveCombatEncounterRequest(expected_revision=1,draft=fight.draft))
    scope=RunEncounterScope(run_id=run_id,scene_id='scene:gate')
    changed=fight.draft.model_dump(mode='json');changed['entities'][0]['hp']=14
    updated=save_encounter(world_id='elderwyld',encounter_id=fight.encounter_id,scope=scope,request=SaveCombatEncounterRequest(expected_revision=1,draft=changed))
    assert get_encounter(world_id='elderwyld',encounter_id=fight.encounter_id,scope=scope)==updated
    replay=service.materialize_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)
    assert replay['encounter']==updated
    assert service.cancel_materialization(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)['encounter']==updated
    with pytest.raises(ApplicationStateConflictError,match='already has an encounter'):
        service.materialize_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request.model_copy(update={'operation_id':uuid4()}))


def test_materialization_cancel_and_preview_mismatch_do_not_create_fights(scene_case):
    p=scene_case;run_id,request,_=materialization_case(p)
    wrong=request.model_copy(update={'preview_digest':'sha256:'+'0'*64})
    with pytest.raises(ApplicationStateConflictError,match='preview'):
        service.materialize_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=wrong)
    assert service.cancel_materialization(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)['state']=='canceled'
    with pytest.raises(ApplicationStateConflictError,match='canceled'):
        service.materialize_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)
    with psycopg.connect(p.dsn) as conn:
        assert conn.execute('SELECT count(*) FROM combat.run_scene_encounter').fetchone()[0]==0


def test_ended_and_trashed_sessions_refuse_mutation_but_allow_recovery(scene_case):
    from application_state.combat_encounters.service import get_encounter
    from application_state.play.session_encounter_types import RunEncounterScope
    p=scene_case;run_id,request,_=materialization_case(p)
    result=service.materialize_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)
    fight=result['encounter'];scope=RunEncounterScope(run_id=run_id,scene_id='scene:gate')
    with psycopg.connect(p.dsn) as conn:
        conn.execute("UPDATE play.run SET lifecycle_status='trashed' WHERE run_id=%s",(run_id,))
    assert get_encounter(world_id='elderwyld',encounter_id=fight.encounter_id,scope=scope)==fight
    assert service.materialize_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)['encounter']==fight
    with pytest.raises(ApplicationStateConflictError,match='Restore'):
        save_encounter(world_id='elderwyld',encounter_id=fight.encounter_id,scope=scope,request=SaveCombatEncounterRequest(expected_revision=1,draft=fight.draft))


def test_preparation_preview_names_choices_and_excludes_orphans(scene_case):
    from application_state.play.session_encounter_types import WorldSessionSourceRequest
    p=scene_case;pin=template_for(p)
    source=WorldSessionSourceRequest.model_validate({key:value for key,value in request_for(p).model_dump().items()
        if key not in ('schema_version','entry_scene_id','encounters')})
    preview=service.preparation_preview(world_id='elderwyld',request=source)
    assert preview['scenes'][0]['name']=='The Gate'
    assert preview['scenes'][0]['encounter_name']=='Gate guardians'
    assert preview['request']['encounters'][0]['template']['encounter_id']==str(pin['encounter_id'])
    assert preview['request']['entry_scene_id']=='scene:gate'
    assert preview['excluded_orphan_count']==0
    obj,rev=commit_plan(str(p.obj.work_object_id),V2_SOURCE_MARKDOWN.replace('scene:gate','scene:other'),expected_world_id='elderwyld',expected_revision=p.obj.object_revision)
    source=source.model_copy(update={'expected_playable_revision':rev.revision_n,'expected_playable_work_revision_id':rev.work_revision_id,'expected_playable_content_sha256':rev.content_sha256})
    changed=service.preparation_preview(world_id='elderwyld',request=source)
    assert changed['excluded_orphan_count']==1 and changed['request']['encounters'][0]['template'] is None


def test_session_close_blocks_new_mutations_and_reopen_restores_them(scene_case):
    from application_state.play.session_review import commit_review,ReviewCommand
    from application_state.play.edition_service import read_content
    from application_state.play.session_encounter_types import RunEncounterScope
    p=scene_case;run_id,request,_=materialization_case(p)
    fight=service.materialize_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)['encounter']
    content=read_content(world_id='elderwyld',run_id=run_id)
    commit_review(world_id='elderwyld',run_id=run_id,command_id=uuid4(),request=ReviewCommand(action='end',expected_revision=0,expected_run_revision=1,expected_content_sha256=content.content_sha256,final_thoughts='Stopped at the gate'))
    scope=RunEncounterScope(run_id=run_id,scene_id='scene:gate')
    with pytest.raises(ApplicationStateConflictError,match='Reopen'):
        save_encounter(world_id='elderwyld',encounter_id=fight.encounter_id,scope=scope,request=SaveCombatEncounterRequest(expected_revision=1,draft=fight.draft))
    assert service.cancel_materialization(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)['encounter']==fight
    commit_review(world_id='elderwyld',run_id=run_id,command_id=uuid4(),request=ReviewCommand(action='reopen',expected_revision=1,expected_run_revision=1,expected_content_sha256=content.content_sha256))
    assert save_encounter(world_id='elderwyld',encounter_id=fight.encounter_id,scope=scope,request=SaveCombatEncounterRequest(expected_revision=1,draft=fight.draft)).revision==2


def test_concurrent_materializations_have_one_binding_and_fresh_instance(scene_case):
    p=scene_case;run_id,request,_=materialization_case(p)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(lambda _:service.materialize_encounter(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request),range(2)))
    assert outcomes[0]==outcomes[1]
    with psycopg.connect(p.dsn) as conn:
        assert conn.execute('SELECT count(*) FROM combat.run_scene_encounter').fetchone()[0]==1
        assert conn.execute('SELECT count(*) FROM combat.encounter').fetchone()[0]==2


@pytest.mark.parametrize(('maximum','expected'),[(0,0),(None,3),('30',3)])
def test_initialization_uses_only_actual_typed_maximum_hp(scene_case,maximum,expected):
    p=scene_case;pin=template_for(p)
    source=scene_templates.read_version(world_id='elderwyld',document_id=p.obj.work_object_id,scene_id='scene:gate',revision=1)
    body=source.draft.model_dump(mode='json');body['entities']=[dict(id='guard',name='Guard',order=1,hp=3,max_hp=maximum,defeated=True)]
    from application_state.combat_encounters.types import CombatEncounterDraft
    source=source.model_copy(update={'draft':CombatEncounterDraft.model_validate(body)})
    draft,_,_=service.initialize_draft(source,fresh_ids=True)
    assert draft.entities[0].hp==expected and draft.entities[0].defeated is False
    body['entities'][0]['max_hp']=-1
    source=source.model_copy(update={'draft':CombatEncounterDraft.model_validate(body)})
    with pytest.raises(Exception,match='Negative maximum'):
        service.initialize_draft(source,fresh_ids=True)


def test_empty_preparation_receipt_still_prevents_rebase(scene_case):
    from application_state.content.service import create_world_runbook,commit_runbook
    from application_state.play.service import rebase_world_play_run
    p=scene_case;obj=create_world_runbook(title='No scenes yet',world_id='elderwyld')
    obj,revision=commit_runbook(str(obj.work_object_id),'<!-- dmb-playable-element:v2 kind=beat id=beat:opening -->\n## Opening\n',expected_revision=obj.object_revision)
    request=WorldSessionCreateRequest(schema_version='dmb_world_session_create_v1',playable_artifact_id=obj.work_object_id,
        expected_playable_revision=revision.revision_n,expected_playable_work_revision_id=revision.work_revision_id,
        expected_playable_content_sha256=revision.content_sha256,entry_scene_id=None,encounters=[])
    run_id=uuid4();created=service.create_session(world_id='elderwyld',run_id=run_id,request=request)
    assert created.receipt['preparation']=={'scenes':[]}
    with pytest.raises(ApplicationStateConflictError,match='captured encounter preparation'):
        rebase_world_play_run(world_id='elderwyld',run_id=run_id,expected_run_revision=1,target_playable_revision=revision.revision_n,target_playable_content_sha256=revision.content_sha256)
    assert service.inspect_creation(world_id='elderwyld',run_id=run_id)==created


def test_migration_cannot_discard_a_retained_cancellation_fence(scene_case):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    p=scene_case;service.cancel_creation(world_id='elderwyld',run_id=uuid4(),request=request_for(p))
    engine=create_engine(p.dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError,match='Cannot discard retained'):
                    import_module('application_state.migrations.versions.20261022_0052_run_scene_encounters').downgrade()
    finally:engine.dispose()


def test_selected_later_scene_seeds_its_own_parent_beat(scene_case):
    p=scene_case;markdown=V2_SOURCE_MARKDOWN+'\n<!-- dmb-playable-element:v2 kind=beat id=beat:landing -->\n## Landing\n<!-- dmb-playable-element:v2 kind=scene id=scene:landing -->\n### The Landing\n'
    obj,revision=commit_plan(str(p.obj.work_object_id),markdown,expected_world_id='elderwyld',expected_revision=p.obj.object_revision)
    from tests.application_state.session_encounter_helpers import session_request
    request=session_request(world_id='elderwyld',playable_artifact_id=obj.work_object_id,expected_playable_revision=revision.revision_n,expected_playable_content_sha256=revision.content_sha256).model_copy(update={'entry_scene_id':'scene:landing'})
    result=service.create_session(world_id='elderwyld',run_id=uuid4(),request=request)
    assert result.aggregate.run.progress['current_scene_id']=='scene:landing'
    assert result.aggregate.run.progress['current_beat_id']=='beat:landing'


def test_capture_serializes_a_concurrent_template_save(scene_case,monkeypatch):
    from threading import Event
    p=scene_case;pin=template_for(p);request=request_for(p,pin);entered=Event();release=Event()
    original=service.read_snapshot
    def paused(*args,**kwargs):
        result=original(*args,**kwargs);entered.set();assert release.wait(10);return result
    monkeypatch.setattr(service,'read_snapshot',paused)
    source=scene_templates.read_version(world_id='elderwyld',document_id=p.obj.work_object_id,scene_id='scene:gate',revision=1)
    draft=source.draft.model_dump(mode='json');draft['title']='Later saved preparation'
    with ThreadPoolExecutor(max_workers=2) as pool:
        creating=pool.submit(service.create_session,world_id='elderwyld',run_id=uuid4(),request=request)
        assert entered.wait(10)
        saving=pool.submit(save_encounter,world_id='elderwyld',encounter_id=source.encounter_id,request=SaveCombatEncounterRequest(expected_revision=1,draft=draft))
        release.set();created=creating.result(10);saved=saving.result(10)
    assert saved.revision==2
    assert created.receipt['request']['encounters'][0]['template']==request.encounters[0].template.model_dump(mode='json')
    assert created.receipt['preparation']['scenes'][0]['title']=='Gate guardians'


def test_cancel_waits_for_the_same_inflight_session_creation(scene_case,monkeypatch):
    from threading import Event
    p=scene_case;entered=Event();release=Event();request=request_for(p);run_id=uuid4();original=service.repo.insert_manifest
    def paused(*args,**kwargs):
        entered.set();assert release.wait(10);return original(*args,**kwargs)
    monkeypatch.setattr(service.repo,'insert_manifest',paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        creating=pool.submit(service.create_session,world_id='elderwyld',run_id=run_id,request=request)
        assert entered.wait(10)
        canceling=pool.submit(service.cancel_creation,world_id='elderwyld',run_id=run_id,request=request)
        release.set();assert creating.result(10)==canceling.result(10)


def test_cancel_waits_for_the_same_inflight_encounter_creation(scene_case,monkeypatch):
    from threading import Event
    from application_state.combat_encounters import repository as encounters
    p=scene_case;run_id,request,_=materialization_case(p);entered=Event();release=Event();original=encounters.insert_encounter
    def paused(*args,**kwargs):
        entered.set();assert release.wait(10);return original(*args,**kwargs)
    monkeypatch.setattr(encounters,'insert_encounter',paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        creating=pool.submit(service.materialize_encounter,world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)
        assert entered.wait(10)
        canceling=pool.submit(service.cancel_materialization,world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)
        release.set();assert creating.result(10)==canceling.result(10)
