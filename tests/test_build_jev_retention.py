"""Retention is an inspectable heuristic view, not destruction of source evidence."""

import asyncio
import hashlib

import pytest

from apps.live_control_server.services.build_jev_retention import (
    POLICY,
    fits,
    packets,
    packet_questions,
    packet_state,
)
from apps.live_control_server.services.build_jev_transitions import (
    BuildJevTransitions,
    DecisionIntent,
    Disposition,
    ReadAction,
)
from tests.test_build_jev_transitions import SCOPE, answer, unit


def judge(machine, selections=None, scores=None):
    intent = machine.step
    assert isinstance(intent, DecisionIntent) and intent.phase == "retention"
    replies = {}
    for q in intent.questions:
        selected = (selections or {}).get(q.name, "unknown")
        replies[q.name] = {"kind": "choice", "selected": selected}
        if scores is not None:
            replies[q.name]["probabilities"] = scores
    machine.accept_decision(intent.request_id, intent.model, replies)
    return intent, replies


def begin(units):
    action = ReadAction(
        id="a",
        label="Relevant neighborhood",
        kind="graph_observations",
        unit_ids=tuple(u.id for u in units),
    )
    machine = BuildJevTransitions(
        "What governs Harbor?", SCOPE, (action,), retention_policy=POLICY
    )
    answer(machine, next_id="a")
    machine.accept_acquisition({"a": units})
    return machine


@pytest.mark.parametrize(
    "selected,scores,omitted",
    [
        ("irrelevant", {"useful": 0.01, "irrelevant": 0.98, "unknown": 0.01}, True),
        ("irrelevant", {"useful": 0.1, "irrelevant": 0.89, "unknown": 0}, False),
        ("irrelevant", {"useful": 1, "irrelevant": 1, "unknown": 0}, False),
        ("irrelevant", None, False),
        ("unknown", {"useful": 0, "irrelevant": 1, "unknown": 0}, False),
        ("useful", None, False),
    ],
)
def test_only_explicit_high_confidence_irrelevance_is_omitted(
    selected, scores, omitted
):
    original = unit(
        "u", "Aster believes the council rules Harbor, but this is disputed."
    )
    machine = begin((original,))
    intent, replies = judge(machine, {"retain_0": selected}, scores)
    assert len(machine.step.state["evidence"]) == (0 if omitted else 1)
    if scores:
        replies["retain_0"]["probabilities"]["irrelevant"] = 0
    terminal = machine.refuse()
    assert terminal.evidence == (original,)
    row = terminal.retention_judgments[0]
    assert row["omitted"] == omitted and row["request_id"] == intent.request_id
    assert row["content_sha256"] == hashlib.sha256(original.text.encode()).hexdigest()
    assert row["scope_sha256"] and row["question_sha256"]
    if scores:
        assert row["answer"]["probabilities"]["irrelevant"] != 0


def test_unknown_intermediate_hop_and_competing_claim_survive_to_global_conflict():
    originals = (
        unit("hop", "Aster leads the assembly."),
        unit("claim", "The assembly governs Harbor."),
        unit("conflict", "A later source says only the captain governs Harbor."),
    )
    machine = begin(originals)
    judge(machine)
    assert len(machine.step.state["evidence"]) == 3
    end = answer(machine, label="conflict")
    assert end.status == "unresolved_conflict" and end.evidence == originals
    assert all(not j["omitted"] for j in end.retention_judgments)


def test_later_support_choices_cannot_reintroduce_omitted_unit():
    machine = begin((unit("u", "Unrelated story."),))
    judge(
        machine,
        {"retain_0": "irrelevant"},
        {"useful": 0, "irrelevant": 1, "unknown": 0},
    )
    assert "support" not in {q.name for q in machine.step.questions}
    assert answer(machine, label="sufficient").status == "insufficient_evidence"


def test_packets_fit_and_preserve_full_qualified_units_without_clipping():
    originals = tuple(
        unit(f"u{i}", (str(i) + " distinctive passage ") * 180) for i in range(12)
    )
    batches = packets("What governs Harbor?", SCOPE, originals)
    assert len(batches) > 1
    assert tuple(u for batch in batches for u in batch) == originals
    for batch in batches:
        state = packet_state("What governs Harbor?", SCOPE, batch)
        assert fits(state, packet_questions(batch))
        assert state["unit_hashes"] == {u.id: u.content_sha256 for u in batch}
    machine = begin(originals)
    seen = set()
    while (
        isinstance(machine.step, DecisionIntent) and machine.step.phase == "retention"
    ):
        assert machine.step.request_id not in seen
        seen.add(machine.step.request_id)
        judge(machine)
    assert isinstance(machine.step, Disposition)
    assert machine.step.reason == "retained_view_exceeds_context_policy"
    assert machine.step.evidence == originals
    assert len(machine.step.retention_judgments) == len(originals)


def test_oversized_single_unit_refuses_preserving_original_proof():
    original = unit("u", "X" * 33000)
    machine = begin((original,))
    assert machine.step.reason == "single_unit_exceeds_context_policy"
    assert machine.step.evidence == (original,)


@pytest.mark.parametrize("fault", ["request", "model", "keys", "distribution"])
def test_retention_replies_are_bound_and_malformed_reply_is_terminal(fault):
    machine = begin((unit("u", "The assembly governs Harbor."),))
    intent = machine.step
    replies = {"retain_0": {"kind": "choice", "selected": "unknown"}}
    request, model = intent.request_id, intent.model
    if fault == "request":
        request = "another"
    if fault == "model":
        model = "another"
    if fault == "keys":
        replies = {}
    if fault == "distribution":
        replies["retain_0"]["probabilities"] = {"unknown": float("nan")}
    with pytest.raises(ValueError):
        machine.accept_decision(request, model, replies)
    assert machine.step.status == "refused"
    assert not machine.step.retention_judgments


def test_completed_retention_request_cannot_replay_after_view_advances():
    machine = begin((unit("u", "The assembly governs Harbor."),))
    intent, replies = judge(machine)
    with pytest.raises(ValueError, match="differs"):
        machine.accept_decision(intent.request_id, intent.model, replies)
    assert machine.step.status == "refused"


def test_scope_and_question_change_packet_identity():
    original = unit("u", "The assembly governs Harbor.")
    state = packet_state("Who governs?", SCOPE, (original,))
    assert state != packet_state("Who opposes?", SCOPE, (original,))
    with pytest.raises(ValueError):
        packet_state(
            "Who governs?", SCOPE.model_copy(update={"world_id": "other"}), (original,)
        )


def test_actual_sdk_serializes_retention_packet_without_authorizing_transport():
    from generationengine import GenerationClient, GenerationEngineError
    from generationengine.types import DecisionRequest
    from generationengine.decision_dispatch import DecisionDispatchGate
    from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
    from apps.live_control_server.services.build_jev_dispatch import validate_body

    machine = begin(
        tuple(unit(f"u{i}", (str(i) + " source passage ") * 250) for i in range(8))
    )
    intent = machine.step
    seen = []

    async def authorize(prepared):
        seen.append(validate_body(prepared.body.decode(), intent.state))
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
                        model=intent.model,
                        state=intent.state,
                        questions=[q.model_dump() for q in intent.questions],
                        max_transport_retries=0,
                    )
                )
        finally:
            await client.aclose()

    asyncio.run(run())
    assert len(seen) == 1 and seen[0]["state"] == intent.state
