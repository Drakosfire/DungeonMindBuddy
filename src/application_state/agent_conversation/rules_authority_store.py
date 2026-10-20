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
    RulesQueryObservedV1,
    RulesToolAuthorizedV1,
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
            """SELECT status,revision,attempt,claim_expires_at
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


def _locked_record(conn, scope):
    with conn.cursor(row_factory=dict_row) as cur:
        # Do not transfer an oversized/corrupt payload before checking its cap.
        cur.execute(
            """SELECT revision,CASE WHEN octet_length(payload::text)<=327680 THEN payload ELSE NULL END AS payload
            FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s FOR UPDATE""",
            (scope.turn_id, scope.product_attempt),
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
    if execution.scope != scope:
        raise ApplicationStateConflictError(
            "Rules scope differs from its frozen attempt authority"
        )
    return RulesLedgerRecordV1(revision=row["revision"], execution=execution)


def open_execution_locked(
    conn: psycopg.Connection, scope: RulesScopeV1, *, expected_turn_revision: int
) -> RulesLedgerRecordV1:
    _lock_current_claim(conn, scope, expected_turn_revision)
    current = _locked_record(conn, scope)
    if current is not None:
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


def append_lookup_event_locked(
    conn: psycopg.Connection,
    scope: RulesScopeV1,
    *,
    expected_turn_revision: int,
    expected_ledger_revision: int,
    event: RulesToolAuthorizedV1 | RulesQueryObservedV1,
    raw_output: str | None = None,
    new_supports: tuple[RulesSupportV1, ...] = (),
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
            data = current.execution.model_dump(mode="json", by_alias=True)
            data["events"].append(event.model_dump(mode="json", by_alias=True))
            calls = [
                item for item in data["events"] if item["kind"] == "tool_authorized"
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
