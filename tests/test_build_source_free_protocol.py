"""Stored pending Build codec boundary; no database, providers or source grants."""
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import types as t
from application_state.agent_conversation import repository
from application_state.errors import ApplicationStateIntegrityError
from tests.test_build_source_free_routing import (
    pending_execution_pair, pending_execution, seal_pending_receipt,
)
from tests.test_surface_native_context import provenance_for
from tests.test_surface_native_turn_records import retained, stored_row, submission


def pending_submission():
    receipt, policy = pending_execution_pair()
    intent = policy.action.intent
    provenance = provenance_for(receipt.work_context).model_copy(
        update={'surface_instance_id': intent.surface_instance_id})
    data = receipt.model_dump(mode='json', by_alias=True)
    data.pop('context_receipt_sha256')
    receipt = seal_pending_receipt(data | {'provenance_sha256': t.canonical_sha256(provenance)})
    execution = pending_execution(receipt, policy)
    return t.TurnSubmission(world_id=intent.world_id, conversation_id=uuid4(),
        idempotency_key=uuid4(), expected_conversation_revision=1,
        user_text=intent.message, provenance=provenance, submitted_intent_v2=intent,
        graph_context_receipt=receipt, graph_context_execution=execution)


def test_pending_submission_and_actual_stored_row_roundtrip_without_core():
    sub = pending_submission()
    assert t.TurnSubmission.model_validate_json(sub.model_dump_json(by_alias=True)) == sub
    turn = retained(sub)
    row, references = stored_row(turn)
    restored = repository._turn_from_row(None, row, references=references)
    assert restored == turn
    assert restored.graph_context_receipt.source_observation.binding is None
    assert not hasattr(restored.graph_context_receipt, 'source_authority')
    assert restored.graph_context_execution.schema_ == 'dmb_build_pending_execution_v1'


@pytest.mark.parametrize('side', ['receipt', 'execution'])
def test_stored_pending_and_legacy_components_cannot_be_crossed(side):
    pending = retained(pending_submission())
    legacy = retained(submission('build'))
    row, references = stored_row(pending)
    old_row, _ = stored_row(legacy)
    key = 'graph_context_' + side
    row[key] = old_row[key]
    with pytest.raises((ApplicationStateIntegrityError, ValidationError, ValueError)):
        repository._turn_from_row(None, row, references=references)


def test_pending_typed_turn_reconstruction_cannot_retain_a_mutated_observation():
    turn = retained(pending_submission())
    observed = turn.graph_context_receipt.source_observation.model_copy(
        update={'requested_revision_id': 'different-request'})
    receipt = turn.graph_context_receipt.model_copy(update={'source_observation': observed})
    with pytest.raises(ValidationError):
        t.Turn.model_validate(turn.model_copy(update={'graph_context_receipt': receipt}))


@pytest.mark.parametrize('field,value', [
    ('user_text', 'Changed request'), ('world_id', 'other-world'),
    ('submitted_intent_fingerprint_v2', 'f' * 64),
])
def test_stored_pending_request_identity_cannot_be_substituted(field, value):
    turn = retained(pending_submission())
    data = turn.model_dump(mode='json', by_alias=True) | {field: value}
    with pytest.raises(ValidationError):
        t.Turn.model_validate_json(json.dumps(data))


def test_pending_prefix_does_not_admit_unowned_terminal_prose():
    turn = retained(pending_submission())
    data = turn.model_dump(mode='json', by_alias=True) | {'assistant_text': 'Unowned answer'}
    with pytest.raises(ValidationError, match='registered terminal output owner'):
        t.Turn.model_validate_json(json.dumps(data))


@pytest.mark.parametrize('field,value', [
    ('assembled_input_sha256', 'f' * 64), ('provider_envelope_input_tokens', 121),
])
def test_pending_first_controller_cannot_replace_its_resealed_initial_envelope(field, value):
    from tests.test_build_source_free_routing import pending_work_prefix
    from application_state.agent_conversation.build_source_free import effective_pending_source
    receipt, policy = pending_execution_pair()
    data = receipt.model_dump(mode='json', by_alias=True)
    data.pop('context_receipt_sha256')
    data['assembled_input'][field] = value
    receipt = seal_pending_receipt(data)
    execution = pending_execution(receipt, policy, pending_work_prefix(policy, scope='anchored'))
    with pytest.raises(ValueError, match='first provider authorization must match'):
        effective_pending_source(receipt, execution)


def test_repository_pending_wire_decode_has_one_component_freshness_owner(monkeypatch):
    from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1
    from application_state.agent_conversation.native_execution import BuildPendingExecutionV1
    turn = retained(pending_submission())
    row, references = stored_row(turn)
    def duplicate_decode(*args, **kwargs):
        raise AssertionError('Stored pending component was independently decoded again')
    monkeypatch.setattr(BuildPendingContextReceiptV1, 'model_validate_json', duplicate_decode)
    monkeypatch.setattr(BuildPendingExecutionV1, 'model_validate_json', duplicate_decode)
    restored = repository._turn_from_row(None, row, references=references)
    assert restored.model_dump_json(by_alias=True) == turn.model_dump_json(by_alias=True)


@pytest.mark.parametrize('status,attempt', [('accepted', 0), ('running', 1)])
def test_stored_pending_live_turn_cannot_carry_a_completion_timestamp(status, attempt):
    turn = retained(pending_submission(), status=status, attempt=attempt)
    row, references = stored_row(turn)
    assert repository._turn_from_row(None, row, references=references) == turn
    data = turn.model_dump(mode='json', by_alias=True)
    data['completed_at'] = data['accepted_at']
    with pytest.raises(ValidationError, match='lifecycle'):
        t.Turn.model_validate_json(json.dumps(data))
    row['completed_at'] = turn.accepted_at
    with pytest.raises((ApplicationStateIntegrityError, ValidationError, ValueError)):
        repository._turn_from_row(None, row, references=references)
