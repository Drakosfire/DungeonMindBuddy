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


def validate_native_authoring_binding(completion,receipt,execution,producer,bindings):
    """Stored object acknowledgement uses the actual shared Build action/writer."""
    from .native_context import BuildWorkContextV1
    from .native_execution import NativeBuildActionV1, NativeWriterAuthorizedV1, NATIVE_WRITER_TYPES
    from .build_intentional_response import selected_action
    action=execution.policy.action
    image=isinstance(completion,BuildImagePreparationCompletionV1)
    from uuid import uuid5
    expected_operation='prepare_build_image' if image else 'propose_build_insertion'
    if (not isinstance(completion,(BuildAuthoringCompletionV1,BuildImagePreparationCompletionV1)) or bindings!={}
            or not isinstance(receipt.work_context,BuildWorkContextV1) or not isinstance(action,NativeBuildActionV1)
            or action.write_capability is None or selected_action(execution).operation!=expected_operation
            or completion.context_receipt_sha256!=receipt.context_receipt_sha256
            or completion.action_id!=(uuid5(action.write_capability.idempotency_key,'image') if image else action.write_capability.idempotency_key)):
        raise ValueError('Native authoring acknowledgement differs from its Build action')
    writers=[e for e in execution.events if type(e) in NATIVE_WRITER_TYPES]
    if (len(writers)!=1 or completion.provider_attempt_id!=producer
            or writers[0].provider_attempt_id!=producer or completion.envelope_sha256!=writers[0].envelope_sha256):
        raise ValueError('Native authoring acknowledgement differs from its actual writer')


def normalize_native_authoring(conn,turn,rules_execution,proof,*,trace,work_proof):
    """Locked producer verification delegates raw-output normalization to this object owner."""
    from .native_rules_output import sealed_native_producer,verify_shared_native_producer
    scope=rules_execution.scope
    if ((scope.world_id,scope.conversation_id,scope.turn_id,scope.product_attempt)
            !=(turn.world_id,turn.conversation_id,turn.turn_id,turn.attempt)
            or rules_execution.budget_use.calls or rules_execution.supports):
        raise ValueError('Build authoring requires its exact unused Rules scope')
    capture,_=sealed_native_producer(turn,rules_execution,proof)
    _,frame=verify_shared_native_producer(turn.graph_context_receipt,turn.graph_context_execution,
        rules_execution,proof,capture,trace=trace,idempotency_key=turn.idempotency_key,
        submitted_intent_fingerprint=turn.submitted_intent_fingerprint_v2,world_id=turn.world_id,
        conversation_id=turn.conversation_id,turn_id=turn.turn_id,attempt=turn.attempt,
        provenance=turn.provenance,work_proof=work_proof)
    if frame.lookups:
        raise ValueError('Build authoring cannot omit used Rules')
    action=turn.graph_context_execution.policy.action
    from .build_intentional_response import selected_action
    image=selected_action(turn.graph_context_execution).operation=='prepare_build_image'
    from uuid import uuid5
    action_id=uuid5(action.write_capability.idempotency_key,'image') if image else action.write_capability.idempotency_key
    row=conn.execute('SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s',
        (turn.world_id,action_id)).fetchone()
    if image:
        from application_state.build_proposal.types import BuildImagePreparation
        record=BuildImagePreparation.model_validate(row[0] if row else None)
        if (record.writer_proof is None or record.writer_proof.raw_response!=proof.raw_output_json
                or record.writer_proof.request_json!=proof.prepared_request_json):
            raise ValueError('Native image preparation differs from its sealed producing output/input')
        completion=completion_for_image(record,turn.graph_context_receipt)
        text=BUILD_IMAGE_READY_TEXT
    else:
        record=BuildProposalRecord.model_validate(row[0] if row else None)
        if record.raw_response!=proof.raw_output_json:
            raise ValueError('Native proposal differs from its sealed producing output')
        completion=completion_for_proposal(record,turn.graph_context_receipt)
        text=BUILD_PROPOSAL_READY_TEXT
    validate_stored_proposal(conn,turn,completion)
    return completion,{},text


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
        from .native_context import SurfaceNativeContextReceiptV1,BuildWorkContextV1
        shared=type(receipt) is SurfaceNativeContextReceiptV1
        if shared and not isinstance(receipt.work_context,BuildWorkContextV1):
            raise ValueError('Native proposal requires its actual Build source')
        source=receipt.work_context.source_basis if shared else receipt.source_basis
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
            or basis.document_id != source.document_id
            or basis.registry_revision != source.registry_revision
            or basis.content_sha256 != source.content_sha256
            or basis.visibility != source.visibility
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
            BuildJevActionSelectionV1, BuildReviewedActionSelectionV1,
        )

        if isinstance(
            turn.graph_context_execution.policy, BuildActionControllerWriterPolicyV1
        ):
            choices = [
                e
                for e in turn.graph_context_execution.events
                if isinstance(e, (BuildJevActionSelectionV1, BuildReviewedActionSelectionV1))
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
        if shared:
            from .build_intentional_response import selected_action
            from application_state.build_proposal.types import normalize_proposal_output
            selected=selected_action(turn.graph_context_execution)
            validate_native_authoring_binding(completion,receipt,turn.graph_context_execution,completion.provider_attempt_id,{})
            capability=turn.graph_context_execution.policy.action.write_capability
            if (origin.broker_operation_id!=selected.broker_operation_id
                    or origin.arguments_sha256!=selected.arguments_sha256
                    or reservation.model_dump(mode='json',exclude={'instruction','origin'})
                        !=capability.model_dump(mode='json',exclude={'draft_markdown','instruction','origin'})
                    or reservation.instruction!=turn.user_text
                    or normalize_proposal_output(record.raw_response,reservation.page_body_offer,reservation.page_end_offer)!=record.proposal):
                raise ValueError('Native proposal result differs from its captured action/editor/output')
            responses=[e for e in turn.graph_context_execution.events if e.kind=='provider_outcome'
                and e.provider_attempt_id==completion.provider_attempt_id and e.outcome=='response_received']
            if len(responses)!=1 or responses[0].response_sha256!=sha256(record.raw_response.encode()).hexdigest():
                raise ValueError('Native proposal differs from its acknowledged selected output')
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
            and e.kind in ({"native_writer_authorized_v1", "native_build_writer_authorized_v2"} if shared else {"provider_attempt_authorized_v3"})
        )
        if not shared:
            from .authored_graph_references import validate_stored_writer
            validate_stored_writer(conn, turn, producing)
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



def _native_build(turn):
    from .native_execution import SurfaceNativeExecutionV1,NativeBuildActionV1
    return (type(turn.graph_context_execution) is SurfaceNativeExecutionV1
        and type(turn.graph_context_execution.policy.action) is NativeBuildActionV1)


def validate_prepared_native_authoring(conn,turn,result,*,trace):
    """Recover an admitted immutable object; never admit new prose or provider IO."""
    from .rules_authority_store import load_turn_rules_locked
    from .native_rules_output import sealed_native_producer,verify_captured_output
    from .source_writer_output import require_captured_answer
    from types import SimpleNamespace
    if not _native_build(turn):
        raise ValueError('Prepared native recovery requires its actual Build owner')
    validate_stored_proposal(conn,turn,result.completion)
    current=load_turn_rules_locked(conn,turn)
    if (current is None or current.execution.state not in {'active','unused','failed'}
            or current.execution.budget_use.calls or current.execution.supports):
        raise ValueError('Prepared Build recovery cannot accept used or missing Rules authority')
    row=conn.execute('SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s',
        (turn.world_id,result.completion.action_id)).fetchone()
    if isinstance(result.completion,BuildImagePreparationCompletionV1):
        from application_state.build_proposal.types import BuildImagePreparation
        record=BuildImagePreparation.model_validate(row[0] if row else None)
        raw=record.writer_proof.raw_response
    else:
        record=BuildProposalRecord.model_validate(row[0] if row else None)
        raw=record.raw_response
    producer=result.producing_provider_attempt_id
    capture,_=sealed_native_producer(turn,current.execution,
        SimpleNamespace(producing_provider_attempt_id=producer,raw_output_json=raw))
    encoded=raw.encode('utf-8')
    responses=[e for e in turn.graph_context_execution.events
        if e.kind=='provider_outcome' and e.provider_attempt_id==producer and e.outcome=='response_received']
    if len(responses)!=1:
        raise ValueError('Prepared Build recovery lacks its unique acknowledged writer')
    verify_captured_output(capture,raw_output_json=raw,raw_output_sha256=sha256(encoded).hexdigest(),
        raw_output_utf8_bytes=len(encoded),response_sha256=responses[0].response_sha256)
    require_captured_answer(trace,world_id=turn.world_id,conversation_id=turn.conversation_id,
        turn_id=turn.turn_id,attempt=turn.attempt,provider_attempt_id=producer,
        context_receipt_sha256=turn.graph_context_receipt.context_receipt_sha256,raw_output_json=raw)
    return current.execution.state


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
        ) and not _native_build(turn)
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


def _validate_native_image(turn,completion,image):
    """Existing image owner binds its inert fields to the admitted native writer."""
    from .build_intentional_response import selected_action
    from .native_execution import NativeWriterAuthorizedV1, NATIVE_WRITER_TYPES
    from application_state.build_proposal.types import ImageDirectionV2
    from uuid import NAMESPACE_URL,uuid5
    execution,receipt=turn.graph_context_execution,turn.graph_context_receipt
    validate_native_authoring_binding(completion,receipt,execution,completion.provider_attempt_id,{})
    selected=selected_action(execution)
    cap=execution.policy.action.write_capability
    reservation,proof=image.reservation,image.writer_proof
    origin=reservation.origin
    if proof is None or origin is None:
        raise ValueError('Native image preparation lacks its actual owner proof')
    writer=next(e for e in execution.events if type(e) in NATIVE_WRITER_TYPES)
    decoded=ImageDirectionV2.model_validate_json(proof.raw_response)
    body=json.loads(proof.request_json)
    expected_format=dict(type='json_schema',name='build_image_direction',schema=ImageDirectionV2.model_json_schema(),strict=True)
    responses=[e for e in execution.events if e.kind=='provider_outcome'
        and e.provider_attempt_id==writer.provider_attempt_id and e.outcome=='response_received']
    if (completion_for_image(image,receipt)!=completion
            or image.action_id!=uuid5(cap.idempotency_key,'image')
            or reservation.basis!=cap.basis or reservation.conversation_id!=turn.conversation_id
            or reservation.conversation_id!=cap.conversation_id or reservation.expected_pointer_revision!=cap.expected_pointer_revision
            or origin.durable_turn_id!=turn.turn_id or origin.turn_attempt!=turn.attempt
            or origin.broker_operation_id!=selected.broker_operation_id or origin.arguments_sha256!=selected.arguments_sha256
            or reservation.instruction!=turn.user_text or _image_digest({'instruction':reservation.instruction})!=origin.arguments_sha256
            or turn.idempotency_key!=uuid5(NAMESPACE_URL,f'dmb-agent-turn:{turn.world_id}:{origin.client_turn_id}')
            or (decoded.prompt,decoded.alt,decoded.purpose)!=(image.prompt,image.alt,image.purpose)
            or (proof.authorization.provider_attempt_id,proof.authorization.payload_sha256)!=(writer.provider_attempt_id,writer.envelope_sha256)
            or (proof.authorization.provider,proof.authorization.model,proof.authorization.api_mode)!=(writer.provider,writer.model,writer.api_mode)
            or sha256(proof.request_json.encode()).hexdigest()!=writer.envelope_sha256
            or body.get('tools')!=[] or body.get('text',{}).get('format')!=expected_format
            or len(responses)!=1 or responses[0].response_sha256!=sha256(proof.raw_response.encode()).hexdigest()):
        raise ValueError('Native image preparation differs from its source/selection/writer')


def validate_stored_image(conn, turn, completion):
    from application_state.build_proposal.types import BuildImagePreparation
    from application_state.build_proposal.types import ImageDirection, ImageDirectionV2
    from .types import BuildJevActionSelectionV1, BuildImageActionPolicyV1

    try:
        row = conn.execute(
            "SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s",
            (turn.world_id, completion.action_id),
        ).fetchone()
        image = BuildImagePreparation.model_validate(row[0] if row else None)
        from .native_context import SurfaceNativeContextReceiptV1
        if type(turn.graph_context_receipt) is SurfaceNativeContextReceiptV1:
            return _validate_native_image(turn,completion,image)
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
        direction_type = ImageDirectionV2 if "purpose" in json.loads(proof.raw_response) else ImageDirection
        decoded = direction_type.model_validate_json(proof.raw_response)
        from .authored_graph_references import validate_stored_writer
        validate_stored_writer(conn, turn, writer, proof.request_json)
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
            or getattr(decoded, "purpose", None) != image.purpose
            or (image.purpose is not None) != (execution.policy.image_preparation_policy == "captured_build_image_prompt_alt_purpose_v2")
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
            **({"purpose": record.purpose} if record.purpose is not None else {}),
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
        or not (isinstance(turn.graph_context_execution.policy, BuildImageActionPolicyV1) or _native_build(turn))
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
