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
        return
    validate_selection_bases(adapter)
    turn = adapter.fence.turn
    append(adapter, t.BuildAuthoredReferencesCapturedV1(event_id=uuid4(), sequence=len(turn.graph_context_execution.events),
        kind='build_authored_references_captured_v1', references=adapter.request.build_authored_references,
        read_graph_revision=adapter.bootstrap.world_scope.revision_id, turn_id=turn.turn_id,
        conversation_id=turn.conversation_id, attempt=turn.attempt,
        submitted_intent_fingerprint=turn.submitted_intent_fingerprint_v2))
    if adapter.context_capture:
        for ref in adapter.request.build_authored_references.references:
            adapter.context_capture.observe({'kind': 'context_decision', 'action': 'retained',
                'item_ids': ['Selected, unread · ' + ref.node_id], 'reason_code': 'route_preserved',
                'policy_version': 'authored_graph_reference_context_v1'})


def acquire(adapter):
    refs = adapter.request.build_authored_references
    if refs is None:
        return
    execution = adapter._broker_execution()
    capture = next(e for e in execution.events if isinstance(e, t.BuildAuthoredReferencesCapturedV1))
    attempted = {(r.anchor_id, r.evidence_ref_id, r.source_artifact_id, r.source_revision_id)
        for e in execution.events if isinstance(e, t.ValidatedSourceReadEventV2) for r in e.receipts}
    for ref in refs.references:
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
        if adapter.context_capture:
            adapter.context_capture.observe({'kind': 'context_decision', 'action': 'retrieved',
                'item_ids': [outcome + ' · ' + ref.node_id],
                'reason_code': 'retrieval_sufficient' if outcome == 'read' else 'coverage_gap',
                'policy_version': 'authored_graph_reference_context_v1'})
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
