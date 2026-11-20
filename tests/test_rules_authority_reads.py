"""Mixed completed bodies do not impersonate existing base-domain Turns."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import types as t
from application_state.agent_conversation.rules_authority_reads import (
    MixedCompletedTurnV1,
)
from application_state.agent_conversation.rules_authority_types import canonical_sha256
from tests.test_rules_authority_types import binding
from tests.application_state.test_build_graph_turns import _submission, _completion
from tests.application_state.test_agent_conversation_postgres import (
    _provider_authorization_event,
)


def mixed_absent():
    accepted, _, answer = binding(False)
    now = datetime.now(UTC)
    envelope = dict(
        turn_id=accepted.turn_id,
        conversation_id=accepted.conversation_id,
        world_id=accepted.world_id,
        idempotency_key=uuid4(),
        sequence=1,
        revision=accepted.accepted_turn_revision,
        status="completed",
        user_text="What does the rule say?",
        failure_code=None,
        provenance=t.TurnProvenance(
            world_id=accepted.world_id,
            surface_resolution="resolved",
            surface_id="index",
            surface_instance_id="rules-test",
            primary_work=t.HistoricalReference(resolution="absent"),
            supporting_work=[],
            selected_object=t.HistoricalReference(resolution="absent"),
        ),
        submitted_intent_fingerprint_v1="a" * 64,
        submitted_intent_fingerprint_v2=None,
        play_context_receipt=None,
        attempt=accepted.product_attempt,
        claim_expires_at=None,
        accepted_at=now,
        completed_at=now,
        updated_at=now,
    )
    return MixedCompletedTurnV1(
        schema="dmb_mixed_completed_turn_v1",
        envelope=envelope,
        assistant_text=answer,
        accepted_binding=accepted,
        accepted_binding_sha256=canonical_sha256(accepted),
        base_projection={"kind": "absent"},
    )


def mutate(model, change):
    raw = model.model_dump(mode="json", by_alias=True)
    change(raw)
    return MixedCompletedTurnV1.model_validate_json(json.dumps(raw))


def test_rules_only_read_has_no_fake_base_turn_or_graph_completion():
    mixed = mixed_absent()
    assert mixed.base_projection.kind == "absent"
    assert not mixed.accepted_binding.graph_used
    assert "graph_context_receipt" not in type(mixed.envelope).model_fields
    assert (
        MixedCompletedTurnV1.model_validate_json(mixed.model_dump_json(by_alias=True))
        == mixed
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["envelope"].update(status="running"),
        lambda d: d["envelope"].update(completed_at=None),
        lambda d: d["envelope"].update(attempt=2),
        lambda d: d["envelope"].update(revision=99),
        lambda d: d["envelope"].update(world_id="other"),
        lambda d: d["envelope"].update(conversation_id=str(uuid4())),
        lambda d: d["envelope"].update(submitted_intent_fingerprint_v2="b" * 64),
        lambda d: d["envelope"].update(graph_context_receipt={}),
        lambda d: d.update(assistant_text="altered source claim"),
        lambda d: d.update(accepted_binding_sha256="f" * 64),
        lambda d: d["base_projection"].update(kind="unclaimed"),
        lambda d: d["base_projection"].update(completion={}),
    ],
)
def test_read_rejects_marker_owner_lifecycle_and_seal_corruption(change):
    with pytest.raises(ValidationError):
        mutate(mixed_absent(), change)


def build_projection(approved):
    original = mixed_absent()
    submission = _submission(original.envelope.conversation_id)
    producer = uuid4()
    auth = _provider_authorization_event(attempt_id=producer, sequence=0)
    auth = t.ProviderAttemptAuthorizedEventV2.model_validate(
        auth.model_dump(mode="python")
        | {
            "kind": "provider_attempt_authorized_v2",
            "included_source_read_event_ids": [],
        }
    )
    outcome = t.ProviderOutcomeEventV1(
        event_id=uuid4(),
        sequence=2,
        kind="provider_outcome",
        provider_attempt_id=producer,
        outcome="response_received",
    )
    events = [
        auth,
        t.ProviderOutcomeEventV1(
            event_id=uuid4(),
            sequence=1,
            kind="provider_outcome",
            provider_attempt_id=producer,
            outcome="sdk_entered",
        ),
        outcome,
    ]
    completion = _completion(submission)
    if approved:
        events.append(
            t.CompletionBindingEventV1(
                event_id=uuid4(),
                sequence=3,
                kind="completion_binding",
                provider_attempt_id=producer,
                completion_sha256=t._canonical_sha256(
                    completion.model_dump(mode="json", by_alias=True)
                ),
                claim_graph_event_ids={},
            )
        )
    execution = type(submission.graph_context_execution).model_validate(
        submission.graph_context_execution.model_dump(mode="python", by_alias=True)
        | {"events": events}
    )
    env = original.envelope.model_dump(mode="python", by_alias=True)
    env.update(
        world_id=submission.world_id,
        provenance=submission.provenance,
        submitted_intent_fingerprint_v1=None,
        submitted_intent_fingerprint_v2="c" * 64,
    )
    accepted = original.accepted_binding.model_dump(mode="json", by_alias=True)
    accepted.update(
        world_id=submission.world_id,
        producing_provider_attempt_id=producer,
        request_envelope_sha256=auth.envelope_sha256,
    )
    if approved:
        # Build's existing validator sees only its exact saved-source answer.
        base = "\n".join(segment.text for segment in completion.answer_segments)
        turn = t.Turn(
            **env,
            assistant_text=base,
            completion=completion,
            graph_context_receipt=submission.graph_context_receipt,
            graph_context_execution=execution,
        )
        answer = base + "\n" + original.assistant_text
        raw = original.accepted_binding.model_dump(mode="json", by_alias=True)
        first = dict(
            ordinal=0,
            domain="base",
            text_start=0,
            text_end=len(base),
            base_segment_index=0,
            rules_claim_id=None,
            rules_context_id=None,
            category=None,
            support_refs=[],
        )
        shifted = [
            dict(
                item,
                ordinal=item["ordinal"] + 1,
                text_start=item["text_start"] + len(base) + 1,
                text_end=item["text_end"] + len(base) + 1,
            )
            for item in raw["segment_map"]
        ]
        accepted.update(
            base_disposition="approved",
            base_text_sha256=sha256(base.encode()).hexdigest(),
            assistant_text_sha256=sha256(answer.encode()).hexdigest(),
            segment_map=[first, *shifted],
        )
        projection = {"kind": "approved", "turn": turn}
    else:
        answer = original.assistant_text
        accepted["base_disposition"] = "unclaimed"
        projection = {
            "kind": "unclaimed",
            "graph_context_receipt": submission.graph_context_receipt,
            "graph_context_execution": execution,
        }
    from application_state.agent_conversation.rules_authority_types import (
        RulesAcceptedBindingV1,
    )

    accepted = RulesAcceptedBindingV1.model_validate_json(
        json.dumps(accepted, default=str)
    )
    return MixedCompletedTurnV1(
        schema="dmb_mixed_completed_turn_v1",
        envelope=env,
        assistant_text=answer,
        accepted_binding=accepted,
        accepted_binding_sha256=canonical_sha256(accepted),
        base_projection=projection,
    )


def test_build_approved_validates_only_exact_base_subsequence():
    mixed = build_projection(True)
    assert mixed.base_projection.turn.assistant_text == "Mirathorn source."
    assert mixed.assistant_text.startswith("Mirathorn source.\n")
    assert len(mixed.assistant_text) > len(mixed.base_projection.turn.assistant_text)


def test_build_unclaimed_retains_actual_graph_execution_without_fake_completion():
    mixed = build_projection(False)
    assert (
        mixed.base_projection.kind == "unclaimed"
        and not mixed.accepted_binding.graph_used
    )
    assert len(mixed.base_projection.graph_context_execution.events) == 3


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["base_projection"]["graph_context_execution"]["events"][0].update(
            envelope_sha256="b" * 64
        ),
        lambda d: d["base_projection"]["graph_context_execution"]["events"][-1].update(
            outcome="outcome_unknown"
        ),
        lambda d: d["base_projection"]["graph_context_execution"]["events"].pop(),
        lambda d: d["envelope"]["provenance"]["primary_work"].update(
            content_sha256="d" * 64
        ),
    ],
)
def test_unclaimed_requires_exact_graph_provenance_and_same_acknowledged_producing_request(
    change,
):
    model = build_projection(False)
    with pytest.raises(ValidationError):
        mutate(model, change)
