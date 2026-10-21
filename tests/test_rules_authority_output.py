"""Actual producing-input joins and deterministic mixed output, not base approval."""
from copy import deepcopy
from hashlib import sha256
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from jsonschema import Draft202012Validator

from application_state.agent_conversation import source_writer_output as base
from application_state.agent_conversation.rules_authority_output import (
    POLICY, SCHEMA, MAX_OUTPUT_BYTES, build_output_format, parse_answer, verify_build_output,
)
from tests.test_rules_build_input import read_after_controller, prepared_provider, acknowledge


def packet():
    return {"source_writer_output_policy": base.POLICY,
            "requested_detail_gap_policy": base.GAP_POLICY,
            "rules_mixed_output_policy": POLICY,
            "user_question": "What happened and what about travel?",
            "retrieval_disposition": {"status": "insufficient_evidence", "coverage_status": "heuristic_partial"},
            "opened_passages": [], "exposure": {"saved_sections": []}}


def raw_answer(refs=(), *, with_base=False):
    value = {"schema": SCHEMA, "base_output": None,
        "rules_segments": [{"kind": "rules_claim", "text": "Occupancy limits apply. 🐉",
                            "support_ids": [str(refs[0].support_id)]}] if refs else [
            {"kind": "rules_context", "category": "gap", "text": "No travel rules were retrieved."}],
        "ordered_refs": [{"domain": "rules", "segment_index": 0}]}
    if with_base:
        value["base_output"] = {"answer_context_status": "source_insufficient_evidence", "answer_segments": [],
            "limitations": ["missing_requested_details", "partial_retrieval"],
            "requested_detail_gaps": [{"question_phrase": "travel"}]}
        value["ordered_refs"].insert(0, {"domain": "base", "segment_index": None})
    return value


def producing_case(*, expose=True, with_base=True):
    owner, result, _ = read_after_controller()
    event, request = prepared_provider(owner, role="writer", result=result if expose else None)
    body = json.loads(request)
    carrier = json.loads(body["input"])
    carrier.update(packet())
    refs = result.observation.support_refs if expose else ()
    body["input"] = json.dumps(carrier)
    body["text"] = {"format": build_output_format(carrier, refs)}
    request = json.dumps(body)
    event = event.model_copy(update={"request_envelope_sha256": sha256(request.encode()).hexdigest()})
    owner = acknowledge(owner, event, request)
    raw = json.dumps(raw_answer(refs, with_base=with_base), ensure_ascii=False)
    scope = owner.scope
    trace = {"world_id": scope.world_id, "conversation_id": str(scope.conversation_id),
        "turn_id": str(scope.turn_id), "attempt": scope.product_attempt, "capture_status": "recording",
        "observations": [{"kind": "context_snapshot", "stage": "after", "materials": [{
            "item_id": f"unvalidated-rules-answer:{event.provider_attempt_id}:{scope.execution_id}",
            "state": "model_context", "role": "assistant", "text": raw}]}]}
    return owner, result, event, request, raw, trace


def verify(case):
    owner, _, event, request, raw, trace = case
    return verify_build_output(owner, producing_provider_attempt_id=event.provider_attempt_id,
        prepared_request_json=request, raw_output_json=raw, trace=trace)


def test_actual_writer_output_preserves_host_gaps_and_limits_and_python_offsets():
    case = producing_case()
    answer = verify(case)
    owner, result, _, request, raw, _ = case
    # This normalization is not Graph completion approval; its owner still proves receipts.
    carrier = json.loads(json.loads(request)["input"])
    normalized = base.normalize(json.dumps(answer.base_output), carrier)
    texts = tuple(seg["text"] for seg in normalized["answer_segments"])
    assert len(texts) == 3 and "travel" in texts[0]
    composition = answer.composition(supplied_refs=result.observation.support_refs,
        base_segments=texts, base_disposition="approved")
    assert [ref.segment_index for ref in composition.ordered_refs if ref.domain == "base"] == [0, 1, 2]
    assert composition.render(texts) == "\n".join((*texts, "Occupancy limits apply. 🐉"))
    claim = composition.rules_segments[0]
    assert claim.claim_id == "rules:0" and claim.support_refs == result.observation.support_refs
    assert "support_sha256" not in raw and str(owner.scope.execution_id) not in raw


def test_rules_only_partition_does_not_invent_a_graph_completion():
    case = producing_case(with_base=False)
    answer = verify(case)
    composition = answer.composition(supplied_refs=case[1].observation.support_refs,
        base_segments=(), base_disposition="unclaimed")
    assert composition.base_disposition == "unclaimed"
    assert not any(ref.domain == "base" for ref in composition.ordered_refs)
    with pytest.raises(ValueError, match="disposition"):
        answer.composition(supplied_refs=(), base_segments=(), base_disposition="approved")


@pytest.mark.parametrize("expose", [False, True])
def test_schema_is_strict_finite_with_resolved_namespaced_base_definitions(expose):
    case = producing_case(expose=expose)
    fmt = json.loads(case[3])["text"]["format"]
    schema = fmt["schema"]
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(case[4]))
    assert fmt["strict"] is True
    assert "Base_RequestedDetailGap" in schema["$defs"]
    assert ("WriterRulesClaimV1" in schema["$defs"]) is expose
    invalid = raw_answer(case[1].observation.support_refs)
    invalid["rules_segments"][0]["support_ids"] = [str(uuid4())]
    assert list(Draft202012Validator(schema).iter_errors(invalid))
    # Finite base selector branches with no admitted passages/sections are absent.
    assert "Base_PassageFact" not in schema["$defs"] and "Base_SavedFact" not in schema["$defs"]


@pytest.mark.parametrize("change", [
    lambda value: value.update(extra="metadata"),
    lambda value: value["rules_segments"][0].update(support_sha256="a" * 64),
    lambda value: value["rules_segments"][0].update(support_ids=[str(uuid4()).upper()]),
    lambda value: value["rules_segments"][0].update(text="  "),
    lambda value: value["ordered_refs"].append(value["ordered_refs"][0]),
    lambda value: value["ordered_refs"][0].update(segment_index=True),
    lambda value: value["ordered_refs"][0].update(segment_index=None),
    lambda value: value.update(base_output={}),
    lambda value: value.update(rules_segments=[]),
])
def test_ambiguous_or_model_supplied_authority_rejects(change):
    value = raw_answer((type("Ref", (), {"support_id": uuid4()})(),))
    change(value)
    with pytest.raises((ValueError, ValidationError)):
        parse_answer(json.dumps(value))


@pytest.mark.parametrize("raw", ['{"schema":"x","schema":"x"}',
    '{"schema":NaN}', '[]', '"answer"', 'not JSON'])
def test_invalid_or_duplicate_json_rejects(raw):
    with pytest.raises(ValueError): parse_answer(raw)


def test_utf8_and_visible_text_budgets_reject_without_truncation():
    value = raw_answer()
    value["rules_segments"] = [{"kind": "rules_context", "category": "gap", "text": "🐉" * 4000}] * 20
    value["ordered_refs"] = [{"domain": "rules", "segment_index": index} for index in range(20)]
    raw = json.dumps(value, ensure_ascii=False)
    assert len(raw.encode()) > MAX_OUTPUT_BYTES
    with pytest.raises(ValueError, match="UTF8"): parse_answer(raw)
    value["rules_segments"] = value["rules_segments"][:9]
    value["ordered_refs"] = value["ordered_refs"][:9]
    answer = parse_answer(json.dumps(value, ensure_ascii=False))
    with pytest.raises(ValueError, match="Full answer"):
        answer.composition(supplied_refs=(), base_segments=(), base_disposition="absent")


@pytest.mark.parametrize("field,value", [("world_id", "other"), ("turn_id", str(uuid4())),
    ("conversation_id", str(uuid4())), ("attempt", 2), ("capture_status", "incomplete")])
def test_foreign_or_incomplete_capture_rejects(field, value):
    case = list(producing_case())
    case[5][field] = value
    with pytest.raises(ValueError, match="capture"): verify(case)


@pytest.mark.parametrize("mutation", ["raw", "duplicate", "role", "item", "stage"])
def test_missing_changed_or_ambiguous_raw_producer_rejects(mutation):
    case = list(producing_case())
    observation = case[5]["observations"][0]
    material = observation["materials"][0]
    if mutation == "raw": case[4] += " "
    elif mutation == "duplicate": observation["materials"].append(deepcopy(material))
    elif mutation == "role": material["role"] = "user"
    elif mutation == "item": material["item_id"] = "unvalidated-provider-answer:other"
    else: observation["stage"] = "before"
    with pytest.raises(ValueError, match="captured producer"): verify(case)


def test_actual_request_mutation_fails_even_when_output_capture_matches():
    case = list(producing_case())
    body = json.loads(case[3]); body["model"] = "other"; case[3] = json.dumps(body)
    with pytest.raises(ValueError, match="envelope"): verify(case)


def test_retained_support_not_sent_to_final_writer_cannot_be_cited():
    case = list(producing_case(expose=False))
    value = json.loads(case[4])
    value["rules_segments"] = raw_answer(case[1].observation.support_refs)["rules_segments"]
    case[4] = json.dumps(value)
    case[5]["observations"][0]["materials"][0]["text"] = case[4]
    with pytest.raises(ValueError, match="absent from its producing input"): verify(case)


def test_base_normalization_failure_remains_failure_not_rules_fallback():
    case = producing_case()
    answer = verify(case)
    corrupt = dict(answer.base_output, limitations=[])
    with pytest.raises(ValueError, match="Abstention"):
        base.normalize(json.dumps(corrupt), json.loads(json.loads(case[3])["input"]))


@pytest.mark.parametrize("mutation", ["strict_integer", "schema_selector", "policy", "missing_format", "wrong_text"])
def test_acknowledged_request_with_wrong_frozen_output_contract_rejects(mutation):
    owner, result, _ = read_after_controller()
    event, request = prepared_provider(owner, role="writer", result=result)
    body = json.loads(request)
    carrier = json.loads(body["input"])
    carrier.update(packet())
    body["text"] = {"format": build_output_format(carrier, result.observation.support_refs)}
    if mutation == "strict_integer": body["text"]["format"]["strict"] = 1
    elif mutation == "schema_selector":
        body["text"]["format"]["schema"]["$defs"]["WriterRulesClaimV1"]["properties"]["support_ids"]["items"]["enum"] = [str(uuid4())]
    elif mutation == "policy": carrier["rules_mixed_output_policy"] = "unknown"
    elif mutation == "wrong_text": body["text"] = "json"
    else: del body["text"]
    body["input"] = json.dumps(carrier)
    request = json.dumps(body)
    event = event.model_copy(update={"request_envelope_sha256": sha256(request.encode()).hexdigest()})
    owner = acknowledge(owner, event, request)
    with pytest.raises(ValueError, match="format|policy"):
        verify_build_output(owner, producing_provider_attempt_id=event.provider_attempt_id,
            prepared_request_json=request, raw_output_json=json.dumps(raw_answer()), trace={})


def test_wrong_or_controller_producer_never_becomes_final_output_authority():
    case = producing_case()
    for producer in (uuid4(), case[0].events[0].provider_attempt_id):
        with pytest.raises(ValueError, match="actual final"):
            verify_build_output(case[0], producing_provider_attempt_id=producer,
                prepared_request_json=case[3], raw_output_json=case[4], trace=case[5])


def test_more_than_sixteen_claims_rejects_before_persistence():
    case = producing_case()
    value = raw_answer(case[1].observation.support_refs)
    value["rules_segments"] *= 17
    value["ordered_refs"] = [{"domain": "rules", "segment_index": index} for index in range(17)]
    with pytest.raises(ValueError, match="claim limit"):
        parse_answer(json.dumps(value))


def test_expanded_base_plus_rules_cannot_exceed_durable_map_budget():
    answer = parse_answer(json.dumps(raw_answer(with_base=True)))
    with pytest.raises(ValidationError):
        answer.composition(supplied_refs=(), base_segments=("base",) * 128, base_disposition="approved")
