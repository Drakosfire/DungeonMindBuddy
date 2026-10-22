"""Claim-fenced Rules ledger storage. All operations use their caller's UOW.

No operation commits, starts a provider, or admits a source catalog. Completion
and bounded historical reads are separate operations on this same ledger.
"""

from __future__ import annotations

import json
from typing import Annotated

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import Field, ValidationError

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from .rules_authority_events import (
    RulesExecutionV1,
    RulesProviderAuthorizedV1,
    RulesProviderIncludedV1,
    RulesProviderOutcomeV1,
    RulesPlanPacketProviderAuthorizedV1, RulesPlanPacketProviderIncludedV1,
    RulesQueryObservedV1,
    RulesToolAuthorizedV1, RulesPlanJevToolAuthorizedV1,
    empty_execution,
)
from .rules_authority_packet import append_observed_output
from .rules_authority_types import ClosedRulesModel, RulesScopeV1, RulesSupportV1


class RulesLedgerRecordV1(ClosedRulesModel):
    revision: Annotated[int, Field(ge=1)]
    execution: RulesExecutionV1


def _lock_current_claim(
    conn: psycopg.Connection, scope: RulesScopeV1, expected_turn_revision: int
):
    # Lock the owning turn first in every writer, matching normal completion.
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT status,revision,attempt,claim_expires_at,idempotency_key,
                   submitted_intent_fingerprint_v1,submitted_intent_fingerprint_v2
            FROM agent.turn WHERE world_id=%s AND conversation_id=%s AND turn_id=%s FOR UPDATE""",
            (scope.world_id, scope.conversation_id, scope.turn_id),
        )
        row = cur.fetchone()
    if row is None:
        raise ApplicationStateNotFoundError(
            "Rules turn not found in verified World conversation"
        )
    now = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    if (
        row["status"] != "running"
        or row["revision"] != expected_turn_revision
        or row["attempt"] != scope.product_attempt
        or row["claim_expires_at"] is None
        or row["claim_expires_at"] <= now
    ):
        raise ApplicationStateConflictError(
            "Rules operation is fenced by a stale or expired turn claim"
        )
    from .rules_authority_policy import capability_for_policy_sha256, rules_submission_authorization_id
    capability = capability_for_policy_sha256(scope.capability_policy_sha256)
    if capability is not None:
        intents = [row[key] for key in ("submitted_intent_fingerprint_v1", "submitted_intent_fingerprint_v2") if row[key] is not None]
        if len(intents) != 1:
            raise ApplicationStateConflictError("Rules runtime requires one verified submitted-intent identity")
        expected = rules_submission_authorization_id(world_id=scope.world_id,
            conversation_id=scope.conversation_id, idempotency_key=row["idempotency_key"],
            submitted_intent_sha256=intents[0], capability=capability)
        if scope.authorization_id != expected:
            raise ApplicationStateConflictError("Rules correlation differs from the actual logical submission")


def _read_record_locked(conn, turn_id, product_attempt):
    with conn.cursor(row_factory=dict_row) as cur:
        # Do not transfer an oversized/corrupt payload before checking its cap.
        cur.execute(
            """SELECT revision,CASE WHEN octet_length(payload::text)<=327680 THEN payload ELSE NULL END AS payload
            FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s FOR UPDATE""",
            (turn_id, product_attempt),
        )
        row = cur.fetchone()
    if row is None:
        return None
    if row["payload"] is None:
        raise ApplicationStateIntegrityError(
            "Rules ledger exceeds its SQL transfer cap"
        )
    try:
        execution = RulesExecutionV1.model_validate_json(
            json.dumps(row["payload"], ensure_ascii=False)
        )
    except (ValueError, ValidationError) as exc:
        raise ApplicationStateIntegrityError(
            "Stored Rules ledger failed strict validation"
        ) from exc
    return RulesLedgerRecordV1(revision=row["revision"], execution=execution)


def _locked_record(conn, scope):
    record = _read_record_locked(conn, scope.turn_id, scope.product_attempt)
    if record is not None and record.execution.scope != scope:
        raise ApplicationStateConflictError(
            "Rules scope differs from its frozen attempt authority"
        )
    return record


def load_turn_rules_locked(conn, turn):
    """Caller holds the exact owning Turn lock; read one current-attempt ledger."""
    record = _read_record_locked(conn, turn.turn_id, turn.attempt)
    if record is not None:
        scope = record.execution.scope
        if (
            scope.world_id,
            scope.conversation_id,
            scope.turn_id,
            scope.product_attempt,
        ) != (turn.world_id, turn.conversation_id, turn.turn_id, turn.attempt):
            raise ApplicationStateIntegrityError(
                "Rules ledger differs from its owning turn"
            )
    return record


def close_unused_locked(conn, turn):
    record = load_turn_rules_locked(conn, turn)
    if record is None or record.execution.state == "unused":
        return
    if (
        record.execution.state != "active"
        or record.execution.budget_use.calls
        or record.execution.supports
    ):
        raise ApplicationStateValidationError(
            "Used Rules capability requires mixed finalization or failure"
        )
    _write_closed_state_locked(conn, turn, record, "unused")


def fail_execution_locked(conn, turn):
    record = load_turn_rules_locked(conn, turn)
    if record is None or record.execution.state == "failed":
        return
    if record.execution.state != "active":
        raise ApplicationStateConflictError("Rules execution already closed")
    _write_closed_state_locked(conn, turn, record, "failed")


def _write_closed_state_locked(conn, turn, record, state):
    data = record.execution.model_dump(mode="json", by_alias=True)
    data["state"] = state
    execution = RulesExecutionV1.model_validate_json(
        json.dumps(data, ensure_ascii=False)
    )
    result = conn.execute(
        """UPDATE agent.turn_rules_execution SET revision=revision+1,payload=%s
        WHERE turn_id=%s AND product_attempt=%s AND revision=%s AND accepted_binding IS NULL""",
        (
            Jsonb(execution.model_dump(mode="json", by_alias=True)),
            turn.turn_id,
            turn.attempt,
            record.revision,
        ),
    )
    if result.rowcount != 1:
        raise ApplicationStateConflictError("Rules closure CAS failed")


def open_execution_locked(
    conn: psycopg.Connection, scope: RulesScopeV1, *, expected_turn_revision: int
) -> RulesLedgerRecordV1:
    _lock_current_claim(conn, scope, expected_turn_revision)
    current = _locked_record(conn, scope)
    if current is not None:
        if current.execution.state != "active":
            raise ApplicationStateConflictError(
                "Rules execution already closed for this attempt"
            )
        return current
    execution = empty_execution(scope)
    conn.execute(
        """INSERT INTO agent.turn_rules_execution(turn_id,product_attempt,revision,payload)
        VALUES(%s,%s,1,%s)""",
        (
            scope.turn_id,
            scope.product_attempt,
            Jsonb(execution.model_dump(mode="json", by_alias=True)),
        ),
    )
    return RulesLedgerRecordV1(revision=1, execution=execution)


def require_open_plan_jev_acquisition_locked(conn, scope):
    """Caller owns the Turn lock; shared Rules reads obey Plan's final phase."""
    from . import repository
    from .types import PlanJevRetrievalPolicyV1, PlanJevRetrievalSelectionV1, ProviderAttemptAuthorizedEventV1
    turn = repository.get_turn(conn, scope.world_id, scope.turn_id)
    execution = getattr(turn, "graph_context_execution", None)
    if execution is None or not isinstance(execution.policy, PlanJevRetrievalPolicyV1):
        return turn
    selections = [event for event in execution.events if isinstance(event, PlanJevRetrievalSelectionV1)]
    providers = [event for event in execution.events if isinstance(event, ProviderAttemptAuthorizedEventV1)]
    if (not selections or not providers or selections[-1].operation == "finish_retrieval"
            or selections[-1].controller_attempt_id != providers[-1].provider_attempt_id):
        raise ApplicationStateValidationError("Rules read requires an open Plan Jev acquisition phase")
    return turn


def append_lookup_event_locked(
    conn: psycopg.Connection,
    scope: RulesScopeV1,
    *,
    expected_turn_revision: int,
    expected_ledger_revision: int,
    event: RulesToolAuthorizedV1 | RulesQueryObservedV1,
    raw_output: str | None = None,
    new_supports: tuple[RulesSupportV1, ...] = (),
    plan_jev_parent_request_json: str | None = None,
) -> tuple[RulesLedgerRecordV1, bool]:
    """Append only lookup events; provider exposure requires its own raw proof seam."""
    _lock_current_claim(conn, scope, expected_turn_revision)
    current = _locked_record(conn, scope)
    if current is None:
        raise ApplicationStateNotFoundError("Rules attempt has no admitted execution")
    prior = next(
        (item for item in current.execution.events if item.event_id == event.event_id),
        None,
    )
    if prior is None and current.revision != expected_ledger_revision:
        raise ApplicationStateConflictError(
            "Rules ledger revision changed before append"
        )
    try:
        if isinstance(event, RulesQueryObservedV1):
            if raw_output is None:
                raise ValueError(
                    "Rules observation requires its exact internal output proof"
                )
            updated = append_observed_output(
                current.execution, event, raw_output, new_supports
            )
        else:
            if raw_output is not None or new_supports:
                raise ValueError(
                    "Rules call authorization cannot admit output or sources"
                )
            if current.execution.state != "active":
                raise ValueError("Rules execution is immutable after closure")
            if prior is not None:
                if prior != event:
                    raise ValueError(
                        "Rules event identity was reused with different content"
                    )
                return current, False
            turn = require_open_plan_jev_acquisition_locked(conn, scope)
            from .types import PlanJevRetrievalPolicyV1
            if isinstance(event, RulesPlanJevToolAuthorizedV1):
                from .plan_jev_rules_lookup import verify_authorization
                verify_authorization(current.execution, turn, event, plan_jev_parent_request_json)
            elif turn.graph_context_execution is not None and isinstance(turn.graph_context_execution.policy, PlanJevRetrievalPolicyV1):
                raise ValueError("Plan Jev Rules lookup requires its actual selected decision proof")
            data = current.execution.model_dump(mode="json", by_alias=True)
            data["events"].append(event.model_dump(mode="json", by_alias=True))
            calls = [
                item for item in data["events"] if item["kind"] in {"tool_authorized", "build_tool_authorized", "plan_jev_tool_authorized"}
            ]
            data["budget_use"]["calls"] = len(calls)
            data["budget_use"]["distinct_questions"] = len(
                {item["normalized_question"] for item in calls}
            )
            updated = RulesExecutionV1.model_validate_json(
                json.dumps(data, ensure_ascii=False)
            )
    except (ValueError, ValidationError) as exc:
        raise ApplicationStateValidationError(
            "Rules lookup event or internal proof is invalid"
        ) from exc
    if updated == current.execution:
        return current, False
    # Both fences remain locked; the explicit CAS protects accidental misuse.
    result = conn.execute(
        """UPDATE agent.turn_rules_execution SET revision=revision+1,payload=%s
        WHERE turn_id=%s AND product_attempt=%s AND revision=%s""",
        (
            Jsonb(updated.model_dump(mode="json", by_alias=True)),
            scope.turn_id,
            scope.product_attempt,
            current.revision,
        ),
    )
    if result.rowcount != 1:
        raise ApplicationStateConflictError("Rules ledger CAS failed")
    return RulesLedgerRecordV1(revision=current.revision + 1, execution=updated), True


def append_provider_event_locked(
    conn: psycopg.Connection,
    scope: RulesScopeV1,
    *,
    expected_turn_revision: int,
    expected_ledger_revision: int,
    event: RulesProviderAuthorizedV1 | RulesProviderIncludedV1 | RulesProviderOutcomeV1,
    prepared_request_json: str | None = None,
) -> tuple[RulesLedgerRecordV1, bool]:
    """Seal an actual parent-observed request/outcome under the current claim.

    Completion is deliberately not an admitted event here; it is created only
    together with the accepted answer/binding in mixed finalization.
    """
    from .rules_authority_input import verify_prepared_input

    if not isinstance(
        event,
        (RulesProviderAuthorizedV1, RulesProviderIncludedV1, RulesProviderOutcomeV1),
    ):
        raise ApplicationStateValidationError("Not a Rules provider lifecycle event")
    _lock_current_claim(conn, scope, expected_turn_revision)
    current = _locked_record(conn, scope)
    if current is None:
        raise ApplicationStateNotFoundError("Rules attempt has no admitted execution")
    prior = next(
        (item for item in current.execution.events if item.event_id == event.event_id),
        None,
    )
    if prior is None and current.revision != expected_ledger_revision:
        raise ApplicationStateConflictError(
            "Rules ledger revision changed before provider append"
        )
    try:
        if current.execution.state != "active":
            raise ValueError("Rules execution no longer accepts provider events")
        if isinstance(event, (RulesProviderAuthorizedV1, RulesProviderIncludedV1)):
            if prepared_request_json is None:
                raise ValueError(
                    "Rules provider authorization/inclusion requires actual prepared input"
                )
            plan_turn = None
            if isinstance(event, (RulesPlanPacketProviderAuthorizedV1, RulesPlanPacketProviderIncludedV1)):
                # _lock_current_claim already owns this row lock; join the full
                # current owner before accepting the new Plan-only carrier.
                from . import repository
                plan_turn = repository.get_turn(conn, scope.world_id, scope.turn_id)
                from .types import ProviderAttemptAuthorizedEventV3, ProviderOutcomeEventV1, PlanJevWriterAuthorizedV1
                graph_execution = getattr(plan_turn, "graph_context_execution", None)
                attempts = [item for item in getattr(graph_execution, "events", ())
                            if isinstance(item, ProviderAttemptAuthorizedEventV3)]
                graph_auth = attempts[-1] if attempts else None
                body = json.loads(prepared_request_json)
                if (not isinstance(body, dict) or graph_auth is None or graph_auth.provider_attempt_id != event.provider_attempt_id
                        or graph_auth.envelope_sha256 != event.request_envelope_sha256
                        or (graph_auth.api_mode != "codex_responses" and not (
                            isinstance(graph_auth, PlanJevWriterAuthorizedV1) and graph_auth.api_mode == "responses"))
                        or body.get("model") != graph_auth.model):
                    raise ValueError("Plan packet provider lacks its actual current Graph authorization")
                if prior is None and any(isinstance(item, ProviderOutcomeEventV1)
                        and item.provider_attempt_id == graph_auth.provider_attempt_id
                        for item in graph_execution.events):
                    raise ValueError("Plan packet admission must finish before Graph SDK entry")
            verify_prepared_input(current.execution, event, prepared_request_json, plan_turn=plan_turn)
        elif prepared_request_json is not None:
            raise ValueError(
                "Rules provider outcome cannot change the authorized input"
            )
        if prior is not None:
            if prior != event:
                raise ValueError(
                    "Rules provider event ID was reused with changed content"
                )
            return current, False
        data = current.execution.model_dump(mode="json", by_alias=True)
        data["events"].append(event.model_dump(mode="json", by_alias=True))
        if isinstance(event, RulesProviderAuthorizedV1):
            data["budget_use"]["provider_requests"] += 1
        updated = RulesExecutionV1.model_validate_json(
            json.dumps(data, ensure_ascii=False)
        )
    except (ValueError, ValidationError) as exc:
        raise ApplicationStateValidationError(
            "Rules provider event or actual input proof is invalid"
        ) from exc
    result = conn.execute(
        """UPDATE agent.turn_rules_execution SET revision=revision+1,payload=%s
        WHERE turn_id=%s AND product_attempt=%s AND revision=%s""",
        (
            Jsonb(updated.model_dump(mode="json", by_alias=True)),
            scope.turn_id,
            scope.product_attempt,
            current.revision,
        ),
    )
    if result.rowcount != 1:
        raise ApplicationStateConflictError("Rules provider ledger CAS failed")
    return RulesLedgerRecordV1(revision=current.revision + 1, execution=updated), True


def persist_accepted_locked(
    conn, current: RulesLedgerRecordV1, accepted: RulesExecutionV1, binding
):
    """Only mixed finalization may call this after locking/validating both owners."""
    from .rules_authority_types import canonical_sha256

    scope = current.execution.scope
    if (
        current.execution.state != "active"
        or accepted.state != "accepted"
        or accepted.scope != scope
        or accepted.events[:-1] != current.execution.events
        or accepted.events[-1].accepted_binding_sha256 != canonical_sha256(binding)
    ):
        raise ApplicationStateValidationError(
            "Accepted Rules value differs from its locked execution"
        )
    if (
        binding.world_id,
        binding.conversation_id,
        binding.turn_id,
        binding.product_attempt,
        binding.execution_id,
        binding.corpus_sha256,
        binding.ruleset_id,
    ) != (
        scope.world_id,
        scope.conversation_id,
        scope.turn_id,
        scope.product_attempt,
        scope.execution_id,
        scope.corpus_sha256,
        scope.ruleset_id,
    ):
        raise ApplicationStateValidationError(
            "Accepted Rules binding differs from frozen scope"
        )
    if (
        binding.composition_sha256 != canonical_sha256(accepted.composition)
        or binding.assistant_text_sha256 != accepted.composition.assistant_text_sha256
        or binding.accepted_turn_revision != accepted.events[-1].accepted_turn_revision
        or binding.producing_provider_attempt_id
        != accepted.rules_completion.producing_provider_attempt_id
        or binding.request_envelope_sha256
        != accepted.rules_completion.request_envelope_sha256
    ):
        raise ApplicationStateValidationError(
            "Accepted Rules binding differs from completion seal"
        )
    result = conn.execute(
        """UPDATE agent.turn_rules_execution SET revision=revision+1,payload=%s,accepted_binding=%s,accepted_binding_sha256=%s
        WHERE turn_id=%s AND product_attempt=%s AND revision=%s AND payload->>'state'='active'
            AND accepted_binding IS NULL AND accepted_binding_sha256 IS NULL""",
        (
            Jsonb(accepted.model_dump(mode="json", by_alias=True)),
            Jsonb(binding.model_dump(mode="json", by_alias=True)),
            canonical_sha256(binding),
            scope.turn_id,
            scope.product_attempt,
            current.revision,
        ),
    )
    if result.rowcount != 1:
        raise ApplicationStateConflictError("Rules acceptance CAS failed")
