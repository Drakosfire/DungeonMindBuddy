"""Plan Jev → direct Rules → finish → one native writer; actual APP, mock inference."""
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4
import pytest

from application_state.agent_conversation.plan_jev_rules_lookup import prepare_authorization
from application_state.agent_conversation.rules_authority_plan_packet import build_plan_rules_frame
from application_state.agent_conversation.rules_authority_types import canonical_bytes
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services import rules_lookup_broker as broker
from tests.test_rules_lookup_broker import args
from tests.application_state.test_plan_jev_decision_admission import prepare_case, append, rules_scope
from tests.application_state.test_plan_rules_packet_admission import (
    graph_authorize, graph_finish, authorization, inclusion, append as append_rules,
)


def digest(raw): return sha256(raw.encode()).hexdigest()


def admitted_lookup(dsn):
    case = prepare_case(dsn, question=args().question); append(case)
    case.scope = rules_scope(case)
    case.record = case.service.begin_rules_execution(case.scope, expected_turn_revision=case.turn.revision)
    parent = case.proof["parent_request_json"]
    auth = prepare_authorization(case.record.execution, case.turn, parent)
    case.record = case.service.authorize_plan_jev_rules_lookup(case.scope,
        expected_turn_revision=case.turn.revision, expected_ledger_revision=case.record.revision,
        event=auth, parent_request_json=parent)
    return case, auth, parent


@pytest.mark.parametrize("mutation", ["question", "parent", "controller", "decision", "generic"])
def test_forged_rules_carrier_cannot_read(application_state_dsn, mutation):
    case = prepare_case(application_state_dsn, question=args().question); append(case)
    scope = rules_scope(case)
    record = case.service.begin_rules_execution(scope, expected_turn_revision=case.turn.revision)
    parent = case.proof["parent_request_json"]
    auth = prepare_authorization(record.execution, case.turn, parent)
    if mutation == "question": auth = auth.model_copy(update={"normalized_question": "foreign question"})
    elif mutation == "parent": parent = case.host.model_copy(update={"question": "foreign"}).model_dump_json(by_alias=True)
    elif mutation == "controller": auth = auth.model_copy(update={"origin_provider_attempt_id": uuid4()})
    elif mutation == "decision": auth = auth.model_copy(update={"decision_event_id": uuid4()})
    else: auth = broker.prepare_authorization(record.execution, "native:fake", args())
    with pytest.raises(ApplicationStateValidationError):
        if mutation == "generic":
            case.service.authorize_rules_lookup(scope, expected_turn_revision=case.turn.revision,
                expected_ledger_revision=record.revision, event=auth)
        else:
            case.service.authorize_plan_jev_rules_lookup(scope, expected_turn_revision=case.turn.revision,
                expected_ledger_revision=record.revision, event=auth, parent_request_json=parent)


def test_direct_rules_replays_after_finish_without_new_reads(application_state_dsn):
    case, auth, parent = admitted_lookup(application_state_dsn)
    calls = []
    def read(current):
        calls.append(auth.call_id)
        return broker.prepare_plan_lookup(current, auth.call_id, case.turn.user_text)
    delivery = case.service.execute_rules_lookup(case.scope, expected_turn_revision=case.turn.revision,
        call_id=auth.call_id, local_reader=read)
    assert delivery.prepared.observation.status == "evidence"
    case.record = delivery.record
    # A second completed actual GE/SDK decision ends acquisition.
    case.redecide("finish_retrieval"); append(case)
    replay_auth = case.service.authorize_plan_jev_rules_lookup(case.scope, expected_turn_revision=case.turn.revision,
        expected_ledger_revision=case.record.revision, event=auth, parent_request_json=parent)
    replay = case.service.execute_rules_lookup(case.scope, expected_turn_revision=case.turn.revision,
        call_id=auth.call_id, local_reader=lambda _: pytest.fail("finished replay must not read"))
    assert replay_auth == case.record and replay.replayed and len(calls) == 1
    assert len(case.sent) == 2 and replay.prepared.raw_output == delivery.prepared.raw_output


def test_complete_jev_rules_native_answer_accepts_atomically(application_state_dsn):
    from application_state.agent_conversation.rules_authority_events import RulesNativeProviderOutcomeV1
    from application_state.agent_conversation.rules_authority_output import parse_answer
    from application_state.agent_conversation.native_rules_output import NativeRulesOutputProofV1
    from application_state.agent_conversation.rules_authority_completion import NativeRulesMixedTurnResultV1
    case, lookup, _ = admitted_lookup(application_state_dsn)
    delivery = case.service.execute_rules_lookup(case.scope, expected_turn_revision=case.turn.revision,
        call_id=lookup.call_id, local_reader=lambda current: broker.prepare_plan_lookup(current, lookup.call_id, case.turn.user_text))
    case.record, case.packet = delivery.record, delivery.prepared
    case.redecide("finish_retrieval"); append(case)
    frame = build_plan_rules_frame(case.record.execution, (lookup.call_id,))
    case.raw = json.dumps({"model": "synthetic-model", "tools": [], "input": [
        {"role": "user", "content": canonical_bytes(frame).decode()}]}, ensure_ascii=False)
    case.producer = uuid4(); graph_authorize(case, case.producer, digest(case.raw))
    auth = authorization(case)
    auth = type(auth).model_validate_json(json.dumps(auth.model_dump(mode="json", by_alias=True) | {"matched_outputs": [
        {"call_id": lookup.call_id, "packet_sha256": case.packet.observation.packet_sha256}]}))
    append_rules(case, auth, case.raw); append_rules(case, inclusion(case, auth), case.raw)
    graph_finish(case, case.producer)
    ref = case.packet.observation.support_refs[0]
    text = case.record.execution.supports[ref.support_id].support.excerpt_text
    raw = json.dumps({"schema": "dmb_rules_mixed_answer_v1", "base_output": None,
        "rules_segments": [{"kind": "rules_claim", "text": text, "support_ids": [str(ref.support_id)]}],
        "ordered_refs": [{"domain": "rules", "segment_index": 0}]}, ensure_ascii=False)
    capture = SimpleNamespace(authorization_id="synthetic-plan-jev-rules", api_request_id="synthetic-final-writer",
        provider="test-provider", model="synthetic-model", api_mode="codex_responses", request_sha256=digest(case.raw),
        status="answered", finish_reason="stop", text=raw, text_sha256=digest(raw), text_utf8_bytes=len(raw.encode()), tool_calls=())
    append_rules(case, RulesNativeProviderOutcomeV1.from_capture(capture, event_id=uuid4(), sequence=len(case.record.execution.events),
        execution_id=case.scope.execution_id, provider_attempt_id=case.producer, request_envelope_sha256=digest(case.raw)))
    composition = parse_answer(raw).composition(supplied_refs=(ref,), base_segments=(), base_disposition="unclaimed")
    result = NativeRulesMixedTurnResultV1(schema="dmb_native_rules_mixed_turn_result_v1", scope=case.scope,
        expected_turn_revision=case.turn.revision, expected_rules_revision=case.record.revision,
        assistant_text=composition.render(()), composition=composition, producing_provider_attempt_id=case.producer, base_result=None,
        output_proof=NativeRulesOutputProofV1.from_capture(capture, prepared_request_json=case.raw,
            rules_execution_id=case.scope.execution_id, producing_provider_attempt_id=case.producer))
    completed = case.service.complete_mixed_turn(result)
    assert completed.assistant_text == text
    assert case.service.complete_mixed_turn(result) == completed


def test_long_plan_question_uses_only_scoped_plan_reader_without_clipping(application_state_dsn, monkeypatch):
    question = ("Full table context. " * 90) + args().question
    case = prepare_case(application_state_dsn, question=question); append(case)
    scope = rules_scope(case)
    record = case.service.begin_rules_execution(scope, expected_turn_revision=case.turn.revision)
    parent = case.proof["parent_request_json"]
    auth = prepare_authorization(record.execution, case.turn, parent)
    record = case.service.authorize_plan_jev_rules_lookup(scope, expected_turn_revision=case.turn.revision,
        expected_ledger_revision=record.revision, event=auth, parent_request_json=parent)
    actual = broker.reader.query_plan_rules
    received = []
    def read(corpus, raw):
        received.append(raw)
        return actual(corpus, raw)
    monkeypatch.setattr(broker.reader, "query_plan_rules", read)
    delivered = case.service.execute_rules_lookup(scope, expected_turn_revision=case.turn.revision,
        call_id=auth.call_id, local_reader=lambda current: broker.prepare_plan_lookup(current, auth.call_id, question))
    assert received == [question] and len(question) > 800
    assert delivered.prepared.observation.status == "evidence"
    # The unrelated HTTP/native-tool service contract was not broadened.
    with pytest.raises(ValueError): broker.reader.query_rules(scope.corpus_sha256, question)


def test_later_jev_decision_reuses_the_same_exact_rules_read(application_state_dsn):
    case, auth, _ = admitted_lookup(application_state_dsn)
    delivered = case.service.execute_rules_lookup(case.scope, expected_turn_revision=case.turn.revision,
        call_id=auth.call_id, local_reader=lambda current: broker.prepare_plan_lookup(current, auth.call_id, case.turn.user_text))
    case.record = delivered.record
    case.redecide("select_candidates"); append(case)
    repeated = prepare_authorization(case.record.execution, case.turn, case.proof["parent_request_json"])
    assert repeated == auth
    replay_auth = case.service.authorize_plan_jev_rules_lookup(case.scope, expected_turn_revision=case.turn.revision,
        expected_ledger_revision=case.record.revision, event=repeated, parent_request_json=case.proof["parent_request_json"])
    replay = case.service.execute_rules_lookup(case.scope, expected_turn_revision=case.turn.revision,
        call_id=repeated.call_id, local_reader=lambda _: pytest.fail("later decision must reuse its exact earlier Rules read"))
    assert replay_auth == case.record and replay.replayed
    assert replay.record.execution.budget_use.calls == 1
    assert replay.prepared.raw_output == delivered.prepared.raw_output
