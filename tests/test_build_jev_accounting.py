"""Explicit estimate evaluation; never an asserted Jev tokenizer guarantee."""

import asyncio
import json
import os
from pathlib import Path

import pytest

from apps.live_control_server.services.build_jev_accounting import (
    DecisionCapacityError,
    ExperimentalAccounting,
    RAW_WIRE_LIMIT,
)
from apps.live_control_server.services.build_jev_dispatch import MODEL, validate_body
from apps.live_control_server.services.build_jev_transitions import (
    BuildJevTransitions,
    DecisionIntent,
)
from tests.test_build_jev_transitions import SCOPE, actions, answer, unit


@pytest.fixture
def accounting(monkeypatch):
    # Use the same verified offline preparation as serving; never an ambient cache.
    pytest.importorskip("tiktoken")
    from importlib import import_module

    load = import_module("tiktoken.load")

    def no_download(*args, **kwargs):
        raise ValueError("offline tokenizer asset missing")

    monkeypatch.setattr(load, "read_file", no_download)
    configured = os.environ.get("DMB_TEST_JEV_TOKENIZER_FILE", "")
    if not configured:
        pytest.skip("Configure the verified offline tokenizer asset for conformance")
    from apps.live_control_server.services.build_jev_runtime import load_offline_accounting
    return load_offline_accounting(Path(configured))


def body_for(policy, text="Short source.", questions=None):
    state = {"context_accounting": policy.descriptor, "text": text}
    body = {
        "model": MODEL,
        "state": state,
        "questions": questions
        or {"q": {"type": "noul", "instructions": "Is the text relevant?"}},
    }
    return json.dumps(body, ensure_ascii=False), state


@pytest.mark.parametrize(
    "text",
    [
        "🐐 café 中文 Ελληνικά " * 100,
        '\\u0000 \\n "quoted" \\"escaped"' * 100,
        "012345678901234567890123456789 " * 100,
        "def fun(x):\n    return {'id': x + 1}\n" * 100,
        "<|endoftext|> <|fim_suffix|> " * 100,
    ],
    ids=["unicode", "escaped-json", "digits", "code", "special-like-text"],
)
def test_adversarial_content_counted_without_normalization(accounting, text):
    raw, state = body_for(accounting, text)
    decoded = validate_body(raw, state, accounting=accounting)
    assert decoded["state"]["text"] == text
    assert accounting.estimate(decoded) >= 4096


def test_full_question_and_full_request_independent_limits():
    policy = ExperimentalAccounting("synthetic-test", lambda text: len(text))
    raw, state = body_for(policy, "x" * 15000)
    with pytest.raises(DecisionCapacityError, match="per-question") as refusal:
        validate_body(raw, state, accounting=policy)
    assert refusal.value.code == "decision_question_capacity_exceeded"
    questions = {
        f"q{i}": {"type": "noul", "instructions": "x" * 900} for i in range(35)
    }
    raw, state = body_for(policy, questions=questions)
    with pytest.raises(DecisionCapacityError, match="request context") as refusal:
        validate_body(raw, state, accounting=policy)
    assert refusal.value.code == "decision_request_capacity_exceeded"


def test_raw_wire_bound_precedes_tokenizer_and_is_separate():
    def forbidden(text):
        raise AssertionError("must not tokenize oversized raw wire")

    policy = ExperimentalAccounting("synthetic-test", forbidden)
    raw, state = body_for(policy, "x" * RAW_WIRE_LIMIT)
    with pytest.raises(DecisionCapacityError, match="raw wire") as refusal:
        validate_body(raw, state, accounting=policy)
    assert refusal.value.code == "decision_wire_capacity_exceeded"


def test_explicit_policy_and_exact_state_required(accounting):
    raw, state = body_for(accounting)
    state["context_accounting"]["reserve"] = 0
    raw = json.dumps(
        {"model": MODEL, "state": state, "questions": {"q": {"type": "noul"}}}
    )
    with pytest.raises(ValueError, match="descriptor"):
        validate_body(raw, state, accounting=accounting)
    with pytest.raises(ValueError, match="differs"):
        validate_body(raw, {}, accounting=accounting)


@pytest.mark.parametrize("count", [None, -1, True, 1.1])
def test_invalid_tokenizer_fails_closed(count):
    policy = ExperimentalAccounting("synthetic-test", lambda text: count)
    raw, state = body_for(policy)
    with pytest.raises(ValueError, match="tokenizer count"):
        validate_body(raw, state, accounting=policy)


def test_missing_tokenizer_cannot_fall_back_or_download():
    with pytest.raises(ValueError, match="required"):
        ExperimentalAccounting("", lambda text: 1)

    def absent(text):
        raise ValueError("offline tokenizer unavailable")

    policy = ExperimentalAccounting("synthetic-test", absent)
    raw, state = body_for(policy)
    with pytest.raises(ValueError, match="unavailable"):
        validate_body(raw, state, accounting=policy)


def test_opt_in_changes_identity_and_keeps_legacy_gate(accounting):
    legacy = BuildJevTransitions(
        "What governs Harbor?",
        SCOPE,
        actions("Assembly"),
        retention_policy="question_relevance_packets_v1",
    )
    machine = BuildJevTransitions(
        "What governs Harbor?",
        SCOPE,
        actions("Assembly"),
        retention_policy="question_relevance_packets_v1",
        accounting=accounting,
    )
    assert legacy.step.request_id != machine.step.request_id
    assert "context_accounting" not in legacy.step.state
    assert machine.step.state["context_accounting"] == accounting.descriptor
    raw, state = body_for(accounting, "Full qualified source. " * 2500)
    with pytest.raises(ValueError, match="conservative ceiling"):
        validate_body(raw, state)
    validate_body(raw, state, accounting=accounting)
    with pytest.raises(ValueError, match="explicit retention"):
        BuildJevTransitions("Question?", SCOPE, actions("A"), accounting=accounting)


def test_actual_sdk_body_admitted_without_transport(accounting):
    from generationengine import GenerationClient, GenerationEngineError
    from generationengine.types import DecisionRequest
    from generationengine.decision_dispatch import DecisionDispatchGate
    from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider

    machine = BuildJevTransitions(
        "What governs Harbor?",
        SCOPE,
        actions("Assembly"),
        retention_policy="question_relevance_packets_v1",
        accounting=accounting,
    )
    answer(machine, next_id="a0")
    machine.accept_acquisition(
        {"a0": (unit("u0", "The assembly governs Harbor. " * 1600),)}
    )
    intent = machine.step
    assert isinstance(intent, DecisionIntent) and intent.phase == "retention"
    seen = []

    async def authorize(prepared):
        seen.append(
            validate_body(prepared.body.decode(), intent.state, accounting=accounting)
        )
        return False

    async def lifecycle(event):
        return True

    async def run():
        provider = TypeSafeDecisionProvider(
            api_key="synthetic-not-a-credential",
            dispatch_gate=DecisionDispatchGate(authorize, lifecycle),
        )
        client = GenerationClient(decision_providers={"typesafe": provider})
        try:
            with pytest.raises(GenerationEngineError):
                await client.decide(
                    DecisionRequest(
                        provider="typesafe",
                        model=MODEL,
                        state=intent.state,
                        questions=[q.model_dump() for q in intent.questions],
                        max_transport_retries=0,
                    )
                )
        finally:
            await client.aclose()

    asyncio.run(run())
    assert len(seen) == 1 and seen[0]["state"] == intent.state


def test_shared_preflight_counts_sdk_null_criteria_at_real_dispatch_boundary():
    from generationengine import GenerationClient, GenerationEngineError
    from generationengine.types import DecisionRequest
    from generationengine.decision_dispatch import DecisionDispatchGate
    from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
    from apps.live_control_server.services.build_jev_retention import fits
    from apps.live_control_server.services.build_jev_transitions import DecisionQuestion

    policy = ExperimentalAccounting("synthetic-character-counter", len)
    state = {"context_accounting": policy.descriptor}
    question = DecisionQuestion(
        name="support",
        kind="choice",
        question="Choose support.",
        options=tuple(f"evidence_{i:03}_" + "x" * 68 for i in range(100)),
    )
    assert fits(state, (question,), accounting=policy)
    seen = []

    async def authorize(prepared):
        body = validate_body(prepared.body.decode(), state, accounting=policy)
        assert all(v is None for v in body["questions"]["support"]["criteria"].values())
        seen.append(body)
        # The previous duplicate-description projection falsely refused the same options.
        body["questions"]["support"]["criteria"] = {o: o for o in question.options}
        with pytest.raises(ValueError, match="per-question"):
            validate_body(json.dumps(body), state, accounting=policy)
        return False

    async def lifecycle(event):
        return True

    async def run():
        provider = TypeSafeDecisionProvider(
            api_key="synthetic-not-a-credential",
            dispatch_gate=DecisionDispatchGate(authorize, lifecycle),
        )
        client = GenerationClient(decision_providers={"typesafe": provider})
        try:
            with pytest.raises(GenerationEngineError):
                await client.decide(
                    DecisionRequest(
                        provider="typesafe",
                        model=MODEL,
                        state=state,
                        questions=[question.model_dump()],
                        max_transport_retries=0,
                    )
                )
        finally:
            await client.aclose()

    asyncio.run(run())
    assert len(seen) == 1
