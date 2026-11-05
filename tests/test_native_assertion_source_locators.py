"""Core byte admission plus the captured many-assertion APP storage shape."""
from uuid import uuid4
import json

import pytest
from pydantic import ValidationError
from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_plan_assertions import (
    NativePlanAssertionReadV1, NativePlanAssertionReadV2,
    NativePlanAssertionReadObservedV2, compact_assertion_read, selection_handle,
    model_frame_records,
)
from apps.live_control_server.services.native_graph_reads import read_selected
from tests import test_source_statements as source_fixture
from tests.test_native_plan_assertions import publish, query, grant, GM, lane as lane
from tests.application_state.test_native_plan_statements import native_read_admission_probes as native_read_admission_probes
from tests.test_surface_native_context import seal
from tests.test_surface_native_execution import component, execution, controller, decision_prefix, choice


@pytest.fixture
def core_read(application_state_dsn, tmp_path, monkeypatch):
    body = 'A reports that B fled; uncertain. 🌿 ' + 'Source-local details. ' * 420 + '\n'
    monkeypatch.setattr(source_fixture, 'BODY', body)
    lane = source_fixture.make_lane(tmp_path, monkeypatch, narrow=True)
    publish(lane, qualified=True)
    context, _ = query(lane)
    reads, missing = read_selected(context, grant(context), GM)
    assert not missing
    return next(r for r in reads if r.assertion.predicate == 'dnd5e:summary')


def test_complete_core_bytes_are_validated_before_only_the_copy_is_removed(core_read):
    compact = compact_assertion_read(core_read)
    assert type(compact) is NativePlanAssertionReadV2
    assert compact.assertion == core_read.assertion
    assert compact.evidence == core_read.evidence
    assert [s.model_dump() for s in compact.spans] == [s.model_dump(exclude={'text'}) for s in core_read.spans]
    assert 'text' not in type(compact.spans[0]).model_fields
    with pytest.raises(ValueError, match='complete native source materialization'):
        compact_assertion_read(compact)
    changed_span = core_read.spans[0].model_copy(update={'text': core_read.spans[0].text + 'changed'})
    changed = core_read.model_copy(update={'spans': (changed_span,)})
    with pytest.raises(ValidationError, match='span bytes differ'):
        compact_assertion_read(changed)
    # Historical records still decode with their exact text, without rewriting them.
    assert NativePlanAssertionReadV1.model_validate_json(core_read.model_dump_json()) == core_read


def test_many_shared_supports_fit_existing_ledger_without_changing_writer_facts(core_read):
    # Distinct synthetic catalog assertions sharing one actual Core-validated span.
    # This tests APP storage, not extraction accuracy or independent assessment.
    reads = tuple(core_read.model_copy(update={'assertion': core_read.assertion.model_copy(
        update={'assertion_id': f'asrt:{index:032x}'})}) for index in range(168))
    context, record = component('plan')
    data = context.model_dump(mode='json', by_alias=True)
    first = controller('plan', record.policy)
    data['assembled_input']['tokenizer_name'] = first.input_estimator
    subject = core_read.assertion.subject_entity_id
    data['native_query'].update(discovered_entity_ids=[subject], assertion_matches=[dict(
        assertion_id=r.assertion.assertion_id, subject_entity_id=subject,
        discovered_entity_ids=[subject], assertion_sha256=t.canonical_sha256(r.assertion),
        label='Selected assertion') for r in reads])
    context = type(context).model_validate_json(json.dumps(seal(data)))
    policy = record.policy.model_copy(update={'native_query_sha256': t.canonical_sha256(context.native_query)})
    record = execution(context.context_receipt_sha256, policy)
    prefix, active = decision_prefix('plan', context, record)
    prefix.append(choice(context, record, active, len(prefix), 'select_candidates',
        [selection_handle(context.native_query, match) for match in context.native_query.assertion_matches]))
    authorization = t.NativePlanAssertionReadAuthorizedV1(event_id=uuid4(), sequence=len(prefix),
        provider_attempt_id=active.provider_attempt_id, query_sha256=context.native_query.sha256,
        assertion_ids=tuple(r.assertion.assertion_id for r in reads))
    prefix.append(authorization)
    common = dict(event_id=uuid4(), sequence=len(prefix), authorization_event_id=authorization.event_id,
        unavailable_assertion_ids=(), status='complete')
    old = t.NativePlanAssertionReadObservedV1(**common, reads=reads)
    with pytest.raises(ValueError, match='ledger storage bound'):
        execution(context.context_receipt_sha256, policy, [*prefix, old])
    current = NativePlanAssertionReadObservedV2(**common, reads=tuple(compact_assertion_read(r) for r in reads))
    admitted = execution(context.context_receipt_sha256, policy, [*prefix, current])
    assert len(admitted.model_dump_json(by_alias=True).encode()) < 1_048_576
    previous = record.model_copy(update={'events': [*prefix, old]})
    assert model_frame_records(context.native_query, admitted, schema='dmb_native_assertion_frame_v2') == model_frame_records(
        context.native_query, previous, schema='dmb_native_assertion_frame_v2')
    assert len(model_frame_records(context.native_query, admitted)['assertions']) == 168


def test_current_citation_reopens_core_and_rejects_changed_locator_and_player(
        lane, tmp_path, monkeypatch, native_read_admission_probes):
    from types import SimpleNamespace
    from dataclasses import replace
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.authored_graph_references import BuildAuthoredReferenceReadV3
    from apps.live_control_server.services.native_statement_clause_reads import open_assertion_source
    from apps.live_control_server.services.agent_source_passages import SourcePassageOpenError
    from tests.test_native_plan_assertions import _ordinary_native_case
    seen = []
    original = AgentConversationService.inspect_turn
    def inspect(self, **kwargs):
        turn = original(self, **kwargs)
        seen.append(turn)
        return turn
    monkeypatch.setattr(AgentConversationService, 'inspect_turn', inspect)
    _ordinary_native_case(lane, tmp_path, monkeypatch, True, False, None, None, False,
        native_read_admission_probes, authored=True)
    turn = next(turn for turn in reversed(seen) if turn.status == 'completed')
    event = next(e for e in turn.graph_context_execution.events if type(e) is BuildAuthoredReferenceReadV3)
    selected_id = turn.completion.native_assertion_citations[0].assertion_id
    read = next(r for r in event.assertion_reads if r.assertion.assertion_id == selected_id)
    changed = read.model_copy(update={'spans': (read.spans[0].model_copy(update={'body_sha256': 'f' * 64}),)})
    altered = event.model_copy(update={'assertion_reads': tuple(
        changed if r.assertion.assertion_id == selected_id else r for r in event.assertion_reads)})
    execution = turn.graph_context_execution.model_copy(update={'events': [
        altered if item.event_id == event.event_id else item for item in turn.graph_context_execution.events]})
    forged = turn.model_copy(update={'graph_context_execution': execution})
    for stored, principal in [(forged, GM), (turn, replace(GM, role='player'))]:
        with pytest.raises(SourcePassageOpenError):
            open_assertion_source(world_id=turn.world_id, turn_id=turn.turn_id, citation_index=0,
                principal=principal, service=SimpleNamespace(inspect_turn=lambda **_: stored))
