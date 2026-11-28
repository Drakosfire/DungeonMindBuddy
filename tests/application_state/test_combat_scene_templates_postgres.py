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


def test_prepare_exact_saved_encounter_leaves_original_and_replays(scene_case):
    from application_state.combat_encounters import service as encounters
    from application_state.combat_encounters.types import CreateCombatEncounterRequest, SaveCombatEncounterRequest

    world_id = "elderwyld"
    source = encounters.create_encounter(
        world_id=world_id, request=CreateCombatEncounterRequest(title="Bath House roster"),
    )
    source = encounters.save_encounter(
        world_id=world_id,
        encounter_id=source.encounter_id,
        request=SaveCombatEncounterRequest(
            expected_revision=source.revision, draft=source.draft.model_copy(update={"title": "Bath House reserves"}),
        ),
    )
    body = {
        **scene_case.body,
        "encounter": {
            "schema_version": "dmb_scene_template_copy_saved_v1",
            "source_encounter_id": str(source.encounter_id),
            "expected_revision": source.revision - 1,
        },
    }
    with pytest.raises(ApplicationStateConflictError, match="saved Combat encounter changed"):
        service.create(world_id=world_id, request=CreateSceneTemplateRequest.model_validate(body))
    assert read(scene_case).json() is None

    body["encounter"]["expected_revision"] = source.revision
    request = CreateSceneTemplateRequest.model_validate(body)
    prepared = service.create(world_id=world_id, request=request)
    assert prepared.encounter.encounter_id != source.encounter_id
    assert prepared.encounter.revision == 1
    assert prepared.encounter.draft == source.draft
    assert prepared.encounter.ruleset_digest == source.ruleset_digest
    assert len(prepared.versions) == 1
    assert service.create(world_id=world_id, request=request) == prepared
    assert encounters.get_encounter(world_id=world_id, encounter_id=source.encounter_id) == source

    second = request.model_copy(update={"operation_id": uuid4()})
    with pytest.raises(ApplicationStateConflictError, match="scene already has an encounter"):
        service.create(world_id=world_id, request=second)


def copy_intent(scene_case, source_id, revision):
    return CreateSceneTemplateRequest.model_validate({
        **scene_case.body,
        "encounter": {
            "schema_version": "dmb_scene_template_copy_saved_v1",
            "source_encounter_id": source_id,
            "expected_revision": revision,
        },
    })


def test_copy_preserves_grouped_actors_and_exact_mechanics(scene_case, adoption_case):
    from application_state.combat_encounters.service import get_encounter

    world_id = "elderwyld"
    source = get_encounter(world_id=world_id, encounter_id=adoption_case.before["encounter_id"])
    assert len(source.draft.entities) == 2
    assert source.draft.groups
    assert all(actor.mechanics_snapshot for actor in source.draft.entities)
    request = copy_intent(scene_case, source.encounter_id, source.revision)
    prepared = service.create(world_id=world_id, request=request)
    assert prepared.encounter.draft == source.draft
    assert prepared.encounter.ruleset == source.ruleset
    assert get_encounter(world_id=world_id, encounter_id=source.encounter_id) == source


def test_copy_manual_profile_authorization_and_cancel(scene_case):
    from application_state.combat_encounters.manual_encounters import CreateManualEncounterRequest
    from application_state.combat_encounters.service import create_encounter
    from tests.test_combat_manual_encounters import profile

    world_id = "elderwyld"
    source = create_encounter(world_id=world_id, request=CreateManualEncounterRequest(
        title="Bath House clocks", profile=profile(),
    ))
    request = copy_intent(scene_case, source.encounter_id, source.revision)

    def deny():
        raise PermissionError("Write denied")

    with pytest.raises(PermissionError, match="Write denied"):
        service.create(world_id=world_id, request=request, authorize=deny)
    assert read(scene_case).json() is None
    assert service.cancel(world_id=world_id, request=request)["state"] == "canceled"
    with pytest.raises(ApplicationStateConflictError, match="canceled"):
        service.create(world_id=world_id, request=request)
    assert read(scene_case).json() is None

    retry = request.model_copy(update={"operation_id": uuid4()})
    prepared = service.create(world_id=world_id, request=retry)
    assert prepared.encounter.draft == source.draft
    assert prepared.encounter.ruleset == source.ruleset


def test_copy_refuses_foreign_source(scene_case):
    from application_state.combat_encounters.service import create_encounter
    from application_state.combat_encounters.types import CreateCombatEncounterRequest
    from application_state.errors import ApplicationStateNotFoundError

    foreign = create_encounter(world_id="other-world", request=CreateCombatEncounterRequest(title="Foreign"))
    with pytest.raises(ApplicationStateNotFoundError, match="unavailable"):
        service.create(world_id="elderwyld", request=copy_intent(scene_case, foreign.encounter_id, foreign.revision))
    assert read(scene_case).json() is None


def test_copy_refuses_run_instance(scene_case):
    from application_state.content.service import commit_plan, create_world_plan
    from application_state.errors import ApplicationStateNotFoundError
    from application_state.play.session_encounters import materialize_encounter
    from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN
    from tests.application_state.test_run_scene_encounters_postgres import materialization_case

    world_id = "elderwyld"
    run_id, initial, _ = materialization_case(scene_case)
    fight = materialize_encounter(
        world_id=world_id, run_id=run_id, scene_id="scene:gate", request=initial,
    )["encounter"]
    plan = create_world_plan(title="Unoccupied preparation", world_id=world_id)
    plan, saved = commit_plan(
        str(plan.work_object_id), V2_SOURCE_MARKDOWN,
        expected_world_id=world_id, expected_revision=plan.object_revision,
    )
    request = copy_intent(scene_case, fight.encounter_id, fight.revision)
    target = request.pin.model_copy(update={
        "document_id": plan.work_object_id, "revision_n": saved.revision_n,
        "work_revision_id": saved.work_revision_id, "content_sha256": saved.content_sha256,
    })
    with pytest.raises(ApplicationStateNotFoundError, match="unavailable"):
        service.create(world_id=world_id, request=request.model_copy(update={"pin": target, "operation_id": uuid4()}))
    assert service.read(world_id=world_id, document_id=plan.work_object_id, scene_id="scene:gate") is None


def test_deleted_statblock_is_removed_from_scene_history_under_original_pin(scene_case, adoption_case):
    from types import SimpleNamespace
    from uuid import UUID

    from application_state.combat_encounters.service import get_encounter
    from application_state.errors import ApplicationStateConflictError
    from application_state.mechanics_revisions import purge
    from application_state.unit_of_work import unit_of_work

    p = adoption_case
    world_id = "elderwyld"
    source = get_encounter(world_id=world_id, encounter_id=p.before["encounter_id"])
    request = copy_intent(scene_case, source.encounter_id, source.revision)
    template = service.create(world_id=world_id, request=request)
    start = template.versions[0]
    pin = SimpleNamespace(encounter_id=template.binding.encounter_id, revision=start.revision, digest=start.digest)
    scope = dict(world_id=world_id, document_id=request.pin.document_id, scene_id=request.pin.scene_id)
    target = purge.PurgeTarget(
        p.original["locator"]["statblock_id"], world_id, UUID(p.draft.draft_id),
        p.draft.version, p.locator["revision_id"],
    )
    assert purge.claim(target, authorize=lambda: None) is False
    with pytest.raises(ApplicationStateConflictError, match="being deleted"):
        service.read_version(**scope, revision=start.revision)

    purge.remove_current_combat_copies(target)
    reopened = service.read_version(**scope, revision=start.revision)
    assert reopened.draft.groups == source.draft.groups
    assert all(actor.mechanics_snapshot is None and actor.deleted_mechanics for actor in reopened.draft.entities)
    with unit_of_work() as conn:
        assert service.read_snapshot(conn, **scope, pin=pin) == reopened
        digest, payload, redacted_digest = conn.execute("""
            SELECT digest, payload, redacted_digest FROM combat.scene_template_version
            WHERE encounter_id=%s AND revision=%s
        """, (pin.encounter_id, pin.revision)).fetchone()
    assert digest == pin.digest
    assert redacted_digest == service.digest(payload)
    assert all(actor["mechanics_snapshot"] is None for actor in payload["draft"]["entities"])
    purge.remove_current_combat_copies(target)
    assert service.read_version(**scope, revision=start.revision) == reopened
