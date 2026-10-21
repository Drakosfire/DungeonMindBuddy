"""Owning tests for the pure typed decision seam; no product IO authority."""
from uuid import uuid4
import json
import pytest
from pydantic import ValidationError
from generationengine.observation import InferenceObservation
from generationengine.types import ChoiceDecisionAnswer, DecisionResult, BinaryDecisionAnswer
from application_state.agent_conversation.jev_retrieval_contract import (
    MODEL, PROVIDER, RetrievalCandidate, RetrievalDecisionInput, RetrievalSelection,
    prepare_decision, decode_selection, validate_selection,
)


def request():
    return RetrievalDecisionInput(request_id=uuid4(), parent_attempt_id=uuid4(),
        scope_sha256="a" * 64, revision="graph:1", question="Ground an image of the swamp road near Edge.",
        candidates=(RetrievalCandidate(handle="opaque:1", label="The Swamp", kind="location"),
                    RetrievalCandidate(handle="opaque:2", label="Edge", kind="location")),
        allowed_operations=("select_candidates", "discover_more", "finish_retrieval"))


def result(**overrides):
    body = dict(answers={"operation": ChoiceDecisionAnswer(selected="select_candidates"),
                         "candidate_0": ChoiceDecisionAnswer(selected="include"),
                         "candidate_1": ChoiceDecisionAnswer(selected="include")},
                observation=InferenceObservation(provider=PROVIDER, resolved_model=MODEL, response_model=MODEL,
                                                 latency_ms=100, retry_count=0, state="completed", provider_attempt_count=1))
    return DecisionResult(**(body | overrides))


def validate(req, selection, **overrides):
    kwargs = dict(expected_request_sha256=req.digest, current_scope_sha256=req.scope_sha256,
                  current_revision=req.revision, current_parent_attempt_id=req.parent_attempt_id)
    return validate_selection(req, selection, **(kwargs | overrides))


def test_one_batch_excludes_host_and_authority_metadata_and_roundtrips():
    req = request()
    assert RetrievalDecisionInput.model_validate_json(req.model_dump_json(by_alias=True)) == req
    prepared = prepare_decision(req)
    assert prepared.provider == PROVIDER and prepared.model == MODEL
    assert prepared.max_transport_retries == 0
    assert len(prepared.questions) == 3
    assert set(prepared.state) == {"question", "candidates"}
    payload = json.dumps(prepared.state)
    for value in (str(req.request_id), str(req.parent_attempt_id), req.scope_sha256, req.revision,
                  "opaque:1", "opaque:2", "Workspace", "system_prompt"):
        assert value not in payload
    selection = decode_selection(req, result())
    assert validate(req, selection) == req.candidates


@pytest.mark.parametrize("field,value", [
    ("current_scope_sha256", "b" * 64), ("current_revision", "graph:2"),
    ("current_parent_attempt_id", uuid4()), ("expected_request_sha256", "c" * 64),
])
def test_stale_parent_scope_revision_or_changed_request_refuses(field, value):
    req = request()
    with pytest.raises(ValueError):
        validate(req, decode_selection(req, result()), **{field: value})


def test_changed_catalog_refuses_even_when_handle_still_matches():
    req = request()
    altered = req.model_copy(update={"candidates": (req.candidates[0].model_copy(update={"label": "different"}), req.candidates[1])})
    with pytest.raises(ValueError):
        validate(altered, decode_selection(req, result()), expected_request_sha256=req.digest)


@pytest.mark.parametrize("handles", [("foreign",), ("opaque:1", "foreign")])
def test_model_cannot_invent_handle(handles):
    req = request()
    with pytest.raises(ValueError):
        validate(req, RetrievalSelection(operation="select_candidates", selected_handles=handles))


@pytest.mark.parametrize("payload", [
    {"operation": "select_candidates", "selected_handles": ["opaque:1", "opaque:1"]},
    {"operation": "select_candidates", "selected_handles": []},
    {"operation": "finish_retrieval", "selected_handles": ["opaque:1"]},
    {"operation": "discover_more", "selected_handles": [], "citation": "made up"},
    {"operation": "select_candidates", "selected_handles": [1]},
])
def test_ambiguous_selection_or_prose_not_admitted(payload):
    with pytest.raises(ValidationError):
        RetrievalSelection.model_validate(payload)


def test_catalog_immutable_and_duplicate_rejected():
    req = request()
    with pytest.raises(ValidationError):
        req.candidates[0].label = "changed"
    with pytest.raises(ValidationError):
        RetrievalDecisionInput.model_validate(req.model_dump(by_alias=True) | {"candidates": [req.candidates[0], req.candidates[0]]})


@pytest.mark.parametrize("mutation", ["missing", "extra", "binary", "bad_choice", "bad_operation"])
def test_wrong_or_incomplete_provider_answers_refused(mutation):
    req = request(); raw = result(); answers = dict(raw.answers)
    if mutation == "missing": answers.pop("candidate_1")
    elif mutation == "extra": answers["invented"] = ChoiceDecisionAnswer(selected="include")
    elif mutation == "binary": answers["candidate_0"] = BinaryDecisionAnswer(value=True, probability_true=1.0)
    elif mutation == "bad_choice": answers["candidate_0"] = ChoiceDecisionAnswer(selected="invented")
    else: answers["operation"] = ChoiceDecisionAnswer(selected="publish")
    with pytest.raises(ValueError):
        decode_selection(req, result(answers=answers))


def test_wrong_provider_or_model_refused():
    for values in ({"provider": "other"}, {"resolved_model": "other"}, {"response_model": None}):
        observation = result().observation.model_copy(update=values)
        with pytest.raises(ValueError):
            decode_selection(request(), result(observation=observation))


def test_explicit_discovery_with_no_candidates():
    req = request().model_copy(update={"candidates": ()})
    assert len(prepare_decision(req).questions) == 1
    raw = result(answers={"operation": ChoiceDecisionAnswer(selected="discover_more")})
    assert validate(req, decode_selection(req, raw)) == ()


@pytest.mark.parametrize("update", [
    {"retry_count": 1}, {"provider_attempt_count": 2}, {"provider_attempt_count": None},
    {"state": "incomplete", "failure_code": "PROVIDER_INCOMPLETE"},
])
def test_nonterminal_unknown_or_retried_result_not_consumed(update):
    observation = InferenceObservation.model_validate(result().observation.model_dump() | update)
    with pytest.raises(ValueError):
        decode_selection(request(), result(observation=observation))


def test_actual_ge_sdk_request_is_checked_before_mock_transport_dispatch():
    import asyncio
    import httpx2
    from generationengine import GenerationClient
    from generationengine.decision_dispatch import DecisionDispatchGate
    from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
    from application_state.agent_conversation.jev_retrieval_contract import validate_prepared_decision
    req = request(); events = []; sent = []
    class Wire(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, wire):
            sent.append(wire)
            body = json.loads(wire.content)
            assert body["state"] == prepare_decision(req).state
            answers = {}
            for name, q in body["questions"].items():
                choice = "select_candidates" if name == "operation" else "include"
                answers[name] = {"type": "choice", "choice": choice, "confidence": 1,
                                "probabilities": {key: float(key == choice) for key in q["criteria"]}}
            return httpx2.Response(200, request=wire, json={"model": MODEL,
                "usage": {"input_tokens": 120, "output_tokens": 10}, "answers": answers})
    async def run():
        async def authorize(prepared):
            validate_prepared_decision(req, prepared)
            events.append("authorized")
            from dataclasses import replace
            from hashlib import sha256
            body = json.loads(prepared.body); body["state"]["question"] = "changed"
            changed = json.dumps(body).encode()
            forged = replace(prepared, body=changed, body_size=len(changed), body_sha256=sha256(changed).hexdigest())
            with pytest.raises(ValueError):
                validate_prepared_decision(req, forged)
            return True
        async def record(event):
            events.append(event.outcome)
            return True
        provider = TypeSafeDecisionProvider(api_key="synthetic-test-key",
            dispatch_gate=DecisionDispatchGate(authorize, record), transport=Wire())
        client = GenerationClient(decision_providers={PROVIDER: provider})
        try:
            actual = await client.decide(prepare_decision(req))
            assert validate(req, decode_selection(req, actual)) == req.candidates
        finally:
            await client.aclose()
    asyncio.run(run())
    assert len(sent) == 1
    assert events == ["authorized", "sending", "response_received"]
