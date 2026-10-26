"""Real APP review/dispatch persistence for author-edited Graph context."""
from uuid import UUID, uuid4
import pytest
from application_state.agent_conversation import work_plan as w
from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1
from application_state.errors import ApplicationStateConflictError
from tests.application_state.test_reviewed_work_plan import case


def reference(node):
    return AuthoredGraphReferenceV1(managed_world_id='world-one', native_world_id='native-world',
        binding_version=1, graph_revision='selected-revision', node_id=node, label=node)


def test_review_adds_references_and_dispatch_preserves_selected_snapshot(case):
    service, cid, source, steps, before = case
    root, selected, deferred = [reference(x) for x in ('root-box', 'selected-box', 'deferred-box')]
    reviewed = [w.StepV2(**steps[0].model_dump(), references=(selected,)),
                w.StepV2(**steps[1].model_dump(), references=(deferred,))]
    saved = w.save('world-one', cid, source.turn_id, w.ReviewV3(expected_revision=1,
        objective='Discuss one box before drafting.', root_references=(root,), steps=reviewed))
    assert saved['schema'] == 'dmb_reviewed_work_plan_v3'
    assert w.read('world-one', cid, source.turn_id)['plan'] == saved
    result = w.continue_step('world-one', cid, source.turn_id,
        w.Continue(expected_revision=2, step_id=steps[0].step_id, command_id=uuid4()))
    dispatch = result['dispatch']
    assert [r['node_id'] for r in dispatch['authored_references']['references']] == ['root-box', 'selected-box']
    assert 'deferred-box' not in str(dispatch['authored_references'])
    later = w.save('world-one', cid, source.turn_id, w.ReviewV3(expected_revision=3,
        objective='A later outcome.', root_references=(), steps=reviewed))
    assert later['dispatches'] == [dispatch]
    with pytest.raises(ApplicationStateConflictError, match='exact reviewed step'):
        w.save('world-one', cid, source.turn_id, w.ReviewV3(expected_revision=4,
            objective='Do not rewrite the dispatch.', root_references=(),
            steps=[reviewed[0].model_copy(update={'references': ()}), reviewed[1]]))
    bound = w.resolve_action
    from application_state.unit_of_work import unit_of_work
    from application_state.agent_conversation.service import _ready_dsn
    from application_state.agent_conversation.reviewed_action import ReviewedStepReference, ReviewedStepBindingV2
    with unit_of_work(_ready_dsn()) as conn:
        binding = bound(conn, 'world-one', ReviewedStepReference.model_validate(result['reviewed_step']),
            document_id=before['document_id'], client_thread_id=dispatch['client_thread_id'],
            client_turn_id=dispatch['client_turn_id'], message=dispatch['message'])
    assert isinstance(binding, ReviewedStepBindingV2)
    assert [r.node_id for r in binding.authored_references.references] == ['root-box', 'selected-box']


def test_reference_upgrade_preserves_legacy_dispatch_binding(case):
    service, cid, source, steps, before = case
    result = w.continue_step('world-one', cid, source.turn_id,
        w.Continue(expected_revision=1, step_id=steps[0].step_id, command_id=uuid4()))
    from application_state.unit_of_work import unit_of_work
    from application_state.agent_conversation.service import _ready_dsn
    from application_state.agent_conversation.reviewed_action import ReviewedStepReference, ReviewedStepBindingV2
    dispatch = result['dispatch']
    ref = ReviewedStepReference.model_validate(result['reviewed_step'])
    def resolve():
        with unit_of_work(_ready_dsn()) as conn:
            return w.resolve_action(conn, 'world-one', ref, document_id=before['document_id'],
                client_thread_id=dispatch['client_thread_id'], client_turn_id=dispatch['client_turn_id'],
                message=dispatch['message'])
    original = resolve()
    assert not isinstance(original, ReviewedStepBindingV2)
    upgraded = w.save('world-one', cid, source.turn_id, w.ReviewV3(expected_revision=2,
        objective='Read the new reference only on future continuations.',
        root_references=(reference('later-box'),),
        steps=[w.StepV2(**s.model_dump(), references=()) for s in steps]))
    assert upgraded['dispatches'] == [dispatch]
    assert resolve().model_dump(mode='json') == original.model_dump(mode='json')
