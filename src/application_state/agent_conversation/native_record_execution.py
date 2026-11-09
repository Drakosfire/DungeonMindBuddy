"""Pure selected-record transitions; no source, provider or APP authority.

Recovery folds the same groups as a later incremental consumer. Only compact
value indexes survive a group. Query models and read/support bodies stay with
existing owners, never cached in this state. Full APP prefix integrity, global
provider/event checks and actual producing SDK proof remain separate obligations.
"""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class _Selection:
    select_candidates: bool
    handles: frozenset[str]
    handle_error: str | None = None

    @classmethod
    def capture(cls, event):
        # This predicate only uses handle membership. Preserve its old lazy
        # TypeError on malformed JSON values without retaining mutable lists.
        try:
            handles = frozenset(event.selected_handles)
        except TypeError as exc:
            return cls(event.operation == 'select_candidates', frozenset(), str(exc))
        return cls(event.operation == 'select_candidates', handles)

    @property
    def selected_handles(self):
        if self.handle_error is not None:
            raise TypeError(self.handle_error)
        return self.handles


@dataclass(frozen=True, slots=True)
class _Grant:
    event_id: UUID
    assertion: bool
    provider_attempt_id: UUID
    ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Observation:
    event_id: UUID
    authorization_event_id: UUID
    assertion: bool


@dataclass(frozen=True, slots=True)
class _RecordState:
    provider: UUID | None = None
    response_received: bool = False
    selection: _Selection | None = None
    grants: tuple[_Grant, ...] = ()
    observations: tuple[_Observation, ...] = ()
    attempted: frozenset[tuple[bool, str]] = frozenset()
    pending_object_reads: frozenset[tuple[bool, str]] = frozenset()
    writer: bool = False


def _advance(state, query, events):
    from . import types as t
    from .native_plan_statements import (
        NativePlanQueryV1, NativePlanStatementReadAuthorizedV1,
        NativePlanStatementReadObservedV1, selection_handle, validate_record_reads,
    )
    from .native_plan_assertions import (
        NativePlanQueryV2, NativeGraphQueryV4, NativePlanAssertionReadAuthorizedV1,
        NativePlanAssertionReadObservedV1, selection_handle as assertion_handle,
        object_record_ids,
    )

    statements = {m.statement_id: m for m in query.matches} if isinstance(query, NativePlanQueryV1) else {}
    assertions = {m.assertion_id: m for m in query.assertion_matches} if isinstance(query, NativePlanQueryV2) else {}
    provider, response_received, selection, writer = (
        state.provider, state.response_received, state.selection, state.writer)
    grants = {g.event_id: g for g in state.grants}
    observations = {o.event_id: o for o in state.observations}
    attempted, pending = set(state.attempted), set(state.pending_object_reads)
    for event in events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            if pending or (isinstance(query, NativeGraphQueryV4)
                    and set(grants) != {o.authorization_event_id for o in observations.values()}):
                raise ValueError('Native object selection must acquire and settle its complete record closure before another provider')
            shared_writer = False
            if event.kind in {'native_writer_authorized_v1', 'native_build_writer_authorized_v2'}:
                from .native_execution import NATIVE_WRITER_TYPES
                shared_writer = type(event) in NATIVE_WRITER_TYPES
            if shared_writer or isinstance(event, t.PlanJevWriterAuthorizedV1):
                if not shared_writer:
                    expected = t.PlanNativeWriterAuthorizedV2 if isinstance(query, NativePlanQueryV2) else t.PlanNativeWriterAuthorizedV1
                    if not isinstance(event, expected) or (not isinstance(query, NativePlanQueryV2) and isinstance(event, t.PlanNativeWriterAuthorizedV2)):
                        raise ValueError('Native query Plan requires its own writer inclusion')
                if set(grants) != {o.authorization_event_id for o in observations.values()}:
                    raise ValueError('Native writer requires every selected read grant to be settled')
                families = [] if shared_writer else [(False, event.native_statement_read_event_ids)]
                if not shared_writer and isinstance(query, NativePlanQueryV2):
                    families.append((True, event.native_assertion_read_event_ids))
                for assertion, included in families:
                    if (len(included) != len(set(included))
                            or set(included) != {o.event_id for o in observations.values() if o.assertion == assertion}):
                        raise ValueError('Native writer changed selected support exposure')
                writer = True
            provider, response_received, selection = event.provider_attempt_id, False, None
        elif isinstance(event, t.ProviderOutcomeEventV1) and event.provider_attempt_id == provider:
            response_received = event.outcome == 'response_received'
        elif isinstance(event, t.PlanJevRetrievalSelectionV1):
            selection = _Selection.capture(event)
            if isinstance(query, NativeGraphQueryV4):
                pending = {(family, identity) for family in (False, True)
                    for identity in object_record_ids(query, event.selected_handles, assertion=family,
                        attempted=(i for f, i in attempted if f == family))}
        elif isinstance(event, (NativePlanStatementReadAuthorizedV1, NativePlanAssertionReadAuthorizedV1)):
            assertion = isinstance(event, NativePlanAssertionReadAuthorizedV1)
            ids = event.assertion_ids if assertion else event.statement_ids
            matches = assertions if assertion else statements
            handle = assertion_handle if assertion else selection_handle
            if isinstance(query, NativeGraphQueryV4) and selection is not None:
                expected_ids = object_record_ids(query, selection.selected_handles,
                    assertion=assertion, attempted=(i for family, i in attempted if family == assertion))
                selected_closure = set(ids) == set(expected_ids)
            else:
                selected_closure = (selection is not None and
                    {handle(query, matches[i]) for i in ids if i in matches} <= set(selection.selected_handles))
            keys = {(assertion, identity) for identity in ids}
            if (writer or not response_received or selection is None
                    or not selection.select_candidates or event.provider_attempt_id != provider
                    or not isinstance(query, NativePlanQueryV1) or event.query_sha256 != query.sha256
                    or not set(ids) <= set(matches) or attempted & keys
                    or not selected_closure):
                raise ValueError('Native selected read lacks its exact current controller/query grant')
            grants[event.event_id] = _Grant(event.event_id, assertion, event.provider_attempt_id, tuple(ids))
            attempted.update(keys)
            pending.difference_update(keys)
        elif isinstance(event, (NativePlanStatementReadObservedV1, NativePlanAssertionReadObservedV1)):
            grant = grants.get(event.authorization_event_id)
            assertion = isinstance(event, NativePlanAssertionReadObservedV1)
            ids = {r.assertion.assertion_id for r in event.reads} if assertion else {r.support.statement_id for r in event.reads}
            unavailable = event.unavailable_assertion_ids if assertion else event.unavailable_statement_ids
            granted = set(grant.ids) if grant is not None and grant.assertion == assertion else None
            if (writer or granted is None or grant.provider_attempt_id != provider or not response_received
                    or any(o.authorization_event_id == grant.event_id for o in observations.values())
                    or granted != ids | set(unavailable)):
                raise ValueError('Native read observation differs from selected grant')
            validate_record_reads(query.authority, event.reads,
                assertions if assertion else statements, assertion=assertion)
            observations[event.event_id] = _Observation(event.event_id, event.authorization_event_id, assertion)
    return _RecordState(provider=provider, response_received=response_received, selection=selection,
        grants=tuple(grants.values()), observations=tuple(observations.values()),
        attempted=frozenset(attempted), pending_object_reads=frozenset(pending), writer=writer)


def validate(query, execution):
    """One recovery consumer; a pure record fold cannot authorize a full Turn."""
    _advance(_RecordState(), query, execution.events)
