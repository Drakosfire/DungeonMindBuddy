"""Owning transaction rollback and retained terminal receipt constraints."""
import pytest
from tests.test_world_mechanics_associations import prepared
from tests.test_statblock_saved_revisions import revision_case
from tests.test_combat_mechanics_adoption import adoption_case,apply
from application_state.combat_encounters import adoption


def test_receipt_failure_rolls_back_actor_cas(adoption_case,monkeypatch):
    p=adoption_case
    def fail(*args):raise RuntimeError('Receipt storage unavailable')
    monkeypatch.setattr(adoption,'_insert',fail)
    with pytest.raises(RuntimeError,match='Receipt storage unavailable'):apply(p)
    assert p.client.get(p.encounter_url).json()==p.before
    assert adoption.inspect(world_id='elderwyld',encounter_id=p.before['encounter_id'],operation_id=p.intent['operation_id']) is None


def test_retained_receipt_prevents_destructive_downgrade(adoption_case,application_state_dsn):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    p=adoption_case;result=apply(p);assert result.status_code==200,result.text
    engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError,match='Cannot discard retained mechanics adoption history'):
                    import_module('application_state.migrations.versions.20261022_0050_combat_mechanics_adoption').downgrade()
    finally:engine.dispose()


def test_sql_rejects_null_receipt_discriminator(adoption_case,application_state_dsn):
    import psycopg
    p=adoption_case;assert apply(p).status_code==200
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE combat.mechanics_adoption SET payload=jsonb_set(payload,'{schema}','null'::jsonb)")
    assert adoption.inspect(world_id='elderwyld',encounter_id=p.before['encounter_id'],operation_id=p.intent['operation_id']).receipt.state=='applied'


@pytest.mark.parametrize('damage',['predecessor','target'])
def test_exact_historical_receipt_rejects_changed_target_or_broken_chain(adoption_case,application_state_dsn,damage):
    from uuid import uuid4
    import psycopg
    from psycopg.types.json import Jsonb
    from tests.test_world_mechanics_associations import post
    from application_state.combat_encounters.types import CombatMechanicsSnapshot,CombatWorldIdentity
    p=adoption_case
    first=post(p);assert first.status_code==200,first.text
    second_body={**p.body,'request_id':str(uuid4()),'expected_version':1}
    second=post(p,second_body);assert second.status_code==200,second.text
    association=second.json()['association']
    payload=dict(association_id=association['association_id'],association_version=2,target=p.body['target'],locator=p.original['locator'],resource=p.original['resource'])
    snapshot=CombatMechanicsSnapshot(**payload,snapshot_digest=CombatMechanicsSnapshot.digest_payload(payload))
    if damage=='predecessor':association['previous_association_id']=association['association_id']
    else:
        from application_state.world_mechanics.types import AssociateWorldMechanicsRequest
        association['request']['target']['label']='Different keeper'
        association['request_digest']=AssociateWorldMechanicsRequest.model_validate(association['request']).digest
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute('UPDATE world_mechanics.association SET payload=%s,previous_association_id=%s WHERE association_id=%s',(Jsonb(association),association['previous_association_id'],association['association_id']))
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(Exception,match='Historical mechanics association|Actor differs'):
            adoption._historical_association(conn,'elderwyld',snapshot)
