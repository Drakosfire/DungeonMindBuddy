"""APP claim/CAS boundary for a single inert Build Compose proposal."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid5, NAMESPACE_URL

from psycopg.types.json import Jsonb

from application_state.agent_conversation.service import _lock_pointer, _ready_dsn
from application_state.build_proposal.types import (
    BUILD_MARKDOWN_PROPOSAL_CODECS, BuildProposalRecord, BuildProposalReservation, BuildProseBoundaryProposalRecord,
    BuildProseBoundaryReservation, decode_build_markdown_proposal, explicit_build_page_target, normalize_boundary_proposal_output,
    normalize_proposal_output,
)
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from application_state.unit_of_work import unit_of_work


def _load(row) -> BuildProposalRecord:
    payload = row[0]
    if payload.get("schema_version") not in BUILD_MARKDOWN_PROPOSAL_CODECS:
        raise ApplicationStateNotFoundError('Markdown proposal unavailable')
    return decode_build_markdown_proposal(payload)


def _save(conn, previous, updated):
    checked = type(previous).model_validate(updated)
    result = conn.execute("UPDATE agent.build_proposal SET payload=%s, revision=%s WHERE world_id=%s AND action_id=%s AND revision=%s",
        (Jsonb(checked.model_dump(mode="json")), checked.revision, checked.reservation.basis.world_id, checked.action_id, previous.revision))
    if result.rowcount != 1:
        raise ApplicationStateConflictError("Build proposal claim changed")
    return checked


def _require_origin_claim(conn, reservation):
    origin = reservation.origin
    if origin is None:
        return
    from application_state.agent_conversation import repository
    turn = repository.lock_turn(conn, reservation.basis.world_id, origin.durable_turn_id)
    if (turn is None or turn.conversation_id != reservation.conversation_id
            or turn.status != "running" or turn.attempt != origin.turn_attempt
            or turn.claim_expires_at is None or turn.claim_expires_at <= repository.database_clock(conn)
            or turn.idempotency_key != uuid5(NAMESPACE_URL,
                f"dmb-agent-turn:{reservation.basis.world_id}:{origin.client_turn_id}")
            or turn.provenance.surface_id != "build"
            or turn.provenance.primary_work.kind != "build"
            or turn.provenance.primary_work.object_id != reservation.basis.document_id
            or turn.provenance.primary_work.revision != str(reservation.basis.registry_revision)
            or turn.provenance.primary_work.content_sha256 != reservation.basis.content_sha256):
        raise ApplicationStateConflictError("Build proposal origin is fenced by the current Agent turn claim")
    return turn


def admit_native_prose_boundary(conn, reservation):
    """Join a reservation to the protected opening action under the turn lock."""
    from application_state.agent_conversation.native_execution import NativeBuildActionV1
    from application_state.agent_conversation.types import BuildRequestedWorkResolutionV1

    turn = _require_origin_claim(conn, reservation)
    execution = turn.graph_context_execution if turn is not None else None
    action = getattr(getattr(execution, "policy", None), "action", None)
    if type(action) is not NativeBuildActionV1 or action.write_capability is None:
        raise ApplicationStateConflictError("Build paragraph reservation requires its native captured capability")
    cap = action.write_capability
    selection = next((event for event in execution.events
                      if isinstance(event, BuildRequestedWorkResolutionV1)
                      and event.broker_operation_id == reservation.origin.broker_operation_id), None)
    if (
        selection is None or selection.operation != "propose_build_insertion"
        or selection.paragraph_placement is None
        or selection.paragraph_placement.target != reservation.prose_target
        or selection.arguments_sha256 != reservation.origin.arguments_sha256
        or selection.capability_sha256 != action.intent.build_write_capability_sha256
        or cap.basis != reservation.basis or cap.idempotency_key != reservation.idempotency_key
        or cap.conversation_id != reservation.conversation_id
        or cap.expected_pointer_revision != reservation.expected_pointer_revision
        or turn.user_text != reservation.instruction
    ):
        raise ApplicationStateConflictError("Build paragraph reservation differs from the admitted opening action")


class BuildProposalService:
    def __init__(self, *, admit_prose_boundary=None, require_native_page_target=False):
        self.admit_prose_boundary = admit_prose_boundary
        self.require_native_page_target = require_native_page_target

    def reserve(self, reservation: BuildProposalReservation) -> tuple[BuildProposalRecord, bool]:
        boundary = type(reservation) is BuildProseBoundaryReservation
        if boundary and self.admit_prose_boundary is None:
            raise ApplicationStateConflictError("Build prose boundaries require their admitted catalog owner")
        world = reservation.basis.world_id
        with unit_of_work(_ready_dsn()) as conn:
            # Same World serialization also covers concurrent duplicate submissions.
            pointer = _lock_pointer(conn, world)
            row = conn.execute("SELECT payload FROM agent.build_proposal WHERE world_id=%s AND idempotency_key=%s FOR UPDATE",
                (world, reservation.idempotency_key)).fetchone()
            if row:
                result = _load(row)
                if result.request_fingerprint != reservation.fingerprint:
                    raise ApplicationStateConflictError("Build proposal key has a different request")
                return result, False
            if (pointer.active_conversation_id != reservation.conversation_id
                    or pointer.revision != reservation.expected_pointer_revision):
                raise ApplicationStateConflictError("World conversation changed before Compose")
            conversation = conn.execute("SELECT next_turn_sequence FROM agent.conversation WHERE world_id=%s AND conversation_id=%s AND status='active' FOR UPDATE",
                (world, reservation.conversation_id)).fetchone()
            if not conversation:
                raise ApplicationStateNotFoundError("Active World conversation is unavailable")
            _require_origin_claim(conn, reservation)
            if boundary:
                self.admit_prose_boundary(conn, reservation)
            now = datetime.now(timezone.utc)
            codec = BuildProseBoundaryProposalRecord if boundary else BuildProposalRecord
            result = codec(action_id=reservation.idempotency_key, reservation=reservation, request_fingerprint=reservation.fingerprint,
                after_turn_sequence=conversation[0] - 1, revision=1, state="reserved", created_at=now, updated_at=now,
                claim_expires_at=now + timedelta(seconds=180))
            conn.execute("INSERT INTO agent.build_proposal(action_id,world_id,conversation_id,idempotency_key,revision,payload) VALUES(%s,%s,%s,%s,1,%s)",
                (result.action_id, world, reservation.conversation_id, reservation.idempotency_key, Jsonb(result.model_dump(mode="json"))))
            return result, True

    def get(self, world_id: str, action_id: UUID) -> BuildProposalRecord:
        with unit_of_work(_ready_dsn()) as conn:
            row = conn.execute("SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s", (world_id, action_id)).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("Build proposal unavailable in this World")
        return _load(row)

    def list(self, world_id: str, conversation_id: UUID) -> list[BuildProposalRecord]:
        with unit_of_work(_ready_dsn()) as conn:
            exists = conn.execute("SELECT 1 FROM agent.conversation WHERE world_id=%s AND conversation_id=%s", (world_id, conversation_id)).fetchone()
            if not exists:
                raise ApplicationStateNotFoundError("World conversation unavailable")
            rows = conn.execute("SELECT payload FROM agent.build_proposal WHERE world_id=%s AND conversation_id=%s ORDER BY payload->>'created_at', action_id",
                (world_id, conversation_id)).fetchall()
        return [_load(row) for row in rows if row[0].get("schema_version") in BUILD_MARKDOWN_PROPOSAL_CODECS]

    def advance(self, world_id: str, action_id: UUID, *, expected_revision: int, state: str, **fields) -> BuildProposalRecord:
        allowed = {"reserved": {"authorized", "failed"}, "authorized": {"sdk_entered", "failed"},
            "sdk_entered": {"response_received", "unknown"}, "response_received": {"response_received", "proposed", "failed", "unknown"}}
        allowed_fields = {"authorization", "proposal", "failure_code", "raw_response", "observation"}
        if not set(fields).issubset(allowed_fields):
            raise ValueError("Unsupported Build receipt fields")
        with unit_of_work(_ready_dsn()) as conn:
            row = conn.execute("SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s FOR UPDATE", (world_id, action_id)).fetchone()
            if row is None:
                raise ApplicationStateNotFoundError("Build proposal unavailable in this World")
            previous = _load(row)
            if previous.revision != expected_revision or state not in allowed.get(previous.state, set()):
                raise ApplicationStateConflictError("Build proposal transition is stale or terminal")
            if previous.authorization is not None and "authorization" in fields and fields["authorization"] != previous.authorization:
                raise ApplicationStateConflictError("Build provider authorization is immutable")
            if previous.raw_response is not None and "raw_response" in fields and fields["raw_response"] != previous.raw_response:
                raise ApplicationStateConflictError("Build final writer response is immutable")
            if previous.claim_expires_at <= datetime.now(timezone.utc):
                raise ApplicationStateConflictError("Build proposal worker claim expired")
            if state in {"authorized", "sdk_entered"}:
                _require_origin_claim(conn, previous.reservation)
            if state == "proposed":
                # The proposal owner derives its result from the acknowledged raw
                # final. Caller-created Markdown cannot replace the writer result.
                if type(previous) is BuildProseBoundaryProposalRecord:
                    proposal = normalize_boundary_proposal_output(previous.raw_response)
                else:
                    required_target = None
                    if self.require_native_page_target:
                        from application_state.agent_conversation.build_intentional_response import selected_action
                        from application_state.agent_conversation.native_execution import NativeBuildActionV1

                        turn = _require_origin_claim(conn, previous.reservation)
                        execution = turn.graph_context_execution if turn is not None else None
                        action = getattr(getattr(execution, "policy", None), "action", None)
                        if type(action) is not NativeBuildActionV1:
                            raise ApplicationStateConflictError("Explicit Build target requires its native opening")
                        selected = selected_action(execution)
                        required_target = explicit_build_page_target(action.write_capability, selected)
                        if required_target is None or selected.broker_operation_id != previous.reservation.origin.broker_operation_id:
                            raise ApplicationStateConflictError("Explicit Build target differs from its native opening")
                    proposal = normalize_proposal_output(previous.raw_response,
                        previous.reservation.page_body_offer, previous.reservation.page_end_offer,
                        required_target=required_target)
                if "raw_response" in fields or "proposal" in fields and fields["proposal"] != proposal:
                    raise ApplicationStateConflictError("Build proposal differs from its captured writer result")
                fields["proposal"] = proposal
            updated = {**previous.model_dump(mode="python"), **fields, "state": state,
                "revision": previous.revision + 1, "updated_at": datetime.now(timezone.utc)}
            return _save(conn, previous, updated)

    def report_inserted(self, world_id: str, action_id: UUID, *, expected_revision: int, authorize=None) -> BuildProposalRecord:
        """Client-observed draft insertion; never a durable workspace Save receipt."""
        with unit_of_work(_ready_dsn()) as conn:
            row = conn.execute("SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s FOR UPDATE", (world_id, action_id)).fetchone()
            if row is None:
                raise ApplicationStateNotFoundError("Build proposal unavailable in this World")
            previous = _load(row)
            if previous.inserted_in_draft:
                return previous
            if type(previous) is BuildProseBoundaryProposalRecord:
                raise ApplicationStateConflictError("Build prose insertion requires its exact Review receipt")
            if previous.state != "proposed" or previous.revision != expected_revision:
                raise ApplicationStateConflictError("Build proposal cannot be inserted")
            if authorize is not None:
                authorize()
            return _save(conn, previous, {**previous.model_dump(mode="python"), "inserted_in_draft": True,
                "revision": previous.revision + 1, "updated_at": datetime.now(timezone.utc)})
