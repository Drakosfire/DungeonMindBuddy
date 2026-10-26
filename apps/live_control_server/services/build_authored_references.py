"""Host-owned exact reads requested by the author, never model-selected retrieval."""
from __future__ import annotations
import json
from uuid import uuid4

from application_state.agent_conversation import types as t
from application_state.agent_conversation.authored_graph_references import digest, source_event_ids
from .world_source_acquisition import read_operation_sources


def refusal(message, code, *, before_provider=False):
    from .agent_turn_service import AgentTurnServiceError
    return AgentTurnServiceError(message, code=code, provider_dispatched=False if before_provider else None)


def append(adapter, event, **proof):
    from .agent_turn_service import _require_fresh_execution_append
    adapter.turn = _require_fresh_execution_append(adapter.fence.append('record_build_authored_reference', 'event', event, **proof))
    if adapter.context_capture:
        adapter.context_capture.authored_reference(event)


def validate_selection_bases(adapter):
    """Resolve membership, not evidence: picker display text never enters a writer."""
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as native
    from graph_memory.retrieval.models import WorldGraphObjectRequest
    refs = adapter.request.build_authored_references
    if refs is None:
        return
    refs.require_world(adapter.world_id)
    scope = adapter.bootstrap.world_scope
    for ref in refs.references:
        if ref.native_world_id != scope.world_id or ref.binding_version != adapter.bootstrap.binding_version:
            raise refusal('The referenced object’s World binding changed. Choose it again; your request is retained.', 'build_authored_reference_binding_changed', before_provider=True)
    if not refs.references:
        return
    services = native.direct_services_from_config(scope.world_id)
    for ref in refs.references:
        # The old selected snapshot remains origin provenance, never current evidence.
        request = WorldGraphObjectRequest.model_validate({'schema': 'dmb_world_graph_object_request_v1',
            'worldId': scope.world_id, 'campaignId': '', 'scopeMode': 'world',
            'focus': {'kind': 'none', 'sessionId': None, 'campaignId': None},
            'admissibility': 'gm', 'revisionPin': ref.graph_revision, 'nodeId': ref.node_id})
        try:
            result = native.get_object_direct(services, request)
        except Exception as exc:
            raise refusal('The selected Graph snapshot could not be opened. Your request and reference are retained.',
                'build_authored_reference_snapshot_unavailable', before_provider=True) from exc
        if not any(node.node_id == ref.node_id for node in result.nodes):
            raise refusal('The selected Graph object is absent from its original snapshot. Choose it again; your request is retained.', 'build_authored_reference_missing', before_provider=True)


def capture_input(adapter):
    existing = [e for e in adapter._broker_execution().events if isinstance(e, t.BuildAuthoredReferencesCapturedV1)]
    if existing:
        if existing[0].references != adapter.request.build_authored_references:
            raise ValueError('The retained Graph reference input changed')
        validate_selection_bases(adapter)
        return
    turn = adapter.fence.turn
    append(adapter, t.BuildAuthoredReferencesCapturedV1(event_id=uuid4(), sequence=len(turn.graph_context_execution.events),
        kind='build_authored_references_captured_v1', references=adapter.request.build_authored_references,
        read_graph_revision=adapter.bootstrap.world_scope.revision_id, turn_id=turn.turn_id,
        conversation_id=turn.conversation_id, attempt=turn.attempt,
        submitted_intent_fingerprint=turn.submitted_intent_fingerprint_v2))
    validate_selection_bases(adapter)


def prior_selection_attempt(adapter, selection):
    """Identify provenance for an existing APP selection, never grant a new action."""
    from application_state.agent_conversation.authored_graph_references import capture
    turn=adapter.fence.turn
    first=capture(adapter._broker_execution()).attempt
    from application_state.errors import ApplicationStateError
    try:
        traces=adapter.service.list_context_trace_attempts(world_id=turn.world_id,turn_id=turn.turn_id)
    except ApplicationStateError as exc:
        raise refusal('The earlier step trace could not be verified. Your request and references are retained; inspect the trace before continuing.',
            'build_authored_reference_recovery_unavailable',before_provider=True) from exc
    owners=[trace.attempt for trace in traces if first <= trace.attempt < turn.attempt
        and trace.execution_start_sequence <= selection.sequence
        and not any(other.attempt > trace.attempt and other.execution_start_sequence <= selection.sequence for other in traces)]
    if len(owners)!=1:
        raise refusal('The retained selection has no unique prior physical attempt. Your request and references are retained; inspect the trace before continuing.',
            'build_authored_reference_recovery_unavailable',before_provider=True)
    return owners[0]


def validate_retained_operation(adapter, operation, arguments):
    """Reconstitution verifies one completed read, never grants a new execution operation."""
    execution = adapter._broker_execution()
    if (adapter.turn.status != 'running' or adapter.request.build_authored_references is None
        or any(isinstance(e,t.ProviderAttemptAuthorizedEventV1) for e in execution.events)
        or arguments.get('operation') != 'object'
        or operation not in execution.events or operation.request_arguments_sha256 != digest(arguments)
        or operation.graph_revision != execution.policy.source_read_scope.graph_revision):
        raise ValueError('Retained object verification differs from its frozen acquisition')
    reads = [e for e in execution.events if isinstance(e,t.BuildAuthoredReferenceReadV1)
        and e.outcome == 'read' and operation.event_id in e.operation_event_ids]
    if len(reads) != 1:
        raise ValueError('Retained object verification requires one completed authored read')
    authorization = next(e for e in execution.events if e.event_id == reads[0].authorization_event_id)
    if (not isinstance(authorization,t.BuildAuthoredReferenceAuthorizedV1)
        or operation.sequence != authorization.sequence+1
        or operation.request_arguments_sha256 != authorization.arguments_sha256):
        raise ValueError('Retained object verification lacks its exact authorization')


def restore_material(adapter, read):
    """Restore exact existing bodies; no new execution or activity receipts."""
    from application_state.agent_conversation.surface_source_answer import passage_handle
    from application_state.agent_conversation.authored_graph_references import protected_source_material
    execution = adapter._broker_execution()
    events = {e.event_id:e for e in execution.events}
    try:
        for identity in read.operation_event_ids:
            operation = events[identity]
            arguments = {'retrievalSessionId':execution.policy.source_read_scope.retrieval_session_id,
                'operation':'object','targets':[{'kind':'node','id':read.node_id}]}
            validate_retained_operation(adapter,operation,arguments)
            adapter.broker_graph_operation({'toolName':'expand_graph_retrieval','arguments':arguments},
                retained_authored_operation=operation)
            if adapter.failure is not None or identity not in adapter.operation_payloads:
                raise ValueError('Exact retained object body unavailable')
        traces = adapter.service.list_context_trace_attempts(world_id=adapter.turn.world_id,turn_id=adapter.turn.turn_id)
        material=protected_source_material(adapter.fence.turn,traces)
        for identity in read.source_read_event_ids:
            event=events[identity]
            rows=[]
            for receipt in event.receipts:
                passages=[p for p in material['observations'] if p['source_read_event_id']==str(identity)
                    and p['source_read_id']==receipt.source_read_id]
                if len(passages)!=1:
                    raise ValueError('Retained source has no unique protected body')
                passage=passages[0]
                rows.append({'schema':'dmb_world_graph_source_anchor_read_v1','anchorId':receipt.anchor_id,
                    'evidenceRefId':receipt.evidence_ref_id,'sourceArtifactId':receipt.source_artifact_id,
                    'sourceRevisionId':receipt.source_revision_id,'sourceName':passage['source_name'],
                    'content':passage['text'],'contentSha256':receipt.content_sha256,'lineStart':receipt.line_start,
                    'lineEnd':receipt.line_end,'outcome':'enough','truncated':False,'diagnostics':[],
                    'passageHandle':passage_handle(receipt)})
            payload = rows[0] if len(rows)==1 else {'schema':'dmb_read_graph_source_batch_v1','reads':rows}
            adapter.source_payloads[identity] = json.dumps(payload,ensure_ascii=False,separators=(',',':'))
        # Validate this exact read before restoring any other referenced object.
        from application_state.agent_conversation.build_world_context import opened_world_passages
        opened_world_passages(execution,read.operation_event_ids,read.source_read_event_ids,
            adapter.operation_payloads,adapter.source_payloads)
    except Exception as exc:
        raise refusal('The earlier selected-object read could not be restored exactly. Your request and reference are retained; inspect the trace, then refresh plan results and choose Try step again.',
            'build_authored_reference_recovery_unavailable',before_provider=True) from exc


def acquire(adapter):
    refs = adapter.request.build_authored_references
    if refs is None:
        return
    execution = adapter._broker_execution()
    capture = next(e for e in execution.events if isinstance(e, t.BuildAuthoredReferencesCapturedV1))
    attempted = {(r.anchor_id, r.evidence_ref_id, r.source_artifact_id, r.source_revision_id)
        for e in execution.events if isinstance(e, t.ValidatedSourceReadEventV2) for r in e.receipts}
    for ref in refs.references:
        prior = [e for e in execution.events if isinstance(e,t.BuildAuthoredReferenceAuthorizedV1) and e.node_id == ref.node_id]
        if prior:
            settled = [e for e in execution.events if isinstance(e,t.BuildAuthoredReferenceReadV1) and e.authorization_event_id == prior[0].event_id]
            if len(prior) != 1 or len(settled) != 1 or settled[0].outcome != 'read':
                raise refusal('The earlier selected-object acquisition did not settle. Your request and reference are retained; refresh plan results and choose Try step again.',
                    'build_authored_reference_recovery_indeterminate',before_provider=True)
            restore_material(adapter, settled[0])
            continue
        arguments = {'retrievalSessionId': execution.policy.source_read_scope.retrieval_session_id,
            'operation': 'object', 'targets': [{'kind': 'node', 'id': ref.node_id}]}
        authorization = t.BuildAuthoredReferenceAuthorizedV1(event_id=uuid4(), sequence=len(adapter._broker_execution().events),
            kind='build_authored_reference_authorized_v1', capture_event_id=capture.event_id,
            node_id=ref.node_id, arguments_sha256=digest(arguments))
        append(adapter, authorization)
        before = set(adapter.operation_payloads)
        reply = adapter.broker_graph_operation({'toolName': 'expand_graph_retrieval', 'arguments': arguments})
        if adapter.failure is not None:
            raise adapter.failure
        operations = set(adapter.operation_payloads) - before
        if not operations:
            reason = json.loads(reply['resultJson']).get('code', 'object_unavailable')
            raise refusal(f'The requested Graph object could not be read: {reason}. The reference and request are retained.', 'build_authored_reference_read_unavailable')
        packets = {str(eid): json.loads(adapter.operation_payloads[eid]) for eid in operations}
        returned_nodes = sorted({node['nodeId'] for packet in packets.values() for node in packet.get('nodes', [])})
        if ref.node_id not in returned_nodes:
            raise refusal('The Graph response did not contain the selected object. Your request is retained.',
                'build_authored_reference_result_mismatch')
        gaps = []
        read_operation_sources(adapter, operations, attempted, gaps)
        execution = adapter._broker_execution()
        pins = {pin.anchor_id for e in execution.events if e.event_id in operations for pin in e.returned_source_pins}
        reads = [e.event_id for e in execution.events if isinstance(e, t.ValidatedSourceReadEventV2)
            and any(r.anchor_id in pins for r in e.receipts)]
        partial = any(e.truncated or e.coverage_status != 'complete' or e.evidence_sufficiency_status != 'sufficient'
            for e in execution.events if e.event_id in operations)
        outcome = 'source_gap' if gaps or not pins else 'read_partial' if partial else 'read'
        append(adapter, t.BuildAuthoredReferenceReadV1(event_id=uuid4(), sequence=len(execution.events),
            kind='build_authored_reference_read_v1', capture_event_id=capture.event_id,
            authorization_event_id=authorization.event_id, node_id=ref.node_id,
            operation_event_ids=sorted(operations, key=str), source_read_event_ids=reads, returned_node_ids=returned_nodes, outcome=outcome), object_result_proof=packets)
        if outcome == 'read_partial':
            raise refusal('The selected object read was incomplete. Your request and reference are retained; inspect its trace before continuing.',
                'build_authored_reference_partial_object')
        if outcome == 'source_gap':
            raise refusal('The requested Graph object has no complete acquired source support. Your reference and request are retained.',
                'build_authored_reference_source_gap')


def include_in_projection(adapter, staged):
    """Reuse finite source selectors and exact source bodies; no duplicate source lane."""
    from dataclasses import replace
    from application_state.agent_conversation.authored_graph_references import writer_context
    context = writer_context(adapter._broker_execution())
    if context is None:
        return staged
    packet = json.loads(staged.input_json)
    packet['authored_reference_context'] = context
    return replace(staged, input_json=json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def writer_material(adapter):
    """Exact existing object/source material for proposal and media writers."""
    from application_state.agent_conversation.authored_graph_references import writer_context
    from application_state.agent_conversation.build_world_context import opened_world_passages
    execution = adapter._broker_execution()
    context = writer_context(execution)
    if context is None:
        return None
    reads = [e for e in execution.events if isinstance(e, t.BuildAuthoredReferenceReadV1) and e.outcome == 'read']
    operations = sorted({eid for e in reads for eid in e.operation_event_ids}, key=str)
    sources = sorted({eid for e in reads for eid in e.source_read_event_ids}, key=str)
    passages = opened_world_passages(execution, operations, sources, adapter.operation_payloads, adapter.source_payloads)
    return {'authored_reference_context': context, 'authored_reference_passages': [
        {'origin': origin.model_dump(mode='json'), 'text': text, 'source_name': name}
        for origin, text, name in passages]}
