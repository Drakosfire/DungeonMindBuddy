"""APP typed Rules joins; parent complete Build carrier proof is separate."""
from hashlib import sha256
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.rules_authority_events import (
    RulesExecutionV1, RulesToolAuthorizedV1, RulesProviderAuthorizedV1,
    RulesProviderIncludedV1, RulesProviderOutcomeV1, RulesOutputRefV1,
    RulesBuildProviderAuthorizedV1, RulesBuildProviderIncludedV1,
)
from application_state.agent_conversation.rules_authority_input import verify_prepared_input
from application_state.agent_conversation.rules_authority_packet import append_observed_output
from application_state.agent_conversation.rules_authority_build_input import RulesBuildProjectionV1, RulesBuildOperationV1
from application_state.agent_conversation.rules_authority_policy import rules_capability
from application_state.agent_conversation.rules_authority_completion import prepare_rules_acceptance
from application_state.agent_conversation.rules_authority_types import (
    AnswerCompositionV1, RulesClaimV1, OrderedAnswerRefV1,
)
from apps.live_control_server.services import rules_lookup_broker as broker
from tests.test_rules_lookup_broker import execution as initial_execution, args


def hashed(raw): return sha256(raw.encode()).hexdigest()


def execution():
    data = initial_execution().model_dump(mode="json", by_alias=True)
    data["scope"]["capability_policy_sha256"] = rules_capability(graph=True).policy_sha256
    return RulesExecutionV1.model_validate_json(json.dumps(data))


def append(owner, event):
    data = owner.model_dump(mode="json", by_alias=True)
    data["events"].append(event.model_dump(mode="json", by_alias=True))
    if isinstance(event, RulesToolAuthorizedV1):
        data["budget_use"]["calls"] += 1
        data["budget_use"]["distinct_questions"] = len({e["query_id"] for e in data["events"] if e["kind"] in {"tool_authorized", "build_tool_authorized"}})
    if isinstance(event, RulesProviderAuthorizedV1):
        data["budget_use"]["provider_requests"] += 1
    return RulesExecutionV1.model_validate_json(json.dumps(data))


def prepared_provider(owner, *, role="controller", result=None, schema=None, phase="assess"):
    previous = [e for e in owner.events if isinstance(e, RulesProviderAuthorizedV1)]
    schema = schema or ("dmb_build_jev_driver_decision_v2" if not previous else "dmb_build_jev_phase_controller_v1") if role == "controller" else (schema or "dmb_build_source_passage_writer_v1")
    operations = () if result is None else (RulesBuildOperationV1(operation_id=result.observation.call_id, packet_json=result.raw_output),)
    projection = RulesBuildProjectionV1(schema="dmb_build_rules_projection_v1",
        authorization_id=owner.scope.authorization_id,
        rules_event_sequence=len(owner.events), role=role, carrier_schema=schema,
        request_id=f"request:{len(owner.events)}", prior_provider_attempt_id=previous[-1].provider_attempt_id if previous else None,
        operations=operations)
    carrier = {"schema": schema, "rules_projection": projection.model_dump(mode="json", by_alias=True)}
    if role == "controller":
        if schema == "dmb_build_jev_driver_decision_v2":
            carrier.update(policy="parent_machine_lossless_v1", initial_packet_codec="dmb_build_initial_packet_table_v1")
        elif schema == "dmb_build_jev_driver_continuation_v1":
            carrier.update(input_policy="receipt_bound_factored_controller_v1")
        else:
            carrier.update(input_policy="role_separated_controller_inputs_v1", phase_binding={"phase": phase})
        body = {"model": "jev-1.14.0", "state": carrier, "questions": {"action": {"question": "Choose current action"}}}
    else:
        if schema in {"dmb_build_source_passage_writer_v1", "dmb_build_primary_context_writer_v1"}:
            carrier.update(source_writer_output_policy="cited_facts_host_limitations_v1",
                requested_detail_gap_policy="exact_question_phrase_selected_excerpts_v1")
        else:
            carrier.update(input_policy="complete_exposed_graph_and_opened_sources_v1")
        if schema == "dmb_build_primary_context_writer_v1":
            from application_state.agent_conversation import build_primary_context as primary
            carrier["artifact_under_edit"] = {"policy": primary.POLICY, "role": primary.ROLE, "sections": []}
        body = {"model": "gpt-6-luna", "input": json.dumps(carrier), "tools": []}
    raw = json.dumps(body)
    refs = () if result is None else result.observation.support_refs
    outputs = () if result is None else (RulesOutputRefV1(call_id=result.observation.call_id, packet_sha256=result.observation.packet_sha256),)
    event = RulesBuildProviderAuthorizedV1(kind="build_provider_authorized", event_id=uuid4(),
        sequence=len(owner.events), execution_id=owner.scope.execution_id, provider_attempt_id=uuid4(),
        request_envelope_sha256=hashed(raw), matched_outputs=outputs, declared_support_refs=refs,
        role=role, carrier_schema=schema, request_id=projection.request_id,
        prior_provider_attempt_id=projection.prior_provider_attempt_id)
    return event, raw


def acknowledge(owner, event, raw, *, status="answered"):
    verify_prepared_input(owner, event, raw)
    owner = append(owner, event)
    included = RulesBuildProviderIncludedV1(kind="build_provider_included", event_id=uuid4(), sequence=len(owner.events),
        execution_id=owner.scope.execution_id, provider_attempt_id=event.provider_attempt_id,
        request_envelope_sha256=event.request_envelope_sha256, matched_outputs=event.matched_outputs,
        support_refs=event.declared_support_refs, role=event.role, carrier_schema=event.carrier_schema,
        request_id=event.request_id, prior_provider_attempt_id=event.prior_provider_attempt_id)
    verify_prepared_input(owner, included, raw)
    owner = append(owner, included)
    return append(owner, RulesProviderOutcomeV1(kind="provider_outcome", event_id=uuid4(), sequence=len(owner.events),
        execution_id=owner.scope.execution_id, provider_attempt_id=event.provider_attempt_id,
        request_envelope_sha256=event.request_envelope_sha256, status=status))


def read_after_controller():
    owner = execution()
    controller, raw = prepared_provider(owner)
    owner = acknowledge(owner, controller, raw)
    auth = broker.prepare_build_authorization(owner, args(), origin_provider_attempt_id=controller.provider_attempt_id,
        origin_request_envelope_sha256=controller.request_envelope_sha256, decision_request_id=controller.request_id,
        operation_index=0)
    owner = append(owner, auth)
    result = broker.prepare_lookup(owner, auth.call_id, args())
    return append_observed_output(owner, result.observation, result.raw_output, result.new_supports), result, controller


def accept(owner, event, refs):
    text = "The cited source limits ending movement in occupied space."
    composition = AnswerCompositionV1(schema="dmb_answer_composition_v1", base_disposition="absent",
        ordered_refs=(OrderedAnswerRefV1(domain="rules", segment_index=0),),
        rules_segments=(RulesClaimV1(kind="rules_claim", claim_id="rules:1", text=text, support_refs=refs),),
        assistant_text_sha256=hashed(text))
    return prepare_rules_acceptance(owner, composition, producing_provider_attempt_id=event.provider_attempt_id,
        accepted_turn_revision=9, event_id=uuid4())


def test_actual_typed_writer_source_and_accepted_producer_are_joined():
    owner, result, controller = read_after_controller()
    writer, raw = prepared_provider(owner, role="writer", result=result)
    owner = acknowledge(owner, writer, raw)
    accepted, binding = accept(owner, writer, result.observation.support_refs)
    assert accepted.state == "accepted" and binding.producing_provider_attempt_id == writer.provider_attempt_id
    assert accepted.budget_use.calls == 1 and accepted.budget_use.provider_requests == 2
    assert len(accepted.supports) == 1 and binding.graph_used is False
    assert controller.provider_attempt_id != binding.producing_provider_attempt_id


def test_controller_body_is_not_inherited_by_empty_final_writer():
    owner, result, _ = read_after_controller()
    controller, raw = prepared_provider(owner, result=result)
    owner = acknowledge(owner, controller, raw)
    writer, raw = prepared_provider(owner, role="writer")
    owner = acknowledge(owner, writer, raw)
    with pytest.raises(ValueError, match="absent from its producing input"):
        accept(owner, writer, result.observation.support_refs)
    with pytest.raises(ValueError, match="controller"):
        accept(owner, controller, result.observation.support_refs)


@pytest.mark.parametrize("status", ["failed", "unknown"])
def test_failed_or_unknown_origin_cannot_authorize_a_rules_read(status):
    owner = execution()
    controller, raw = prepared_provider(owner)
    owner = acknowledge(owner, controller, raw, status=status)
    with pytest.raises(ValueError, match="acknowledged"):
        broker.prepare_build_authorization(owner, args(), origin_provider_attempt_id=controller.provider_attempt_id,
            origin_request_envelope_sha256=controller.request_envelope_sha256, decision_request_id=controller.request_id,
            operation_index=0)


@pytest.mark.parametrize("mutate", [
    lambda c: c["rules_projection"].update(authorization_id=str(uuid4())),
    lambda c: c["rules_projection"].update(execution_id=str(uuid4())),
    lambda c: c["rules_projection"].update(turn_id=str(uuid4())),
    lambda c: c["rules_projection"].update(product_attempt=2),
    lambda c: c["rules_projection"].update(rules_event_sequence=0),
    lambda c: c["rules_projection"].update(role="controller"),
    lambda c: c["rules_projection"].update(request_id="foreign"),
    lambda c: c["rules_projection"].update(prior_provider_attempt_id=None),
    lambda c: c["rules_projection"].update(unknown=True),
    lambda c: c.update(schema="opaque_json"),
    lambda c: c.update(source_writer_output_policy="unknown"),
    lambda c: c["rules_projection"]["operations"][0].update(operation_id="fabricated"),
    lambda c: c["rules_projection"]["operations"][0].update(packet_json=c["rules_projection"]["operations"][0]["packet_json"] + " "),
])
def test_changed_typed_source_join_rejects_even_with_new_whole_request_hash(mutate):
    owner, result, _ = read_after_controller()
    writer, raw = prepared_provider(owner, role="writer", result=result)
    body = json.loads(raw); carrier = json.loads(body["input"])
    mutate(carrier); body["input"] = json.dumps(carrier); raw = json.dumps(body)
    writer = writer.model_copy(update={"request_envelope_sha256": hashed(raw)})
    with pytest.raises(ValueError):
        verify_prepared_input(owner, writer, raw)


def test_source_text_in_an_unregistered_field_grants_no_support():
    owner, result, _ = read_after_controller()
    writer, raw = prepared_provider(owner, role="writer", result=result)
    body = json.loads(raw); carrier = json.loads(body["input"])
    carrier["quoted_source"] = carrier["rules_projection"]["operations"].pop()["packet_json"]
    body["input"] = json.dumps(carrier); raw = json.dumps(body)
    writer = writer.model_copy(update={"request_envelope_sha256": hashed(raw)})
    with pytest.raises(ValueError, match="output declarations"):
        verify_prepared_input(owner, writer, raw)


def test_build_operation_cannot_be_recast_as_a_function_transcript():
    owner, result, _ = read_after_controller()
    raw = json.dumps({"input": [dict(type="function_call", call_id=result.observation.call_id,
        name="lookup_rules", arguments=args().model_dump_json()),
        dict(type="function_call_output", call_id=result.observation.call_id, output=result.raw_output)]})
    ordinary = RulesProviderAuthorizedV1(kind="provider_authorized", event_id=uuid4(), sequence=len(owner.events),
        execution_id=owner.scope.execution_id, provider_attempt_id=uuid4(), request_envelope_sha256=hashed(raw),
        matched_outputs=(RulesOutputRefV1(call_id=result.observation.call_id, packet_sha256=result.observation.packet_sha256),),
        declared_support_refs=result.observation.support_refs)
    with pytest.raises(ValueError, match="parent-produced"):
        verify_prepared_input(owner, ordinary, raw)
    typed, _ = prepared_provider(owner, role="writer", result=result)
    with pytest.raises(ValueError, match="synthetic function"):
        verify_prepared_input(owner, typed.model_copy(update={"request_envelope_sha256": hashed(raw)}), raw)


@pytest.mark.parametrize("phase", ["navigate", "coverage", "select"])
def test_navigation_projection_cannot_expose_source_bodies(phase):
    owner, result, _ = read_after_controller()
    controller, raw = prepared_provider(owner, result=result, phase=phase)
    with pytest.raises(ValueError, match="navigation"):
        verify_prepared_input(owner, controller, raw)


def test_missing_typed_policy_selector_never_accepts_state_as_source():
    owner, result, _ = read_after_controller()
    writer, raw = prepared_provider(owner, role="writer", result=result)
    data = owner.model_dump(mode="json", by_alias=True)
    data["scope"]["capability_policy_sha256"] = "b" * 64
    # Don't use model_copy as authority; the raw verifier checks the frozen scope
    # independently even when handed an internal forged object.
    foreign = owner.model_copy(update={"scope": owner.scope.model_copy(update={"capability_policy_sha256": "b" * 64})})
    with pytest.raises(ValueError, match="select"):
        verify_prepared_input(foreign, writer, raw)


def test_operation_identity_rejects_changed_decision_binding():
    owner, _, _ = read_after_controller()
    data = owner.model_dump(mode="json", by_alias=True)
    operation = next(e for e in data["events"] if e["kind"] == "build_tool_authorized")
    operation["decision_request_id"] = "foreign"
    with pytest.raises(ValidationError, match="decision identity"):
        RulesExecutionV1.model_validate_json(json.dumps(data))


def test_mixed_result_json_roundtrip_retains_cited_source_proof_subtype():
    from application_state.agent_conversation.rules_authority_completion import MixedTurnResultV1
    from application_state.agent_conversation.types import CitedSourceTurnResult
    from application_state.agent_conversation.rules_authority_types import RulesContextV1
    from tests.application_state.test_build_graph_turns import _submission, _completion
    owner = execution(); scope = owner.scope
    producer = uuid4()
    completion = _completion(_submission(scope.conversation_id))
    base_text = "\n".join(segment.text for segment in completion.answer_segments)
    base = CitedSourceTurnResult(world_id=scope.world_id, conversation_id=scope.conversation_id,
        turn_id=scope.turn_id, expected_revision=4, assistant_text=base_text, completion=completion,
        producing_provider_attempt_id=producer, claim_graph_event_ids={},
        writer_request_json='{"tools":[]}', raw_provider_output_json='{"proof":"raw captured output"}')
    # This is only serialization proof. The real base validator must still
    # reject fabricated raw producer evidence at transactional acceptance.
    text = base_text + "\nRules interpretation remains separate."
    composition = AnswerCompositionV1(schema="dmb_answer_composition_v1", base_disposition="approved",
        ordered_refs=(OrderedAnswerRefV1(domain="base", segment_index=0), OrderedAnswerRefV1(domain="rules", segment_index=0)),
        rules_segments=(RulesContextV1(kind="rules_context", segment_id="context:1", category="connective",
            text="Rules interpretation remains separate."),), assistant_text_sha256=hashed(text))
    result = MixedTurnResultV1(schema="dmb_mixed_turn_result_v1", scope=scope,
        expected_turn_revision=4, expected_rules_revision=7, assistant_text=text, composition=composition,
        producing_provider_attempt_id=producer, base_result=base)
    decoded = MixedTurnResultV1.model_validate_json(result.model_dump_json(by_alias=True))
    assert isinstance(decoded.base_result, CitedSourceTurnResult)
    assert decoded.base_result.writer_request_json == base.writer_request_json
    assert decoded.base_result.raw_provider_output_json == base.raw_provider_output_json


@pytest.mark.parametrize("mutate", [
    lambda body: body.update(model=None),
    lambda body: body.update(model=123),
    lambda body: body.update(model=""),
    lambda body: body.update(model="   "),
    lambda body: body.update(tools=[{"type": "function", "name": "unexpected"}]),
    lambda body: body.update(input=json.loads(body["input"])),
    lambda body: body.update(messages=[]),
    lambda body: body.update(state={}),
])
def test_unknown_or_ambiguous_actual_writer_carrier_is_rejected(mutate):
    owner, result, _ = read_after_controller()
    writer, raw = prepared_provider(owner, role="writer", result=result)
    body = json.loads(raw); mutate(body); raw = json.dumps(body)
    writer = writer.model_copy(update={"request_envelope_sha256": hashed(raw)})
    with pytest.raises(ValueError):
        verify_prepared_input(owner, writer, raw)


@pytest.mark.parametrize("model", ["gpt-6-luna", "gpt-6.1-sol"])
def test_writer_carrier_leaves_model_authorization_to_its_build_parent(model):
    owner, result, _ = read_after_controller()
    writer, raw = prepared_provider(owner, role="writer", result=result)
    body = json.loads(raw)
    body["model"] = model
    raw = json.dumps(body)
    writer = writer.model_copy(update={"request_envelope_sha256": hashed(raw)})
    owner = acknowledge(owner, writer, raw)
    accepted, binding = accept(owner, writer, result.observation.support_refs)
    assert accepted.state == "accepted"
    assert binding.producing_provider_attempt_id == writer.provider_attempt_id


def test_ordinary_provider_variant_cannot_borrow_typed_build_projection():
    owner, result, _ = read_after_controller()
    writer, raw = prepared_provider(owner, role="writer", result=result)
    ordinary = RulesProviderAuthorizedV1(kind="provider_authorized", event_id=writer.event_id,
        sequence=writer.sequence, execution_id=writer.execution_id, provider_attempt_id=writer.provider_attempt_id,
        request_envelope_sha256=writer.request_envelope_sha256, matched_outputs=writer.matched_outputs,
        declared_support_refs=writer.declared_support_refs)
    with pytest.raises(ValueError, match="Unknown or ambiguous"):
        verify_prepared_input(owner, ordinary, raw)


def test_inclusion_cannot_switch_its_persisted_typed_role():
    owner = execution(); controller, raw = prepared_provider(owner)
    verify_prepared_input(owner, controller, raw)
    owner = append(owner, controller)
    included = RulesBuildProviderIncludedV1(kind="build_provider_included", event_id=uuid4(), sequence=len(owner.events),
        execution_id=owner.scope.execution_id, provider_attempt_id=controller.provider_attempt_id,
        request_envelope_sha256=controller.request_envelope_sha256, matched_outputs=(), support_refs=(),
        role="writer", carrier_schema=controller.carrier_schema, request_id=controller.request_id,
        prior_provider_attempt_id=None)
    with pytest.raises(ValueError, match="role/request"):
        append(owner, included)


def test_first_body_uses_only_stable_correlation_across_fresh_never_dispatched_scopes():
    owner = execution()
    first, body1 = prepared_provider(owner)
    fields = owner.model_dump(mode="json", by_alias=True)
    fields["scope"].update(execution_id=str(uuid4()), product_attempt=2)
    retry = RulesExecutionV1.model_validate_json(json.dumps(fields))
    second, body2 = prepared_provider(retry)
    assert first.execution_id != second.execution_id and body1 == body2
    projection = json.loads(body1)["state"]["rules_projection"]
    assert projection["authorization_id"] == str(owner.scope.authorization_id)
    assert not {"execution_id", "turn_id", "product_attempt"} & set(projection)
    assert projection["rules_event_sequence"] == 0 and projection["prior_provider_attempt_id"] is None
    assert projection["operations"] == []
    verify_prepared_input(owner, first, body1)
    verify_prepared_input(retry, second, body2)
    # This only proves metadata can remain stable. Product-parent retries must
    # still prove the actual prior frozen Graph envelope and no dispatch.


def test_logical_correlation_separates_every_identity_component():
    from application_state.agent_conversation.rules_authority_policy import rules_submission_authorization_id
    identity = dict(world_id="elderwyld", conversation_id=uuid4(), idempotency_key=uuid4(),
        submitted_intent_sha256="a" * 64, capability=rules_capability(graph=True))
    original = rules_submission_authorization_id(**identity)
    assert original == rules_submission_authorization_id(**identity)
    for key, value in dict(world_id="other", conversation_id=uuid4(), idempotency_key=uuid4(),
            submitted_intent_sha256="b" * 64, capability=rules_capability(graph=False)).items():
        assert rules_submission_authorization_id(**(identity | {key: value})) != original


def test_prior_attempt_operation_never_becomes_current_by_shared_correlation():
    owner, result, _ = read_after_controller()
    fresh = execution()
    fields = fresh.model_dump(mode="json", by_alias=True)
    fields["scope"].update(authorization_id=str(owner.scope.authorization_id), product_attempt=2)
    fresh = RulesExecutionV1.model_validate_json(json.dumps(fields))
    controller, raw = prepared_provider(fresh)
    fresh = acknowledge(fresh, controller, raw)
    writer, raw = prepared_provider(fresh, role="writer", result=result)
    with pytest.raises(ValueError, match="admitted operation"):
        verify_prepared_input(fresh, writer, raw)


def test_first_provider_cannot_skip_to_a_writer_even_without_source_claims():
    owner = execution()
    writer, raw = prepared_provider(owner, role="writer")
    with pytest.raises(ValueError, match="initial controller"):
        append(owner, writer)


@pytest.mark.parametrize("schema", ["dmb_build_source_passage_writer_v1", "dmb_build_primary_context_writer_v1"])
def test_exact_versioned_writer_carrier_keeps_rules_binding(schema):
    owner, result, _ = read_after_controller()
    writer, raw = prepared_provider(owner, role="writer", result=result, schema=schema)
    completed = acknowledge(owner, writer, raw)
    accepted, _ = accept(completed, writer, result.observation.support_refs)
    assert accepted.state == "accepted"
    if schema == "dmb_build_primary_context_writer_v1":
        body = json.loads(raw)
        carrier = json.loads(body["input"])
        carrier["artifact_under_edit"]["role"] = "world_truth"
        body["input"] = json.dumps(carrier)
        with pytest.raises(ValueError):
            verify_prepared_input(owner, writer, json.dumps(body))
