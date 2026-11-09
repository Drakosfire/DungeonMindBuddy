"""Exclusive APP materialization for one claimed readonly Plan retrieval.

The database remains authority. This owner guards the complete stored image on
every transaction; its private typed materialization never crosses an export or
external callback boundary. Existing service admission and complete prospective
execution validation remain in force.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from enum import Enum
from threading import RLock

from pydantic import BaseModel, TypeAdapter

from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError
from application_state.unit_of_work import unit_of_work
from . import repository as repo
from .native_execution import (
    NativePlanActionV2, NativePlanRequestedWorkSelectedV3, SurfaceNativeEvent,
    SurfaceNativeExecutionV1, _join_turn_fields, _join_turn_lifecycle,
    _validate_owned_context_binding,
)
from .service import AgentConversationService, _ready_dsn, _validate_turn_claim_lease


class PlanSessionCommand(str, Enum):
    CONTROLLER = 'authorize_plan_jev_provider'
    OUTCOME = 'record_provider_outcome'
    SELECTION = 'record_plan_jev_retrieval_selection'
    RECORD_GRANT = 'authorize_native_read'
    RECORD_OBSERVATION = 'observe_native_read'
    DIRECT_GRANTS = 'authorize_native_direct_sources'
    DIRECT_OBSERVATION = 'observe_native_direct_source'
    BODY_SEARCH_GRANT = 'authorize_native_body_search'
    BODY_SEARCH_OBSERVATION = 'observe_native_body_search'
    BODY_GRANT = 'authorize_native_body_read'
    BODY_OBSERVATION = 'observe_native_body_read'
    AUTHORED_CAPTURE = 'capture_native_authored_references'
    AUTHORED_GRANT = 'authorize_native_authored_reference'
    AUTHORED_OBSERVATION = 'observe_native_authored_reference'
    AUTHORED_SOURCE = 'observe_native_authored_source'
    RELATED_PAGE = 'record_build_related_pages'


_EVENT = TypeAdapter(SurfaceNativeEvent)


def _owned_event(event):
    if not isinstance(event, BaseModel):
        raise ApplicationStateIntegrityError('Session event requires its concrete native codec')
    return _EVENT.validate_json(event.model_dump_json(by_alias=True))


def eligible(turn):
    from .types import PlanRequestedWorkSelectedV2
    execution = getattr(turn, 'graph_context_execution', None)
    choices = ([] if type(execution) is not SurfaceNativeExecutionV1 else
        [e for e in execution.events if isinstance(e, PlanRequestedWorkSelectedV2)])
    return (type(execution) is SurfaceNativeExecutionV1
        and type(execution.policy.action) is NativePlanActionV2
        and turn.status == 'running'
        and len(choices) == 1 and type(choices[0]) is NativePlanRequestedWorkSelectedV3
        and choices[0].requested_work in {'discuss', 'clarify'})


class _SessionAdmission(AgentConversationService):
    """Reuse the actual append admission, with a single private storage owner."""

    def __init__(self, owner):
        self._owner = owner

    def _lock_execution_append_turn(self, conn, world_id, turn_id):
        if self._owner._pending is not None:
            raise ApplicationStateConflictError('Session command cannot reenter before publication')
        self._owner._guard_locked(conn)
        turn = self._owner._committed
        if (world_id, turn_id) != (turn.world_id, turn.turn_id):
            raise ApplicationStateIntegrityError('Session append crossed its claimed Turn')
        return turn

    def _materialize_execution_source(self, materialize, conn, turn):
        from .native_reads import _NativeReadOperation
        if type(materialize) is not _NativeReadOperation:
            raise ApplicationStateIntegrityError('Readonly session requires its closed native read producer')
        # Only existing, closed read producers inspect the private materialized
        # prefix. Those owners detach each value passed to an external callback;
        # no generic callback receives the Turn, and no whole-history copy is needed.
        produced = materialize(conn, turn)
        return tuple(_owned_event(e) for e in produced) if type(produced) is tuple else _owned_event(produced)

    def _bind_execution_append(self, context, execution):
        prior = self._owner._committed.graph_context_execution
        count = len(prior.events)
        if (context is not self._owner._committed.graph_context_receipt
                or type(execution) is not SurfaceNativeExecutionV1
                or execution.policy is not prior.policy
                or execution.schema_ != prior.schema_
                or execution.context_receipt_sha256 != prior.context_receipt_sha256
                or execution.execution_policy_sha256 != prior.execution_policy_sha256
                or len(execution.events) < count
                or any(a is not b for a, b in zip(execution.events[:count], prior.events))):
            raise ApplicationStateIntegrityError('Session transition replaced its owned committed prefix')
        # Preserve the genuine complete execution. Only its new group crosses
        # the strict storage codec; every existing predicate still inspects the
        # actual complete prefix, including source, role and record invariants.
        candidate = execution.model_copy(update={'events': [*prior.events,
            *(_owned_event(event) for event in execution.events[count:])]})
        return _validate_owned_context_binding(context, candidate)

    def _persist_execution_append(self, conn, *, world_id, turn_id, expected_revision, execution):
        owner = self._owner
        if expected_revision != owner._committed.revision:
            raise ApplicationStateConflictError('Session append has a stale revision')
        image = repo._update_plan_session_execution(conn, world_id=world_id,
            turn_id=turn_id, before=owner._image, execution=execution)
        if image is None:
            return None
        root = dict(image[0])
        # The complete prospective execution has just passed the existing
        # context owner. All other root/provenance fields are byte-identical to
        # the validated committed root, apart from the verified revision/clock.
        candidate = owner._committed.model_copy(update={
            'revision': root['revision'], 'updated_at': root['updated_at'],
            'graph_context_execution': execution})
        _join_turn_fields(candidate.graph_context_receipt, execution,
                          candidate.completion, candidate.assistant_text)
        _join_turn_lifecycle(candidate)
        owner._pending = candidate, image
        return candidate


class NativePlanSession:
    """One nonescaping materialization, serialized with the runtime claim fence."""

    def __init__(self, expected):
        self._lock = RLock()
        self._committed = self._image = self._pending = None
        self._sealed = False
        self._busy = False
        with unit_of_work(_ready_dsn()) as conn:
            image = repo._lock_plan_session_image(conn, expected.world_id, expected.turn_id)
            current = repo.lock_turn(conn, expected.world_id, expected.turn_id)
            if (current is None or not eligible(current)
                    or (current.conversation_id, current.revision, current.attempt)
                    != (expected.conversation_id, expected.revision, expected.attempt)
                    or current.claim_expires_at is None
                    or current.claim_expires_at <= repo.database_clock(conn)
                    or repo._lock_plan_session_image(conn, expected.world_id, expected.turn_id) != image):
                raise ApplicationStateConflictError('Readonly session requires its current classified Plan claim')
        self._committed, self._image = current, image
        self._admission = _SessionAdmission(self)

    def _require_live(self):
        if self._sealed or self._committed is None:
            raise ApplicationStateConflictError('Plan session is sealed')

    def _enter(self):
        self._require_live()
        if self._busy:
            raise ApplicationStateConflictError('Session command cannot reenter before publication')
        self._busy = True

    def _guard_locked(self, conn):
        self._require_live()
        turn = self._committed
        current = repo._lock_plan_session_image(conn, turn.world_id, turn.turn_id)
        if current != self._image:
            raise ApplicationStateIntegrityError('Plan session differs from current locked storage')
        return current

    def _seal(self):
        self._sealed = True
        self._committed = self._image = self._pending = None

    def abort(self):
        """Discard a generation when its runtime owner refuses before dispatch."""
        with self._lock:
            self._seal()

    def execute(self, command: PlanSessionCommand, *, expected_revision, expected_attempt, **fields):
        with self._lock:
            try:
                self._enter()
                if type(command) is not PlanSessionCommand:
                    raise ApplicationStateIntegrityError('Session requires a closed native command')
                turn = self._committed
                if (expected_revision, expected_attempt) != (turn.revision, turn.attempt):
                    raise ApplicationStateConflictError('Session command crossed its claim fence')
                owned = {name: (value if callable(value) else deepcopy(value)) for name, value in fields.items()}
                for name in ('authorization', 'outcome', 'selection', 'event'):
                    if name in owned:
                        owned[name] = _owned_event(owned[name])
                self._pending = None
                # This dispatch is closed over APP methods, not an arbitrary
                # caller-supplied method name or a new admission implementation.
                method = getattr(AgentConversationService, command.value)
                updated, fresh = method(self._admission, turn.world_id,
                    turn.conversation_id, turn.turn_id, expected_revision=expected_revision,
                    expected_attempt=expected_attempt, **owned)
                if type(fresh) is not bool:
                    raise ApplicationStateIntegrityError('Session admission returned an invalid disposition')
                # Service return occurs only after its transaction commits.
                if fresh:
                    if self._pending is None or updated is not self._pending[0]:
                        raise ApplicationStateIntegrityError('Session append has no committed successor')
                    self._committed, self._image = self._pending
                elif updated is not self._committed or self._pending is not None:
                    raise ApplicationStateIntegrityError('Session replay changed its committed generation')
                self._pending = None
                return deepcopy(self._committed), fresh
            except BaseException:
                self._seal()
                raise
            finally:
                self._busy = False

    def finish(self):
        """Rehydrate the genuine complete Turn before the writer frontier."""
        with self._lock:
            try:
                self._enter()
                with unit_of_work(_ready_dsn()) as conn:
                    self._guard_locked(conn)
                    turn = self._committed
                    return repo.lock_turn(conn, turn.world_id, turn.turn_id)
            finally:
                self._seal()
                self._busy = False

    def renew(self, *, expected_revision, lease_seconds):
        """Renew through the existing owner, then adopt its exact committed row."""
        with self._lock:
            try:
                self._enter()
                _validate_turn_claim_lease(lease_seconds)
                turn = self._committed
                if expected_revision != turn.revision:
                    raise ApplicationStateConflictError('Session renewal has a stale claim')
                with unit_of_work(_ready_dsn()) as conn:
                    before = self._guard_locked(conn)
                    started = repo.database_clock(conn)
                    renewed = repo.renew_turn_claim(conn, world_id=turn.world_id,
                        turn_id=turn.turn_id, expected_revision=expected_revision,
                        lease_seconds=lease_seconds)
                    if renewed is None:
                        raise ApplicationStateConflictError('Session claim expired during renewal')
                    image = repo._lock_plan_session_image(conn, turn.world_id, turn.turn_id)
                    finished = repo.database_clock(conn)
                    root = dict(image[0])
                    expected = dict(before[0]) | {'revision': expected_revision + 1,
                        'updated_at': renewed.updated_at, 'claim_expires_at': renewed.claim_expires_at}
                    if (root != expected or image[1:] != before[1:]
                            or not started <= renewed.updated_at <= finished
                            or not started + timedelta(seconds=lease_seconds)
                                <= renewed.claim_expires_at <= finished + timedelta(seconds=lease_seconds)):
                        raise ApplicationStateIntegrityError('Session renewal changed its locked storage image')
                self._committed, self._image = renewed, image
                return deepcopy(renewed)
            except BaseException:
                self._seal()
                raise
            finally:
                self._busy = False

    def rules_checkpoint(self, operation, record):
        """Join an existing Rules operation without trusting an image refresh.

        Each Rules write keeps its existing transaction owner. The runtime holds
        the moving claim lock throughout this checkpoint; any failure seals this
        generation, including a failure after a successfully committed child.
        """
        from .rules_authority_store import load_turn_rules_locked, RulesLedgerRecordV1
        with self._lock:
            try:
                self._enter()
                with unit_of_work(_ready_dsn()) as conn:
                    before = self._guard_locked(conn)
                    if self._committed.claim_expires_at <= repo.database_clock(conn):
                        raise ApplicationStateConflictError('Session claim expired before Rules checkpoint')
                    prior = load_turn_rules_locked(conn, self._committed)
                result = operation()
                expected = record()
                expected = (None if expected is None else
                    RulesLedgerRecordV1.model_validate_json(expected.model_dump_json(by_alias=True)))
                turn = self._committed
                with unit_of_work(_ready_dsn()) as conn:
                    image = repo._lock_plan_session_image(conn, turn.world_id, turn.turn_id)
                    actual = load_turn_rules_locked(conn, turn)
                    if image is None or image[:2] != before[:2] or actual != expected:
                        raise ApplicationStateIntegrityError('Rules checkpoint differs from its committed owner result')
                    if prior is not None and (actual is None or actual.revision < prior.revision
                            or actual.execution.scope != prior.execution.scope
                            or actual.execution.events[:len(prior.execution.events)] != prior.execution.events):
                        raise ApplicationStateIntegrityError('Rules checkpoint replaced its committed prefix')
                    old_row = dict(before[2]) if before[2] is not None else None
                    new_row = dict(image[2]) if image[2] is not None else None
                    if new_row is not None:
                        if old_row is not None:
                            expected_row = old_row | {'payload': new_row['payload'], 'revision': new_row['revision']}
                            if new_row != expected_row:
                                raise ApplicationStateIntegrityError('Rules checkpoint changed non-ledger child fields')
                        elif new_row['accepted_binding'] is not None or new_row['accepted_binding_sha256'] is not None:
                            raise ApplicationStateIntegrityError('Readonly Rules checkpoint cannot accept a completion')
                self._image = image
                return result
            except BaseException:
                self._seal()
                raise
            finally:
                self._busy = False
