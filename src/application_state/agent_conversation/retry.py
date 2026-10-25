"""Explicit retry admission and read-only lineage; never resets a provider claim."""

import json
from typing import Literal
from uuid import UUID
from pydantic import Field
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work
from . import repository as repo
from .types import (
    StrictModel,
    Turn,
    BuildGraphIntentV1,
    BuildGraphContextReceiptV1,
    ProviderAttemptAuthorizedEventV1,
    ProviderOutcomeEventV1,
)


class RetryUnavailableError(ApplicationStateConflictError):
    """A new retry was refused before acceptance or provider authorization."""


class RetryContext(StrictModel):
    world_id: str
    conversation_id: UUID
    turn_id: UUID
    revision: int = Field(strict=True, ge=1)
    root_id: UUID
    predecessor_id: UUID | None
    successor_id: UUID | None
    ordinal: int = Field(strict=True, ge=0)
    eligible: bool
    reason: Literal[
        "ready",
        "not_terminal",
        "unknown_outcome",
        "existing_result",
        "reviewed_step",
        "retried",
        "inactive",
        "unverified",
    ]


def _edges(conn, turn):
    incoming = conn.execute(
        "SELECT root_id,predecessor_id,ordinal FROM agent.turn_retry WHERE successor_id=%s AND world_id=%s AND conversation_id=%s",
        (turn.turn_id, turn.world_id, turn.conversation_id),
    ).fetchone()
    outgoing = conn.execute(
        "SELECT successor_id FROM agent.turn_retry WHERE predecessor_id=%s AND world_id=%s AND conversation_id=%s",
        (turn.turn_id, turn.world_id, turn.conversation_id),
    ).fetchone()
    return incoming, outgoing


def _settled(conn, turn, *, lock=False):
    if turn.status not in {"failed", "interrupted"} or turn.completion is not None:
        return "not_terminal"
    if (
        not isinstance(turn.graph_context_receipt, BuildGraphContextReceiptV1)
        or turn.graph_context_execution is None
    ):
        return "unverified"
    if conn.execute(
        "SELECT 1 FROM agent.turn_reviewed_action WHERE turn_id=%s", (turn.turn_id,)
    ).fetchone():
        return "reviewed_step"
    events = turn.graph_context_execution.events
    outcomes = {
        e.provider_attempt_id: e.outcome
        for e in events
        if isinstance(e, ProviderOutcomeEventV1)
    }
    if any(
        outcomes.get(e.provider_attempt_id)
        not in {"response_received", "known_not_sent"}
        for e in events
        if isinstance(e, ProviderAttemptAuthorizedEventV1)
    ):
        return "unknown_outcome"
    from .rules_authority_events import (
        RulesExecutionV1,
        RulesProviderAuthorizedV1,
        RulesProviderOutcomeV1,
    )

    for payload, binding in conn.execute(
        "SELECT payload,accepted_binding FROM agent.turn_rules_execution WHERE turn_id=%s"
        + (" FOR UPDATE" if lock else ""),
        (turn.turn_id,),
    ).fetchall():
        rules = RulesExecutionV1.model_validate_json(json.dumps(payload))
        if (rules.scope.world_id, rules.scope.conversation_id, rules.scope.turn_id) != (
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
        ):
            return "unverified"
        if binding is not None or rules.state not in {"failed", "unused"}:
            return "existing_result"
        final = {
            e.provider_attempt_id: e.status
            for e in rules.events
            if isinstance(e, RulesProviderOutcomeV1)
        }
        if any(
            final.get(e.provider_attempt_id) not in {"answered", "tool_calls"}
            for e in rules.events
            if isinstance(e, RulesProviderAuthorizedV1)
        ):
            return "unknown_outcome"
    records = conn.execute(
        "SELECT payload FROM agent.build_proposal WHERE world_id=%s AND conversation_id=%s AND payload->'reservation'->'origin'->>'durable_turn_id'=%s"
        + (" FOR UPDATE" if lock else ""),
        (turn.world_id, turn.conversation_id, str(turn.turn_id)),
    ).fetchall()
    from application_state.build_proposal.types import BuildProposalRecord

    operations = [
        getattr(event, "operation", None)
        for event in events
        if event.kind
        in {"build_jev_action_selected_v1", "build_requested_work_resolved_v1"}
    ]
    role = getattr(
        getattr(turn.graph_context_execution.policy, "provider_roles", None),
        "writer",
        None,
    )
    writer_sent = role is not None and any(
        isinstance(event, ProviderAttemptAuthorizedEventV1)
        and (event.provider, event.model, event.api_mode)
        == (role.provider, role.model, role.api_mode)
        and outcomes.get(event.provider_attempt_id) == "response_received"
        for event in events
    )
    if (
        writer_sent
        and any(
            operation in {"propose_build_insertion", "prepare_build_image"}
            for operation in operations
        )
        and not records
    ):
        # A missing origin join is not proof that an old authoring operation had no effect.
        return "unverified"
    for (payload,) in records:
        if payload.get("schema_version") != "dmb_build_document_proposal_v1":
            return "existing_result"
        record = BuildProposalRecord.model_validate(payload)
        if (
            record.state != "failed"
            or record.proposal is not None
            or record.inserted_in_draft
        ):
            return "existing_result"
    return "ready"


def context(conn, turn, *, active):
    meta = getattr(turn, "envelope", turn)
    if (
        meta.provenance.surface_id != "build"
        or meta.provenance.primary_work.kind != "build"
    ):
        return None
    incoming, outgoing = _edges(conn, meta)
    reason = (
        "inactive"
        if not active
        else "retried"
        if outgoing
        else _settled(conn, turn)
        if isinstance(turn, Turn)
        else "not_terminal"
    )
    return RetryContext(
        world_id=meta.world_id,
        conversation_id=meta.conversation_id,
        turn_id=meta.turn_id,
        revision=meta.revision,
        root_id=incoming[0] if incoming else meta.turn_id,
        predecessor_id=incoming[1] if incoming else None,
        successor_id=outgoing[0] if outgoing else None,
        ordinal=incoming[2] if incoming else 0,
        eligible=reason == "ready",
        reason=reason,
    ).model_dump(mode="json")


def validate_reference_retry(parent, intent):
    """A deliberate retry retains author identity and origin, never newer inputs."""
    from .authored_graph_references import capture, policy_enabled
    execution = parent.graph_context_execution
    original = capture(execution).references if execution and policy_enabled(execution.policy) else None
    if getattr(intent, 'authored_references', None) != original:
        raise RetryUnavailableError('Retry requires the original Graph references and selection snapshots')


def validate_predecessor(conn, submission):
    intent = submission.submitted_intent_v2
    reference = intent.retry_of if isinstance(intent, BuildGraphIntentV1) else None
    if reference is None:
        return None
    parent = repo.lock_turn(conn, submission.world_id, reference.turn_id)
    if (
        not isinstance(parent, Turn)
        or parent.conversation_id != submission.conversation_id
    ):
        raise RetryUnavailableError(
            "Retry predecessor is unavailable in this conversation"
        )
    if parent.revision != reference.revision:
        raise RetryUnavailableError(
            "The failed attempt changed. Refresh its history before retrying."
        )
    old, new = parent.provenance, submission.provenance
    if (
        old.surface_id != "build"
        or new.surface_id != "build"
        or old.primary_work.kind != "build"
        or new.primary_work.kind != "build"
        or old.primary_work.object_id != new.primary_work.object_id
        or parent.user_text != submission.user_text
    ):
        raise RetryUnavailableError("Retry requires the same question and Build page")
    validate_reference_retry(parent, intent)
    previous_capability = getattr(
        getattr(parent.graph_context_execution, "policy", None),
        "action_capability_sha256",
        None,
    )
    if (
        intent.build_write_capability_sha256 is not None
        and intent.build_write_capability_sha256 == previous_capability
    ):
        raise RetryUnavailableError("Capture a fresh page placement before retrying")
    incoming, outgoing = _edges(conn, parent)
    reason = "retried" if outgoing else _settled(conn, parent, lock=True)
    if reason != "ready":
        raise RetryUnavailableError(
            "Retry unavailable: "
            + reason
            + ". Refresh history and recover the existing result first."
        )
    return parent, incoming


def retain_edge(conn, admitted, parent):
    if parent is None:
        return
    predecessor, incoming = parent
    conn.execute(
        "INSERT INTO agent.turn_retry(predecessor_id,successor_id,root_id,world_id,conversation_id,predecessor_revision,ordinal) VALUES(%s,%s,%s,%s,%s,%s,%s)",
        (
            predecessor.turn_id,
            admitted.turn_id,
            incoming[0] if incoming else predecessor.turn_id,
            admitted.world_id,
            admitted.conversation_id,
            predecessor.revision,
            (incoming[2] if incoming else 0) + 1,
        ),
    )


def read_context(world, conversation, turn_ids):
    if not 1 <= len(turn_ids) <= 100 or len(set(turn_ids)) != len(turn_ids):
        raise ApplicationStateValidationError(
            "Select between one and 100 distinct turns"
        )
    from .service import _ready_dsn

    with unit_of_work(_ready_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        owner = repo.get_conversation(conn, world, conversation)
        if owner is None:
            raise ApplicationStateNotFoundError(
                "Conversation unavailable in this World"
            )
        pointer = repo.get_world_state(conn, world)
        active = (
            owner.status == "active"
            and pointer is not None
            and pointer.active_conversation_id == conversation
        )
        rows = []
        for turn_id in turn_ids:
            turn = repo.get_turn(conn, world, turn_id)
            if (
                turn is None
                or getattr(turn, "envelope", turn).conversation_id != conversation
            ):
                raise ApplicationStateNotFoundError(
                    "Turn unavailable in this conversation"
                )
            rows.append(
                {"turn_id": str(turn_id), "context": context(conn, turn, active=active)}
            )
        return {
            "schema": "dmb_turn_retry_context_v1",
            "world_id": world,
            "conversation_id": str(conversation),
            "turns": rows,
        }


def require_leaf(conn, turn):
    if conn.execute(
        "SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s", (turn.turn_id,)
    ).fetchone():
        raise ApplicationStateConflictError(
            "This attempt has a saved successor. Inspect its latest attempt instead."
        )
