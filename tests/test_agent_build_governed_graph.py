"""Ordinary saved Build requests through the real governed conversation ledger."""
import json
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

import pytest

from application_state.agent_conversation import AgentConversationService
from apps.live_control_server.routes import agent
from apps.live_control_server.services import agent_turn_service as svc
from apps.live_control_server.services.agent_runtime import (
    AgentRuntimeDescriptor, AgentRuntimeResult, AgentWorldScope,
)
from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore
from graph_memory.interaction.session import CoverageState, GraphRetrievalSession, SessionSnapshot
from tests.test_agent_build_surface_context import source as source_fixture, graph_request


# Native evidence construction composes artifact/span IDs. Exercise the whole
# governed path at the consumer boundary, rather than only a codec helper.
from application_state.agent_conversation.identifier_limits import (
    GRAPH_EVIDENCE_REF_ID_MAX_CHARS, GRAPH_CLAIM_ID_MAX_CHARS,
)
EVIDENCE_ID = 'evidence:artifact:worldbuilding:' + 'r' * (GRAPH_EVIDENCE_REF_ID_MAX_CHARS - len('evidence:artifact:worldbuilding:'))
CLAIM_ID = 'claim:' + 'c' * (GRAPH_CLAIM_ID_MAX_CHARS - len('claim:'))


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    source = source_fixture.__wrapped__(tmp_path, monkeypatch)
    monkeypatch.setattr(
        'apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference',
        lambda **_: ('openai-api', 'gpt-6-luna', 'https://api.openai.com/v1'),
    )
    request = graph_request(source, revision_pin=None).model_copy(update={'turn_id': str(uuid4())})
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(world_id='native-build-world', campaign_id='', focus={'kind': 'none'},
            admissibility='gm', revision_id='native-rev-3', is_head=True, scope_mode='world'),
        question=request.message, coverage=CoverageState(state='empty'), claims=[], source_anchors=[],
    )
    bootstrap = svc.AgentPlanWorldGraphBootstrap(
        graph_envelope={'status': 'empty', 'revision_id': 'native-rev-3', 'world_id': 'native-build-world',
                        'scope_mode': 'world'},
        world_scope=AgentWorldScope(world_id='native-build-world', campaign_id='', focus={'kind': 'none'},
            admissibility='gm', revision_id='native-rev-3', scope_mode='world'),
        retrieval_session=session, binding_version=7, source_root_relpath='corpus/elderwyld-markdown',
        candidate_assertion_ids=(), candidate_relationship_ids=(), candidate_evidence_ref_ids=(),
        evidence_by_anchor_id={},
    )
    return source, request, bootstrap


class SyntheticHarness:
    descriptor = AgentRuntimeDescriptor('synthetic', 'fake', 'test', 'graph')

    def __init__(self, source, bootstrap, *, fail=False, forged=False, graph=False, refuse=False, tamper_evidence=False, malformed=False, mutation=None, omit_source=False):
        self.source, self.bootstrap = source, bootstrap
        self.malformed = malformed
        self.mutation = mutation
        self.omit_source = omit_source
        self.final_text = None
        self.calls = 0
        self.refuse = refuse
        self.tamper_evidence = tamper_evidence
        self.fail, self.forged, self.graph = fail, forged, graph

    def run(self, invocation):
        pytest.fail('Build Graph bypassed the parent provider gate')

    def run_with_provider_authorization(self, invocation, authorize, *, request_budget,
            on_graph_operation, on_provider_lifecycle, context_read_enabled=False, source_read_enabled=False):
        self.calls += 1
        assert context_read_enabled and callable(on_graph_operation)
        projection = self.bootstrap.retrieval_session.project_for_hermes()
        packet = {'candidates': projection['candidates'][:8], 'claimLedger': projection['claim_ledger'][:24],
                  'intentHint': projection['intent_hint'], 'availableExpansions': projection['available_expansions']}
        from apps.live_control_server.services.hermes_agent_runtime import map_invocation_to_hermes_request
        from apps.live_control_server.services.hermes_graph_agent_contract import (
            serialize_hermes_graph_agent_turn_request, deserialize_hermes_graph_agent_turn_request,
        )
        wire = serialize_hermes_graph_agent_turn_request(map_invocation_to_hermes_request(invocation))
        restored = deserialize_hermes_graph_agent_turn_request(json.loads(json.dumps(wire)))
        assert restored.world_id == 'native-build-world' and restored.revision_pin == 'native-rev-3'
        message = restored.question
        self.request_question = message
        if getattr(self, "omit_discovery", False):
            head, rest = message.split("\n\nReviewed-source discovery", 1)
            message = head + "\n\n" + rest.split("\n\n", 1)[1]
        assert self.source.markdown in json.loads(message.split('\n\n')[0])['saved_source']['content']
        assert 'saved_source_claim' in message
        assert 'Return only JSON with exactly answer_context_status and answer_segments.' in message
        assert 'Do not emit citation_map or source-opening flags' in message
        payload = json.dumps({'input': [
            {'role': 'system', 'content': 'Turn capability policy (runtime-enforced; also required on tool calls):\n'
                + json.dumps({'initialClaimPacket': packet})}, {'role': 'user', 'content': message}], 'tools': []})
        admitted = authorize({'provider': request_budget['provider'], 'model': request_budget['model'],
            'apiMode': request_budget['apiMode'], 'payloadJson': payload,
            'payloadSha256': sha256(payload.encode()).hexdigest(), 'payloadUtf8Bytes': len(payload.encode())})
        if self.refuse:
            assert not admitted
            return AgentRuntimeResult(status='error', error_code='receipt_freeze_failed')
        assert admitted
        assert on_provider_lifecycle({'transition': 'sdk_entered'})
        if self.fail:
            assert on_provider_lifecycle({'transition': 'outcome_unknown'})
            return AgentRuntimeResult(status='error', error_code='hermes_worker_timeout', observed_model_call_count=1)
        assert on_provider_lifecycle({'transition': 'response_received'})
        if self.graph:
            assert source_read_enabled
            operation = None
            if self.graph == 'recover-selected':
                bad_args = {'schema': 'dmb_expand_graph_retrieval_request_v1',
                    'retrievalSessionId': self.bootstrap.retrieval_session.id, 'operation': 'object',
                    'targets': [{'kind': 'node', 'id': 'frank'}], 'observationIds': ['unavailable']}
                denial = on_graph_operation({'toolName': 'expand_graph_retrieval', 'arguments': bad_args})
                refusal = json.loads(denial['resultJson'])
                assert refusal['code'] == 'selected_observation_unavailable' and refusal['statusCode'] == 422
                denied_body = json.loads(payload)
                denied_body['input'].extend([
                    {'type': 'function_call', 'name': 'expand_graph_retrieval', 'call_id': 'rejected', 'arguments': json.dumps(bad_args)},
                    {'type': 'function_call_output', 'call_id': 'rejected', 'output': denial['resultJson']}])
                payload = json.dumps(denied_body)
                assert authorize({'provider': request_budget['provider'], 'model': request_budget['model'],
                    'apiMode': request_budget['apiMode'], 'payloadJson': payload,
                    'payloadSha256': sha256(payload.encode()).hexdigest(), 'payloadUtf8Bytes': len(payload.encode())})
                assert on_provider_lifecycle({'transition': 'sdk_entered'})
                assert on_provider_lifecycle({'transition': 'response_received'})
            if self.graph in {'observation', 'selected-observation', 'paged', 'paged-mutated', 'paged-unseen', 'initial-small', 'initial-small-unseen', 'recover-selected', 'fatal-native', 'batch-selected'}:
                operation = on_graph_operation({'toolName': 'expand_graph_retrieval', 'arguments': {
                    'schema': 'dmb_expand_graph_retrieval_request_v1',
                    'retrievalSessionId': self.bootstrap.retrieval_session.id, 'operation': 'object',
                    **({'operation': 'observations', 'observationIds': ['observation-one', 'observation-two']}
                       if self.graph == 'batch-selected' else {'targets': [{'kind': 'node', 'id': 'frank'}]}),
                    **({'observationIds': ['observation-one']} if self.graph == 'selected-observation' else {}),
                }})
                operation_args = {'schema': 'dmb_expand_graph_retrieval_request_v1',
                    'retrievalSessionId': self.bootstrap.retrieval_session.id, 'operation': 'object',
                    'targets': [{'kind': 'node', 'id': 'frank'}]}
                operation_pages = []
                result = json.loads(operation['resultJson'])
                if self.graph == 'batch-selected' and result.get('schema') == 'dmb_graph_tool_overview_v1':
                    operation_args = {'retrievalSessionId': self.bootstrap.retrieval_session.id,
                        'operation': 'observations', 'observationIds': ['observation-one', 'observation-two'],
                        'schema': 'dmb_expand_graph_retrieval_request_v1'}
                    token = result['detailPageToken']
                    while token:
                        page_args = {**operation_args, 'resultPageToken': token}
                        page = on_graph_operation({'toolName': 'expand_graph_retrieval', 'arguments': page_args})
                        operation_pages.append((page_args, page['resultJson']))
                        token = json.loads(page['resultJson']).get('nextPageToken')
                if self.graph in {'paged', 'paged-mutated', 'paged-unseen'} and result.get('schema') == 'dmb_graph_tool_overview_v1':
                    overview_body = json.loads(payload)
                    overview_body['input'].extend([
                        {'type': 'function_call', 'name': 'expand_graph_retrieval', 'call_id': 'overview', 'arguments': json.dumps(operation_args)},
                        {'type': 'function_call_output', 'call_id': 'overview', 'output': operation['resultJson']}])
                    encoded = json.dumps(overview_body)
                    assert authorize({'provider': request_budget['provider'], 'model': request_budget['model'],
                        'apiMode': request_budget['apiMode'], 'payloadJson': encoded,
                        'payloadSha256': sha256(encoded.encode()).hexdigest(), 'payloadUtf8Bytes': len(encoded.encode())})
                    assert on_provider_lifecycle({'transition': 'sdk_entered'})
                    assert on_provider_lifecycle({'transition': 'response_received'})
                    token = result['detailPageToken']
                    while token:
                        page_args = {**operation_args, 'resultPageToken': token}
                        page = on_graph_operation({'toolName': 'expand_graph_retrieval', 'arguments': page_args})
                        operation_pages.append((page_args, page['resultJson']))
                        page_value = json.loads(page['resultJson'])
                        token = page_value.get('nextPageToken')
                        needed = [r for r in page_value.get('records', [])
                            if r['path'] == ['reviewedSourceObservations', 0]]
                        if any('value' in r or r.get('end') == r.get('length') for r in needed):
                            if self.mutation != 'multi-ref':
                                assert token, 'fixture must leave unrelated pages unread'
                            break
                elif self.graph in {'paged', 'paged-mutated', 'paged-unseen'} and result.get('schema') == 'dmb_graph_tool_page_v1':
                    assert result['nextPageToken'] is None
                    assert self.mutation == 'multi-ref'
                elif self.graph in {'initial-small', 'initial-small-unseen'}:
                    assert result['schema'] == 'dmb_graph_tool_overview_v1'
                    assert result['completeRecordCounts']['included'] == 1
                elif 'reviewedSourceObservations' not in result and not (self.graph == 'batch-selected' and result.get('schema') in {'dmb_graph_tool_overview_v1', 'dmb_graph_tool_page_v1'}):
                    return AgentRuntimeResult(status='error', error_code=result.get('code', 'graph_operation_unavailable'))
                if self.graph == 'observation':
                    assert result['reviewedSourceObservations'][0]['assertionId'] == 'observation-one'
            opened = on_graph_operation({'toolName': 'read_graph_source', 'arguments': {
                'retrievalSessionId': self.bootstrap.retrieval_session.id, 'anchorIds': ['anchor-one'], 'maxChars': 12000,
            }})
            result = json.loads(opened['resultJson'])
            source_pages = []
            if self.graph in {'paged', 'paged-mutated', 'paged-unseen'} and self.mutation != 'multi-ref':
                assert result['schema'] == 'dmb_graph_tool_page_v1'
            if result.get('schema') == 'dmb_graph_tool_page_v1':
                token = result.get('nextPageToken')
                while token:
                    page_args = {'retrievalSessionId': self.bootstrap.retrieval_session.id,
                        'anchorIds': ['anchor-one'], 'maxChars': 12000, 'resultPageToken': token}
                    page = on_graph_operation({'toolName': 'read_graph_source', 'arguments': page_args})
                    source_pages.append((page_args, page['resultJson']))
                    token = json.loads(page['resultJson']).get('nextPageToken')
            else:
                assert result.get('content') == 'Frank guards the western gate.', result
            body = json.loads(payload)
            if operation is not None:
                body['input'].extend([
                    {'type': 'function_call', 'name': 'expand_graph_retrieval', 'call_id': 'object-call', 'arguments': '{}'},
                    {'type': 'function_call_output', 'call_id': 'object-call', 'output': operation['resultJson']},
                ])
            body['input'].extend([
                {'type': 'function_call', 'name': 'read_graph_source', 'call_id': 'source-call', 'arguments': '{}'},
                {'type': 'function_call_output', 'call_id': 'source-call', 'output': opened['resultJson']},
            ])
            for tool, pages in [('expand_graph_retrieval', operation_pages if operation else []), ('read_graph_source', source_pages)]:
                for i, (page_args, page) in enumerate(reversed(pages)):
                    call_id = f'{tool}:{i}'
                    body['input'].extend([
                        {'type': 'function_call', 'name': tool, 'call_id': call_id, 'arguments': json.dumps(page_args)},
                        {'type': 'function_call_output', 'call_id': call_id, 'output': page}])
            if self.graph == 'paged-mutated':
                body['input'][-1]['output'] += ' '
            if self.omit_source:
                source_calls = {item['call_id'] for item in body['input']
                    if item.get('type') == 'function_call' and item.get('name') == 'read_graph_source'}
                body['input'] = [item for item in body['input'] if item.get('call_id') not in source_calls]
            encoded = json.dumps(body)
            if self.graph == 'paged-mutated':
                assert not authorize({'provider': request_budget['provider'], 'model': request_budget['model'],
                    'apiMode': request_budget['apiMode'], 'payloadJson': encoded,
                    'payloadSha256': sha256(encoded.encode()).hexdigest(), 'payloadUtf8Bytes': len(encoded.encode())})
                return AgentRuntimeResult(status='error', error_code='provider_authorization_denied')
            assert authorize({'provider': request_budget['provider'], 'model': request_budget['model'],
                'apiMode': request_budget['apiMode'], 'payloadJson': encoded,
                'payloadSha256': sha256(encoded.encode()).hexdigest(), 'payloadUtf8Bytes': len(encoded.encode())})
            assert on_provider_lifecycle({'transition': 'sdk_entered'})
            assert on_provider_lifecycle({'transition': 'response_received'})
            claim = {'claim_id': CLAIM_ID, 'target_kind': 'assertion' if operation else 'relationship',
                     'target_id': 'observation-one' if operation else 'rel-gate',
                     }
            if self.tamper_evidence:
                claim['evidence_ref_ids'] = [EVIDENCE_ID[:-1] + 'z']
            segment = {'kind': 'graph_claim', 'text': 'Frank guards the western gate.', **claim}
            if self.mutation == 'source-open':
                segment['source_opened'] = True
            elif self.mutation == 'target':
                segment['target_id'] = 'unadmitted-target'
            elif self.mutation == 'revision':
                segment['graph_revision'] = 'different-revision'
            if self.graph in {'paged-unseen', 'initial-small-unseen'}:
                segment['target_id'] = 'unrelated-observation'
            final = {'answer_context_status': 'graph_grounded', 'answer_segments': [segment]}
            if self.mutation == 'citation-map':
                final['citation_map'] = {'entries': [{**claim, 'source_opened': False}]}
            self.final_text = json.dumps(final)
            return AgentRuntimeResult(status='ok', final_text=self.final_text)
        segment = {'kind': 'saved_source_claim', 'text': 'Frank and Sara operate the Rocky Talkie.'}
        if self.forged:
            segment['content_sha256'] = 'f' * 64
        final = {'answer_context_status': 'source_only_insufficient_evidence', 'answer_segments': [segment]}
        if self.malformed:
            final['citation_map'] = {'wrong-citation-shape': []}
        self.final_text = json.dumps(final)
        return AgentRuntimeResult(status='ok', final_text=self.final_text,
            runtime_session_id='synthetic-build-session')


def execute(case, tmp_path, runtime, **overrides):
    _, request, bootstrap = case
    options = dict(root=tmp_path, pointer_store=HermesSessionPointerStore(tmp_path/'pointers'),
        owner_resolver=lambda _: {'kind': 'world', 'id': 'elderwyld', 'name': 'Elderwyld'},
        work_resolver=agent._work_resolver,
        graph_resolver=lambda *_: pytest.fail('generic Graph bypass'),
        plan_graph_resolver=lambda *_: bootstrap, runtime=runtime,
        conversation_service=AgentConversationService())
    options.update(overrides)
    return svc.execute_agent_turn(request, **options)


def test_build_source_answer_durable_history_and_replay(build_case, tmp_path, monkeypatch):
    source, request, bootstrap = build_case
    harness = SyntheticHarness(source, bootstrap)
    response = execute(build_case, tmp_path, harness)
    assert response.knowledge_context.receipt.source_basis.content_sha256 == source.content_sha256
    assert response.knowledge_context.receipt.graph_authority.native_world_id == 'native-build-world'
    assert response.knowledge_context.completion.answer_basis == 'saved_source'
    service = AgentConversationService()
    conversation = service.get_active_conversation('elderwyld')
    turn, = service.list_turns('elderwyld', conversation.conversation_id)
    assert turn.status == 'completed'
    assert turn.provenance.primary_work.kind == 'build'
    assert turn.provenance.primary_work.work_revision_id is None
    assert service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)
    projection = svc.project_plan_turn_context(turn, delivery_replay=False)
    assert projection.schema_ == 'dmb_build_graph_context_response_v1'
    from starlette.requests import Request
    monkeypatch.setattr(agent, 'enforce_native_graph_gm', lambda _: None)
    monkeypatch.setattr(agent, '_verified_world_id', lambda value: value)
    monkeypatch.setattr(agent, '_conversation_service', lambda _: service)
    page = agent.get_world_conversation_history('elderwyld', Request({'type': 'http'}),
        limit=50, before_sequence=None, include_turn_correlation=True)
    wire = page.model_dump(mode='json', by_alias=True)
    assert wire['schema'] == 'dmb_agent_conversation_history_v3'
    assert wire['turns'][0]['knowledge_context']['receipt']['source_basis']['document_id'] == source.record.document_id
    assert 'plan_context' not in wire['turns'][0]
    replay = execute(build_case, tmp_path, harness,
        work_resolver=lambda *_: pytest.fail('replay read current source'),
        plan_graph_resolver=lambda *_: pytest.fail('replay read Graph'))
    assert replay.knowledge_context.delivery_replay
    assert harness.calls == 1


@pytest.mark.parametrize('forged', [False, True], ids=['timeout', 'forged-source-hash'])
def test_build_failure_retains_execution_and_trace(build_case, tmp_path, forged):
    source, _, bootstrap = build_case
    with pytest.raises(svc.AgentTurnServiceError):
        execute(build_case, tmp_path, SyntheticHarness(source, bootstrap, fail=not forged, forged=forged))
    service = AgentConversationService()
    conversation = service.get_active_conversation('elderwyld')
    turn, = service.list_turns('elderwyld', conversation.conversation_id)
    assert turn.status == ('failed' if forged else 'interrupted')
    assert turn.graph_context_execution.events
    assert service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)
    assert turn.completion is None


@pytest.mark.parametrize('observation', [False, True, 'wrong_subject', 'wrong_source', 'mutated-evidence', 'paged', 'paged-mutated', 'paged-unseen', 'model-map', 'model-open', 'forged-target', 'forged-revision', 'omitted-source', 'multi-ref', 'selected-observation', 'initial-small', 'initial-small-unseen', 'recover-selected', 'fatal-native', 'batch-selected', 'batch-missing', 'batch-overflow', 'batch-wrong-world', 'batch-no-source'],
    ids=['relationship', 'reviewed-source-observation', 'foreign-observation-subject', 'foreign-observation-source', 'mutated-producing-evidence', 'parent-paged-evidence', 'mutated-page', 'unseen-page-claim', 'forbidden-model-map', 'forbidden-model-open', 'forged-target', 'forged-revision', 'performed-but-omitted-source', 'traversal-three-refs-one-open', 'selected-observation', 'initial-small', 'initial-small-unseen', 'recover-selected', 'fatal-native', 'batch-selected', 'batch-missing', 'batch-overflow', 'batch-wrong-world', 'batch-no-source'])
def test_build_graph_claim_uses_parent_source_broker_and_opens_pinned_target(build_case, tmp_path, monkeypatch, observation):
    from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
    from graph_memory.interaction.session import SourceAnchorState
    from graph_memory.interaction.session_store import create_session
    source, request, bootstrap = build_case
    session = bootstrap.retrieval_session
    session.claims = claims_from_retrieval_result({
        'relationships': [{'edgeId': 'rel-gate', 'sourceNodeId': 'frank', 'targetNodeId': 'gate',
            'predicate': 'guards', 'evidenceRefIds': [EVIDENCE_ID]}],
        'sourceAnchors': [{'anchorId': 'anchor-one', 'revisionId': 'native-rev-3',
            'evidenceRefId': EVIDENCE_ID, 'readable': True, 'supportingGraphObjectIds': ['rel-gate']}],
    }, revision_id='native-rev-3')
    session.source_anchors = [SourceAnchorState(anchor_id='anchor-one', readable=True)]
    create_session(session)
    bootstrap = replace(bootstrap, candidate_relationship_ids=('rel-gate',), candidate_evidence_ref_ids=(EVIDENCE_ID,),
        evidence_by_anchor_id={'anchor-one': EVIDENCE_ID}, source_scope_anchors=({
            'anchor_id': 'anchor-one', 'evidence_ref_id': EVIDENCE_ID, 'source_artifact_id': 'artifact-one',
            'source_revision_id': 'source-rev-one'},))
    if observation == 'multi-ref':
        bootstrap = replace(bootstrap, source_index_commitment={
            'schema': 'dmb_bounded_source_anchor_index_commitment_v1',
            'world_id': 'native-build-world', 'graph_revision': 'native-rev-3',
            'status': 'complete', 'max_entries': 512, 'eligible_count': 1,
            'source_pins': list(bootstrap.source_scope_anchors)})
    text = 'Frank guards the western gate.' * (310 if observation in {'paged', 'paged-mutated', 'paged-unseen'} else 1)
    digest = sha256(text.encode()).hexdigest()
    def read_external_graph(arguments, *, receipt_version):
        assert receipt_version == 2 and arguments['anchorIds'] == ['anchor-one']
        return {'schema': 'dmb_internal_read_graph_source_batch_v2', 'retrievalSessionId': session.id,
            'reads': [{'sourceReadId': 'source-read-one', 'result': {
                'schema': 'dmb_world_graph_source_anchor_read_v1', 'anchorId': 'anchor-one',
                'evidenceRefId': EVIDENCE_ID, 'sourceArtifactId': 'artifact-one',
                'outcome': 'enough', 'content': text, 'contentSha256': digest,
                'lineStart': 1, 'lineEnd': 1, 'truncated': False,
            }, 'receipt': {'source_read_id': 'source-read-one', 'retrieval_session_id': session.id,
                'graph_revision': 'native-rev-3', 'anchor_id': 'anchor-one', 'evidence_ref_id': EVIDENCE_ID,
                'source_artifact_id': 'artifact-one', 'source_revision_id': 'source-rev-one',
                'read_content_sha256': digest, 'outcome': 'enough', 'truncated': False}}]}
    monkeypatch.setattr('graph_memory.interaction.expansion_executor.execute_read_graph_source', read_external_graph)
    if observation:
        from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
        from apps.live_control_server.models.world_graph_object_projection import WorldGraphObjectReviewedSourceObservation
        from graph_memory.retrieval.models import WorldGraphRetrievalResult
        from types import SimpleNamespace
        native_observation = WorldGraphObjectReviewedSourceObservation(
            assertion_id='observation-one', subject_node_id='frank', observation_kind='worldbuilding_observation',
            text=text, entity_kind='npc', review_id='review-one', contribution_id='contribution-one',
            publication_revision_id='native-rev-3', source_artifact_id='artifact-one',
            source_revision_id='source-rev-one', evidence_ref_ids=[EVIDENCE_ID], visibility='gm', epistemic_kind='fact')
        if observation == 'wrong_subject':
            native_observation = native_observation.model_copy(update={'subject_node_id': 'another-person'})
        elif observation == 'wrong_source':
            native_observation = native_observation.model_copy(update={'source_revision_id': 'another-source-revision'})
        if observation == 'multi-ref':
            native_observation = native_observation.model_copy(update={
                'evidence_ref_ids': sorted([EVIDENCE_ID, 'evidence-extra-one', 'evidence-extra-two'])})
        observations = (native_observation,)
        if observation in {'paged', 'paged-mutated', 'paged-unseen', 'initial-small', 'initial-small-unseen'}:
            observations += (native_observation.model_copy(update={
                'assertion_id': 'unrelated-observation', 'text': 'Unrelated qualified description. ' * 1500}),)
        result = WorldGraphRetrievalResult.model_validate({
            'operation': 'object', 'outcome': 'enough', 'requestedNodeId': 'frank',
            'snapshot': {'worldId': 'native-build-world', 'campaignId': '', 'scopeMode': 'world',
                'focus': {'kind': 'none', 'sessionId': None}, 'admissibility': 'gm', 'revisionId': 'native-rev-3',
                'headRevisionId': 'native-rev-3', 'isHead': True},
            'sourceAnchors': [{'anchorId': 'anchor-one', 'revisionId': 'native-rev-3', 'evidenceRefId': EVIDENCE_ID,
                'sourceArtifactId': 'artifact-one', 'sourceDomain': 'worldbuilding', 'readable': True,
                'locatorKind': 'source_span', 'supportingAssertionIds': [row.assertion_id for row in observations]}],
        })
        pins = [SimpleNamespace(anchor_id='anchor-one', graph_revision='native-rev-3', evidence_ref_id=EVIDENCE_ID,
            source_artifact_id='artifact-one', source_revision_id='source-rev-one')]
        if observation == 'multi-ref':
            extra_anchors = [result.source_anchors[0].model_copy(update={
                'anchor_id': f'anchor-extra-{i}', 'evidence_ref_id': ref})
                for i, ref in enumerate(['evidence-extra-one', 'evidence-extra-two'])]
            result = result.model_copy(update={'source_anchors': [*result.source_anchors, *extra_anchors]})
            pins.extend(SimpleNamespace(anchor_id=anchor.anchor_id, graph_revision='native-rev-3',
                evidence_ref_id=anchor.evidence_ref_id, source_artifact_id='artifact-one',
                source_revision_id='source-rev-one') for anchor in extra_anchors)
        if str(observation).startswith('batch-'):
            second = native_observation.model_copy(update={'assertion_id': 'observation-two',
                'subject_node_id': 'sara', 'text': 'Sara watches the eastern gate.',
                'evidence_ref_ids': ['evidence-two']})
            observations += (second,)
            second_anchor = result.source_anchors[0].model_copy(update={'anchor_id': 'anchor-two',
                'evidence_ref_id': 'evidence-two', 'supporting_assertion_ids': ['observation-two']})
            result = result.model_copy(update={'operation': 'observations', 'matched_node_ids': ['frank', 'sara'],
                'source_anchors': [*result.source_anchors, second_anchor]})
            pins.append(SimpleNamespace(anchor_id='anchor-two', graph_revision='native-rev-3',
                evidence_ref_id='evidence-two', source_artifact_id='artifact-one', source_revision_id='source-rev-one'))
            bootstrap = replace(bootstrap, build_source_discovery={'status': 'complete',
                'world_id': 'native-build-world', 'graph_revision': 'native-rev-3',
                'source_artifact_id': 'artifact-one', 'source_revision_id': 'source-rev-one'})
        resolved = direct.ResolvedWorldGraphReviewedObjectV3(result, tuple(sorted(pins, key=lambda pin: pin.anchor_id)), observations, (), ())
        monkeypatch.setattr(direct, 'direct_services_from_config', lambda _: SimpleNamespace())
        def read_reviewed(*_args, **kwargs):
            if kwargs.get('observation_ids') == ('unavailable',) or observation == 'fatal-native':
                raise direct.DirectWorldGraphReadError('Synthetic native refusal',
                    code='source_integrity_error' if observation == 'fatal-native' else 'selected_observation_unavailable',
                    status_code=422)
            assert kwargs == ({'observation_ids': ('observation-one',)} if observation == 'selected-observation' else {})
            return resolved
        monkeypatch.setattr(direct, 'get_object_with_reviewed_sources_direct_v3', read_reviewed)
        if str(observation).startswith('batch-'):
            if observation == 'batch-wrong-world':
                bootstrap = replace(bootstrap, build_source_discovery={**bootstrap.build_source_discovery, 'world_id': 'foreign'})
            if observation == 'batch-no-source':
                bootstrap = replace(bootstrap, build_source_discovery=None)
            def read_batch(_services, effective):
                if observation in {'batch-missing', 'batch-overflow'}:
                    raise direct.DirectWorldGraphReadError('Synthetic atomic selection refusal',
                        code='selected_observation_unavailable' if observation == 'batch-missing' else 'observation_selection_overflow',
                        status_code=422 if observation == 'batch-missing' else 413)
                if observation in {'batch-wrong-world', 'batch-no-source'}:
                    pytest.fail('Invalid frozen source reached native selection')
                assert effective.observation_ids == ['observation-one', 'observation-two']
                assert effective.source_artifact_id == 'artifact-one'
                assert effective.source_revision_id == 'source-rev-one' and effective.revision_pin == 'native-rev-3'
                return resolved
            monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.selected_observation_reads.select_observations_direct', read_batch)
        monkeypatch.setattr(svc._PolicyExecutionAdapter, '_related_recap_offers', lambda *_: [])
    if observation in {'batch-missing', 'batch-overflow', 'batch-wrong-world', 'batch-no-source'}:
        with pytest.raises(svc.AgentTurnServiceError):
            execute((source, request, bootstrap), tmp_path, SyntheticHarness(source, bootstrap, graph='batch-selected'))
        service = AgentConversationService()
        conversation = service.get_active_conversation('elderwyld')
        turn, = service.list_turns('elderwyld', conversation.conversation_id)
        assert not any(e.kind in {'validated_graph_operation_v3', 'source_scope_extension_v3'}
            for e in turn.graph_context_execution.events)
        assert turn.completion is None
        return
    if observation in {'wrong_subject', 'wrong_source'}:
        with pytest.raises(svc.AgentTurnServiceError):
            execute((source, request, bootstrap), tmp_path, SyntheticHarness(source, bootstrap, graph='observation'))
        service = AgentConversationService()
        conversation = service.get_active_conversation('elderwyld')
        turn, = service.list_turns('elderwyld', conversation.conversation_id)
        assert not any(e.kind == 'validated_graph_operation_v3' for e in turn.graph_context_execution.events)
        assert turn.completion is None
        return
    if observation in {'mutated-evidence', 'paged-mutated'}:
        with pytest.raises(svc.AgentTurnServiceError):
            execute((source, request, bootstrap), tmp_path,
                SyntheticHarness(source, bootstrap, graph='paged-mutated' if observation == 'paged-mutated' else 'observation', tamper_evidence=observation == 'mutated-evidence'))
        service = AgentConversationService()
        conversation = service.get_active_conversation('elderwyld')
        turn, = service.list_turns('elderwyld', conversation.conversation_id)
        assert turn.completion is None
        return
    harness = SyntheticHarness(source, bootstrap,
        graph=observation if observation in {'initial-small', 'initial-small-unseen', 'recover-selected', 'fatal-native', 'batch-selected'} else 'selected-observation' if observation == 'selected-observation' else 'paged' if observation == 'multi-ref' else (observation if observation in {'paged', 'paged-unseen'} else ('observation' if observation else True)),
        mutation={'model-map':'citation-map','model-open':'source-open','forged-target':'target',
            'forged-revision':'revision', 'multi-ref':'multi-ref'}.get(observation), omit_source=observation == 'omitted-source')
    if observation == 'fatal-native':
        with pytest.raises(svc.AgentTurnServiceError):
            execute((source, request, bootstrap), tmp_path, harness)
        service = AgentConversationService()
        conversation = service.get_active_conversation('elderwyld')
        turn, = service.list_turns('elderwyld', conversation.conversation_id)
        assert turn.completion is None and turn.status != 'completed'
        return
    if observation in {'paged-unseen', 'initial-small-unseen', 'model-map', 'model-open', 'forged-target', 'forged-revision'}:
        with pytest.raises(svc.AgentTurnServiceError) as error:
            execute((source, request, bootstrap), tmp_path, harness)
        assert error.value.code == 'answer_validation_failed'
        service = AgentConversationService()
        conversation = service.get_active_conversation('elderwyld')
        turn, = service.list_turns('elderwyld', conversation.conversation_id)
        assert turn.completion is None and turn.assistant_text is None
        return
    response = execute((source, request, bootstrap), tmp_path, harness)
    context = response.knowledge_context
    assert context.completion.answer_basis == 'saved_source_plus_world_graph'
    citation, = context.completion.citation_map.entries
    if observation == 'omitted-source':
        assert not citation.source_opened and citation.source_read_ids == []
        service = AgentConversationService()
        conversation = service.get_active_conversation('elderwyld')
        turn, = service.list_turns('elderwyld', conversation.conversation_id)
        assert any(e.kind == 'validated_source_read_v2' for e in turn.graph_context_execution.events)
        return
    assert citation.source_opened and citation.source_read_ids == ['source-read-one']
    expected_refs = sorted([EVIDENCE_ID, 'evidence-extra-one', 'evidence-extra-two']) if observation == 'multi-ref' else [EVIDENCE_ID]
    assert citation.evidence_ref_ids == expected_refs and citation.claim_id == CLAIM_ID
    if observation == 'batch-selected':
        service = AgentConversationService()
        conversation = service.get_active_conversation('elderwyld')
        turn, = service.list_turns('elderwyld', conversation.conversation_id)
        event, = [e for e in turn.graph_context_execution.events if e.kind == 'validated_graph_operation_v3']
        assert event.assertion_ids == ['observation-one', 'observation-two']
        assert set(event.evidence_ref_ids) == {EVIDENCE_ID, 'evidence-two'}
        assert len(event.returned_source_pins) == 2
        assert citation.evidence_ref_ids == [EVIDENCE_ID]
        captured = service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)
        assert any(o.kind == 'graph_tool' and o.request.operation == 'observations'
            and o.request.observation_ids == ['observation-one', 'observation-two']
            for trace in captured for o in trace.observations)

    if observation == 'multi-ref':
        assert len(context.source_open_targets) == 3
        assert sum(t.source_read_id is not None for t in context.source_open_targets) == 1
    target, = [target for target in context.source_open_targets if target.evidence_ref_id == EVIDENCE_ID]
    assert target.managed_world_id == 'elderwyld' and target.native_world_id == 'native-build-world'
    assert target.evidence_ref_id == EVIDENCE_ID and target.claim_id == CLAIM_ID
    assert target.source_revision_id == 'source-rev-one' and target.graph_revision == 'native-rev-3'
    service = AgentConversationService()
    conversation = service.get_active_conversation('elderwyld')
    turn, = service.list_turns('elderwyld', conversation.conversation_id)
    traces = service.list_context_trace_attempts(world_id='elderwyld', turn_id=turn.turn_id)
    assert any(getattr(observation, 'text', None) == text and observation.evidence_ref_id == EVIDENCE_ID
        for trace in traces for observation in trace.observations)
    if observation == 'multi-ref':
        assert turn.status == 'completed' and turn.completion.citation_map.entries[0] == citation
        assert not {'evidence-extra-one', 'evidence-extra-two'} & set(turn.graph_context_receipt.assembled_input.dispatched_evidence_ref_ids)
        assert len(citation.source_read_ids) == 1
    if observation:
        event, = [e for e in turn.graph_context_execution.events if e.kind == 'validated_graph_operation_v3']
        assert set(event.assertion_ids) == ({'observation-one', 'unrelated-observation'} if observation in {'paged', 'initial-small', 'initial-small-unseen'} else {'observation-one', 'observation-two'} if observation == 'batch-selected' else {'observation-one'})
        assert event.returned_source_pins[0].source_revision_id == 'source-rev-one'
        if observation == 'initial-small':
            attempts = [e for e in turn.graph_context_execution.events if e.kind == 'provider_attempt_authorized_v3']
            assert set(attempts[-1].included_assertion_ids) == {'observation-one'}
            assert 'unrelated-observation' not in attempts[-1].included_assertion_ids
            assert len(attempts[-1].included_source_read_event_ids) == 1
        if observation == 'paged':
            attempts = [e for e in turn.graph_context_execution.events if e.kind == 'provider_attempt_authorized_v3']
            assert len(attempts) == 3
            assert 'observation-one' not in attempts[1].included_assertion_ids
            assert 'observation-one' in attempts[2].included_assertion_ids
            assert 'unrelated-observation' not in attempts[2].included_assertion_ids
            assert len(attempts[2].included_source_read_event_ids) == 1
            assert len([e for e in turn.graph_context_execution.events if e.kind == 'validated_source_read_v2']) == 1


@pytest.mark.parametrize('change', ['source', 'question'])
def test_changed_build_retry_cannot_dispatch(build_case, tmp_path, change):
    source, request, bootstrap = build_case
    harness = SyntheticHarness(source, bootstrap)
    execute(build_case, tmp_path, harness)
    if change == 'source':
        request = request.model_copy(update={'primary_work': request.primary_work.model_copy(
            update={'expected_content_sha256': 'f' * 64})})
    else:
        request = request.model_copy(update={'message': 'Another question'})
    with pytest.raises(svc.AgentTurnServiceError) as error:
        execute((source, request, bootstrap), tmp_path, harness)
    assert error.value.code == 'turn_idempotency_conflict'
    assert harness.calls == 1


def test_stale_build_source_refuses_before_provider_admission(build_case, tmp_path):
    source, request, bootstrap = build_case
    (tmp_path / source.record.target_relpath).write_text('Changed source body')
    harness = SyntheticHarness(source, bootstrap)
    with pytest.raises(svc.AgentTurnServiceError) as error:
        execute(build_case, tmp_path, harness)
    assert error.value.code == 'build_source_unavailable'
    assert harness.calls == 0
    assert AgentConversationService().get_active_conversation('elderwyld') is None


def test_over_limit_native_evidence_refuses_before_provider_dispatch(build_case, tmp_path):
    source, request, bootstrap = build_case
    bootstrap = replace(bootstrap, source_scope_anchors=({
        'anchor_id': 'anchor-one', 'evidence_ref_id': EVIDENCE_ID + 'x',
        'source_artifact_id': 'artifact-one', 'source_revision_id': 'source-rev-one'},))
    with pytest.raises(svc.AgentTurnServiceError) as error:
        execute((source, request, bootstrap), tmp_path, SyntheticHarness(source, bootstrap, refuse=True))
    assert error.value.provider_dispatched is False
    assert AgentConversationService().get_active_conversation('elderwyld') is None


def test_rejected_build_answer_survives_only_in_protected_trace(build_case, tmp_path):
    source, _, bootstrap = build_case
    harness = SyntheticHarness(source, bootstrap, malformed=True)
    with pytest.raises(svc.AgentTurnServiceError) as error:
        execute(build_case, tmp_path, harness)
    assert error.value.code == 'answer_validation_failed'
    service = AgentConversationService()
    conversation = service.get_active_conversation('elderwyld')
    turn, = service.list_turns('elderwyld', conversation.conversation_id)
    assert turn.status == 'failed' and turn.failure_code == 'answer_validation_failed'
    assert turn.assistant_text is None and turn.completion is None
    assert harness.final_text not in turn.model_dump_json()
    traces = service.list_context_trace_attempts(world_id='elderwyld',turn_id=turn.turn_id)
    drafts = [material for trace in traces for observation in trace.observations
        if observation.kind == 'context_snapshot' for material in observation.materials
        if material.item_id.startswith('unvalidated-provider-answer:')]
    assert len(drafts) == 1 and drafts[0].text == harness.final_text
    producer = [e for e in turn.graph_context_execution.events if e.kind == 'provider_attempt_authorized_v3'][-1]
    assert str(producer.provider_attempt_id) in drafts[0].item_id
    assert turn.graph_context_receipt.context_receipt_sha256 in drafts[0].item_id
    assert all(not hasattr(material, 'claim_id') for material in drafts)


@pytest.mark.parametrize('malformed', [True, False])
def test_answer_capture_persistence_error_cannot_publish_or_mask_parse_failure(build_case,tmp_path,monkeypatch,malformed):
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
    def failed_capture(*args,**kwargs):
        raise ApplicationStateConflictError('synthetic fenced capture')
    monkeypatch.setattr(ContextTraceCollector,'answer_draft',failed_capture)
    source,_,bootstrap=build_case
    harness=SyntheticHarness(source,bootstrap,malformed=malformed)
    with pytest.raises(svc.AgentTurnServiceError) as error:
        execute(build_case,tmp_path,harness)
    assert error.value.code == ('answer_validation_failed' if malformed else 'turn_persistence_indeterminate')
    service=AgentConversationService()
    conversation=service.get_active_conversation('elderwyld')
    turn,=service.list_turns('elderwyld',conversation.conversation_id)
    assert turn.completion is None and turn.assistant_text is None
    if malformed:
        assert turn.status == 'failed' and turn.failure_code == 'answer_validation_failed'


def test_build_discovery_reaches_governed_provider_without_admitting_claims(build_case, tmp_path):
    source, request, bootstrap = build_case
    packet = {"schema": "dmb_build_source_discovery_v1", "discovery_only": True,
              "entries": [{"subject_object_id": "person:barin", "assertion_id": "discovery:only"}],
              "eligible_count": 1, "status": "complete"}
    bootstrap = replace(bootstrap, build_source_discovery=packet)
    harness = SyntheticHarness(source, bootstrap)
    result = execute((source, request, bootstrap), tmp_path, harness)
    assert result.answer.status == "ok"
    assert "person:barin" in harness.request_question
    assert bootstrap.candidate_assertion_ids == ()
    assert bootstrap.candidate_evidence_ref_ids == ()


def test_missing_discovery_in_final_provider_payload_is_rejected(build_case, tmp_path):
    source, request, bootstrap = build_case
    bootstrap = replace(bootstrap, build_source_discovery={"discovery_only": True, "entries": []})
    harness = SyntheticHarness(source, bootstrap, refuse=True)
    harness.omit_discovery = True
    with pytest.raises(svc.AgentTurnServiceError):
        execute((source, request, bootstrap), tmp_path, harness)
