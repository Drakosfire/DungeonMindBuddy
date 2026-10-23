"""Native Play shares exact source selector rules without Graph claim promotion."""

from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_answer_output import (
    normalize_native_answer,
)
from application_state.agent_conversation.surface_source_answer import (
    passage_handle,
    producing_passages,
)
from tests.test_play_graph_context import fixture
from tests.test_play_graph_authority import native_provider, native_events
from tests.test_play_graph_completion import acknowledge
from tests.test_settled_source_read_accounting import (
    authorization,
    receipt as source_done,
)
from tests.test_native_answer_output import owner_turn


def case():
    receipt, execution, _frame = fixture()
    initial = native_provider(0)
    execution = native_events(execution, [initial])
    execution = acknowledge(execution, initial)
    auth = authorization(execution, len(execution.events), count=1)
    done = source_done(auth, len(execution.events) + 1)
    text = "The bridge keeper lights three copper lanterns at the eastern post."
    read = done.receipts[0].model_copy(
        update={
            "content_sha256": sha256(text.encode()).hexdigest(),
            "returned_chars": len(text),
            "line_start": 5,
            "line_end": 5,
        }
    )
    done = done.model_copy(update={"receipts": [read]})
    execution = native_events(execution, [*execution.events, auth, done])
    payload = {
        "schema": "dmb_world_graph_source_anchor_read_v1",
        "anchorId": read.anchor_id,
        "passageHandle": passage_handle(read),
        "sourceName": "Reedbridge notes",
        "content": text,
        "lineStart": 5,
        "lineEnd": 5,
        "outcome": "enough",
    }
    body = {
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "read-one",
                        "type": "function",
                        "function": {"name": "read_graph_source", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "read-one",
                "content": json.dumps(payload),
            },
        ]
    }
    raw = json.dumps(body)
    provider = native_provider(len(execution.events)).model_copy(
        update={
            "envelope_sha256": sha256(raw.encode()).hexdigest(),
            "included_source_read_event_ids": [done.event_id],
            "included_evidence_ref_ids": [read.evidence_ref_id],
        }
    )
    execution = native_events(execution, [*execution.events, provider])
    execution = acknowledge(execution, provider)
    turn = owner_turn(receipt, execution)
    passages, partial = producing_passages(turn, provider, raw)
    support = SimpleNamespace(
        provider_attempt_id=provider.provider_attempt_id,
        envelope_sha256=provider.envelope_sha256,
        context_receipt_sha256=receipt.context_receipt_sha256,
        graph_revision=receipt.graph_authority.graph_revision,
        closures=(),
        passages=passages,
        source_partial=partial,
    )
    answer = {
        "schema": "dmb_surface_source_answer_v1",
        "answer_context_status": "source_grounded",
        "answer_segments": [
            {
                "kind": "source_passage_claim",
                "text": "Reedbridge notes describe three copper lanterns.",
                "passage_handles": [passage_handle(read)],
            }
        ],
    }
    return turn, provider, raw, support, answer


def test_play_source_claim_uses_exact_producing_receipt_and_roundtrips():
    turn, provider, _raw, support, answer = case()
    completion, bindings, text = normalize_native_answer(
        answer, turn, provider.provider_attempt_id, support=support
    )
    assert (
        completion.surface_id == "play"
        and completion.citation_map is None
        and bindings == {}
    )
    assert completion.source_citations[0].source_name == "Reedbridge notes"
    assert completion.source_citations[0].receipt.line_start == 5
    binding = t.CompletionBindingEventV1(
        kind="completion_binding",
        event_id=uuid4(),
        sequence=len(turn.graph_context_execution.events),
        provider_attempt_id=provider.provider_attempt_id,
        completion_sha256=t.canonical_sha256(completion),
        claim_graph_event_ids={},
    )
    execution = native_events(
        turn.graph_context_execution, [*turn.graph_context_execution.events, binding]
    )
    stored = turn.model_dump(mode="json", by_alias=True) | {
        "status": "completed",
        "completed_at": turn.accepted_at.isoformat(),
        "claim_expires_at": None,
        "assistant_text": text,
        "completion": completion.model_dump(mode="json", by_alias=True),
        "graph_context_execution": execution.model_dump(mode="json", by_alias=True),
    }
    reopened = t.Turn.model_validate_json(json.dumps(stored))
    assert reopened.completion == completion


@pytest.mark.parametrize(
    "change",
    [
        "content",
        "line",
        "handle",
        "omitted_read",
        "source_revision",
        "truncated",
        "failed",
        "envelope",
    ],
)
def test_play_source_claim_cannot_use_changed_or_unincluded_read(change):
    turn, provider, raw, _support, _answer = case()
    body = json.loads(raw)
    row = json.loads(body["messages"][1]["content"])
    if change in {"content", "line", "handle"}:
        row[
            {"content": "content", "line": "lineStart", "handle": "passageHandle"}[
                change
            ]
        ] = "changed" if change != "line" else 6
        body["messages"][1]["content"] = json.dumps(row)
        raw = json.dumps(body)
        provider = provider.model_copy(
            update={"envelope_sha256": sha256(raw.encode()).hexdigest()}
        )
    elif change == "omitted_read":
        provider = provider.model_copy(update={"included_source_read_event_ids": []})
    elif change == "envelope":
        raw += " "
    else:
        events = list(turn.graph_context_execution.events)
        index = next(
            i
            for i, e in enumerate(events)
            if isinstance(e, t.ValidatedSourceReadEventV2)
        )
        event = events[index]
        read = event.receipts[0]
        delta = (
            {"source_revision_id": "other"}
            if change == "source_revision"
            else {"truncated": True}
            if change == "truncated"
            else {"outcome": "partial"}
        )
        events[index] = event.model_copy(
            update={"receipts": [read.model_copy(update=delta)]}
        )
        turn = turn.model_copy(
            update={
                "graph_context_execution": turn.graph_context_execution.model_copy(
                    update={"events": events}
                )
            }
        )
    with pytest.raises(ValueError):
        producing_passages(turn, provider, raw)


@pytest.mark.parametrize('with_quote',[False,True])
@pytest.mark.parametrize('historical_policy',[None,'v1','v2'])
def test_play_source_answer_persists_through_native_output_owner(application_state_dsn,with_quote,historical_policy,*,typed_gap=False):
    """Real APP accept/read/input/output/reopen; synthetic provider, no SQL forging."""
    from tests.application_state.test_native_play_input_postgres import (
        prepared_native,
        append,
    )
    from tests.application_state.test_plan_jev_decision_admission import rules_scope
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.native_rules_output import (
        NativeRulesOutputProofV1,
        normalize_unused_native_output,
    )
    from application_state.agent_conversation.rules_authority_events import (
        RulesProviderAuthorizedV1,
        RulesProviderIncludedV1,
        RulesNativeProviderOutcomeV1,
    )

    service, sub, turn, initial, raw = prepared_native(application_state_dsn)
    turn, _ = append(service, sub, turn, initial, raw)

    def outcome(turn, provider):
        for value in ("sdk_entered", "response_received"):
            turn, _ = service.record_provider_outcome(
                turn.world_id,
                turn.conversation_id,
                turn.turn_id,
                expected_revision=turn.revision,
                expected_attempt=turn.attempt,
                outcome=t.ProviderOutcomeEventV1(
                    kind="provider_outcome",
                    event_id=uuid4(),
                    sequence=len(turn.graph_context_execution.events),
                    provider_attempt_id=provider.provider_attempt_id,
                    outcome=value,
                ),
            )
        return turn

    turn = outcome(turn, initial)
    auth = authorization(
        turn.graph_context_execution, len(turn.graph_context_execution.events), count=1
    )
    turn, _ = service.authorize_source_read(
        turn.world_id,
        turn.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        authorization=auth,
    )
    text = "The bridge keeper lights three copper lanterns at the eastern post."
    done = source_done(auth, len(turn.graph_context_execution.events))
    read = done.receipts[0].model_copy(
        update={
            "content_sha256": sha256(text.encode()).hexdigest(),
            "returned_chars": len(text),
            "line_start": 5,
            "line_end": 5,
        }
    )
    done = done.model_copy(update={"receipts": [read]})
    turn, _ = service.record_validated_source_read(
        turn.world_id,
        turn.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        receipt=done,
    )
    payload = dict(
        schema="dmb_world_graph_source_anchor_read_v1",
        anchorId=read.anchor_id,
        passageHandle=passage_handle(read),
        sourceName="Reedbridge notes",
        content=text,
        lineStart=5,
        lineEnd=5,
        outcome="enough",
    )
    body = json.loads(raw)
    current_carrier = json.loads(body['messages'][0]['content'])
    if historical_policy:
        from application_state.agent_conversation.play_graph_input import NativePlayInputV2,unpack_play_frame
        if historical_policy == 'v1':
            old = NativePlayInputV2(submission_id=uuid4(),message='An earlier scene question.',
                source_frame=unpack_play_frame(current_carrier['source_frame']))
            historical = old.model_dump(mode='json',by_alias=True)
        else:
            historical = current_carrier | {'submission_id':str(uuid4()),'message':'An earlier scene question.'}
        body['messages'].insert(0,dict(role='user',content=json.dumps(historical)))
    body["messages"].extend(
        [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "read-one",
                        "type": "function",
                        "function": {"name": "read_graph_source", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "read-one",
                "content": json.dumps(payload),
            },
        ]
    )
    raw = json.dumps(body)
    producer = native_provider(len(turn.graph_context_execution.events) + 1).model_copy(
        update={
            "envelope_sha256": sha256(raw.encode()).hexdigest(),
            "api_mode": "chat_completions",
            "included_source_read_event_ids": [done.event_id],
            "included_evidence_ref_ids": [read.evidence_ref_id],
        }
    )
    turn, _ = append(service, sub, turn, producer, raw)
    scope = rules_scope(SimpleNamespace(turn=turn))
    ledger = service.begin_rules_execution(scope, expected_turn_revision=turn.revision)
    for cls, kind in (
        (RulesProviderAuthorizedV1, "provider_authorized"),
        (RulesProviderIncludedV1, "provider_included"),
    ):
        fields = dict(
            kind=kind,
            event_id=uuid4(),
            sequence=len(ledger.execution.events),
            execution_id=scope.execution_id,
            provider_attempt_id=producer.provider_attempt_id,
            request_envelope_sha256=producer.envelope_sha256,
            matched_outputs=(),
        )
        fields[
            "declared_support_refs"
            if cls is RulesProviderAuthorizedV1
            else "support_refs"
        ] = ()
        ledger = service.append_rules_provider_event(
            scope,
            expected_turn_revision=turn.revision,
            expected_ledger_revision=ledger.revision,
            event=cls(**fields),
            prepared_request_json=raw,
        )
    turn = outcome(turn, producer)
    output = json.dumps(
        dict(
            schema="dmb_surface_evidence_answer_v2",
            limitations=[], requested_detail_gaps=[],
            answer_segments=[
                dict(
                    kind="source_passage_claim",
                    text="Reedbridge notes describe three copper lanterns.",
                    passage_handles=[passage_handle(read)],
                )
            ],
        )
    )
    if typed_gap:
        payload=json.loads(output)
        payload['requested_detail_gaps']=[{'question_phrase':turn.user_text}]
        output=json.dumps(payload)
    if with_quote:
        frame=current_carrier['source_frame']
        payload=json.loads(output)
        payload['answer_segments'].append(dict(kind='authored_excerpt',block_handle=frame['sources'][0]['text_blocks'][0]['block_handle']))
        output=json.dumps(payload)
    capture = SimpleNamespace(
        authorization_id="synthetic-native",
        api_request_id="synthetic-answer",
        provider=producer.provider,
        model=producer.model,
        api_mode=producer.api_mode,
        request_sha256=producer.envelope_sha256,
        status="answered",
        finish_reason="stop",
        text=output,
        text_sha256=sha256(output.encode()).hexdigest(),
        text_utf8_bytes=len(output.encode()),
        tool_calls=(),
    )
    ledger = service.append_rules_provider_event(
        scope,
        expected_turn_revision=turn.revision,
        expected_ledger_revision=ledger.revision,
        event=RulesNativeProviderOutcomeV1.from_capture(
            capture,
            event_id=uuid4(),
            sequence=len(ledger.execution.events),
            execution_id=scope.execution_id,
            provider_attempt_id=producer.provider_attempt_id,
            request_envelope_sha256=producer.envelope_sha256,
        ),
    )
    proof = NativeRulesOutputProofV1.from_capture(
        capture,
        prepared_request_json=raw,
        rules_execution_id=scope.execution_id,
        producing_provider_attempt_id=producer.provider_attempt_id,
    )
    completion, bindings, answer_text = normalize_unused_native_output(
        turn, ledger.execution, proof
    )
    result = t.TurnResult(
        world_id=turn.world_id,
        conversation_id=turn.conversation_id,
        turn_id=turn.turn_id,
        expected_revision=turn.revision,
        assistant_text=answer_text,
        completion=completion,
        producing_provider_attempt_id=producer.provider_attempt_id,
        claim_graph_event_ids=bindings,
    )
    completed = service.complete_native_base_turn(
        result, output_proof=proof, expected_rules_revision=ledger.revision
    )
    reopened = AgentConversationService().inspect_turn(
        world_id=turn.world_id, turn_id=turn.turn_id
    )
    assert reopened == completed and reopened.completion.surface_id == "play"
    assert reopened.completion.source_citations[0].source_name == "Reedbridge notes"
    if typed_gap:
        assert sum(getattr(s, "code", None) == "missing_requested_details"
                   for s in reopened.completion.answer_segments) == 2
    assert (
        service.complete_native_base_turn(
            result, output_proof=proof, expected_rules_revision=ledger.revision
        )
        == completed
    )


def test_current_plan_and_play_source_instructions_share_host_attribution():
    from application_state.agent_conversation.surface_source_answer import (
        INSTRUCTIONS, SOURCE_ATTRIBUTION_INSTRUCTIONS,
    )
    from apps.live_control_server.services.agent_turn_service import (
        _PLAN_GRAPH_ANSWER_INSTRUCTIONS,
    )
    assert SOURCE_ATTRIBUTION_INSTRUCTIONS in INSTRUCTIONS
    assert SOURCE_ATTRIBUTION_INSTRUCTIONS in _PLAN_GRAPH_ANSWER_INSTRUCTIONS
    assert "Use source names in prose" not in INSTRUCTIONS
    for current in (INSTRUCTIONS, _PLAN_GRAPH_ANSWER_INSTRUCTIONS):
        assert current.count("Ground each factual clause in that claim's own admitted evidence.") == 1
        assert "Do not turn a request," in current
        assert "select its authored_excerpt instead" in current


def test_play_typed_gap_derives_flag_through_native_owner(application_state_dsn):
    test_play_source_answer_persists_through_native_output_owner(
        application_state_dsn, False, None, typed_gap=True)
