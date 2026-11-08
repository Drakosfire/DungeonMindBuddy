"""Real claim/CAS and native acceptance for the Plan-only tool-free packet carrier.

Provider replies/lifecycles are synthetic; Rules packets use the actual local reader.
No inference or network calls are performed.
"""
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4
import psycopg
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.rules_authority_events import (
    RulesPlanPacketProviderAuthorizedV1, RulesPlanPacketProviderIncludedV1,
    RulesNativeProviderOutcomeV1, RulesProviderAuthorizedV1, RulesProviderIncludedV1, RulesProviderOutcomeV1,
)
from application_state.agent_conversation.rules_authority_policy import rules_capability, rules_submission_authorization_id
from application_state.agent_conversation.rules_authority_types import RulesScopeV1, canonical_bytes
from application_state.agent_conversation.rules_authority_plan_packet import build_plan_rules_frame, verify_plan_rules_packet_input
from application_state.agent_conversation.rules_authority_output import parse_answer
from application_state.agent_conversation.native_rules_output import NativeRulesOutputProofV1
from application_state.agent_conversation.rules_authority_completion import NativeRulesMixedTurnResultV1
from application_state.errors import ApplicationStateValidationError, ApplicationStateConflictError
from apps.live_control_server.services import rules_lookup_broker as broker
from tests.test_rules_lookup_broker import args
from tests.application_state.test_agent_conversation_postgres import _accepted_execution_turn, _provider_authorization_event


def digest(raw): return sha256(raw.encode()).hexdigest()


def graph_authorize(case, attempt, envelope):
    event = _provider_authorization_event(attempt_id=attempt, sequence=len(case.turn.graph_context_execution.events))
    event = t.ProviderAttemptAuthorizedEventV3.model_validate(event.model_dump(mode="json", by_alias=True) | {
        "kind": "provider_attempt_authorized_v3", "api_mode": "codex_responses",
        "envelope_sha256": envelope, "included_source_read_event_ids": []})
    case.turn, _ = case.service.authorize_provider_attempt(case.turn.world_id, case.turn.conversation_id,
        case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
        provider_attempt_event=event)


def graph_finish(case, attempt):
    for outcome in ("sdk_entered", "response_received"):
        case.turn, _ = case.service.record_provider_outcome(case.turn.world_id, case.turn.conversation_id,
            case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            outcome=t.ProviderOutcomeEventV1(kind="provider_outcome", event_id=uuid4(),
                sequence=len(case.turn.graph_context_execution.events), provider_attempt_id=attempt, outcome=outcome))


def prepared(dsn, *, build=False, with_writer=True, uncapped=False, semantic=False, two_supports=False):
    service = AgentConversationService()
    if build:
        from tests.application_state.test_build_graph_turns import _accept_claim
        _, turn = _accept_claim(service)
    else:
        _, _, _, turn = _accepted_execution_turn(service, "plan-packet-admission", execution_version=3, uncapped=uncapped)
    cap = rules_capability(graph=True)
    scope = RulesScopeV1(schema="dmb_rules_scope_v1", execution_id=uuid4(), world_id=turn.world_id,
        conversation_id=turn.conversation_id, turn_id=turn.turn_id, product_attempt=turn.attempt,
        ruleset_id=cap.ruleset_id, corpus_sha256=cap.corpus_sha256, capability_policy_sha256=cap.policy_sha256,
        authorization_id=rules_submission_authorization_id(world_id=turn.world_id, conversation_id=turn.conversation_id,
            idempotency_key=turn.idempotency_key, submitted_intent_sha256=turn.submitted_intent_fingerprint_v2, capability=cap),
        budget=cap.budget)
    record = service.begin_rules_execution(scope, expected_turn_revision=turn.revision)
    authorization = broker.prepare_authorization(record.execution, "rules:1", args())
    record = service.authorize_rules_lookup(scope, expected_turn_revision=turn.revision,
        expected_ledger_revision=record.revision, event=authorization)
    def local_reader(current):
        original = broker.prepare_lookup(current, "rules:1", args())
        if not two_supports:
            return original
        from application_state.agent_conversation.rules_authority_packet import RulesPacketV1
        from application_state.agent_conversation.rules_authority_types import RulesSupportRefV1, canonical_sha256
        first = original.new_supports[0]
        second = first.model_copy(update={"support_id": uuid4(), "source_uri": first.source_uri + "#second",
            "unit_id": digest(first.unit_id + ":second")})
        capsules = tuple(sorted((first, second), key=lambda row: str(row.support_id)))
        refs = tuple(RulesSupportRefV1(support_id=row.support_id, support_sha256=canonical_sha256(row)) for row in capsules)
        packet = RulesPacketV1.model_validate_json(original.raw_output).model_copy(update={
            "support_capsules": capsules, "support_refs": refs,
            "emitted_support_ids": tuple(row.support_id for row in capsules)})
        raw = canonical_bytes(packet).decode()
        return broker._prepared(current, authorization, raw, "evidence", refs, capsules, capsules)
    delivery = service.execute_rules_lookup(scope, expected_turn_revision=turn.revision, call_id="rules:1",
        local_reader=local_reader)
    frame = build_plan_rules_frame(delivery.record.execution, ("rules:1",))
    if semantic:
        from application_state.agent_conversation.rules_authority_plan_packet import model_rules_frame
        frame = model_rules_frame(frame)
    from tests.plan_writer_schema_fixture import with_plan_schema
    raw = json.dumps(with_plan_schema({"model": "synthetic-model", "tools": [], "input": [
        {"role": "user", "content": canonical_bytes(frame).decode()}]}, frame), ensure_ascii=False)
    case = SimpleNamespace(dsn=dsn, service=service, turn=turn, scope=scope, record=delivery.record,
        raw=raw, producer=uuid4(), packet=delivery.prepared)
    if not build:
        first = uuid4(); graph_authorize(case, first, "c" * 64); graph_finish(case, first)
        if with_writer: graph_authorize(case, case.producer, digest(raw))
    return case


def append(case, event, raw=None, **overrides):
    params = dict(expected_turn_revision=case.turn.revision, expected_ledger_revision=case.record.revision,
                  event=event, prepared_request_json=raw)
    case.record = case.service.append_rules_provider_event(case.scope, **(params | overrides))
    return case.record


def authorization(case):
    receipt = case.turn.graph_context_receipt
    return RulesPlanPacketProviderAuthorizedV1(kind="plan_packet_provider_authorized", event_id=uuid4(),
        sequence=len(case.record.execution.events), execution_id=case.scope.execution_id,
        provider_attempt_id=case.producer, request_envelope_sha256=digest(case.raw),
        plan_context_receipt_sha256=receipt.context_receipt_sha256,
        matched_outputs=({"call_id": "rules:1", "packet_sha256": case.packet.observation.packet_sha256},),
        declared_support_refs=case.packet.observation.support_refs)


def inclusion(case, auth):
    return RulesPlanPacketProviderIncludedV1(kind="plan_packet_provider_included", event_id=uuid4(),
        sequence=len(case.record.execution.events), execution_id=case.scope.execution_id,
        provider_attempt_id=auth.provider_attempt_id, request_envelope_sha256=auth.request_envelope_sha256,
        plan_context_receipt_sha256=auth.plan_context_receipt_sha256,
        matched_outputs=auth.matched_outputs, support_refs=auth.declared_support_refs)


def persisted(case):
    with psycopg.connect(case.dsn) as conn:
        return conn.execute("SELECT revision,payload FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s",
                            (case.turn.turn_id, case.scope.product_attempt)).fetchone()


def test_actual_plan_admission_replays_and_fences_further_reads(application_state_dsn):
    case = prepared(application_state_dsn); auth = authorization(case); before = case.record.revision
    new_auth = broker.prepare_authorization(case.record.execution, "rules:next", args("What about movement?"))
    first = append(case, auth, case.raw)
    assert append(case, auth, case.raw, expected_ledger_revision=before) == first
    append(case, inclusion(case, auth), case.raw)
    assert case.record.execution.budget_use.provider_requests == 1
    before = persisted(case)
    new_auth = new_auth.model_copy(update={"sequence": len(case.record.execution.events)})
    with pytest.raises(ApplicationStateValidationError):
        case.service.authorize_rules_lookup(case.scope, expected_turn_revision=case.turn.revision,
            expected_ledger_revision=case.record.revision, event=new_auth)
    assert persisted(case) == before
    later = authorization(case)
    with pytest.raises(ApplicationStateValidationError): append(case, later, case.raw)
    assert persisted(case) == before


@pytest.mark.parametrize("mutation", ["receipt", "request", "attempt", "supports", "late", "orphan", "build", "stale_claim"])
def test_wrong_or_late_plan_packet_cannot_append(application_state_dsn, mutation):
    case = prepared(application_state_dsn, build=mutation == "build", with_writer=mutation != "orphan")
    auth = authorization(case); raw = case.raw
    if mutation == "receipt": auth = auth.model_copy(update={"plan_context_receipt_sha256": "0" * 64})
    elif mutation == "request": raw += " "
    elif mutation == "attempt": auth = auth.model_copy(update={"provider_attempt_id": uuid4()})
    elif mutation == "supports": auth = auth.model_copy(update={"declared_support_refs": ()})
    elif mutation == "late": graph_finish(case, case.producer)
    snapshot = persisted(case)
    with pytest.raises((ApplicationStateValidationError, ApplicationStateConflictError)):
        append(case, auth, raw, **({"expected_turn_revision": case.turn.revision - 1} if mutation == "stale_claim" else {}))
    assert persisted(case) == snapshot


def test_final_packet_carrier_cannot_change_on_inclusion(application_state_dsn):
    case = prepared(application_state_dsn); auth = authorization(case); append(case, auth, case.raw)
    old = RulesProviderIncludedV1(kind="provider_included", event_id=uuid4(), sequence=len(case.record.execution.events),
        execution_id=case.scope.execution_id, provider_attempt_id=auth.provider_attempt_id,
        request_envelope_sha256=auth.request_envelope_sha256, matched_outputs=auth.matched_outputs,
        support_refs=auth.declared_support_refs)
    snapshot = persisted(case)
    with pytest.raises(ApplicationStateValidationError): append(case, old, case.raw)
    assert persisted(case) == snapshot


@pytest.mark.parametrize('historical_binding', [False, True])
def test_native_packet_writer_accepts_and_replays_atomically(application_state_dsn, historical_binding):
    case = prepared(application_state_dsn); auth = authorization(case); append(case, auth, case.raw)
    append(case, inclusion(case, auth), case.raw); graph_finish(case, case.producer)
    ref = case.packet.observation.support_refs[0]
    text = case.record.execution.supports[ref.support_id].support.excerpt_text
    raw_output = json.dumps({"schema": "dmb_rules_mixed_answer_v1", "base_output": None,
        "rules_segments": [{"kind": "rules_claim", "text": text, "support_ids": [str(ref.support_id)]}],
        "ordered_refs": [{"domain": "rules", "segment_index": 0}]}, ensure_ascii=False)
    capture = SimpleNamespace(authorization_id="synthetic-plan-packet", api_request_id="synthetic-plan-writer",
        provider="test-provider", model="synthetic-model", api_mode="codex_responses",
        request_sha256=digest(case.raw), status="answered", finish_reason="stop", text=raw_output,
        text_sha256=digest(raw_output), text_utf8_bytes=len(raw_output.encode()), tool_calls=())
    append(case, RulesNativeProviderOutcomeV1.from_capture(capture, event_id=uuid4(),
        sequence=len(case.record.execution.events), execution_id=case.scope.execution_id,
        provider_attempt_id=case.producer, request_envelope_sha256=digest(case.raw)))
    composition = parse_answer(raw_output).composition(base_completion=None, supplied_refs=(ref,), base_segments=(), base_disposition="unclaimed")
    result = NativeRulesMixedTurnResultV1(schema="dmb_native_rules_mixed_turn_result_v1", scope=case.scope,
        expected_turn_revision=case.turn.revision, expected_rules_revision=case.record.revision,
        assistant_text=composition.render(()), composition=composition, producing_provider_attempt_id=case.producer,
        base_result=None, output_proof=NativeRulesOutputProofV1.from_capture(capture,
            prepared_request_json=case.raw, rules_execution_id=case.scope.execution_id,
            producing_provider_attempt_id=case.producer))
    completed = case.service.complete_mixed_turn(result)
    assert completed.assistant_text == text and completed.accepted_binding.base_disposition == "unclaimed"
    assert case.service.complete_mixed_turn(result) == completed
    if historical_binding:
        from psycopg.types.json import Jsonb
        from application_state.agent_conversation.rules_authority_types import canonical_sha256
        binding = completed.accepted_binding.model_dump(mode='json', by_alias=True)
        del binding['producing_support_refs_sha256']
        binding['schema'] = 'dmb_rules_accepted_binding_v1'
        with psycopg.connect(case.dsn) as conn:
            conn.execute("UPDATE agent.turn_rules_execution SET accepted_binding=%s,accepted_binding_sha256=%s "
                "WHERE turn_id=%s AND product_attempt=%s", (Jsonb(binding), canonical_sha256(binding),
                    case.turn.turn_id, case.scope.product_attempt))
        historical = case.service.inspect_turn(world_id=case.turn.world_id, turn_id=case.turn.turn_id)
        assert historical.accepted_binding.schema_ == 'dmb_rules_accepted_binding_v1'
        assert historical.assistant_text == text
        assert case.service.complete_mixed_turn(result) == historical


@pytest.mark.parametrize("mutation", [None, "unused_hash", "unused_id", "duplicate_map", "missing_map",
    "binding_missing_map_digest", "binding_bad_map_digest", "reordered_map"])
def test_semantic_second_support_survives_reload_and_rejects_unused_map_tampering(application_state_dsn, mutation):
    from application_state.agent_conversation.rules_authority_output import parse_producing_answer
    from application_state.agent_conversation.rules_authority_types import RulesAcceptedBindingV2
    from application_state.agent_conversation.rules_authority_passages import RulesHistoricalPassageRequestV1
    from psycopg.types.json import Jsonb
    case = prepared(application_state_dsn, semantic=True, two_supports=True)
    auth = authorization(case); append(case, auth, case.raw)
    append(case, inclusion(case, auth), case.raw); graph_finish(case, case.producer)
    refs = tuple(sorted(case.packet.observation.support_refs, key=lambda row: str(row.support_id)))
    chosen = case.record.execution.supports[refs[1].support_id].support
    raw_output = json.dumps({"kind": "rules_answer", "base_output": None,
        "rules_segments": [{"kind": "rules_claim", "text": chosen.excerpt_text, "support_ids": ["rule_1"]}],
        "ordered_refs": [{"domain": "rules", "segment_index": 0}]}, ensure_ascii=False)
    capture = SimpleNamespace(authorization_id="semantic-rules", api_request_id="semantic-writer",
        provider="test-provider", model="synthetic-model", api_mode="codex_responses",
        request_sha256=digest(case.raw), status="answered", finish_reason="stop", text=raw_output,
        text_sha256=digest(raw_output), text_utf8_bytes=len(raw_output.encode()), tool_calls=())
    append(case, RulesNativeProviderOutcomeV1.from_capture(capture, event_id=uuid4(),
        sequence=len(case.record.execution.events), execution_id=case.scope.execution_id,
        provider_attempt_id=case.producer, request_envelope_sha256=digest(case.raw)))
    composition = parse_producing_answer(raw_output, case.raw, refs).composition(
        base_completion=None, supplied_refs=refs, base_segments=(), base_disposition="unclaimed")
    result = NativeRulesMixedTurnResultV1(schema="dmb_native_rules_mixed_turn_result_v1", scope=case.scope,
        expected_turn_revision=case.turn.revision, expected_rules_revision=case.record.revision,
        assistant_text=composition.render(()), composition=composition, producing_provider_attempt_id=case.producer,
        base_result=None, output_proof=NativeRulesOutputProofV1.from_capture(capture,
            prepared_request_json=case.raw, rules_execution_id=case.scope.execution_id,
            producing_provider_attempt_id=case.producer))
    completed = case.service.complete_mixed_turn(result)
    assert isinstance(completed.accepted_binding, RulesAcceptedBindingV2)
    assert [row.support_id for row in completed.accepted_binding.support_table] == [refs[1].support_id]
    assert result.output_proof.raw_output_sha256 == digest(raw_output)
    assert case.service.inspect_turn(world_id=case.turn.world_id, turn_id=case.turn.turn_id) == completed
    request = RulesHistoricalPassageRequestV1(world_id=case.turn.world_id,
        conversation_id=case.turn.conversation_id, turn_id=case.turn.turn_id, attempt=case.turn.attempt,
        support_id=refs[1].support_id, support_sha256=refs[1].support_sha256)
    assert case.service.inspect_rules_passage(request).support.source_uri == chosen.source_uri
    assert case.service.complete_mixed_turn(result) == completed
    if mutation is None:
        return
    if mutation.startswith('binding_'):
        binding = completed.accepted_binding.model_dump(mode='json', by_alias=True)
        if mutation == 'binding_missing_map_digest': del binding['producing_support_refs_sha256']
        else: binding['producing_support_refs_sha256'] = 'not-a-digest'
        with pytest.raises(psycopg.errors.CheckViolation):
            with psycopg.connect(case.dsn) as conn:
                conn.execute("UPDATE agent.turn_rules_execution SET accepted_binding=%s WHERE turn_id=%s AND product_attempt=%s",
                    (Jsonb(binding), case.turn.turn_id, case.scope.product_attempt))
        return
    with psycopg.connect(case.dsn) as conn:
        payload = conn.execute("SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s",
            (case.turn.turn_id, case.scope.product_attempt)).fetchone()[0]
        inc = next(row for row in payload['events'] if row['kind'] == 'plan_packet_provider_included')
        if mutation == 'unused_hash': inc['support_refs'][0]['support_sha256'] = '0' * 64
        elif mutation == 'unused_id': inc['support_refs'][0]['support_id'] = str(uuid4())
        elif mutation == 'duplicate_map': inc['support_refs'].append(dict(inc['support_refs'][0]))
        elif mutation == 'reordered_map': inc['support_refs'].reverse()
        else: inc['support_refs'] = None
        conn.execute("UPDATE agent.turn_rules_execution SET payload=%s WHERE turn_id=%s AND product_attempt=%s",
            (Jsonb(payload), case.turn.turn_id, case.scope.product_attempt))
    if mutation == 'reordered_map':
        assert case.service.complete_mixed_turn(result) == completed
        return
    with pytest.raises(ApplicationStateValidationError):
        case.service.complete_mixed_turn(result)


def test_unknown_prior_rules_outcome_prevents_final_writer_admission(application_state_dsn):
    case = prepared(application_state_dsn)
    prior_attempt = uuid4(); raw = json.dumps({"input": []})
    old = RulesProviderAuthorizedV1(kind="provider_authorized", event_id=uuid4(),
        sequence=len(case.record.execution.events), execution_id=case.scope.execution_id,
        provider_attempt_id=prior_attempt, request_envelope_sha256=digest(raw),
        matched_outputs=(), declared_support_refs=())
    append(case, old, raw)
    append(case, RulesProviderIncludedV1(kind="provider_included", event_id=uuid4(),
        sequence=len(case.record.execution.events), execution_id=case.scope.execution_id,
        provider_attempt_id=prior_attempt, request_envelope_sha256=digest(raw), matched_outputs=(), support_refs=()), raw)
    append(case, RulesProviderOutcomeV1(kind="provider_outcome", event_id=uuid4(),
        sequence=len(case.record.execution.events), execution_id=case.scope.execution_id,
        provider_attempt_id=prior_attempt, request_envelope_sha256=digest(raw), status="unknown"))
    snapshot = persisted(case)
    with pytest.raises(ApplicationStateValidationError): append(case, authorization(case), case.raw)
    assert persisted(case) == snapshot


def test_metadata_only_answered_status_cannot_seal_plan_packet_writer(application_state_dsn):
    case = prepared(application_state_dsn); auth = authorization(case); append(case, auth, case.raw)
    append(case, inclusion(case, auth), case.raw)
    snapshot = persisted(case)
    event = RulesProviderOutcomeV1(kind="provider_outcome", event_id=uuid4(),
        sequence=len(case.record.execution.events), execution_id=case.scope.execution_id,
        provider_attempt_id=case.producer, request_envelope_sha256=digest(case.raw), status="answered")
    with pytest.raises(ApplicationStateValidationError): append(case, event)
    assert persisted(case) == snapshot


def test_final_writer_fences_graph_provider_even_without_budget_cap(application_state_dsn):
    case = prepared(application_state_dsn, uncapped=True)
    writer_auth = case.turn.graph_context_execution.events[-1]
    auth = authorization(case); append(case, auth, case.raw)
    append(case, inclusion(case, auth), case.raw)
    replay, fresh = case.service.authorize_provider_attempt(case.turn.world_id, case.turn.conversation_id,
        case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
        provider_attempt_event=writer_auth)
    assert not fresh and replay == case.turn
    graph_finish(case, case.producer)
    with psycopg.connect(case.dsn) as conn:
        before = conn.execute("SELECT revision,graph_context_execution FROM agent.turn WHERE turn_id=%s", (case.turn.turn_id,)).fetchone()
    with pytest.raises(ApplicationStateValidationError, match="final writer"):
        graph_authorize(case, uuid4(), "d" * 64)
    with psycopg.connect(case.dsn) as conn:
        assert conn.execute("SELECT revision,graph_context_execution FROM agent.turn WHERE turn_id=%s", (case.turn.turn_id,)).fetchone() == before
