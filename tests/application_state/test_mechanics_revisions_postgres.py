"""Real APP admission, concurrent keys, immutable outcomes and reopen."""
from datetime import UTC,datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import pytest
from application_state.errors import ApplicationStateConflictError
from application_state.mechanics_revisions import service
from application_state.mechanics_revisions.types import RevisionOperation,digest
from application_state.world_mechanics.types import MechanicsLocator


def intent():
    origin=MechanicsLocator(provider='dungeonmind',statblock_id='sb_one',revision_id='rev_original',
        contract='dungeonmind.dungeonbuddy-statblocks',contract_version='1.0.0',definition_digest='sha256:'+'a'*64)
    key=uuid4();draft=uuid4();body=dict(idempotency_key=str(key),parent_revision_id=origin.revision_id,definition={},change_summary='Edited')
    submitted=dict(operation_id=str(key),world_id='elderwyld',base=origin.model_dump(mode='json'),definition={},change_summary='Edited')
    now=datetime.now(UTC)
    return RevisionOperation(operation_id=key,world_id='elderwyld',draft_id=draft,origin=origin,base=origin,
        origin_acceptance_operation_id=str(uuid4()),input_digest=digest(submitted),request_body=body,request_digest=digest(body),
        definition_digest='sha256:'+'b'*64,created_at=now,updated_at=now)


def test_claim_replay_key_fence_unknown_terminal_and_reopen(application_state_dsn):
    record=intent();claimed,fresh=service.claim(record);assert fresh
    assert service.claim(record)==(claimed,False)
    body=record.request_body|dict(change_summary='Changed')
    submitted=dict(operation_id=str(record.operation_id),world_id=record.world_id,base=record.base.model_dump(mode='json'),definition={},change_summary='Changed')
    changed=record.model_copy(update={'request_body':body,'request_digest':digest(body),'input_digest':digest(submitted)})
    with pytest.raises(ApplicationStateConflictError):service.claim(changed)
    with pytest.raises(ApplicationStateConflictError):service.read(world_id='other',draft_id=record.draft_id,operation_id=record.operation_id)
    unknown=service.settle(record,state='outcome_unknown')
    assert service.unresolved(world_id=record.world_id,draft_id=record.draft_id).operation_id==unknown.operation_id
    result=record.origin.model_copy(update={'revision_id':'rev_second','definition_digest':record.definition_digest})
    committed=service.settle(unknown,state='committed',result=result)
    assert service.settle(unknown,state='committed',result=result)==committed
    assert service.read(world_id=record.world_id,draft_id=record.draft_id,operation_id=record.operation_id)==committed
    page=service.list_operations(world_id=record.world_id,draft_id=record.draft_id)
    assert page[0].operation_id==committed.operation_id and 'request_body' not in page[0].model_dump()
    with pytest.raises(ApplicationStateConflictError):service.settle(record,state='refused',refusal_code='stale_parent_revision')


@pytest.mark.parametrize('same_key',[True,False])
def test_two_writers_have_one_active_intent(application_state_dsn,same_key):
    first=intent();second=first if same_key else intent();barrier=Barrier(2)
    def write(record):
        barrier.wait(timeout=5)
        try:return service.claim(record)
        except ApplicationStateConflictError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(write,[first,second]))
    if same_key:assert sorted(result[1] for result in results)==[False,True]
    else:assert sum(result is not None for result in results)==1


def test_populated_downgrade_refuses_discarding_recovery(application_state_dsn):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    service.claim(intent())
    engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError,match='retained mechanics revision'):
                    import_module('application_state.migrations.versions.20261022_0049_mechanics_revision_operations').downgrade()
    finally:engine.dispose()


def test_absent_recovery_fences_a_later_preflight_claim(application_state_dsn):
    record=intent()
    assert service.cancel_if_absent(world_id=record.world_id,draft_id=record.draft_id,operation_id=record.operation_id) is None
    with pytest.raises(ApplicationStateConflictError,match='canceled before dispatch'):service.claim(record)
    assert service.cancel_if_absent(world_id=record.world_id,draft_id=record.draft_id,operation_id=record.operation_id) is None


def test_recovery_does_not_cancel_a_committed_claim(application_state_dsn):
    record=intent();service.claim(record)
    assert service.cancel_if_absent(world_id=record.world_id,draft_id=record.draft_id,operation_id=record.operation_id)==record


def test_sql_rejects_null_discriminator_without_corrupting_the_operation(application_state_dsn):
    import psycopg
    record=intent();service.claim(record)
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE mechanics_revision.operation SET payload=jsonb_set(payload,'{schema}','null'::jsonb) WHERE operation_id=%s",(record.operation_id,))
    assert service.read(world_id=record.world_id,draft_id=record.draft_id,operation_id=record.operation_id)==record
