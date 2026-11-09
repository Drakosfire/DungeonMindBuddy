"""Shared native writer evidence from actual admitted read records.

The producing input must contain both native evidence and exact surface work.
Rules, authored output and locked Turn acceptance remain separately owned.
No synthetic Plan Turn or second durable inclusion witness is constructed here.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from . import types as t
from .native_context import SurfaceNativeContextReceiptV1
from .native_execution import NativeWriterAuthorizedV1, SurfaceNativeExecutionV1, NATIVE_WRITER_TYPES
from .native_reads import validate_execution_binding
from . import native_corpus as bodies
from . import native_plan_statements as statements
from . import native_plan_assertions as assertions
from .source_writer_output import responses_text_frame, strict_json

LEGACY_SCHEMA = "dmb_surface_native_writer_evidence_v1"
SCHEMA = "dmb_surface_native_writer_evidence_v2"
AUTHORING_GUIDANCE = ('\nUse surface_work as the authored page and editor context. '
    'Use native_evidence as supplied World material; preserve uncertainty, attribution and temporal qualifications. '
    'Authored drafts and proposed ideas do not establish played events. '
    'Local entity and citation aliases select supplied records; do not treat aliases as names or infer missing identities.')


def json_container_count(value):
    """Existing conservative SDK estimate; shared by host and APP admission."""
    if isinstance(value, Mapping):
        return 1 + sum(json_container_count(item) for item in value.values())
    if isinstance(value, list):
        return 1 + sum(json_container_count(item) for item in value)
    return 0


def output_request_fields(reserve):
    """Zero is no APP reservation; omit the SDK cap rather than sending zero."""
    if type(reserve) is not int or reserve < 0:
        raise ValueError('Writer output reservation must be nonnegative')
    return {} if reserve == 0 else {'max_output_tokens': reserve}


def validate_output_request(body, reserve):
    expected=output_request_fields(reserve)
    actual={key:body[key] for key in ('max_output_tokens',) if key in body}
    if actual != expected or reserve > 0 and type(body.get("max_output_tokens")) is not int:
        raise ValueError('Writer output parameter differs from its frozen allowance')


def body_handle(read):
    excerpt = read.excerpt
    if excerpt.selector_policy == "native_full_document_v1":
        return bodies.native_full_document_handle(excerpt.catalog_sha256)
    return bodies.native_body_handle(excerpt.catalog_sha256, excerpt.section.section_id)


def model_frame(receipt, execution, *, schema=SCHEMA):
    """Current semantic projection; V1 remains an exact historical input codec."""
    if schema not in {LEGACY_SCHEMA, SCHEMA}:
        raise ValueError('Unknown native writer evidence presentation')
    if (type(receipt), type(execution)) != (SurfaceNativeContextReceiptV1, SurfaceNativeExecutionV1):
        raise ValueError("Native writer requires its exact shared receipt and execution")
    validate_execution_binding(receipt, execution)
    if any(type(event) in NATIVE_WRITER_TYPES for event in execution.events):
        raise ValueError("Native evidence projection requires the prefix before its writer")
    query = receipt.native_query
    partial = (isinstance(receipt.source_authority, t.NativeCorpusUnavailableV1)
        or isinstance(query, statements.NativePlanQueryUnavailableV1)
        or bodies.body_input_partial(execution)
        or statements.input_partial_records(query, execution)
        or assertions.input_partial_records(query, execution))
    return dict(schema=schema, answer_policy=assertions.POLICY, input_status='partial' if partial else 'complete',
        user_question=execution.policy.action.intent.message,
        native_body_evidence=bodies.model_body_frame_records(receipt.source_authority, execution, body_handle),
        native_statements=statements.model_frame_records(query, execution),
        native_assertions=assertions.model_frame_records(query, execution,
            schema='dmb_plan_native_assertion_frame_v1' if schema == LEGACY_SCHEMA else 'dmb_native_assertion_frame_v2')
            if isinstance(query, assertions.NativePlanQueryV2) else None)


def model_input_frame(receipt,execution):
    from .native_evidence_view import semantic_frame
    return semantic_frame(model_frame(receipt,execution))


@dataclass(frozen=True)
class NativeWriterEvidence:
    """Transient supports; eligibility still requires completion/output proof."""
    frame: dict
    work_frame: dict
    output_work_frame: dict
    authored: tuple
    idempotency_key: UUID
    saved_sections: tuple
    related_pages: tuple
    draft_record: object | None
    body_excerpts: tuple
    native_statements: tuple
    native_assertions: tuple
    authored_local: bool = False
    build_local: bool = False


def model_work_frame(receipt, execution, *, provenance, idempotency_key, work_proof,
                     world_id, conversation_id, turn_id, attempt, play_context_receipt=None):
    """Reconstruct real surface work through its owner; no second stored authority."""
    from .native_context import validate_work_context, BuildWorkContextV1, PlanWorkContextV1
    validate_execution_binding(receipt,execution)
    validate_work_context(receipt,provenance,play_context_receipt=play_context_receipt)
    action=execution.policy.action
    from .authored_graph_references import validate_native_capture_identity
    validate_native_capture_identity(execution, turn_id=turn_id, conversation_id=conversation_id,
        attempt=attempt, fingerprint=t.submitted_turn_intent_fingerprint_v2(action.intent))
    if (world_id != action.intent.world_id or provenance.surface_instance_id != action.intent.surface_instance_id
            or any(type(value) is not UUID for value in (idempotency_key,conversation_id,turn_id))
            or type(attempt) is not int or attempt < 1):
        raise ValueError('Native writer work differs from its actual submission identity')
    if any(type(event) in NATIVE_WRITER_TYPES for event in execution.events):
        raise ValueError('Native work projection requires the prefix before its writer')
    if isinstance(receipt.work_context,BuildWorkContextV1):
        from .build_primary_context import native_work_frame
        from .build_draft_context import context_record, validate_native_record
        if not isinstance(work_proof,dict) or work_proof:
            raise ValueError('Native Build work must use its captured records, not supplied bodies')
        if action.intent.build_draft_context_sha256 is not None:
            validate_native_record(context_record(execution).record,receipt,execution,world_id=world_id,
                conversation_id=conversation_id,turn_id=turn_id,attempt=attempt,
                submitted_intent_fingerprint=t.submitted_turn_intent_fingerprint_v2(action.intent))
        if action.write_capability is not None and action.write_capability.conversation_id != conversation_id:
            raise ValueError('Native Build writer capability belongs to another conversation')
        from .build_intentional_response import validate_turn_arguments
        validate_turn_arguments(execution,user_text=action.intent.message,turn_id=turn_id,attempt=attempt)
        frame = native_work_frame(execution,receipt.work_context.source_basis)
        from .authored_graph_references import native_writer_context
        authored = native_writer_context(execution)
        return frame if authored is None else frame | {'authored_references': authored}
    if isinstance(receipt.work_context,PlanWorkContextV1):
        from .plan_jev_graph_packet import project_native_plan_work, NATIVE_WORK_SCHEMA
        frame = dict(schema=NATIVE_WORK_SCHEMA,**project_native_plan_work(receipt,execution,provenance,
            idempotency_key,work_proof,conversation_id=conversation_id))
        from .authored_graph_references import native_writer_context
        authored = native_writer_context(execution)
        from .build_related_pages import project as related_project
        related = related_project(execution)
        if related is not None:
            frame = frame | {'related_authored_pages': related}
        return frame if authored is None else frame | {'authored_references': authored}
    from .native_context import PlayWorkContextV1
    if isinstance(receipt.work_context,PlayWorkContextV1):
        from .native_play_work import project_work
        return project_work(receipt.work_context,provenance,idempotency_key,work_proof)
    raise ValueError('Native writer requires its actual surface work owner')


def authoring_input(native_context, capability, instruction, operation):
    """Host-only producer material; actual APP admission still joins locked state."""
    if not isinstance(native_context,tuple) or len(native_context)!=3:
        raise ValueError('Native authoring requires concrete context, execution and submission')
    receipt,execution,work=native_context
    from .native_execution import NativeBuildActionV1
    from .build_intentional_response import selected_action
    if type(execution) is not SurfaceNativeExecutionV1 or type(execution.policy.action) is not NativeBuildActionV1:
        raise ValueError('Native authoring requires the actual Build action')
    action=execution.policy.action
    selected=selected_action(execution)
    if (operation not in {'propose_build_insertion','prepare_build_image'}
            or selected.operation!=operation or action.write_capability is None
            or instruction!=action.intent.message
            or capability.model_dump(mode='json',exclude={'instruction','origin'})
                !=action.write_capability.model_dump(mode='json',exclude={'instruction','origin'})):
        raise ValueError('Native authoring differs from its selected operation or captured editor')
    if operation=='propose_build_insertion':
        origin=capability.origin
        if (origin is None or origin.durable_turn_id!=work['turn_id']
                or origin.turn_attempt!=work['attempt'] or capability.conversation_id!=work['conversation_id']
                or origin.broker_operation_id!=selected.broker_operation_id
                or origin.arguments_sha256!=selected.arguments_sha256):
            raise ValueError('Native proposal origin differs from its actual selected action')
    from .native_build_work_view import semantic_frame as build_work_view
    return dict(native_evidence=model_input_frame(receipt,execution),
        surface_work=build_work_view(model_work_frame(receipt,execution,**work),execution))


def _input_frames(raw,execution,work_schema):
    """One actual producer packet, selected by the stored operation."""
    from .native_execution import NativeBuildActionV1
    from .build_intentional_response import selected_action
    selected=selected_action(execution) if isinstance(execution.policy.action,NativeBuildActionV1) else None
    operation=None if selected is None else selected.operation
    schema={'propose_build_insertion':'dmb_build_compose_input_v1',
        'prepare_build_image':'dmb_build_image_direction_input_v1'}.get(operation)
    if schema is None:
        from .native_evidence_view import semantic_frame_in_request
        semantic=semantic_frame_in_request(strict_json(raw),legacy_schemas={LEGACY_SCHEMA,SCHEMA})
        from .plan_jev_graph_packet import NATIVE_WORK_SCHEMA as PLAN_WORK_SCHEMA
        from .native_plan_work_view import frame_in_request
        from .native_play_work import SCHEMA as PLAY_WORK_SCHEMA
        if work_schema == PLAY_WORK_SCHEMA:
            from .native_play_work import frame_in_request as play_frame
            work = play_frame(strict_json(raw))
        elif work_schema == PLAN_WORK_SCHEMA:
            work = frame_in_request(strict_json(raw))
            from .native_execution import NativePlanActionV2
            if type(execution.policy.action) is NativePlanActionV2 and work is None:
                raise ValueError('Current Plan saved-page work requires its semantic producer frame')
        else:
            from .native_build_work_view import frame_in_request as build_frame
            work = build_frame(strict_json(raw))
        return (semantic if semantic is not None else responses_text_frame(raw,schemas={LEGACY_SCHEMA,SCHEMA},label='Native writer'),
            work if work is not None else responses_text_frame(raw,schemas={work_schema},label='Native surface work'))
    body=strict_json(raw)
    if (not isinstance(body,dict) or not isinstance(body.get('input'),str) or 'messages' in body
            or body.get('tools',[])!=[] or body.get('tool_choice') not in (None,'none')):
        raise ValueError('Native authoring requires its one exact producer packet')
    packet=strict_json(body['input'])
    task={'propose_build_insertion':'compose_current_page',
        'prepare_build_image':'prepare_image_direction'}[operation]
    if (not isinstance(packet,dict) or not (
            packet.get('schema')==schema and 'task' not in packet
            or packet.get('task')==task and 'schema' not in packet)):
        raise ValueError('Native authoring requires its selected producer kind')
    from .native_build_work_view import is_semantic_frame as semantic_build_work
    if ('task' in packet) != semantic_build_work(packet.get('surface_work')):
        raise ValueError('Native authoring cannot mix historical and current work carriers')
    if 'task' in packet:
        allowed={'task','recent_dialogue','source_class','source_title','instruction',
            'native_evidence','surface_work','rules_evidence','page_body_offer','page_end_offer'}
        if set(packet)-allowed:
            raise ValueError('Unclassified semantic Build authoring fields')
    if packet.get('instruction')!=execution.policy.action.intent.message:
        raise ValueError('Native authoring instruction differs from selected work')
    if any(key in packet for key in ('source_basis','draft_markdown','captured_capability',
            'related_authored_pages','authored_reference_passages')):
        raise ValueError('Native authoring cannot duplicate or substitute work/source bodies')
    return packet.get('native_evidence'),packet.get('surface_work')


def verify_input_records(receipt, execution, authorization, raw, *, provenance, idempotency_key,
                         work_proof, world_id, conversation_id, turn_id, attempt, play_context_receipt=None):
    """Bind one shared native frame to the exact stored producing SDK request."""
    if ((type(receipt), type(execution)) != (SurfaceNativeContextReceiptV1, SurfaceNativeExecutionV1)
            or type(authorization) not in NATIVE_WRITER_TYPES):
        raise ValueError("Native writer proof requires its concrete shared owner records")
    validate_execution_binding(receipt, execution)
    writers = [event for event in execution.events if type(event) in NATIVE_WRITER_TYPES]
    if writers != [authorization] or execution.events[authorization.sequence] != authorization:
        raise ValueError("Native writer proof differs from its unique stored authorization")
    # Reparse actual records, not a legacy policy/view. Later outcomes never add
    # evidence to this producing frame; read owners refuse post-writer acquisition.
    prefix = SurfaceNativeExecutionV1.model_validate_json(execution.model_copy(
        update={"events": execution.events[:authorization.sequence]}).model_dump_json(by_alias=True))
    expected_work = model_work_frame(receipt,prefix,provenance=provenance,idempotency_key=idempotency_key,
        work_proof=work_proof,world_id=world_id,conversation_id=conversation_id,turn_id=turn_id,attempt=attempt,
        play_context_receipt=play_context_receipt)
    frame,work_frame = _input_frames(raw,prefix,expected_work['schema'])
    from .native_execution import NativeBuildWriterAuthorizedV2
    from .native_build_work_view import is_semantic_frame as semantic_build_work
    if type(authorization) is NativeBuildWriterAuthorizedV2:
        if not semantic_build_work(work_frame):
            raise ValueError('Build work authorization requires its current semantic carrier')
        if authorization.work_frame_sha256 != t.canonical_sha256(expected_work):
            raise ValueError('Build writer complete work commitment differs from its producing catalog')
    elif semantic_build_work(work_frame):
        raise ValueError('Semantic Build work requires its complete authorization commitment')
    if not isinstance(frame,dict):
        raise ValueError('Native writer requires its exact evidence presentation')
    from .native_evidence_view import is_semantic_frame,expected_semantic_frame,output_frame
    host = model_frame(receipt,prefix) if is_semantic_frame(frame) else model_frame(receipt,prefix,schema=frame.get('schema'))
    expected = expected_semantic_frame(host, frame) if is_semantic_frame(frame) else host
    schema_frame = output_frame(host,expected)
    from .native_plan_work_view import is_semantic_frame as semantic_work, semantic_frame as plan_work_view
    from .native_play_work import is_semantic_frame as semantic_play, semantic_frame as play_work_view
    play_local = semantic_play(work_frame)
    authored_local = semantic_work(work_frame) or play_local
    from .native_build_work_view import is_semantic_frame as semantic_build, semantic_frame as build_work_view
    build_local = semantic_build(work_frame)
    expected_wire_work = (build_work_view(expected_work,prefix) if build_local
        else play_work_view(expected_work) if play_local
        else plan_work_view(expected_work,prefix) if authored_local else expected_work)
    if t.canonical_sha256(work_frame) != t.canonical_sha256(expected_wire_work):
        raise ValueError('Native writer changed or omitted its exact surface work')
    body = strict_json(raw)
    from .native_execution import NativeWriterEstimatedBudgetV1
    if isinstance(execution.policy.writer_context_budget, NativeWriterEstimatedBudgetV1):
        # Trusted host estimation has the same boundary as controller accounting.
        # APP proves frozen policy, role, allowance and exact producing bytes;
        # it must not reinterpret token estimates as serialized byte counts.
        from .build_decision_context import validate_accounting
        validate_accounting(authorization, execution, provider_index=sum(
            isinstance(e, t.ProviderAttemptAuthorizedEventV1) for e in prefix.events))
    elif authorization.input_tokens != len(raw.encode()) + 64 * (1 + json_container_count(body)):
        raise ValueError('Native writer byte accounting differs from its historical contract')
    if ((authorization.provider, authorization.api_mode, authorization.serializer_version)
            != ("openai", "responses", "openai-sdk-json-v1")
            or body.get("model") != authorization.model
            or sha256(raw.encode()).hexdigest() != authorization.envelope_sha256
            or t.canonical_sha256(body.get("tools", [])) != authorization.tool_schema_sha256
            or t.canonical_sha256(frame) != authorization.frame_sha256
            or t.canonical_sha256(expected) != authorization.frame_sha256):
        raise ValueError("Native writer evidence differs from its actual producing SDK request")
    validate_output_request(body,authorization.output_token_reserve)
    from .build_related_pages import records as related_records
    related_pages = tuple(related_records(prefix))
    authored,saved_sections,draft_record = (),(),None
    from .native_context import PlanWorkContextV1,BuildWorkContextV1
    if isinstance(receipt.work_context,PlanWorkContextV1):
        from .surface_evidence_answer import producing_plan_authored_records
        authored=producing_plan_authored_records(receipt.work_context.plan_basis,
            provenance.supporting_work,expected_work,idempotency_key)
    elif play_local:
        from .native_play_work import producing_authored_records
        authored=producing_authored_records(receipt.work_context,provenance,expected_work,idempotency_key)
    elif isinstance(receipt.work_context,BuildWorkContextV1):
        from .build_primary_context import records
        from .build_draft_context import context_record
        saved_sections=records(prefix,receipt.work_context.source_basis)
        from .build_related_pages import records as related_records
        related_pages=tuple(related_records(prefix))
        if prefix.policy.action.intent.build_draft_context_sha256 is not None:
            draft_record=context_record(prefix).record
    return NativeWriterEvidence(frame=schema_frame,work_frame=expected_work,output_work_frame=expected_work if build_local else expected_work | expected_wire_work,
        authored=authored,idempotency_key=idempotency_key,
        authored_local=authored_local,build_local=build_local,
        saved_sections=saved_sections,related_pages=related_pages,draft_record=draft_record,
        **read_evidence_records(prefix,expected))


def read_evidence_records(prefix, frame):
    """Project the exact included read records through their native owners."""
    catalogs = bodies.acquired_body_catalogs(prefix)
    body_reads = bodies.selected_body_reads(prefix)
    statement_reads = statements.selected_read_records(prefix)
    assertion_reads = assertions.selected_read_records(prefix)
    return dict(body_excerpts=tuple(bodies.NativeBodySupport(row['excerpt_handle'], read,
            catalogs[read.excerpt.catalog_sha256]) for row,read in zip(frame['native_body_evidence']['excerpts'],body_reads,strict=True)),
        native_statements=tuple((row['statement_handle'], event, read) for row, (event, read)
            in zip(frame['native_statements']['statements'], statement_reads, strict=True)),
        native_assertions=tuple((row['assertion_handle'], event, read) for row, (event, read)
            in zip(frame['native_assertions']['assertions'] if frame['native_assertions'] else (),
                assertion_reads, strict=True)))
