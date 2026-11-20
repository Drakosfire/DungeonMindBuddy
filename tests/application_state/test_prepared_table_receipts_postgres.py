from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import psycopg
import pytest
from alembic import command
from application_state.cli import alembic_config
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError, ApplicationStateValidationError
from application_state.play.prepared_table_service import TableRollCommand, inventory, record_roll, receipts
from application_state.play.service import replace_world_play_run_progress, rebase_world_play_run
from application_state.content.service import commit_plan, commit_runbook
from tests.application_state.test_play_run_editions_postgres import create_source_run, WORLD
from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN
from tests.test_prepared_tables import source


def setup(kind='plan'):
    return create_source_run(kind=kind, markdown=V2_SOURCE_MARKDOWN+'\n\n'+source())


def body(run_id, value=2):
    current=inventory(world_id=WORLD,run_id=run_id)
    table=current['tables'][0]
    return TableRollCommand(expected_run_revision=current['run']['run_revision'], **current['source'],
                            table_id=table['table_id'],table_sha256=table['table_sha256'],physical_value=value)


def roll(run_id, request=None, command_id=None, world=WORLD):
    return record_roll(world_id=world,run_id=run_id,command_id=command_id or str(uuid4()),request=request or body(run_id))


def test_atomic_receipt_replay_independent_progress_and_append_only(application_state_dsn):
    obj,revision,aggregate=setup(); run_id=str(aggregate.run.run_id)
    request=body(run_id); key=str(uuid4())
    accepted=roll(run_id,request,key)
    assert accepted['receipt']['outcome']=='Dry'
    assert accepted['run']['run_revision']==2
    assert accepted['run']['progress']==aggregate.run.progress
    assert roll(run_id,request,key)['receipt']==accepted['receipt']
    assert receipts(world_id=WORLD,run_id=run_id)['receipts']==[accepted['receipt']]
    with pytest.raises(ApplicationStateConflictError):roll(run_id,request.model_copy(update={'physical_value':3}),key)
    with pytest.raises(ApplicationStateNotFoundError):roll(run_id,request,key,world='other')
    progress=dict(aggregate.run.progress);progress['notes_by_element_id']={'scene:gate':'Remember this.'}
    replace_world_play_run_progress(world_id=WORLD,run_id=run_id,expected_run_revision=2,progress=progress)
    assert roll(run_id,request,key)['receipt']==accepted['receipt']
    assert receipts(world_id=WORLD,run_id=run_id)['receipts']==[accepted['receipt']]
    with psycopg.connect(application_state_dsn,autocommit=True) as conn:
        for sql in ('UPDATE play.prepared_table_receipt SET payload=payload','DELETE FROM play.prepared_table_receipt','TRUNCATE play.prepared_table_receipt'):
            with pytest.raises(psycopg.errors.RaiseException):conn.execute(sql)
    with pytest.raises(Exception,match='refusing to discard'):
        command.downgrade(alembic_config(),'20261022_0043')


def test_stale_invalid_and_concurrent_leave_no_partial_receipt(application_state_dsn):
    _,_,aggregate=setup();run_id=str(aggregate.run.run_id);request=body(run_id)
    for bad in (request.model_copy(update={'physical_value':7}), request.model_copy(update={'table_sha256':'0'*64})):
        with pytest.raises((ApplicationStateValidationError,ApplicationStateConflictError)):roll(run_id,bad)
    assert receipts(world_id=WORLD,run_id=run_id)['receipts']==[]
    assert inventory(world_id=WORLD,run_id=run_id)['run']['run_revision']==1
    def submit(_):
        try:return roll(run_id,request)['receipt']['outcome']
        except ApplicationStateConflictError:return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(submit,range(2)))==['Dry','conflict']
    assert len(receipts(world_id=WORLD,run_id=run_id)['receipts'])==1


def test_source_advance_pins_existing_run_and_replay_after_ended_trash(application_state_dsn):
    from application_state.play.session_review import commit_review
    from tests.application_state.test_play_session_review_postgres import request as review_request
    from application_state.play.lifecycle import set_world_play_session_trash
    obj,_,aggregate=setup();run_id=str(aggregate.run.run_id);request=body(run_id);key=str(uuid4())
    accepted=roll(run_id,request,key)
    commit_plan(str(obj.work_object_id),V2_SOURCE_MARKDOWN+'\n\n'+source(title='Changed'),expected_revision=obj.object_revision)
    assert inventory(world_id=WORLD,run_id=run_id)['tables'][0]['title']=='Weather'
    commit_review(world_id=WORLD,run_id=run_id,command_id=str(uuid4()),request=review_request(run_id))
    assert roll(run_id,request,key)['receipt']==accepted['receipt']
    with pytest.raises(ApplicationStateConflictError):roll(run_id,body(run_id))
    set_world_play_session_trash(world_id=WORLD,run_id=aggregate.run.run_id,expected_revision=2,expected_content_revision=0,restore=False)
    assert roll(run_id,request,key)['receipt']==accepted['receipt']
    with pytest.raises(ApplicationStateConflictError):roll(run_id,body(run_id))


def test_history_pages_and_empty_downgrade(application_state_dsn):
    _,_,aggregate=setup();run_id=str(aggregate.run.run_id)
    for _ in range(3):roll(run_id)
    first=receipts(world_id=WORLD,run_id=run_id,limit=2)
    second=receipts(world_id=WORLD,run_id=run_id,limit=2,before=first['next_before'])
    assert [r['resulting_run_revision'] for r in first['receipts']+second['receipts']]==[4,3,2]
    assert second['next_before'] is None


def test_rebase_refreshes_new_roll_authority_but_not_prior_receipt(application_state_dsn):
    obj,_,aggregate=setup(kind='runbook');run_id=str(aggregate.run.run_id);request=body(run_id);key=str(uuid4())
    accepted=roll(run_id,request,key)
    _,revision=commit_runbook(str(obj.work_object_id),V2_SOURCE_MARKDOWN+'\n\n'+source(title='Later weather'),expected_revision=obj.object_revision)
    rebase_world_play_run(world_id=WORLD,run_id=run_id,expected_run_revision=2,
                          target_playable_revision=revision.revision_n,target_playable_content_sha256=revision.content_sha256)
    assert roll(run_id,request,key)['receipt']==accepted['receipt']
    with pytest.raises(ApplicationStateConflictError):roll(run_id,request)
    fresh=roll(run_id,body(run_id,3))
    assert fresh['receipt']['table_title']=='Later weather'
    assert fresh['receipt']['source']!=accepted['receipt']['source']
    assert fresh['receipt']['outcome']=='Rain'


def test_invalid_saved_table_and_atomic_failure(application_state_dsn,monkeypatch):
    from application_state.play import prepared_table_service as service
    _,_,aggregate=setup();run_id=str(aggregate.run.run_id);request=body(run_id)
    original=service.repo.cas_replace_progress
    def fail_after_cas(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('synthetic failure before ledger insertion')
    monkeypatch.setattr(service.repo,'cas_replace_progress',fail_after_cas)
    with pytest.raises(RuntimeError,match='synthetic failure'):roll(run_id,request)
    monkeypatch.setattr(service.repo,'cas_replace_progress',original)
    assert inventory(world_id=WORLD,run_id=run_id)['run']['run_revision']==1
    assert receipts(world_id=WORLD,run_id=run_id)['receipts']==[]
    _,_,broken=create_source_run(markdown=V2_SOURCE_MARKDOWN+'\n\n'+source(die_sides=True))
    with pytest.raises(ApplicationStateValidationError):inventory(world_id=WORLD,run_id=str(broken.run.run_id))
