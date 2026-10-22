from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest

from application_state.errors import ApplicationStateConflictError
from application_state.world_mechanics import service
from application_state.world_mechanics.types import (
    AcceptedMechanicsProof, AssociateWorldMechanicsRequest, WorldMechanicsTarget,
)


def request(**changes):
    body = dict(request_id=uuid4(), draft_id=uuid4(), expected_draft_version=3,
                expected_version=0, target=WorldMechanicsTarget(
                    managed_world_id="elderwyld", native_world_id="world:opaque", binding_version=1,
                    graph_revision_id="rev:head", node_id="node:keeper", label="Keeper",
                    kind="npc", role="", campaign_scope=None))
    return AssociateWorldMechanicsRequest(**(body | changes))


def proof():
    return AcceptedMechanicsProof(locator=dict(provider="dungeonmind",statblock_id="sb_one",revision_id="rev_exact",
        contract="dungeonmind.dungeonbuddy-statblocks",contract_version="1.0.0",definition_digest="sha256:"+"a"*64),
        acceptance_operation_id=str(uuid4()),accepted_from_draft_version=2,
        accepted_from_candidate_id="cand_one",acceptance_request_digest="sha256:"+"b"*64)


def test_append_replay_replace_history_scope_and_reopen(application_state_dsn):
    body=request(); accepted=proof()
    first=service.append_verified(request=body,proof=accepted,actor="gm")
    assert first.replayed is False and first.association.version==1
    assert service.replay(body)==first.association
    assert service.append_verified(request=body,proof=proof(),actor="other-gm").association==first.association
    second_body=body.model_copy(update={"request_id":uuid4(),"expected_version":1})
    second=service.append_verified(request=second_body,proof=accepted,actor="gm")
    assert second.association.version==2
    assert second.association.previous_association_id==first.association.association_id
    assert service.list_current(world_id="elderwyld")==[second.association]
    assert service.list_current(world_id="other-world")==[]
    # Historical same-key acknowledgement does not claim current usability.
    assert service.replay(body)==first.association
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM world_mechanics.association').fetchone()[0]==2


def test_same_key_different_body_and_stale_slot_cannot_append(application_state_dsn):
    body=request();service.append_verified(request=body,proof=proof(),actor="gm")
    changed=body.model_copy(update={"expected_draft_version":4})
    with pytest.raises(ApplicationStateConflictError):service.replay(changed)
    with pytest.raises(ApplicationStateConflictError):service.append_verified(request=changed,proof=proof(),actor="gm")
    with pytest.raises(ApplicationStateConflictError):service.append_verified(request=request(),proof=proof(),actor="gm")
    assert len(service.list_current(world_id="elderwyld"))==1


@pytest.mark.parametrize("same_key",[False,True])
def test_concurrent_writes_have_one_durable_winner(application_state_dsn,same_key):
    first=request(); second=first if same_key else request(); barrier=Barrier(2)
    def write(body):
        barrier.wait(timeout=5)
        try:return service.append_verified(request=body,proof=proof(),actor="gm")
        except ApplicationStateConflictError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(write,[first,second]))
    if same_key:
        assert results[0].association==results[1].association
        assert sorted(r.replayed for r in results)==[False,True]
    else:assert sum(r is not None for r in results)==1
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM world_mechanics.association').fetchone()[0]==1


def test_additive_migration_preserves_encounters_and_refuses_populated_downgrade(application_state_dsn):
    from alembic import command
    from application_state.cli import alembic_config, assert_at_head
    from application_state.combat_encounters.service import create_encounter,get_encounter
    from application_state.combat_encounters.types import CreateCombatEncounterRequest
    encounter=create_encounter(world_id="elderwyld",request=CreateCombatEncounterRequest(title="Retained fight"))
    command.downgrade(alembic_config(),"20261020_0042")
    command.upgrade(alembic_config(),"head")
    assert get_encounter(world_id="elderwyld",encounter_id=encounter.encounter_id)==encounter
    service.append_verified(request=request(),proof=proof(),actor="gm")
    with pytest.raises(RuntimeError,match="Cannot downgrade"):
        command.downgrade(alembic_config(),"20261020_0042")
    assert_at_head(dsn=application_state_dsn)
    assert len(service.list_current(world_id="elderwyld"))==1
