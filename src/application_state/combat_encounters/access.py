"""APP authority for scoped Run encounter access and lifecycle locking."""
from dataclasses import dataclass
from application_state.play.types import PlayRun
from application_state.combat_encounters.scene_templates import _row
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError, ApplicationStateIntegrityError
from application_state.play import repository as runs


@dataclass(frozen=True)
class LockedSession:
    run: PlayRun
    preparation: dict | None


def lock_session(conn, *, world_id, run_id, for_mutation=False, require_preparation=False):
    from application_state.play.service import _resolve_world_run_owner
    run = runs.lock_run(conn, run_id, allow_trashed=True)
    if run is None or run.world_id != world_id:
        raise ApplicationStateNotFoundError('Session not found in selected World')
    _resolve_world_run_owner(conn, run, world_id=world_id)
    from application_state.play.session_encounters import _receipt, require_receipt_run
    from application_state.play.service import require_persisted_aggregate_integrity
    receipt = _receipt(conn, world_id, run_id)
    if receipt is None and require_preparation:
        raise ApplicationStateIntegrityError("Run encounter has no retained preparation")
    if receipt is not None:
        require_receipt_run(run, receipt)
        require_persisted_aggregate_integrity(run, runs.get_manifest(conn, run_id))
    if for_mutation:
        require_mutable_session(conn, run)

    return LockedSession(run=run, preparation=receipt)


def require_mutable_session(conn, run):
    from application_state.play.session_review import _head
    if run.lifecycle_status != 'active':
        raise ApplicationStateConflictError('Restore this session before changing its encounter')
    head = _head(conn, run.run_id)
    if head and head['status'] == 'ended':
        raise ApplicationStateConflictError('Reopen this session before changing its encounter')


def validate_binding(binding, preparation):
    """Join routing columns to the immutable creation intent and preparation."""
    from application_state.play.session_encounter_types import MaterializeSceneEncounterRequest, WorldSessionCreateRequest
    from application_state.play.session_encounters import _materialization_intent
    from application_state.combat_encounters.scene_templates import digest
    try:
        payload = binding['payload']
        intent = payload['intent']
        request = MaterializeSceneEncounterRequest.model_validate(intent['request'])
        expected = _materialization_intent(binding['world_id'], binding['run_id'], binding['scene_id'], request)
        preview = payload['preview']
        if preparation is None:
            raise ValueError('Missing preparation')
        source = WorldSessionCreateRequest.model_validate(preparation['request'])
        selected = next((choice.template for choice in source.encounters if choice.scene_id == binding['scene_id']), None)
        if (payload['schema_version'] != 'dmb_run_scene_encounter_v1'
                or intent != expected or binding['request_digest'] != digest(expected)
                or payload['encounter_id'] != str(binding['encounter_id'])
                or request.operation_id != binding['operation_id']
                or request.template.encounter_id != binding['template_encounter_id']
                or request.template.revision != binding['template_revision']
                or selected != request.template
                or request.expected_preparation_digest != preparation['preparation_digest']
                or request.preview_digest != digest(preview)
                or preview['world_id'] != binding['world_id']
                or preview['run_id'] != str(binding['run_id'])
                or preview['scene_id'] != binding['scene_id']
                or preview['preparation_digest'] != request.expected_preparation_digest
                or preview['template'] != request.template.model_dump(mode='json')
                or preview['initialization_policy'] != request.initialization_policy):
            raise ValueError('Binding disagrees with receipt')
    except (KeyError, TypeError, ValueError) as exc:
        raise ApplicationStateIntegrityError('Session encounter binding is inconsistent') from exc
    return payload


def guard(conn, *, world_id, encounter_id, scope=None, for_mutation=False):
    binding = _row(conn, 'SELECT * FROM combat.run_scene_encounter WHERE encounter_id=%s', (encounter_id,))
    if binding is not None and binding['world_id'] != world_id:
        raise ApplicationStateNotFoundError('Encounter not found in selected World')
    if scope is None:
        if binding is not None:
            raise ApplicationStateConflictError('Open this encounter through its owning session scene')
        return
    if binding is None or (binding['world_id'], binding['run_id'], binding['scene_id']) != (world_id, scope.run_id, scope.scene_id):
        raise ApplicationStateNotFoundError('Encounter not found in selected session scene')
    locked = lock_session(conn, world_id=world_id, run_id=scope.run_id, for_mutation=for_mutation, require_preparation=True)
    validate_binding(binding, locked.preparation)
    return locked.run
