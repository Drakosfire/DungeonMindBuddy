"""Shared native writer evidence from actual admitted read records.

The producing input must contain both native evidence and exact surface work.
Rules, authored output and locked Turn acceptance remain separately owned.
No synthetic Plan Turn or second durable inclusion witness is constructed here.
"""
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from . import types as t
from .native_context import SurfaceNativeContextReceiptV1
from .native_execution import NativeWriterAuthorizedV1, SurfaceNativeExecutionV1
from .native_reads import validate_execution_binding
from . import native_corpus as bodies
from . import native_plan_statements as statements
from . import native_plan_assertions as assertions
from .source_writer_output import responses_text_frame, strict_json

SCHEMA = "dmb_surface_native_writer_evidence_v1"


def body_handle(read):
    excerpt = read.excerpt
    if excerpt.selector_policy == "native_full_document_v1":
        return bodies.native_full_document_handle(excerpt.catalog_sha256)
    return bodies.native_body_handle(excerpt.catalog_sha256, excerpt.section.section_id)


def model_frame(receipt, execution):
    """Project the current admitted prefix, without a provider authorization."""
    if (type(receipt), type(execution)) != (SurfaceNativeContextReceiptV1, SurfaceNativeExecutionV1):
        raise ValueError("Native writer requires its exact shared receipt and execution")
    validate_execution_binding(receipt, execution)
    if any(type(event) is NativeWriterAuthorizedV1 for event in execution.events):
        raise ValueError("Native evidence projection requires the prefix before its writer")
    query = receipt.native_query
    partial = (isinstance(receipt.source_authority, t.NativeCorpusUnavailableV1)
        or isinstance(query, statements.NativePlanQueryUnavailableV1)
        or bodies.body_input_partial(execution)
        or statements.input_partial_records(query, execution)
        or assertions.input_partial_records(query, execution))
    return dict(schema=SCHEMA, answer_policy=assertions.POLICY, input_status='partial' if partial else 'complete',
        user_question=execution.policy.action.intent.message,
        native_body_evidence=bodies.model_body_frame_records(receipt.source_authority, execution, body_handle),
        native_statements=statements.model_frame_records(query, execution),
        native_assertions=assertions.model_frame_records(query, execution)
            if isinstance(query, assertions.NativePlanQueryV2) else None)


@dataclass(frozen=True)
class NativeWriterEvidence:
    """Transient supports; eligibility still requires completion/output proof."""
    frame: dict
    work_frame: dict
    authored: tuple
    idempotency_key: UUID
    saved_sections: tuple
    related_pages: tuple
    draft_record: object | None
    body_excerpts: tuple
    native_statements: tuple
    native_assertions: tuple


def model_work_frame(receipt, execution, *, provenance, idempotency_key, work_proof,
                     world_id, conversation_id, turn_id, attempt):
    """Reconstruct real surface work through its owner; no second stored authority."""
    from .native_context import validate_work_context, BuildWorkContextV1, PlanWorkContextV1
    validate_execution_binding(receipt,execution)
    validate_work_context(receipt,provenance)
    action=execution.policy.action
    if (world_id != action.intent.world_id or provenance.surface_instance_id != action.intent.surface_instance_id
            or any(type(value) is not UUID for value in (idempotency_key,conversation_id,turn_id))
            or type(attempt) is not int or attempt < 1):
        raise ValueError('Native writer work differs from its actual submission identity')
    if any(type(event) is NativeWriterAuthorizedV1 for event in execution.events):
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
        return native_work_frame(execution,receipt.work_context.source_basis)
    if isinstance(receipt.work_context,PlanWorkContextV1):
        from .plan_jev_graph_packet import project_native_plan_work, NATIVE_WORK_SCHEMA
        return dict(schema=NATIVE_WORK_SCHEMA,**project_native_plan_work(receipt,execution,provenance,
            idempotency_key,work_proof,conversation_id=conversation_id))
    raise ValueError('Native Play writer requires its actual single-provider work-input owner')


def verify_input_records(receipt, execution, authorization, raw, *, provenance, idempotency_key,
                         work_proof, world_id, conversation_id, turn_id, attempt):
    """Bind one shared native frame to the exact stored producing SDK request."""
    if (type(receipt), type(execution), type(authorization)) != (
            SurfaceNativeContextReceiptV1, SurfaceNativeExecutionV1, NativeWriterAuthorizedV1):
        raise ValueError("Native writer proof requires its concrete shared owner records")
    validate_execution_binding(receipt, execution)
    writers = [event for event in execution.events if type(event) is NativeWriterAuthorizedV1]
    if writers != [authorization] or execution.events[authorization.sequence] != authorization:
        raise ValueError("Native writer proof differs from its unique stored authorization")
    # Reparse actual records, not a legacy policy/view. Later outcomes never add
    # evidence to this producing frame; read owners refuse post-writer acquisition.
    prefix = SurfaceNativeExecutionV1.model_validate_json(execution.model_copy(
        update={"events": execution.events[:authorization.sequence]}).model_dump_json(by_alias=True))
    expected = model_frame(receipt, prefix)
    expected_work = model_work_frame(receipt,prefix,provenance=provenance,idempotency_key=idempotency_key,
        work_proof=work_proof,world_id=world_id,conversation_id=conversation_id,turn_id=turn_id,attempt=attempt)
    work_frame = responses_text_frame(raw,schemas={expected_work['schema']},label='Native surface work')
    if t.canonical_sha256(work_frame) != t.canonical_sha256(expected_work):
        raise ValueError('Native writer changed or omitted its exact surface work')
    body = strict_json(raw)
    frame = responses_text_frame(raw, schemas={SCHEMA}, label="Native writer")
    if ((authorization.provider, authorization.api_mode, authorization.serializer_version)
            != ("openai", "responses", "openai-sdk-json-v1")
            or body.get("model") != authorization.model
            or sha256(raw.encode()).hexdigest() != authorization.envelope_sha256
            or t.canonical_sha256(body.get("tools", [])) != authorization.tool_schema_sha256
            or t.canonical_sha256(frame) != authorization.frame_sha256
            or t.canonical_sha256(expected) != authorization.frame_sha256):
        raise ValueError("Native writer evidence differs from its actual producing SDK request")
    authored,saved_sections,related_pages,draft_record = (),(),(),None
    from .native_context import PlanWorkContextV1,BuildWorkContextV1
    if isinstance(receipt.work_context,PlanWorkContextV1):
        from .surface_evidence_answer import producing_plan_authored_records
        authored=producing_plan_authored_records(receipt.work_context.plan_basis,
            provenance.supporting_work,expected_work,idempotency_key)
    elif isinstance(receipt.work_context,BuildWorkContextV1):
        from .build_primary_context import records
        from .build_draft_context import context_record
        saved_sections=records(prefix,receipt.work_context.source_basis)
        from .build_related_pages import records as related_records
        related_pages=tuple(related_records(prefix))
        if prefix.policy.action.intent.build_draft_context_sha256 is not None:
            draft_record=context_record(prefix).record
    catalogs = {catalog.catalog_sha256: catalog for event in prefix.events
        if isinstance(event, bodies.NativeBodySearchObservedV1) for catalog in event.catalogs}
    body_reads = bodies.selected_body_reads(prefix)
    statement_reads = statements.selected_read_records(prefix)
    assertion_reads = assertions.selected_read_records(prefix)
    return NativeWriterEvidence(frame=expected,work_frame=expected_work,authored=authored,idempotency_key=idempotency_key,
        saved_sections=saved_sections,related_pages=related_pages,draft_record=draft_record,
        body_excerpts=tuple(bodies.NativeBodySupport(body_handle(read), read,
            catalogs[read.excerpt.catalog_sha256]) for read in body_reads),
        native_statements=tuple((row['statement_handle'], event, read) for row, (event, read)
            in zip(expected['native_statements']['statements'], statement_reads, strict=True)),
        native_assertions=tuple((row['assertion_handle'], event, read) for row, (event, read)
            in zip(expected['native_assertions']['assertions'] if expected['native_assertions'] else (),
                assertion_reads, strict=True)))
