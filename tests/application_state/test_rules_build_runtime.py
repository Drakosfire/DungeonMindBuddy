"""Real APP typed Rules persistence; Graph parent carrier admission is separate."""
import json
from uuid import uuid4
from datetime import UTC, datetime

import psycopg
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_policy import rules_capability, rules_submission_authorization_id
from application_state.agent_conversation.rules_authority_types import RulesScopeV1, AnswerCompositionV1, OrderedAnswerRefV1, RulesClaimV1
from application_state.agent_conversation.rules_authority_completion import MixedTurnResultV1, BuildRulesMixedTurnResultV1
from application_state.agent_conversation.rules_authority_output import (
    POLICY, BuildRulesOutputProofV1, build_output_format, parse_answer,
)
from application_state.agent_conversation.context_trace import TraceContextSnapshot
from tests.test_rules_authority_output import packet as output_packet, raw_answer
from application_state.agent_conversation.rules_authority_events import RulesBuildProviderIncludedV1, RulesProviderOutcomeV1
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services import rules_lookup_broker as broker
from tests.application_state.test_rules_authority_store import admitted
from tests.test_rules_build_input import prepared_provider, hashed
from tests.test_rules_lookup_broker import args


def ready():
    turn, original = admitted()
    cap = rules_capability(graph=True)
    fields = original.model_dump(mode="json", by_alias=True)
    fields.update(ruleset_id=cap.ruleset_id, corpus_sha256=cap.corpus_sha256, capability_policy_sha256=cap.policy_sha256,
        authorization_id=str(rules_submission_authorization_id(world_id=turn.world_id,
            conversation_id=turn.conversation_id, idempotency_key=turn.idempotency_key,
            submitted_intent_sha256=turn.submitted_intent_fingerprint_v2 or turn.submitted_intent_fingerprint_v1,
            capability=cap)))
    scope = RulesScopeV1.model_validate_json(json.dumps(fields))
    service = AgentConversationService()
    return service, turn, scope, service.begin_rules_execution(scope, expected_turn_revision=turn.revision)


def persist_provider(service, turn, scope, record, event, raw):
    record = service.append_rules_provider_event(scope, expected_turn_revision=turn.revision,
        expected_ledger_revision=record.revision, event=event, prepared_request_json=raw)
    included = RulesBuildProviderIncludedV1(kind="build_provider_included", event_id=uuid4(), sequence=len(record.execution.events),
        execution_id=scope.execution_id, provider_attempt_id=event.provider_attempt_id,
        request_envelope_sha256=event.request_envelope_sha256, matched_outputs=event.matched_outputs,
        support_refs=event.declared_support_refs, role=event.role, carrier_schema=event.carrier_schema,
        request_id=event.request_id, prior_provider_attempt_id=event.prior_provider_attempt_id)
    record = service.append_rules_provider_event(scope, expected_turn_revision=turn.revision,
        expected_ledger_revision=record.revision, event=included, prepared_request_json=raw)
    outcome = RulesProviderOutcomeV1(kind="provider_outcome", event_id=uuid4(), sequence=len(record.execution.events),
        execution_id=scope.execution_id, provider_attempt_id=event.provider_attempt_id,
        request_envelope_sha256=event.request_envelope_sha256, status="answered")
    return service.append_rules_provider_event(scope, expected_turn_revision=turn.revision,
        expected_ledger_revision=record.revision, event=outcome)


def read_under_controller():
    service, turn, scope, record = ready()
    controller, raw = prepared_provider(record.execution)
    record = persist_provider(service, turn, scope, record, controller, raw)
    auth = broker.prepare_build_authorization(record.execution, args(), origin_provider_attempt_id=controller.provider_attempt_id,
        origin_request_envelope_sha256=controller.request_envelope_sha256, decision_request_id=controller.request_id, operation_index=0)
    record = service.authorize_rules_lookup(scope, expected_turn_revision=turn.revision,
        expected_ledger_revision=record.revision, event=auth)
    delivery = service.execute_rules_lookup(scope, expected_turn_revision=turn.revision, call_id=auth.call_id,
        local_reader=lambda current: broker.prepare_lookup(current, auth.call_id, args()))
    return service, turn, scope, delivery


def mixed_result(turn, scope, record, writer, refs):
    text = "The supplied occupancy source restricts this movement."
    comp = AnswerCompositionV1(schema="dmb_answer_composition_v1", base_disposition="absent",
        ordered_refs=(OrderedAnswerRefV1(domain="rules", segment_index=0),),
        rules_segments=(RulesClaimV1(kind="rules_claim", claim_id="rules:1", text=text, support_refs=refs),),
        assistant_text_sha256=hashed(text))
    return MixedTurnResultV1(schema="dmb_mixed_turn_result_v1", scope=scope,
        expected_turn_revision=turn.revision, expected_rules_revision=record.revision,
        assistant_text=text, composition=comp, producing_provider_attempt_id=writer.provider_attempt_id, base_result=None)


def test_typed_origin_and_writer_are_durable_and_mixed_result_replays(application_state_dsn):
    service, turn, scope, delivery = read_under_controller()
    record, writer, result = runtime_result(service, turn, scope, delivery)
    result = BuildRulesMixedTurnResultV1.model_validate_json(result.model_dump_json(by_alias=True))
    completed = service.complete_mixed_turn(result)
    assert completed.accepted_binding.producing_provider_attempt_id == writer.provider_attempt_id
    assert completed.base_projection.kind == "absent" and not completed.accepted_binding.graph_used
    assert service.complete_mixed_turn(result) == completed
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute("SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s", (turn.turn_id,)).fetchone()[0]
    assert payload["state"] == "accepted" and len(payload["supports"]) == 1
    assert any(e["kind"] == "build_tool_authorized" for e in payload["events"])
    assert [e["role"] for e in payload["events"] if e["kind"] == "build_provider_authorized"] == ["controller", "writer"]


def test_changed_typed_packet_is_denied_without_persisting_authorization(application_state_dsn):
    service, turn, scope, delivery = read_under_controller()
    record = delivery.record
    writer, raw = prepared_provider(record.execution, role="writer", result=delivery.prepared)
    body = json.loads(raw); packet = json.loads(body["input"])
    packet["rules_projection"]["operations"][0]["packet_json"] += " "
    body["input"] = json.dumps(packet); changed = json.dumps(body)
    writer = writer.model_copy(update={"request_envelope_sha256": hashed(changed)})
    with pytest.raises(ApplicationStateValidationError):
        service.append_rules_provider_event(scope, expected_turn_revision=turn.revision,
            expected_ledger_revision=record.revision, event=writer, prepared_request_json=changed)
    with psycopg.connect(application_state_dsn) as conn:
        revision, payload = conn.execute("SELECT revision,payload FROM agent.turn_rules_execution WHERE turn_id=%s", (turn.turn_id,)).fetchone()
    assert revision == record.revision and payload["events"][-1]["kind"] == "query_observed"
    assert payload["state"] == "active"


def test_controller_cannot_commit_the_final_cited_answer(application_state_dsn):
    service, turn, scope, delivery = read_under_controller()
    record = delivery.record
    controller, raw = prepared_provider(record.execution, result=delivery.prepared)
    record = persist_provider(service, turn, scope, record, controller, raw)
    result = mixed_result(turn, scope, record, controller, delivery.prepared.observation.support_refs)
    with pytest.raises(ApplicationStateValidationError) as rejected:
        service.complete_mixed_turn(result)
    assert "outer output proof" in str(rejected.value)
    assert service.inspect_turn(world_id=scope.world_id, turn_id=scope.turn_id).status == "running"
    with psycopg.connect(application_state_dsn) as conn:
        state = conn.execute("SELECT payload->>'state',accepted_binding FROM agent.turn_rules_execution WHERE turn_id=%s", (turn.turn_id,)).fetchone()
    assert state == ("active", None)


def test_expired_typed_controller_is_nonreclaimable_and_keeps_source_evidence(application_state_dsn):
    from application_state.errors import ApplicationStateConflictError
    service, turn, scope, delivery = read_under_controller()
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (turn.turn_id,))
    with pytest.raises(ApplicationStateConflictError, match="cannot be reclaimed"):
        service.claim_turn(scope.world_id, scope.conversation_id, scope.turn_id, expected_revision=turn.revision)
    interrupted = service.inspect_turn(world_id=scope.world_id, turn_id=scope.turn_id)
    assert interrupted.status == "interrupted" and interrupted.attempt == scope.product_attempt
    assert interrupted.failure_code == "rules_provider_authorized_nonreclaimable"
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute("SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s", (turn.turn_id,)).fetchone()[0]
    assert payload["state"] == "failed" and len(payload["supports"]) == 1
    assert any(e["kind"] == "build_provider_authorized" for e in payload["events"])


def test_same_correlation_cannot_open_a_different_actual_logical_turn(application_state_dsn):
    from application_state.errors import ApplicationStateConflictError
    service, turn, scope, record = ready()
    other, original = admitted()
    cap = rules_capability(graph=True)
    data = original.model_dump(mode="json", by_alias=True)
    data.update(ruleset_id=cap.ruleset_id, corpus_sha256=cap.corpus_sha256,
        capability_policy_sha256=cap.policy_sha256, authorization_id=str(scope.authorization_id))
    wrong = RulesScopeV1.model_validate_json(json.dumps(data))
    with pytest.raises(ApplicationStateConflictError, match="logical submission"):
        service.begin_rules_execution(wrong, expected_turn_revision=other.revision)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM agent.turn_rules_execution WHERE turn_id=%s", (other.turn_id,)).fetchone()[0] == 0


def runtime_result(service, turn, scope, delivery, *, capture=True):
    record = delivery.record
    writer, request = prepared_provider(record.execution, role="writer", result=delivery.prepared)
    body = json.loads(request)
    carrier = json.loads(body["input"])
    carrier.update(output_packet())
    carrier["user_question"] = turn.user_text
    body["input"] = json.dumps(carrier)
    refs = delivery.prepared.observation.support_refs
    body["text"] = {"format": build_output_format(carrier, refs)}
    request = json.dumps(body)
    writer = writer.model_copy(update={"request_envelope_sha256": hashed(request)})
    record = persist_provider(service, turn, scope, record, writer, request)
    raw = json.dumps(raw_answer(refs), ensure_ascii=False)
    if capture:
        trace = service.start_context_trace(world_id=scope.world_id, conversation_id=scope.conversation_id,
            turn_id=scope.turn_id, expected_revision=turn.revision, attempt=turn.attempt,
            trace_id=uuid4(), started_at=datetime.now(UTC))
        service.append_context_trace(world_id=scope.world_id, conversation_id=scope.conversation_id,
            turn_id=scope.turn_id, expected_revision=turn.revision, attempt=turn.attempt, trace_id=trace.trace_id,
            observation=TraceContextSnapshot(sequence=0, elapsed_ms=0, stage="after", materials=[{
                "item_id": f"unvalidated-rules-answer:{writer.provider_attempt_id}:{scope.execution_id}",
                "state": "model_context", "role": "assistant", "text": raw}]))
    composition = parse_answer(raw).composition(base_completion=None, supplied_refs=refs, base_segments=(), base_disposition="absent")
    result = BuildRulesMixedTurnResultV1(schema="dmb_build_rules_mixed_turn_result_v1", scope=scope,
        expected_turn_revision=turn.revision, expected_rules_revision=record.revision,
        assistant_text=composition.render(), composition=composition,
        producing_provider_attempt_id=writer.provider_attempt_id, base_result=None,
        output_proof=BuildRulesOutputProofV1(policy=POLICY, prepared_request_json=request, raw_output_json=raw))
    return record, writer, result


def db_state(dsn, turn):
    with psycopg.connect(dsn) as conn:
        return conn.execute("""SELECT t.status,t.revision,t.assistant_text,t.answer_composition_kind,
            r.revision,r.payload,r.accepted_binding FROM agent.turn t
            JOIN agent.turn_rules_execution r ON r.turn_id=t.turn_id AND r.product_attempt=t.attempt
            WHERE t.turn_id=%s""", (turn.turn_id,)).fetchone()


@pytest.mark.parametrize("mutation", ["raw", "composition", "request", "missing_capture"])
def test_actual_output_guard_rejects_without_changing_either_domain(application_state_dsn, mutation):
    service, turn, scope, delivery = read_under_controller()
    record, writer, result = runtime_result(service, turn, scope, delivery, capture=mutation != "missing_capture")
    before = db_state(application_state_dsn, turn)
    if mutation == "raw":
        result = result.model_copy(update={"output_proof": result.output_proof.model_copy(update={
            "raw_output_json": result.output_proof.raw_output_json + " "})})
    elif mutation == "request":
        result = result.model_copy(update={"output_proof": result.output_proof.model_copy(update={
            "prepared_request_json": result.output_proof.prepared_request_json + " "})})
    elif mutation == "composition":
        ordinary = mixed_result(turn, scope, record, writer, delivery.prepared.observation.support_refs)
        result = result.model_copy(update={"composition": ordinary.composition, "assistant_text": ordinary.assistant_text})
    with pytest.raises(ApplicationStateValidationError):
        service.complete_mixed_turn(result)
    assert db_state(application_state_dsn, turn) == before
    assert service.inspect_turn(world_id=scope.world_id, turn_id=scope.turn_id).status == "running"


def test_runtime_policy_cannot_use_the_proofless_internal_result(application_state_dsn):
    service, turn, scope, delivery = read_under_controller()
    record, writer, result = runtime_result(service, turn, scope, delivery)
    proofless = MixedTurnResultV1(**result.model_dump(exclude={"schema_", "output_proof"}), schema="dmb_mixed_turn_result_v1")
    before = db_state(application_state_dsn, turn)
    with pytest.raises(ApplicationStateValidationError, match="actual outer output proof"):
        service.complete_mixed_turn(proofless)
    assert db_state(application_state_dsn, turn) == before


def test_completed_runtime_replay_uses_only_frozen_summary_and_not_transient_trace(application_state_dsn):
    service, turn, scope, delivery = read_under_controller()
    _, _, result = runtime_result(service, turn, scope, delivery)
    completed = service.complete_mixed_turn(result)
    with psycopg.connect(application_state_dsn) as conn:
        # Diagnostic retention is not an accepted citation's authority.
        conn.execute("DELETE FROM agent.turn_context_trace WHERE turn_id=%s", (turn.turn_id,))
    assert service.complete_mixed_turn(result) == completed
    changed = result.model_copy(update={"output_proof": result.output_proof.model_copy(update={
        "prepared_request_json": result.output_proof.prepared_request_json + " "})})
    with pytest.raises(ApplicationStateValidationError, match="Replayed output"):
        service.complete_mixed_turn(changed)
    assert service.inspect_turn(world_id=scope.world_id, turn_id=scope.turn_id) == completed


def test_actual_outer_output_acceptance_rolls_back_on_late_commit_failure(application_state_dsn):
    service, turn, scope, delivery = read_under_controller()
    _, _, result = runtime_result(service, turn, scope, delivery)
    before = db_state(application_state_dsn, turn)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("""CREATE FUNCTION reject_accepted_rules() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.accepted_binding IS NOT NULL THEN RAISE EXCEPTION 'fixture deferred mixed commit failure'; END IF;
            RETURN NEW; END $$""")
        conn.execute("""CREATE CONSTRAINT TRIGGER fail_mixed_at_commit AFTER UPDATE ON agent.turn_rules_execution
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION reject_accepted_rules()""")
    with pytest.raises(psycopg.errors.RaiseException, match="deferred mixed commit failure"):
        service.complete_mixed_turn(result)
    assert db_state(application_state_dsn, turn) == before


@pytest.fixture
def current_build_case(tmp_path, monkeypatch, application_state_dsn):
    from tests.test_agent_build_jev_ordinary_harness import build_case
    return build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def test_mixed_base_projection_reconstructs_actual_build_receipts_without_a_fake_capture(
        current_build_case, monkeypatch, tmp_path):
    """Base helper witness only; actual mixed parent dispatch is a remaining gate."""
    from types import SimpleNamespace
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.rules_authority_completion import RulesCitedSourceTurnResultV1
    from application_state.agent_conversation.rules_authority_output import validate_build_base_completion
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from tests.test_agent_build_jev_ordinary_harness import ordinary_case, DecisionWire, WriterWire
    from tests.test_agent_build_governed_graph import execute
    from tests.test_build_jev_estimated_continuations import counter

    case, _ = ordinary_case(current_build_case, monkeypatch)
    original = AgentConversationService.complete_turn
    seen = []
    def guarded(service, result):
        assert isinstance(result, t.CitedSourceTurnResult)
        turn = service.list_turns(result.world_id, result.conversation_id)[0]
        execution_id = uuid4()
        # A pure outer projection, never submitted as captured provider bytes.
        outer = raw_answer(with_base=True)
        outer["base_output"] = json.loads(result.raw_provider_output_json)
        raw = json.dumps(outer)
        proof = BuildRulesOutputProofV1(policy=POLICY, prepared_request_json=result.writer_request_json, raw_output_json=raw)
        mixed_base = RulesCitedSourceTurnResultV1(**result.model_dump(by_alias=True, exclude={"raw_provider_output_json"}),
            raw_provider_output_json=raw, rules_execution_id=execution_id, rules_output_policy=POLICY)
        execution = SimpleNamespace(scope=SimpleNamespace(execution_id=execution_id))
        candidate = parse_answer(raw)
        composition = candidate.composition(base_completion=result.completion, supplied_refs=(),
            base_segments=tuple(item.text for item in result.completion.answer_segments), base_disposition="approved")
        cap = rules_capability(graph=True)
        serialization_scope = RulesScopeV1(schema="dmb_rules_scope_v1", execution_id=execution_id,
            world_id=turn.world_id, conversation_id=turn.conversation_id, turn_id=turn.turn_id,
            product_attempt=turn.attempt, ruleset_id=cap.ruleset_id, corpus_sha256=cap.corpus_sha256,
            capability_policy_sha256=cap.policy_sha256, authorization_id=uuid4(), budget=cap.budget)
        serializable = BuildRulesMixedTurnResultV1(schema="dmb_build_rules_mixed_turn_result_v1",
            scope=serialization_scope, expected_turn_revision=turn.revision, expected_rules_revision=1,
            assistant_text=composition.render(tuple(item.text for item in result.completion.answer_segments)),
            composition=composition, producing_provider_attempt_id=result.producing_provider_attempt_id,
            base_result=mixed_base, output_proof=proof)
        decoded = BuildRulesMixedTurnResultV1.model_validate_json(serializable.model_dump_json(by_alias=True))
        assert isinstance(decoded.base_result, RulesCitedSourceTurnResultV1)
        assert isinstance(decoded.base_result.completion, t.BuildGraphCompletionV2)
        assert decoded.base_result == mixed_base
        validate_build_base_completion(mixed_base, turn, rules_execution=execution, output_proof=proof, answer=candidate)
        forged = mixed_base.model_copy(deep=True)
        forged.completion.answer_segments[0].text = "Uncaptured changed source fact"
        with pytest.raises(ValueError, match="normalization"):
            validate_build_base_completion(forged, turn, rules_execution=execution, output_proof=proof, answer=candidate)
        foreign = mixed_base.model_copy(update={"producing_provider_attempt_id": uuid4()})
        with pytest.raises(ValueError, match="same producing Graph"):
            validate_build_base_completion(foreign, turn, rules_execution=execution, output_proof=proof, answer=candidate)
        with pytest.raises(ApplicationStateValidationError, match="atomic mixed acceptance"):
            original(service, mixed_base)
        seen.append(result)
        return original(service, result)
    monkeypatch.setattr(AgentConversationService, "complete_turn", guarded)
    wire = WriterWire()
    response = execute(case, tmp_path, BuildJevHarness(decision_transport=DecisionWire(),
        writer_transport=wire, accounting=counter()))
    assert len(wire.calls) == len(seen) == 1 and "Frank believes" in response.answer.text
