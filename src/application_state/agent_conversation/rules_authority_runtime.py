"""Internal serialized local-reader port; no inference, routes or source imports."""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from pydantic import Field

from application_state.errors import ApplicationStateIntegrityError, ApplicationStateValidationError
from .rules_authority_events import RulesExecutionV1, RulesToolAuthorizedV1, RulesQueryObservedV1
from .rules_authority_packet import RulesPacketV1, RulesBudgetDiagnosticV1, verify_output_proof
from .rules_authority_store import (
    RulesLedgerRecordV1, _lock_current_claim, _locked_record, append_lookup_event_locked,
)
from .rules_authority_types import ClosedRulesModel, RulesScopeV1, RulesSupportV1, canonical_bytes


class RulesLookupPreparedV1(ClosedRulesModel):
    raw_output: Annotated[str, Field(min_length=1, max_length=65536)]
    observation: RulesQueryObservedV1
    new_supports: Annotated[tuple[RulesSupportV1, ...], Field(max_length=4)]


class RulesLookupDeliveryV1(ClosedRulesModel):
    record: RulesLedgerRecordV1
    prepared: RulesLookupPreparedV1
    replayed: bool


RulesLocalReader = Callable[[RulesExecutionV1], RulesLookupPreparedV1]


def _replay(execution, auth, observed):
    """The kernel emits canonical packets; never guess alternate historical bytes."""
    if observed.status == "over_budget":
        packet = RulesBudgetDiagnosticV1(schema="dmb_rules_budget_diagnostic_v1",
            execution_id=execution.scope.execution_id, call_id=auth.call_id, code="rules_budget_exhausted")
    else:
        emitted = set(observed.emitted_support_ids)
        packet = RulesPacketV1(schema="dmb_rules_packet_v1", call_id=auth.call_id,
            query_id=auth.query_id, normalized_question=auth.normalized_question,
            corpus_sha256=execution.scope.corpus_sha256, ruleset_id=execution.scope.ruleset_id,
            status=observed.status, support_refs=observed.support_refs,
            emitted_support_ids=observed.emitted_support_ids,
            previous_support_ids=tuple(r.support_id for r in observed.support_refs if r.support_id not in emitted),
            support_capsules=tuple(execution.supports[sid].support for sid in observed.emitted_support_ids),
            diagnostic={"unavailable": "corpus_unavailable", "denied": "unsupported_ruleset"}.get(observed.status))
    raw = canonical_bytes(packet).decode()
    try:
        verify_output_proof(execution.scope, observed, execution.supports, raw)
    except ValueError as exc:
        raise ApplicationStateIntegrityError("Rules lookup replay differs from sealed canonical packet") from exc
    return RulesLookupPreparedV1(raw_output=raw, observation=observed, new_supports=())


def execute_local_lookup_locked(conn, scope: RulesScopeV1, *, expected_turn_revision: int,
                                call_id: str, local_reader: RulesLocalReader) -> RulesLookupDeliveryV1:
    """Caller owns UOW and must commit before releasing any returned bytes.

    The trusted callback may perform only bounded local source reads. Reload under
    the owning Turn lock serializes concurrent readers, including query cache reuse.
    No callback or prepared packet from an earlier ledger snapshot is accepted.
    """
    _lock_current_claim(conn, scope, expected_turn_revision)
    current = _locked_record(conn, scope)
    if current is None or current.execution.state != "active":
        raise ApplicationStateValidationError("Rules lookup has no active execution")
    execution = current.execution
    auth = next((e for e in execution.events if isinstance(e, RulesToolAuthorizedV1) and e.call_id == call_id), None)
    if auth is None:
        raise ApplicationStateValidationError("Rules lookup has no sealed call authorization")
    observed = next((e for e in execution.events if isinstance(e, RulesQueryObservedV1) and e.call_id == call_id), None)
    if observed is not None:
        return RulesLookupDeliveryV1(record=current, prepared=_replay(execution, auth, observed), replayed=True)
    prepared = RulesLookupPreparedV1.model_validate(local_reader(execution))
    if prepared.observation.call_id != call_id or prepared.observation.query_id != auth.query_id:
        raise ApplicationStateValidationError("Rules local read differs from its authorized call")
    # Existing store independently validates scope, sequence, raw bytes/capsules,
    # exact result reuse, all budgets and the current claim/CAS after local read.
    updated, _ = append_lookup_event_locked(conn, scope,
        expected_turn_revision=expected_turn_revision, expected_ledger_revision=current.revision,
        event=prepared.observation, raw_output=prepared.raw_output, new_supports=prepared.new_supports)
    return RulesLookupDeliveryV1(record=updated, prepared=prepared, replayed=False)
