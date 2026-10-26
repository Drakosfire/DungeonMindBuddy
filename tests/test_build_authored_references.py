"""Authored node context through the actual SDK and disposable APP boundaries."""
from dataclasses import replace
import json
import pytest
from application_state.agent_conversation import AgentConversationService, types as t
from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1, AuthoredGraphReferencesV1
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_build_world_context import build_case, world_case, WorldDecisions
from tests.test_agent_build_jev_ordinary_harness import WriterWire, ordinary_case
from tests.test_agent_build_governed_graph import execute
from tests.test_build_jev_estimated_continuations import counter


def referenced_case(build_case, monkeypatch, *, authoring=True):
    authoring_case, _ = ordinary_case(build_case, monkeypatch, authoring=authoring)
    (source, request, bootstrap), reads = world_case(authoring_case, monkeypatch)
    # The native boundary is synthetic in this fixture; SDK and APP are real.
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as native
    from graph_memory.retrieval.models import WorldGraphRetrievalNode
    original_object = native.get_object_with_reviewed_sources_direct_v3
    def current_object(services, query):
        value = original_object(services, query)
        return replace(value, result=value.result.model_copy(update={'nodes': [WorldGraphRetrievalNode(node_id='frank',
            label='River Watch', kind='npc', role='match')] if query.node_id == 'frank' else []}))
    monkeypatch.setattr(native, 'get_object_with_reviewed_sources_direct_v3', current_object)
    monkeypatch.setattr(native, 'get_object_direct', lambda services, query: current_object(services, query).result)
    ref = AuthoredGraphReferenceV1(managed_world_id='elderwyld', native_world_id=bootstrap.world_scope.world_id,
        binding_version=bootstrap.binding_version, graph_revision=bootstrap.world_scope.revision_id,
        node_id='frank', label='CLIENT DISPLAY ONLY — NEVER PROVIDER CONTEXT')
    request = request.model_copy(update={'build_authored_references': AuthoredGraphReferencesV1(references=(ref,))})
    return (source, request, bootstrap), reads


@pytest.mark.parametrize('operation', ['propose_build_insertion', 'prepare_build_image'])
def test_authored_object_reaches_one_authoring_writer_with_durable_input_proof(build_case, monkeypatch, tmp_path, operation):
    case, reads = referenced_case(build_case, monkeypatch)
    decisions = WorldDecisions()
    decisions.operation = operation
    from tests.test_build_jev_image import ImageWire
    writer = ImageWire() if operation == 'prepare_build_image' else WriterWire()
    harness = BuildJevHarness(world_context=True, named_citations=True, related_pages=True,
        accounting=counter(), decision_transport=decisions, writer_transport=writer)
    response = execute(case, tmp_path, harness, operator_subject='local_operator')
    completion = response.knowledge_context.completion
    assert isinstance(completion, t.BuildImagePreparationCompletionV1 if operation == 'prepare_build_image' else t.BuildAuthoringCompletionV1)
    assert len(writer.calls) == 1
    body = json.loads(writer.calls[0].content)
    packet = json.loads(body['input'])
    assert packet['authored_reference_context']['selected_references']['references'][0]['node_id'] == 'frank'
    assert packet['authored_reference_passages']
    assert all('CLIENT DISPLAY ONLY' not in call.content.decode() for call in [*writer.calls, *decisions.calls])
    service = AgentConversationService()
    turns = service.list_turns('elderwyld', case[1].build_write_capability.conversation_id)
    turn = next(turn for turn in turns if turn.completion == completion)
    execution = turn.graph_context_execution
    assert len([e for e in execution.events if isinstance(e, t.BuildAuthoredReferencesCapturedV1)]) == 1
    proofs = [e for e in execution.events if isinstance(e, t.BuildAuthoredProviderInclusionV1)]
    assert len(proofs) == 1 and proofs[0].source_read_event_ids
    assert proofs[0].provider_attempt_id == completion.provider_attempt_id
    assert proofs[0].envelope_sha256 == completion.envelope_sha256


@pytest.mark.parametrize('mutation', ['source_text', 'missing_context'])
def test_self_consistent_host_packet_cannot_substitute_for_actual_source_authority(build_case, monkeypatch, tmp_path, mutation):
    case, _ = referenced_case(build_case, monkeypatch)
    from apps.live_control_server.services import build_authored_references as owner
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    original = owner.writer_material
    def corrupt(adapter):
        material = original(adapter)
        if mutation == 'source_text':
            material['authored_reference_passages'][0]['text'] = 'Unsupported replacement source text.'
        else:
            material.pop('authored_reference_context')
        return material
    monkeypatch.setattr(owner, 'writer_material', corrupt)
    decisions = WorldDecisions()
    decisions.operation = 'propose_build_insertion'
    writer = WriterWire()
    harness = BuildJevHarness(world_context=True, named_citations=True, related_pages=True,
        accounting=counter(), decision_transport=decisions, writer_transport=writer)
    with pytest.raises(AgentTurnServiceError):
        execute(case, tmp_path, harness)
    assert not writer.calls


def test_discussion_keeps_authored_reads_without_asking_for_a_relevance_vote(build_case, monkeypatch, tmp_path):
    case, reads = referenced_case(build_case, monkeypatch, authoring=False)
    decisions, writer = WorldDecisions(), WriterWire()
    harness = BuildJevHarness(world_context=True, named_citations=True, related_pages=True,
        accounting=counter(), decision_transport=decisions, writer_transport=writer)
    response = execute(case, tmp_path, harness)
    assert len(writer.calls) == 1
    # One original-snapshot membership check plus one current object acquisition.
    assert reads == {'graph': 2, 'source': 1}
    # Native object acquisition is host-owned; it must not reappear as an optional vote.
    assert all('world-object:frank' not in call.content.decode() for call in decisions.calls)
    packet = json.loads(json.loads(writer.calls[0].content)['input'])
    assert packet['authored_reference_context']['selected_references']['references'][0]['node_id'] == 'frank'
    assert packet['opened_passages']
    assert all('CLIENT DISPLAY ONLY' not in call.content.decode() for call in [*writer.calls, *decisions.calls])
    from application_state.agent_conversation.authored_graph_references import source_event_ids
    turn = AgentConversationService().list_turns('elderwyld', response.conversation.conversation_id)[0]
    mandatory = source_event_ids(turn.graph_context_execution)
    selections = [e for e in turn.graph_context_execution.events if isinstance(e, t.BuildWriterEvidenceSelectionV1)]
    assert len(selections) == 1
    assert not mandatory.intersection(selections[0].source_event_ids)

def test_missing_origin_retains_selected_input_without_authorizing_a_provider(build_case, monkeypatch, tmp_path):
    case, _ = referenced_case(build_case, monkeypatch, authoring=False)
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as native
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    original = native.get_object_direct
    monkeypatch.setattr(native, 'get_object_direct', lambda services, query: original(services, query).model_copy(update={'nodes': []}))
    decisions, writer = WorldDecisions(), WriterWire()
    harness = BuildJevHarness(world_context=True, named_citations=True, related_pages=True,
        accounting=counter(), decision_transport=decisions, writer_transport=writer)
    with pytest.raises(AgentTurnServiceError, match='absent from its original snapshot'):
        execute(case, tmp_path, harness)
    assert not decisions.calls and not writer.calls
    service = AgentConversationService()
    pointer = service.get_world_pointer('elderwyld')
    turn = service.list_turns('elderwyld', pointer.active_conversation_id)[0]
    captures = [e for e in turn.graph_context_execution.events if isinstance(e, t.BuildAuthoredReferencesCapturedV1)]
    assert len(captures) == 1 and captures[0].references == case[1].build_authored_references
    from application_state.agent_conversation import retry
    from application_state.unit_of_work import unit_of_work
    from application_state.agent_conversation.service import _ready_dsn
    with unit_of_work(_ready_dsn()) as conn:
        context = retry.context(conn, turn, active=True)
    assert context['schema'] == 'dmb_turn_retry_context_row_v2'
    assert context['authored_references'] == captures[0].references.model_dump(mode='json', by_alias=True)
