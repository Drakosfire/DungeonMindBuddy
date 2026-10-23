"""Retained history, cancellation races and migration refusal at the APP boundary."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event
from uuid import uuid4
import pytest
from tests.test_combat_scene_templates import scene_case,create,read
from application_state.combat_encounters import scene_templates as service
from application_state.combat_encounters.scene_template_types import CreateSceneTemplateRequest
from application_state.errors import ApplicationStateConflictError


def test_cancel_before_create_fences_late_request_and_changed_body(scene_case):
    p=scene_case;request=CreateSceneTemplateRequest.model_validate(p.body)
    canceled=service.cancel(world_id='elderwyld',request=request);assert canceled['state']=='canceled'
    assert service.cancel(world_id='elderwyld',request=request)==canceled
    with pytest.raises(ApplicationStateConflictError,match='canceled'):service.create(world_id='elderwyld',request=request)
    body=deepcopy(p.body);body['encounter']['title']='Other intent'
    with pytest.raises(ApplicationStateConflictError,match='different intent'):service.cancel(world_id='elderwyld',request=CreateSceneTemplateRequest.model_validate(body))
    assert read(p).json() is None


def test_commit_before_cancel_returns_applied_and_retains_one_snapshot(scene_case):
    p=scene_case;before=create(p).json();result=service.cancel(world_id='elderwyld',request=CreateSceneTemplateRequest.model_validate(p.body))
    assert result['state']=='applied' and str(result['view'].binding.encounter_id)==before['binding']['encounter_id']
    assert len(read(p).json()['versions'])==1


def test_inflight_creation_and_cancel_have_one_terminal_outcome(scene_case,monkeypatch):
    p=scene_case;entered=Event();release=Event();original=service.append_version
    def paused(conn,record):
        entered.set();assert release.wait(10);return original(conn,record)
    monkeypatch.setattr(service,'append_version',paused)
    request=CreateSceneTemplateRequest.model_validate(p.body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        creating=pool.submit(service.create,world_id='elderwyld',request=request)
        assert entered.wait(10)
        canceling=pool.submit(service.cancel,world_id='elderwyld',request=request)
        release.set();created=creating.result(10);result=canceling.result(10)
    assert result['state']=='applied' and result['view'].binding==created.binding
    assert len(read(p).json()['versions'])==1


def test_retained_template_blocks_destructive_downgrade(scene_case):
    p=scene_case;assert create(p).status_code==200
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    engine=create_engine(p.dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError,match='Cannot discard retained'):
                    import_module('application_state.migrations.versions.20261022_0051_combat_scene_templates').downgrade()
    finally:engine.dispose()


def test_adoption_and_generic_save_share_template_history(adoption_case,monkeypatch):
    # Existing exact producer/HTTP fixture; only synthetic resources are used.
    from tests.test_combat_mechanics_adoption import apply
    from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN
    from application_state.content.service import create_world_plan,commit_plan
    from application_state.combat_encounters.types import SaveCombatEncounterRequest,AcceptedCombatMechanicsSnapshot
    from application_state.combat_encounters.service import save_encounter
    p=adoption_case;obj=create_world_plan(title='Adoption template',world_id='elderwyld')
    obj,rev=commit_plan(str(obj.work_object_id),V2_SOURCE_MARKDOWN,expected_world_id='elderwyld',expected_revision=obj.object_revision)
    request=CreateSceneTemplateRequest(operation_id=uuid4(),pin=dict(document_id=obj.work_object_id,scene_id='scene:gate',revision_n=rev.revision_n,work_revision_id=rev.work_revision_id,content_sha256=rev.content_sha256),encounter={'title':'Template actor'})
    view=service.create(world_id='elderwyld',request=request)
    # Use the same public service and independent snapshot verifier as normal Save.
    before=save_encounter(world_id='elderwyld',encounter_id=view.binding.encounter_id,request=SaveCombatEncounterRequest(expected_revision=1,draft=p.before['draft']),verified_mechanics_snapshots={actor['id']: AcceptedCombatMechanicsSnapshot.model_validate(actor['mechanics_snapshot']) for actor in p.before['draft']['entities']})
    original=service.read_version(world_id='elderwyld',document_id=obj.work_object_id,scene_id='scene:gate',revision=2)
    p.intent['expected_revision']=before.revision
    p.adopt_url=f'/api/live/combat/encounters/{before.encounter_id}/mechanics-adoptions?world_id=elderwyld'
    result=apply(p);assert result.status_code==200,result.text
    latest=service.read(world_id='elderwyld',document_id=obj.work_object_id,scene_id='scene:gate')
    assert [version.revision for version in latest.versions]==[3,2,1]
    assert service.read_version(world_id='elderwyld',document_id=obj.work_object_id,scene_id='scene:gate',revision=2)==original
    assert original.draft.entities[0].mechanics_snapshot!=latest.encounter.draft.entities[0].mechanics_snapshot
    from apps.live_control_server.services import combat_mechanics
    monkeypatch.setattr(combat_mechanics,'build_statblock_v1_client',lambda:(_ for _ in ()).throw(RuntimeError('Producer offline')))
    assert service.read_version(world_id='elderwyld',document_id=obj.work_object_id,scene_id='scene:gate',revision=2)==original
    assert apply(p).status_code==200
    assert len(service.read(world_id='elderwyld',document_id=obj.work_object_id,scene_id='scene:gate').versions)==3

from tests.test_world_mechanics_associations import prepared
from tests.test_statblock_saved_revisions import revision_case
from tests.test_combat_mechanics_adoption import adoption_case
