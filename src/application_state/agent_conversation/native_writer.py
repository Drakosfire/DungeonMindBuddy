"""Shared native writer evidence from actual admitted read records.

This proof covers native evidence, not surface work, Rules or output acceptance.
Those owners must verify their actual SDK input/output before shared Turn activation.
No synthetic Plan Turn or second durable inclusion witness is constructed here.
"""
from dataclasses import dataclass
from hashlib import sha256

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
    return dict(schema=SCHEMA, user_question=execution.policy.action.intent.message,
        native_body_evidence=bodies.model_body_frame_records(receipt.source_authority, execution, body_handle),
        native_statements=statements.model_frame_records(query, execution),
        native_assertions=assertions.model_frame_records(query, execution)
            if isinstance(query, assertions.NativePlanQueryV2) else None)


@dataclass(frozen=True)
class NativeWriterEvidence:
    """Transient supports; eligibility still requires completion/output proof."""
    frame: dict
    body_excerpts: tuple
    native_statements: tuple
    native_assertions: tuple


def verify_input_records(receipt, execution, authorization, raw):
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
    catalogs = {catalog.catalog_sha256: catalog for event in prefix.events
        if isinstance(event, bodies.NativeBodySearchObservedV1) for catalog in event.catalogs}
    body_reads = bodies.selected_body_reads(prefix)
    statement_reads = statements.selected_read_records(prefix)
    assertion_reads = assertions.selected_read_records(prefix)
    return NativeWriterEvidence(frame=expected,
        body_excerpts=tuple(bodies.NativeBodySupport(body_handle(read), read,
            catalogs[read.excerpt.catalog_sha256]) for read in body_reads),
        native_statements=tuple((row['statement_handle'], event, read) for row, (event, read)
            in zip(expected['native_statements']['statements'], statement_reads, strict=True)),
        native_assertions=tuple((row['assertion_handle'], event, read) for row, (event, read)
            in zip(expected['native_assertions']['assertions'] if expected['native_assertions'] else (),
                assertion_reads, strict=True)))
