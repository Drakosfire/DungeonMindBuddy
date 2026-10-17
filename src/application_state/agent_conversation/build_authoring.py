"""Bind host authoring acknowledgement to its immutable proposal owner result."""

from hashlib import sha256
import json

from application_state.build_proposal.types import BuildProposalRecord
from application_state.errors import ApplicationStateIntegrityError
from .types import (
    BuildAuthoringCompletionV1,
    BUILD_PROPOSAL_READY_TEXT,
    BuildImagePreparationCompletionV1,
    PlanWorldGraphConnectiveSegmentV1,
    BUILD_IMAGE_READY_TEXT,
)


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
    from .types import BuildImagePreparationCompletionV1

    if isinstance(completion, BuildImagePreparationCompletionV1):
        return validate_stored_image(conn, turn, completion)
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
        from .types import (
            BuildActionControllerWriterPolicyV1,
            BuildJevActionSelectionV1,
        )

        if isinstance(
            turn.graph_context_execution.policy, BuildActionControllerWriterPolicyV1
        ):
            choices = [
                e
                for e in turn.graph_context_execution.events
                if isinstance(e, BuildJevActionSelectionV1)
            ]
            if (
                len(choices) != 1
                or choices[0].operation != "propose_build_insertion"
                or choices[0].broker_operation_id != origin.broker_operation_id
                or choices[0].arguments_sha256 != origin.arguments_sha256
            ):
                raise ValueError(
                    "Proposal origin differs from the controller-selected operation"
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


def recover_prepared_proposal(service, turn, action_id):
    """Finish only an already persisted, acknowledged proposal; never dispatch."""
    from application_state.build_proposal.service import BuildProposalService
    from application_state.errors import ApplicationStateNotFoundError
    from .types import BuildActionControllerWriterPolicyV1, TurnResult

    if (
        turn.status not in {"running", "interrupted"}
        or turn.graph_context_execution is None
        or not isinstance(
            turn.graph_context_execution.policy, BuildActionControllerWriterPolicyV1
        )
    ):
        return None
    try:
        record = BuildProposalService().get(turn.world_id, action_id)
    except ApplicationStateNotFoundError:
        return None
    if record.state != "proposed":
        return None
    completion = completion_for_proposal(record, turn.graph_context_receipt)
    # The completion transaction independently validates the actual proposal,
    # turn, source, action selection, writer acknowledgement and result digest.
    return service.recover_prepared_build_turn(
        TurnResult(
            world_id=turn.world_id,
            conversation_id=turn.conversation_id,
            turn_id=turn.turn_id,
            expected_revision=turn.revision,
            assistant_text=BUILD_PROPOSAL_READY_TEXT,
            completion=completion,
            producing_provider_attempt_id=record.authorization.provider_attempt_id,
            claim_graph_event_ids={},
        )
    )


def validate_stored_image(conn, turn, completion):
    from application_state.build_proposal.types import BuildImagePreparation
    from application_state.build_proposal.types import ImageDirection
    from .types import BuildJevActionSelectionV1, BuildImageActionPolicyV1

    try:
        row = conn.execute(
            "SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s",
            (turn.world_id, completion.action_id),
        ).fetchone()
        image = BuildImagePreparation.model_validate(row[0] if row else None)
        origin = image.reservation.origin
        execution = turn.graph_context_execution
        proof = image.writer_proof
        receipt = turn.graph_context_receipt
        if (
            proof is None
            or origin is None
            or receipt is None
            or not isinstance(execution.policy, BuildImageActionPolicyV1)
        ):
            raise ValueError("Image completion lacks its owned proof")
        selected = next(
            e for e in execution.events if isinstance(e, BuildJevActionSelectionV1)
        )
        writer = next(
            e
            for e in execution.events
            if e.kind == "provider_attempt_authorized_v3"
            and e.provider_attempt_id == completion.provider_attempt_id
        )
        decoded = ImageDirection.model_validate_json(proof.raw_response)
        writer_body = json.loads(proof.request_json)
        packet = json.loads(writer_body["input"])
        captured = packet["captured_capability"]
        basis = image.reservation.basis
        from uuid import NAMESPACE_URL, uuid5

        if (
            completion_for_image(image, receipt) != completion
            or origin.durable_turn_id != turn.turn_id
            or origin.turn_attempt != turn.attempt
            or image.reservation.conversation_id != turn.conversation_id
            or turn.idempotency_key
            != uuid5(
                NAMESPACE_URL, f"dmb-agent-turn:{turn.world_id}:{origin.client_turn_id}"
            )
            or basis.world_id != turn.world_id
            or turn.provenance.surface_id != "build"
            or basis.document_id != receipt.source_basis.document_id
            or basis.registry_revision != receipt.source_basis.registry_revision
            or basis.content_sha256 != receipt.source_basis.content_sha256
            or basis.visibility != receipt.source_basis.visibility
            or packet["source_basis"] != basis.model_dump(mode="json")
            or packet["instruction"] != image.reservation.instruction
            or packet["instruction"] != turn.user_text
            or _image_digest(captured) != selected.capability_sha256
            or captured["basis"] != basis.model_dump(mode="json")
            or captured["draft_markdown"] != packet["draft_markdown"]
            or sha256(packet["draft_markdown"].encode()).hexdigest()
            != basis.draft_sha256
            or uuid5(__import__("uuid").UUID(captured["idempotency_key"]), "image")
            != image.action_id
            or captured["conversation_id"] != str(turn.conversation_id)
            or captured["expected_pointer_revision"]
            != image.reservation.expected_pointer_revision
            or writer_body.get("tools") != []
            or writer_body["text"]["format"]["type"] != "json_schema"
            or _image_digest(writer_body["text"]["format"]["schema"])
            != execution.policy.image_preparation_schema_sha256
            or decoded.prompt != image.prompt
            or decoded.alt != image.alt
            or selected.operation != "prepare_build_image"
            or selected.broker_operation_id != origin.broker_operation_id
            or selected.arguments_sha256 != origin.arguments_sha256
            or origin.arguments_sha256
            != sha256(
                json.dumps(
                    {"instruction": image.reservation.instruction},
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode()
            ).hexdigest()
            or proof.authorization.provider_attempt_id != writer.provider_attempt_id
            or proof.authorization.payload_sha256 != writer.envelope_sha256
            or sha256(proof.request_json.encode()).hexdigest() != writer.envelope_sha256
            or (
                proof.authorization.provider,
                proof.authorization.model,
                proof.authorization.api_mode,
            )
            != (writer.provider, writer.model, writer.api_mode)
        ):
            raise ValueError(
                "Image preparation differs from its source/selection/writer"
            )
    except (ValueError, TypeError, KeyError, AttributeError, StopIteration) as exc:
        raise ApplicationStateIntegrityError(
            "Build image completion failed owner integrity validation"
        ) from exc


def _image_digest(value):
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def result_digest(record):
    return _image_digest(
        {
            "prompt": record.prompt,
            "alt": record.alt,
            "writer_proof": record.writer_proof.model_dump(mode="json"),
        }
    )


def completion_for_image(record, receipt):
    if record.writer_proof is None:
        raise ValueError("Image preparation has no acknowledged writer")
    auth = record.writer_proof.authorization
    return BuildImagePreparationCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_segments=[
            PlanWorldGraphConnectiveSegmentV1(
                kind="connective", text=BUILD_IMAGE_READY_TEXT
            )
        ],
        action_id=record.action_id,
        reservation_sha256=record.request_fingerprint,
        preparation_result_sha256=result_digest(record),
        provider_attempt_id=auth.provider_attempt_id,
        envelope_sha256=auth.payload_sha256,
    )


def recover_prepared_image(service, turn, action_id, owner):
    from uuid import uuid5
    from application_state.build_proposal.images import BuildImageService
    from application_state.errors import ApplicationStateNotFoundError
    from .types import BuildImageActionPolicyV1, TurnResult

    if (
        turn.status not in {"running", "interrupted"}
        or turn.graph_context_execution is None
        or not isinstance(turn.graph_context_execution.policy, BuildImageActionPolicyV1)
        or not owner
    ):
        return None
    try:
        image = BuildImageService().get(uuid5(action_id, "image"), owner)
    except ApplicationStateNotFoundError:
        return None
    completion = completion_for_image(image, turn.graph_context_receipt)
    return service.recover_prepared_build_turn(
        TurnResult(
            world_id=turn.world_id,
            conversation_id=turn.conversation_id,
            turn_id=turn.turn_id,
            expected_revision=turn.revision,
            assistant_text=BUILD_IMAGE_READY_TEXT,
            completion=completion,
            producing_provider_attempt_id=completion.provider_attempt_id,
            claim_graph_event_ids={},
        )
    )
