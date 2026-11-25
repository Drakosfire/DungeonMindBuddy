"""Shared native writer evidence from actual admitted read records.

The producing input must contain both native evidence and exact surface work.
Rules, authored output and locked Turn acceptance remain separately owned.
No synthetic Plan Turn or second durable inclusion witness is constructed here.
"""
import re
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


def _writer_assertion_reads(execution, *, passages_only):
    records = assertions.selected_read_records(execution)
    if not passages_only or not records:
        return records
    campaigns = {support.catalog.source.registered_campaign_id
                 for support in bodies.writer_passage_supports(execution, body_handle)}
    if len(campaigns) != 1 or None in campaigns:
        return records
    campaign, = campaigns
    from .corpus_source_search import session_cutoff
    cutoff = session_cutoff(execution.policy.action.intent.message)
    included = []
    for event, read in records:
        metadata = read.assertion.metadata
        scopes = {binding.value for binding in metadata.scope
                  if binding.axis == "dungeonbuddy.scope:campaign"}
        if scopes and campaign not in scopes:
            continue
        if cutoff is not None and campaign in scopes:
            temporal = metadata.temporal_scope
            if temporal.kind == "domain_ref" and temporal.schema_term == "dungeonbuddy.time:fictional_anchor_v1":
                payload = temporal.payload
                episode = payload.get("episode") if isinstance(payload, Mapping) else None
                session = re.fullmatch(r"session-(\d+)", episode) if isinstance(episode, str) else None
                if session is not None and int(session[1]) > int(cutoff[1]):
                    continue
        included.append((event, read))
    return tuple(included)


def _validate_writer_binding(receipt, execution):
    from .native_context import BuildPendingContextReceiptV1
    from .native_execution import BuildPendingExecutionV1
    if (type(receipt), type(execution)) == (BuildPendingContextReceiptV1, BuildPendingExecutionV1):
        from .build_source_free import validate_pending_execution_binding
        validate_pending_execution_binding(receipt, execution)
    else:
        validate_execution_binding(receipt, execution)


def _pending_model_frame(receipt, execution, *, schema, passages_only):
    from .build_source_free import effective_pending_source
    from .retained_conversation import native_frame_rows
    if schema != SCHEMA:
        raise ValueError('Pending Build has no historical writer evidence presentation')
    _validate_writer_binding(receipt, execution)
    if any(type(event) in NATIVE_WRITER_TYPES for event in execution.events):
        raise ValueError('Pending evidence projection requires its prefix before the writer')
    source = effective_pending_source(receipt, execution)
    authority, query = source if source is not None else (None, None)
    body_frame = bodies.model_body_frame_records(authority, execution, body_handle,
        passages_only=passages_only)
    if authority is None:
        body_frame['source_authority_status'] = 'not_prepared'
    body_frame['excerpts'].extend(native_frame_rows(execution, authority, body_handle))
    partial = (source is None or isinstance(query, statements.NativePlanQueryUnavailableV1)
        or bodies.body_input_partial(execution) or statements.input_partial_records(query, execution)
        or assertions.input_partial_records(query, execution))
    statement_frame = statements.model_frame_records(query, execution)
    if source is None:
        statement_frame['status'] = 'not_prepared'
    return dict(schema=schema, answer_policy=assertions.POLICY,
        input_status='partial' if partial else 'complete',
        user_question=execution.policy.action.intent.message, native_body_evidence=body_frame,
        native_statements=statement_frame,
        native_assertions=assertions.model_frame_records(query, execution,
            schema='dmb_native_assertion_frame_v2',
            read_records=_writer_assertion_reads(execution, passages_only=passages_only))
            if isinstance(query, assertions.NativePlanQueryV2) else None)


def model_frame(receipt, execution, *, schema=SCHEMA, passages_only=False):
    """Current semantic projection; V1 remains an exact historical input codec."""
    from .native_context import BuildPendingContextReceiptV1
    from .native_execution import BuildPendingExecutionV1
    if (type(receipt), type(execution)) == (BuildPendingContextReceiptV1, BuildPendingExecutionV1):
        return _pending_model_frame(receipt, execution, schema=schema, passages_only=passages_only)
    if schema not in {LEGACY_SCHEMA, SCHEMA}:
        raise ValueError('Unknown native writer evidence presentation')
    if (type(receipt), type(execution)) != (SurfaceNativeContextReceiptV1, SurfaceNativeExecutionV1):
        raise ValueError("Native writer requires its exact shared receipt and execution")
    validate_execution_binding(receipt, execution)
    return _model_frame_from_validated_prefix(receipt, execution, schema=schema, passages_only=passages_only)


def _model_frame_from_validated_prefix(receipt, execution, *, schema=SCHEMA, passages_only=False):
    if any(type(event) in NATIVE_WRITER_TYPES for event in execution.events):
        raise ValueError("Native evidence projection requires the prefix before its writer")
    from .native_execution import effective_native_query
    query = effective_native_query(receipt, execution)
    from .native_context import NativeBuildQueryPendingV1
    if isinstance(query, NativeBuildQueryPendingV1):
        if not any(isinstance(event, t.BuildPriorBodyEvidenceAdmittedV1) for event in execution.events):
            raise ValueError("Native writer requires the settled Build Graph query or conversation evidence admission")
        query = None
    partial = (isinstance(receipt.source_authority, t.NativeCorpusUnavailableV1)
        or isinstance(query, statements.NativePlanQueryUnavailableV1)
        or bodies.body_input_partial(execution)
        or statements.input_partial_records(query, execution)
        or assertions.input_partial_records(query, execution))
    body_frame = bodies.model_body_frame_records(receipt.source_authority, execution, body_handle,
        passages_only=passages_only)
    body_frame["excerpts"].extend(support.frame() for support in bodies.prior_body_writer_supports(execution))
    from .retained_conversation import native_frame_rows
    body_frame["excerpts"].extend(native_frame_rows(execution, receipt.source_authority, body_handle))
    return dict(schema=schema, answer_policy=assertions.POLICY, input_status='partial' if partial else 'complete',
        user_question=execution.policy.action.intent.message,
        native_body_evidence=body_frame,
        native_statements=statements.model_frame_records(query, execution),
        native_assertions=assertions.model_frame_records(query, execution,
            schema='dmb_plan_native_assertion_frame_v1' if schema == LEGACY_SCHEMA else 'dmb_native_assertion_frame_v2',
            read_records=_writer_assertion_reads(execution, passages_only=passages_only))
            if isinstance(query, assertions.NativePlanQueryV2) else None)


def model_input_frame(receipt,execution):
    from .native_evidence_view import semantic_frame
    from .native_execution import NativeBuildActionV1
    return semantic_frame(model_frame(receipt,execution),
        project_managed_images=isinstance(execution.policy.action, NativeBuildActionV1))


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
    supplied_source_references: bool = False
    typed_source_answer: bool = False
    lore_page_limitations: bool = False
    lore_request_reference: bool = False
    lore_outcome: bool = False
    semantic_reply: bool = False
    generic_limitations: bool = False
    semantic_evidence: bool = False
    variant_format: bool = False
    variant_edits: bool = False
    variant_visible_reply: bool = False
    variant_witnesses: bool = False
    variant_carried_condition: bool = False
    variant_passage_review: bool = False
    variant_trigger_retention: bool = False
    variant_passage_witnesses: bool = False


def model_work_frame(receipt, execution, *, provenance, idempotency_key, work_proof,
                     world_id, conversation_id, turn_id, attempt, play_context_receipt=None):
    """Reconstruct real surface work through its owner; no second stored authority."""
    from .native_context import validate_work_context, BuildWorkContextV1, PlanWorkContextV1
    _validate_writer_binding(receipt,execution)
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
        from .retained_conversation import admission, authored_frame, validate_binding
        retained = admission(execution)
        if retained is not None:
            validate_binding(retained, world_id=world_id, conversation_id=conversation_id,
                turn_id=turn_id, attempt=attempt)
            frame = frame | {'retained_authored_context': authored_frame(execution)}
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


def _build_paragraph_work(action, selected):
    from application_state.build_proposal.prose_catalog import catalog_for_build_capability

    placement = getattr(selected, "paragraph_placement", None)
    if placement is None or placement.target is None:
        return None
    catalog = catalog_for_build_capability(action.write_capability)
    alias, _, _ = placement.target.alias.partition(":")
    passage = next(item for item in catalog.passages if item.alias == alias)
    return {
        "relation": "before" if placement.target.operation == "insert_before" else "after",
        "existing_passage": passage.passage,
        "section": list(passage.headings),
    }


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
    from application_state.build_proposal.types import explicit_build_page_target
    explicit_target = explicit_build_page_target(action.write_capability, selected)
    paragraph_work = _build_paragraph_work(action, selected)
    exclusions = {"instruction", "origin"}
    if explicit_target is not None and operation == "propose_build_insertion":
        exclusions.add("boundary_editor_json")
    if paragraph_work is not None:
        exclusions.update({"boundary_editor_json", "page_body_offer", "page_end_offer", "prose_target"})
        if (getattr(capability, "prose_target", None) != selected.paragraph_placement.target
                or capability.page_body_offer is not None or capability.page_end_offer is not None):
            raise ValueError("Native paragraph authoring must use only its selected boundary")
    if (operation not in {'propose_build_insertion','prepare_build_image'}
            or selected.operation!=operation or action.write_capability is None
            or instruction!=action.intent.message
            or capability.model_dump(mode='json',exclude=exclusions)
                !=action.write_capability.model_dump(mode='json',exclude=exclusions)):
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
        **({"paragraph_placement": paragraph_work} if paragraph_work is not None else {}),
        surface_work=build_work_view(model_work_frame(receipt,execution,**work),execution))


def _input_frames(raw,execution,work_schema, *, prose_frame=None, prose_work=None):
    """One actual producer packet, selected by the stored operation."""
    from .native_execution import NativeBuildActionV1
    from .build_intentional_response import placement_question, selected_action
    selected=selected_action(execution) if isinstance(execution.policy.action,NativeBuildActionV1) else None
    operation = None if selected is None or placement_question(execution, selected) is not None else selected.operation
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
            from .native_execution import NativePlanActionV2, NativePlanActionV3
            if prose_work is not None:
                if work is not None:
                    raise ValueError('Ambiguous Plan writer work')
                work = prose_work
            if type(execution.policy.action) in (NativePlanActionV2, NativePlanActionV3) and work is None:
                raise ValueError('Current Plan saved-page work requires its semantic producer frame')
        else:
            from .native_build_work_view import frame_in_request as build_frame
            work = build_frame(strict_json(raw))
        if prose_frame is not None and semantic is not None:
            raise ValueError('Ambiguous Plan writer evidence')
        semantic = prose_frame if prose_frame is not None else semantic
        return (semantic if semantic is not None else responses_text_frame(raw,schemas={LEGACY_SCHEMA,SCHEMA},label='Native writer'),
            work if work is not None else responses_text_frame(raw,schemas={work_schema},label='Native surface work'))
    body=strict_json(raw)
    from .build_proposal_input import proposal_packet_text
    packet_text = proposal_packet_text(body) if isinstance(body, dict) else None
    if (not isinstance(body,dict) or packet_text is None or 'messages' in body
            or body.get('tools',[])!=[] or body.get('tool_choice') not in (None,'none')):
        raise ValueError('Native authoring requires its one exact producer packet')
    packet=strict_json(packet_text)
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
            'native_evidence','surface_work','rules_evidence','page_body_offer','page_end_offer','paragraph_placement'}
        if set(packet)-allowed:
            raise ValueError('Unclassified semantic Build authoring fields')
        paragraph_work = _build_paragraph_work(execution.policy.action, selected)
        if (("paragraph_placement" in packet) != (paragraph_work is not None)
                or packet.get("paragraph_placement") != paragraph_work):
            raise ValueError("Native Build writer paragraph differs from the admitted boundary")
    if packet.get('instruction')!=execution.policy.action.intent.message:
        raise ValueError('Native authoring instruction differs from selected work')
    if any(key in packet for key in ('source_basis','draft_markdown','captured_capability',
            'related_authored_pages','authored_reference_passages')):
        raise ValueError('Native authoring cannot duplicate or substitute work/source bodies')
    return packet.get('native_evidence'),packet.get('surface_work')


def verify_input_records(receipt, execution, authorization, raw, *, provenance, idempotency_key,
                         work_proof, world_id, conversation_id, turn_id, attempt, play_context_receipt=None,
                         retained_build_proof=False):
    """Bind one shared native frame to the exact stored producing SDK request."""
    from .native_context import BuildPendingContextReceiptV1
    from .native_execution import BuildPendingExecutionV1
    if ((type(receipt), type(execution)) not in {
            (SurfaceNativeContextReceiptV1, SurfaceNativeExecutionV1),
            (BuildPendingContextReceiptV1, BuildPendingExecutionV1)}
            or type(authorization) not in NATIVE_WRITER_TYPES):
        raise ValueError("Native writer proof requires its concrete shared owner records")
    _validate_writer_binding(receipt, execution)
    writers = [event for event in execution.events if type(event) in NATIVE_WRITER_TYPES]
    if writers != [authorization] or execution.events[authorization.sequence] != authorization:
        raise ValueError("Native writer proof differs from its unique stored authorization")
    # Reparse actual records, not a legacy policy/view. Later outcomes never add
    # evidence to this producing frame; read owners refuse post-writer acquisition.
    prefix = type(execution).model_validate_json(execution.model_copy(
        update={"events": execution.events[:authorization.sequence]}).model_dump_json(by_alias=True))
    expected_work = model_work_frame(receipt,prefix,provenance=provenance,idempotency_key=idempotency_key,
        work_proof=work_proof,world_id=world_id,conversation_id=conversation_id,turn_id=turn_id,attempt=attempt,
        play_context_receipt=play_context_receipt)
    from .build_proposal_input import proposal_packet_text
    from .native_evidence_view import PLAN_EVIDENCE_HEADING, render_plan_evidence, semantic_frame
    from .native_execution import NativePlanActionV2, NativePlanActionV3
    body = strict_json(raw)
    from .native_plan_work_view import SOURCE_REFERENCE_FORMAT
    plan_source_references = body.get('text', {}).get('format', {}).get('name') == SOURCE_REFERENCE_FORMAT
    if plan_source_references and type(prefix.policy.action) not in (NativePlanActionV2, NativePlanActionV3):
        raise ValueError('Plan source references require native Plan work')
    from .retained_conversation import validate_dialogue_request
    validate_dialogue_request(prefix, body)
    messages = body.get('input')
    prose_host = prose_frame = prose_work = None
    if type(prefix.policy.action) in (NativePlanActionV2, NativePlanActionV3) and isinstance(messages, list):
        prose = [message.get('content') for message in messages
                 if isinstance(message, dict) and isinstance(message.get('content'), str)
                 and message['content'].startswith(PLAN_EVIDENCE_HEADING)]
        if prose:
            prose_host = model_frame(receipt, prefix, passages_only=True)
            prose_frame = semantic_frame(prose_host)
            from .native_plan_work_view import compact_editor_prose, semantic_frame as plan_work_view
            prose_work = plan_work_view(expected_work, prefix, supplied_source_references=plan_source_references)
            if authorization.compact_plan_editor_prose:
                compact = compact_editor_prose(prose_work)
                if compact is prose_work:
                    raise ValueError('Plan compact editor prose requires a redundant editor view')
                prose_work = compact
            if authorization.compact_plan_graph_qualifications and not (
                    prose_frame.get("native_assertions") or {}).get("assertions"):
                raise ValueError("Compact Graph qualifications require admitted assertions")
            expected_message = {'role': 'user', 'content': render_plan_evidence(
                prose_frame, prose_work,
                compact_graph_qualifications=authorization.compact_plan_graph_qualifications,
                deduplicate_recap_prose=authorization.deduplicate_plan_recap_prose,
            )}
            if len(prose) != 1 or messages[-1] != expected_message:
                raise ValueError('Plan writer prose differs from its exact admitted evidence')
    if (authorization.compact_plan_editor_prose or authorization.compact_plan_graph_qualifications
            or authorization.deduplicate_plan_recap_prose) and prose_work is None:
        raise ValueError('Plan compact prose markers require native Plan prose')
    frame,work_frame = _input_frames(raw,prefix,expected_work['schema'],prose_frame=prose_frame, prose_work=prose_work)
    from .plan_writer_output_schema import offered_generic_limits
    generic_reply_limits = offered_generic_limits(body.get('text', {}).get('format'))
    has_image = isinstance(body.get("input"), list) and proposal_packet_text(body) is not None
    from .native_execution import NativeBuildActionV1
    if isinstance(prefix.policy.action, NativeBuildActionV1):
        image_id = prefix.policy.action.intent.build_reference_image_id
        if has_image != bool(image_id) or expected_work.get("captured_editor", {}).get("reference_image_id") != (
            str(image_id) if image_id is not None else None
        ):
            raise ValueError("Build writer image differs from the captured editor reference")
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
    if prose_host is not None:
        host = prose_host
    elif is_semantic_frame(frame):
        host = model_frame(receipt, prefix)
    else:
        host = model_frame(receipt, prefix, schema=frame.get('schema'))
    semantic_evidence = is_semantic_frame(frame)
    if generic_reply_limits and not semantic_evidence:
        raise ValueError('Generic reply limitations require semantic native evidence')
    expected = host
    if is_semantic_frame(frame):
        project_build_images = isinstance(prefix.policy.action, NativeBuildActionV1)
        expected = expected_semantic_frame(host, frame, project_managed_images=project_build_images)
        if project_build_images and retained_build_proof and expected != frame:
            expected = expected_semantic_frame(host, frame)
    schema_frame = output_frame(host,expected)
    from .native_plan_work_view import is_semantic_frame as semantic_work, semantic_frame as plan_work_view
    from .native_play_work import is_semantic_frame as semantic_play, semantic_frame as play_work_view
    play_local = semantic_play(work_frame)
    authored_local = semantic_work(work_frame) or play_local
    from .native_build_work_view import is_semantic_frame as semantic_build, semantic_frame as build_work_view
    from .native_build_work_view import VARIANT_CARRIED_CONDITION_FORMAT, VARIANT_EDITS_FORMAT, VARIANT_VISIBLE_REPLY_FORMAT, VARIANT_WITNESS_FORMAT, VARIANT_WRITER_FORMAT, VARIANT_PASSAGE_FORMATS, VARIANT_TRIGGER_RETENTION_FORMAT, VARIANT_PASSAGE_WITNESS_FORMAT
    build_local = semantic_build(work_frame)
    format_name = body.get("text", {}).get("format", {}).get("name")
    from .lore_page_review import LORE_REQUEST_FORMAT, LORE_OUTCOME_FORMAT
    lore_outcome = format_name == LORE_OUTCOME_FORMAT
    from .native_build_work_view import (BUILD_REPLY_FORMAT, semantic_reply_eligible,
        source_backed_discussion, lore_page_reply, lore_request_reference_eligible)
    semantic_reply = format_name == BUILD_REPLY_FORMAT
    if semantic_reply and (not build_local or not semantic_reply_eligible(expected_work, prefix)):
        raise ValueError('Semantic reply requires captured ordinary Build work')
    lore_request_reference = (lore_request_reference_eligible(expected_work, prefix) if semantic_reply
                              else format_name in {LORE_REQUEST_FORMAT, LORE_OUTCOME_FORMAT})
    citation_policy = (work_frame.get('citation_policy') if type(prefix.policy.action) in (NativePlanActionV2, NativePlanActionV3)
                       else work_frame.get('build_work', {}).get('citation_policy'))
    if citation_policy not in (None, 'supplied_source_references_v1'):
        raise ValueError('Unknown Build citation policy')
    supplied_source_references = semantic_reply or lore_outcome or citation_policy == 'supplied_source_references_v1'
    from .native_build_work_view import SOURCE_ANSWER_POLICY, LORE_LIMITATION_POLICY
    source_answer_policy = work_frame.get('build_work', {}).get('source_answer_policy')
    if source_answer_policy not in (None, SOURCE_ANSWER_POLICY):
        raise ValueError('Unknown Build source answer policy')
    typed_source_answer = (source_backed_discussion(expected_work, prefix) if semantic_reply
                           else source_answer_policy == SOURCE_ANSWER_POLICY)
    lore_limitation_policy = work_frame.get('build_work', {}).get('lore_limitation_policy')
    if lore_limitation_policy not in (None, LORE_LIMITATION_POLICY):
        raise ValueError('Unknown lore review limitation policy')
    lore_page_limitations = (lore_page_reply(expected_work, prefix) if semantic_reply
                            else lore_outcome or lore_limitation_policy == LORE_LIMITATION_POLICY)
    variant_passage_review = format_name in VARIANT_PASSAGE_FORMATS
    variant_edits = format_name in {VARIANT_EDITS_FORMAT, VARIANT_VISIBLE_REPLY_FORMAT, VARIANT_WITNESS_FORMAT, VARIANT_CARRIED_CONDITION_FORMAT, *VARIANT_PASSAGE_FORMATS}
    variant_format = variant_edits or format_name == VARIANT_WRITER_FORMAT
    expected_wire_work = (build_work_view(expected_work,prefix,include_variant=variant_format,
        variant_edits=variant_edits, variant_passage_review=variant_passage_review,
        bind_lore_page="lore_page_destination" in work_frame["build_work"],
        supplied_source_references=supplied_source_references,
        typed_source_answer=typed_source_answer or semantic_reply, lore_page_limitations=lore_page_limitations or semantic_reply,
        lore_request_reference=lore_request_reference or semantic_reply, lore_outcome=lore_outcome,
        semantic_reply=semantic_reply) if build_local
        else play_work_view(expected_work) if play_local
        else prose_work if prose_work is not None
        else plan_work_view(expected_work,prefix,supplied_source_references=plan_source_references) if authored_local else expected_work)
    if t.canonical_sha256(work_frame) != t.canonical_sha256(expected_wire_work):
        if not build_local or not retained_build_proof:
            raise ValueError('Native writer changed or omitted its exact surface work')
        retained_work = build_work_view(
            expected_work, prefix, include_variant=variant_format, variant_edits=variant_edits,
            variant_passage_review=variant_passage_review,
            bind_lore_page="lore_page_destination" in work_frame["build_work"], retained_raw_markdown=True,
            supplied_source_references=supplied_source_references,
            typed_source_answer=typed_source_answer or semantic_reply, lore_page_limitations=lore_page_limitations or semantic_reply,
            lore_request_reference=lore_request_reference or semantic_reply, lore_outcome=lore_outcome,
            semantic_reply=semantic_reply,
        )
        if t.canonical_sha256(work_frame) != t.canonical_sha256(retained_work):
            raise ValueError('Native writer changed or omitted its exact surface work')
    if generic_reply_limits and not (build_local or authored_local):
        raise ValueError('Generic reply limitations require semantic surface work')
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
    return NativeWriterEvidence(frame=schema_frame,work_frame=expected_work,output_work_frame=expected_work | expected_wire_work,
        authored=authored,idempotency_key=idempotency_key,
        authored_local=authored_local,build_local=build_local,
        supplied_source_references=supplied_source_references,typed_source_answer=typed_source_answer,
        lore_page_limitations=lore_page_limitations,generic_limitations=generic_reply_limits,
        lore_request_reference=lore_request_reference, lore_outcome=lore_outcome, semantic_reply=semantic_reply,
        semantic_evidence=semantic_evidence,
        variant_format=variant_format,variant_edits=variant_edits,
        variant_visible_reply=format_name in {VARIANT_VISIBLE_REPLY_FORMAT, VARIANT_WITNESS_FORMAT, VARIANT_CARRIED_CONDITION_FORMAT, *VARIANT_PASSAGE_FORMATS},
        variant_witnesses=format_name in {VARIANT_WITNESS_FORMAT, VARIANT_CARRIED_CONDITION_FORMAT, *VARIANT_PASSAGE_FORMATS},
        variant_carried_condition=format_name in {VARIANT_CARRIED_CONDITION_FORMAT, *VARIANT_PASSAGE_FORMATS},
        variant_passage_review=variant_passage_review,
        variant_trigger_retention=format_name in {VARIANT_TRIGGER_RETENTION_FORMAT, VARIANT_PASSAGE_WITNESS_FORMAT},
        variant_passage_witnesses=format_name == VARIANT_PASSAGE_WITNESS_FORMAT,
        saved_sections=saved_sections,related_pages=related_pages,draft_record=draft_record,
        **read_evidence_records(prefix,expected,passages_only=prose_frame is not None))


def read_evidence_records(prefix, frame, *, passages_only=False):
    """Project the exact included read records through their native owners."""
    catalogs = bodies.acquired_body_catalogs(prefix)
    from dataclasses import replace
    supports = (bodies.writer_passage_supports(prefix, body_handle) if passages_only else tuple(
        bodies.NativeBodySupport(body_handle(read), read, catalogs[read.excerpt.catalog_sha256])
        for read in bodies.selected_body_reads(prefix)))
    supports += bodies.prior_body_writer_supports(prefix)
    from .retained_conversation import native_supports
    supports += native_supports(prefix)
    statement_reads = statements.selected_read_records(prefix)
    assertion_reads = _writer_assertion_reads(prefix, passages_only=passages_only)
    return dict(body_excerpts=tuple(replace(support, handle=row['excerpt_handle']) for row, support in
            zip(frame['native_body_evidence']['excerpts'], supports, strict=True)),
        native_statements=tuple((row['statement_handle'], event, read) for row, (event, read)
            in zip(frame['native_statements']['statements'], statement_reads, strict=True)),
        native_assertions=tuple((row['assertion_handle'], event, read) for row, (event, read)
            in zip(frame['native_assertions']['assertions'] if frame['native_assertions'] else (),
                assertion_reads, strict=True)))
