"""Provider fold parity against the frozen pre-refactor test-only oracle."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.types import (
    ProviderAttemptAuthorizedEventV1, ProviderAttemptAuthorizedEventV5,
    ProviderOutcomeEventV1, CompletionBindingEventV1,
)
from application_state.agent_conversation.provider_execution import (
    _ProviderState, _advance, validate,
)
from tests.test_surface_native_context import provider_ledger, controller_writer_ledger

# Original predicate at f6e174e40; only test-relative imports are qualified.
# TEST ONLY, not a runtime fallback.
def _original_validate(execution) -> None:
    """Validate the actual typed record; never project native events to V1."""
    policy, events = execution.policy, execution.events
    if [event.sequence for event in events] != list(range(len(events))):
        raise ValueError("Graph execution events must have contiguous sequence numbers")
    if len({event.event_id for event in events}) != len(events):
        raise ValueError("Graph execution event IDs must be unique")
    attempts: dict[UUID, ProviderAttemptAuthorizedEventV1] = {}
    outcomes: dict[UUID, list[str]] = {}
    completion_bindings = 0
    for event in events:
        if isinstance(event, ProviderAttemptAuthorizedEventV1):
            if event.provider_attempt_id in attempts:
                raise ValueError("provider attempt ID was authorized more than once")
            if attempts:
                latest_attempt_id = next(reversed(attempts))
                prior_outcomes = outcomes[latest_attempt_id]
                if not prior_outcomes or prior_outcomes[-1] not in {"response_received", "known_not_sent"}:
                    raise ValueError("a new provider attempt requires a resolved prior attempt")
            if isinstance(event, ProviderAttemptAuthorizedEventV5):
                from application_state.agent_conversation.build_decision_context import validate_event
                validate_event(event, execution)
            from application_state.agent_conversation.build_decision_context import uses_role_accounting
            if uses_role_accounting(policy):
                from application_state.agent_conversation.build_decision_context import validate_accounting
                validate_accounting(event, execution, provider_index=len(attempts))
            elif (event.input_accounting_kind != policy.provider_input_accounting.kind
                    or event.input_estimator != policy.provider_input_accounting.estimator):
                raise ValueError("provider attempt accounting differs from accepted policy")
            attempts[event.provider_attempt_id] = event
            outcomes[event.provider_attempt_id] = []
        elif isinstance(event, ProviderOutcomeEventV1):
            if event.provider_attempt_id not in attempts:
                raise ValueError("provider outcome requires a prior authorization")
            prior = outcomes[event.provider_attempt_id]
            if event.outcome == "sdk_entered" and prior:
                raise ValueError("SDK entry must be the first provider outcome")
            if event.outcome == "known_not_sent" and prior:
                raise ValueError("known-not-sent must be recorded before SDK entry")
            if event.outcome not in {"sdk_entered", "known_not_sent", "outcome_unknown"} and not prior:
                raise ValueError("provider outcome requires observed SDK entry")
            if prior and prior[-1] in {"response_received", "known_not_sent", "outcome_unknown"}:
                raise ValueError("provider attempt already has a terminal outcome")
            prior.append(event.outcome)
        elif isinstance(event, CompletionBindingEventV1):
            completion_bindings += 1
            if completion_bindings > 1 or event.sequence != len(events) - 1:
                raise ValueError("completion binding must be unique and the final execution event")
            if event.provider_attempt_id not in attempts or outcomes[event.provider_attempt_id][-1:] != ["response_received"]:
                raise ValueError("completion binding requires a response-received attempt")
    if policy.max_provider_attempts is not None and len(attempts) > policy.max_provider_attempts:
        raise ValueError("provider attempt policy limit exceeded")
    input_total = sum(event.input_tokens for event in attempts.values())
    output_total = sum(event.output_token_reserve for event in attempts.values())
    if (
        policy.max_total_provider_input_tokens is not None
        and input_total > policy.max_total_provider_input_tokens
    ) or (
        policy.max_total_provider_output_tokens is not None
        and output_total > policy.max_total_provider_output_tokens
    ):
        raise ValueError("provider token budget exceeded")



def judgment(check, execution):
    try:
        check(execution)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return type(exc).__name__, str(exc)
    return "PASS", None


@pytest.mark.parametrize("factory", [provider_ledger, controller_writer_ledger])
def test_every_valid_prefix_and_grouping_replays_the_same_fold(factory):
    ledger = factory()
    original = deepcopy(ledger)
    for size in range(len(ledger.events) + 1):
        prefix = SimpleNamespace(policy=ledger.policy, events=ledger.events[:size])
        assert judgment(validate, prefix) == judgment(_original_validate, prefix) == ("PASS", None)
        expected = _advance(_ProviderState(), prefix, prefix.events)
        # Every partition of this retained short lifecycle, not just singletons.
        for mask in range(1 << max(0, size - 1)):
            state = _ProviderState()
            start = 0
            for end in range(1, size + 1):
                if end == size or mask & (1 << (end - 1)):
                    state = _advance(state, prefix, prefix.events[start:end])
                    start = end
            assert state == expected
    assert ledger.policy == original.policy
    assert ledger.events == original.events


def test_group_failure_does_not_mutate_the_previously_accepted_provider_indexes():
    ledger = provider_ledger()
    prior = _advance(_ProviderState(), ledger, ledger.events[:2])
    before = deepcopy(prior)
    bad = ledger.events[2].model_copy(update={"outcome": "response_received"})
    with pytest.raises(ValueError, match="observed SDK entry"):
        _advance(prior, ledger, [bad])
    assert prior == before
    with pytest.raises(FrozenInstanceError):
        prior.event_count = 200
    assert isinstance(prior.event_ids, frozenset)
    assert all(isinstance(identity, UUID) and type(seen) is bool
               and (outcome is None or type(outcome) is str)
               for identity, seen, outcome in prior.attempts)


@pytest.mark.parametrize("mutation", [
    "sequence", "duplicate_id", "duplicate_attempt", "outcome_before_authorization",
    "sdk_twice", "known_not_sent_after_sdk", "response_before_sdk", "after_terminal",
    "unresolved_next_attempt", "completion_not_final", "completion_no_response",
    "attempt_budget", "input_budget", "output_budget", "accounting",
    "header_error_has_priority", "unknown_without_sdk", "known_not_sent_without_sdk",
])
def test_negative_history_parity_and_original_error_priority(mutation):
    ledger = provider_ledger()
    if mutation == "sequence":
        ledger.events[-1] = ledger.events[-1].model_copy(update={"sequence": 100})
    elif mutation == "duplicate_id":
        ledger.events[-1] = ledger.events[-1].model_copy(update={"event_id": ledger.events[0].event_id})
    elif mutation == "duplicate_attempt":
        ledger.events[-1] = ledger.events[1].model_copy(update={"sequence": 4, "event_id": uuid4()})
    elif mutation == "outcome_before_authorization":
        ledger.events[2] = ledger.events[2].model_copy(update={"provider_attempt_id": uuid4()})
    elif mutation == "sdk_twice":
        ledger.events[3] = ledger.events[3].model_copy(update={"outcome": "sdk_entered"})
    elif mutation == "known_not_sent_after_sdk":
        ledger.events[3] = ledger.events[3].model_copy(update={"outcome": "known_not_sent"})
    elif mutation in {"response_before_sdk", "header_error_has_priority"}:
        ledger.events[2] = ledger.events[2].model_copy(update={"outcome": "response_received"})
        if mutation == "header_error_has_priority":
            ledger.events[-1] = ledger.events[-1].model_copy(update={"sequence": 50})
    elif mutation == "after_terminal":
        ledger.events[-1] = ledger.events[3].model_copy(update={"sequence": 4, "event_id": uuid4()})
    elif mutation == "unresolved_next_attempt":
        ledger.events[2] = ledger.events[1].model_copy(update={"sequence": 2, "event_id": uuid4(),
            "provider_attempt_id": uuid4()})
    elif mutation == "completion_not_final":
        ledger.events.append(ledger.events[0].model_copy(update={"sequence": 5, "event_id": uuid4()}))
    elif mutation == "completion_no_response":
        ledger.events[-1] = ledger.events[-1].model_copy(update={"provider_attempt_id": uuid4()})
    elif mutation == "attempt_budget":
        ledger.policy.max_provider_attempts = 0
    elif mutation == "input_budget":
        ledger.policy.max_total_provider_input_tokens = 11
    elif mutation == "output_budget":
        ledger.policy.max_total_provider_output_tokens = 9
    elif mutation == "accounting":
        ledger.events[1] = ledger.events[1].model_copy(update={"input_estimator": "unaccepted"})
    elif mutation in {"unknown_without_sdk", "known_not_sent_without_sdk"}:
        ledger.events = ledger.events[:2] + [ledger.events[2].model_copy(update={
            "outcome": "outcome_unknown" if mutation == "unknown_without_sdk" else "known_not_sent"})]
    before = deepcopy(ledger)
    result = judgment(validate, ledger)
    assert result == judgment(_original_validate, ledger)
    assert (result[0] == "PASS") == (mutation in {"unknown_without_sdk", "known_not_sent_without_sdk"})
    assert ledger.policy == before.policy and ledger.events == before.events


def test_seeded_negative_and_partial_histories_match_frozen_provider_predicate():
    import random
    randomizer = random.Random(20261109)
    for _ in range(400):
        ledger = controller_writer_ledger()
        ledger.events = ledger.events[:randomizer.randrange(len(ledger.events) + 1)]
        if ledger.events:
            index = randomizer.randrange(len(ledger.events))
            event = ledger.events[index]
            change = randomizer.choice(["sequence", "event_id", "provider_attempt_id", "outcome", "budget", "input_type", "output_type"])
            if change == "sequence":
                ledger.events[index] = event.model_copy(update={"sequence": randomizer.randrange(9)})
            elif change == "event_id":
                ledger.events[index] = event.model_copy(update={"event_id": ledger.events[0].event_id})
            elif change == "provider_attempt_id" and hasattr(event, "provider_attempt_id"):
                ledger.events[index] = event.model_copy(update={"provider_attempt_id": uuid4()})
            elif change in {"input_type", "output_type"} and isinstance(event, t.ProviderAttemptAuthorizedEventV1):
                ledger.events[index] = event.model_copy(update={
                    "input_tokens" if change == "input_type" else "output_token_reserve": "bad"})
            elif change == "outcome" and isinstance(event, t.ProviderOutcomeEventV1):
                ledger.events[index] = event.model_copy(update={"outcome": randomizer.choice([
                    "sdk_entered", "response_received", "known_not_sent", "outcome_unknown", None, ""])})
            else:
                ledger.policy.max_total_provider_input_tokens = randomizer.choice([None, 0, 12, 24])
        assert judgment(validate, ledger) == judgment(_original_validate, ledger)


def test_completion_is_terminal_even_when_a_later_group_contains_only_nonprovider_events():
    ledger = provider_ledger()
    state = _advance(_ProviderState(), ledger, ledger.events)
    later = ledger.events[0].model_copy(update={"sequence": 5, "event_id": uuid4()})
    with pytest.raises(ValueError, match="unique and the final"):
        _advance(state, ledger, [later])


@pytest.mark.parametrize("semantic", [False, True])
def test_concrete_native_build_dispatch_and_role_accounting_remain_at_their_owner(semantic):
    from tests.test_surface_native_execution import component, controller, outcomes
    _, record = component("build", unavailable=True)
    first = controller("build", record.policy, semantic=semantic)
    second = controller("build", record.policy, sequence=3, semantic=not semantic)
    ledger = SimpleNamespace(policy=record.policy, events=[first, *outcomes(first, 1), second])
    assert judgment(validate, ledger) == judgment(_original_validate, ledger) == ("PASS", None)
    for index in (0, 3):
        bad = deepcopy(ledger)
        bad.events[index] = bad.events[index].model_copy(update={"input_estimator": "foreign-counter"})
        result = judgment(validate, bad)
        assert result == judgment(_original_validate, bad)
        assert result[0] == "ValueError"
    # Current concrete Build policies still reject a writer/foreign role in the
    # controller position; the fold does not reinterpret it as generic accounting.
    bad = deepcopy(ledger)
    bad.events[0] = first.model_copy(update={"provider": "foreign"})
    assert judgment(validate, bad) == judgment(_original_validate, bad)
    assert judgment(validate, bad)[0] == "ValueError"


def test_mutated_none_outcome_cannot_erase_observed_sdk_entry():
    ledger = provider_ledger()
    ledger.events = ledger.events[:3] + [
        ledger.events[3].model_copy(update={"sequence": 3, "outcome": None}),
        ledger.events[2].model_copy(update={"sequence": 4, "event_id": uuid4()}),
    ]
    expected = ("ValueError", "SDK entry must be the first provider outcome")
    assert judgment(validate, ledger) == judgment(_original_validate, ledger) == expected
    state = _advance(_ProviderState(), ledger, ledger.events[:4])
    assert state.attempts[-1][1:] == (True, None)
    with pytest.raises(ValueError, match="SDK entry must be the first"):
        _advance(state, ledger, ledger.events[4:])


def test_structural_failure_precedes_mutated_numeric_arithmetic():
    ledger = provider_ledger()
    first = ledger.events[1].model_copy(update={"input_tokens": "bad"})
    next_attempt = first.model_copy(update={"sequence": 2, "event_id": uuid4(),
        "provider_attempt_id": uuid4()})
    ledger.events = [ledger.events[0], first, next_attempt]
    expected = ("ValueError", "a new provider attempt requires a resolved prior attempt")
    assert judgment(validate, ledger) == judgment(_original_validate, ledger) == expected
    ledger.events = [ledger.events[0], first]
    ledger.policy.max_provider_attempts = 0
    expected = ("ValueError", "provider attempt policy limit exceeded")
    assert judgment(validate, ledger) == judgment(_original_validate, ledger) == expected
    ledger.policy.max_provider_attempts = 1
    assert judgment(validate, ledger) == judgment(_original_validate, ledger)
    assert judgment(validate, ledger)[0] == "TypeError"
