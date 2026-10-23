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
    return lock_session(conn, world_id=world_id, run_id=scope.run_id, for_mutation=for_mutation, require_preparation=True).run
