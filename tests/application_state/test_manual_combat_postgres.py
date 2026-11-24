"""Versioned manual records at the actual transactional PostgreSQL boundary."""
from copy import deepcopy

import psycopg
import pytest
from psycopg.types.json import Jsonb

from application_state.combat_encounters.manual_encounters import (
    CreateManualEncounterRequest, SaveManualEncounterRequest, ManualParticipant,
)
from application_state.combat_encounters.manual_profiles import initial_actor_values, ManualCombatProfile
from application_state.combat_encounters.service import create_encounter, get_encounter, save_encounter
from application_state.combat_encounters.types import SaveCombatEncounterRequest, CombatEncounterDraft
from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
from tests.test_combat_manual_encounters import profile
from tests.test_combat_scene_templates import scene_case


def create(rules=None):
    return create_encounter(world_id="crossing-world", request=CreateManualEncounterRequest(
        title="Crossing", profile=rules if rules is not None else profile()))


def profile_for(pacing):
    return ManualCombatProfile.model_validate(profile().model_dump(mode='json',by_alias=True)|{'pacing':{'mode':pacing,'rounds':False}})


def test_manual_cold_read_save_cas_and_profile_membership(application_state_dsn):
    record = create()
    draft = deepcopy(record.draft)
    draft.entities.append(ManualParticipant(id="crew", name="Crew", values=initial_actor_values(record.ruleset)))
    stress = draft.entities[0].values.resources["stress"]
    draft.entities[0].values.resources["stress"] = stress.model_copy(update={"current": 0})
    draft.entities[0].participation = "out_of_action"
    draft.entities[0].statuses = ("Pinned",)
    draft.entities[0].notes = "Hold the bridge"
    saved = save_encounter(world_id=record.world_id, encounter_id=record.encounter_id,
        request=SaveManualEncounterRequest(expected_revision=1, draft=draft))
    assert get_encounter(world_id=record.world_id, encounter_id=record.encounter_id) == saved
    assert saved.draft.entities[0].participation == "out_of_action"
    with pytest.raises(ApplicationStateConflictError):
        save_encounter(world_id=record.world_id, encounter_id=record.encounter_id,
            request=SaveManualEncounterRequest(expected_revision=1, draft=draft))
    bad = deepcopy(draft)
    bad.entities[0].values.stats["foreign"] = "Not a declared field"
    with pytest.raises(ApplicationStateValidationError, match="exactly match"):
        save_encounter(world_id=record.world_id, encounter_id=record.encounter_id,
            request=SaveManualEncounterRequest(expected_revision=2, draft=bad))
    assert get_encounter(world_id=record.world_id, encounter_id=record.encounter_id) == saved


def test_manual_refuses_legacy_save_before_mutation(application_state_dsn):
    record = create()
    with pytest.raises(ApplicationStateValidationError, match="version"):
        save_encounter(world_id=record.world_id, encounter_id=record.encounter_id,
            request=SaveCombatEncounterRequest(expected_revision=1, draft=CombatEncounterDraft(title="Wrong")))
    assert get_encounter(world_id=record.world_id, encounter_id=record.encounter_id) == record


def test_canonical_profile_budget_does_not_bypass_actual_jsonb_limit(application_state_dsn):
    from application_state.combat_encounters.manual_profiles import ManualCombatProfile
    from application_state.combat_encounters.service import list_encounters
    rules = ManualCombatProfile(profile_id="crossing", name="Crossing", system_id="crossing",
        stats=[dict(field_id=f"f-{n}",label="名"*80,value_type="text",initial="界"*236) for n in range(32)])
    with pytest.raises(ApplicationStateValidationError, match="PostgreSQL storage limit"):
        create_encounter(world_id="crossing-world",request=CreateManualEncounterRequest(title="Too large",profile=rules))
    assert list_encounters(world_id="crossing-world") == []


@pytest.mark.parametrize("draft_schema", [None, "dmb_combat_encounter_draft_v1", "unknown"])
def test_database_refuses_missing_unknown_and_mixed_versions(application_state_dsn, draft_schema):
    record = create()
    payload = record.draft.model_dump(mode="json", by_alias=True)
    if draft_schema is None:
        del payload["schema"]
    else:
        payload["schema"] = draft_schema
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("UPDATE combat.encounter SET draft=%s WHERE encounter_id=%s", (Jsonb(payload), record.encounter_id))
    assert get_encounter(world_id=record.world_id, encounter_id=record.encounter_id) == record


@pytest.mark.parametrize("pacing", ['ordered','side','spotlight'])
def test_manual_preparation_materialization_scope_save_and_independence(scene_case, pacing):
    from uuid import uuid4
    from application_state.combat_encounters import scene_templates
    from application_state.combat_encounters.scene_template_types import CreateSceneTemplateRequest
    from application_state.play import session_encounters
    from application_state.play.session_encounter_types import MaterializeManualSceneEncounterRequest, RunEncounterScope
    from tests.application_state.test_run_scene_encounters_postgres import request_for
    p=scene_case
    body=deepcopy(p.body)
    rules=profile_for(pacing)
    body['encounter']=CreateManualEncounterRequest(title="Crossing",profile=rules).model_dump(mode="json",by_alias=True)
    view=scene_templates.create(world_id="elderwyld",request=CreateSceneTemplateRequest.model_validate(body))
    draft=deepcopy(view.encounter.draft)
    draft.entities=[ManualParticipant(id="crew",name="Crew",values=initial_actor_values(profile()),notes="Prepared note",statuses=("Pinned",),participation="out_of_action")]
    if pacing=='side':
        from application_state.combat_encounters.manual_encounters import ManualSide, SideTurn
        draft.sides=[ManualSide(id='crew-side',label='Crew'),ManualSide(id='empty-side',label='Empty')]
        draft.entities[0].side_id='crew-side'
        draft.turn=SideTurn(active_side_id='crew-side',acted_actor_ids=['crew'])
    if pacing=='spotlight':
        from application_state.combat_encounters.manual_encounters import SpotlightTurn
        draft.entities.append(ManualParticipant(id='guide',name='Guide',values=initial_actor_values(rules)))
        draft.turn=SpotlightTurn(active_actor_id='guide')
    prepared=save_encounter(world_id="elderwyld",encounter_id=view.encounter.encounter_id,request=SaveManualEncounterRequest(expected_revision=1,draft=draft))
    view=scene_templates.read(world_id="elderwyld",document_id=p.obj.work_object_id,scene_id="scene:gate")
    pin=dict(encounter_id=prepared.encounter_id,revision=2,digest=view.versions[0].digest)
    run_id=uuid4()
    session_encounters.create_session(world_id="elderwyld",run_id=run_id,request=request_for(p,pin))
    preview=session_encounters.preview_encounter(world_id="elderwyld",run_id=run_id,scene_id="scene:gate")
    assert preview['initialization_policy']=='dmb_preserve_manual_preparation_v2'
    request=MaterializeManualSceneEncounterRequest(schema_version='dmb_scene_encounter_materialize_v2',operation_id=uuid4(),expected_preparation_digest=preview['preparation_digest'],template=pin,initialization_policy=preview['initialization_policy'],preview_digest=preview['preview_digest'])
    outcome=session_encounters.materialize_encounter(world_id="elderwyld",run_id=run_id,scene_id="scene:gate",request=request)
    fight=outcome['encounter'];scope=RunEncounterScope(run_id=run_id,scene_id="scene:gate")
    assert fight.draft.entities[0].id!='crew'
    assert fight.draft.entities[0].notes=='Prepared note'
    assert fight.draft.entities[0].participation=='out_of_action'
    if pacing=='side':
        assert fight.draft.turn==SideTurn()
        assert fight.draft.entities[0].side_id==fight.draft.sides[0].id!='crew-side'
        assert fight.draft.sides[1].id!='empty-side'
    if pacing=='spotlight':
        assert fight.draft.turn==SpotlightTurn()
        assert fight.draft.entities[1].id!='guide'
    assert get_encounter(world_id="elderwyld",encounter_id=fight.encounter_id,scope=scope)==fight
    with pytest.raises(ApplicationStateConflictError,match="owning session"):
        get_encounter(world_id="elderwyld",encounter_id=fight.encounter_id)
    changed=deepcopy(fight.draft);changed.entities[0].notes='Run-only note'
    if pacing=='side':
        changed.turn=SideTurn(active_side_id=changed.sides[0].id,acted_actor_ids=[changed.entities[0].id])
    if pacing=='spotlight':
        changed.entities[0].participation='in_action'
        changed.turn=SpotlightTurn(active_actor_id=changed.entities[0].id)
    saved=save_encounter(world_id="elderwyld",encounter_id=fight.encounter_id,scope=scope,request=SaveManualEncounterRequest(expected_revision=1,draft=changed))
    assert saved.revision==2
    assert get_encounter(world_id="elderwyld",encounter_id=prepared.encounter_id)==prepared
    assert scene_templates.read_version(world_id="elderwyld",document_id=p.obj.work_object_id,scene_id="scene:gate",revision=2)==prepared
    assert session_encounters.materialize_encounter(world_id="elderwyld",run_id=run_id,scene_id="scene:gate",request=request)['encounter']==saved


def downgrade_0163(dsn):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    engine=create_engine(dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                import_module('application_state.migrations.versions.20261118_0163_manual_combat_profiles').downgrade()
    finally:
        engine.dispose()


@pytest.mark.parametrize('kind',['template','run'])
def test_cancellation_only_manual_history_refuses_downgrade(scene_case,kind):
    from uuid import uuid4
    from application_state.combat_encounters import scene_templates
    from application_state.combat_encounters.scene_template_types import CreateSceneTemplateRequest
    from application_state.play import session_encounters
    from application_state.play.session_encounter_types import MaterializeManualSceneEncounterRequest
    from tests.application_state.test_run_scene_encounters_postgres import request_for
    p=scene_case
    if kind=='template':
        body=deepcopy(p.body)
        body['encounter']=CreateManualEncounterRequest(title="Crossing",profile=profile()).model_dump(mode="json",by_alias=True)
        scene_templates.cancel(world_id='elderwyld',request=CreateSceneTemplateRequest.model_validate(body))
    else:
        run_id=uuid4()
        session_encounters.create_session(world_id='elderwyld',run_id=run_id,request=request_for(p))
        request=MaterializeManualSceneEncounterRequest(schema_version='dmb_scene_encounter_materialize_v2',operation_id=uuid4(),expected_preparation_digest='sha256:'+'a'*64,
            template=dict(encounter_id=uuid4(),revision=1,digest='sha256:'+'b'*64),initialization_policy='dmb_preserve_manual_preparation_v2',preview_digest='sha256:'+'c'*64)
        session_encounters.cancel_materialization(world_id='elderwyld',run_id=run_id,scene_id='scene:gate',request=request)
    with psycopg.connect(p.dsn) as conn:
        assert conn.execute('SELECT count(*) FROM combat.encounter').fetchone()[0]==0
    with pytest.raises(RuntimeError,match='manual Combat records or history'):
        downgrade_0163(p.dsn)


def test_oversized_template_profile_refuses_atomically(scene_case):
    from application_state.combat_encounters import scene_templates
    from application_state.combat_encounters.scene_template_types import CreateSceneTemplateRequest
    from application_state.combat_encounters.manual_profiles import ManualCombatProfile
    p=scene_case
    rules=ManualCombatProfile(profile_id='crossing',name='Crossing',system_id='crossing',
        stats=[dict(field_id=f'f-{n}',label='名'*80,value_type='text',initial='界'*236) for n in range(32)])
    body=deepcopy(p.body);body['encounter']=CreateManualEncounterRequest(title='Crossing',profile=rules).model_dump(mode='json',by_alias=True)
    with pytest.raises(ApplicationStateValidationError,match='PostgreSQL storage limit'):
        scene_templates.create(world_id='elderwyld',request=CreateSceneTemplateRequest.model_validate(body))
    with psycopg.connect(p.dsn) as conn:
        for table in ('combat.encounter','combat.scene_template','combat.scene_template_version'):
            assert conn.execute('SELECT count(*) FROM '+table).fetchone()[0]==0


def test_serial_0160_through_0166_rehearsal_preserves_legacy_row(
    application_state_dsn, application_state_database, monkeypatch,
):
    import json
    from pathlib import Path
    from alembic import command
    from application_state.cli import alembic_config
    from application_state.config import APPLICATION_STATE_DSN_ENV
    from application_state.combat_encounters import repository
    from application_state.combat_encounters.types import CombatEncounterRecord
    from tests.application_state.conftest import empty_app_state
    with empty_app_state(application_state_database) as dsn:
        with monkeypatch.context() as patch:
            patch.setenv(APPLICATION_STATE_DSN_ENV,dsn)
            config=alembic_config();command.upgrade(config,'20261117_0160')
            fixture=json.loads((Path(__file__).parents[1]/'fixtures/combat/manual-profile-v1-compat.json').read_text())
            legacy=CombatEncounterRecord.model_validate(fixture['api'])
            with psycopg.connect(dsn) as conn:
                repository.insert_encounter(conn,legacy)
            def stored():
                with psycopg.connect(dsn) as conn:
                    return conn.execute('SELECT ruleset_snapshot::text,ruleset_digest,draft::text FROM combat.encounter WHERE encounter_id=%s',(legacy.encounter_id,)).fetchone()
            before=stored()
            for revision in ('20261117_0161','20261118_0162','20261118_0163','20261118_0164','20261118_0165','20261118_0166'):
                command.upgrade(config,revision)
                assert stored()==before
            # Historical storage compatibility is independent of today's head.
            with psycopg.connect(dsn) as conn:
                assert conn.execute('SELECT version_num FROM application_state.schema_migrations').fetchone()[0]=='20261118_0166'
                migrated = repository.get_encounter(
                    conn, world_id=legacy.world_id, encounter_id=legacy.encounter_id)
            assert migrated == legacy
            with pytest.raises(RuntimeError,match='forward recovery'):
                command.downgrade(config,'20261118_0165')
            assert stored()==before
            with psycopg.connect(dsn) as conn:
                assert conn.execute('SELECT version_num FROM application_state.schema_migrations').fetchone()[0]=='20261118_0166'
    # Exercise the public reader on its real current schema, using the
    # actual migrated record. Never spoof the historical schema guard.
    with psycopg.connect(application_state_dsn) as conn:
        repository.insert_encounter(conn, migrated)
    with monkeypatch.context() as current:
        current.setenv(APPLICATION_STATE_DSN_ENV, application_state_dsn)
        assert get_encounter(world_id=legacy.world_id,encounter_id=legacy.encounter_id)==legacy


@pytest.mark.parametrize('pacing',['ordered','side','spotlight'])
def test_manual_http_versions_cas_and_principal_boundary(scene_case,monkeypatch,pacing):
    from tests.test_run_scene_encounters import client_for
    from apps.live_control_server.services import agent_graph_auth
    p=scene_case;client,_=client_for(p,monkeypatch)
    root='/api/live/combat/encounters'
    rules=profile_for(pacing)
    result=client.post(root+'?world_id=elderwyld',json=CreateManualEncounterRequest(title='Crossing',profile=rules).model_dump(mode='json',by_alias=True))
    assert result.status_code==200,result.text
    record=result.json();path=f"{root}/{record['encounter_id']}?world_id=elderwyld"
    assert record['ruleset']['schema']=='dmb_combat_profile_v2'
    assert client.get(path).json()==record
    assert client.get(root+'?world_id=elderwyld').json()==[record]
    draft=deepcopy(record['draft']);draft['entities']=[ManualParticipant(id='crew',name='Crew',values=initial_actor_values(profile())).model_dump(mode='json',by_alias=True)]
    if pacing=='side':
        draft['sides']=[dict(id='crew-side',label='Crew')]
        draft['entities'][0]['side_id']='crew-side'
        draft['turn']=dict(kind='side',active_side_id='crew-side',active_actor_id=None,acted_actor_ids=['crew'])
    if pacing=='spotlight':
        draft['turn']=dict(kind='spotlight',active_actor_id='crew')
    changed=client.put(path,json=dict(expected_revision=1,draft=draft))
    assert changed.status_code==200,changed.text
    assert changed.json()['revision']==2
    assert client.put(path,json=dict(expected_revision=1,draft=draft)).status_code==409
    if pacing=='side':
        invalid=deepcopy(draft);invalid['turn']['active_side_id']='foreign-side'
        assert client.put(path,json=dict(expected_revision=2,draft=invalid)).status_code==422
        assert client.get(path).json()==changed.json()
    if pacing=='spotlight':
        invalid=deepcopy(draft);invalid['turn']['active_actor_id']='foreign-actor'
        assert client.put(path,json=dict(expected_revision=2,draft=invalid)).status_code==422
        assert client.get(path).json()==changed.json()
    draft['entities'][0]['values']['stats']['position']=12
    assert client.put(path,json=dict(expected_revision=2,draft=draft)).status_code==422
    assert client.get(path).json()==changed.json()
    assert client.get(path.replace('elderwyld','foreign-world')).status_code==404
    monkeypatch.setattr(agent_graph_auth,'authenticate_native_graph_principal',lambda _request:agent_graph_auth.NativeGraphPrincipal('player','player','local_session'))
    assert client.get(path).status_code==403
    assert client.put(path,json=dict(expected_revision=2,draft=changed.json()['draft'])).status_code==403


@pytest.mark.parametrize('pacing',['ordered','side','spotlight'])
def test_manual_source_admission_and_ordinary_save_cannot_replace_source(application_state_dsn,pacing):
    from tests.test_combat_manual_encounters import source
    record=create(profile_for(pacing));draft=deepcopy(record.draft);snapshot=source('accepted')
    actor=ManualParticipant(id='crew',name='Crew',values=initial_actor_values(profile()),mechanics_snapshot=snapshot)
    draft.entities=[actor]
    with pytest.raises(ApplicationStateValidationError,match='independently verified'):
        save_encounter(world_id=record.world_id,encounter_id=record.encounter_id,request=SaveManualEncounterRequest(expected_revision=1,draft=draft))
    saved=save_encounter(world_id=record.world_id,encounter_id=record.encounter_id,request=SaveManualEncounterRequest(expected_revision=1,draft=draft),verified_mechanics_snapshots={'crew':snapshot})
    replacement=deepcopy(saved.draft);replacement.entities[0].mechanics_snapshot=None
    with pytest.raises(ApplicationStateValidationError,match='snapshot cannot be changed'):
        save_encounter(world_id=record.world_id,encounter_id=record.encounter_id,request=SaveManualEncounterRequest(expected_revision=2,draft=replacement))
    assert get_encounter(world_id=record.world_id,encounter_id=record.encounter_id)==saved
