"""One provider lifecycle fold, shared by replay and grouped transition checks.

This owns provider sequencing/accounting only. A fold is NOT an accepted native
execution, a capability, a stored-state witness or authorization to issue IO.
Context, source, producer, current DB and mutable-command validation stay with
those owners. No mutable policy/event model is retained in the fold's indexes.
"""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class _ProviderState:
    event_count: int = 0
    event_ids: frozenset[UUID] = frozenset()
    # In insertion order: identity, whether any outcome was seen, latest outcome.
    # Presence is separate: a mutated typed model can contain outcome=None, which
    # must not turn a nonempty observed history back into an empty one.
    attempts: tuple[tuple[UUID, bool, str | None], ...] = ()
    input_total: int = 0
    output_total: int = 0
    completed: bool = False


def _advance(state, execution, events):
    """Fold one atomic group; this is not an authority-bearing append API.

    The caller supplies its actual execution to the existing Build accounting
    owners. Structural transitions finish before aggregate group checks.
    Immutable indexes describe the provider predicate only, not every invariant
    of a valid native prefix. They must never replace APP's locked-row admission.
    """
    from . import types as t

    events = tuple(events)
    end = state.event_count + len(events)
    if [event.sequence for event in events] != list(range(state.event_count, end)):
        raise ValueError("Graph execution events must have contiguous sequence numbers")
    ids = frozenset(event.event_id for event in events)
    if len(ids) != len(events) or state.event_ids.intersection(ids):
        raise ValueError("Graph execution event IDs must be unique")
    if events and state.completed:
        raise ValueError("completion binding must be unique and the final execution event")
    attempts = {identity: (seen, outcome) for identity, seen, outcome in state.attempts}
    new_inputs, new_outputs = [], []
    completed = state.completed
    for event in events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            if event.provider_attempt_id in attempts:
                raise ValueError("provider attempt ID was authorized more than once")
            if attempts and next(reversed(attempts.values()))[1] not in {"response_received", "known_not_sent"}:
                raise ValueError("a new provider attempt requires a resolved prior attempt")
            if isinstance(event, t.ProviderAttemptAuthorizedEventV5):
                from .build_decision_context import validate_event
                validate_event(event, execution)
            from .build_decision_context import uses_role_accounting
            if uses_role_accounting(execution.policy):
                from .build_decision_context import validate_accounting
                validate_accounting(event, execution, provider_index=len(attempts))
            elif (event.input_accounting_kind != execution.policy.provider_input_accounting.kind
                    or event.input_estimator != execution.policy.provider_input_accounting.estimator):
                raise ValueError("provider attempt accounting differs from accepted policy")
            attempts[event.provider_attempt_id] = (False, None)
            # Defer arithmetic until structural checks finish. A mutable typed
            # event can contain malformed numeric data; the original owner
            # reports lifecycle/attempt-limit errors before aggregate type errors.
            new_inputs.append(event.input_tokens)
            new_outputs.append(event.output_token_reserve)
        elif isinstance(event, t.ProviderOutcomeEventV1):
            if event.provider_attempt_id not in attempts:
                raise ValueError("provider outcome requires a prior authorization")
            seen, prior = attempts[event.provider_attempt_id]
            if event.outcome == "sdk_entered" and seen:
                raise ValueError("SDK entry must be the first provider outcome")
            if event.outcome == "known_not_sent" and seen:
                raise ValueError("known-not-sent must be recorded before SDK entry")
            if event.outcome not in {"sdk_entered", "known_not_sent", "outcome_unknown"} and not seen:
                raise ValueError("provider outcome requires observed SDK entry")
            if prior in {"response_received", "known_not_sent", "outcome_unknown"}:
                raise ValueError("provider attempt already has a terminal outcome")
            attempts[event.provider_attempt_id] = (True, event.outcome)
        elif isinstance(event, t.CompletionBindingEventV1):
            if completed or event.sequence != end - 1:
                raise ValueError("completion binding must be unique and the final execution event")
            if attempts.get(event.provider_attempt_id) != (True, "response_received"):
                raise ValueError("completion binding requires a response-received attempt")
            completed = True
    policy = execution.policy
    if policy.max_provider_attempts is not None and len(attempts) > policy.max_provider_attempts:
        raise ValueError("provider attempt policy limit exceeded")
    input_total = state.input_total + sum(new_inputs)
    output_total = state.output_total + sum(new_outputs)
    if (policy.max_total_provider_input_tokens is not None
            and input_total > policy.max_total_provider_input_tokens
            or policy.max_total_provider_output_tokens is not None
            and output_total > policy.max_total_provider_output_tokens):
        raise ValueError("provider token budget exceeded")
    return _ProviderState(event_count=end, event_ids=state.event_ids | ids,
        attempts=tuple((identity, seen, outcome) for identity, (seen, outcome) in attempts.items()),
        input_total=input_total, output_total=output_total, completed=completed)


def validate(execution):
    """Full recovery uses the same grouped transition implementation."""
    _advance(_ProviderState(), execution, execution.events)
