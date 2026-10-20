"""Real APP typed Rules persistence; Graph parent carrier admission is separate."""
import json
from uuid import uuid4

import psycopg
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_policy import rules_capability, rules_submission_authorization_id
from application_state.agent_conversation.rules_authority_types import RulesScopeV1, AnswerCompositionV1, OrderedAnswerRefV1, RulesClaimV1
from application_state.agent_conversation.rules_authority_completion import MixedTurnResultV1
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
    record = delivery.record
    writer, raw = prepared_provider(record.execution, role="writer", result=delivery.prepared)
    record = persist_provider(service, turn, scope, record, writer, raw)
    result = mixed_result(turn, scope, record, writer, delivery.prepared.observation.support_refs)
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
    assert "controller" in str(rejected.value.__cause__)
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
