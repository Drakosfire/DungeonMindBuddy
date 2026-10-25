"""Authored identity is scoped input, not labels parsed from generated prose."""
from uuid import uuid4
import pytest
from pydantic import ValidationError
from application_state.agent_conversation.authored_graph_references import (
    AuthoredGraphReferenceV1 as Reference, AuthoredGraphReferencesV1 as References,
    effective_references,
)
from application_state.agent_conversation.work_plan import StepV2, DispatchV2, PlanV3, PlanV2


def ref(node='object:cedar-box', **kw):
    return Reference(managed_world_id='quarry', native_world_id='native-quarry', binding_version=1,
        graph_revision='revision-one', node_id=node, label='Cedar box', **kw)


def test_exact_identity_and_conflicting_snapshot_refusal():
    original = ref()
    assert original.node_id == 'object:cedar-box'
    assert effective_references([original], [original.model_copy(update={'label': 'Renamed display'})]) == (original,)
    with pytest.raises(ValueError, match='conflicting'):
        effective_references([original], [original.model_copy(update={'graph_revision': 'revision-two'})])
    with pytest.raises(ValueError, match='distinct'):
        References(references=(original, original))
    with pytest.raises(ValueError, match='different managed World'):
        References(references=(original,)).require_world('another-world')
    with pytest.raises(ValidationError):
        Reference.model_validate(original.model_dump(by_alias=True) | {'summary': 'Claimed evidence'})


def test_dispatch_freezes_only_root_and_selected_step_references():
    root, selected, sibling = ref('root'), ref('selected'), ref('sibling')
    one = StepV2(step_id=uuid4(), text='Discuss this box.', selected=True, references=(selected,))
    two = StepV2(step_id=uuid4(), text='Defer this other box.', selected=False, references=(sibling,))
    dispatch = DispatchV2(command_id=uuid4(), step_id=one.step_id, client_thread_id=uuid4(),
        client_turn_id=uuid4(), message='Exact authored instruction',
        authored_references=References(references=effective_references((root,), one.references)))
    plan = PlanV3(world_id='quarry', conversation_id=uuid4(), source_turn_id=uuid4(),
        source_answer_sha256='a'*64, document_id='page', revision=1, objective='Keep the wick dry.',
        root_references=(root,), steps=[one, two], dispatches=[dispatch])
    before = dispatch.model_dump(mode='json', by_alias=True)
    later = PlanV3.model_validate(plan.model_dump(by_alias=True) | {'root_references': []})
    assert later.dispatches[0].model_dump(mode='json', by_alias=True) == before
    assert [r.node_id for r in dispatch.authored_references.references] == ['root', 'selected']
    assert 'sibling' not in str(before)
    with pytest.raises(ValidationError):
        PlanV2.model_validate(plan.model_dump(by_alias=True))


def acquired_execution(*, partial=False):
    """Focused validator fixture; native/APP integration is proved separately."""
    from types import SimpleNamespace
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.authored_graph_references import POLICY, digest
    refs = References(references=(ref(),))
    captured = t.BuildAuthoredReferencesCapturedV1(event_id=uuid4(), sequence=0,
        kind='build_authored_references_captured_v1', references=refs,
        read_graph_revision='read-revision', turn_id=uuid4(), conversation_id=uuid4(),
        attempt=1, submitted_intent_fingerprint='a'*64)
    arguments = {'retrievalSessionId': 'session', 'operation': 'object',
        'targets': [{'kind': 'node', 'id': ref().node_id}]}
    authorized = t.BuildAuthoredReferenceAuthorizedV1(event_id=uuid4(), sequence=1,
        kind='build_authored_reference_authorized_v1', capture_event_id=captured.event_id,
        node_id=ref().node_id, arguments_sha256=digest(arguments))
    pin = SimpleNamespace(anchor_id='pin', evidence_ref_id='evidence', source_artifact_id='artifact', source_revision_id='revision')
    operation = t.ValidatedGraphOperationEventV3.model_construct(event_id=uuid4(), sequence=2,
        kind='validated_graph_operation_v3', request_arguments_sha256=digest(arguments),
        graph_revision='read-revision', returned_source_pins=[pin], truncated=partial,
        coverage_status='incomplete' if partial else 'complete', evidence_sufficiency_status='sufficient')
    receipt = SimpleNamespace(**vars(pin), outcome='enough', truncated=False, evidence_sufficiency_status='sufficient')
    source = t.ValidatedSourceReadEventV2.model_construct(event_id=uuid4(), sequence=3,
        kind='validated_source_read_v2', receipts=[receipt])
    read = t.BuildAuthoredReferenceReadV1(event_id=uuid4(), sequence=4,
        kind='build_authored_reference_read_v1', capture_event_id=captured.event_id,
        authorization_event_id=authorized.event_id, node_id=ref().node_id,
        operation_event_ids=[operation.event_id], source_read_event_ids=[source.event_id],
        returned_node_ids=[ref().node_id], outcome='read_partial' if partial else 'read')
    policy = SimpleNamespace(authored_graph_reference_policy=POLICY,
        authored_graph_references_sha256=refs.sha256,
        source_read_scope=SimpleNamespace(world_id='quarry', graph_revision='read-revision', retrieval_session_id='session'),
        provider_roles=SimpleNamespace(writer=SimpleNamespace(identity=lambda: ('openai', 'writer', 'responses'))))
    return SimpleNamespace(policy=policy, events=[captured, authorized, operation, source, read])


def test_partial_object_cannot_be_presented_as_complete_and_receipt_is_single_use():
    from application_state.agent_conversation.authored_graph_references import validate_execution, writer_context, validate_packet
    execution = acquired_execution(partial=True)
    validate_execution(execution)
    with pytest.raises(ValueError, match='not been read successfully'):
        writer_context(execution)
    complete = acquired_execution()
    context = writer_context(complete)
    assert 'label' not in context['selected_references']['references'][0]
    validate_packet({'authored_reference_context': context}, complete)
    with pytest.raises(ValueError, match='differs'):
        validate_packet({}, complete)
    original = execution.events[-1]
    execution.events[-1] = original.model_copy(update={'outcome': 'read'})
    with pytest.raises(ValueError, match='partial object coverage'):
        validate_execution(execution)
    execution.events[-1] = original
    execution.events.append(original.model_copy(update={'event_id': uuid4(), 'sequence': 5}))
    with pytest.raises(ValueError, match='recorded twice'):
        validate_execution(execution)


def test_retry_preserves_original_selection_and_rejects_newer_composer_references():
    from types import SimpleNamespace
    from application_state.agent_conversation.retry import validate_reference_retry, RetryUnavailableError
    execution = acquired_execution()
    original = execution.events[0].references
    parent = SimpleNamespace(graph_context_execution=execution)
    validate_reference_retry(parent, SimpleNamespace(authored_references=original))
    for changed in (None, References(references=()), References(references=(ref('unrelated'),)),
        References(references=(ref().model_copy(update={'graph_revision': 'new-origin'}),))):
        with pytest.raises(RetryUnavailableError, match='original Graph references'):
            validate_reference_retry(parent, SimpleNamespace(authored_references=changed))
    legacy = SimpleNamespace(graph_context_execution=None)
    validate_reference_retry(legacy, SimpleNamespace())
    with pytest.raises(RetryUnavailableError):
        validate_reference_retry(legacy, SimpleNamespace(authored_references=original))


def test_object_result_proof_joins_exact_selected_identity_and_validated_bytes():
    from application_state.agent_conversation.authored_graph_references import validate_object_result_proof, digest
    execution = acquired_execution()
    operation, read = execution.events[2], execution.events[-1]
    packet = {'operation': 'object', 'requestedNodeId': ref().node_id,
        'nodes': [{'nodeId': ref().node_id, 'label': 'Native label'}]}
    execution.events[2] = operation.model_copy(update={'result_packet_sha256': digest(packet)})
    proof = {str(operation.event_id): packet | {'retrievalSessionId': 'session', 'claimLedger': [], 'addedClaimIds': []}}
    validate_object_result_proof(read, execution, proof)
    with pytest.raises(ValueError, match='validated native result'):
        validate_object_result_proof(read, execution, {str(operation.event_id): packet | {'nodes': []}})
    unrelated = packet | {'nodes': [{'nodeId': 'unrelated'}]}
    execution.events[2] = operation.model_copy(update={'result_packet_sha256': digest(unrelated)})
    with pytest.raises(ValueError, match='selected identity'):
        validate_object_result_proof(read, execution, {str(operation.event_id): unrelated})
