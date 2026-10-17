"""APP claim/CAS boundary for a single inert Build Compose proposal."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid5, NAMESPACE_URL

from psycopg.types.json import Jsonb

from application_state.agent_conversation.service import _lock_pointer, _ready_dsn
from application_state.build_proposal.types import BuildProposalRecord, BuildProposalReservation
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from application_state.unit_of_work import unit_of_work


def _load(row) -> BuildProposalRecord:
    if row[0].get('schema_version') != 'dmb_build_document_proposal_v1':
        raise ApplicationStateNotFoundError('Markdown proposal unavailable')
    return BuildProposalRecord.model_validate(row[0])


def _save(conn, previous, updated):
    checked = BuildProposalRecord.model_validate(updated)
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


class BuildProposalService:
    def reserve(self, reservation: BuildProposalReservation) -> tuple[BuildProposalRecord, bool]:
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
            now = datetime.now(timezone.utc)
            result = BuildProposalRecord(action_id=reservation.idempotency_key, reservation=reservation, request_fingerprint=reservation.fingerprint,
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
        return [_load(row) for row in rows if row[0].get("schema_version") == "dmb_build_document_proposal_v1"]

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
            if previous.claim_expires_at <= datetime.now(timezone.utc):
                raise ApplicationStateConflictError("Build proposal worker claim expired")
            if state in {"authorized", "sdk_entered"}:
                _require_origin_claim(conn, previous.reservation)
            updated = {**previous.model_dump(mode="python"), **fields, "state": state,
                "revision": previous.revision + 1, "updated_at": datetime.now(timezone.utc)}
            return _save(conn, previous, updated)

    def report_inserted(self, world_id: str, action_id: UUID, *, expected_revision: int) -> BuildProposalRecord:
        """Client-observed draft insertion; never a durable workspace Save receipt."""
        with unit_of_work(_ready_dsn()) as conn:
            row = conn.execute("SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s FOR UPDATE", (world_id, action_id)).fetchone()
            if row is None:
                raise ApplicationStateNotFoundError("Build proposal unavailable in this World")
            previous = _load(row)
            if previous.inserted_in_draft:
                return previous
            if previous.state != "proposed" or previous.revision != expected_revision:
                raise ApplicationStateConflictError("Build proposal cannot be inserted")
            return _save(conn, previous, {**previous.model_dump(mode="python"), "inserted_in_draft": True,
                "revision": previous.revision + 1, "updated_at": datetime.now(timezone.utc)})
