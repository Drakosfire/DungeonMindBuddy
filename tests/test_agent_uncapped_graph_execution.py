"""Uncapped ordinary Build execution across APP, IPC, Harness guards and parent IO."""
import json
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

from application_state.agent_conversation import AgentConversationService
from apps.live_control_server.services import agent_turn_service as svc
from apps.live_control_server.services.hermes_agent_runtime import map_invocation_to_hermes_request
from apps.live_control_server.services.hermes_graph_agent import _GraphOperationReservation, _request_budget_guard
from apps.live_control_server.services.hermes_graph_agent_contract import (
    serialize_hermes_graph_agent_turn_request, deserialize_hermes_graph_agent_turn_request,
)
from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
from graph_memory.interaction.session import SourceAnchorState
from graph_memory.interaction.session_store import create_session
from tests.test_agent_build_governed_graph import (
    build_case, SyntheticHarness, execute, EVIDENCE_ID,  # noqa: F401 fixture registration
)


class ExtendedHarness(SyntheticHarness):
    def run_with_provider_authorization(self, invocation, authorize, *, request_budget,
            on_graph_operation, on_provider_lifecycle, **kwargs):
        request = replace(map_invocation_to_hermes_request(invocation), request_budget=request_budget,
            provider_authorization_required=True, parent_graph_broker_required=True,
            retrieval_session_id=self.bootstrap.retrieval_session.id,
            retrieval_session=self.bootstrap.retrieval_session.project_for_hermes())
        wire = json.loads(json.dumps(serialize_hermes_graph_agent_turn_request(request)))
        restored = deserialize_hermes_graph_agent_turn_request(wire)
        budget = restored.request_budget
        assert budget['schema'] == 'dmb_agent_request_budget_uncapped_v1'
        assert all(budget[k] is None for k in ('maxProviderAttempts', 'maxToolCapableAttempts', 'maxGraphOperations'))
        tools = SimpleNamespace(tools=['expand_graph_retrieval', 'read_graph_source', 'read_related_recap_context'])
        def broker(name, arguments):
            result = on_graph_operation({'toolName': name, 'arguments': arguments})
            return result['resultJson'], result.get('retrievalSession')
        reservation = _GraphOperationReservation(budget['maxGraphOperations'], broker, source_limit=None, context_limit=None)
        reservation.agents.append(tools)
        parent_errors = []
        def parent(view):
            try:
                return authorize({'provider': view.provider, 'model': view.model, 'apiMode': view.api_mode,
                'payloadJson': view.payload_json, 'payloadSha256': sha256(view.payload_json.encode()).hexdigest(),
                    'payloadUtf8Bytes': view.payload_utf8_bytes})
            except Exception as error:
                parent_errors.append(error)
                return False
        guard = _request_budget_guard(budget, on_provider_authorization=parent,
            on_provider_lifecycle=on_provider_lifecycle, graph_outcome_indeterminate=lambda: reservation.indeterminate)
        guard.bind_agent.append(tools)
        latest = []
        def authorize_wire(view):
            body = json.loads(view['payloadJson']) | {'model': budget['model'], 'max_output_tokens': budget['outputReserveTokens']}
            payload = json.dumps(body)
            request_view = SimpleNamespace(provider=budget['provider'], model=budget['model'], api_mode=budget['apiMode'],
                payload_json=payload, payload_utf8_bytes=len(payload.encode()))
            latest[:] = [request_view]
            allowed = guard(request_view)
            assert allowed, (guard.guard_state, [str(error) for error in parent_errors], str(getattr(getattr(authorize, '__self__', None), 'failure', None)))
            return allowed
        extended = False
        def lifecycle(event):
            nonlocal extended
            assert guard.provider_lifecycle(event)
            if event['transition'] == 'response_received' and not extended:
                extended = True
                for i in range(9):
                    graph, _ = reservation('expand_graph_retrieval', {
                        'schema': 'dmb_expand_graph_retrieval_request_v1', 'retrievalSessionId': restored.retrieval_session_id,
                        'operation': 'object', 'targets': [{'kind': 'node', 'id': 'frank'}]})
                    assert json.loads(graph)['schema'] != 'dmb_world_graph_retrieval_error_v1'
                    opened, _ = reservation('read_graph_source', {
                        'retrievalSessionId': restored.retrieval_session_id, 'anchorIds': ['anchor-one'], 'maxChars': i + 1})
                    assert json.loads(opened)['content'] == 'Frank guards the western gate.'[:i + 1]
                    if i < 5:
                        assert guard(latest[0])
                        assert guard.provider_lifecycle({'transition': 'sdk_entered'})
                        assert guard.provider_lifecycle({'transition': 'response_received'})
                    assert len(tools.tools) == 3 and not reservation.indeterminate
            return True
        def transport(message):
            result, packet = reservation(message['toolName'], message['arguments'])
            return {'resultJson': result, 'retrievalSession': packet}
        result = super().run_with_provider_authorization(invocation, authorize_wire,
            request_budget=budget, on_graph_operation=transport, on_provider_lifecycle=lifecycle, **kwargs)
        assert reservation.count == 9 and reservation.source_count == 10
        return result


def test_ordinary_build_can_open_passage_after_old_count_cutoffs(build_case, tmp_path, monkeypatch):  # noqa: F811 imported pytest fixture
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
    from graph_memory.retrieval.models import WorldGraphRetrievalResult
    source, request, bootstrap = build_case
    session = bootstrap.retrieval_session
    session.claims = claims_from_retrieval_result({'relationships': [{
        'edgeId': 'rel-gate', 'sourceNodeId': 'frank', 'targetNodeId': 'gate', 'predicate': 'guards', 'evidenceRefIds': [EVIDENCE_ID]}],
        'sourceAnchors': [{'anchorId': 'anchor-one', 'revisionId': 'native-rev-3', 'evidenceRefId': EVIDENCE_ID,
            'readable': True, 'supportingGraphObjectIds': ['rel-gate']}]}, revision_id='native-rev-3')
    session.source_anchors = [SourceAnchorState(anchor_id='anchor-one', readable=True)]
    create_session(session)
    pin = {'anchor_id': 'anchor-one', 'graph_revision': 'native-rev-3', 'evidence_ref_id': EVIDENCE_ID,
        'source_artifact_id': 'artifact-one', 'source_revision_id': 'source-rev-one'}
    bootstrap = replace(bootstrap, candidate_relationship_ids=('rel-gate',), candidate_evidence_ref_ids=(EVIDENCE_ID,),
        evidence_by_anchor_id={'anchor-one': EVIDENCE_ID}, source_scope_anchors=({k: v for k, v in pin.items() if k != 'graph_revision'},))
    result = WorldGraphRetrievalResult.model_validate({'operation': 'object', 'outcome': 'empty', 'requestedNodeId': 'frank',
        'snapshot': {'worldId': 'native-build-world', 'campaignId': '', 'scopeMode': 'world', 'focus': {'kind': 'none', 'sessionId': None},
            'admissibility': 'gm', 'revisionId': 'native-rev-3', 'headRevisionId': 'native-rev-3', 'isHead': True}})
    resolved = direct.ResolvedWorldGraphReviewedObjectV3(result, (), (), (), ())
    monkeypatch.setattr(direct, 'direct_services_from_config', lambda _: SimpleNamespace())
    monkeypatch.setattr(direct, 'get_object_with_reviewed_sources_direct_v3', lambda *_: resolved)
    monkeypatch.setattr(svc._PolicyExecutionAdapter, '_related_recap_offers', lambda *_: [])
    text = 'Frank guards the western gate.'
    def read(_arguments, *, receipt_version, root):
        assert root == tmp_path
        assert receipt_version == 2
        read_id = f'source-read-{uuid4()}'
        passage = text[:_arguments['maxChars']]
        truncated = len(passage) < len(text)
        outcome = 'truncated' if truncated else 'enough'
        return {'schema': 'dmb_internal_read_graph_source_batch_v2', 'retrievalSessionId': session.id, 'reads': [{
            'sourceReadId': read_id, 'result': {'schema': 'dmb_world_graph_source_anchor_read_v1', 'anchorId': 'anchor-one',
                'evidenceRefId': EVIDENCE_ID, 'sourceArtifactId': 'artifact-one', 'outcome': outcome, 'content': passage,
                'contentSha256': sha256(passage.encode()).hexdigest(), 'lineStart': 1, 'lineEnd': 1, 'truncated': truncated},
            'receipt': {'source_read_id': read_id, 'retrieval_session_id': session.id, 'graph_revision': 'native-rev-3',
                **{k: v for k, v in pin.items() if k != 'graph_revision'}, 'read_content_sha256': sha256(passage.encode()).hexdigest(),
                'outcome': outcome, 'truncated': truncated}}]}
    monkeypatch.setattr('graph_memory.interaction.expansion_executor.execute_read_graph_source', read)
    response = execute((source, request, bootstrap), tmp_path, ExtendedHarness(source, bootstrap, graph=True))
    citation, = response.knowledge_context.completion.citation_map.entries
    assert citation.source_opened and len(citation.source_read_ids) == 1
    service = AgentConversationService()
    conversation = service.get_active_conversation('elderwyld')
    turn, = service.list_turns('elderwyld', conversation.conversation_id)
    assert turn.status == 'completed'
    assert turn.graph_context_execution.policy.max_provider_attempts is None
    kinds = [event.kind for event in turn.graph_context_execution.events]
    assert kinds.count('provider_attempt_authorized_v3') == 7
    assert kinds.count('validated_graph_operation_v3') == 9
    assert kinds.count('validated_source_read_v2') == 10
