from __future__ import annotations

import json
import logging
from hashlib import sha256
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from application_state.agent_conversation.types import (
    HistoricalReference,
    PlanWorldGraphCompletionV1,
    PlanWorldGraphContextReceiptV1,
    PlanWorldGraphPlanClaimSegmentV1,
    PlanPlayableTargetReceiptV1,
    SubmittedTurnIntentV2,
    SubmittedPlanPlayableTargetV1,
    Turn,
    TurnProvenance,
    encode_plan_playable_target_reference,
)
from apps.live_control_server.models.agent_turn import (
    AgentTurnContentBasis,
    AgentTurnRequest,
)
from apps.live_control_server.services.agent_runtime import (
    CONVERSATION_ONLY_POLICY_ID,
    AgentRuntimeDescriptor,
    AgentRuntimeResult,
)
from apps.live_control_server.services.agent_turn_service import (
    _ClaimFence,
    _accept_world_turn,
    _completed_turn_replay,
    _submitted_turn_intent,
    project_plan_graph_execution_state,
    project_plan_turn_context,
    AgentTurnResolvedWork,
    AgentTurnServiceError,
    execute_agent_turn,
    _require_fresh_execution_append,
)
from apps.live_control_server.services.hermes_session_store import (
    HermesSessionPointerStore,
)


def _request(**updates: Any) -> AgentTurnRequest:
    payload: dict[str, Any] = {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": "thread-1",
        "turn_id": "turn-1",
        "surface": {"surface_id": "index", "instance_id": "index-main"},
        "owner_scope": None,
        "primary_work": None,
        "client_work_state": "none",
        "graph_request": {"mode": "none"},
        "graph_selection": None,
        "message": "Hello there",
    }
    payload.update(updates)
    return AgentTurnRequest.model_validate(payload)


def test_graph_operation_membership_requires_exact_typed_function_output() -> None:
    from apps.live_control_server.services.agent_turn_service import (
        _included_graph_operation_payloads,
    )

    payload = '{"schema":"dmb_world_graph_retrieval_result_v1","claim":"accepted"}'
    call = {
        "type": "function_call", "call_id": "call-1",
        "name": "expand_graph_retrieval", "arguments": "{}",
    }
    output = {"type": "function_call_output", "call_id": "call-1", "output": payload}
    assert _included_graph_operation_payloads({"input": [call, output]}) == [payload]
    assert _included_graph_operation_payloads({
        "input": [{"role": "user", "content": payload}],
    }) == []
    assert _included_graph_operation_payloads({
        "input": [call, {**output, "output": payload + " altered"}],
    }) == [payload + " altered"]
    with pytest.raises(ValueError, match="not matched"):
        _included_graph_operation_payloads({
            "input": [{**call, "name": "other_tool"}, output],
        })
    with pytest.raises(ValueError, match="not matched"):
        _included_graph_operation_payloads({
            "input": [call, {**output, "call_id": "wrong"}],
        })
    assert _included_graph_operation_payloads({"input": [
        call, output,
        {**call, "call_id": "call-2"},
        {**output, "call_id": "call-2"},
    ]}) == [payload, payload]


def test_explicit_plan_context_policy_is_fingerprinted_as_submitted_intent_v2() -> None:
    request = _request(
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "managed-world-1"},
        primary_work={
            "kind": "plan",
            "object_id": "plan-1",
            "expected_revision": 7,
            "expected_revision_n": 3,
            "expected_content_sha256": "a" * 64,
        },
        client_work_state="saved_clean",
        plan_context_policy={"policy": "auto_plan_world"},
    )
    intent = _submitted_turn_intent(request, world_id="managed-world-1")
    assert isinstance(intent, SubmittedTurnIntentV2)
    assert intent.plan_context_policy.policy == "auto_plan_world"


def test_plan_context_policy_cannot_be_accepted_without_frozen_provider_receipt() -> None:
    request = _request(
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "managed-world-1"},
        primary_work={
            "kind": "plan",
            "object_id": "plan-1",
            "expected_revision": 7,
            "expected_revision_n": 3,
            "expected_content_sha256": "a" * 64,
        },
        client_work_state="saved_clean",
        plan_context_policy={"policy": "auto_plan_world"},
    )
    intent = _submitted_turn_intent(request, world_id="managed-world-1")
    assert isinstance(intent, SubmittedTurnIntentV2)
    provenance = TurnProvenance(
        world_id="managed-world-1",
        surface_resolution="resolved",
        surface_id="plan",
        primary_work=HistoricalReference(resolution="absent"),
        selected_object=HistoricalReference(resolution="absent"),
    )
    with pytest.raises(AgentTurnServiceError) as caught:
        _accept_world_turn(
            None,  # Guard must run before touching the persistence service.
            request,
            world_id="managed-world-1",
            provenance=provenance,
            submitted_intent=intent,
        )
    assert caught.value.code == "plan_graph_receipt_unavailable"


def test_plan_context_policy_fails_after_replay_preflight_before_mutable_reads(
    tmp_path: Path,
) -> None:
    request = _request(
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
        primary_work={
            "kind": "plan",
            "object_id": "plan:one",
            "expected_revision": 7,
            "expected_revision_n": 4,
            "expected_content_sha256": "b" * 64,
        },
        client_work_state="saved_dirty",
        plan_context_policy={"policy": "auto_plan_world"},
    )

    class ReconcileOnly:
        calls = 0

        def reconcile_turn(self, *_args: Any) -> None:
            self.calls += 1
            return None

    conversation_service = ReconcileOnly()
    mutable_reads: list[str] = []
    runtime_lookups: list[str] = []

    with pytest.raises(AgentTurnServiceError) as caught:
        execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
            owner_resolver=lambda _request: {
                "kind": "world",
                "id": "world:one",
                "name": "One",
            },
            work_resolver=lambda *_args: mutable_reads.append("plan") or None,
            graph_resolver=lambda *_args: pytest.fail("generic Graph must stay disabled"),
            runtime_factory=lambda: runtime_lookups.append("runtime"),
            conversation_service=conversation_service,  # type: ignore[arg-type]
        )

    assert caught.value.code == "plan_graph_execution_unavailable"
    assert conversation_service.calls == 1
    assert mutable_reads == []
    assert runtime_lookups == []


@pytest.mark.parametrize(
    ("authorization", "completed", "claimability", "projected_authorization"),
    [
        ("none", False, "safe_to_reclaim_without_dispatch", "none"),
        ("known_not_sent", False, "explicit_new_attempt_required", "known_not_sent"),
        ("authorized", False, "blocked_unknown_or_sent", "authorized"),
        ("sdk_entered", False, "blocked_unknown_or_sent", "sdk_entered"),
        ("response_received", False, "blocked_unknown_or_sent", "response_received"),
        ("outcome_unknown", False, "blocked_unknown_or_sent", "outcome_unknown"),
        (None, False, "blocked_unknown_or_sent", "outcome_unknown"),
        ("response_received", True, "completed", "response_received"),
        ("invalid", False, "blocked_unknown_or_sent", "outcome_unknown"),
    ],
)
def test_execution_projection_never_implies_automatic_redispatch(
    authorization: str | None,
    completed: bool,
    claimability: str,
    projected_authorization: str,
) -> None:
    projection = project_plan_graph_execution_state(
        authorization, completed=completed
    )
    assert projection.claimability == claimability
    assert projection.authorization_state == projected_authorization
    assert projection.automatic_redispatch is False


def _policy_turn(
    *, status: str = "completed", completion_present: bool = True, drift: bool = False
) -> Turn:

    revision_id = uuid4()
    receipt_payload = {
        "schema": "dmb_agent_plan_world_graph_context_receipt_v1",
        "receipt_serializer_version": "canonical-json-utf8-v1",
        "context_receipt_sha256": "0" * 64,
        "plan_context_policy": {
            "schema": "dmb_plan_context_policy_v1",
            "policy": "auto_plan_world",
        },
        "plan_basis": {
            "world_id": "world:one",
            "document_id": "plan:one",
            "object_revision": 7,
            "work_revision_id": str(revision_id),
            "revision_n": 4,
            "content_sha256": "b" * 64,
        },
        "playable_target": None,
        "graph_authority": {
            "managed_world_id": "world:one",
            "native_world_id": "native:one",
            "binding_version": 2,
            "scope_mode": "world",
            "campaign_id": None,
            "admissibility_version": "gm-v1",
            "graph_revision": "graph-revision-3",
        },
        "graph_packet": {
            "schema": "dmb_plan_world_graph_packet_v1",
            "packet_serializer_version": "canonical-json-utf8-v1",
            "selection_policy_version": "selection-v1",
            "evidence_sufficiency_policy_version": "sufficiency-v1",
            "retrieval_packet_sha256": "c" * 64,
            "candidate_assertion_ids": [],
            "candidate_relationship_ids": [],
            "candidate_evidence_ref_ids": [],
            "retrieval_status": "empty",
            "evidence_sufficiency_status": "insufficient",
            "result_limit": 32,
            "coverage_status": "incomplete",
            "truncated": False,
            "omission_reasons": ["no_admissible_evidence"],
        },
        "assembled_input": {
            "assembler_version": "assembler-v1",
            "budget_policy_version": "budget-v1",
            "provider_model_name": "synthetic-model",
            "provider_model_version": "1",
            "tokenizer_name": "utf8_json_bytes_plus_64_per_node_v1",
            "tokenizer_version": "v1",
            "provider_envelope_input_tokens": 10,
            "output_token_reserve": 10,
            "context_window_limit": 100,
            "packet_disposition": "omitted_insufficient",
            "packet_disposition_reason": "insufficient_evidence",
            "dispatched_packet_sha256": None,
            "dispatched_assertion_ids": [],
            "dispatched_relationship_ids": [],
            "dispatched_evidence_ref_ids": [],
            "source_token_accounting": [],
            "included_history": [],
            "assembled_input_sha256": "d" * 64,
        },
        "evidence_mode": "metadata_only",
        "source_opened": False,
    }
    canonical = json.dumps(
        {key: value for key, value in receipt_payload.items() if key != "context_receipt_sha256"},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    receipt_payload["context_receipt_sha256"] = sha256(canonical).hexdigest()
    receipt = PlanWorldGraphContextReceiptV1.model_validate(receipt_payload)
    completion = PlanWorldGraphCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis="committed_plan",
        answer_context_status="plan_only_insufficient_evidence",
        answer_segments=[
            PlanWorldGraphPlanClaimSegmentV1(
                kind="plan_claim",
                text="The keeper waits below the arch.",
                plan_content_sha256="b" * 64,
            )
        ],
        citation_map=None,
    )
    primary = HistoricalReference(
        resolution="resolved",
        kind="plan",
        object_id="plan:one",
        revision="7",
        content_sha256="b" * 64 if not drift else "e" * 64,
        object_revision=7,
        work_revision_id=revision_id,
        revision_n=4,
    )
    now = datetime.now(UTC)
    return Turn(
        turn_id=uuid4(),
        conversation_id=uuid4(),
        world_id="world:one",
        idempotency_key=uuid4(),
        sequence=1,
        revision=1,
        status=status,
        user_text="What does the Plan say?",
        assistant_text=(
            "The keeper waits below the arch."
            if completion_present and status == "completed"
            else None
        ),
        failure_code=None,
        provenance=TurnProvenance(
            world_id="world:one",
            surface_resolution="resolved",
            surface_id="plan",
            surface_instance_id="plan-main",
            primary_work=primary,
            selected_object=HistoricalReference(resolution="absent"),
        ),
        submitted_intent_fingerprint_v2="f" * 64,
        graph_context_receipt=receipt,
        completion=completion if completion_present else None,
        attempt=1 if status in {"running", "completed"} else 0,
        claim_expires_at=None,
        accepted_at=now,
        completed_at=now if status == "completed" else None,
        updated_at=now,
    )


def _policy_turn_with_targets(
    receipt_target: PlanPlayableTargetReceiptV1 | None,
    provenance_target: PlanPlayableTargetReceiptV1 | None,
) -> Turn:
    turn = _policy_turn()
    payload = turn.graph_context_receipt.model_dump(mode="json", by_alias=True)
    payload["playable_target"] = (
        None
        if receipt_target is None
        else receipt_target.model_dump(mode="json", by_alias=True)
    )
    canonical = json.dumps(
        {key: value for key, value in payload.items() if key != "context_receipt_sha256"},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    payload["context_receipt_sha256"] = sha256(canonical).hexdigest()
    receipt = PlanWorldGraphContextReceiptV1.model_validate(payload)
    completion = turn.completion.model_copy(update={
        "context_receipt_sha256": receipt.context_receipt_sha256,
    })
    provenance = turn.provenance.model_copy(update={
        "supporting_work": (
            [] if provenance_target is None
            else [encode_plan_playable_target_reference(provenance_target)]
        ),
    })
    return turn.model_copy(update={
        "graph_context_receipt": receipt,
        "completion": completion,
        "provenance": provenance,
    })


def _cited_card_a_policy_turn() -> Turn:
    card_a = PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind="scene",
        id="scene:opening",
        marker_grammar_version="v1",
    )
    turn = _policy_turn_with_targets(card_a, card_a)
    payload = turn.graph_context_receipt.model_dump(mode="json", by_alias=True)
    payload["plan_basis"].update({
        "world_id": "world-conversation-test",
        "document_id": "saved-plan-test",
        "work_revision_id": "00000000-0000-4000-8000-000000000011",
        "revision_n": 1,
        "content_sha256": "a" * 64,
    })
    payload["graph_authority"]["managed_world_id"] = "world-conversation-test"
    payload["graph_packet"].update({
        "candidate_assertion_ids": ["assertion-internal-test"],
        "candidate_evidence_ref_ids": ["evidence-internal-test"],
        "retrieval_status": "complete",
        "evidence_sufficiency_status": "sufficient",
        "coverage_status": "complete",
        "omission_reasons": [],
    })
    payload["assembled_input"].update({
        "packet_disposition": "included",
        "packet_disposition_reason": None,
        "dispatched_packet_sha256": "c" * 64,
        "dispatched_assertion_ids": ["assertion-internal-test"],
        "dispatched_evidence_ref_ids": ["evidence-internal-test"],
    })
    canonical = json.dumps(
        {key: value for key, value in payload.items() if key != "context_receipt_sha256"},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    payload["context_receipt_sha256"] = sha256(canonical).hexdigest()
    receipt = PlanWorldGraphContextReceiptV1.model_validate(payload)
    claim = {
        "kind": "graph_claim",
        "claim_id": "claim-internal-test",
        "text": "The western gate is watched.",
        "target_kind": "assertion",
        "target_id": "assertion-internal-test",
        "graph_revision": "graph-revision-3",
        "evidence_ref_ids": ["evidence-internal-test"],
    }
    completion = PlanWorldGraphCompletionV1.model_validate({
        "schema": "dmb_plan_world_graph_completion_v1",
        "context_receipt_sha256": receipt.context_receipt_sha256,
        "answer_basis": "committed_plan_plus_world_graph",
        "answer_context_status": "graph_grounded",
        "answer_segments": [claim],
        "citation_map": {
            "schema": "dmb_graph_citation_map_v1",
            "context_receipt_sha256": receipt.context_receipt_sha256,
            "entries": [{
                **{key: value for key, value in claim.items() if key not in {"kind", "text"}},
                "source_opened": False,
            }],
        },
    })
    provenance = turn.provenance.model_copy(update={
        "world_id": "world-conversation-test",
        "primary_work": turn.provenance.primary_work.model_copy(update={
            "object_id": "saved-plan-test",
            "work_revision_id": UUID("00000000-0000-4000-8000-000000000011"),
            "revision_n": 1,
            "content_sha256": "a" * 64,
        }),
    })
    return turn.model_copy(update={
        "turn_id": UUID("00000000-0000-4000-8000-000000000032"),
        "conversation_id": UUID("00000000-0000-4000-8000-000000000031"),
        "world_id": "world-conversation-test",
        "user_text": "Who watches the western gate?",
        "assistant_text": claim["text"],
        "provenance": provenance,
        "graph_context_receipt": receipt,
        "completion": completion,
    })


def test_history_projection_keeps_receipt_and_completion_bound_to_provenance() -> None:
    context = project_plan_turn_context(_policy_turn(), delivery_replay=False)
    assert context.receipt.plan_basis.document_id == "plan:one"
    assert context.completion is not None
    assert context.execution is None
    assert context.delivery_replay is False

    with pytest.raises(AgentTurnServiceError, match="historical turn provenance"):
        project_plan_turn_context(_policy_turn(drift=True), delivery_replay=False)


def test_history_projection_requires_exact_canonical_playable_target() -> None:
    card_a = PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind="scene",
        id="scene:card-a",
        marker_grammar_version="v1",
    )
    card_b = card_a.model_copy(update={"id": "scene:card-b"})
    for receipt_target, provenance_target in (
        (card_a, None),
        (None, card_a),
        (card_a, card_b),
    ):
        turn = _policy_turn_with_targets(receipt_target, provenance_target)
        with pytest.raises(AgentTurnServiceError) as caught:
            project_plan_turn_context(turn, delivery_replay=False)
        assert caught.value.code == "turn_receipt_unverifiable"

    matching = project_plan_turn_context(
        _policy_turn_with_targets(card_a, card_a), delivery_replay=False
    )
    assert matching.receipt.playable_target == card_a
    assert project_plan_turn_context(
        _policy_turn_with_targets(None, None), delivery_replay=False
    ).receipt.playable_target is None


def test_completed_policy_replay_returns_v2_from_stored_receipt_only() -> None:
    from apps.live_control_server.models.agent_turn import AgentTurnResponseV2

    turn = _policy_turn()
    request = _request(
        client_thread_id="plan-main-thread",
        turn_id=str(turn.turn_id),
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
        primary_work={
            "kind": "plan",
            "object_id": "plan:one",
            "expected_revision": 7,
            "expected_revision_n": 4,
            "expected_content_sha256": "b" * 64,
        },
        client_work_state="saved_clean",
        message=turn.user_text,
        plan_context_policy={"policy": "auto_plan_world"},
    )

    response = _completed_turn_replay(
        request,
        owner={"kind": "world", "id": "world:one", "name": "One"},
        turn=turn,
    )

    assert isinstance(response, AgentTurnResponseV2)
    assert response.graph.status == "not_requested"
    assert response.plan_context.receipt == turn.graph_context_receipt
    assert response.plan_context.completion == turn.completion
    assert response.plan_context.execution is None
    assert response.plan_context.delivery_replay is True
    assert response.answer.text == "The keeper waits below the arch."
    assert response.answer.graph_grounded is False


def _serialized_card_a_history_body(
    monkeypatch: Any,
) -> dict[str, Any]:
    """Exercise FastAPI's response serialization for additive policy history."""
    import asyncio
    from fastapi.encoders import jsonable_encoder
    from fastapi.routing import serialize_response
    from types import SimpleNamespace

    from apps.live_control_server.routes import agent as agent_route

    policy_turn = _cited_card_a_policy_turn()
    legacy_turn = SimpleNamespace(
        turn_id=UUID("00000000-0000-4000-8000-000000000033"),
        sequence=1,
        status="completed",
        user_text="A legacy question",
        assistant_text="A legacy answer",
        provenance=policy_turn.provenance,
        graph_context_receipt=None,
    )
    policy_turn = policy_turn.model_copy(update={"sequence": 2})
    conversation_id = policy_turn.conversation_id

    class HistoryService:
        def get_world_pointer(self, _world_id: str) -> Any:
            return SimpleNamespace(
                revision=4, active_conversation_id=conversation_id
            )

        def get_active_conversation(self, _world_id: str) -> Any:
            return SimpleNamespace(conversation_id=conversation_id)

        def list_turns(self, *_args: Any, **_kwargs: Any) -> list[Any]:
            return [policy_turn, legacy_turn]

    monkeypatch.setattr(agent_route, "_verified_world_id", lambda value: value)
    monkeypatch.setattr(agent_route, "enforce_native_graph_gm", lambda _request: None)
    route = next(
        item
        for item in agent_route.router.routes
        if getattr(item, "path", None) == "/agent/worlds/{world_id}/conversation"
    )
    assert route.response_model == (
        agent_route.AgentConversationHistoryResponse
        | agent_route.AgentConversationHistoryResponseV2
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(
            agent_conversation_service=HistoryService()
        ))
    )
    response = agent_route.get_world_conversation_history(
        "world-conversation-test", request, limit=50, before_sequence=None
    )
    serialized = asyncio.run(
        serialize_response(
            field=route.response_field,
            response_content=response,
            by_alias=True,
            is_coroutine=True,
        )
    )
    body = jsonable_encoder(serialized, by_alias=True)

    return body


def test_history_http_route_serializes_mixed_v1_and_v2_turns(
    monkeypatch: Any,
) -> None:
    body = _serialized_card_a_history_body(monkeypatch)

    assert body["schema"] == "dmb_agent_conversation_history_v2"
    assert body["world_id"] == "world-conversation-test"
    assert [turn["sequence"] for turn in body["turns"]] == [2, 1]
    policy_payload = body["turns"][0]["plan_context"]
    assert policy_payload["schema"] == "dmb_agent_plan_world_graph_context_response_v1"
    assert policy_payload["receipt"]["schema"] == "dmb_agent_plan_world_graph_context_receipt_v1"
    assert policy_payload["receipt"]["plan_basis"]["document_id"] == "saved-plan-test"
    assert policy_payload["receipt"]["playable_target"] == {
        "schema": "dmb_plan_playable_target_receipt_v1",
        "kind": "scene",
        "id": "scene:opening",
        "marker_grammar_version": "v1",
    }
    assert body["turns"][0]["provenance"]["supporting_work"] == [
        encode_plan_playable_target_reference(
            PlanPlayableTargetReceiptV1(
                schema="dmb_plan_playable_target_receipt_v1",
                kind="scene",
                id="scene:opening",
                marker_grammar_version="v1",
            )
        ).model_dump(mode="json")
    ]
    assert policy_payload["completion"]["citation_map"]["entries"][0] == {
        "claim_id": "claim-internal-test",
        "target_kind": "assertion",
        "target_id": "assertion-internal-test",
        "graph_revision": "graph-revision-3",
        "evidence_ref_ids": ["evidence-internal-test"],
        "source_opened": False,
    }
    assert body["turns"][1]["assistant_text"] == "A legacy answer"
    assert "plan_context" not in body["turns"][1]


def test_execution_claim_fence_serializes_appends_with_latest_revision() -> None:
    turn = _policy_turn(status="running", completion_present=False)

    class AppendService:
        revisions: list[int] = []

        def record_provider_outcome(self, _world: str, _conversation: Any, _turn: Any,
                                    *, expected_revision: int, expected_attempt: int,
                                    outcome: Any) -> tuple[Turn, bool]:
            self.revisions.append(expected_revision)
            assert expected_attempt == turn.attempt
            assert outcome is not None
            return turn.model_copy(update={"revision": expected_revision + 1}), True

        def renew_turn_claim(self, *_args: Any, **_kwargs: Any) -> Turn:
            raise AssertionError("renewal should not run in this short witness")

    service = AppendService()
    fence = _ClaimFence(service, turn)  # type: ignore[arg-type]
    try:
        first, first_fresh = fence.append(
            "record_provider_outcome", "outcome", {"outcome": "sdk_entered"}
        )
        second, second_fresh = fence.append(
            "record_provider_outcome", "outcome", {"outcome": "response_received"}
        )
    finally:
        latest, error = fence.stop()

    assert error is None
    assert first_fresh is True and second_fresh is True
    assert [first.revision, second.revision, latest.revision] == [2, 3, 3]
    assert service.revisions == [1, 2]


def test_duplicate_execution_event_never_acknowledges_harness_progress() -> None:
    turn = _policy_turn(status="running", completion_present=False)
    with pytest.raises(AgentTurnServiceError) as caught:
        _require_fresh_execution_append((turn, False))
    assert caught.value.code == "turn_persistence_indeterminate"


def test_plan_graph_budget_fails_closed_for_unverified_model(
    monkeypatch: Any,
) -> None:
    from apps.live_control_server.services import agent_turn_service as service_module

    monkeypatch.setattr(
        "apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference",
        lambda **_kwargs: ("openai-api", "unverified-model", "https://api.openai.com/v1"),
    )
    with pytest.raises(AgentTurnServiceError) as caught:
        service_module._policy_request_budget()
    assert caught.value.code == "provider_envelope_over_budget"
    assert caught.value.provider_dispatched is False


@pytest.mark.parametrize(
    "plan_markdown",
    ["The keeper waits.", "The keeper waits.\n" + "x" * 50_000],
    ids=["short", "long-committed-plan"],
)
def test_policy_adapter_freezes_first_envelope_and_fences_provider_lifecycle(
    monkeypatch: Any,
    plan_markdown: str,
    caplog: Any,
) -> None:
    from datetime import timedelta
    from application_state.agent_conversation import types as graph_types
    if not hasattr(graph_types, "PlanWorldGraphExecutionV1"):
        pytest.skip("run with pinned APP-STATE candidate")
    from apps.live_control_server.services import agent_turn_service as service_module
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference",
        lambda **_kwargs: ("openai-api", "gpt-6-luna", "https://api.openai.com/v1"),
    )
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from graph_memory.interaction.session import (
        CoverageState, GraphRetrievalSession, SessionSnapshot,
    )
    from application_state.agent_conversation.types import TurnClaimReceipt

    request = _request(
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
        primary_work={
            "kind": "plan", "object_id": "plan:one", "expected_revision": 7,
            "expected_revision_n": 4, "expected_content_sha256": "b" * 64,
        },
        client_work_state="saved_clean",
        plan_context_policy={"policy": "auto_plan_world"},
        message="What does the Plan say?",
    )
    basis = AgentTurnContentBasis(
        world_id="world:one", document_id="plan:one", object_revision=7,
        work_revision_id=str(uuid4()), revision_n=4, content_sha256="b" * 64,
        committed_status="committed", has_divergent_working_copy=False,
    )
    work = AgentTurnResolvedWork(
        kind="plan", object_id="plan:one", revision=7,
        changed_since_expected=False, owner_kind="world", owner_id="world:one",
        world_id="world:one", content_basis=basis, plan_markdown=plan_markdown,
    )
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="native:one", campaign_id="", focus={"kind": "none"},
            admissibility="gm", revision_id="graph-revision-3",
            is_head=True, scope_mode="world",
        ),
        question=request.message,
        coverage=CoverageState(state="empty"),
    )
    bootstrap = service_module.AgentPlanWorldGraphBootstrap(
            graph_envelope={
                "revision_id": "graph-revision-3", "world_id": "native:one",
                "scope_mode": "world",
            },
        world_scope=AgentWorldScope(
            world_id="native:one", campaign_id="", focus={"kind": "none"},
            admissibility="gm", revision_id="graph-revision-3", scope_mode="world",
        ),
        retrieval_session=session,
        binding_version=2,
        source_root_relpath="corpus/world-one-markdown",
        candidate_assertion_ids=(), candidate_relationship_ids=(),
        candidate_evidence_ref_ids=(), evidence_by_anchor_id={},
    )
    projected = session.project_for_hermes()
    initial_packet = {
        "candidates": projected["candidates"][:8],
        "claimLedger": projected["claim_ledger"][:24],
        "intentHint": projected["intent_hint"],
        "availableExpansions": projected["available_expansions"],
    }
    provider_body = {
        "input": [{
            "role": "system",
            "content": "Turn capability policy (runtime-enforced; also required on tool calls):\n"
            + json.dumps({"initialClaimPacket": initial_packet}),
        }, {
            "role": "user",
            "content": service_module._plan_message(
                request.message, work.plan_markdown,
                content_basis=work.content_basis,
            ),
        }],
        "tools": [],
    }
    payload_json = json.dumps(provider_body, sort_keys=True, separators=(",", ":"))
    view = {
        "provider": "openai-api", "model": "gpt-6-luna",
        "apiMode": "codex_responses", "payloadJson": payload_json,
        "payloadSha256": sha256(payload_json.encode()).hexdigest(),
        "payloadUtf8Bytes": len(payload_json.encode()),
    }
    budget = service_module._policy_request_budget()
    assert budget["contextLimitTokens"] == 1_050_000

    class FakeExecutionPort:
        turn: Turn | None = None
        accepted_count = 0
        authorize_count = 0

        def reconcile_turn(self, *_args: Any) -> None:
            return None

        def accept_turn(self, _submission: Any) -> Turn:
            raise AssertionError("test intercepts acceptance after final envelope")

        def claim_turn(self, world_id: str, conversation_id: Any, turn_id: Any, *, expected_revision: int, lease_seconds: int = 120) -> Any:
            assert self.turn is not None
            assert (world_id, conversation_id, turn_id, expected_revision) == (
                self.turn.world_id, self.turn.conversation_id, self.turn.turn_id,
                self.turn.revision,
            )
            now = datetime.now(UTC)
            self.turn = self.turn.model_copy(update={
                "status": "running", "attempt": self.turn.attempt + 1,
                "revision": self.turn.revision + 1,
                "claim_expires_at": now + timedelta(seconds=lease_seconds),
                "updated_at": now,
            })
            return TurnClaimReceipt(disposition="claimed", turn=self.turn)

        def _append(self, event: Any, expected_revision: int, expected_attempt: int) -> tuple[Turn, bool]:
            assert self.turn is not None
            assert (expected_revision, expected_attempt) == (
                self.turn.revision, self.turn.attempt,
            )
            execution = self.turn.graph_context_execution
            assert execution is not None
            updated = graph_types.PlanWorldGraphExecutionV1.model_validate({
                **execution.model_dump(mode="json", by_alias=True),
                "events": [
                    *[prior.model_dump(mode="json", by_alias=True) for prior in execution.events],
                    event.model_dump(mode="json", by_alias=True),
                ],
            })
            self.turn = self.turn.model_copy(update={
                "graph_context_execution": updated,
                "revision": self.turn.revision + 1,
            })
            return self.turn, True

        def authorize_provider_attempt(self, _world_id: str, _conversation_id: Any, _turn_id: Any, *, expected_revision: int, expected_attempt: int, provider_attempt_event: Any) -> tuple[Turn, bool]:
            self.authorize_count += 1
            return self._append(provider_attempt_event, expected_revision, expected_attempt)

        def record_provider_outcome(self, _world_id: str, _conversation_id: Any, _turn_id: Any, *, expected_revision: int, expected_attempt: int, outcome: Any) -> tuple[Turn, bool]:
            return self._append(outcome, expected_revision, expected_attempt)

        def append_validated_graph_operation(self, _world_id: str, _conversation_id: Any, _turn_id: Any, *, expected_revision: int, expected_attempt: int, operation_event: Any) -> tuple[Turn, bool]:
            return self._append(operation_event, expected_revision, expected_attempt)

        def complete_turn(self, result: Any) -> Turn:
            assert self.turn is not None
            assert self.turn.revision == result.expected_revision
            execution = self.turn.graph_context_execution
            assert execution is not None
            binding = graph_types.CompletionBindingEventV1(
                event_id=uuid4(), sequence=len(execution.events),
                kind="completion_binding",
                provider_attempt_id=result.producing_provider_attempt_id,
                completion_sha256=service_module._canonical_sha256(
                    result.completion.model_dump(mode="json", by_alias=True)
                ),
                claim_graph_event_ids=result.claim_graph_event_ids,
            )
            updated_execution = graph_types.PlanWorldGraphExecutionV1.model_validate({
                **execution.model_dump(mode="json", by_alias=True),
                "events": [
                    *[prior.model_dump(mode="json", by_alias=True) for prior in execution.events],
                    binding.model_dump(mode="json", by_alias=True),
                ],
            })
            graph_types.validate_execution_completion(
                result.completion, self.turn.graph_context_receipt,
                updated_execution, result.producing_provider_attempt_id,
                result.claim_graph_event_ids,
            )
            now = datetime.now(UTC)
            self.turn = Turn.model_validate(self.turn.model_copy(update={
                "status": "completed", "revision": self.turn.revision + 1,
                "assistant_text": result.assistant_text,
                "completion": result.completion,
                "graph_context_execution": updated_execution,
                "claim_expires_at": None,
                "completed_at": now, "updated_at": now,
            }).model_dump(mode="json", by_alias=True))
            return self.turn

        def fail_turn(self, _failure: Any, *, interrupted: bool = False) -> Turn:
            raise AssertionError("valid typed answer must not fail the turn")

        def renew_turn_claim(self, *_args: Any, **_kwargs: Any) -> Turn:
            assert self.turn is not None
            return self.turn

    fake = FakeExecutionPort()

    def accept(_service: Any, _request: Any, **kwargs: Any) -> Turn:
        fake.accepted_count += 1
        now = datetime.now(UTC)
        fake.turn = Turn(
            turn_id=uuid4(), conversation_id=uuid4(), world_id="world:one",
            idempotency_key=uuid4(), sequence=1, revision=1,
            status="accepted", user_text=request.message,
            assistant_text=None, failure_code=None,
            provenance=kwargs["provenance"],
            submitted_intent_fingerprint_v2="f" * 64,
            graph_context_receipt=kwargs["graph_context_receipt"],
            graph_context_execution=kwargs["graph_context_execution"],
            completion=None, attempt=0, claim_expires_at=None,
            accepted_at=now, completed_at=None, updated_at=now,
        )
        return fake.turn

    monkeypatch.setattr(service_module, "_accept_world_turn", accept)
    if len(plan_markdown) > 50_000:
        over_budget = service_module._PolicyExecutionAdapter(
            service=fake,
            request=request,
            world_id="world:one",
            work=work,
            bootstrap=bootstrap,
            playable_target=None,
            submitted_intent=_submitted_turn_intent(request, world_id="world:one"),
            existing_turn=None,
            budget={**budget, "contextLimitTokens": 32768},
        )
        assert over_budget.authorize(view) is False
        assert over_budget.failure is not None
        assert over_budget.failure.code == "provider_envelope_over_budget"
        assert over_budget.failure.provider_dispatched is False
        assert fake.accepted_count == 0
        assert fake.authorize_count == 0
        over_budget.stop()
    adapter = service_module._PolicyExecutionAdapter(
        service=fake, request=request, world_id="world:one", work=work,
        bootstrap=bootstrap, playable_target=None,
        submitted_intent=_submitted_turn_intent(request, world_id="world:one"),
        existing_turn=None, budget=budget,
    )
    assert adapter.authorize(view) is True
    user_content = json.loads(view["payloadJson"])["input"][1]["content"]
    assert json.loads(user_content.split("\n", 1)[1])[
        "committed_plan_markdown"
    ] == plan_markdown
    assert fake.accepted_count == 1
    assert fake.authorize_count == 1
    assert adapter.record_lifecycle({"transition": "sdk_entered"}) is True
    assert adapter.record_lifecycle({"transition": "response_received"}) is True
    assert adapter.fence is not None
    turn = adapter.fence.turn
    assert turn is not None
    assert adapter.producing_provider_attempt_id is not None
    assert turn.graph_context_receipt is not None
    assert turn.graph_context_receipt.assembled_input.assembled_input_sha256 == view["payloadSha256"]
    typed_answer = json.dumps({
        "answer_context_status": "plan_only_insufficient_evidence",
        "answer_segments": [{"kind": "plan_claim", "text": "The keeper waits."}],
        "citation_map": None,
    })
    completion, bindings, answer = service_module._parse_policy_completion(
        typed_answer, turn, adapter.producing_provider_attempt_id,
    )
    assert completion.answer_context_status == "plan_only_insufficient_evidence"
    assert bindings == {}
    assert answer == "The keeper waits."

    # The one public synthetic provider witness returned this exact shape.
    # It must remain rejected at the owning completion boundary rather than
    # being silently coerced into a Graph claim or an invented citation.
    malformed_live_answer = json.dumps({
        "answer_context_status": "graph_used_insufficient_evidence",
        "answer_segments": [{
            "type": "graph_claim",
            "text": "The graph identifies the tavern as The Prancing Tavern, but provides no information about where it is.",
            "claim_ids": ["identity:obj:tavern"],
            "evidence_ids": [],
        }, {
            "type": "plan_claim",
            "text": "The committed Plan says the keeper waits by the tavern.",
        }],
        "citation_map": {
            "graph_claims": [{"segment_index": 0, "claim_ids": ["identity:obj:tavern"], "evidence_ids": []}],
            "plan_claims": [{"segment_index": 1}],
        },
    })
    with pytest.raises(AgentTurnServiceError, match="pinned Plan/Graph evidence contract") as malformed:
        service_module._parse_policy_completion(
            malformed_live_answer, turn, adapter.producing_provider_attempt_id,
        )
    assert malformed.value.code == "answer_validation_failed"

    duplicate_payload = '{"schema":"dmb_world_graph_retrieval_result_v1","claim":"same"}'
    operation_event = graph_types.ValidatedGraphOperationEventV1(
        event_id=uuid4(), sequence=len(turn.graph_context_execution.events),
        kind="validated_graph_operation", operation_id=uuid4(),
        operation="expand_graph_retrieval",
        request_arguments_sha256=sha256(b"{}").hexdigest(),
        graph_revision="graph-revision-3",
        result_packet_sha256=sha256(duplicate_payload.encode()).hexdigest(),
        assertion_ids=[], relationship_ids=["rel:one"],
        evidence_ref_ids=["ev:one"],
        evidence_sufficiency_status="sufficient", coverage_status="complete",
        truncated=False, source_opened=False,
    )
    turn, fresh = adapter.fence.append(
        "append_validated_graph_operation", "operation_event", operation_event,
    )
    assert fresh is True
    adapter.operation_payloads[operation_event.event_id] = duplicate_payload
    repeated_body = json.loads(payload_json)
    repeated_body["input"].extend([
        {"type": "function_call", "call_id": "call-a", "name": "expand_graph_retrieval", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call-a", "output": duplicate_payload},
        {"type": "function_call", "call_id": "call-b", "name": "expand_graph_retrieval", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call-b", "output": duplicate_payload},
    ])
    repeated_json = json.dumps(repeated_body, sort_keys=True, separators=(",", ":"))
    repeated_view = {
        **view, "payloadJson": repeated_json,
        "payloadSha256": sha256(repeated_json.encode()).hexdigest(),
        "payloadUtf8Bytes": len(repeated_json.encode()),
    }
    assert adapter.authorize(repeated_view) is False
    assert adapter.failure is not None
    assert adapter.failure.code == "graph_evidence_invalid"
    assert adapter.failure.provider_dispatched is False
    assert fake.authorize_count == 1
    assert adapter.fence.turn.graph_context_execution.events[-1].kind == "validated_graph_operation"
    adapter.stop()

    fake = FakeExecutionPort()

    class GuardedRuntime:
        descriptor = AgentRuntimeDescriptor("fake-guarded", "fake", "test", "graph")

        def run_with_provider_authorization(
            self, _invocation: Any, authorize: Any, *, request_budget: Any,
            on_graph_operation: Any, on_provider_lifecycle: Any,
        ) -> AgentRuntimeResult:
            assert callable(on_graph_operation)
            adjusted = dict(view)
            adjusted["model"] = request_budget["model"]
            assert authorize(adjusted) is True
            assert on_provider_lifecycle({"transition": "sdk_entered"}) is True
            assert on_provider_lifecycle({"transition": "response_received"}) is True
            return AgentRuntimeResult(
                status="ok", final_text=typed_answer,
                runtime_session_id="synthetic-plan-session",
            )

    class BudgetVetoRuntime:
        descriptor = AgentRuntimeDescriptor("budget-veto", "fake", "test", "graph")

        def __init__(
            self, result: AgentRuntimeResult, *, authorize_first: bool = False,
            reject_at_adapter: bool = False,
        ) -> None:
            self.result = result
            self.authorize_first = authorize_first
            self.reject_at_adapter = reject_at_adapter

        def run_with_provider_authorization(
            self, _invocation: Any, authorize: Any, *, request_budget: Any,
            on_graph_operation: Any, on_provider_lifecycle: Any,
        ) -> AgentRuntimeResult:
            assert request_budget["contextLimitTokens"] == 1_050_000
            if self.authorize_first:
                adjusted = dict(view)
                adjusted["model"] = request_budget["model"]
                assert authorize(adjusted) is True
            if self.reject_at_adapter:
                adjusted = dict(view)
                adjusted["model"] = request_budget["model"]
                assert authorize(adjusted) is False
            return self.result

    def execute_budget_result(
        result: AgentRuntimeResult, *, authorize_first: bool = False,
        reject_at_adapter: bool = False,
    ):
        return execute_agent_turn(
            request, root=Path("/tmp"),
            pointer_store=HermesSessionPointerStore(Path("/tmp") / f"plan-veto-{uuid4()}"),
            owner_resolver=lambda _request: {
                "kind": "world", "id": "world:one", "name": "World One",
            },
            work_resolver=lambda _request, _owner: work,
            graph_resolver=lambda *_args: pytest.fail("generic Graph resolver was used"),
            plan_graph_resolver=lambda *_args: bootstrap,
            runtime=BudgetVetoRuntime(
                result, authorize_first=authorize_first,
                reject_at_adapter=reject_at_adapter,
            ),
            conversation_service=fake,
        )

    caplog.clear()
    with pytest.raises(AgentTurnServiceError) as veto:
        execute_budget_result(AgentRuntimeResult(
            status="error", error_code="request_budget_exceeded",
            error_message="PRIVATE_PLAN_BODY api_key=sk-secret-shaped",
            observed_model_call_count=0,
            runtime_metadata={"host_phase_spans": [{"name": "rung3_plugin_discovery"}]},
        ))
    assert veto.value.code == "provider_envelope_over_budget"
    assert veto.value.status_code == 413
    assert veto.value.provider_dispatched is False
    assert "PRIVATE_PLAN_BODY" not in caplog.text
    assert "sk-secret-shaped" not in caplog.text
    assert "rung3_plugin_discovery" in caplog.text
    assert fake.accepted_count == 0
    assert fake.authorize_count == 0

    for uncertain in (
        AgentRuntimeResult(status="error", error_code="request_budget_exceeded"),
        AgentRuntimeResult(
            status="error", error_code="request_budget_exceeded",
            observed_model_call_count=1,
        ),
        AgentRuntimeResult(
            status="error", error_code="request_budget_exceeded",
            model_calls=[{"provider": "openai-api"}],
            observed_model_call_count=1,
        ),
    ):
        with pytest.raises(AgentTurnServiceError) as caught:
            execute_budget_result(uncertain)
        assert caught.value.code == "plan_context_delivery_failure"
        assert caught.value.provider_dispatched is None
        assert fake.accepted_count == 0

    for ambiguous_denial in (
        AgentRuntimeResult(status="error", error_code="provider_authorization_denied"),
        AgentRuntimeResult(
            status="error", error_code="provider_authorization_denied",
            observed_model_call_count=0,
        ),
        AgentRuntimeResult(
            status="error", error_code="provider_authorization_denied",
            observed_model_call_count=1,
        ),
        AgentRuntimeResult(
            status="error", error_code="provider_authorization_unavailable",
            observed_model_call_count=0,
        ),
    ):
        with pytest.raises(AgentTurnServiceError) as uncertain:
            execute_budget_result(ambiguous_denial)
        assert uncertain.value.code == "plan_context_delivery_failure"
        assert uncertain.value.status_code == 503
        assert uncertain.value.provider_dispatched is None
        assert fake.accepted_count == 0

    persistence_denial_calls: list[bool] = []

    def refuse_accept(_service: Any, _request: Any, **_kwargs: Any) -> Turn:
        persistence_denial_calls.append(True)
        raise ValueError("PRIVATE_PERSISTENCE_DIAGNOSTIC")

    with monkeypatch.context() as rejected_persistence:
        rejected_persistence.setattr(service_module, "_accept_world_turn", refuse_accept)
        with pytest.raises(AgentTurnServiceError) as denied_by_adapter:
            execute_budget_result(AgentRuntimeResult(
                status="error", error_code="provider_authorization_denied",
                observed_model_call_count=0,
            ), reject_at_adapter=True)
    assert denied_by_adapter.value.code == "turn_persistence_indeterminate"
    assert denied_by_adapter.value.status_code == 503
    assert denied_by_adapter.value.provider_dispatched is None
    assert "PRIVATE_PERSISTENCE_DIAGNOSTIC" not in str(denied_by_adapter.value)
    assert "PRIVATE_PERSISTENCE_DIAGNOSTIC" not in caplog.text
    assert persistence_denial_calls == [True]
    assert fake.accepted_count == 0
    assert fake.authorize_count == 0

    with pytest.raises(AgentTurnServiceError) as after_authorization:
        execute_budget_result(AgentRuntimeResult(
            status="error", error_code="request_budget_exceeded",
            observed_model_call_count=0,
        ), authorize_first=True)
    assert after_authorization.value.code == "plan_context_delivery_failure"
    assert after_authorization.value.provider_dispatched is None
    assert fake.authorize_count == 1

    with pytest.raises(AgentTurnServiceError) as denial_after_authorization:
        execute_budget_result(AgentRuntimeResult(
            status="error", error_code="provider_authorization_denied",
            observed_model_call_count=0,
        ), authorize_first=True)
    assert denial_after_authorization.value.code == "plan_context_delivery_failure"
    assert denial_after_authorization.value.status_code == 503
    assert denial_after_authorization.value.provider_dispatched is None
    assert fake.authorize_count == 2

    fake = FakeExecutionPort()

    response = execute_agent_turn(
        request,
        root=Path("/tmp"),
        pointer_store=HermesSessionPointerStore(Path("/tmp") / f"plan-policy-{uuid4()}"),
        owner_resolver=lambda _request: {
            "kind": "world", "id": "world:one", "name": "World One",
        },
        work_resolver=lambda _request, _owner: work,
        graph_resolver=lambda *_args: pytest.fail("generic Graph resolver was used"),
        plan_graph_resolver=lambda *_args: bootstrap,
        runtime=GuardedRuntime(),
        conversation_service=fake,
    )
    assert response.schema_ == "dmb_agent_turn_response_v2"
    assert response.plan_context.delivery_replay is False
    assert response.plan_context.completion is not None
    assert response.answer.text == "The keeper waits."
    assert fake.turn is not None and fake.turn.status == "completed"


@pytest.mark.parametrize(
    ("status", "completion_present"),
    [("completed", False), ("running", True), ("failed", True)],
)
def test_history_projection_requires_completion_to_match_lifecycle(
    status: str, completion_present: bool
) -> None:
    with pytest.raises(AgentTurnServiceError, match="completion"):
        project_plan_turn_context(
            _policy_turn(status=status, completion_present=completion_present),
            delivery_replay=False,
        )


class FakeRuntime:
    descriptor = AgentRuntimeDescriptor(
        runtime_id="fake",
        trace_backend="fake",
        trace_runtime="test",
        trace_mode="conversation",
    )

    def __init__(self) -> None:
        self.invocations = []
        self.result: AgentRuntimeResult | None = None

    def run(self, invocation: Any) -> AgentRuntimeResult:
        self.invocations.append(invocation)
        if self.result is not None:
            return self.result
        return AgentRuntimeResult(
            status="ok",
            final_text="Hello.",
            runtime_session_id="runtime-session-1",
        )


def _plan_work(_request: Any, _owner: Any) -> AgentTurnResolvedWork:
    return AgentTurnResolvedWork(
        kind="plan",
        object_id="plan:one",
        revision=3,
        changed_since_expected=False,
        owner_kind=None,
        owner_id=None,
    )


def _plan_request() -> AgentTurnRequest:
    return _request(surface={"surface_id": "plan", "instance_id": "plan-main"})


def _pinned_plan_request() -> AgentTurnRequest:
    return _request(
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
        primary_work={
            "kind": "plan",
            "object_id": "plan:one",
            "expected_revision": 7,
            "expected_revision_n": 4,
            "expected_content_sha256": "b" * 64,
        },
        client_work_state="saved_dirty",
        message="What is beneath the black arch?",
    )


def _pinned_plan_work(markdown: str) -> AgentTurnResolvedWork:
    return AgentTurnResolvedWork(
        kind="plan",
        object_id="plan:one",
        revision=7,
        changed_since_expected=False,
        owner_kind="world",
        owner_id="world:one",
        world_id="world:one",
        content_basis=AgentTurnContentBasis(
            world_id="world:one",
            document_id="plan:one",
            object_revision=7,
            work_revision_id="work-revision-4",
            revision_n=4,
            content_sha256="b" * 64,
            committed_status="committed",
            has_divergent_working_copy=True,
        ),
        plan_markdown=markdown,
    )


def test_plan_turn_sends_exact_committed_markdown_and_returns_source_free_basis(
    tmp_path: Path,
) -> None:
    markdown = "# Saved Plan\n\nThe keeper waits below the black arch.\n"
    runtime = FakeRuntime()
    response = execute_agent_turn(
        _pinned_plan_request(),
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda _request: {
            "kind": "world",
            "id": "world:one",
            "name": "The Glass Orchard",
        },
        work_resolver=lambda _request, _owner: _pinned_plan_work(markdown),
        graph_resolver=lambda *_args: pytest.fail(
            "Plan content turn must not resolve graph"
        ),
        runtime=runtime,
    )

    assert len(runtime.invocations) == 1
    prefix, payload = runtime.invocations[0].message.split("\n", maxsplit=1)
    assert prefix.startswith("Answer the user's question using the committed Plan")
    assert json.loads(payload) == {
        "committed_plan_markdown": markdown,
        "user_question": "What is beneath the black arch?",
    }
    assert response.graph.status == "not_requested"
    assert (
        response.primary_work.content_basis == _pinned_plan_work(markdown).content_basis
    )
    assert markdown not in response.model_dump_json(by_alias=True)
    assert response.answer.trace.get("context_summary", {}).get("content_basis") is None


def test_targeted_plan_turn_sends_server_resolved_target_and_exact_basis_to_runtime(
    tmp_path: Path,
) -> None:
    markdown = """# Saved Plan

<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->
## Arrival
The keeper waits below the black arch.
"""
    request = _pinned_plan_request().model_copy(update={
        "playable_target": SubmittedPlanPlayableTargetV1(
            schema="dmb_plan_playable_target_v1", kind="scene", id="scene:arrival"
        )
    })
    runtime = FakeRuntime()
    response = execute_agent_turn(
        request,
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda _request: {
            "kind": "world", "id": "world:one", "name": "The Glass Orchard"
        },
        work_resolver=lambda _request, _owner: _pinned_plan_work(markdown),
        graph_resolver=lambda *_args: pytest.fail("Targeted Plan Ask must not resolve Graph"),
        runtime=runtime,
    )

    assert len(runtime.invocations) == 1
    prefix, payload = runtime.invocations[0].message.split("\n", maxsplit=1)
    assert prefix.startswith("Answer the user's question using the committed Plan")
    assert json.loads(payload) == {
        "committed_plan_markdown": markdown,
        "user_question": "What is beneath the black arch?",
        "focus_metadata": {
            "playable_target": {
                "kind": "scene",
                "id": "scene:arrival",
                "marker_grammar_version": "v1",
            },
            "work_revision": {
                "work_revision_id": "work-revision-4",
                "revision_n": 4,
                "content_sha256": "b" * 64,
                "object_revision": 7,
            },
        },
    }
    assert response.graph.status == "not_requested"
    assert "focus_metadata" not in response.model_dump_json(by_alias=True)
    assert request.model_dump_json(by_alias=True).find("The keeper waits") == -1


@pytest.mark.parametrize(
    ("grammar", "marker"),
    [
        ("v1", "<!-- dmb-playable-element:v1 kind=beat id=beat:a -->"),
        ("v2", "<!-- dmb-playable-element:v2 kind=beat id=beat:a beat_kind=spine -->"),
    ],
)
def test_targeted_plan_service_accepts_shortest_canonical_beat_id(
    tmp_path: Path, grammar: str, marker: str
) -> None:
    heading = "###" if grammar == "v1" else "##"
    prior_scene = (
        "<!-- dmb-playable-element:v1 kind=scene id=scene:s -->\n## S\n\n"
        if grammar == "v1"
        else ""
    )
    markdown = f"# Saved Plan\n\n{prior_scene}{marker}\n{heading} A\nA one-character beat ID.\n"
    request = _pinned_plan_request().model_copy(update={
        "playable_target": SubmittedPlanPlayableTargetV1(
            schema="dmb_plan_playable_target_v1", kind="beat", id="beat:a"
        )
    })
    runtime = FakeRuntime()
    execute_agent_turn(
        request,
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda _request: {
            "kind": "world", "id": "world:one", "name": "The Glass Orchard"
        },
        work_resolver=lambda _request, _owner: _pinned_plan_work(markdown),
        graph_resolver=lambda *_args: pytest.fail("Targeted Plan Ask must not resolve Graph"),
        runtime=runtime,
    )

    _prefix, payload = runtime.invocations[0].message.split("\n", maxsplit=1)
    assert json.loads(payload)["focus_metadata"] == {
        "playable_target": {
            "kind": "beat",
            "id": "beat:a",
            "marker_grammar_version": grammar,
        },
        "work_revision": {
            "work_revision_id": "work-revision-4",
            "revision_n": 4,
            "content_sha256": "b" * 64,
            "object_revision": 7,
        },
    }


def test_completed_targeted_retry_replays_frozen_receipt_without_resolving_or_dispatching(
    tmp_path: Path,
) -> None:
    request = _pinned_plan_request().model_copy(update={
        "playable_target": SubmittedPlanPlayableTargetV1(
            schema="dmb_plan_playable_target_v1", kind="scene", id="scene:arrival"
        )
    })
    work_revision_id = uuid4()
    provenance = TurnProvenance(
        world_id="world:one",
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id="plan-main",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="plan:one",
            revision="7",
            content_sha256="b" * 64,
            object_revision=7,
            work_revision_id=work_revision_id,
            revision_n=4,
        ),
        supporting_work=[encode_plan_playable_target_reference(PlanPlayableTargetReceiptV1(
            schema="dmb_plan_playable_target_receipt_v1",
            kind="scene",
            id="scene:arrival",
            marker_grammar_version="v1",
        ))],
        selected_object=HistoricalReference(resolution="absent"),
    )
    now = datetime.now(UTC)
    completed = Turn(
        turn_id=uuid4(),
        conversation_id=uuid4(),
        world_id="world:one",
        idempotency_key=uuid4(),
        sequence=3,
        revision=4,
        status="completed",
        user_text=request.message,
        assistant_text="The arrival is guarded.",
        failure_code=None,
        provenance=provenance,
        submitted_intent_fingerprint_v1="a" * 64,
        attempt=1,
        accepted_at=now,
        completed_at=now,
        updated_at=now,
    )

    class CompletedConversationService:
        submitted_intent = None

        def reconcile_turn(self, _world_id: str, _key: Any, submitted_intent: Any) -> Turn:
            self.submitted_intent = submitted_intent
            return completed

    conversation_service = CompletedConversationService()
    runtime = FakeRuntime()
    response = execute_agent_turn(
        request,
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda _request: {"kind": "world", "id": "world:one", "name": "The Glass Orchard"},
        work_resolver=lambda *_args: pytest.fail("Completed target replay must not resolve current Plan"),
        graph_resolver=lambda *_args: pytest.fail("Target replay must not resolve Graph"),
        runtime=runtime,
        conversation_service=conversation_service,  # type: ignore[arg-type]
    )

    assert conversation_service.submitted_intent.playable_target.id == "scene:arrival"
    assert response.answer.text == "The arrival is guarded."
    assert response.conversation.conversation_id == completed.conversation_id
    assert response.answer.trace["runtime"] == "durable_receipt"
    assert response.primary_work.content_basis is None
    assert runtime.invocations == []


def test_target_absent_from_committed_revision_stops_before_runtime_dispatch(
    tmp_path: Path,
) -> None:
    request = _pinned_plan_request().model_copy(update={
        "playable_target": SubmittedPlanPlayableTargetV1(
            schema="dmb_plan_playable_target_v1", kind="scene", id="scene:draft-only"
        )
    })
    runtime = FakeRuntime()
    with pytest.raises(AgentTurnServiceError) as error:
        execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
            owner_resolver=lambda _request: {"kind": "world", "id": "world:one", "name": "The Glass Orchard"},
            work_resolver=lambda _request, _owner: _pinned_plan_work(
                "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->\n## Arrival\n"
            ),
            graph_resolver=lambda *_args: pytest.fail("Target validation must stay graphless"),
            runtime=runtime,
        )
    assert error.value.code == "plan_playable_target_unavailable"
    assert runtime.invocations == []


def test_large_committed_plan_is_not_rejected_as_a_short_user_question(
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime()
    pointer_dir = tmp_path / "pointers"
    markdown = "# Committed Plan\n" + "x" * 50_000
    execute_agent_turn(
        _pinned_plan_request(),
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(pointer_dir),
        owner_resolver=lambda _request: {
            "kind": "world",
            "id": "world:one",
            "name": "The Glass Orchard",
        },
        work_resolver=lambda _request, _owner: _pinned_plan_work(markdown),
        graph_resolver=lambda *_args: pytest.fail(
            "Plan content turn must not resolve graph"
        ),
        runtime=runtime,
    )
    assert len(runtime.invocations) == 1
    assert json.loads(runtime.invocations[0].message.split("\n", 1)[1])[
        "committed_plan_markdown"
    ] == markdown


def test_no_graph_turn_uses_no_scope_runtime_and_only_structured_pointer_store(
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime()

    def unexpected_graph(*_args: Any) -> Any:
        raise AssertionError("no-graph turn must not resolve graph authority")

    response = execute_agent_turn(
        _request(),
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointer-only"),
        owner_resolver=lambda _request: None,
        work_resolver=lambda _request, _owner: None,
        graph_resolver=unexpected_graph,
        runtime=runtime,
    )

    assert len(runtime.invocations) == 1
    invocation = runtime.invocations[0]
    assert invocation.context_packet.world_scope is None
    assert invocation.context_packet.retrieval_session is None
    assert invocation.capability_policy.policy_id == CONVERSATION_ONLY_POLICY_ID
    assert response.graph.status == "not_requested"
    assert response.answer.graph_grounded is False
    assert response.conversation.pointer_id
    pointer_path = tmp_path / "pointer-only" / "hermes_thread_pointers.json"
    assert pointer_path.is_file()


@pytest.mark.parametrize(
    ("surface_id", "label"),
    [
        ("index", "Index"),
        ("plan", "Plan"),
        ("play", "Play"),
        ("build", "Build"),
        ("ingest", "Ingest"),
        ("combat", "Combat Tracker"),
    ],
)
def test_no_work_turn_carries_surface_and_verified_world_through_real_adapters(
    tmp_path: Path, surface_id: str, label: str
) -> None:
    from apps.live_control_server.services.agent_surface_context import (
        render_agent_surface_context,
    )
    from apps.live_control_server.services.hermes_agent_runtime import (
        map_invocation_to_hermes_request,
    )
    from apps.live_control_server.services.hermes_graph_agent import (
        _build_ephemeral_system_prompt,
    )
    from apps.live_control_server.services.pydantic_ai_agent_runtime import (
        pydantic_ai_agent_instructions,
    )

    runtime = FakeRuntime()
    request = _request(
        surface={"surface_id": surface_id, "instance_id": f"{surface_id}-pane-1"},
        owner_scope={"kind": "world", "world_id": "world:one"},
    )
    execute_agent_turn(
        request,
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda _request: {
            "kind": "world",
            "id": "world:one",
            "name": "The Glass Orchard",
        },
        work_resolver=lambda _request, _owner: None,
        graph_resolver=lambda *_args: pytest.fail(
            "no-graph turn resolved graph authority"
        ),
        runtime=runtime,
    )

    invocation = runtime.invocations[0]
    assert invocation.plan_continuity_turn is False
    context = invocation.context_packet.surface_context
    assert context is not None
    assert context.surface_id == surface_id
    assert context.surface_instance_id == f"{surface_id}-pane-1"
    assert context.current_owner is not None
    assert context.current_owner.owner_id == "world:one"
    assert invocation.context_packet.world_scope is None
    assert invocation.context_packet.retrieval_session is None
    rendered = render_agent_surface_context(context)
    assert rendered is not None
    assert label in rendered
    assert 'Current World: "The Glass Orchard"' in rendered
    assert "world:one" not in rendered

    hermes_request = map_invocation_to_hermes_request(invocation)
    assert hermes_request.world_id is None
    assert hermes_request.campaign_id is None
    assert hermes_request.retrieval_session is None
    assert hermes_request.capability_policy.mode == "conversation_only"
    assert hermes_request.capability_policy.graph_scope is None
    assert hermes_request.capability_policy.enabled_toolsets == ()
    assert hermes_request.plan_continuity_turn is False
    hermes_prompt = _build_ephemeral_system_prompt(
        hermes_request.capability_policy,
        hermes_request,
        retrieval_session_packet=None,
    )
    assert label in hermes_prompt
    assert 'Current World: "The Glass Orchard"' in hermes_prompt
    pydantic_prompt = pydantic_ai_agent_instructions(invocation)
    assert label in pydantic_prompt
    assert 'Current World: "The Glass Orchard"' in pydantic_prompt
    assert "No graph retrieval is performed on this turn" in pydantic_prompt


def test_server_resolves_saved_plan_continuity_flag_before_runtime_dispatch(
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime()
    execute_agent_turn(
        _plan_request(),
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda _request: None,
        work_resolver=_plan_work,
        graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
        runtime=runtime,
    )

    assert len(runtime.invocations) == 1
    assert runtime.invocations[0].plan_continuity_turn is True


def test_graphless_followup_reuses_same_binding_without_current_graph_authority(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from apps.live_control_server.services.hermes_agent_runtime import (
        map_invocation_to_hermes_request,
    )
    from apps.live_control_server.services.hermes_graph_agent import (
        _build_ephemeral_system_prompt,
    )

    runtime = FakeRuntime()
    pointer_store = HermesSessionPointerStore(tmp_path / "pointers")

    def owner(_request):
        return {
            "kind": "world",
            "id": "world:one",
            "name": "The Glass Orchard",
        }

    def graph(_request, _owner, _work):
        return (
            {
                "status": "ready",
                "world_id": "world:one",
                "campaign_id": "",
                "scope_mode": "world",
                "revision_id": "revision-one",
                "head_revision_id": "revision-one",
                "is_head": True,
                "focus": {"kind": "none"},
                "matched_node_ids": ["node:one"],
                "nodes": [{"node_id": "node:one", "label": "The Glass Orchard"}],
            },
            AgentWorldScope(
                world_id="world:one",
                campaign_id="",
                focus={"kind": "none"},
                admissibility="gm",
                revision_id="revision-one",
                scope_mode="world",
            ),
        )

    first = _request(
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
        graph_request={
            "mode": "world",
            "world_id": "world:one",
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        },
    )
    execute_agent_turn(
        first,
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=owner,
        work_resolver=lambda _request, _owner: None,
        graph_resolver=graph,
        runtime=runtime,
    )
    second = _request(
        turn_id="turn-2",
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
    )
    response = execute_agent_turn(
        second,
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=owner,
        work_resolver=lambda _request, _owner: None,
        graph_resolver=lambda *_args: pytest.fail(
            "graphless follow-up must not retrieve"
        ),
        runtime=runtime,
    )

    assert runtime.invocations[1].run_options.runtime_session_id == "runtime-session-1"
    assert runtime.invocations[1].context_packet.world_scope is None
    assert runtime.invocations[1].context_packet.retrieval_session is None
    assert response.graph.status == "not_requested"
    assert response.answer.graph_grounded is False
    assert response.conversation.pointer_status == "reused"
    hermes_request = map_invocation_to_hermes_request(runtime.invocations[1])
    prompt = _build_ephemeral_system_prompt(
        hermes_request.capability_policy,
        hermes_request,
        retrieval_session_packet=None,
    )
    assert "No graph retrieval is performed on this turn" in prompt
    assert "historical graph-derived statements" in prompt
    assert "not revalidated as current graph evidence" in prompt
    assert "request an explicit graph-retrieval turn" in prompt


def test_expired_structured_binding_stops_before_runtime_and_removes_profile(
    tmp_path: Path,
) -> None:
    from datetime import datetime, timedelta, timezone

    pointer_base = tmp_path / "pointers"
    pointer_store = HermesSessionPointerStore(pointer_base)
    binding = pointer_store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="expired-session",
    )
    profile = pointer_store.structured_profile_home(binding.hermes_session_id)
    profile.mkdir(parents=True)
    (profile / "state.db").write_text("native state", encoding="utf-8")
    store_path = pointer_base / "hermes_thread_pointers.json"
    payload = json.loads(store_path.read_text(encoding="utf-8"))
    key = next(iter(payload["structured_bindings"]))
    payload["structured_bindings"][key]["updated_at"] = (
        datetime.now(timezone.utc) - timedelta(days=8)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    store_path.write_text(json.dumps(payload), encoding="utf-8")
    runtime = FakeRuntime()

    with pytest.raises(AgentTurnServiceError) as error:
        execute_agent_turn(
            _plan_request(),
            root=tmp_path,
            pointer_store=pointer_store,
            owner_resolver=lambda _request: None,
            work_resolver=_plan_work,
            graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
            runtime=runtime,
        )

    assert error.value.status_code == 409
    assert error.value.code == "hermes_continuity_unavailable"
    assert not runtime.invocations
    assert not profile.exists()
    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    assert persisted["structured_bindings"][key]["status"] == "expired"


def test_rejected_plan_pointer_does_not_change_other_agent_surface_behavior(
    tmp_path: Path,
) -> None:
    from datetime import datetime, timedelta, timezone

    pointer_base = tmp_path / "pointers"
    pointer_store = HermesSessionPointerStore(pointer_base)
    pointer_store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="expired-session",
    )
    store_path = pointer_base / "hermes_thread_pointers.json"
    payload = json.loads(store_path.read_text(encoding="utf-8"))
    key = next(iter(payload["structured_bindings"]))
    payload["structured_bindings"][key]["updated_at"] = (
        datetime.now(timezone.utc) - timedelta(days=8)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    store_path.write_text(json.dumps(payload), encoding="utf-8")
    runtime = FakeRuntime()
    request = _request(surface={"surface_id": "build", "instance_id": "plan-main"})

    response = execute_agent_turn(
        request,
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=lambda _request: None,
        work_resolver=_plan_work,
        graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
        runtime=runtime,
    )

    assert response.answer.status == "ok"
    assert len(runtime.invocations) == 1
    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    assert persisted["structured_bindings"][key]["status"] == "expired"


def test_native_continuity_failure_revokes_binding_without_returning_answer(
    tmp_path: Path,
) -> None:
    pointer_base = tmp_path / "pointers"
    pointer_store = HermesSessionPointerStore(pointer_base)
    binding = pointer_store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="session-original",
    )
    profile = pointer_store.structured_profile_home(binding.hermes_session_id)
    profile.mkdir(parents=True)
    (profile / "state.db").write_text("native state", encoding="utf-8")
    runtime = FakeRuntime()
    runtime.result = AgentRuntimeResult(
        status="error",
        runtime_session_id="session-original",
        error_code="hermes_continuity_unavailable",
        error_message="missing native history",
    )

    with pytest.raises(AgentTurnServiceError) as error:
        execute_agent_turn(
            _plan_request(),
            root=tmp_path,
            pointer_store=pointer_store,
            owner_resolver=lambda _request: None,
            work_resolver=_plan_work,
            graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
            runtime=runtime,
        )

    assert error.value.status_code == 409
    assert error.value.code == "hermes_continuity_unavailable"
    assert len(runtime.invocations) == 1
    assert not profile.exists()
    payload = json.loads((pointer_base / "hermes_thread_pointers.json").read_text())
    stored = next(iter(payload["structured_bindings"].values()))
    assert stored["status"] == "invalid"


def test_changed_hermes_session_identity_revokes_saved_plan_binding(
    tmp_path: Path,
) -> None:
    pointer_base = tmp_path / "pointers"
    pointer_store = HermesSessionPointerStore(pointer_base)
    binding = pointer_store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="session-original",
    )
    profile = pointer_store.structured_profile_home(binding.hermes_session_id)
    profile.mkdir(parents=True)
    (profile / "state.db").write_text("native state", encoding="utf-8")
    runtime = FakeRuntime()
    runtime.result = AgentRuntimeResult(
        status="ok",
        final_text="This answer must not be shown.",
        runtime_session_id="session-different",
    )

    with pytest.raises(AgentTurnServiceError) as error:
        execute_agent_turn(
            _plan_request(),
            root=tmp_path,
            pointer_store=pointer_store,
            owner_resolver=lambda _request: None,
            work_resolver=_plan_work,
            graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
            runtime=runtime,
        )

    assert error.value.code == "hermes_continuity_unavailable"
    assert "This answer must not be shown." not in str(error.value)
    assert not profile.exists()
    payload = json.loads((pointer_base / "hermes_thread_pointers.json").read_text())
    stored = next(iter(payload["structured_bindings"].values()))
    assert stored["status"] == "invalid"


def test_runtime_error_does_not_create_or_renew_structured_pointer(
    tmp_path: Path,
) -> None:
    pointer_store = HermesSessionPointerStore(tmp_path / "pointers")
    runtime = FakeRuntime()
    runtime.result = AgentRuntimeResult(
        status="error",
        runtime_session_id="unpersisted-session",
        error_code="provider_unavailable",
        error_message="provider failed",
    )

    response = execute_agent_turn(
        _plan_request(),
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=lambda _request: None,
        work_resolver=_plan_work,
        graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
        runtime=runtime,
    )

    assert response.answer.status == "error"
    assert not (tmp_path / "pointers" / "hermes_thread_pointers.json").exists()


def test_successful_persisted_plan_turn_refreshes_sliding_idle_ttl(
    tmp_path: Path,
) -> None:
    from datetime import datetime, timedelta, timezone

    pointer_base = tmp_path / "pointers"
    pointer_store = HermesSessionPointerStore(pointer_base)
    pointer_store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="plan-session",
    )
    store_path = pointer_base / "hermes_thread_pointers.json"
    payload = json.loads(store_path.read_text(encoding="utf-8"))
    key = next(iter(payload["structured_bindings"]))
    payload["structured_bindings"][key]["updated_at"] = (
        datetime.now(timezone.utc) - timedelta(days=6)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    store_path.write_text(json.dumps(payload), encoding="utf-8")
    runtime = FakeRuntime()
    runtime.result = AgentRuntimeResult(
        status="ok",
        final_text="Plan reply.",
        runtime_session_id="plan-session",
    )

    response = execute_agent_turn(
        _plan_request(),
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=lambda _request: None,
        work_resolver=_plan_work,
        graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
        runtime=runtime,
    )

    assert response.answer.status == "ok"
    refreshed = json.loads(store_path.read_text(encoding="utf-8"))
    binding = refreshed["structured_bindings"][key]
    updated_at = datetime.fromisoformat(binding["updated_at"].replace("Z", "+00:00"))
    assert updated_at > datetime.now(timezone.utc) - timedelta(minutes=1)
    assert binding["hermes_session_id"] == "plan-session"


def test_unresolvable_requested_graph_fails_before_runtime(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    request = _request(
        graph_request={
            "mode": "world",
            "world_id": "world-1",
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        }
    )

    def reject_graph(*_args: Any) -> Any:
        raise AgentTurnServiceError(
            "foreign graph", code="graph_scope_rejected", status_code=403
        )

    with pytest.raises(AgentTurnServiceError, match="foreign graph"):
        execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
            owner_resolver=lambda _request: None,
            work_resolver=lambda _request, _owner: None,
            graph_resolver=reject_graph,
            runtime=runtime,
        )
    assert runtime.invocations == []


def test_successful_plan_turn_returns_one_sanitized_trace_event(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    prompt_secret = "plan-prompt-secret-6d3b"
    runtime = FakeRuntime()
    runtime.result = AgentRuntimeResult(
        status="ok",
        final_text="ANSWER_SENTINEL synthetic answer",
        runtime_metadata={
            "host_phase_spans": [
                {
                    "span_id": "0123456789abcdef0123456789abcdef:1",
                    "parent_span_id": None,
                    "kind": "phase",
                    "name": "host_worker_result_wait",
                    "status": "ok",
                    "started_at": "2026-10-01T23:59:59.991Z",
                    "completed_at": "2026-10-02T00:00:00Z",
                    "duration_ms": 9,
                    "attributes": {
                        "host_phase_group_id": "0123456789abcdef0123456789abcdef",
                        "request_summary": "TRACE_LEAK_SENTINEL from innocuous field",
                    },
                    "extra_context": "TRACE_LEAK_SENTINEL from arbitrary field",
                },
                {
                    "span_id": "0123456789abcdef0123456789abcdef:2",
                    "name": "host_worker_result_wait",
                    "status": "ok",
                    "started_at": "2026-10-02T00:00:00Z",
                    "completed_at": "2026-10-02T00:00:00Z",
                    "duration_ms": -1,
                    "attributes": {
                        "host_phase_group_id": "0123456789abcdef0123456789abcdef"
                    },
                },
                {
                    "span_id": "abcdef0123456789abcdef0123456789:1",
                    "name": "rung3_bootstrap_logger_home_setup",
                    "status": "ok",
                    "started_at": "2026-10-01T23:59:59.991Z",
                    "completed_at": "2026-10-02T00:00:00Z",
                    "duration_ms": 9,
                    "attributes": {
                        "host_phase_group_id": "abcdef0123456789abcdef0123456789"
                    },
                },
                {
                    "span_id": "TRACE_LEAK_SENTINEL",
                    "name": "unapproved_phase_name",
                    "status": "ok",
                    "started_at": "2026-10-02T00:00:00Z",
                    "completed_at": "2026-10-02T00:00:00Z",
                    "duration_ms": 9,
                    "attributes": {},
                },
            ]
        },
    )
    request = _request(
        message=prompt_secret,
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:plan"},
    )

    with caplog.at_level(logging.INFO, logger="dmb.agent.turn_trace"):
        response = execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
            owner_resolver=lambda _request: {
                "kind": "world",
                "id": "world:plan",
                "name": "Trace Test World",
            },
            work_resolver=lambda _request, _owner: None,
            graph_resolver=lambda *_args: pytest.fail(
                "graphless Plan turn must not resolve graph authority"
            ),
            runtime=runtime,
        )

    trace = response.answer.trace
    trace_events = [
        record.getMessage()
        for record in caplog.records
        if record.name == "dmb.agent.turn_trace"
        and record.getMessage().startswith("dmb_agent_turn_trace ")
    ]

    assert response.answer.status == "ok"
    assert trace["status"] == "ok"
    assert len(trace_events) == 1
    logged_trace = json.loads(trace_events[0].removeprefix("dmb_agent_turn_trace "))
    assert logged_trace["trace_id"] == trace["trace_id"]
    runtime_span = next(
        span for span in trace["spans"] if span["name"] == "runtime_dispatch"
    )
    host_span = next(
        span for span in trace["spans"] if span["name"] == "host_worker_result_wait"
    )
    worker_span = next(
        span
        for span in trace["spans"]
        if span["name"] == "rung3_bootstrap_logger_home_setup"
    )
    assert sum(span.get("name", "").startswith("host_") for span in trace["spans"]) == 1
    assert sum(span.get("name", "").startswith("rung3_") for span in trace["spans"]) == 1
    assert host_span["parent_span_id"] == runtime_span["span_id"]
    assert worker_span["parent_span_id"] == runtime_span["span_id"]
    assert prompt_secret not in json.dumps(trace["spans"])
    assert "ANSWER_SENTINEL" not in json.dumps(trace)
    assert "TRACE_LEAK_SENTINEL" not in json.dumps(trace)
    assert prompt_secret not in trace_events[0]
    assert "ANSWER_SENTINEL" not in trace_events[0]
    assert "TRACE_LEAK_SENTINEL" not in trace_events[0]
