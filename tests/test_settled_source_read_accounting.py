"""Receipt settlement must release unused capacity without legalizing overbooking."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.types import (
    GraphExecutionPolicyV3,
    PlanWorldGraphExecutionV3,
    SettledGraphExecutionPolicyV3,
    SourceReadAnchorReceiptV2,
    SourceReadAuthorizationEventV2,
    ValidatedSourceReadEventV2,
    graph_execution_policy_digest_v3,
    source_read_character_usage,
)


def fixture_execution(*, settled=True):
    policy_type = SettledGraphExecutionPolicyV3 if settled else GraphExecutionPolicyV3
    policy = policy_type.model_validate(
        {
            "policy_version": "world_graph_execution_uncapped_v1",
            "allowed_graph_operations": ["expand_graph_retrieval"],
            "max_provider_attempts": None,
            "max_graph_operations": None,
            "max_total_provider_input_tokens": None,
            "max_total_provider_output_tokens": None,
            "max_results_per_operation": 512,
            "provider_input_accounting": {
                "kind": "exact_token_count",
                "estimator": "synthetic",
            },
            "source_opened": False,
            "max_source_read_chars": 96000,
            "max_chars_per_source_read": 12000,
            "source_read_scope": {
                "retrieval_session_id": "synthetic-session",
                "world_id": "synthetic-world",
                "campaign_id": None,
                "graph_revision": "synthetic-rev",
                "admitted_anchors": [
                    {
                        "anchor_id": f"a{i}",
                        "evidence_ref_id": f"e{i}",
                        "source_artifact_id": "artifact",
                        "source_revision_id": "source-rev",
                    }
                    for i in range(8)
                ],
            },
            **({"source_read_accounting": "settled_receipts_v1"} if settled else {}),
        }
    )
    return PlanWorldGraphExecutionV3(
        context_receipt_sha256="a" * 64,
        policy=policy,
        execution_policy_sha256=graph_execution_policy_digest_v3("a" * 64, policy),
        events=[],
    )


def authorization(execution, sequence=0, *, count=8, max_chars=12000):
    scope = execution.policy.source_read_scope
    return SourceReadAuthorizationEventV2(
        event_id=uuid4(),
        sequence=sequence,
        kind="source_read_authorized_v2",
        read_call_id=uuid4(),
        context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        retrieval_session_id=scope.retrieval_session_id,
        world_id=scope.world_id,
        campaign_id=scope.campaign_id,
        graph_revision=scope.graph_revision,
        anchors=scope.admitted_anchors[:count],
        max_chars=max_chars,
    )


def receipt(auth, sequence=1, *, counts=None):
    counts = counts if counts is not None else [10] * len(auth.anchors)
    return ValidatedSourceReadEventV2(
        event_id=uuid4(),
        sequence=sequence,
        kind="validated_source_read_v2",
        read_call_id=auth.read_call_id,
        receipts=[
            SourceReadAnchorReceiptV2(
                source_read_id=f"read-{uuid4()}",
                anchor_id=pin.anchor_id,
                evidence_ref_id=pin.evidence_ref_id,
                source_artifact_id=pin.source_artifact_id,
                source_revision_id=pin.source_revision_id,
                outcome="enough" if chars else "unavailable",
                returned_chars=chars,
                content_sha256="b" * 64 if chars else None,
                truncated=False,
                evidence_sufficiency_status="sufficient" if chars else "insufficient",
            )
            for pin, chars in zip(auth.anchors, counts, strict=True)
        ],
    )


def rebuild(execution, events):
    return PlanWorldGraphExecutionV3.model_validate(
        execution.model_dump(mode="json", by_alias=True)
        | {"events": [event.model_dump(mode="json", by_alias=True) for event in events]}
    )


def test_eight_short_passages_settle_and_allow_more_after_reconstruction():
    execution = fixture_execution()
    auth = authorization(execution)
    done = receipt(auth)
    next_auth = authorization(execution, 2, count=1)
    restored = rebuild(execution, [auth, done, next_auth])
    assert source_read_character_usage(restored.policy, restored.events) == 12080
    encoded = restored.model_dump_json(by_alias=True)
    assert (
        PlanWorldGraphExecutionV3.model_validate_json(encoded).model_dump_json(
            by_alias=True
        )
        == encoded
    )
    assert restored.policy.source_read_accounting == "settled_receipts_v1"


def test_unresolved_reservation_blocks_even_if_later_receipt_would_refund():
    execution = fixture_execution()
    auth = authorization(execution)
    overbook = authorization(execution, 1, count=1)
    done = receipt(auth, 2)
    with pytest.raises(
        ValidationError, match="character budget exceeded at authorization"
    ):
        rebuild(execution, [auth, overbook, done])


def test_old_policy_keeps_reserved_chars_and_exact_bytes():
    execution = fixture_execution(settled=False)
    auth = authorization(execution)
    done = receipt(auth)
    original = rebuild(execution, [auth, done])
    assert source_read_character_usage(original.policy, original.events) == 96000
    encoded = original.model_dump_json(by_alias=True)
    assert "source_read_accounting" not in encoded
    assert (
        PlanWorldGraphExecutionV3.model_validate_json(encoded).model_dump_json(
            by_alias=True
        )
        == encoded
    )
    with pytest.raises(ValidationError, match="character budget"):
        rebuild(execution, [auth, done, authorization(execution, 2, count=1)])


@pytest.mark.parametrize(
    "change", ["partial", "duplicate", "changed_pin", "future", "read_id", "excess"]
)
def test_invalid_receipts_never_release_capacity(change):
    execution = fixture_execution()
    auth = authorization(execution)
    done = receipt(auth)
    events = [auth, done]
    if change == "partial":
        done = done.model_copy(update={"receipts": done.receipts[:-1]})
    elif change == "duplicate":
        events.append(done.model_copy(update={"event_id": uuid4(), "sequence": 2}))
    elif change == "changed_pin":
        done = done.model_copy(
            update={
                "receipts": [
                    done.receipts[0].model_copy(update={"anchor_id": "foreign"}),
                    *done.receipts[1:],
                ]
            }
        )
    elif change == "future":
        events = [
            done.model_copy(update={"sequence": 0}),
            auth.model_copy(update={"sequence": 1}),
        ]
    elif change == "read_id":
        done = done.model_copy(
            update={
                "receipts": [
                    done.receipts[0],
                    done.receipts[1].model_copy(
                        update={"source_read_id": done.receipts[0].source_read_id}
                    ),
                    *done.receipts[2:],
                ]
            }
        )
    else:
        auth = auth.model_copy(update={"max_chars": 1})
    if change not in {"duplicate", "future"}:
        events = [auth, done]
    with pytest.raises(ValidationError):
        rebuild(execution, events)


def test_mixed_unavailable_truncated_and_complete_charge_exact_returned_chars():
    execution = fixture_execution()
    auth = authorization(execution)
    done = receipt(auth, counts=[0, 12000, 19, 0, 10, 5, 1, 0])
    done = done.model_copy(
        update={
            "receipts": [
                done.receipts[0],
                done.receipts[1].model_copy(
                    update={"outcome": "truncated", "truncated": True}
                ),
                *done.receipts[2:],
            ]
        }
    )
    restored = rebuild(execution, [auth, done])
    assert source_read_character_usage(restored.policy, restored.events) == 12035


def test_repeated_read_charges_each_actual_result_and_unresolved_other_call():
    execution = fixture_execution()
    a = authorization(execution, count=1)
    b = authorization(execution, 1, count=1)
    done = receipt(a, 2, counts=[14])
    again = authorization(execution, 3, count=1)
    done_again = receipt(again, 4, counts=[14])
    restored = rebuild(execution, [a, b, done, again, done_again])
    assert source_read_character_usage(restored.policy, restored.events) == 12028


def test_accounting_version_and_digest_cannot_be_silently_changed():
    execution = fixture_execution()
    payload = execution.model_dump(mode="json", by_alias=True)
    payload["policy"]["source_read_accounting"] = "guess"
    with pytest.raises(ValidationError):
        PlanWorldGraphExecutionV3.model_validate(payload)
    del payload["policy"]["source_read_accounting"]
    with pytest.raises(ValidationError, match="policy digest"):
        PlanWorldGraphExecutionV3.model_validate(payload)
