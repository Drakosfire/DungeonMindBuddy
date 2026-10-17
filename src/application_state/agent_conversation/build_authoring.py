"""Bind host authoring acknowledgement to its immutable proposal owner result."""

from hashlib import sha256
import json

from application_state.build_proposal.types import BuildProposalRecord
from application_state.errors import ApplicationStateIntegrityError
from .types import BuildAuthoringCompletionV1, BUILD_PROPOSAL_READY_TEXT


def proposal_result_digest(record: BuildProposalRecord) -> str:
    if (
        record.state != "proposed"
        or record.proposal is None
        or record.authorization is None
    ):
        raise ValueError("Only a persisted proposal has a completed result digest")
    return sha256(
        json.dumps(
            record.proposal.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def completion_for_proposal(record, receipt):
    """Pure preparation. complete_turn still verifies the actual owner DB record."""
    digest = proposal_result_digest(record)
    if record.reservation.origin is None:
        raise ValueError("An Agent-origin proposal is required")
    return BuildAuthoringCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_segments=[{"kind": "connective", "text": BUILD_PROPOSAL_READY_TEXT}],
        action_id=record.action_id,
        reservation_sha256=record.request_fingerprint,
        proposal_result_sha256=digest,
        provider_attempt_id=record.authorization.provider_attempt_id,
        envelope_sha256=record.authorization.payload_sha256,
    )


def validate_stored_proposal(conn, turn, completion):
    """Same APP transaction as completion/reload; never call a provider here."""
    if not isinstance(completion, BuildAuthoringCompletionV1):
        return
    row = conn.execute(
        "SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s",
        (turn.world_id, completion.action_id),
    ).fetchone()
    try:
        if row is None:
            raise ValueError("Proposal owner record is missing")
        record = BuildProposalRecord.model_validate(row[0])
        reservation, receipt = record.reservation, turn.graph_context_receipt
        origin, auth = reservation.origin, record.authorization
        basis = reservation.basis
        if (
            record.action_id != completion.action_id
            or reservation.idempotency_key != record.action_id
            or origin is None
            or auth is None
            or receipt is None
            or turn.provenance.surface_id != "build"
            or turn.provenance.primary_work.kind != "build"
            or reservation.basis.world_id != turn.world_id
            or reservation.conversation_id != turn.conversation_id
            or origin.durable_turn_id != turn.turn_id
            or origin.turn_attempt != turn.attempt
            or basis.document_id != receipt.source_basis.document_id
            or basis.registry_revision != receipt.source_basis.registry_revision
            or basis.content_sha256 != receipt.source_basis.content_sha256
            or basis.visibility != receipt.source_basis.visibility
            or completion.reservation_sha256 != record.request_fingerprint
            or completion.proposal_result_sha256 != proposal_result_digest(record)
            or completion.provider_attempt_id != auth.provider_attempt_id
            or completion.envelope_sha256 != auth.payload_sha256
        ):
            raise ValueError(
                "Authoring completion differs from its exact proposal owner record"
            )
        expected_arguments = sha256(
            json.dumps(
                {"instruction": reservation.instruction},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        if origin.arguments_sha256 != expected_arguments:
            raise ValueError(
                "Proposal instruction differs from its selected tool arguments"
            )
        from uuid import NAMESPACE_URL, uuid5

        if turn.idempotency_key != uuid5(
            NAMESPACE_URL, f"dmb-agent-turn:{turn.world_id}:{origin.client_turn_id}"
        ):
            raise ValueError("Proposal client origin differs from its turn")
        producing = next(
            e
            for e in turn.graph_context_execution.events
            if getattr(e, "provider_attempt_id", None) == completion.provider_attempt_id
            and e.kind == "provider_attempt_authorized_v3"
        )
        if (auth.provider, auth.model, auth.api_mode) != (
            producing.provider,
            producing.model,
            producing.api_mode,
        ):
            raise ValueError("Proposal provider identity differs from its writer")
    except (ValueError, TypeError, AttributeError, StopIteration) as exc:
        raise ApplicationStateIntegrityError(
            "Build authoring completion failed proposal-owner integrity validation"
        ) from exc
