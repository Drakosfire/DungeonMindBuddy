"""APP-owned Plan scene preparation, exact creation replay and version history."""
from datetime import UTC, datetime
from typing import Callable
from uuid import UUID, uuid4
import hashlib
import json
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.unit_of_work import unit_of_work
from application_state.content import repository as content_repo
from application_state.content.playable_admission import admit_playable_revision
from application_state.combat_encounters import repository as repo
from application_state.combat_encounters.rulesets import load_ruleset, ruleset_digest
from application_state.combat_encounters.service import _world_id, _require_integrity
from application_state.combat_encounters.types import CombatEncounterDraft, CombatEncounterRecord
from application_state.combat_encounters.manual_encounters import CreateManualEncounterRequest, ManualEncounterRecord, empty_manual_draft, decode_combat_record
from application_state.combat_encounters.manual_profiles import manual_profile_digest
from application_state.combat_encounters.scene_template_types import (
    CopySavedEncounterRequest, CreateSceneTemplateRequest, SceneTemplateBinding, SceneTemplateView, TemplateVersion,
)
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError, ApplicationStateNotFoundError, ApplicationStateValidationError
from apps.live_control_server.services.play_run_edition_structure import structure_signature


def digest(payload):
    return "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def append_version(conn, record):
    """Called inside the encounter mutation transaction, never after commit."""
    if conn.execute("SELECT 1 FROM combat.scene_template WHERE encounter_id=%s AND world_id=%s", (record.encounter_id,record.world_id)).fetchone() is None:
        return
    payload = record.model_dump(mode="json")
    conn.execute("""INSERT INTO combat.scene_template_version(encounter_id,revision,digest,saved_at,payload)
        VALUES(%s,%s,%s,%s,%s)""", (record.encounter_id,record.revision,digest(payload),record.updated_at,Jsonb(payload)))


def redact_saved_versions(conn, *, world_id: str, statblock_id: str) -> None:
    from application_state.mechanics_revisions.purge import redact_combat_draft

    pattern = {"draft": {"entities": [{"mechanics_snapshot": {"locator": {"statblock_id": statblock_id}}}]}}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT version.* FROM combat.scene_template_version AS version
            JOIN combat.scene_template AS owner USING (encounter_id)
            WHERE owner.world_id=%s AND version.payload @> %s
            ORDER BY version.encounter_id, version.revision FOR UPDATE OF version
        """, (world_id, Jsonb(pattern)))
        versions = cur.fetchall()
    for version in versions:
        current = version["payload"]
        if digest(current) != (version["redacted_digest"] or version["digest"]):
            raise ApplicationStateIntegrityError("Prepared encounter version digest is invalid")
        record = decode_combat_record(current)
        if (record.world_id, record.encounter_id, record.revision) != (
            world_id, version["encounter_id"], version["revision"],
        ):
            raise ApplicationStateIntegrityError("Prepared encounter snapshot identity is invalid")
        updated = record.model_copy(update={"draft": redact_combat_draft(record.draft, statblock_id)})
        payload = updated.model_dump(mode="json", by_alias=True)
        conn.execute("""
            UPDATE combat.scene_template_version SET payload=%s, redacted_digest=%s
            WHERE encounter_id=%s AND revision=%s
        """, (Jsonb(payload), digest(payload), record.encounter_id, record.revision))


def _scene_ids(markdown):
    try:
        return {scene["scene_id"] for scene in structure_signature(markdown)["membership"]["scenes"]}
    except ValueError as exc:
        raise ApplicationStateValidationError("Plan needs valid current scene markers before preparing an encounter") from exc


def _binding(row):
    binding=SceneTemplateBinding.model_validate(row["payload"])
    if (binding.world_id,binding.encounter_id,binding.origin.document_id,binding.origin.scene_id,binding.operation_id,binding.request_digest) != (row["world_id"],row["encounter_id"],row["document_id"],row["scene_id"],row["operation_id"],row["request_digest"]):
        raise ApplicationStateIntegrityError("Scene template identity differs from its retained binding")
    request=CreateSceneTemplateRequest.model_validate(row['request'])
    if request.pin!=binding.origin or request.operation_id!=binding.operation_id or digest({'world_id':binding.world_id,'request':row['request']})!=binding.request_digest:
        raise ApplicationStateIntegrityError("Scene template creation proof is invalid")
    return binding


def _row(conn, sql, params):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def _present(conn,binding):
    obj=content_repo.get_work_object(conn,binding.origin.document_id)
    if obj is None or obj.world_id!=binding.world_id or obj.kind!='plan' or obj.campaign_id is not None:
        raise ApplicationStateConflictError("Selected World does not own this Plan template")
    if obj.status!='active' or obj.current_revision_id is None:
        return False
    revision=content_repo.get_work_revision(conn,obj.current_revision_id)
    if revision is None:
        raise ApplicationStateIntegrityError("Plan committed revision is missing")
    if revision.work_object_id!=obj.work_object_id or revision.world_id!=binding.world_id or hashlib.sha256(revision.markdown.encode()).hexdigest()!=revision.content_sha256:
        raise ApplicationStateIntegrityError('Plan committed revision identity/digest is invalid')
    try:
        return binding.origin.scene_id in _scene_ids(revision.markdown)
    except ApplicationStateValidationError:
        return False


def _view(conn,binding):
    conn.execute("SELECT encounter_id FROM combat.encounter WHERE encounter_id=%s AND world_id=%s FOR SHARE",(binding.encounter_id,binding.world_id))
    encounter=repo.get_encounter(conn,world_id=binding.world_id,encounter_id=binding.encounter_id)
    if encounter is None:
        raise ApplicationStateIntegrityError("Scene template encounter is missing")
    _require_integrity(encounter)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT revision,digest,saved_at FROM combat.scene_template_version WHERE encounter_id=%s ORDER BY revision DESC",(binding.encounter_id,))
        versions=[TemplateVersion.model_validate(row) for row in cur.fetchall()]
    if not versions or versions[0].revision!=encounter.revision:
        raise ApplicationStateIntegrityError("Scene template history is incomplete")
    return SceneTemplateView(binding=binding,encounter=encounter,versions=versions,scene_present=_present(conn,binding))


def _require_available_encounter_mechanics(conn, record) -> None:
    from application_state.mechanics_revisions.purge import require_available_statblocks

    require_available_statblocks(conn, (
        actor.mechanics_snapshot.locator.statblock_id
        for actor in record.draft.entities if actor.mechanics_snapshot is not None
    ))


def _copy_saved_encounter(conn, *, world_id, request, now):
    source_id = request.source_encounter_id
    # Take statblock locks before the source row lock, matching deletion order.
    observed = repo.get_encounter(conn, world_id=world_id, encounter_id=source_id)
    if observed is not None:
        _require_available_encounter_mechanics(conn, observed)
    owned = _row(conn, """
        SELECT source.encounter_id
        FROM combat.encounter AS source
        WHERE source.encounter_id = %s AND source.world_id = %s
          AND NOT EXISTS (
              SELECT 1 FROM combat.scene_template WHERE encounter_id = source.encounter_id
          )
          AND NOT EXISTS (
              SELECT 1 FROM combat.run_scene_encounter WHERE encounter_id = source.encounter_id
          )
        FOR SHARE OF source
        """, (source_id, world_id))
    if owned is None:
        raise ApplicationStateNotFoundError("Saved Combat encounter is unavailable")
    source = repo.get_encounter(conn, world_id=world_id, encounter_id=source_id)
    if source is None:
        raise ApplicationStateIntegrityError("Locked Combat encounter is missing")
    _require_integrity(source)
    if source.revision != request.expected_revision or observed is None or source.revision != observed.revision:
        raise ApplicationStateConflictError("The saved Combat encounter changed; review its current revision")
    return type(source).model_validate({
        **source.model_dump(mode="json", by_alias=True),
        "encounter_id": uuid4(),
        "campaign_id": None,
        "session": None,
        "revision": 1,
        "created_at": now,
        "updated_at": now,
    })


def create(*,world_id,request:CreateSceneTemplateRequest,authorize: Callable[[], None] | None = None):
    world_id=_world_id(world_id)
    copying = isinstance(request.encounter, CopySavedEncounterRequest)
    if not copying and (request.encounter.campaign_id is not None or request.encounter.session is not None):
        raise ApplicationStateValidationError("Plan encounter templates cannot claim campaign/session ownership")
    body=request.model_dump(mode="json");request_digest=digest({"world_id":world_id,"request":body})
    dsn=load_runtime_dsn();assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",('scene-template:'+str(request.operation_id),))
        canceled=_row(conn,"SELECT * FROM combat.scene_template_cancellation WHERE operation_id=%s",(request.operation_id,))
        if canceled is not None:
            if canceled['world_id']!=world_id or canceled['request_digest']!=request_digest or canceled['request']!=body:
                raise ApplicationStateConflictError("Scene encounter creation key already has a different intent")
            raise ApplicationStateConflictError("Scene encounter creation was canceled; it cannot commit")
        existing=_row(conn,"SELECT * FROM combat.scene_template WHERE operation_id=%s",(request.operation_id,))
        if existing is not None:
            if existing['request_digest']!=request_digest or existing['request']!=body:
                raise ApplicationStateConflictError("Scene encounter creation key already has a different intent")
            return _view(conn,_binding(existing))
        pin=request.pin
        admitted=admit_playable_revision(conn,pin.document_id,pin.revision_n,pin.content_sha256,expected_world_id=world_id,require_current=True,require_clean=True)
        if admitted.work_object.kind!='plan' or admitted.work_revision.work_revision_id!=pin.work_revision_id:
            raise ApplicationStateConflictError("Scene encounter requires the exact current saved Plan")
        if pin.scene_id not in _scene_ids(admitted.work_revision.markdown):
            raise ApplicationStateConflictError("The selected scene is not in the saved Plan")
        if _row(conn,"SELECT encounter_id FROM combat.scene_template WHERE world_id=%s AND document_id=%s AND scene_id=%s",(world_id,pin.document_id,pin.scene_id)):
            raise ApplicationStateConflictError("This scene already has an encounter; reopen it instead of creating another")
        now=datetime.now(UTC)
        if isinstance(request.encounter, CopySavedEncounterRequest):
            record = _copy_saved_encounter(conn, world_id=world_id, request=request.encounter, now=now)
        elif isinstance(request.encounter, CreateManualEncounterRequest):
            profile=request.encounter.profile
            record=ManualEncounterRecord(encounter_id=uuid4(),world_id=world_id,revision=1,ruleset=profile,ruleset_digest=manual_profile_digest(profile),draft=empty_manual_draft(profile,request.encounter.title),created_at=now,updated_at=now)
        else:
            try:
                ruleset=load_ruleset(request.encounter.ruleset_id)
            except ValueError as exc:
                raise ApplicationStateValidationError(str(exc)) from exc
            record=CombatEncounterRecord(encounter_id=uuid4(),world_id=world_id,revision=1,ruleset=ruleset,ruleset_digest=ruleset_digest(ruleset),draft=CombatEncounterDraft(title=request.encounter.title),created_at=now,updated_at=now)
        if authorize is not None:
            authorize()
        repo.insert_encounter(conn,record)
        binding=SceneTemplateBinding(world_id=world_id,encounter_id=record.encounter_id,origin=pin,operation_id=request.operation_id,request_digest=request_digest,created_at=now)
        conn.execute("""INSERT INTO combat.scene_template(encounter_id,world_id,document_id,scene_id,operation_id,request_digest,request,payload)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",(record.encounter_id,world_id,pin.document_id,pin.scene_id,request.operation_id,request_digest,Jsonb(body),Jsonb(binding.model_dump(mode='json'))))
        append_version(conn,record)
        return _view(conn,binding)


def read(*,world_id,document_id,scene_id):
    world_id=_world_id(world_id);dsn=load_runtime_dsn();assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        row=_row(conn,"SELECT * FROM combat.scene_template WHERE world_id=%s AND document_id=%s AND scene_id=%s",(world_id,UUID(str(document_id)),scene_id))
        if row is None:
            return None
        return _view(conn,_binding(row))


def inspect_operation(*,world_id,operation_id):
    world_id=_world_id(world_id);dsn=load_runtime_dsn();assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        row=_row(conn,"SELECT * FROM combat.scene_template WHERE world_id=%s AND operation_id=%s",(world_id,UUID(str(operation_id))))
        return None if row is None else _view(conn,_binding(row))


def read_version(*,world_id,document_id,scene_id,revision):
    world_id=_world_id(world_id);dsn=load_runtime_dsn();assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        row=_row(conn,"SELECT * FROM combat.scene_template WHERE world_id=%s AND document_id=%s AND scene_id=%s",(world_id,UUID(str(document_id)),scene_id))
        if row is None:
            raise ApplicationStateNotFoundError("Scene encounter template not found")
        binding=_binding(row);_present(conn,binding)
        saved=_row(conn,"SELECT * FROM combat.scene_template_version WHERE encounter_id=%s AND revision=%s",(binding.encounter_id,revision))
        if saved is None:
            raise ApplicationStateNotFoundError("Prepared encounter version not found")
        record=decode_combat_record(saved['payload'])
        if record.encounter_id!=binding.encounter_id or record.world_id!=world_id or record.revision!=revision or digest(saved['payload'])!=(saved['redacted_digest'] or saved['digest']):
            raise ApplicationStateIntegrityError("Prepared encounter version identity/digest is invalid")
        _require_integrity(record)
        _require_available_encounter_mechanics(conn, record)
        return record


def cancel(*,world_id,request:CreateSceneTemplateRequest,authorize: Callable[[], None] | None = None):
    world_id=_world_id(world_id);body=request.model_dump(mode='json');request_digest=digest({'world_id':world_id,'request':body})
    dsn=load_runtime_dsn();assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",('scene-template:'+str(request.operation_id),))
        applied=_row(conn,"SELECT * FROM combat.scene_template WHERE operation_id=%s",(request.operation_id,))
        if applied is not None:
            if applied['world_id']!=world_id or applied['request_digest']!=request_digest or applied['request']!=body:
                raise ApplicationStateConflictError("Creation key already has a different intent")
            return {'state':'applied','view':_view(conn,_binding(applied))}
        existing=_row(conn,"SELECT * FROM combat.scene_template_cancellation WHERE operation_id=%s",(request.operation_id,))
        if existing is not None and (existing['world_id']!=world_id or existing['request_digest']!=request_digest or existing['request']!=body):
            raise ApplicationStateConflictError("Creation key already has a different intent")
        if existing is None:
            if authorize is not None:
                authorize()
            conn.execute("INSERT INTO combat.scene_template_cancellation(operation_id,world_id,request_digest,request) VALUES(%s,%s,%s,%s)",(request.operation_id,world_id,request_digest,Jsonb(body)))
        return {'state':'canceled','operation_id':str(request.operation_id),'world_id':world_id,'request_digest':request_digest}


def read_snapshot(conn, *, world_id, document_id, scene_id, pin, require_head=False):
    """Resolve an immutable captured version without consulting today's Plan or producers."""
    row = _row(conn, 'SELECT * FROM combat.scene_template WHERE encounter_id=%s', (pin.encounter_id,))
    if row is None:
        raise ApplicationStateNotFoundError('Prepared encounter template not found')
    binding = _binding(row)
    if (binding.world_id != world_id or binding.origin.document_id != document_id
            or binding.origin.scene_id != scene_id):
        raise ApplicationStateConflictError('Encounter template belongs to another source scene')
    if require_head:
        head = repo.get_encounter(conn, world_id=world_id, encounter_id=pin.encounter_id)
        if head is None or head.revision != pin.revision:
            raise ApplicationStateConflictError('Prepared encounter version changed; review session choices again')
    saved = _row(conn, 'SELECT * FROM combat.scene_template_version WHERE encounter_id=%s AND revision=%s',
                 (pin.encounter_id, pin.revision))
    if saved is None:
        raise ApplicationStateNotFoundError('Prepared encounter version not found')
    if saved['digest'] != pin.digest or digest(saved['payload']) != (saved['redacted_digest'] or pin.digest):
        raise ApplicationStateIntegrityError('Prepared encounter version digest is invalid')
    record = decode_combat_record(saved['payload'])
    if record.encounter_id != pin.encounter_id or record.world_id != world_id or record.revision != pin.revision:
        raise ApplicationStateIntegrityError('Prepared encounter snapshot identity is invalid')
    _require_integrity(record)
    _require_available_encounter_mechanics(conn, record)
    return record
