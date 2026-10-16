from __future__ import annotations

import json
import logging
from dataclasses import replace
from hashlib import sha256
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from application_state.errors import ApplicationStateConflictError
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
        _included_tool_payloads,
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
    source_call = {**call, "call_id": "source-1", "name": "read_graph_source"}
    source_output = {**output, "call_id": "source-1", "output": "source excerpt"}
    assert _included_tool_payloads(
        {"input": [source_call, source_output]}, tool_name="read_graph_source"
    ) == ["source excerpt"]
    assert _included_graph_operation_payloads({"input": [source_call, source_output]}) == []


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


@pytest.mark.parametrize('missing_method', [
    'all', 'extend_source_scope', 'authorize_source_read',
    'record_validated_source_read', 'authorize_provider_attempt_v2',
])
def test_plan_context_policy_fails_after_replay_preflight_before_mutable_reads(
    tmp_path: Path, missing_method: str,
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

        def __getattr__(self, name):
            if missing_method == 'all' or name == missing_method:
                return None
            return lambda *_a, **_kw: pytest.fail('incompatible producer must fail before any mutable call')

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


def test_plan_graph_requires_status_derivation_contract(monkeypatch: Any) -> None:
    from application_state.agent_conversation import types as graph_types
    from apps.live_control_server.services import agent_turn_service as service_module

    monkeypatch.delattr(graph_types, "derive_execution_answer_context_status")
    with pytest.raises(AgentTurnServiceError) as caught:
        service_module._app_state_graph_execution_types()
    assert caught.value.code == "plan_graph_execution_unavailable"


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
    assert context.source_open_targets == []
    assert context.evidence_anchor_statuses == []

    with pytest.raises(AgentTurnServiceError, match="historical turn provenance"):
        project_plan_turn_context(_policy_turn(drift=True), delivery_replay=False)


def test_plan_context_wire_preserves_v2_source_read_citation() -> None:
    from apps.live_control_server.models.agent_turn import AgentPlanWorldGraphContextResponseV2

    turn = _cited_card_a_policy_turn()
    completion = turn.completion.model_dump(mode="json", by_alias=True)
    completion["schema"] = "dmb_plan_world_graph_completion_v2"
    completion["citation_map"]["schema"] = "dmb_graph_citation_map_v2"
    completion["citation_map"]["entries"][0].update({
        "source_opened": True, "source_read_ids": ["source-read:one"],
    })
    response = AgentPlanWorldGraphContextResponseV2.model_validate({
        "receipt": turn.graph_context_receipt.model_dump(mode="json", by_alias=True),
        "completion": completion,
        "execution": None,
        "delivery_replay": True,
    })
    wire = response.model_dump(mode="json", by_alias=True)
    assert wire["completion"]["schema"] == "dmb_plan_world_graph_completion_v2"
    assert wire["completion"]["citation_map"]["entries"][0]["source_read_ids"] == [
        "source-read:one"
    ]
    assert wire["completion"]["citation_map"]["entries"][0]["source_opened"] is True
    assert wire["evidence_anchor_statuses"] == []


def test_v2_completion_opens_citation_only_from_producing_source_envelope(
    monkeypatch: Any,
) -> None:
    from application_state.agent_conversation import types as graph_types
    from apps.live_control_server.services import agent_turn_service as service_module

    turn = _cited_card_a_policy_turn()
    receipt = turn.graph_context_receipt
    assert receipt is not None
    scope_anchor = graph_types.GraphSourceScopeAnchorV2(
        anchor_id="anchor:one", evidence_ref_id="evidence-internal-test",
        source_artifact_id="artifact:one", source_revision_id="source-revision:one",
    )
    policy = graph_types.GraphExecutionPolicyV2(
        policy_version="plan_world_graph_execution_v1",
        allowed_graph_operations=["expand_graph_retrieval"],
        max_provider_attempts=4, max_graph_operations=8, max_results_per_operation=512,
        max_total_provider_input_tokens=100_000, max_total_provider_output_tokens=10_000,
        provider_input_accounting=graph_types.GraphExecutionAccountingV1(
            kind="conservative_upper_bound", estimator="utf8_json_bytes_plus_64_per_node_v1",
        ),
        source_opened=False,
        source_read_scope=graph_types.GraphSourceReadScopeV2(
            retrieval_session_id="session:one",
            world_id=receipt.graph_authority.managed_world_id,
            campaign_id=None,
            graph_revision=receipt.graph_authority.graph_revision,
            admitted_anchors=[scope_anchor],
        ),
        max_source_read_calls=8, max_source_read_anchors=8,
        max_source_read_chars=96_000, max_chars_per_source_read=12_000,
    )
    policy_digest = service_module._canonical_sha256({
        "schema": "dmb_agent_plan_world_graph_execution_v2",
        "context_receipt_sha256": receipt.context_receipt_sha256,
        "policy": policy.model_dump(mode="json", by_alias=True),
    })
    read_call_id, read_event_id, attempt_id = uuid4(), uuid4(), uuid4()
    read_auth = graph_types.SourceReadAuthorizationEventV2(
        event_id=uuid4(), sequence=0, kind="source_read_authorized_v2",
        read_call_id=read_call_id,
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=policy_digest,
        retrieval_session_id="session:one",
        world_id=receipt.graph_authority.managed_world_id,
        campaign_id=None, graph_revision=receipt.graph_authority.graph_revision,
        anchors=[scope_anchor], max_chars=4000,
    )
    read_event = graph_types.ValidatedSourceReadEventV2(
        event_id=read_event_id, sequence=1, kind="validated_source_read_v2",
        read_call_id=read_call_id,
        receipts=[graph_types.SourceReadAnchorReceiptV2(
            source_read_id="source-read:one", anchor_id="anchor:one",
            evidence_ref_id="evidence-internal-test", source_artifact_id="artifact:one",
            source_revision_id="source-revision:one", outcome="enough",
            content_sha256="a" * 64, returned_chars=12, truncated=False,
            evidence_sufficiency_status="sufficient",
        )],
    )
    attempt_fields = dict(
        event_id=uuid4(), sequence=2, kind="provider_attempt_authorized_v2",
        provider_attempt_id=attempt_id, envelope_sha256="b" * 64,
        serializer_version="canonical-json-utf8-v1", provider="openai-api",
        model="gpt-6-luna", api_mode="codex_responses",
        tool_schema_sha256="c" * 64,
        input_accounting_kind="conservative_upper_bound",
        input_estimator="utf8_json_bytes_plus_64_per_node_v1",
        input_tokens=1000, output_token_reserve=2048,
        included_assertion_ids=["assertion-internal-test"],
        included_relationship_ids=[],
        included_evidence_ref_ids=["evidence-internal-test"],
        included_graph_event_ids=[],
    )
    attempt = graph_types.ProviderAttemptAuthorizedEventV2(
        **attempt_fields, included_source_read_event_ids=[read_event_id],
    )
    sdk_entered = graph_types.ProviderOutcomeEventV1(
        event_id=uuid4(), sequence=3, kind="provider_outcome",
        provider_attempt_id=attempt_id, outcome="sdk_entered",
    )
    outcome = graph_types.ProviderOutcomeEventV1(
        event_id=uuid4(), sequence=4, kind="provider_outcome",
        provider_attempt_id=attempt_id, outcome="response_received",
    )
    execution = graph_types.PlanWorldGraphExecutionV2(
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=policy_digest,
        policy=policy, events=[read_auth, read_event, attempt, sdk_entered, outcome],
    )
    turn = turn.model_copy(update={"graph_context_execution": execution})
    claim = turn.completion.answer_segments[0].model_dump(mode="json")
    model_answer = json.dumps({
        "answer_context_status": "graph_grounded",
        "answer_segments": [claim],
        "citation_map": {"entries": [{
            **{key: value for key, value in claim.items() if key not in {"kind", "text"}},
            "source_opened": False,
        }]},
    })
    completion, bindings, _answer = service_module._parse_policy_completion(
        model_answer, turn, attempt_id,
    )
    assert bindings == {"claim-internal-test": []}
    citation = completion.citation_map.entries[0]
    assert citation.source_opened is True
    assert citation.source_read_ids == ["source-read:one"]
    binding = graph_types.CompletionBindingEventV1(
        event_id=uuid4(), sequence=5, kind="completion_binding",
        provider_attempt_id=attempt_id,
        completion_sha256=service_module._canonical_sha256(
            completion.model_dump(mode="json", by_alias=True)
        ),
        claim_graph_event_ids=bindings,
    )
    completed_execution = graph_types.PlanWorldGraphExecutionV2(
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=policy_digest, policy=policy,
        events=[read_auth, read_event, attempt, sdk_entered, outcome, binding],
    )
    completed_turn = turn.model_copy(update={
        "completion": completion, "graph_context_execution": completed_execution,
    })
    from types import SimpleNamespace
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct_reads,
    )

    def no_context_service(_world: str) -> Any:
        raise RuntimeError("synthetic context service unavailable")

    with monkeypatch.context() as unavailable_scope:
        unavailable_scope.setattr(
            direct_reads, "direct_services_from_config", no_context_service
        )
        projected = project_plan_turn_context(completed_turn, delivery_replay=True)
        assert project_plan_turn_context(
            completed_turn, delivery_replay=False
        ).source_open_targets == projected.source_open_targets
    assert projected.completion.citation_map.entries[0].source_opened is True
    assert len(projected.source_open_targets) == 1
    assert [(item.status, item.target_count) for item in (
        projected.evidence_anchor_statuses
    )] == [("available", 1)]
    assert projected.related_recap_context_statuses[0].status == "metadata_unavailable"
    target = projected.source_open_targets[0]
    assert target.kind == "evidence_anchor"
    assert (
        target.claim_id, target.anchor_id, target.evidence_ref_id,
        target.source_artifact_id, target.source_revision_id,
    ) == (
        "claim-internal-test", "anchor:one", "evidence-internal-test",
        "artifact:one", "source-revision:one",
    )
    assert (target.managed_world_id, target.native_world_id, target.graph_revision) == (
        receipt.graph_authority.managed_world_id,
        receipt.graph_authority.native_world_id,
        receipt.graph_authority.graph_revision,
    )
    assert (target.source_read_id, target.read_outcome) == ("source-read:one", "enough")
    descriptors = [SimpleNamespace(
        context_anchor_id="dm-context-anchor:v2:one",
        world_id=receipt.graph_authority.native_world_id,
        campaign_id="campaign:one",
        graph_revision_id=receipt.graph_authority.graph_revision,
        source_artifact_id="artifact:one",
        source_revision_id="source-revision:one",
        source_uri="repo://recaps/session-22.md",
        content_sha256="d" * 64,
        section_selector=SimpleNamespace(
            schema_version="dm_recap_context_section_selector_v2",
            kind="recap_section", policy="markdown-session-recap-v2",
            expected_session_id="session-22",
            canonical_heading="# Session 22 Recap", legacy_session_heading="## Session 22:", legacy_recap_marker="**Recap**:",
        ),
    )]
    good_descriptor = descriptors[0]

    def snapshot(projection: Any) -> Any:
        return SimpleNamespace(
            world_id=projection.world_id,
            campaign_id=projection.campaign_id,
            scope_mode=projection.scope_mode,
            admissibility=projection.admissibility,
            focus=projection.focus,
            revision_id=projection.revision_pin,
        )

    metadata_state = {"evidence_complete": True, "index_complete": True}

    class RelatedMetadata:
        def get_evidence(self, projection: Any, *, target: Any, max_anchors: int) -> Any:
            assert (target.kind, target.target_id, max_anchors) == (
                "assertion", "assertion-internal-test", 32,
            )
            assert (
                projection.world_id, projection.campaign_id,
                projection.scope_mode.value, projection.admissibility.value,
                projection.revision_pin,
            ) == (
                receipt.graph_authority.native_world_id, None,
                "world_cross_campaign", "gm",
                receipt.graph_authority.graph_revision,
            )
            return SimpleNamespace(
                found=True, target=target, snapshot=snapshot(projection),
                coverage=SimpleNamespace(
                    truncated_fields=(
                        () if metadata_state["evidence_complete"] else ("anchors",)
                    ), gap_codes=(), missing_ids=(),
                ),
                anchors=(SimpleNamespace(
                    evidence_ref_id="evidence-internal-test",
                    source_artifact_id="artifact:one",
                    source_revision_id="source-revision:one",
                    can_open_source=False,
                ),),
            )

        def list_source_context_index(self, request: Any) -> Any:
            return SimpleNamespace(
                status=("complete" if metadata_state["index_complete"] else "overflow"),
                max_entries=512,
                eligible_count=len(descriptors),
                entries=tuple(descriptors), snapshot=snapshot(request.projection),
            )

    with monkeypatch.context() as related_scope:
        related_scope.setattr(
            direct_reads, "direct_services_from_config",
            lambda _world: SimpleNamespace(retrieval=RelatedMetadata()),
        )
        related = project_plan_turn_context(completed_turn, delivery_replay=False)
        assert [item.kind for item in related.source_open_targets] == [
            "evidence_anchor", "related_recap_context",
        ]
        context_target = related.source_open_targets[1]
        assert context_target.context_anchor_id == "dm-context-anchor:v2:one"
        assert context_target.provenance_evidence_ref_id == "evidence-internal-test"
        assert context_target.source_revision_id == "source-revision:one"
        assert context_target.source_campaign_id == "campaign:one"
        assert related.completion.citation_map.entries[0].source_read_ids == [
            "source-read:one"
        ]
        context_only_citation = completion.citation_map.entries[0].model_copy(update={
            "source_read_ids": [], "source_opened": False,
        })
        context_only_completion = completion.model_copy(update={
            "citation_map": completion.citation_map.model_copy(update={
                "entries": [context_only_citation],
            }),
        })
        context_only_policy = graph_types.GraphExecutionPolicyV2.model_validate({
            **policy.model_dump(mode="json", by_alias=True),
            "source_read_scope": {
                **policy.source_read_scope.model_dump(mode="json", by_alias=True),
                "admitted_anchors": [],
            },
            "max_source_read_calls": 0,
            "max_source_read_anchors": 0,
            "max_source_read_chars": 0,
        })
        context_only_policy_digest = service_module._canonical_sha256({
            "schema": "dmb_agent_plan_world_graph_execution_v2",
            "context_receipt_sha256": receipt.context_receipt_sha256,
            "policy": context_only_policy.model_dump(mode="json", by_alias=True),
        })
        context_attempt_id = uuid4()
        context_attempt = graph_types.ProviderAttemptAuthorizedEventV2(
            **{
                **attempt_fields,
                "event_id": uuid4(), "sequence": 0,
                "provider_attempt_id": context_attempt_id,
            },
            included_source_read_event_ids=[],
        )
        context_sdk = sdk_entered.model_copy(update={
            "event_id": uuid4(), "sequence": 1,
            "provider_attempt_id": context_attempt_id,
        })
        context_outcome = outcome.model_copy(update={
            "event_id": uuid4(), "sequence": 2,
            "provider_attempt_id": context_attempt_id,
        })
        context_binding = binding.model_copy(update={
            "event_id": uuid4(), "sequence": 3,
            "provider_attempt_id": context_attempt_id,
            "completion_sha256": service_module._canonical_sha256(
                context_only_completion.model_dump(mode="json", by_alias=True)
            ),
        })
        context_only_execution = graph_types.PlanWorldGraphExecutionV2(
            context_receipt_sha256=receipt.context_receipt_sha256,
            execution_policy_sha256=context_only_policy_digest,
            policy=context_only_policy,
            events=[context_attempt, context_sdk, context_outcome, context_binding],
        )
        context_only_turn = completed_turn.model_copy(update={
            "completion": context_only_completion,
            "graph_context_execution": context_only_execution,
        })
        context_only_projection = project_plan_turn_context(
            context_only_turn, delivery_replay=True
        )
        assert [item.kind for item in context_only_projection.source_open_targets] == [
            "related_recap_context"
        ]
        assert [(item.status, item.choice_count) for item in (
            context_only_projection.related_recap_context_statuses
        )] == [
            ("available", 1)
        ]
        context_only_history = _serialized_card_a_history_body(
            related_scope, policy_turn_override=context_only_turn
        )
        assert [item["kind"] for item in context_only_history["turns"][0][
            "plan_context"
        ]["source_open_targets"]] == ["related_recap_context"]
        assert project_plan_turn_context(
            completed_turn, delivery_replay=True
        ).source_open_targets == related.source_open_targets
        assert [(item.status, item.choice_count) for item in (
            related.related_recap_context_statuses
        )] == [("available", 1)]
        history = _serialized_card_a_history_body(
            related_scope, policy_turn_override=completed_turn
        )
        assert history["turns"][0]["plan_context"]["source_open_targets"] == [
            item.model_dump(mode="json", by_alias=True)
            for item in related.source_open_targets
        ]
        assert history["turns"][0]["plan_context"]["evidence_anchor_statuses"] == [
            item.model_dump(mode="json", by_alias=True)
            for item in related.evidence_anchor_statuses
        ]
        descriptors.append(SimpleNamespace(
            **{**vars(descriptors[0]), "context_anchor_id": "dm-context-anchor:v2:two"}
        ))
        choices = project_plan_turn_context(completed_turn, delivery_replay=True)
        assert [
            item.context_anchor_id for item in choices.source_open_targets
            if item.kind == "related_recap_context"
        ] == ["dm-context-anchor:v2:one", "dm-context-anchor:v2:two"]
        assert choices.related_recap_context_statuses[0].status == "multiple_choices"
        assert choices.related_recap_context_statuses[0].choice_count == 2
        descriptors[0] = SimpleNamespace(
            **{**vars(descriptors[0]), "source_revision_id": "foreign-revision"}
        )
        descriptors.pop()
        assert [item.kind for item in project_plan_turn_context(
            completed_turn, delivery_replay=True
        ).source_open_targets] == ["evidence_anchor"]
        assert project_plan_turn_context(
            completed_turn, delivery_replay=True
        ).related_recap_context_statuses[0].status == "no_context"
        descriptors[0] = SimpleNamespace(
            **{
                **vars(descriptors[0]),
                "source_revision_id": "source-revision:one",
                "section_selector": SimpleNamespace(
                    **{
                        **vars(descriptors[0].section_selector),
                        "canonical_heading": "# Session 23 Recap",
                    }
                ),
            }
        )
        assert [item.kind for item in project_plan_turn_context(
            completed_turn, delivery_replay=True
        ).source_open_targets] == ["evidence_anchor"]
        assert project_plan_turn_context(
            completed_turn, delivery_replay=True
        ).related_recap_context_statuses[0].status == "metadata_unavailable"
        descriptors[0] = good_descriptor
        metadata_state["evidence_complete"] = False
        assert project_plan_turn_context(
            completed_turn, delivery_replay=True
        ).related_recap_context_statuses[0].status == "metadata_unavailable"
        metadata_state["evidence_complete"] = True
        metadata_state["index_complete"] = False
        assert project_plan_turn_context(
            completed_turn, delivery_replay=True
        ).related_recap_context_statuses[0].status == "metadata_unavailable"

    # Build validated V2 completion/scope fixtures at the projection boundary.
    # A bad Core lookup or exhausted metadata budget must not hide checked peers.
    metadata_state["index_complete"] = True
    claim_segment = completed_turn.completion.answer_segments[0]
    original_citation = completed_turn.completion.citation_map.entries[0]

    def expanded_completion(count: int) -> Any:
        payload = completed_turn.completion.model_dump(mode="json", by_alias=True)
        payload["answer_segments"] = []
        payload["citation_map"]["entries"] = []
        for number in range(count):
            claim_id = f"claim-{number:02d}"
            target_id = f"assertion-{number:02d}"
            segment = claim_segment.model_dump(mode="json", by_alias=True)
            segment.update(claim_id=claim_id, target_id=target_id)
            citation_payload = original_citation.model_dump(mode="json", by_alias=True)
            citation_payload.update(claim_id=claim_id, target_id=target_id)
            payload["answer_segments"].append(segment)
            payload["citation_map"]["entries"].append(citation_payload)
        return graph_types.PlanWorldGraphCompletionV2.model_validate(payload)

    mixed_turn = completed_turn.model_copy(update={"completion": expanded_completion(2)})

    class MixedMetadata(RelatedMetadata):
        def get_evidence(self, projection: Any, *, target: Any, max_anchors: int) -> Any:
            if target.target_id == "assertion-01":
                raise RuntimeError("synthetic unavailable target")
            result = super().get_evidence(
                projection,
                target=SimpleNamespace(kind="assertion", target_id="assertion-internal-test"),
                max_anchors=max_anchors,
            )
            return SimpleNamespace(**{**vars(result), "target": target})

    with monkeypatch.context() as mixed_scope:
        mixed_scope.setattr(
            direct_reads, "direct_services_from_config",
            lambda _world: SimpleNamespace(retrieval=MixedMetadata()),
        )
        mixed_targets, mixed_statuses = service_module._related_recap_context_open_targets(
            mixed_turn
        )
    assert [(item.claim_id, item.context_anchor_id) for item in mixed_targets] == [
        ("claim-00", "dm-context-anchor:v2:one")
    ]
    assert [(item.claim_id, item.status) for item in mixed_statuses] == [
        ("claim-00", "available"), ("claim-01", "metadata_unavailable")
    ]

    # The scope and completion reach their legitimate protocol sizes. A 9x9
    # cited-pin crossproduct exposes 64 deterministic links, with no duplication.
    many_pins = [graph_types.GraphSourceScopeAnchorV2(
        anchor_id=f"anchor:{number:02d}",
        evidence_ref_id="evidence-internal-test",
        source_artifact_id=f"artifact:{number:02d}",
        source_revision_id=f"source-revision:{number:02d}",
    ) for number in range(9)]
    large_scope = graph_types.GraphSourceReadScopeV2.model_validate({
        **policy.source_read_scope.model_dump(mode="json", by_alias=True),
        "admitted_anchors": [pin.model_dump(mode="json", by_alias=True) for pin in many_pins],
    })
    large_execution = completed_execution.model_copy(update={
        "policy": policy.model_copy(update={"source_read_scope": large_scope}),
    })
    large_turn = completed_turn.model_copy(update={
        "completion": expanded_completion(9),
        "graph_context_execution": large_execution,
    })
    large_targets, large_statuses = service_module._evidence_anchor_open_projection(
        large_turn
    )
    assert len(large_targets) == 64
    assert len({(
        item.claim_id, item.evidence_ref_id, item.anchor_id,
        item.source_artifact_id, item.source_revision_id,
    ) for item in large_targets}) == 64
    assert [(item.claim_id, item.status, item.target_count) for item in large_statuses] == [
        *((f"claim-{number:02d}", "partial", 8) for number in range(8)),
        ("claim-08", "overflow", 0),
    ]
    with monkeypatch.context() as budget_scope:
        budget_scope.setattr(
            direct_reads, "direct_services_from_config",
            lambda _world: SimpleNamespace(retrieval=MixedMetadata()),
        )
        retained, budget_statuses = service_module._related_recap_context_open_targets(
            mixed_turn, available_slots=0
        )
    assert retained == []
    assert [(item.claim_id, item.status) for item in budget_statuses] == [
        ("claim-00", "overflow"), ("claim-01", "metadata_unavailable")
    ]
    nine_claim_turn = completed_turn.model_copy(update={"completion": expanded_completion(9)})

    class CompleteMetadata(MixedMetadata):
        def get_evidence(self, projection: Any, *, target: Any, max_anchors: int) -> Any:
            result = RelatedMetadata.get_evidence(
                self, projection,
                target=SimpleNamespace(kind="assertion", target_id="assertion-internal-test"),
                max_anchors=max_anchors,
            )
            return SimpleNamespace(**{**vars(result), "target": target})

    with monkeypatch.context() as nine_scope:
        nine_scope.setattr(
            direct_reads, "direct_services_from_config",
            lambda _world: SimpleNamespace(retrieval=CompleteMetadata()),
        )
        nine_targets, nine_statuses = service_module._related_recap_context_open_targets(
            nine_claim_turn, available_slots=1
        )
    assert [(item.claim_id, item.context_anchor_id) for item in nine_targets] == [
        ("claim-00", "dm-context-anchor:v2:one")
    ]
    assert [item.status for item in nine_statuses] == [
        "available", *("overflow" for _ in range(7)), "metadata_unavailable"
    ]
    descriptors.extend(SimpleNamespace(
        **{**vars(good_descriptor), "context_anchor_id": f"dm-context-anchor:v2:{number:02d}"}
    ) for number in range(2, 10))
    with monkeypatch.context() as choice_budget_scope:
        choice_budget_scope.setattr(
            direct_reads, "direct_services_from_config",
            lambda _world: SimpleNamespace(retrieval=RelatedMetadata()),
        )
        capped_choices, capped_statuses = service_module._related_recap_context_open_targets(
            completed_turn
        )
    assert len(capped_choices) == 8
    assert capped_statuses[0].status == "partial"
    assert capped_statuses[0].choice_count == 8
    foreign_scope = policy.source_read_scope.model_copy(update={
        "graph_revision": "foreign-revision",
    })
    foreign_execution = completed_execution.model_copy(update={
        "policy": policy.model_copy(update={"source_read_scope": foreign_scope}),
    })
    assert service_module._evidence_anchor_open_targets(
        completed_turn.model_copy(update={"graph_context_execution": foreign_execution})
    ) == []
    foreign_pin = scope_anchor.model_copy(update={"evidence_ref_id": "foreign-evidence"})
    foreign_pin_scope = policy.source_read_scope.model_copy(update={
        "admitted_anchors": [foreign_pin],
    })
    foreign_pin_execution = completed_execution.model_copy(update={
        "policy": policy.model_copy(update={"source_read_scope": foreign_pin_scope}),
    })
    assert service_module._evidence_anchor_open_targets(
        completed_turn.model_copy(update={"graph_context_execution": foreign_pin_execution})
    ) == []

    unincluded_attempt = graph_types.ProviderAttemptAuthorizedEventV2(
        **attempt_fields, included_source_read_event_ids=[],
    )
    excluded_execution = graph_types.PlanWorldGraphExecutionV2(
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=policy_digest,
        policy=policy, events=[read_auth, read_event, unincluded_attempt, sdk_entered, outcome],
    )
    excluded_turn = turn.model_copy(update={"graph_context_execution": excluded_execution})
    excluded, _, _ = service_module._parse_policy_completion(
        model_answer, excluded_turn, attempt_id,
    )
    assert excluded.citation_map.entries[0].source_opened is False
    assert excluded.citation_map.entries[0].source_read_ids == []


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
    assert response.primary_work.revision_used == 7
    assert isinstance(response.primary_work.revision_used, int)
    assert response.primary_work.content_basis is None
    assert response.answer.text == "The keeper waits below the arch."
    assert response.answer.graph_grounded is False


def _serialized_card_a_history_body(
    monkeypatch: Any, *, include_turn_correlation: bool = False,
    policy_turn_override: Turn | None = None,
) -> dict[str, Any]:
    """Exercise FastAPI's response serialization for additive policy history."""
    import asyncio
    from fastapi.encoders import jsonable_encoder
    from fastapi.routing import serialize_response
    from types import SimpleNamespace

    from apps.live_control_server.routes import agent as agent_route

    policy_turn = policy_turn_override or _cited_card_a_policy_turn()
    legacy_turn = SimpleNamespace(
        turn_id=UUID("00000000-0000-4000-8000-000000000033"),
        sequence=1,
        status="completed",
        user_text="A legacy question",
        assistant_text="A legacy answer",
        provenance=policy_turn.provenance,
        graph_context_receipt=None,
        idempotency_key=UUID("00000000-0000-4000-8000-000000000044"),
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
        | agent_route.AgentConversationHistoryResponseV3
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(
            agent_conversation_service=HistoryService()
        ))
    )
    response = agent_route.get_world_conversation_history(
        "world-conversation-test", request, limit=50, before_sequence=None,
        include_turn_correlation=include_turn_correlation,
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
    assert policy_payload["schema"] == "dmb_agent_plan_world_graph_context_response_v2"
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
    assert all("idempotency_key" not in turn for turn in body["turns"])


def test_opted_in_history_serializes_persisted_correlation_keys(
    monkeypatch: Any,
) -> None:
    body = _serialized_card_a_history_body(
        monkeypatch, include_turn_correlation=True,
    )

    assert body["schema"] == "dmb_agent_conversation_history_v3"
    assert [turn["sequence"] for turn in body["turns"]] == [2, 1]
    assert all("idempotency_key" in turn for turn in body["turns"])
    assert body["turns"][1]["idempotency_key"] == "00000000-0000-4000-8000-000000000044"
    assert "plan_context" in body["turns"][0]
    assert "plan_context" not in body["turns"][1]


def test_history_http_opt_in_uses_persisted_key_not_durable_turn_id(
    monkeypatch: Any,
) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from uuid import NAMESPACE_URL, uuid5

    from apps.live_control_server.routes import agent as agent_route

    client_turn_id = uuid4()
    persisted_key = uuid5(
        NAMESPACE_URL, f"dmb-agent-turn:world:one:{client_turn_id}"
    )
    policy_turn = _policy_turn().model_copy(update={
        "idempotency_key": persisted_key,
    })
    assert policy_turn.turn_id != client_turn_id

    class HistoryService:
        def get_world_pointer(self, _world_id: str) -> Any:
            return type("Pointer", (), {
                "revision": 1,
                "active_conversation_id": policy_turn.conversation_id,
            })()

        def get_active_conversation(self, _world_id: str) -> Any:
            return type("Conversation", (), {
                "conversation_id": policy_turn.conversation_id,
            })()

        def list_turns(self, *_args: Any, **_kwargs: Any) -> list[Turn]:
            return [policy_turn]

    monkeypatch.setattr(agent_route, "_verified_world_id", lambda value: value)
    monkeypatch.setattr(agent_route, "enforce_native_graph_gm", lambda _request: None)
    app = FastAPI()
    app.include_router(agent_route.router, prefix="/api/live")
    app.state.agent_conversation_service = HistoryService()

    with TestClient(app) as client:
        legacy = client.get("/api/live/agent/worlds/world:one/conversation")
        correlated = client.get(
            "/api/live/agent/worlds/world:one/conversation",
            params={"include_turn_correlation": "true"},
        )
        correlated_retry = client.get(
            "/api/live/agent/worlds/world:one/conversation",
            params={"include_turn_correlation": "true"},
        )
        original_turn = policy_turn
        policy_turn = policy_turn.model_copy(update={"idempotency_key": None})
        uncorrelatable = client.get(
            "/api/live/agent/worlds/world:one/conversation",
            params={"include_turn_correlation": "true"},
        )
        legacy_without_key = client.get(
            "/api/live/agent/worlds/world:one/conversation"
        )
        policy_turn = original_turn
        app.state.agent_conversation_service = type("EmptyHistoryService", (), {
            "get_world_pointer": lambda _self, _world_id: type("Pointer", (), {
                "revision": 1, "active_conversation_id": None,
            })(),
            "get_active_conversation": lambda _self, _world_id: None,
        })()
        absent = client.get(
            "/api/live/agent/worlds/world:one/conversation",
            params={"include_turn_correlation": "true"},
        )

    assert legacy.status_code == 200
    assert correlated.status_code == 200
    assert correlated_retry.status_code == 200
    assert correlated_retry.content == correlated.content
    assert len(correlated_retry.json()["turns"]) == 1
    assert legacy.json()["schema"] == "dmb_agent_conversation_history_v2"
    assert "idempotency_key" not in legacy.json()["turns"][0]
    assert correlated.json()["schema"] == "dmb_agent_conversation_history_v3"
    row = correlated.json()["turns"][0]
    assert row["idempotency_key"] == str(persisted_key)
    assert row["turn_id"] == str(policy_turn.turn_id)
    assert row["turn_id"] != str(client_turn_id)
    assert row["plan_context"]["receipt"]["plan_basis"]["object_revision"] == 7
    assert uncorrelatable.status_code == 409
    assert uncorrelatable.json()["detail"]["code"] == "turn_correlation_unavailable"
    assert legacy_without_key.status_code == 200
    assert absent.status_code == 200
    assert absent.json()["schema"] == "dmb_agent_conversation_history_v3"
    assert absent.json()["turns"] == []


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


@pytest.mark.parametrize("capture_enabled", [False, True, "limit"])
def test_parent_source_broker_persists_authorization_before_content_and_result_before_reply(
    monkeypatch: Any, capture_enabled: bool | str,
) -> None:
    from application_state.agent_conversation import types as graph_types
    from apps.live_control_server.services import agent_turn_service as service_module
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from graph_memory.interaction.session import GraphRetrievalSession, SessionSnapshot, SourceAnchorState
    from graph_memory.interaction.session_store import create_session, clear_sessions, replace_session

    turn = _policy_turn(status="running", completion_present=False)
    receipt = turn.graph_context_receipt
    assert receipt is not None
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="native:one", campaign_id="", focus={"kind": "none"},
            admissibility="gm", revision_id="graph-revision-3", scope_mode="world",
        ),
        question="Where is the gate?",
        source_anchors=[SourceAnchorState(anchor_id="anchor:one", readable=True)],
    )
    clear_sessions()
    create_session(session)
    scope_anchor = graph_types.GraphSourceScopeAnchorV2(
        anchor_id="anchor:one", evidence_ref_id="evidence:one",
        source_artifact_id="artifact:one", source_revision_id="source-revision:one",
    )
    policy = graph_types.GraphExecutionPolicyV2(
        policy_version="plan_world_graph_execution_v1",
        allowed_graph_operations=["expand_graph_retrieval"],
        max_provider_attempts=4, max_graph_operations=8, max_results_per_operation=512,
        max_total_provider_input_tokens=100_000,
        max_total_provider_output_tokens=10_000,
        provider_input_accounting=graph_types.GraphExecutionAccountingV1(
            kind="conservative_upper_bound", estimator="utf8_json_bytes_plus_64_per_node_v1",
        ),
        source_opened=False,
        source_read_scope=graph_types.GraphSourceReadScopeV2(
            retrieval_session_id=session.id, world_id="world:one", campaign_id=None,
            graph_revision="graph-revision-3", admitted_anchors=[
                scope_anchor,
                graph_types.GraphSourceScopeAnchorV2(
                    anchor_id="anchor:two", evidence_ref_id="evidence:two",
                    source_artifact_id="artifact:two", source_revision_id="source-revision:two",
                ),
            ],
        ),
        max_source_read_calls=8, max_source_read_anchors=8,
        max_source_read_chars=96_000, max_chars_per_source_read=12_000,
    )
    policy_digest = service_module._canonical_sha256({
        "schema": "dmb_agent_plan_world_graph_execution_v2",
        "context_receipt_sha256": receipt.context_receipt_sha256,
        "policy": policy.model_dump(mode="json", by_alias=True),
    })
    execution = graph_types.PlanWorldGraphExecutionV2(
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=policy_digest, policy=policy, events=[],
    )
    turn = turn.model_copy(update={"graph_context_execution": execution})
    order: list[str] = []
    captured_passages = []

    class Fence:
        def __init__(self) -> None:
            self.turn = turn

        def append(self, method: str, _key: str, event: Any, **extras: Any) -> tuple[Turn, bool]:
            order.append(method)
            if method == "record_validated_source_read" and capture_enabled:
                if capture_enabled == "limit" and extras:
                    from application_state.errors import ApplicationStateValidationError
                    raise ApplicationStateValidationError("trace exceeds the explicit 1 MiB per-attempt ceiling")
                if extras:
                    passages = extras["source_passages"]
                    assert passages[0].source_read_event_id == event.event_id
                    assert passages[0].text == "bound source text"
                    assert passages[0].content_sha256 == sha256(passages[0].text.encode()).hexdigest()
                    captured_passages.extend(passages)
            current = self.turn.graph_context_execution
            self.turn = self.turn.model_copy(update={
                "graph_context_execution": graph_types.PlanWorldGraphExecutionV2.model_validate({
                    **current.model_dump(mode="json", by_alias=True),
                    "events": [
                        *[prior.model_dump(mode="json", by_alias=True) for prior in current.events],
                        event.model_dump(mode="json", by_alias=True),
                    ],
                }),
                "revision": self.turn.revision + 1,
            })
            return self.turn, True

    bootstrap = service_module.AgentPlanWorldGraphBootstrap(
        graph_envelope={},
        world_scope=AgentWorldScope(
            world_id="native:one", campaign_id="", focus={"kind": "none"},
            admissibility="gm", revision_id="graph-revision-3", scope_mode="world",
        ),
        retrieval_session=session, binding_version=1, source_root_relpath="corpus",
        candidate_assertion_ids=(), candidate_relationship_ids=(),
        candidate_evidence_ref_ids=(), evidence_by_anchor_id={},
        source_scope_anchors=(scope_anchor.model_dump(),),
    )
    # A retry may re-resolve a fresh search session. Recover the exact frozen
    # session before the provider gate, and reject changed metadata pins.
    frozen_pins = tuple(anchor.model_dump() for anchor in policy.source_read_scope.admitted_anchors)
    fresh = replace(
        bootstrap,
        retrieval_session=session.model_copy(update={"id": "grs:fresh-retry"}),
        source_scope_anchors=frozen_pins,
    )
    restored = service_module._restore_v2_retry_bootstrap(fresh, turn)
    assert restored.retrieval_session.id == session.id
    assert len(restored.source_scope_anchors) == 2
    assert service_module._restore_v2_retry_bootstrap(
        replace(bootstrap, source_scope_anchors=frozen_pins), turn,
    ).retrieval_session.id == session.id
    unfrozen = _policy_turn(status="accepted", completion_present=False)
    assert service_module._restore_v2_retry_bootstrap(fresh, unfrozen) is fresh
    legacy_policy = graph_types.GraphExecutionPolicyV1.model_validate({
        key: value for key, value in policy.model_dump(mode="json").items()
        if key in graph_types.GraphExecutionPolicyV1.model_fields
    })
    legacy_execution = graph_types.PlanWorldGraphExecutionV1(
        context_receipt_sha256=unfrozen.graph_context_receipt.context_receipt_sha256,
        policy=legacy_policy, events=[],
    )
    legacy_retry = service_module._restore_v2_retry_bootstrap(
        fresh, unfrozen.model_copy(update={"graph_context_execution": legacy_execution}),
    )
    assert legacy_retry.source_scope_anchors == ()
    changed = replace(fresh, source_scope_anchors=({
        **scope_anchor.model_dump(), "source_revision_id": "source-revision:changed",
    },))
    with pytest.raises(AgentTurnServiceError) as changed_pin:
        service_module._restore_v2_retry_bootstrap(changed, turn)
    assert changed_pin.value.code == "turn_receipt_unverifiable"
    for invalid_pins in (
        frozen_pins[:1],
        (*frozen_pins, {
            "anchor_id": "anchor:extra", "evidence_ref_id": "evidence:extra",
            "source_artifact_id": "artifact:extra",
            "source_revision_id": "source-revision:extra",
        }),
        (frozen_pins[0], frozen_pins[0]),
    ):
        with pytest.raises(AgentTurnServiceError) as changed_scope:
            service_module._restore_v2_retry_bootstrap(
                replace(fresh, source_scope_anchors=invalid_pins), turn,
            )
        assert changed_scope.value.code == "turn_receipt_unverifiable"

    provider_body = json.dumps({"input": [], "tools": []})
    budget = service_module._policy_request_budget() | {"schema": "dmb_hermes_request_budget_policy_v1", "maxProviderAttempts": 4, "maxToolCapableAttempts": 3, "maxGraphOperations": 8}  # Frozen finite fixture
    view = {
        "provider": budget["provider"], "model": budget["model"],
        "apiMode": budget["apiMode"], "payloadJson": provider_body,
        "payloadSha256": sha256(provider_body.encode()).hexdigest(),
        "payloadUtf8Bytes": len(provider_body.encode()),
    }
    denied_retry = service_module._PolicyExecutionAdapter(
        service=object(), request=_request(), world_id="world:one", work=None,
        bootstrap=fresh, playable_target=None, submitted_intent=None,
        existing_turn=turn, budget=budget,
    )
    denied_retry.fence = Fence()
    denied_retry._ensure_claimed = lambda _view: (denied_retry.fence.turn, [], [], [])
    assert denied_retry.authorize(view) is False
    assert denied_retry.failure is not None
    assert denied_retry.failure.code == "turn_receipt_unverifiable"

    safe_retry = service_module._PolicyExecutionAdapter(
        service=object(), request=_request(), world_id="world:one", work=None,
        bootstrap=restored, playable_target=None, submitted_intent=None,
        existing_turn=turn, budget=budget,
    )
    safe_retry.fence = Fence()
    safe_retry._ensure_claimed = lambda _view: (safe_retry.fence.turn, [], [], [])
    assert safe_retry.authorize(view) is True
    assert safe_retry.last_provider_attempt_id is not None
    assert safe_retry.fence.turn.graph_context_execution.events[-1].kind == (
        "provider_attempt_authorized_v2"
    )
    with pytest.raises(AgentTurnServiceError) as already_authorized:
        service_module._restore_v2_retry_bootstrap(
            fresh, safe_retry.fence.turn,
        )
    assert already_authorized.value.code == "turn_receipt_unverifiable"
    order.clear()

    adapter = service_module._PolicyExecutionAdapter(
        service=object(), request=_request(), world_id="world:one", work=None,
        bootstrap=bootstrap, playable_target=None, submitted_intent=None,
        existing_turn=turn, budget={},
    )
    adapter.fence = Fence()
    adapter.last_provider_attempt_id = uuid4()
    if capture_enabled:
        from types import SimpleNamespace
        from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
        capture = ContextTraceCollector.__new__(ContextTraceCollector)
        from time import monotonic
        capture.started = monotonic()
        capture.fence = adapter.fence
        capture.trace = SimpleNamespace(capture_status="recording")
        def mark_incomplete(code: str) -> None:
            capture.trace.capture_status = "incomplete"
            capture.trace.capture_failure_code = code
        capture.mark_incomplete = mark_incomplete
        capture.refresh_after_source_capture = lambda: None
        capture.observe = lambda fields: None
        adapter.context_capture = capture
    content = "bound source text"
    digest = "a" * 64  # Parent source revision digest, not the excerpt digest.

    def read(arguments: Any, *, receipt_version: int) -> dict[str, Any]:
        assert receipt_version == 2
        assert order[-1] == "authorize_source_read"
        anchor_id = arguments["anchorIds"][0]
        suffix = "one" if anchor_id == "anchor:one" else "two"
        return {
            "schema": "dmb_internal_read_graph_source_batch_v2",
            "retrievalSessionId": session.id,
            "reads": [{
                "sourceReadId": f"source-read:{suffix}",
                "result": {
                    "schema": "dmb_world_graph_source_anchor_read_v1",
                    "outcome": "enough", "anchorId": anchor_id,
                    "content": content, "contentSha256": digest,
                    "evidenceRefId": f"evidence:{suffix}", "sourceArtifactId": f"artifact:{suffix}",
                },
                "receipt": {
                    "source_read_id": f"source-read:{suffix}", "retrieval_session_id": session.id,
                    "graph_revision": "graph-revision-3", "anchor_id": anchor_id,
                    "evidence_ref_id": f"evidence:{suffix}", "source_artifact_id": f"artifact:{suffix}",
                    "source_revision_id": f"source-revision:{suffix}",
                    "read_content_sha256": digest, "outcome": "enough",
                    "truncated": False,
                },
            }],
        }

    monkeypatch.setattr(
        "graph_memory.interaction.expansion_executor.execute_read_graph_source", read,
    )
    try:
        denied = adapter.broker_source_read({
            "toolName": "read_graph_source",
            "arguments": {"retrievalSessionId": session.id, "anchorIds": ["anchor:foreign"]},
        })
        assert json.loads(denied["resultJson"])["code"] == "source_anchor_not_admitted"
        assert order == []
        not_yet_active = adapter.broker_source_read({
            "toolName": "read_graph_source",
            "arguments": {"retrievalSessionId": session.id, "anchorIds": ["anchor:two"]},
        })
        assert json.loads(not_yet_active["resultJson"])["code"] == "source_anchor_not_admitted"
        assert order == []
        accepted = adapter.broker_source_read({
            "toolName": "read_graph_source",
            "arguments": {"retrievalSessionId": session.id, "anchorIds": ["anchor:one"]},
        })
        if capture_enabled == "limit":
            assert order == ["authorize_source_read", "record_validated_source_read", "record_validated_source_read"]
            assert json.loads(accepted["resultJson"])["code"] == "source_capture_incomplete"
            assert content not in accepted["resultJson"]
            assert adapter.source_payloads == {}
            assert adapter.failure is None
            assert adapter.context_capture.trace.capture_failure_code == "trace_size_limit"
            events = adapter.fence.turn.graph_context_execution.events
            assert sum(event.kind == "source_read_authorized_v2" for event in events) == 1
            assert sum(event.kind == "validated_source_read_v2" for event in events) == 1
            return
        assert order == ["authorize_source_read", "record_validated_source_read"]
        assert content in accepted["resultJson"]
        assert content not in adapter.fence.turn.graph_context_execution.model_dump_json()
        assert len(adapter.source_payloads) == 1
        session.source_anchors.append(SourceAnchorState(anchor_id="anchor:two", readable=True))
        replace_session(session)
        expanded = adapter.broker_source_read({
            "toolName": "read_graph_source",
            "arguments": {"retrievalSessionId": session.id, "anchorIds": ["anchor:two"]},
        })
        assert content in expanded["resultJson"]
        assert len(adapter.source_payloads) == 2
        if capture_enabled:
            assert len(captured_passages) == 2
            def capture_unavailable(*args: Any, **kwargs: Any) -> Any:
                raise ConnectionError("trace storage unavailable")
            monkeypatch.setattr(adapter.context_capture, "source_passages", capture_unavailable)
            rejected_capture = adapter.broker_source_read({
                "toolName": "read_graph_source",
                "arguments": {"retrievalSessionId": session.id, "anchorIds": ["anchor:one"]},
            })
            assert content not in rejected_capture["resultJson"]
            assert len(adapter.source_payloads) == 2
            assert len(captured_passages) == 2
            assert order[-1] == "authorize_source_read"
            assert adapter.failure.code == "source_read_indeterminate"
            assert adapter.authorize(view) is False
            assert order[-1] == "authorize_source_read"
            return
        def forged(arguments: Any, *, receipt_version: int) -> dict[str, Any]:
            batch = read(arguments, receipt_version=receipt_version)
            batch["reads"][0]["receipt"]["source_revision_id"] = "source-revision:forged"
            return batch

        monkeypatch.setattr(
            "graph_memory.interaction.expansion_executor.execute_read_graph_source", forged,
        )
        rejected = adapter.broker_source_read({
            "toolName": "read_graph_source",
            "arguments": {"retrievalSessionId": session.id, "anchorIds": ["anchor:one"]},
        })
        assert json.loads(rejected["resultJson"])["code"] == "source_read_unavailable"
        assert content not in rejected["resultJson"]
        assert adapter.failure is not None and adapter.failure.code == "source_read_indeterminate"
        assert len(adapter.source_payloads) == 2
    finally:
        clear_sessions()


def test_v3_parent_admits_traversal_pin_reads_it_and_binds_opened_citation(
    monkeypatch: Any,
) -> None:
    from types import SimpleNamespace

    from application_state.agent_conversation import types as graph_types
    from apps.live_control_server.services import agent_turn_service as service_module
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from graph_memory.interaction.session import (
        CoverageState, GraphRetrievalSession, SessionSnapshot,
    )
    from graph_memory.interaction.session_store import (
        clear_sessions, create_session,
    )

    monkeypatch.setattr(
        "apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference",
        lambda **_kwargs: ("openai-api", "gpt-6-luna", "https://api.openai.com/v1"),
    )
    turn = _policy_turn(status="running", completion_present=False)
    receipt = turn.graph_context_receipt
    assert receipt is not None
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id=receipt.graph_authority.native_world_id, campaign_id="",
            focus={"kind": "none"}, admissibility="gm",
            revision_id=receipt.graph_authority.graph_revision, scope_mode="world",
        ),
        question="Where is the gate?", coverage=CoverageState(state="ready"),
    )
    scope = graph_types.GraphSourceReadScopeV2(
        retrieval_session_id=session.id,
        world_id=receipt.graph_authority.managed_world_id,
        campaign_id=None, graph_revision=receipt.graph_authority.graph_revision,
        admitted_anchors=[],
    )
    policy = graph_types.GraphExecutionPolicyV3(
        policy_version="plan_world_graph_execution_v1",
        allowed_graph_operations=["expand_graph_retrieval"],
        max_provider_attempts=4, max_graph_operations=8, max_results_per_operation=512,
        max_total_provider_input_tokens=100_000,
        max_total_provider_output_tokens=10_000,
        provider_input_accounting=graph_types.GraphExecutionAccountingV1(
            kind="conservative_upper_bound",
            estimator="utf8_json_bytes_plus_64_per_node_v1",
        ),
        source_opened=False, source_read_scope=scope,
        max_source_read_chars=96_000, max_chars_per_source_read=12_000,
    )
    initial_attempt_id = uuid4()
    initial_attempt = graph_types.ProviderAttemptAuthorizedEventV3(
        event_id=uuid4(), sequence=0, kind="provider_attempt_authorized_v3",
        provider_attempt_id=initial_attempt_id, envelope_sha256="b" * 64,
        serializer_version="canonical-json-utf8-v1", provider="openai-api",
        model="gpt-6-luna", api_mode="codex_responses",
        tool_schema_sha256="c" * 64,
        input_accounting_kind="conservative_upper_bound",
        input_estimator="utf8_json_bytes_plus_64_per_node_v1",
        input_tokens=1000, output_token_reserve=2048,
        included_assertion_ids=[], included_relationship_ids=[],
        included_evidence_ref_ids=[], included_graph_event_ids=[],
        included_source_read_event_ids=[],
    )
    initial_sdk = graph_types.ProviderOutcomeEventV1(
        event_id=uuid4(), sequence=1, kind="provider_outcome",
        provider_attempt_id=initial_attempt_id, outcome="sdk_entered",
    )
    initial_outcome = graph_types.ProviderOutcomeEventV1(
        event_id=uuid4(), sequence=2, kind="provider_outcome",
        provider_attempt_id=initial_attempt_id, outcome="response_received",
    )
    execution = graph_types.PlanWorldGraphExecutionV3(
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=graph_types.graph_execution_policy_digest_v3(
            receipt.context_receipt_sha256, policy,
        ),
        policy=policy, events=[initial_attempt, initial_sdk, initial_outcome],
    )
    turn = turn.model_copy(update={"graph_context_execution": execution})
    append_order: list[str] = []

    class Fence:
        def __init__(self) -> None:
            self.turn = turn

        def append(
            self, method: str, _event_name: str, event: Any, **_extras: Any,
        ) -> tuple[Turn, bool]:
            append_order.append(method)
            current = self.turn.graph_context_execution
            assert isinstance(current, graph_types.PlanWorldGraphExecutionV3)
            updated_execution = graph_types.PlanWorldGraphExecutionV3.model_validate({
                **current.model_dump(mode="json", by_alias=True),
                "events": [
                    *[item.model_dump(mode="json", by_alias=True) for item in current.events],
                    event.model_dump(mode="json", by_alias=True),
                ],
            })
            self.turn = self.turn.model_copy(update={
                "graph_context_execution": updated_execution,
                "revision": self.turn.revision + 1,
            })
            return self.turn, True

    pins = [graph_types.GraphSourceScopeAnchorV2(
        anchor_id=f"anchor:discovered:{index:02d}",
        evidence_ref_id=f"evidence:discovered:{index:02d}",
        source_artifact_id=f"artifact:discovered:{index:02d}",
        source_revision_id=f"source-revision:discovered:{index:02d}",
    ) for index in range(9)]
    cited_pin = pins[0]
    native_result = SimpleNamespace(
        snapshot=SimpleNamespace(
            world_id=receipt.graph_authority.native_world_id,
            revision_id=receipt.graph_authority.graph_revision,
        ),
        attributes=(SimpleNamespace(
            assertion_id="assertion:discovered",
            evidence_ref_ids=tuple(pin.evidence_ref_id for pin in pins),
        ),),
        relationships=(),
        source_anchors=tuple(SimpleNamespace(
            anchor_id=pin.anchor_id, evidence_ref_id=pin.evidence_ref_id,
            source_artifact_id=pin.source_artifact_id,
            revision_id=pin.source_revision_id, readable=True,
            locator_kind="repo_span",
        ) for pin in pins),
        coverage=SimpleNamespace(truncated_fields=("relationships",)),
        outcome="truncated",
        model_dump=lambda **_kwargs: {
            "schema": "dmb_world_graph_retrieval_result_v1",
            "operation": "search", "outcome": "truncated",
            "attributes": [{
                "assertionId": "assertion:discovered",
                "evidenceRefIds": [pin.evidence_ref_id for pin in pins],
            }],
            "sourceAnchors": [{
                "anchorId": pin.anchor_id,
                "evidenceRefId": pin.evidence_ref_id,
                "sourceArtifactId": pin.source_artifact_id,
                "revisionId": pin.source_revision_id, "readable": True,
            } for pin in pins],
            "coverage": {"truncatedFields": ["relationships"]},
        },
    )
    from graph_memory.interaction import authority_classifier
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads

    monkeypatch.setattr(authority_classifier, "claims_from_retrieval_result", lambda *_a, **_kw: [])
    monkeypatch.setattr(world_graph_reads, "direct_services_from_config", lambda *_a: object())
    monkeypatch.setattr(world_graph_reads, "search_world_graph_direct_v3", lambda *_a: SimpleNamespace(
        result=native_result, source_pins=[SimpleNamespace(
            **pin.model_dump(), graph_revision=receipt.graph_authority.graph_revision,
        ) for pin in pins],
    ))
    contents = {
        pin.anchor_id: f"Passage for discovered source {index}."
        for index, pin in enumerate(pins)
    }

    def read_source(arguments: Any, *, receipt_version: int) -> dict[str, Any]:
        assert receipt_version == 2
        assert append_order[-1] == "authorize_source_read"
        returned = []
        for anchor_id in arguments["anchorIds"]:
            pin = next(item for item in pins if item.anchor_id == anchor_id)
            content = contents[anchor_id]
            content_digest = sha256(content.encode()).hexdigest()
            read_id = f"source-read:{anchor_id.rsplit(':', 1)[1]}"
            returned.append({
                "sourceReadId": read_id,
                "result": {
                    "schema": "dmb_world_graph_source_anchor_read_v1",
                    "outcome": "enough", "anchorId": pin.anchor_id,
                    "content": content, "contentSha256": content_digest,
                    "evidenceRefId": pin.evidence_ref_id,
                    "sourceArtifactId": pin.source_artifact_id,
                    "lineStart": 1, "lineEnd": 1, "truncated": False,
                },
                "receipt": {
                    "source_read_id": read_id,
                    "retrieval_session_id": session.id,
                    "graph_revision": receipt.graph_authority.graph_revision,
                    "anchor_id": pin.anchor_id,
                    "evidence_ref_id": pin.evidence_ref_id,
                    "source_artifact_id": pin.source_artifact_id,
                    "source_revision_id": pin.source_revision_id,
                    "read_content_sha256": content_digest,
                    "outcome": "enough", "truncated": False,
                },
            })
        return {
            "schema": "dmb_internal_read_graph_source_batch_v2",
            "retrievalSessionId": session.id,
            "reads": returned,
        }

    monkeypatch.setattr(
        "graph_memory.interaction.expansion_executor.execute_read_graph_source",
        read_source,
    )
    bootstrap = service_module.AgentPlanWorldGraphBootstrap(
        graph_envelope={},
        world_scope=AgentWorldScope(
            world_id=receipt.graph_authority.native_world_id, campaign_id="",
            focus={"kind": "none"}, admissibility="gm",
            revision_id=receipt.graph_authority.graph_revision, scope_mode="world",
        ),
        retrieval_session=session, binding_version=receipt.graph_authority.binding_version,
        source_root_relpath="corpus", candidate_assertion_ids=(),
        candidate_relationship_ids=(), candidate_evidence_ref_ids=(),
        evidence_by_anchor_id={}, source_scope_anchors=(),
    )
    budget = service_module._policy_request_budget() | {"schema": "dmb_hermes_request_budget_policy_v1", "maxProviderAttempts": 4, "maxToolCapableAttempts": 3, "maxGraphOperations": 8}  # Frozen finite fixture
    adapter = service_module._PolicyExecutionAdapter(
        service=object(), request=_request(), world_id=receipt.graph_authority.managed_world_id,
        work=None, bootstrap=bootstrap, playable_target=None, submitted_intent=None,
        existing_turn=turn, budget=budget,
    )
    adapter.fence = Fence()
    adapter.last_provider_attempt_id = initial_attempt_id
    adapter.producing_provider_attempt_id = initial_attempt_id
    adapter._ensure_claimed = lambda _view: (adapter.fence.turn, [], [], [])
    clear_sessions()
    create_session(session)
    try:
        graph_arguments = {
            "retrievalSessionId": session.id, "operation": "search",
        }
        graph_reply = adapter.broker_graph_operation({
            "toolName": "expand_graph_retrieval", "arguments": graph_arguments,
        })
        assert all(content not in graph_reply["resultJson"] for content in contents.values())
        execution_after_graph = adapter.fence.turn.graph_context_execution
        assert isinstance(execution_after_graph, graph_types.PlanWorldGraphExecutionV3)
        origin, extension = execution_after_graph.events[-2:]
        assert origin.kind == "validated_graph_operation_v3"
        assert origin.returned_source_pins == pins
        assert extension.kind == "source_scope_extension_v3"
        assert extension.origin_graph_event_id == origin.event_id
        assert extension.pins == origin.returned_source_pins
        assert execution_after_graph.policy.source_read_scope.admitted_anchors == []

        assert len(session.source_anchors) == 9
        source_replies = []
        input_items = [
            {"type": "function_call", "call_id": "graph-call",
             "name": "expand_graph_retrieval", "arguments": json.dumps(graph_arguments)},
            {"type": "function_call_output", "call_id": "graph-call",
             "output": graph_reply["resultJson"]},
        ]
        for index, pin in enumerate(pins):
            source_arguments = {
                "retrievalSessionId": session.id, "anchorIds": [pin.anchor_id],
            }
            source_reply = adapter.broker_source_read({
                "toolName": "read_graph_source", "arguments": source_arguments,
            })
            assert contents[pin.anchor_id] in source_reply["resultJson"]
            source_replies.append(source_reply)
            input_items.extend([
                {"type": "function_call", "call_id": f"source-call-{index}",
                 "name": "read_graph_source", "arguments": json.dumps(source_arguments)},
                {"type": "function_call_output", "call_id": f"source-call-{index}",
                 "output": source_reply["resultJson"]},
            ])
        assert append_order[-18:] == [
            part for _ in pins for part in (
                "authorize_source_read", "record_validated_source_read",
            )
        ]
        payload = json.dumps({"input": input_items, "tools": []})
        provider_view = {
            "provider": budget["provider"], "model": budget["model"],
            "apiMode": budget["apiMode"], "payloadJson": payload,
            "payloadSha256": sha256(payload.encode()).hexdigest(),
            "payloadUtf8Bytes": len(payload.encode()),
        }
        assert adapter.authorize(provider_view) is True
        assert adapter.record_lifecycle({"transition": "sdk_entered"}) is True
        assert adapter.record_lifecycle({"transition": "response_received"}) is True
        final_execution = adapter.fence.turn.graph_context_execution
        assert isinstance(final_execution, graph_types.PlanWorldGraphExecutionV3)
        final_authorization = final_execution.events[-3]
        read_event = next(
            event for event in final_execution.events
            if event.kind == "validated_source_read_v2"
        )
        assert final_authorization.kind == "provider_attempt_authorized_v3"
        assert len(final_authorization.included_source_read_event_ids) == 9
        assert read_event.event_id in final_authorization.included_source_read_event_ids
        assert final_authorization.included_graph_event_ids == [origin.event_id]

        model_answer = json.dumps({
            "answer_context_status": "graph_grounded_partial",
            "answer_segments": [{
                "kind": "graph_claim", "claim_id": "claim:gate",
                "text": "The gate is sealed with blue wax.",
                "target_kind": "assertion", "target_id": "assertion:discovered",
                "graph_revision": receipt.graph_authority.graph_revision,
                "evidence_ref_ids": [cited_pin.evidence_ref_id],
            }],
            "citation_map": {"entries": [{
                "claim_id": "claim:gate", "target_kind": "assertion",
                "target_id": "assertion:discovered",
                "graph_revision": receipt.graph_authority.graph_revision,
                "evidence_ref_ids": [cited_pin.evidence_ref_id], "source_opened": False,
            }]},
        })
        completion, bindings, _answer = service_module._parse_policy_completion(
            model_answer, adapter.fence.turn, adapter.producing_provider_attempt_id,
        )
        assert completion.citation_map is not None
        citation = completion.citation_map.entries[0]
        assert citation.source_opened is True
        assert citation.source_read_ids == ["source-read:00"]
        assert bindings["claim:gate"] == [origin.event_id]
        completion_binding = graph_types.CompletionBindingEventV1(
            event_id=uuid4(), sequence=len(final_execution.events),
            kind="completion_binding",
            provider_attempt_id=adapter.producing_provider_attempt_id,
            completion_sha256=service_module._canonical_sha256(
                completion.model_dump(mode="json", by_alias=True)
            ),
            claim_graph_event_ids=bindings,
        )
        bound_execution = graph_types.PlanWorldGraphExecutionV3.model_validate({
            **final_execution.model_dump(mode="json", by_alias=True),
            "events": [
                *[item.model_dump(mode="json", by_alias=True) for item in final_execution.events],
                completion_binding.model_dump(mode="json", by_alias=True),
            ],
        })
        graph_types.validate_execution_completion(
            completion, receipt, bound_execution,
            adapter.producing_provider_attempt_id, bindings,
        )
        projected, _statuses = service_module._evidence_anchor_open_projection(
            adapter.fence.turn.model_copy(update={
                "completion": completion, "graph_context_execution": bound_execution,
            }),
        )
        assert len(projected) == 1
        assert projected[0].source_read_id == citation.source_read_ids[0]
        assert projected[0].anchor_id == cited_pin.anchor_id
        from apps.live_control_server.services.plan_action_consultation import _source_open_targets
        saved_plan_targets = _source_open_targets(SimpleNamespace(consultation=SimpleNamespace(
            receipt=receipt, execution=bound_execution,
            result=SimpleNamespace(kind='clarification', citation_map=completion.citation_map,
                                   producing_provider_attempt_id=adapter.producing_provider_attempt_id),
        )))
        assert len(saved_plan_targets) == 1
        assert saved_plan_targets[0]['source_read_id'] == citation.source_read_ids[0]
        assert saved_plan_targets[0]['anchor_id'] == cited_pin.anchor_id
    finally:
        clear_sessions()


def _related_recap_broker_fixture(monkeypatch: Any) -> Any:
    from types import SimpleNamespace
    from application_state.agent_conversation import types as graph_types
    from apps.live_control_server.services import agent_turn_service as service_module
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct_reads,
    )
    from apps.live_control_server.services import world_graph_retrieval as source_reads
    from dungeonmind.application.world_graph_retrieval import RecapContextSectionSelectorV2
    from graph_memory.interaction.session import GraphRetrievalSession, SessionSnapshot

    turn = _cited_card_a_policy_turn().model_copy(update={
        "status": "running", "completion": None, "assistant_text": None,
    })
    receipt = turn.graph_context_receipt
    assert receipt is not None
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id=receipt.graph_authority.native_world_id, campaign_id="",
            focus={"kind": "none"}, admissibility="gm",
            revision_id=receipt.graph_authority.graph_revision, scope_mode="world",
        ),
        question="What happened at the gate?",
    )
    policy = graph_types.GraphExecutionPolicyV2(
        policy_version="plan_world_graph_execution_v1",
        allowed_graph_operations=["expand_graph_retrieval"],
        max_provider_attempts=4, max_graph_operations=8, max_results_per_operation=512,
        max_total_provider_input_tokens=100_000,
        max_total_provider_output_tokens=10_000,
        provider_input_accounting=graph_types.GraphExecutionAccountingV1(
            kind="conservative_upper_bound", estimator="utf8_json_bytes_plus_64_per_node_v1",
        ),
        source_opened=False,
        source_read_scope=graph_types.GraphSourceReadScopeV2(
            retrieval_session_id=session.id,
            world_id=receipt.graph_authority.managed_world_id,
            campaign_id=None, graph_revision=receipt.graph_authority.graph_revision,
            admitted_anchors=[],
        ),
        max_source_read_calls=0, max_source_read_anchors=0,
        max_source_read_chars=0, max_chars_per_source_read=12_000,
    )
    execution = graph_types.PlanWorldGraphExecutionV2(
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=service_module._canonical_sha256({
            "schema": "dmb_agent_plan_world_graph_execution_v2",
            "context_receipt_sha256": receipt.context_receipt_sha256,
            "policy": policy.model_dump(mode="json", by_alias=True),
        }),
        policy=policy, events=[],
    )
    turn = turn.model_copy(update={"graph_context_execution": execution})
    calls: list[str] = []

    class Fence:
        def __init__(self) -> None:
            self.turn = turn

        def append(self, method: str, _key: str, event: Any) -> tuple[Turn, bool]:
            calls.append(method)
            prior = self.turn.graph_context_execution
            self.turn = self.turn.model_copy(update={
                "graph_context_execution": graph_types.PlanWorldGraphExecutionV2.model_validate({
                    **prior.model_dump(mode="json", by_alias=True),
                    "events": [
                        *[item.model_dump(mode="json", by_alias=True) for item in prior.events],
                        event.model_dump(mode="json", by_alias=True),
                    ],
                }),
                "revision": self.turn.revision + 1,
            })
            graph_types.validate_related_recap_context_scope(
                receipt, self.turn.graph_context_execution
            )
            return self.turn, True

    selector = RecapContextSectionSelectorV2(
        expected_session_id="session-22", canonical_heading="# Session 22 Recap", legacy_session_heading="## Session 22:", legacy_recap_marker="**Recap**:"
    )
    descriptor = SimpleNamespace(
        context_anchor_id="dm-context-anchor:v2:recap-22",
        world_id=receipt.graph_authority.native_world_id,
        campaign_id="longmont-c2",
        graph_revision_id=receipt.graph_authority.graph_revision,
        source_artifact_id="artifact:recap-22",
        source_revision_id="source-revision:recap-22",
        source_uri="repo://recaps/session-22.md",
        content_sha256="a" * 64,
        section_selector=selector,
    )

    def snapshot(projection: Any) -> Any:
        return SimpleNamespace(
            world_id=projection.world_id, campaign_id=None,
            scope_mode=projection.scope_mode,
            admissibility=projection.admissibility,
            focus=projection.focus, revision_id=projection.revision_pin,
        )

    class Retrieval:
        def get_evidence(self, projection: Any, *, target: Any, max_anchors: int) -> Any:
            assert max_anchors == 32
            assert target.kind == "assertion"
            assert target.target_id in {"assertion-internal-test", "assertion-traversal-test"}
            assert projection.revision_pin == receipt.graph_authority.graph_revision
            return SimpleNamespace(
                found=True, target=target, snapshot=snapshot(projection),
                coverage=SimpleNamespace(
                    truncated_fields=(), gap_codes=(), missing_ids=(),
                ),
                anchors=(SimpleNamespace(
                    evidence_ref_id="evidence-internal-test",
                    source_artifact_id="artifact:recap-22",
                    source_revision_id="source-revision:recap-22",
                    can_open_source=False,
                ),),
            )

        def list_source_context_index(self, request: Any) -> Any:
            return SimpleNamespace(
                status="complete", max_entries=512, eligible_count=1,
                entries=(descriptor,), snapshot=snapshot(request.projection),
            )

    monkeypatch.setattr(
        direct_reads, "direct_services_from_config",
        lambda _world: SimpleNamespace(retrieval=Retrieval()),
    )
    page_text = "The old watch shifted."
    section_digest = sha256(page_text.encode()).hexdigest()

    def read_source(request: Any) -> Any:
        assert calls[-1] == "authorize_related_recap_context"
        assert request.context_anchor_id == descriptor.context_anchor_id
        assert request.campaign_id == "" and request.scope_mode == "world"
        assert request.revision_pin == receipt.graph_authority.graph_revision
        return SimpleNamespace(
            outcome="enough", context_anchor_id=descriptor.context_anchor_id,
            context=SimpleNamespace(
                context_anchor_id=descriptor.context_anchor_id,
                world_id=descriptor.world_id,
                campaign_id=descriptor.campaign_id,
                graph_revision_id=descriptor.graph_revision_id,
                source_artifact_id=descriptor.source_artifact_id,
                source_revision_id=descriptor.source_revision_id,
                source_uri=descriptor.source_uri,
                content_sha256=descriptor.content_sha256,
                selector_schema=selector.schema_version,
                selector_policy=selector.policy,
                expected_session_id=selector.expected_session_id,
                canonical_heading=selector.canonical_heading, legacy_session_heading=selector.legacy_session_heading, legacy_recap_marker=selector.legacy_recap_marker,
            ),
            snapshot=SimpleNamespace(
                world_id=descriptor.world_id, campaign_id="", scope_mode="world",
                admissibility="gm", focus=SimpleNamespace(
                    kind="none", session_id=None, campaign_id=None,
                ),
                revision_id=descriptor.graph_revision_id,
            ),
            content=page_text, section_sha256=section_digest,
            heading_line=1, selected_form="canonical_h1", session_heading_line=1, recap_marker_line=None, line_start=2, line_end=3, offset_chars=0,
            truncated=False, next_continuation=None,
        )

    monkeypatch.setattr(source_reads, "read_recap_context_v2", read_source)
    budget = service_module._policy_request_budget() | {"schema": "dmb_hermes_request_budget_policy_v1", "maxProviderAttempts": 4, "maxToolCapableAttempts": 3, "maxGraphOperations": 8}  # Frozen finite fixture
    adapter = service_module._PolicyExecutionAdapter(
        service=object(), request=_request(), world_id=turn.world_id, work=None,
        bootstrap=service_module.AgentPlanWorldGraphBootstrap(
            graph_envelope={},
            world_scope=service_module.AgentWorldScope(
                world_id=receipt.graph_authority.native_world_id,
                campaign_id="", focus={"kind": "none"}, admissibility="gm",
                revision_id=receipt.graph_authority.graph_revision, scope_mode="world",
            ),
            retrieval_session=session, binding_version=1,
            source_root_relpath="corpus", candidate_assertion_ids=(),
            candidate_relationship_ids=(), candidate_evidence_ref_ids=(),
            evidence_by_anchor_id={},
        ),
        playable_target=None, submitted_intent=None,
        existing_turn=turn, budget=budget,
    )
    adapter.fence = Fence()
    adapter.last_provider_attempt_id = uuid4()
    return SimpleNamespace(
        adapter=adapter, turn=turn, receipt=receipt, session=session, calls=calls,
        descriptor=descriptor, retrieval_type=Retrieval, read_source=read_source,
        source_reads=source_reads, direct_reads=direct_reads, page_text=page_text,
        section_digest=section_digest, budget=budget, graph_types=graph_types,
        service_module=service_module,
    )


def _denial_authorization_fixture(monkeypatch: Any) -> tuple[Any, Any]:
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference",
        lambda **_kwargs: ("openai-api", "gpt-6-luna", "https://api.openai.com/v1"),
    )
    fixture = _related_recap_broker_fixture(monkeypatch)
    adapter = fixture.adapter
    # This seam isolates inclusion after receipt/claim. The same owning ledger
    # fake validates the provider events; existing entrypoint tests cover freeze.
    monkeypatch.setattr(adapter, "_ensure_claimed", lambda _view: (adapter.fence.turn, [], [], []))

    def authorize(items: list[dict[str, Any]]) -> bool:
        payload = json.dumps({"input": items, "tools": []})
        return adapter.authorize({
            "provider": adapter.budget["provider"], "model": adapter.budget["model"],
            "apiMode": adapter.budget["apiMode"], "payloadJson": payload,
            "payloadSha256": sha256(payload.encode()).hexdigest(), "payloadUtf8Bytes": len(payload.encode()),
        })

    assert authorize([])
    assert adapter.record_lifecycle({"transition": "sdk_entered"})
    assert adapter.record_lifecycle({"transition": "response_received"})
    return adapter, authorize


def _denial_call(tool: str, arguments: dict[str, Any], payload: str, call_id: str = "denied-call") -> list[dict[str, Any]]:
    return [
        {"type": "function_call", "call_id": call_id, "name": tool, "arguments": json.dumps(arguments)},
        {"type": "function_call_output", "call_id": call_id, "output": payload},
    ]


@pytest.mark.parametrize(
    ("invalid", "guidance"),
    [
        ({"operation": "PRIVATE_INVALID_OPERATION"}, "operation must be"),
        ({"operation": "search", "depth": 3}, "depth must be 1 or 2"),
        ({"operation": "search", "targets": [{"id": {"PRIVATE_VALUE": 1}}]}, "targets must be"),
        ({"operation": "search", "PRIVATE_EXTRA_FIELD": "PRIVATE_VALUE"}, "Remove fields outside"),
    ],
)
def test_invalid_graph_request_is_recoverable_before_native_io(
    monkeypatch: Any, invalid: dict[str, Any], guidance: str,
) -> None:
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads
    from apps.live_control_server.services.hermes_graph_agent import _GraphOperationReservation

    adapter, authorize = _denial_authorization_fixture(monkeypatch)
    calls: list[str] = []

    def forbidden_io(_world: str) -> Any:
        calls.append("native_io")
        raise AssertionError("invalid input reached native Graph IO")

    monkeypatch.setattr(world_graph_reads, "direct_services_from_config", forbidden_io)
    arguments = {"retrievalSessionId": adapter.bootstrap.retrieval_session.id, **invalid}
    initial_events = list(adapter.fence.turn.graph_context_execution.events)
    reservation = _GraphOperationReservation(
        8,
        lambda name, args: (
            adapter.broker_graph_operation({"toolName": name, "arguments": args})["resultJson"],
            None,
        ),
    )
    payload, packet = reservation("expand_graph_retrieval", arguments)
    result = json.loads(payload)
    assert result["code"] == "invalid_arguments" and result["statusCode"] == 422
    assert guidance in result["message"]
    assert "PRIVATE" not in payload
    assert calls == [] and packet is None
    assert adapter.failure is None and reservation.indeterminate is False
    assert reservation.count == 0 and adapter.operation_payloads == {}
    assert adapter.fence.turn.graph_context_execution.events == initial_events
    assert authorize(_denial_call("expand_graph_retrieval", arguments, payload))
    admitted = adapter.fence.turn.graph_context_execution.events[-1]
    assert admitted.kind == "provider_attempt_authorized_v2"
    assert admitted.included_graph_event_ids == []
    assert admitted.included_assertion_ids == []
    assert admitted.included_evidence_ref_ids == []


def _empty_native_graph_result(adapter: Any, *, revision: str | None = None) -> Any:
    from graph_memory.retrieval.models import WorldGraphRetrievalResult

    scope = adapter.bootstrap.world_scope
    return WorldGraphRetrievalResult.model_validate({
        "operation": "search", "outcome": "empty",
        "snapshot": {
            "worldId": scope.world_id, "campaignId": "", "scopeMode": "world",
            "revisionId": revision or scope.revision_id,
            "headRevisionId": scope.revision_id, "isHead": True,
            "focus": {"kind": "none", "sessionId": None}, "admissibility": "gm",
        },
    })


def test_corrected_graph_request_reaches_native_adapter_and_provider_continuation(
    monkeypatch: Any,
) -> None:
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads
    from graph_memory.interaction.session_store import clear_sessions

    adapter, authorize = _denial_authorization_fixture(monkeypatch)
    arguments = {"retrievalSessionId": adapter.bootstrap.retrieval_session.id, "operation": "PRIVATE_INVALID"}
    denied = adapter.broker_graph_operation({"toolName": "expand_graph_retrieval", "arguments": arguments})
    feedback = _denial_call("expand_graph_retrieval", arguments, denied["resultJson"])
    assert authorize(feedback)
    assert adapter.record_lifecycle({"transition": "sdk_entered"})
    assert adapter.record_lifecycle({"transition": "response_received"})
    native_requests: list[Any] = []

    def retrieve(_services: Any, request: Any) -> Any:
        native_requests.append(request)
        assert request.world_id == adapter.bootstrap.world_scope.world_id
        assert request.revision_pin == adapter.bootstrap.world_scope.revision_id
        return _empty_native_graph_result(adapter)

    monkeypatch.setattr(world_graph_reads, "search_world_graph_direct", retrieve)
    corrected = {**arguments, "operation": "search", "queryText": "synthetic query"}
    try:
        reply = adapter.broker_graph_operation({"toolName": "expand_graph_retrieval", "arguments": corrected})
        assert json.loads(reply["resultJson"])["outcome"] == "empty"
        assert len(native_requests) == 1 and adapter.failure is None
        graph_events = [event for event in adapter.fence.turn.graph_context_execution.events if event.kind == "validated_graph_operation"]
        assert len(graph_events) == 1
        assert graph_events[0].assertion_ids == [] and graph_events[0].evidence_ref_ids == []
        assert authorize([*feedback, *_denial_call("expand_graph_retrieval", corrected, reply["resultJson"], "corrected-call")])
        continuation = adapter.fence.turn.graph_context_execution.events[-1]
        assert continuation.included_graph_event_ids == [graph_events[0].event_id]
        assert continuation.included_assertion_ids == []
    finally:
        clear_sessions()


@pytest.mark.parametrize("failure", ["transport", "response_validation", "persistence", "revision"])
def test_graph_failures_after_request_validation_keep_their_authority_boundary(
    monkeypatch: Any, failure: str,
) -> None:
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads
    from graph_memory.retrieval.models import WorldGraphRetrievalResult

    adapter, authorize = _denial_authorization_fixture(monkeypatch)
    calls: list[str] = []

    def retrieve(_services: Any, _request: Any) -> Any:
        calls.append("native_io")
        if failure == "transport":
            raise ConnectionError("PRIVATE_TRANSPORT")
        if failure == "response_validation":
            return WorldGraphRetrievalResult.model_validate({"operation": "PRIVATE_INVALID_RESULT"})
        return _empty_native_graph_result(adapter, revision="foreign-revision" if failure == "revision" else None)

    monkeypatch.setattr(world_graph_reads, "search_world_graph_direct", retrieve)
    if failure == "persistence":
        original_append = adapter.fence.append

        def append(method: str, *args: Any, **kwargs: Any) -> Any:
            if method == "append_validated_graph_operation":
                raise ApplicationStateError("PRIVATE_PERSISTENCE")
            return original_append(method, *args, **kwargs)

        monkeypatch.setattr(adapter.fence, "append", append)
    arguments = {"retrievalSessionId": adapter.bootstrap.retrieval_session.id, "operation": "search"}
    reply = adapter.broker_graph_operation({"toolName": "expand_graph_retrieval", "arguments": arguments})
    result = json.loads(reply["resultJson"])
    assert calls == ["native_io"] and "PRIVATE" not in reply["resultJson"]
    assert adapter.operation_payloads == {}
    if failure == "revision":
        assert result["code"] == "graph_revision_conflict" and result["statusCode"] == 409
        assert adapter.failure is None
    else:
        assert result["code"] == "graph_operation_unavailable" and result["statusCode"] == 503
        assert adapter.failure is not None and adapter.failure.code == "graph_operation_indeterminate"
        assert not authorize(_denial_call("expand_graph_retrieval", arguments, reply["resultJson"]))


@pytest.mark.parametrize("tool", ["expand_graph_retrieval", "read_graph_source", "read_related_recap_context"])
def test_exact_parent_tool_denial_can_inform_next_request_without_becoming_evidence(monkeypatch: Any, tool: str) -> None:
    adapter, authorize = _denial_authorization_fixture(monkeypatch)
    arguments = {"retrievalSessionId": "foreign-session"}
    if tool == "expand_graph_retrieval":
        arguments["operation"] = "search"
    elif tool == "read_graph_source":
        arguments["anchorIds"] = ["foreign-anchor"]
    reply = adapter.broker_graph_operation({"toolName": tool, "arguments": arguments})
    assert json.loads(reply["resultJson"])["schema"] == "dmb_world_graph_retrieval_error_v1"
    assert adapter.failure is None
    assert authorize(_denial_call(tool, arguments, reply["resultJson"]))
    event = adapter.fence.turn.graph_context_execution.events[-1]
    assert event.kind == "provider_attempt_authorized_v2"
    assert event.included_graph_event_ids == []
    assert event.included_source_read_event_ids == []
    assert event.included_assertion_ids == []
    assert event.included_relationship_ids == []
    assert event.included_evidence_ref_ids == []
    assert len(adapter.fence.turn.graph_context_execution.events) == 4


@pytest.mark.parametrize("change", ["foreign_tool", "arguments", "payload", "unmatched", "duplicate", "forged_success"])
def test_parent_denial_exemption_requires_exact_tool_arguments_payload_and_occurrence(monkeypatch: Any, change: str) -> None:
    adapter, authorize = _denial_authorization_fixture(monkeypatch)
    tool = "read_graph_source"
    arguments = {"retrievalSessionId": "foreign-session", "anchorIds": ["foreign-anchor"]}
    payload = adapter.broker_graph_operation({"toolName": tool, "arguments": arguments})["resultJson"]
    if change == "foreign_tool":
        tool = "expand_graph_retrieval"
    if change == "arguments":
        arguments = {**arguments, "anchorIds": ["another-anchor"]}
    if change in {"payload", "forged_success"}:
        modified = json.loads(payload)
        modified["code" if change == "payload" else "schema"] = "forged_success"
        payload = json.dumps(modified)
    items = _denial_call(tool, arguments, payload)
    if change == "unmatched":
        items = items[1:]
    if change == "duplicate":
        items += _denial_call(tool, arguments, payload, "another-call")
    assert not authorize(items)
    assert adapter.failure.code == "graph_evidence_invalid"
    assert len(adapter.fence.turn.graph_context_execution.events) == 3


def test_fatal_broker_failure_blocks_later_authorization_and_preserves_original_code(monkeypatch: Any) -> None:
    adapter, authorize = _denial_authorization_fixture(monkeypatch)
    prior_execution = adapter._broker_execution

    def fail_execution() -> Any:
        raise RuntimeError("PRIVATE_BROKER_FAILURE")

    monkeypatch.setattr(adapter, "_broker_execution", fail_execution)
    arguments = {"retrievalSessionId": "foreign-session", "anchorIds": ["foreign-anchor"]}
    payload = adapter.broker_source_read({"toolName": "read_graph_source", "arguments": arguments})["resultJson"]
    original_failure = adapter.failure
    assert original_failure.code == "source_read_indeterminate"
    assert "PRIVATE_BROKER_FAILURE" not in payload
    monkeypatch.setattr(adapter, "_broker_execution", prior_execution)
    assert not authorize(_denial_call("read_graph_source", arguments, payload))
    assert adapter.failure is original_failure
    assert len(adapter.fence.turn.graph_context_execution.events) == 3


def _related_recap_request(fixture: Any, **updates: Any) -> dict[str, Any]:
    return {
        "toolName": "read_related_recap_context",
        "arguments": {
            "retrievalSessionId": fixture.session.id,
            "targetKind": "assertion", "targetId": "assertion-internal-test",
            "evidenceRefIds": ["evidence-internal-test"],
            "contextAnchorId": fixture.descriptor.context_anchor_id,
            **updates,
        },
    }


@pytest.mark.parametrize("capture_gap", [False, True])
def test_parent_related_recap_broker_persists_verified_context_without_evidence_upgrade(
    monkeypatch: Any, capture_gap: bool,
) -> None:
    from types import SimpleNamespace

    fixture = _related_recap_broker_fixture(monkeypatch)
    adapter, receipt, session = fixture.adapter, fixture.receipt, fixture.session
    descriptor, calls = fixture.descriptor, fixture.calls
    Retrieval, direct_reads = fixture.retrieval_type, fixture.direct_reads
    page_text, budget = fixture.page_text, fixture.budget
    traversal = SimpleNamespace(
        snapshot=SimpleNamespace(
            world_id=receipt.graph_authority.native_world_id,
            revision_id=receipt.graph_authority.graph_revision,
        ),
        attributes=(SimpleNamespace(
            assertion_id="assertion-traversal-test",
            evidence_ref_ids=("evidence-internal-test",),
        ),),
        relationships=(),
        source_anchors=(SimpleNamespace(
            anchor_id="old-unreadable-anchor",
            evidence_ref_id="evidence-internal-test",
            readable=False, locator_kind="unsupported",
        ),),
        coverage=SimpleNamespace(truncated_fields=()),
        outcome="enough",
        model_dump=lambda **_kwargs: {
            "schema": "dmb_world_graph_retrieval_result_v1",
            "operation": "search", "outcome": "enough",
            "attributes": [{
                "assertionId": "assertion-traversal-test",
                "evidenceRefIds": ["evidence-internal-test"],
            }],
            "sourceAnchors": [{
                "anchorId": "old-unreadable-anchor",
                "evidenceRefId": "evidence-internal-test", "readable": False,
            }],
        },
    )
    from graph_memory.interaction import authority_classifier, session_store

    monkeypatch.setattr(authority_classifier, "claims_from_retrieval_result", lambda *_a, **_kw: [])
    monkeypatch.setattr(session_store, "replace_session", lambda _session: None)
    monkeypatch.setattr(direct_reads, "search_world_graph_direct", lambda *_a: traversal)
    graph_packet = adapter.broker_graph_operation({
        "toolName": "expand_graph_retrieval",
        "arguments": {
            "retrievalSessionId": session.id, "operation": "search",
        },
    })
    offered = json.loads(graph_packet["resultJson"])["relatedRecapContexts"]
    assert offered == [{
        "targetKind": "assertion", "targetId": "assertion-traversal-test",
        "evidenceRefIds": ["evidence-internal-test"],
        "contextAnchorId": descriptor.context_anchor_id,
        "sourceCampaignId": "longmont-c2",
    }]
    for invalid in (
        {"targetId": "assertion-not-in-turn"},
        {"evidenceRefIds": ["evidence-not-in-turn"]},
        {"contextAnchorId": "dm-context-anchor:v2:wrong"},
    ):
        attempted = adapter.broker_related_recap_context({
            "toolName": "read_related_recap_context",
            "arguments": {
                "retrievalSessionId": session.id,
                "targetKind": "assertion", "targetId": "assertion-traversal-test",
                "evidenceRefIds": ["evidence-internal-test"],
                "contextAnchorId": offered[0]["contextAnchorId"],
                **invalid,
            },
        })
        assert json.loads(attempted["resultJson"])["code"] == (
            "related_recap_context_not_admitted"
        )
    descriptor.graph_revision_id = "stale-graph-revision"
    stale = adapter.broker_related_recap_context({
        "toolName": "read_related_recap_context",
        "arguments": {
            "retrievalSessionId": session.id,
            "targetKind": "assertion", "targetId": "assertion-traversal-test",
            "evidenceRefIds": ["evidence-internal-test"],
            "contextAnchorId": offered[0]["contextAnchorId"],
        },
    })
    assert json.loads(stale["resultJson"])["code"] == "related_recap_context_not_admitted"
    descriptor.graph_revision_id = receipt.graph_authority.graph_revision
    original_index = Retrieval.list_source_context_index

    def overflow_index(self: Any, request: Any) -> Any:
        result = original_index(self, request)
        return SimpleNamespace(**{
            **vars(result), "status": "overflow", "entries": (),
        })

    monkeypatch.setattr(Retrieval, "list_source_context_index", overflow_index)
    overflow = adapter.broker_related_recap_context({
        "toolName": "read_related_recap_context",
        "arguments": {
            "retrievalSessionId": session.id,
            "targetKind": "assertion", "targetId": "assertion-traversal-test",
            "evidenceRefIds": ["evidence-internal-test"],
            "contextAnchorId": offered[0]["contextAnchorId"],
        },
    })
    assert json.loads(overflow["resultJson"])["code"] == "related_recap_context_not_admitted"
    monkeypatch.setattr(Retrieval, "list_source_context_index", original_index)
    assert calls == ["append_validated_graph_operation"]
    gap_observations, gap_codes = [], []
    if capture_gap:
        adapter.context_capture = SimpleNamespace(
            observe=lambda fields: gap_observations.append(fields),
            mark_incomplete=lambda code: gap_codes.append(code),
            provider_context=lambda *args, **kwargs: None,
        )
    output = adapter.broker_related_recap_context({
        "toolName": "read_related_recap_context",
        "arguments": {
            "retrievalSessionId": session.id,
            "targetKind": "assertion", "targetId": "assertion-traversal-test",
            "evidenceRefIds": ["evidence-internal-test"],
            "contextAnchorId": offered[0]["contextAnchorId"],
        },
    })
    assert calls == [
        "append_validated_graph_operation", "authorize_related_recap_context",
        "record_validated_related_recap_context",
    ]
    assert json.loads(output["resultJson"])["content"] == page_text
    if capture_gap:
        assert gap_codes == ["recap_context_capture_unavailable"]
        assert gap_observations == [{"kind": "failure", "phase": "trace_capture", "code": "recap_context_capture_unavailable"}]
        assert page_text not in json.dumps(gap_observations)
    saved = adapter.fence.turn.graph_context_execution
    assert saved.events[1].admission.descriptor_campaign_id == "longmont-c2"
    assert saved.events[1].admission.campaign_id is None
    assert saved.events[1].admission.admission_origin == "validated_graph_operation"
    assert page_text not in saved.model_dump_json()
    assert descriptor.source_uri not in saved.model_dump_json()
    assert len(adapter.context_payloads) == 1

    provider_body = json.dumps({
        "input": [
            {"type": "function_call", "call_id": "recap:one",
             "name": "read_related_recap_context"},
            {"type": "function_call_output", "call_id": "recap:one",
             "output": output["resultJson"]},
        ],
        "tools": [],
    })
    view = {
        "provider": budget["provider"], "model": budget["model"],
        "apiMode": budget["apiMode"], "payloadJson": provider_body,
        "payloadSha256": sha256(provider_body.encode()).hexdigest(),
        "payloadUtf8Bytes": len(provider_body.encode()),
    }
    adapter._ensure_claimed = lambda _view: (adapter.fence.turn, [], [], [])
    assert adapter.authorize(view) is True
    assert calls[-2:] == [
        "record_related_recap_context_inclusion", "authorize_provider_attempt_v2",
    ]
    persisted = adapter.fence.turn.graph_context_execution
    assert persisted.events[-2].included_chars == len(page_text)
    included = persisted.events[-2]
    dispatched = persisted.events[-1]
    validated = saved.events[-1]
    assert included.included_context_event_ids == [validated.event_id]
    assert included.included_context_sha256 == (
        fixture.graph_types.related_recap_context_inclusion_digest([validated])
    )
    assert included.envelope_sha256 == dispatched.envelope_sha256 == view["payloadSha256"]
    assert included.provider_attempt_id == dispatched.provider_attempt_id
    assert json.loads(view["payloadJson"])["input"][1]["output"] == (
        adapter.context_payloads[validated.event_id]
    )
    assert dispatched.included_assertion_ids == []
    assert dispatched.included_relationship_ids == []
    assert dispatched.included_evidence_ref_ids == []
    assert persisted.events[-1].included_source_read_event_ids == []
    assert persisted.policy.source_opened is False
    assert page_text not in persisted.model_dump_json()
    duplicated = json.loads(provider_body)
    duplicated["input"].extend(duplicated["input"])
    duplicated_body = json.dumps(duplicated)
    assert adapter.authorize({
        **view, "payloadJson": duplicated_body,
        "payloadSha256": sha256(duplicated_body.encode()).hexdigest(),
        "payloadUtf8Bytes": len(duplicated_body.encode()),
    }) is False
    assert adapter.failure is not None
    assert adapter.failure.code == "graph_evidence_invalid"


def test_parent_related_recap_known_core_id_requires_admitted_target_and_join(
    monkeypatch: Any,
) -> None:
    fixture = _related_recap_broker_fixture(monkeypatch)
    assert fixture.adapter.operation_payloads == {}
    # This ID is valid in Core, but it cannot authorize an unrelated target.
    denied = fixture.adapter.broker_graph_operation(_related_recap_request(
        fixture, targetId="unadmitted-other-target",
    ))
    assert json.loads(denied["resultJson"])["code"] == "related_recap_context_not_admitted"
    assert fixture.calls == [] and fixture.adapter.context_payloads == {}
    # A previously known ID needs no redundant offer receipt: the full frozen
    # target/ref + same-pin Core provenance/index join remains the authority.
    output = fixture.adapter.broker_graph_operation(_related_recap_request(fixture))
    assert json.loads(output["resultJson"])["content"] == fixture.page_text
    events = fixture.adapter.fence.turn.graph_context_execution.events
    assert events[0].admission.admission_origin == "initial_graph_input"
    assert events[0].admission.context_anchor_id == fixture.descriptor.context_anchor_id
    assert fixture.descriptor.source_uri not in fixture.adapter.fence.turn.graph_context_execution.model_dump_json()


def test_parent_related_recap_selected_index_admission(monkeypatch: Any) -> None:
    fixture = _related_recap_broker_fixture(monkeypatch)
    graph_types = fixture.graph_types
    digest = fixture.service_module._canonical_sha256
    authority = fixture.receipt.graph_authority
    context = {
        "world_id": authority.native_world_id, "campaign_id": None,
        "scope_mode": "world_cross_campaign",
        "focus": {"kind": "none", "session_id": None},
        "admissibility": "gm", "revision_id": authority.graph_revision,
    }
    targets = [{"kind": "assertion", "target_id": "assertion-traversal-test"}]
    entries = [{
        "anchor_id": "dm-source-anchor:v1:selected-recap",
        "evidence_ref_id": "evidence-internal-test",
        "source_artifact_id": fixture.descriptor.source_artifact_id,
        "source_revision_id": fixture.descriptor.source_revision_id,
    }]
    selector_sha = digest({
        "schema": "dm_selected_source_anchor_selector_v1",
        "context": context, "max_entries": 512, "targets": targets,
    })
    index_sha = digest({
        "schema": "dm_selected_source_anchor_index_v1",
        "selector_sha256": selector_sha, "status": "complete",
        "admitted_targets": targets, "not_visible_targets": [],
        "provenance_gap_count": 0, "unavailable_binding_count": 0,
        "eligible_count": 1, "entries": entries,
    })
    commitment = graph_types.GraphSelectedIndexCommitmentV1.model_validate({
        "context": context, "access_context_sha256": digest(context),
        "requested_targets": targets, "admitted_targets": targets,
        "not_visible_targets": [], "requested_count": 1, "admitted_count": 1,
        "not_visible_count": 0, "provenance_gap_count": 0,
        "unavailable_binding_count": 0, "eligible_count": 1,
        "max_entries": 512, "status": "complete", "index_scope": "selected_targets",
        "selector_sha256": selector_sha, "index_sha256": index_sha,
    })
    prior = fixture.adapter.fence.turn.graph_context_execution
    scope = graph_types.GraphSelectedSourceReadScopeV2(
        retrieval_session_id=fixture.session.id, world_id=authority.managed_world_id,
        campaign_id=None, graph_revision=authority.graph_revision,
        admitted_anchors=entries, selected_index_commitment=commitment,
        initial_claim_packet_sha256=fixture.receipt.assembled_input.dispatched_packet_sha256,
    )
    policy = graph_types.GraphExecutionPolicyV2.model_validate({
        **prior.policy.model_dump(mode="json", by_alias=True),
        "policy_version": "plan_world_graph_execution_selected_scope_v1",
        "source_read_scope": scope.model_dump(mode="json", by_alias=True),
    })
    execution = graph_types.PlanWorldGraphExecutionV2(
        context_receipt_sha256=prior.context_receipt_sha256, policy=policy, events=[],
        execution_policy_sha256=digest({
            "schema": "dmb_agent_plan_world_graph_execution_v2",
            "context_receipt_sha256": prior.context_receipt_sha256,
            "policy": policy.model_dump(mode="json", by_alias=True),
        }),
    )
    fixture.adapter.fence.turn = fixture.turn.model_copy(update={
        "graph_context_execution": execution,
    })
    output = fixture.adapter.broker_graph_operation(_related_recap_request(
        fixture, targetId="assertion-traversal-test",
    ))
    assert json.loads(output["resultJson"])["content"] == fixture.page_text
    events = fixture.adapter.fence.turn.graph_context_execution.events
    assert fixture.calls == [
        "authorize_related_recap_context", "record_validated_related_recap_context",
    ]
    assert events[0].admission.admission_origin == "selected_index_admission"
    assert events[0].admission.selected_index_sha256 == index_sha
    assert events[0].admission.admission_graph_event_id is None


@pytest.mark.parametrize("frozen_v1", [False, True], ids=["unfrozen", "frozen-v1"])
def test_reconciled_turn_context_policy_before_provider_freeze(
    monkeypatch: Any, tmp_path: Path, frozen_v1: bool,
) -> None:
    fixture = _related_recap_broker_fixture(monkeypatch)
    accepted = _policy_turn(status="accepted", completion_present=False)
    receipt = accepted.graph_context_receipt
    assert receipt is not None and accepted.graph_context_execution is None
    graph_types, service_module = fixture.graph_types, fixture.service_module
    if frozen_v1:
        policy = graph_types.GraphExecutionPolicyV1.model_validate({
            key: value
            for key, value in fixture.adapter.fence.turn.graph_context_execution.policy.model_dump(mode="json").items()
            if key in graph_types.GraphExecutionPolicyV1.model_fields
        })
        accepted = accepted.model_copy(update={
            "graph_context_execution": graph_types.PlanWorldGraphExecutionV1(
                context_receipt_sha256=receipt.context_receipt_sha256,
                policy=policy, events=[],
            ),
        })
    basis = AgentTurnContentBasis(
        world_id=accepted.world_id, document_id=receipt.plan_basis.document_id,
        object_revision=receipt.plan_basis.object_revision,
        work_revision_id=str(receipt.plan_basis.work_revision_id),
        revision_n=receipt.plan_basis.revision_n,
        content_sha256=receipt.plan_basis.content_sha256,
        committed_status="committed", has_divergent_working_copy=False,
    )
    work = AgentTurnResolvedWork(
        kind="plan", object_id=basis.document_id, revision=basis.object_revision,
        changed_since_expected=False, owner_kind="world", owner_id=accepted.world_id,
        world_id=accepted.world_id, content_basis=basis, plan_markdown="The keeper waits.",
    )
    request = _request(
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": accepted.world_id},
        primary_work={
            "kind": "plan", "object_id": basis.document_id,
            "expected_revision": basis.object_revision, "expected_revision_n": basis.revision_n,
            "expected_content_sha256": basis.content_sha256,
        },
        client_work_state="saved_clean", plan_context_policy={"policy": "auto_plan_world"},
        message=accepted.user_text,
    )
    bootstrap = replace(fixture.adapter.bootstrap, binding_version=2, graph_envelope={
        "revision_id": receipt.graph_authority.graph_revision,
        "world_id": receipt.graph_authority.native_world_id, "scope_mode": "world",
    })
    observed: list[bool] = []
    segment_thread_id = service_module._provider_segment_thread_id(
        accepted.provenance, conversation_id=accepted.conversation_id,
    )

    def no_dispatch(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("This pre-freeze policy witness must not dispatch or mutate APP")

    class ReconciledService:
        def reconcile_turn(self, *_args: Any) -> Turn:
            return accepted

        accept_turn = claim_turn = authorize_provider_attempt = no_dispatch
        record_provider_outcome = append_validated_graph_operation = no_dispatch
        complete_turn = fail_turn = renew_turn_claim = no_dispatch

    class InspectingRuntime:
        descriptor = AgentRuntimeDescriptor("pre-freeze", "fake", "test", "graph")

        def run_with_provider_authorization(
            self, invocation: Any, _authorize: Any, *, request_budget: Any,
            on_graph_operation: Any, on_provider_lifecycle: Any,
            context_read_enabled: bool = False,
        ) -> AgentRuntimeResult:
            assert invocation.run_options.runtime_session_id == "canonical-session"
            observed.append(context_read_enabled)
            projection = bootstrap.retrieval_session.project_for_hermes()
            body = json.dumps({
                "input": [{"role": "system", "content":
                    "Turn capability policy (runtime-enforced; also required on tool calls):\n"
                    + json.dumps({"initialClaimPacket": {
                        "candidates": projection["candidates"][:8],
                        "claimLedger": projection["claim_ledger"][:24],
                        "intentHint": projection["intent_hint"],
                        "availableExpansions": projection["available_expansions"],
                    }}),
                }, {"role": "user", "content": service_module._plan_message(
                    request.message, work.plan_markdown, content_basis=basis,
                )}], "tools": [],
            })
            view = {
                "provider": request_budget["provider"], "model": request_budget["model"],
                "apiMode": request_budget["apiMode"], "payloadJson": body,
                "payloadSha256": sha256(body.encode()).hexdigest(),
                "payloadUtf8Bytes": len(body.encode()),
            }
            frozen_receipt, execution, _ = service_module._freeze_policy_receipt(
                request, work, bootstrap, None, view, request_budget,
                context_read_enabled=context_read_enabled,
            )
            assert isinstance(execution, (
                graph_types.PlanWorldGraphExecutionV1 if frozen_v1
                else graph_types.PlanWorldGraphExecutionV3
            ))
            if not frozen_v1:
                assert execution.policy.source_read_scope.admitted_anchors == []
                assert execution.policy.max_source_read_chars == 96_000
                assert not hasattr(execution.policy, "max_source_read_calls")
                existing_without_ledger = accepted.model_copy(update={
                    "graph_context_receipt": frozen_receipt,
                    "graph_context_execution": None,
                })
                blocked_adapter = service_module._PolicyExecutionAdapter(
                    service=ReconciledService(), request=request,
                    world_id=accepted.world_id, work=work, bootstrap=bootstrap,
                    playable_target=None,
                    submitted_intent=_submitted_turn_intent(request, world_id=accepted.world_id),
                    existing_turn=existing_without_ledger, budget=request_budget,
                    context_read_enabled=True,
                )
                assert blocked_adapter.authorize(view) is False
                assert blocked_adapter.failure.code == "turn_receipt_unverifiable"
                assert blocked_adapter.failure.provider_dispatched is False
                assert blocked_adapter.fence is None
                # Exercise APP's immutable acceptance boundary without a DB:
                # idempotent reaccept cannot attach a new execution to this row.
                from contextlib import contextmanager
                from application_state.agent_conversation import service as app_service

                @contextmanager
                def no_database(_dsn: Any) -> Any:
                    yield object()

                submitted = _submitted_turn_intent(request, world_id=accepted.world_id)
                submission = graph_types.TurnSubmission(
                    world_id=accepted.world_id, conversation_id=accepted.conversation_id,
                    idempotency_key=accepted.idempotency_key, expected_conversation_revision=1,
                    user_text=request.message, provenance=accepted.provenance,
                    submitted_intent_v2=submitted,
                    graph_context_receipt=frozen_receipt, graph_context_execution=execution,
                )
                with monkeypatch.context() as app_contract:
                    app_contract.setattr(app_service, "_ready_dsn", lambda: "unused")
                    app_contract.setattr(app_service, "unit_of_work", no_database)
                    app_contract.setattr(app_service.repo, "get_turn_by_world_key", lambda *_args: (
                        existing_without_ledger, "old-request", "old-idempotency", None,
                        app_service.submitted_turn_intent_fingerprint_v2(submitted),
                    ))
                    with pytest.raises(ApplicationStateConflictError, match="Graph receipt"):
                        app_service.AgentConversationService().accept_turn(submission)
            return AgentRuntimeResult(
                status="error", error_code="request_budget_exceeded",
                observed_model_call_count=0,
            )

    pointer_store = HermesSessionPointerStore(tmp_path / "pointers")
    pointer_store.upsert_structured_after_turn(
        owner_kind="world", owner_id=accepted.world_id,
        work_kind="agent_conversation_segment", work_id=segment_thread_id,
        agent_thread_id=segment_thread_id,
        hermes_session_id="canonical-session",
    )
    with pytest.raises(AgentTurnServiceError) as stopped:
        execute_agent_turn(
            request, root=tmp_path,
            pointer_store=pointer_store,
            owner_resolver=lambda _request: {
                "kind": "world", "id": accepted.world_id, "name": "World One",
            },
            work_resolver=no_dispatch,
            historical_work_resolver=lambda *_args: work,
            graph_resolver=no_dispatch,
            plan_graph_resolver=lambda *_args, **_kwargs: bootstrap,
            runtime=InspectingRuntime(), conversation_service=ReconciledService(),
        )
    assert stopped.value.code == "plan_context_delivery_failure"
    assert observed == [not frozen_v1]
    assert accepted.graph_context_execution is None if not frozen_v1 else isinstance(
        accepted.graph_context_execution, graph_types.PlanWorldGraphExecutionV1
    )


@pytest.mark.parametrize("change", [
    None, "unknown_token", "core_campaign", "source_campaign", "offset", "section", "range",
])
def test_parent_related_recap_continuation_matches_descriptor_and_pages(
    monkeypatch: Any, change: str | None,
) -> None:
    fixture = _related_recap_broker_fixture(monkeypatch)
    pages = ["The old watch ", "shifted."]
    section_sha = sha256("".join(pages).encode()).hexdigest()
    continuation = "opaque-next-page"
    requests: list[Any] = []

    def paged_source(request: Any) -> Any:
        requests.append(request)
        result = fixture.read_source(request)
        second = request.continuation is not None
        result.content = pages[int(second)]
        result.section_sha256 = section_sha
        result.offset_chars = len(pages[0]) if second else 0
        result.outcome = "enough" if second else "truncated"
        result.truncated = not second
        result.next_continuation = None if second else continuation
        if second:
            assert request.continuation == continuation
            if change == "source_campaign":
                result.context.campaign_id = "wrong-campaign"
            elif change == "offset":
                result.offset_chars += 1
            elif change == "section":
                result.section_sha256 = "b" * 64
            elif change == "range":
                result.line_end += 1
        return result

    monkeypatch.setattr(fixture.source_reads, "read_recap_context_v2", paged_source)
    first = fixture.adapter.broker_graph_operation(_related_recap_request(fixture))
    first_payload = json.loads(first["resultJson"])
    assert first_payload["content"] == pages[0]
    assert first_payload["nextContinuation"] == continuation
    assert fixture.adapter.fence.turn.graph_context_execution.events[0].admission.admission_origin == (
        "initial_graph_input"
    )
    if change == "core_campaign":
        fixture.descriptor.campaign_id = "changed-descriptor-campaign"
    second = fixture.adapter.broker_graph_operation(_related_recap_request(
        fixture, continuation=("unissued-token" if change == "unknown_token" else continuation),
    ))
    payload = json.loads(second["resultJson"])
    events = fixture.adapter.fence.turn.graph_context_execution.events
    if change is None:
        assert payload["content"] == pages[1]
        assert payload["offsetChars"] == len(pages[0])
        assert payload["nextContinuation"] is None
        assert len(requests) == 2 and len(fixture.adapter.context_payloads) == 2
        assert events[2].continuation_in_sha256 == events[1].continuation_out_sha256
        assert events[3].offset_chars == events[1].returned_chars
        assert events[3].section_sha256 == events[1].section_sha256
        assert events[3].source_bytes_sha256 == events[1].source_bytes_sha256
    else:
        assert "content" not in payload and pages[1] not in second["resultJson"]
        assert len(fixture.adapter.context_payloads) == 1
        assert sum(event.kind == "validated_related_recap_context_v2" for event in events) == 1
        if change in {"unknown_token", "core_campaign"}:
            assert payload["code"] == "related_recap_context_not_admitted"
            assert len(requests) == 1 and len(events) == 2
        else:
            assert payload["code"] == "related_recap_context_unavailable"
            assert len(requests) == 2 and len(events) == 3
    assert continuation not in fixture.adapter.fence.turn.graph_context_execution.model_dump_json()


@pytest.mark.parametrize(("owner", "field", "value"), [
    ("context", "campaign_id", "wrong-campaign"),
    ("context", "world_id", "wrong-world"),
    ("context", "source_artifact_id", "wrong-artifact"),
    ("context", "source_revision_id", "wrong-source-revision"),
    ("context", "source_uri", "repo://recaps/foreign.md"),
    ("context", "content_sha256", "b" * 64),
    ("context", "selector_policy", "wrong-selector"),
    ("context", "canonical_heading", "# Wrong heading"),
    ("context", "legacy_session_heading", "## Session 99:"),
    ("context", "legacy_recap_marker", "Recap:"),
    ("result", "selected_form", "legacy_h2"),
    ("result", "session_heading_line", 2),
    ("result", "recap_marker_line", 2),
    ("snapshot", "revision_id", "wrong-graph-revision"),
    ("snapshot", "scope_mode", "campaign"),
    ("focus", "session_id", "unexpected-session"),
    ("focus", "campaign_id", "unexpected-campaign"),
    ("result", "section_sha256", "invalid-digest"),
    ("result", "offset_chars", 1),
    ("result", "line_start", 1),
    ("result", "line_end", 1),
])
def test_parent_related_recap_rejects_source_metadata_before_release(
    monkeypatch: Any, owner: str, field: str, value: Any,
) -> None:
    fixture = _related_recap_broker_fixture(monkeypatch)

    def wrong_source(request: Any) -> Any:
        result = fixture.read_source(request)
        returned = (
            result if owner == "result" else
            result.snapshot.focus if owner == "focus" else getattr(result, owner)
        )
        setattr(returned, field, value)
        return result

    monkeypatch.setattr(fixture.source_reads, "read_recap_context_v2", wrong_source)
    output = fixture.adapter.broker_graph_operation(_related_recap_request(fixture))
    payload = json.loads(output["resultJson"])
    assert payload["code"] == "related_recap_context_unavailable"
    assert "content" not in payload and fixture.page_text not in output["resultJson"]
    assert fixture.adapter.context_payloads == {}
    assert len(fixture.adapter.fence.turn.graph_context_execution.events) == 1
    assert fixture.calls == ["authorize_related_recap_context"]


@pytest.mark.parametrize("max_chars", [0, 12001, True])
def test_parent_related_recap_per_call_quota_prevents_source_io(
    monkeypatch: Any, max_chars: Any,
) -> None:
    fixture = _related_recap_broker_fixture(monkeypatch)
    output = fixture.adapter.broker_graph_operation(_related_recap_request(
        fixture, maxChars=max_chars,
    ))
    assert json.loads(output["resultJson"])["code"] == "invalid_arguments"
    assert fixture.calls == [] and fixture.adapter.context_payloads == {}


def test_parent_related_recap_eight_call_and_total_character_quota(monkeypatch: Any) -> None:
    fixture = _related_recap_broker_fixture(monkeypatch)
    page = "x" * 12000
    source_calls: list[Any] = []

    def full_page(request: Any) -> Any:
        source_calls.append(request)
        result = fixture.read_source(request)
        result.content = page
        result.section_sha256 = sha256(page.encode()).hexdigest()
        return result

    monkeypatch.setattr(fixture.source_reads, "read_recap_context_v2", full_page)
    for _ in range(8):
        output = fixture.adapter.broker_graph_operation(_related_recap_request(
            fixture, maxChars=12000,
        ))
        assert json.loads(output["resultJson"])["content"] == page
    events = fixture.adapter.fence.turn.graph_context_execution.events
    assert sum(
        event.max_chars for event in events
        if event.kind == "related_recap_context_authorized_v2"
    ) == 96000
    assert sum(
        event.returned_chars for event in events
        if event.kind == "validated_related_recap_context_v2"
    ) == 96000
    denied = fixture.adapter.broker_graph_operation(_related_recap_request(fixture, maxChars=1))
    assert json.loads(denied["resultJson"])["code"] == "related_recap_context_over_budget"
    assert len(source_calls) == 8
    assert len(fixture.adapter.fence.turn.graph_context_execution.events) == 16


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
@pytest.mark.parametrize("anchor_readable", [True, False], ids=["readable", "opaque"])
def test_policy_adapter_freezes_first_envelope_and_fences_provider_lifecycle(
    monkeypatch: Any,
    plan_markdown: str,
    anchor_readable: bool,
    caplog: Any,
) -> None:
    from datetime import timedelta
    from application_state.agent_conversation import types as graph_types
    if not hasattr(graph_types, "PlanWorldGraphExecutionV1"):
        pytest.skip("run with pinned APP-STATE candidate")
    from apps.live_control_server.services import agent_turn_service as service_module
    from apps.live_control_server.services.agent_turn_trace import AgentTurnTraceBuilder
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference",
        lambda **_kwargs: ("openai-api", "gpt-6-luna", "https://api.openai.com/v1"),
    )
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from graph_memory.interaction.session import (
        CoverageState, GraphRetrievalSession, SessionSnapshot, SourceAnchorState,
    )
    from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
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
        claims=claims_from_retrieval_result({
            "relationships": [{
                "edgeId": "rel:seed", "sourceNodeId": "node:one",
                "targetNodeId": "node:two", "predicate": "guards",
                "evidenceRefIds": ["ev:one"],
            }],
            "sourceAnchors": [{
                "anchorId": "anchor:one", "revisionId": "graph-revision-3",
                "evidenceRefId": "ev:one", "readable": anchor_readable,
                "supportingGraphObjectIds": [],
            }],
        }, revision_id="graph-revision-3"),
        source_anchors=[SourceAnchorState(anchor_id="anchor:one", readable=anchor_readable)],
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
        candidate_assertion_ids=(), candidate_relationship_ids=("rel:seed",),
        candidate_evidence_ref_ids=("ev:one",),
        evidence_by_anchor_id={"anchor:one": "ev:one"},
    )
    projected = session.project_for_hermes()
    initial_packet = {
        "candidates": projected["candidates"][:8],
        "claimLedger": projected["claim_ledger"][:24],
        "intentHint": projected["intent_hint"],
        "availableExpansions": projected["available_expansions"],
    }
    assert initial_packet["claimLedger"][0]["claim_id"] == "rel:seed"
    assert initial_packet["claimLedger"][0]["evidence_ref_ids"] == ["ev:one"]
    assert initial_packet["claimLedger"][0]["support"]["source_anchor_ids"] == ["anchor:one"]
    assert initial_packet["claimLedger"][0]["support"]["source_read_ids"] == []
    assert initial_packet["claimLedger"][0]["support"]["state"] == (
        "source_anchor_available" if anchor_readable else "source_anchor_unreadable"
    )
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
    assert (budget["maxProviderAttempts"], budget["maxToolCapableAttempts"],
            budget["maxGraphOperations"]) == (None, None, None)
    source_receipt, source_execution, membership = service_module._freeze_policy_receipt(
        request, work, replace(bootstrap, source_scope_anchors=({
            "anchor_id": "anchor:one", "evidence_ref_id": "ev:one",
            "source_artifact_id": "artifact:one",
            "source_revision_id": "source-revision:one",
        },)), None, view, budget,
    )
    assert membership == ([], ["rel:seed"], ["ev:one"])
    assert source_receipt.assembled_input.packet_disposition == "included"
    assert source_receipt.assembled_input.dispatched_relationship_ids == ["rel:seed"]
    assert source_receipt.assembled_input.dispatched_evidence_ref_ids == ["ev:one"]
    assert source_receipt.source_opened is False
    assert isinstance(source_execution, graph_types.PlanWorldGraphExecutionV3)
    assert source_execution.policy.source_read_scope.world_id == "world:one"
    assert source_execution.policy.source_read_scope.admitted_anchors[0].source_revision_id == (
        "source-revision:one"
    )
    assert source_execution.policy.max_source_read_chars == 96_000
    assert not hasattr(source_execution.policy, "max_source_read_calls")
    _, context_execution, _ = service_module._freeze_policy_receipt(
        request, work, bootstrap, None, view, budget,
        context_read_enabled=True,
    )
    assert isinstance(context_execution, graph_types.PlanWorldGraphExecutionV3)
    assert context_execution.policy.source_read_scope.admitted_anchors == []
    assert context_execution.policy.max_source_read_chars == 96_000

    class FakeExecutionPort:
        # This execution-ledger fake has no previous conversation to restore.
        def get_active_conversation(self, _world_id: str) -> None:
            return None

        turn: Turn | None = None
        accepted_count = 0
        authorize_count = 0
        fail_count = 0
        fail_error: Exception | None = None
        before_delivery_ledger: Any = None

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
            updated = type(execution).model_validate({
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

        authorize_provider_attempt_v2 = authorize_provider_attempt

        def record_provider_outcome(self, _world_id: str, _conversation_id: Any, _turn_id: Any, *, expected_revision: int, expected_attempt: int, outcome: Any) -> tuple[Turn, bool]:
            return self._append(outcome, expected_revision, expected_attempt)

        def append_validated_graph_operation(self, _world_id: str, _conversation_id: Any, _turn_id: Any, *, expected_revision: int, expected_attempt: int, operation_event: Any) -> tuple[Turn, bool]:
            return self._append(operation_event, expected_revision, expected_attempt)

        def extend_source_scope(self, *_args, expected_revision, expected_attempt, extension):
            return self._append(extension, expected_revision, expected_attempt)

        def authorize_source_read(self, *_args, expected_revision, expected_attempt, authorization):
            return self._append(authorization, expected_revision, expected_attempt)

        def record_validated_source_read(self, *_args, expected_revision, expected_attempt, receipt):
            return self._append(receipt, expected_revision, expected_attempt)

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
            updated_execution = type(execution).model_validate({
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

        def fail_turn(self, failure: Any, *, interrupted: bool = False) -> Turn:
            self.fail_count += 1
            assert self.turn is not None
            assert failure.expected_revision == self.turn.revision
            assert interrupted is True
            if self.fail_error is not None:
                raise self.fail_error
            self.turn = self.turn.model_copy(update={
                "status": "interrupted", "revision": self.turn.revision + 1,
                "failure_code": failure.failure_code, "claim_expires_at": None,
                "completed_at": datetime.now(UTC),
            })
            return self.turn

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
    trace = AgentTurnTraceBuilder(
        agent_thread_id=None,
        turn_id=request.turn_id,
        runtime="test",
        backend="test",
        mode="test",
    )
    admission_span_id = trace.start_phase("runtime_to_admission")
    adapter = service_module._PolicyExecutionAdapter(
        service=fake, request=request, world_id="world:one", work=work,
        bootstrap=bootstrap, playable_target=None,
        submitted_intent=_submitted_turn_intent(request, world_id="world:one"),
        existing_turn=None, budget=budget, trace=trace,
        admission_span_id=admission_span_id,
    )
    assert adapter.authorize(view) is True
    adapter_trace_names = {span["name"] for span in trace.spans}
    assert {"runtime_to_admission", "durable_turn_accept", "durable_turn_claim"} <= adapter_trace_names
    assert all(span["duration_ms"] >= 0 for span in trace.spans)
    assert "PRIVATE" not in json.dumps(trace.spans)
    user_content = json.loads(view["payloadJson"])["input"][1]["content"]
    assert json.loads(user_content.split("\n", 1)[1])[
        "committed_plan_markdown"
    ] == plan_markdown
    assert fake.accepted_count == 1
    assert fake.authorize_count == 1
    assert adapter.record_lifecycle({"transition": "sdk_entered"}) is True
    assert adapter.record_lifecycle({"transition": "response_received"}) is True
    assert adapter.fence is not None
    def unavailable_graph(_world: str) -> Any:
        raise RuntimeError("private Graph admission failure")

    with monkeypatch.context() as graph_down:
        graph_down.setattr(
            "apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config",
            unavailable_graph,
        )
        normalized_failure = adapter.broker_graph_operation({
            "toolName": "expand_graph_retrieval",
            "arguments": {
                "schema": "dmb_expand_graph_retrieval_request_v1",
                "retrievalSessionId": session.id, "operation": "search",
            },
        })
    assert json.loads(normalized_failure["resultJson"])["code"] == "graph_operation_unavailable"
    assert json.loads(normalized_failure["resultJson"])["statusCode"] == 503
    assert adapter.failure is not None and adapter.failure.code == "graph_operation_indeterminate"
    assert (
        "plan_graph_parent_failure stage=native_retrieval "
        "error_code=unexpected_error"
    ) in caplog.text
    assert "private Graph admission failure" not in caplog.text
    from apps.live_control_server.services.hermes_graph_agent import _GraphOperationReservation

    reservation = _GraphOperationReservation(
        8, lambda _name, _args: (normalized_failure["resultJson"], None),
    )
    reservation("expand_graph_retrieval", {})
    assert reservation.indeterminate is True
    adapter.failure = None
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
    assert completion.answer_context_status == "plan_only_graph_unused"
    assert bindings == {}
    assert answer == "The keeper waits."
    for model_status in (
        "plan_only_graph_unused", "graph_grounded", "graph_grounded_partial",
    ):
        mislabeled_plan_answer = json.loads(typed_answer)
        mislabeled_plan_answer["answer_context_status"] = model_status
        derived, derived_bindings, _ = service_module._parse_policy_completion(
            json.dumps(mislabeled_plan_answer), turn,
            adapter.producing_provider_attempt_id,
        )
        assert derived.answer_context_status == "plan_only_graph_unused"
        assert derived_bindings == {}

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
    assert (malformed.value.stage, malformed.value.reason) == (
        "typed", "citation_shape",
    )

    for rejected_text, expected in (
        ('PRIVATE_INVALID_JSON {', ("json", "invalid_json")),
        (json.dumps({"answer_segments": []}), ("shape", "top_level_shape")),
        (json.dumps({
            "answer_context_status": "plan_only_insufficient_evidence",
            "answer_segments": ["PRIVATE_NOT_AN_OBJECT"], "citation_map": None,
        }), ("shape", "segment_shape")),
        (json.dumps({
            "answer_context_status": "plan_only_insufficient_evidence",
            "answer_segments": [
                {"kind": "plan_claim", "text": "Plan fact."},
                "PRIVATE_LATER_NOT_AN_OBJECT",
            ],
            "citation_map": None,
        }), ("shape", "segment_shape")),
        (json.dumps({
            "answer_context_status": "graph_grounded",
            "answer_segments": [
                {"kind": "graph_claim", "claim_id": "claim:one", "text": "Graph fact.",
                 "target_kind": "relationship", "target_id": "rel:one",
                 "graph_revision": "graph-revision-3", "evidence_ref_ids": ["ev:one"]},
                "PRIVATE_LATER_NOT_AN_OBJECT",
            ],
            "citation_map": None,
        }), ("shape", "segment_shape")),
        (json.dumps({
            "answer_context_status": "plan_only_insufficient_evidence",
            "answer_segments": [{"kind": "plan_claim", "text": "PRIVATE_EXTRA_FIELD", "extra": 1}],
            "citation_map": None,
        }), ("typed", "segment_schema")),
        (json.dumps({
            "answer_context_status": "plan_only_insufficient_evidence",
            "answer_segments": [{"kind": "plan_claim", "text": "Plan fact."}],
            "citation_map": {"entries": "PRIVATE_BAD_ENTRIES"},
        }), ("typed", "citation_schema")),
    ):
        with pytest.raises(AgentTurnServiceError) as rejected:
            service_module._parse_policy_completion(
                rejected_text, turn, adapter.producing_provider_attempt_id,
            )
        assert rejected.value.code == "answer_validation_failed"
        assert (rejected.value.stage, rejected.value.reason) == expected
        assert "PRIVATE_" not in str(rejected.value)

    with pytest.raises(AgentTurnServiceError) as missing_attempt:
        service_module._parse_policy_completion(typed_answer, turn, uuid4())
    assert (missing_attempt.value.stage, missing_attempt.value.reason) == (
        "evidence", "producing_attempt_missing",
    )

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
    limited_execution = turn.graph_context_execution.model_copy(update={
        "policy": turn.graph_context_execution.policy.model_copy(update={
            "max_graph_operations": 1,
        }),
    })
    with adapter.fence.renewer._lock:
        adapter.fence.renewer._turn = turn.model_copy(update={
            "graph_context_execution": limited_execution,
        })
    exhausted_graph = adapter.broker_graph_operation({
        "toolName": "expand_graph_retrieval", "arguments": {},
    })
    assert json.loads(exhausted_graph["resultJson"])["code"] == "graph_operation_over_budget"
    with adapter.fence.renewer._lock:
        adapter.fence.renewer._turn = turn
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

    # A fresh turn carries the valid two-attempt expansion through final admission.
    fake = FakeExecutionPort()
    adapter = service_module._PolicyExecutionAdapter(
        service=fake, request=request, world_id="world:one", work=work,
        bootstrap=bootstrap, playable_target=None,
        submitted_intent=_submitted_turn_intent(request, world_id="world:one"),
        existing_turn=None, budget=budget,
    )
    assert adapter.authorize(view) is True
    assert adapter.record_lifecycle({"transition": "sdk_entered"}) is True
    assert adapter.record_lifecycle({"transition": "response_received"}) is True
    turn, fresh = adapter.fence.append(
        "append_validated_graph_operation", "operation_event", operation_event,
    )
    assert fresh is True
    adapter.operation_payloads[operation_event.event_id] = duplicate_payload
    graph_claim = {
        "kind": "graph_claim", "claim_id": "claim:one", "text": "The keeper waits nearby.",
        "target_kind": "relationship", "target_id": "rel:one",
        "graph_revision": "graph-revision-3", "evidence_ref_ids": ["ev:one"],
    }
    graph_answer = json.dumps({
        "answer_context_status": "graph_grounded",
        "answer_segments": [graph_claim],
        "citation_map": {"entries": [{
            **{key: value for key, value in graph_claim.items() if key not in {"kind", "text"}},
            "source_opened": False,
        }]},
    })
    with pytest.raises(AgentTurnServiceError) as unsupported:
        service_module._parse_policy_completion(
            graph_answer, adapter.fence.turn, adapter.producing_provider_attempt_id,
        )
    assert (unsupported.value.stage, unsupported.value.reason) == (
        "evidence", "producing_envelope_support",
    )

    followup_body = json.loads(payload_json)
    followup_body["input"].extend([
        {"type": "function_call", "call_id": "call-a", "name": "expand_graph_retrieval", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call-a", "output": duplicate_payload},
    ])
    followup_json = json.dumps(followup_body, sort_keys=True, separators=(",", ":"))
    followup_view = {
        **view, "payloadJson": followup_json,
        "payloadSha256": sha256(followup_json.encode()).hexdigest(),
        "payloadUtf8Bytes": len(followup_json.encode()),
    }
    assert adapter.authorize(followup_view) is True
    assert adapter.record_lifecycle({"transition": "sdk_entered"}) is True
    assert adapter.record_lifecycle({"transition": "response_received"}) is True
    final_turn = adapter.fence.turn
    final_attempt = adapter.producing_provider_attempt_id
    assert final_turn is not None and final_attempt is not None
    graph_completion, graph_bindings, graph_text = service_module._parse_policy_completion(
        graph_answer, final_turn, final_attempt,
    )
    assert graph_completion.answer_context_status == "graph_grounded"
    assert graph_bindings == {"claim:one": [operation_event.event_id]}
    assert graph_text == "The keeper waits nearby."
    assert fake.authorize_count == 2
    assert len([event for event in final_turn.graph_context_execution.events if event.kind == "provider_attempt_authorized"]) == 2
    assert final_turn.graph_context_execution.events[-1].kind == "provider_outcome"

    for model_status in (
        "graph_grounded_partial", "plan_only_graph_unused",
        "plan_only_insufficient_evidence",
    ):
        wrong_binding_status = json.loads(graph_answer)
        wrong_binding_status["answer_context_status"] = model_status
        derived, derived_bindings, _ = service_module._parse_policy_completion(
            json.dumps(wrong_binding_status), final_turn, final_attempt,
        )
        assert derived.answer_context_status == "graph_grounded"
        assert derived_bindings == graph_bindings
    plan_only_with_graph_available = json.loads(typed_answer)
    plan_only_with_graph_available["answer_context_status"] = "graph_grounded"
    derived_plan, derived_plan_bindings, _ = service_module._parse_policy_completion(
        json.dumps(plan_only_with_graph_available), final_turn, final_attempt,
    )
    assert derived_plan.answer_context_status == "plan_only_graph_unused"
    assert derived_plan_bindings == {}
    for coverage, truncated in (("incomplete", False), ("complete", True)):
        partial_operation = operation_event.model_copy(update={
            "coverage_status": coverage, "truncated": truncated,
        })
        partial_execution = graph_types.PlanWorldGraphExecutionV1.model_validate({
            **final_turn.graph_context_execution.model_dump(mode="json", by_alias=True),
            "events": [
                (partial_operation if event.event_id == operation_event.event_id else event)
                .model_dump(mode="json", by_alias=True)
                for event in final_turn.graph_context_execution.events
            ],
        })
        partial_turn = final_turn.model_copy(update={
            "graph_context_execution": partial_execution,
        })
        partial_completion, partial_bindings, _ = service_module._parse_policy_completion(
            graph_answer, partial_turn, final_attempt,
        )
        assert partial_completion.answer_context_status == "graph_grounded_partial"
        assert partial_bindings == graph_bindings
    for malformed_label in ("PRIVATE_INVALID_STATUS", None, False, 3):
        malformed_status = json.loads(graph_answer)
        malformed_status["answer_context_status"] = malformed_label
        with pytest.raises(AgentTurnServiceError) as invalid_status:
            service_module._parse_policy_completion(
                json.dumps(malformed_status), final_turn, final_attempt,
            )
        assert (invalid_status.value.stage, invalid_status.value.reason) == (
            "typed", "completion_schema",
        )
        assert "PRIVATE_INVALID_STATUS" not in str(invalid_status.value)
    for unclassified_error in (
        ValueError("PRIVATE_UNCLASSIFIED_BINDING_BODY"),
        graph_types.GraphCompletionValidationError(
            "PRIVATE_UNCLOSED_REASON", "PRIVATE_UNCLASSIFIED_BINDING_BODY",
        ),
    ):
        with monkeypatch.context() as unknown_binding:
            def reject_without_code(*_args: Any) -> None:
                raise unclassified_error

            unknown_binding.setattr(
                graph_types, "validate_execution_completion", reject_without_code,
            )
            with pytest.raises(AgentTurnServiceError) as generic_binding:
                service_module._parse_policy_completion(
                    graph_answer, final_turn, final_attempt,
                )
        assert (generic_binding.value.stage, generic_binding.value.reason) == (
            "binding", "completion_binding",
        )
        assert "PRIVATE_UNCLASSIFIED_BINDING_BODY" not in str(generic_binding.value)
        assert "PRIVATE_UNCLOSED_REASON" not in str(generic_binding.value)
    completed_graph_turn = fake.complete_turn(graph_types.TurnResult(
        world_id=final_turn.world_id,
        conversation_id=final_turn.conversation_id,
        turn_id=final_turn.turn_id,
        expected_revision=final_turn.revision,
        assistant_text=graph_text,
        completion=graph_completion,
        producing_provider_attempt_id=final_attempt,
        claim_graph_event_ids=graph_bindings,
    ))
    assert completed_graph_turn.status == "completed"
    assert completed_graph_turn.graph_context_execution.events[-1].kind == "completion_binding"
    adapter.stop()

    fake = FakeExecutionPort()

    class GuardedRuntime:
        descriptor = AgentRuntimeDescriptor("fake-guarded", "fake", "test", "graph")

        def __init__(self, final_text: str = typed_answer) -> None:
            self.final_text = final_text

        def run_with_provider_authorization(
            self, invocation: Any, authorize: Any, *, request_budget: Any,
            on_graph_operation: Any, on_provider_lifecycle: Any,
            context_read_enabled: bool = False,
        ) -> AgentRuntimeResult:
            assert invocation.run_options.runtime_session_id is None
            assert context_read_enabled is True
            assert callable(on_graph_operation)
            adjusted = dict(view)
            adjusted["model"] = request_budget["model"]
            assert authorize(adjusted) is True
            assert on_provider_lifecycle({"transition": "sdk_entered"}) is True
            assert on_provider_lifecycle({"transition": "response_received"}) is True
            basis.has_divergent_working_copy = True
            return AgentRuntimeResult(
                status="ok", final_text=self.final_text,
                runtime_session_id="synthetic-plan-session",
            )

    class BudgetVetoRuntime:
        descriptor = AgentRuntimeDescriptor("budget-veto", "fake", "test", "graph")

        def __init__(
            self, result: AgentRuntimeResult, *, authorize_first: bool = False,
            reject_at_adapter: bool = False,
            uncertain_final: bool = False,
        ) -> None:
            self.result = result
            self.authorize_first = authorize_first
            self.reject_at_adapter = reject_at_adapter
            self.uncertain_final = uncertain_final

        def run_with_provider_authorization(
            self, _invocation: Any, authorize: Any, *, request_budget: Any,
            on_graph_operation: Any, on_provider_lifecycle: Any,
            context_read_enabled: bool = False,
        ) -> AgentRuntimeResult:
            assert context_read_enabled is True
            assert request_budget["contextLimitTokens"] == 1_050_000
            assert (request_budget["maxProviderAttempts"],
                    request_budget["maxToolCapableAttempts"],
                    request_budget["maxGraphOperations"]) == (None, None, None)
            if self.authorize_first:
                adjusted = dict(view)
                adjusted["model"] = request_budget["model"]
                assert authorize(adjusted) is True
            if self.reject_at_adapter:
                adjusted = dict(view)
                adjusted["model"] = request_budget["model"]
                assert authorize(adjusted) is False
            if self.uncertain_final:
                for sequence in range(4):
                    assert authorize(view) is True
                    assert on_provider_lifecycle({"transition": "sdk_entered"}) is True
                    assert on_provider_lifecycle({
                        "transition": "response_received" if sequence < 3 else "outcome_unknown",
                    }) is True
                fake.before_delivery_ledger = fake.turn.graph_context_execution
            return self.result

    def execute_budget_result(
        result: AgentRuntimeResult, *, authorize_first: bool = False,
        reject_at_adapter: bool = False,
        uncertain_final: bool = False,
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
                uncertain_final=uncertain_final,
            ),
            conversation_service=fake,
        )

    caplog.clear()
    with pytest.raises(AgentTurnServiceError) as veto:
        execute_budget_result(AgentRuntimeResult(
            status="error", error_code="request_budget_exceeded",
            error_message="PRIVATE_PLAN_BODY api_key=sk-secret-shaped",
            observed_model_call_count=0,
            runtime_metadata={"host_phase_spans": [{
                "name": "rung3_plugin_discovery", "status": "PRIVATE_PHASE_STATUS",
            }]},
        ))
    assert veto.value.code == "provider_envelope_over_budget"
    assert veto.value.status_code == 413
    assert veto.value.provider_dispatched is False
    assert "PRIVATE_PLAN_BODY" not in caplog.text
    assert "sk-secret-shaped" not in caplog.text
    assert "phase=none phase_status=none" in caplog.text
    assert "PRIVATE_PHASE_STATUS" not in caplog.text
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

    from application_state.errors import ApplicationStateConflictError

    for failure in (None, "stale revision", "expired claim"):
        fake = FakeExecutionPort()
        if failure is not None:
            fake.fail_error = ApplicationStateConflictError(failure)
        caplog.clear()
        with pytest.raises(AgentTurnServiceError) as failed_delivery:
            execute_budget_result(AgentRuntimeResult(
                status="error", error_code="provider_lifecycle_unavailable",
                error_message="PRIVATE_STREAM_BODY",
                observed_model_call_count=4,
                runtime_metadata={"host_phase_spans": [{
                    "name": "host_result_decode", "status": "ok",
                }], "terminal_failure": {
                    "phase": "provider_lifecycle",
                    "reason": "provider_transport_ambiguous",
                    "transition": "outcome_unknown",
                    "acknowledged": True,
                    "transportExceptionClass": "ConnectError",
                }},
            ), uncertain_final=True)
        assert failed_delivery.value.code == (
            "plan_context_delivery_failure" if failure is None else "turn_persistence_indeterminate"
        )
        assert fake.accepted_count == 1 and fake.authorize_count == 4
        assert fake.fail_count == 1
        assert fake.turn is not None
        assert fake.turn.status == ("interrupted" if failure is None else "running")
        assert fake.turn.graph_context_execution == fake.before_delivery_ledger
        outcomes = [e.outcome for e in fake.turn.graph_context_execution.events
                    if e.kind == "provider_outcome"]
        assert outcomes == ["sdk_entered", "response_received"] * 3 + [
            "sdk_entered", "outcome_unknown",
        ]
        assert fake.turn.assistant_text is None and fake.turn.completion is None
        if failure is None:
            assert fake.turn.failure_code == "provider_outcome_unknown"
            history = project_plan_turn_context(fake.turn, delivery_replay=False)
            assert history.completion is None
            assert history.execution.authorization_state == "outcome_unknown"
            assert history.execution.claimability == "blocked_unknown_or_sent"
            assert history.execution.automatic_redispatch is False
        assert (
            "phase=provider_lifecycle phase_status=error "
            "terminal_reason=provider_transport_ambiguous "
            "lifecycle_transition=outcome_unknown "
            "lifecycle_acknowledged=true transport_exception_class=ConnectError"
        ) in caplog.text
        assert "host_result_decode" not in caplog.text
        assert "PRIVATE_STREAM_BODY" not in caplog.text

    fake = FakeExecutionPort()

    pointer_store = HermesSessionPointerStore(
        Path("/tmp") / f"plan-policy-{uuid4()}"
    )
    pointer_store.upsert_structured_after_turn(
        owner_kind="world", owner_id="world:one",
        work_kind="plan", work_id="plan:one",
        agent_thread_id=request.client_thread_id,
        hermes_session_id="legacy-unrelated-plan-session",
    )

    response = execute_agent_turn(
        request,
        root=Path("/tmp"),
        pointer_store=pointer_store,
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
    assert response.primary_work.revision_used == 7
    assert response.primary_work.content_basis is not None
    assert response.primary_work.content_basis.has_divergent_working_copy is False
    assert basis.has_divergent_working_copy is True
    assert response.plan_context.completion is not None
    assert response.answer.text == "The keeper waits."
    assert fake.turn is not None and fake.turn.status == "completed"
    assert fake.fail_count == 0

    for private_final_text in (
        "PRIVATE_PROVIDER_FINAL_BODY {",
        chr(0xD800) + " PRIVATE_PROVIDER_FINAL_BODY {",
    ):
        fake = FakeExecutionPort()
        failed_codes: list[str] = []

        def record_failure(failure: Any, *, interrupted: bool = False) -> Turn:
            assert interrupted is False
            failed_codes.append(failure.failure_code)
            assert fake.turn is not None
            return fake.turn

        fake.fail_turn = record_failure
        caplog.clear()
        with pytest.raises(AgentTurnServiceError) as rejected_service_answer:
            execute_agent_turn(
                request, root=Path("/tmp"),
                pointer_store=HermesSessionPointerStore(Path("/tmp") / f"plan-rejected-{uuid4()}"),
                owner_resolver=lambda _request: {
                    "kind": "world", "id": "world:one", "name": "World One",
                },
                work_resolver=lambda _request, _owner: work,
                graph_resolver=lambda *_args: pytest.fail("generic Graph resolver was used"),
                plan_graph_resolver=lambda *_args: bootstrap,
                runtime=GuardedRuntime(private_final_text),
                conversation_service=fake,
            )
        assert rejected_service_answer.value.code == "answer_validation_failed"
        assert failed_codes == ["answer_validation_failed"]
        assert fake.authorize_count == 1
        assert fake.turn is not None and fake.turn.completion is None
        diagnostic = next(
            record.getMessage() for record in caplog.records
            if record.getMessage().startswith("plan_graph_answer_validation_failed ")
        )
        encoded = private_final_text.encode("utf-8", "surrogatepass")
        assert "stage=json reason=invalid_json" in diagnostic
        assert f"request_turn_sha256={sha256(request.turn_id.encode()).hexdigest()}" in diagnostic
        assert f"idempotency_key={fake.turn.idempotency_key}" in diagnostic
        assert f"durable_turn_id={fake.turn.turn_id}" in diagnostic
        assert f"final_text_sha256={sha256(encoded).hexdigest()}" in diagnostic
        assert f"final_text_utf8_bytes={len(encoded)}" in diagnostic
        assert "producing_provider_attempt_id=" in diagnostic
        assert "PRIVATE_PROVIDER_FINAL_BODY" not in diagnostic
        assert "Expecting property name" not in diagnostic
        assert chr(0xD800) not in diagnostic

    fake = FakeExecutionPort()
    private_binding_answer = json.dumps({
        "answer_context_status": "plan_only_graph_unused",
        "answer_segments": [{
            "kind": "plan_claim", "text": "PRIVATE_PROVIDER_FINAL_BODY",
        }],
        "citation_map": None,
    })
    caplog.clear()
    derived_response = execute_agent_turn(
        request, root=Path("/tmp"),
        pointer_store=HermesSessionPointerStore(
            Path("/tmp") / f"plan-binding-derived-{uuid4()}"
        ),
        owner_resolver=lambda _request: {
            "kind": "world", "id": "world:one", "name": "World One",
        },
        work_resolver=lambda _request, _owner: work,
        graph_resolver=lambda *_args: pytest.fail("generic Graph resolver was used"),
        plan_graph_resolver=lambda *_args: bootstrap,
        runtime=GuardedRuntime(private_binding_answer),
        conversation_service=fake,
    )
    assert derived_response.plan_context.completion.answer_context_status == (
        "plan_only_graph_unused"
    )
    assert fake.turn is not None and fake.turn.status == "completed"
    assert fake.turn.completion.answer_context_status == "plan_only_graph_unused"
    assert fake.turn.assistant_text == "PRIVATE_PROVIDER_FINAL_BODY"
    execution_events = fake.turn.graph_context_execution.events
    assert execution_events[-1].kind == "completion_binding"
    assert execution_events[-1].provider_attempt_id in {
        event.provider_attempt_id for event in execution_events
        if event.kind in {
            "provider_attempt_authorized", "provider_attempt_authorized_v2",
            "provider_attempt_authorized_v3",
        }
    }
    assert "plan_graph_answer_validation_failed" not in caplog.text
    assert "PRIVATE_PROVIDER_FINAL_BODY" not in caplog.text

    for uncertain_last, fail_finalization in ((False, False), (True, False), (False, True)):
        fake = FakeExecutionPort()
        terminal_failures: list[tuple[str, int]] = []

        def record_guard_failure(failure: Any, *, interrupted: bool = False) -> Turn:
            assert interrupted is uncertain_last
            assert fake.turn is not None
            assert failure.expected_revision == fake.turn.revision
            terminal_failures.append((failure.failure_code, failure.expected_revision))
            if fail_finalization:
                raise ApplicationStateConflictError("claim fence changed")
            fake.turn = fake.turn.model_copy(update={
                "status": "interrupted" if interrupted else "failed",
                "failure_code": failure.failure_code,
                "revision": fake.turn.revision + 1, "claim_expires_at": None,
            })
            return fake.turn

        fake.fail_turn = record_guard_failure

        class ExhaustedRuntime:
            descriptor = AgentRuntimeDescriptor("guard-exhausted", "fake", "test", "graph")

            def run_with_provider_authorization(
                self, _invocation: Any, authorize: Any, *, request_budget: Any,
                on_graph_operation: Any, on_provider_lifecycle: Any,
                context_read_enabled: bool = False,
            ) -> AgentRuntimeResult:
                assert context_read_enabled is True
                adjusted = {**view, "model": request_budget["model"]}
                for index in range(4):
                    assert authorize(adjusted) is True
                    assert on_provider_lifecycle({"transition": "sdk_entered"}) is True
                    if index < 3 or not uncertain_last:
                        assert on_provider_lifecycle({"transition": "response_received"}) is True
                assert authorize(adjusted) is False
                return AgentRuntimeResult(
                    status="error", error_code="provider_authorization_denied",
                )

        original_stop = service_module._ClaimFence.stop

        def stop_after_renewal(fence: Any) -> tuple[Turn, Exception | None]:
            turn, error = original_stop(fence)
            if not uncertain_last:
                turn = turn.model_copy(update={"revision": turn.revision + 1})
                fake.turn = turn
            return turn, error

        with monkeypatch.context() as moving_fence:
            moving_fence.setattr(service_module._ClaimFence, "stop", stop_after_renewal)
            with pytest.raises(AgentTurnServiceError) as exhausted:
                execute_agent_turn(
                    request, root=Path("/tmp"),
                    pointer_store=HermesSessionPointerStore(Path("/tmp") / f"plan-exhausted-{uuid4()}"),
                    owner_resolver=lambda _request: {
                        "kind": "world", "id": "world:one", "name": "World One",
                    },
                    work_resolver=lambda _request, _owner: work,
                    graph_resolver=lambda *_args: pytest.fail("generic Graph resolver was used"),
                    plan_graph_resolver=lambda *_args: bootstrap,
                    runtime=ExhaustedRuntime(), conversation_service=fake,
                )
        assert exhausted.value.code == (
            "turn_persistence_indeterminate" if fail_finalization
            else "plan_context_delivery_failure"
        )
        assert exhausted.value.status_code == 503
        assert fake.authorize_count == 4
        assert fake.turn is not None
        assert len(fake.turn.graph_context_execution.events) == (11 if uncertain_last else 12)
        if uncertain_last:
            assert terminal_failures == [("plan_context_delivery_failure", 13)]
            assert fake.turn.status == "interrupted"
        else:
            assert terminal_failures == [("provider_attempt_limit_exhausted", 15)]
            assert fake.turn.status == ("running" if fail_finalization else "failed")


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
    trace_spans = trace["spans"]
    trace_names = {span["name"] for span in trace_spans}
    assert {
        "turn_owner_resolution", "committed_plan_resolution", "context_assembly",
        "runtime_creation",
    } <= trace_names
    assert all(span["duration_ms"] >= 0 for span in trace_spans)
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


def test_selected_multi_hop_graph_read_and_source_scope_remain_separate(tmp_path,monkeypatch):
    import json
    from tests.test_agent_turn_route import _selected_consumer_context
    from tests.test_world_graph_retrieval_contract import _selected_native_fixture
    from apps.live_control_server.services import agent_turn_service as owner
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
    from graph_memory.retrieval.models import WorldGraphNeighborhoodRequest
    from graph_memory.interaction.session import SourceAnchorState
    body,work,bootstrap,receipt,execution,_ = _selected_consumer_context(tmp_path,monkeypatch,neighbor=True)
    services,request,revision = _selected_native_fixture(claims=True,neighbor=True)
    neighborhood = direct.get_neighborhood_direct(services,WorldGraphNeighborhoodRequest.model_validate({
        'schema':'dmb_world_graph_neighborhood_request_v1','worldId':request.world_id,'campaignId':'','scopeMode':'world','revisionPin':revision,'seedNodeIds':['obj:tavern'],'maxDepth':2}))
    assert 'obj:noise:0' in {node.node_id for node in neighborhood.nodes}
    pool={pin['anchor_id'] for pin in bootstrap.source_scope_anchors}
    outside=next(anchor for anchor in neighborhood.source_anchors if anchor.anchor_id not in pool and anchor.readable)
    session=bootstrap.retrieval_session
    session.source_anchors.append(SourceAnchorState(anchor_id=outside.anchor_id,readable=True,opened=False,locator_kind=outside.locator_kind))
    monkeypatch.setattr('graph_memory.interaction.session_store.get_session',lambda _id:session)
    calls=[]
    pin=bootstrap.source_scope_anchors[0]
    def read(args,*,receipt_version):
        calls.append(args)
        return {'schema':'dmb_internal_read_graph_source_batch_v2','retrievalSessionId':session.id,'reads':[{
            'sourceReadId':'source-read:inside','result':{'schema':'dmb_world_graph_source_anchor_read_v1','outcome':'enough','anchorId':pin['anchor_id'],
                'content':'fixture passage','contentSha256':'a'*64,'evidenceRefId':pin['evidence_ref_id'],'sourceArtifactId':pin['source_artifact_id']},
            'receipt':{'source_read_id':'source-read:inside','retrieval_session_id':session.id,'graph_revision':revision,**pin,
                'read_content_sha256':'a'*64,'outcome':'enough','truncated':False}}]}
    monkeypatch.setattr('graph_memory.interaction.expansion_executor.execute_read_graph_source',read)
    class Fence:
        def __init__(self):
            self.turn=_policy_turn(status='running',completion_present=False).model_copy(update={'graph_context_receipt':receipt,'graph_context_execution':execution})
        def append(self,_method,_key,event):
            self.turn=self.turn.model_copy(update={'graph_context_execution':self.turn.graph_context_execution.model_copy(update={'events':[*self.turn.graph_context_execution.events,event]})})
            return self.turn,True
    adapter=owner._PolicyExecutionAdapter(service=object(),request=body,world_id=work.world_id,work=work,bootstrap=bootstrap,
        playable_target=None,submitted_intent=None,existing_turn=None,budget={})
    adapter.fence=Fence()
    adapter.last_provider_attempt_id=__import__('uuid').uuid4()
    denied=adapter.broker_source_read({'toolName':'read_graph_source','arguments':{'retrievalSessionId':session.id,'anchorIds':[outside.anchor_id]}})
    assert json.loads(denied['resultJson'])['code']=='source_anchor_not_admitted' and calls==[]
    inside=adapter.broker_source_read({'toolName':'read_graph_source','arguments':{'retrievalSessionId':session.id,'anchorIds':[pin['anchor_id']]}})
    assert len(calls)==1, inside
    assert json.loads(inside['resultJson'])['content']=='fixture passage'
    assert execution.policy.max_graph_operations==8 and execution.policy.max_source_read_chars==96000
    assert not hasattr(execution.policy,"max_source_read_calls")
    legacy=direct.list_source_anchor_index_direct_v2(services,request,revision_id=revision)
    assert legacy.status=='overflow'
    small,small_request,small_revision=_selected_native_fixture(unrelated=2,claims=True,neighbor=True)
    old_pool=direct.list_source_anchor_index_direct_v2(small,small_request,revision_id=small_revision)
    old_neighbors=direct.get_neighborhood_direct(small,WorldGraphNeighborhoodRequest.model_validate({
        'schema':'dmb_world_graph_neighborhood_request_v1','worldId':small_request.world_id,'campaignId':'','scopeMode':'world','revisionPin':small_revision,'seedNodeIds':['obj:tavern'],'maxDepth':2}))
    assert {anchor.anchor_id for anchor in old_neighbors.source_anchors if anchor.readable}.issubset({item.anchor_id for item in old_pool.source_pins})


def test_mounted_current_related_recap_route_pg_fake_provider_and_saved_history(
    application_state_dsn,
    tmp_path,
    monkeypatch,
):
    """Actual authenticated route/broker/SOURCE/APP; only authority and provider are synthetic."""
    import asyncio
    from types import SimpleNamespace
    import httpx
    import fastapi.routing as routing
    from fastapi import FastAPI
    from application_state.agent_conversation import AgentConversationService
    from apps.live_control_server.routes import agent as route
    from apps.live_control_server.services import agent_turn_service as parent
    from apps.live_control_server.services import world_graph_retrieval as source
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from dungeonmind.application.world_graph_retrieval import (
        RecapContextSectionSelectorV2,
        RecapSourceContextV2,
        SourceContextIndexResult,
        SourceContextResolution,
    )
    from graph_memory.interaction.session import (
        GraphRetrievalSession,
        SessionSnapshot,
        CoverageState,
        SourceAnchorState,
    )
    from graph_memory.interaction.authority_classifier import (
        claims_from_retrieval_result,
    )
    from apps.live_control_server.services.agent_runtime import AgentWorldScope

    token = "synthetic-current-context-token-" + "x" * 32
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)

    async def inline(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr(routing, "run_in_threadpool", inline)
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference",
        lambda **kwargs: ("openai-api", "gpt-6-luna", "https://api.openai.com/v1"),
    )
    world, native, revision = (
        "current-context-world",
        "synthetic-native",
        "rev:current-context",
    )
    plan = "# Plan\nFollow the gate.\n"
    basis = AgentTurnContentBasis(
        world_id=world,
        document_id="synthetic-plan",
        object_revision=1,
        work_revision_id=str(uuid4()),
        revision_n=1,
        content_sha256=sha256(plan.encode()).hexdigest(),
        committed_status="committed",
        has_divergent_working_copy=False,
    )
    work = AgentTurnResolvedWork(
        kind="plan",
        object_id=basis.document_id,
        revision=1,
        changed_since_expected=False,
        owner_kind="world",
        owner_id=world,
        world_id=world,
        content_basis=basis,
        plan_markdown=plan,
    )
    body = _request(
        surface={"surface_id": "plan", "instance_id": "synthetic-plan-pane"},
        owner_scope={"kind": "world", "world_id": world},
        client_work_state="saved_clean",
        primary_work={
            "kind": "plan",
            "object_id": basis.document_id,
            "expected_revision": 1,
            "expected_revision_n": 1,
            "expected_content_sha256": basis.content_sha256,
        },
        turn_id=str(uuid4()),
        plan_context_policy={"policy": "auto_plan_world"},
        message="Summarize the entire prior recap while preserving its context boundary.",
    )
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id=native,
            campaign_id="",
            focus={"kind": "none"},
            admissibility="gm",
            revision_id=revision,
            is_head=True,
            scope_mode="world",
        ),
        question=body.message,
        coverage=CoverageState(state="empty"),
        claims=claims_from_retrieval_result(
            {
                "relationships": [
                    {
                        "edgeId": "rel:gate",
                        "sourceNodeId": "node:keeper",
                        "targetNodeId": "node:gate",
                        "predicate": "guards",
                        "evidenceRefIds": ["ev:gate"],
                    }
                ],
                "sourceAnchors": [
                    {
                        "anchorId": "synthetic-anchor",
                        "revisionId": revision,
                        "evidenceRefId": "ev:gate",
                        "readable": False,
                        "supportingGraphObjectIds": [],
                    }
                ],
            },
            revision_id=revision,
        ),
        source_anchors=[
            SourceAnchorState(anchor_id="synthetic-anchor", readable=False)
        ],
    )
    bootstrap = parent.AgentPlanWorldGraphBootstrap(
        graph_envelope={
            "revision_id": revision,
            "world_id": native,
            "scope_mode": "world",
        },
        world_scope=AgentWorldScope(
            world_id=native,
            campaign_id="",
            focus={"kind": "none"},
            admissibility="gm",
            revision_id=revision,
            scope_mode="world",
        ),
        retrieval_session=session,
        binding_version=1,
        source_root_relpath="corpus",
        candidate_assertion_ids=(),
        candidate_relationship_ids=("rel:gate",),
        candidate_evidence_ref_ids=("ev:gate",),
        evidence_by_anchor_id={"synthetic-anchor": "ev:gate"},
    )
    raw = b"## Session 22:\n## Major Beats:\nExcluded prelude.\n**Recap**:\nFirst synthetic beat.\nSecond synthetic beat.\n## Afterword\nExcluded tail.\n"
    (tmp_path / "recap.md").write_bytes(raw)
    selector = RecapContextSectionSelectorV2(
        expected_session_id="session-22",
        canonical_heading="# Session 22 Recap",
        legacy_session_heading="## Session 22:",
        legacy_recap_marker="**Recap**:",
    )
    descriptor = RecapSourceContextV2(
        context_anchor_id="dm-context-anchor:v2:synthetic-route",
        world_id=native,
        campaign_id="synthetic-campaign",
        graph_revision_id=revision,
        source_artifact_id="synthetic-artifact",
        source_revision_id="sha256:" + sha256(raw).hexdigest(),
        source_uri="repo://recap.md",
        content_sha256=sha256(raw).hexdigest(),
        section_selector=selector,
    )

    def snapshot(projection):
        return SimpleNamespace(
            world_id=native,
            campaign_id=None,
            scope_mode=projection.scope_mode,
            admissibility=projection.admissibility,
            focus=projection.focus,
            revision_id=revision,
            head_revision_id=revision,
            is_head=True,
        )

    class Retrieval:
        def get_evidence(self, projection, *, target, max_anchors):
            assert (target.kind, target.target_id) == ("relationship", "rel:gate")
            return SimpleNamespace(
                found=True,
                target=target,
                snapshot=snapshot(projection),
                coverage=SimpleNamespace(
                    truncated_fields=(), gap_codes=(), missing_ids=()
                ),
                anchors=(
                    SimpleNamespace(
                        evidence_ref_id="ev:gate",
                        source_artifact_id=descriptor.source_artifact_id,
                        source_revision_id=descriptor.source_revision_id,
                        can_open_source=False,
                    ),
                ),
            )

        def list_source_context_index(self, request):
            assert request.selector_policy == "markdown-session-recap-v2"
            return SourceContextIndexResult(
                snapshot=snapshot(request.projection),
                status="complete",
                eligible_count=1,
                max_entries=512,
                entries=(descriptor,),
            )

        def resolve_source_context(
            self, projection, *, context_anchor_id, allow_selector_v2=False
        ):
            assert (
                allow_selector_v2 and context_anchor_id == descriptor.context_anchor_id
            )
            return SourceContextResolution(
                snapshot=snapshot(projection),
                found=True,
                context_anchor_id=context_anchor_id,
                context=descriptor,
            )

    monkeypatch.setattr(
        direct,
        "direct_services_from_config",
        lambda _: SimpleNamespace(
            retrieval=Retrieval(),
            binding=SimpleNamespace(legacy_buddy_revision_id=None),
        ),
    )
    monkeypatch.setattr(source, "_require_mounted_native_read", lambda _: None)
    monkeypatch.setattr(source, "_resolved_repo_root", lambda **kwargs: tmp_path)
    monkeypatch.setattr(route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(
        route,
        "_owner_resolver",
        lambda _: {"kind": "world", "id": world, "name": "Synthetic World"},
    )
    monkeypatch.setattr(route, "_work_resolver", lambda *_: work)
    monkeypatch.setattr(
        route, "_plan_context_resolver", lambda *args, **kwargs: bootstrap
    )
    packet = session.project_for_hermes()
    initial = {
        "candidates": packet["candidates"][:8],
        "claimLedger": packet["claim_ledger"][:24],
        "intentHint": packet["intent_hint"],
        "availableExpansions": packet["available_expansions"],
    }
    provider_calls = []

    class FakeProvider:
        descriptor = AgentRuntimeDescriptor(
            "fake-current-context", "fake", "test", "graph"
        )

        def run_with_provider_authorization(
            self,
            invocation,
            authorize,
            *,
            request_budget,
            on_graph_operation,
            on_provider_lifecycle,
            context_read_enabled=False,
        ):
            assert context_read_enabled
            payload = {
                "input": [
                    {
                        "role": "system",
                        "content": "Turn capability policy (runtime-enforced; also required on tool calls):\n"
                        + json.dumps({"initialClaimPacket": initial}),
                    },
                    {
                        "role": "user",
                        "content": parent._plan_message(
                            body.message, plan, content_basis=basis
                        ),
                    },
                ],
                "tools": [],
            }

            def send():
                encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
                assert authorize(
                    {
                        "provider": "openai-api",
                        "model": request_budget["model"],
                        "apiMode": "codex_responses",
                        "payloadJson": encoded,
                        "payloadSha256": sha256(encoded.encode()).hexdigest(),
                        "payloadUtf8Bytes": len(encoded.encode()),
                    }
                ), str(authorize.__self__.failure)
                assert on_provider_lifecycle({"transition": "sdk_entered"})
                assert on_provider_lifecycle({"transition": "response_received"})
                provider_calls.append(encoded)

            send()
            parts = []
            continuation = None
            for i in range(8):
                response = on_graph_operation(
                    {
                        "toolName": "read_related_recap_context",
                        "arguments": {
                            "schema": "dmb_read_related_recap_context_request_v2",
                            "retrievalSessionId": session.id,
                            "targetKind": "relationship",
                            "targetId": "rel:gate",
                            "evidenceRefIds": ["ev:gate"],
                            "contextAnchorId": descriptor.context_anchor_id,
                            "maxChars": 24,
                            "continuation": continuation,
                        },
                    }
                )
                page = json.loads(response["resultJson"])
                assert page["schema"] == "dmb_related_recap_context_read_v2", page
                parts.append(page["content"])
                payload["input"].extend(
                    [
                        {
                            "type": "function_call",
                            "call_id": f"context-{i}",
                            "name": "read_related_recap_context",
                            "arguments": "{}",
                        },
                        {
                            "type": "function_call_output",
                            "call_id": f"context-{i}",
                            "output": response["resultJson"],
                        },
                    ]
                )
                continuation = page["nextContinuation"]
                if continuation is None:
                    break
            assert "".join(parts) == "First synthetic beat.\nSecond synthetic beat.\n"
            send()
            claim = {
                "kind": "graph_claim",
                "claim_id": "rel:gate",
                "text": "The keeper guards the gate.",
                "target_kind": "relationship",
                "target_id": "rel:gate",
                "graph_revision": revision,
                "evidence_ref_ids": ["ev:gate"],
            }
            answer = {
                "answer_context_status": "graph_grounded",
                "answer_segments": [claim],
                "citation_map": {
                    "entries": [
                        {
                            **{
                                key: value
                                for key, value in claim.items()
                                if key not in {"kind", "text"}
                            },
                            "source_opened": False,
                        }
                    ]
                },
            }
            return AgentRuntimeResult(
                status="ok",
                final_text=json.dumps(answer),
                runtime_session_id="synthetic-session",
            )

    app = FastAPI()
    app.state.agent_turn_runtime = FakeProvider()
    app.state.agent_conversation_service = AgentConversationService()
    app.include_router(route.router, prefix="/api/live")

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            denied = await client.post(
                "/api/live/agent/turn", json=body.model_dump(mode="json", by_alias=True)
            )
            assert denied.status_code == 401 and provider_calls == []
            result = await client.post(
                "/api/live/agent/turn",
                headers={"Authorization": "Bearer " + token},
                json=body.model_dump(mode="json", by_alias=True),
            )
            assert result.status_code == 200, result.text
            return result.json()

    delivered = asyncio.run(exercise())
    assert len(provider_calls) == 2
    service = AgentConversationService()
    conversation = service.get_active_conversation(world)
    saved = service.list_turns(world, conversation.conversation_id)[0]
    assert saved.status == "completed" and saved.user_text == body.message
    events = saved.graph_context_execution.events
    reads = [e for e in events if e.kind == "validated_related_recap_context_v2"]
    assert len(reads) == 2 and all(
        e.selected_form == "legacy_h2"
        and e.session_heading_line == 1
        and e.recap_marker_line == 4
        for e in reads
    )
    assert events[-5].kind == "related_recap_context_provider_inclusion_v2"
    assert saved.completion.citation_map.entries[0].source_opened is False
    assert saved.completion.citation_map.entries[0].source_read_ids == []
    before = saved.model_dump_json()
    rebuilt = project_plan_turn_context(saved, delivery_replay=True)
    assert rebuilt.schema_ == "dmb_agent_plan_world_graph_context_response_v2"
    target = next(
        t for t in rebuilt.source_open_targets if t.kind == "related_recap_context"
    )
    assert (
        target.context_anchor_id == descriptor.context_anchor_id
        and target.legacy_recap_marker == "**Recap**:"
    )
    assert (
        service.list_turns(world, conversation.conversation_id)[0].model_dump_json()
        == before
    )
    assert len(provider_calls) == 2 and (tmp_path / "recap.md").read_bytes() == raw
    import os
    import subprocess
    import sys

    child = subprocess.check_output(
        [
            sys.executable,
            "-c",
            """
import json, sys
from application_state.agent_conversation import AgentConversationService
from apps.live_control_server.services.agent_turn_service import project_plan_turn_context
from uuid import UUID
turn = AgentConversationService().list_turns(sys.argv[1], UUID(sys.argv[2]))[0]
view = project_plan_turn_context(turn, delivery_replay=True)
print(json.dumps({"turn":turn.model_dump(mode="json",by_alias=True), "view_schema":view.schema_}))
""",
            world,
            str(conversation.conversation_id),
        ],
        env=os.environ.copy(),
        text=True,
    )
    readback = json.loads(child)
    assert readback["turn"] == saved.model_dump(mode="json", by_alias=True)
    assert readback["view_schema"] == "dmb_agent_plan_world_graph_context_response_v2"
    assert (
        delivered["plan_context"]["source_open_targets"]
        == rebuilt.model_dump(mode="json", by_alias=True)["source_open_targets"]
    )


@pytest.mark.parametrize("operation", ["search", "object", "neighborhood", "support"])
def test_mounted_v3_traversal_source_route_real_pg_and_history(
    application_state_dsn,
    tmp_path,
    monkeypatch, operation,
):
    """Actual authenticated route/broker/SOURCE/APP; only authority and provider are synthetic."""
    import asyncio
    import httpx
    import fastapi.routing as routing
    from fastapi import FastAPI
    from application_state.agent_conversation import AgentConversationService
    from apps.live_control_server.routes import agent as route
    from apps.live_control_server.services import agent_turn_service as parent
    from apps.live_control_server.services import world_graph_retrieval as source
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from graph_memory.interaction.session import (
        GraphRetrievalSession,
        SessionSnapshot,
        CoverageState,
    )
    from apps.live_control_server.services.agent_runtime import AgentWorldScope

    token = "synthetic-current-context-token-" + "x" * 32
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)

    async def inline(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr(routing, "run_in_threadpool", inline)
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference",
        lambda **kwargs: ("openai-api", "gpt-6-luna", "https://api.openai.com/v1"),
    )
    from tests._cutover_direct_dungeonmind_read_helpers import (
        WORLD_ID, NOW, ANCHOR_CONTENT, _payload, _seed_sources, _receipt, _FakeBundle,
    )
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.memory import InMemoryWorldGraphRepository
    graphs = InMemoryWorldGraphRepository()
    payload = _payload()
    payload['objects'][0]['properties'] = [{
        'property_term': 'dnd5e:population', 'value': 'bustling',
        'assertion_metadata': {
            **payload['objects'][0]['assertion_metadata'], 'assertion_id': 'asrt:population',
        },
    }]
    published = graphs.publish_revision(PublishRevisionCommand(
        world_id=WORLD_ID, parent_revision_id=None, expected_parent_revision_id=None,
        operation_ids=['op:mounted-synthetic'], graph_schema='dm_union_graph_v6',
        graph_payload=payload, created_at=NOW,
    ))
    services = direct.direct_services_from_bundle(
        _FakeBundle(graphs, _seed_sources(), _receipt(WORLD_ID, published.revision_id)), WORLD_ID,
    )
    world, native, revision = 'mounted-v3-world', WORLD_ID, published.revision_id
    plan = "# Plan\nFollow the gate.\n"
    basis = AgentTurnContentBasis(
        world_id=world,
        document_id="synthetic-plan",
        object_revision=1,
        work_revision_id=str(uuid4()),
        revision_n=1,
        content_sha256=sha256(plan.encode()).hexdigest(),
        committed_status="committed",
        has_divergent_working_copy=False,
    )
    work = AgentTurnResolvedWork(
        kind="plan",
        object_id=basis.document_id,
        revision=1,
        changed_since_expected=False,
        owner_kind="world",
        owner_id=world,
        world_id=world,
        content_basis=basis,
        plan_markdown=plan,
    )
    body = _request(
        surface={"surface_id": "plan", "instance_id": "synthetic-plan-pane"},
        owner_scope={"kind": "world", "world_id": world},
        client_work_state="saved_clean",
        primary_work={
            "kind": "plan",
            "object_id": basis.document_id,
            "expected_revision": 1,
            "expected_revision_n": 1,
            "expected_content_sha256": basis.content_sha256,
        },
        turn_id=str(uuid4()),
        plan_context_policy={"policy": "auto_plan_world"},
        message="Summarize the entire prior recap while preserving its context boundary.",
    )
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id=native, campaign_id='', focus={'kind': 'none'}, admissibility='gm',
            revision_id=revision, is_head=True, scope_mode='world',
        ), question=body.message, coverage=CoverageState(state='empty'),
    )
    # Support returns evidence for an already selected object; its claim remains in the initial packet.
    if operation == 'support':
        from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
        from graph_memory.retrieval.models import WorldGraphObjectRequest
        selected = direct.get_object_direct(services, WorldGraphObjectRequest.model_validate({
            'schema':'dmb_world_graph_object_request_v1', 'worldId':native, 'campaignId':'',
            'scopeMode':'world', 'revisionPin':revision, 'nodeId':'obj:tavern',
        }))
        session.claims = claims_from_retrieval_result(selected.model_dump(mode='json', by_alias=True), revision_id=revision)
    bootstrap = parent.AgentPlanWorldGraphBootstrap(
        graph_envelope={'revision_id': revision, 'world_id': native, 'scope_mode': 'world'},
        world_scope=AgentWorldScope(world_id=native, campaign_id='', focus={'kind':'none'},
            admissibility='gm', revision_id=revision, scope_mode='world'),
        retrieval_session=session, binding_version=1, source_root_relpath='corpus',
        candidate_assertion_ids=("asrt:population",) if operation == "support" else (),
        candidate_relationship_ids=(), candidate_evidence_ref_ids=("ev:tavern",) if operation == "support" else (),
        evidence_by_anchor_id=({anchor.anchor_id:anchor.evidence_ref_id for anchor in selected.source_anchors}
                               if operation == 'support' else {}), source_scope_anchors=(),
    )
    (tmp_path / 'corpus').mkdir()
    (tmp_path / 'corpus/world_lore.md').write_text(ANCHOR_CONTENT)
    core_reads = []
    from graph_memory.interaction import expansion_executor
    core_results = []
    original_execute = expansion_executor.execute_read_graph_source
    def checked_execute(*args, **kwargs):
        result = original_execute(*args, **kwargs)
        core_results.append(result)
        assert result.get('reads') and result['reads'][0].get('receipt'), result
        return result
    monkeypatch.setattr(expansion_executor, 'execute_read_graph_source', checked_execute)
    original_read = direct.read_source_anchors_direct_v2
    def counted_read(*args, **kwargs):
        core_reads.extend(request.anchor_id for request in args[1])
        return original_read(*args, **kwargs)
    monkeypatch.setattr(direct, 'read_source_anchors_direct_v2', counted_read)
    monkeypatch.setattr(direct, 'direct_services_from_config', lambda _: services)
    monkeypatch.setattr(source, "_require_mounted_native_read", lambda _: None)
    monkeypatch.setattr(source, "_resolved_repo_root", lambda **kwargs: tmp_path)
    monkeypatch.setattr(route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(
        route,
        "_owner_resolver",
        lambda _: {"kind": "world", "id": world, "name": "Synthetic World"},
    )
    monkeypatch.setattr(route, "_work_resolver", lambda *_: work)
    monkeypatch.setattr(
        route, "_plan_context_resolver", lambda *args, **kwargs: bootstrap
    )
    provider_calls = []

    class FakeProvider:
        descriptor = AgentRuntimeDescriptor(
            "fake-current-context", "fake", "test", "graph"
        )

        def run_with_provider_authorization(
            self,
            invocation,
            authorize,
            *,
            request_budget,
            on_graph_operation,
            on_provider_lifecycle,
            context_read_enabled=False,
        ):
            assert context_read_enabled
            frozen_packet = authorize.__self__.initial_session_projection
            initial = {
                'candidates': frozen_packet['candidates'][:8],
                'claimLedger': frozen_packet['claim_ledger'][:24],
                'intentHint': frozen_packet['intent_hint'],
                'availableExpansions': frozen_packet['available_expansions'],
            }
            payload = {
                "input": [
                    {
                        "role": "system",
                        "content": "Turn capability policy (runtime-enforced; also required on tool calls):\n"
                        + json.dumps({"initialClaimPacket": initial}),
                    },
                    {
                        "role": "user",
                        "content": parent._plan_message(
                            body.message, plan, content_basis=basis
                        ),
                    },
                ],
                "tools": [],
            }

            def send():
                encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
                assert authorize(
                    {
                        "provider": "openai-api",
                        "model": request_budget["model"],
                        "apiMode": "codex_responses",
                        "payloadJson": encoded,
                        "payloadSha256": sha256(encoded.encode()).hexdigest(),
                        "payloadUtf8Bytes": len(encoded.encode()),
                    }
                ), str(authorize.__self__.failure)
                assert on_provider_lifecycle({"transition": "sdk_entered"})
                assert on_provider_lifecycle({"transition": "response_received"})
                provider_calls.append(encoded)

            send()
            adapter = authorize.__self__
            assert adapter._broker_execution().policy.source_read_scope.admitted_anchors == []
            graph_reply = on_graph_operation({
                'toolName': 'expand_graph_retrieval', 'arguments': {
                    'retrievalSessionId': session.id, 'operation': operation,
                    'queryText': 'The Prancing Tavern',
                    'targets': [{'kind':'node','id':'obj:tavern'}],
                },
            })
            graph_packet = json.loads(graph_reply['resultJson'])
            origin, extension = adapter._broker_execution().events[-2:]
            assert origin.kind == 'validated_graph_operation_v3', graph_packet
            assert extension.kind == 'source_scope_extension_v3'
            assert extension.origin_graph_event_id == origin.event_id
            pin = next(pin for pin in origin.returned_source_pins if pin.evidence_ref_id == 'ev:tavern')
            assert pin in extension.pins
            response = on_graph_operation({'toolName':'read_graph_source', 'arguments': {
                'retrievalSessionId': session.id, 'anchorIds':[pin.anchor_id], 'maxChars':1000,
            }})
            page = json.loads(response['resultJson'])
            assert page.get('content') == ANCHOR_CONTENT.rstrip(), json.dumps({'page':page,'core':core_results})
            for call_id, name, reply in [('graph','expand_graph_retrieval',graph_reply),
                                          ('source','read_graph_source',response)]:
                payload['input'].extend([
                    {'type':'function_call','call_id':call_id,'name':name,'arguments':'{}'},
                    {'type':'function_call_output','call_id':call_id,'output':reply['resultJson']},
                ])
            if operation in {'search', 'neighborhood'}:
                # Those operations expose discovery, not this object's complete
                # property assertions. Fetch the claim the synthetic writer uses.
                detail = on_graph_operation({'toolName': 'expand_graph_retrieval', 'arguments': {
                    'retrievalSessionId': session.id, 'operation': 'object',
                    'targets': [{'kind': 'node', 'id': 'obj:tavern'}],
                }})
                payload['input'].extend([
                    {'type': 'function_call', 'call_id': 'graph-detail',
                     'name': 'expand_graph_retrieval', 'arguments': '{}'},
                    {'type': 'function_call_output', 'call_id': 'graph-detail',
                     'output': detail['resultJson']},
                ])
            send()
            claim = {
                "kind": "graph_claim",
                "claim_id": "claim:population",
                "text": "The keeper guards the gate.",
                "target_kind": "assertion",
                "target_id": "asrt:population",
                "graph_revision": revision,
                "evidence_ref_ids": ["ev:tavern"],
            }
            answer = {
                "answer_context_status": "graph_grounded",
                "answer_segments": [claim],
                "citation_map": {
                    "entries": [
                        {
                            **{
                                key: value
                                for key, value in claim.items()
                                if key not in {"kind", "text"}
                            },
                            "source_opened": False,
                        }
                    ]
                },
            }
            return AgentRuntimeResult(
                status="ok",
                final_text=json.dumps(answer),
                runtime_session_id="synthetic-session",
            )

    app = FastAPI()
    app.state.agent_turn_runtime = FakeProvider()
    app.state.agent_conversation_service = AgentConversationService()
    app.include_router(route.router, prefix="/api/live")

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            denied = await client.post(
                "/api/live/agent/turn", json=body.model_dump(mode="json", by_alias=True)
            )
            assert denied.status_code == 401 and provider_calls == []
            result = await client.post(
                "/api/live/agent/turn",
                headers={"Authorization": "Bearer " + token},
                json=body.model_dump(mode="json", by_alias=True),
            )
            assert result.status_code == 200, result.text
            return result.json()

    delivered = asyncio.run(exercise())
    assert len(provider_calls) == 2
    service = AgentConversationService()
    conversation = service.get_active_conversation(world)
    saved = service.list_turns(world, conversation.conversation_id)[0]
    assert saved.status == "completed" and saved.user_text == body.message
    events = saved.graph_context_execution.events
    from application_state.agent_conversation.types import PlanWorldGraphExecutionV3
    assert isinstance(saved.graph_context_execution, PlanWorldGraphExecutionV3)
    assert saved.graph_context_execution.policy.source_read_scope.admitted_anchors == []
    origin = next(e for e in events if e.kind == 'validated_graph_operation_v3')
    extension = next(e for e in events if e.kind == 'source_scope_extension_v3')
    read = next(e for e in events if e.kind == 'validated_source_read_v2')
    producing = [e for e in events if e.kind == 'provider_attempt_authorized_v3'][-1]
    assert extension.origin_graph_event_id == origin.event_id
    assert extension.pins == origin.returned_source_pins
    assert read.event_id in producing.included_source_read_event_ids
    citation = saved.completion.citation_map.entries[0]
    assert citation.source_opened and citation.source_read_ids == [read.receipts[0].source_read_id]
    assert core_reads == [read.receipts[0].anchor_id]
    before = saved.model_dump_json()
    rebuilt = project_plan_turn_context(saved, delivery_replay=True)
    assert rebuilt.schema_ == "dmb_agent_plan_world_graph_context_response_v2"
    target = next(t for t in rebuilt.source_open_targets if t.kind == 'evidence_anchor')
    assert target.source_read_id == citation.source_read_ids[0]
    assert (
        service.list_turns(world, conversation.conversation_id)[0].model_dump_json()
        == before
    )
    assert len(provider_calls) == 2 and (tmp_path / "corpus/world_lore.md").read_text() == ANCHOR_CONTENT
    import os
    import subprocess
    import sys

    child = subprocess.check_output(
        [
            sys.executable,
            "-c",
            """
import json, sys
from application_state.agent_conversation import AgentConversationService
from apps.live_control_server.services.agent_turn_service import project_plan_turn_context
from uuid import UUID
turn = AgentConversationService().list_turns(sys.argv[1], UUID(sys.argv[2]))[0]
view = project_plan_turn_context(turn, delivery_replay=True)
print(json.dumps({"turn":turn.model_dump(mode="json",by_alias=True), "view_schema":view.schema_}))
""",
            world,
            str(conversation.conversation_id),
        ],
        env=os.environ.copy(),
        text=True,
    )
    readback = json.loads(child)
    assert readback["turn"] == saved.model_dump(mode="json", by_alias=True)
    assert readback["view_schema"] == "dmb_agent_plan_world_graph_context_response_v2"
    assert (
        delivered["plan_context"]["source_open_targets"]
        == rebuilt.model_dump(mode="json", by_alias=True)["source_open_targets"]
    )


@pytest.mark.parametrize('consumer', ['ordinary', 'saved_plan'])
@pytest.mark.parametrize('failure', ['foreign', 'stale', 'unreadable', 'mixed'])
def test_v3_source_batch_denied_before_io_for_both_consumers(tmp_path, monkeypatch, consumer, failure):
    from types import SimpleNamespace
    from tests.test_agent_turn_route import _selected_consumer_context
    from apps.live_control_server.services import agent_turn_service as owner
    from apps.live_control_server.services.plan_action_consultation import ActionPolicyExecutionAdapter
    from graph_memory.interaction.session import SourceAnchorState
    body, work, bootstrap, receipt, execution, _ = _selected_consumer_context(tmp_path, monkeypatch)
    session = bootstrap.retrieval_session
    pin = execution.policy.source_read_scope.admitted_anchors[0]
    session.source_anchors = [SourceAnchorState(anchor_id=pin.anchor_id, readable=True)]
    anchor_ids = [pin.anchor_id]
    if failure == 'foreign':
        session.snapshot.world_id = 'foreign-world'
    elif failure == 'stale':
        session.snapshot.revision_id = 'stale-revision'
    elif failure == 'unreadable':
        session.source_anchors[0].readable = False
    else:
        anchor_ids.append('unreturned-anchor')
    monkeypatch.setattr('graph_memory.interaction.session_store.get_session', lambda _: session)
    monkeypatch.setattr('graph_memory.interaction.expansion_executor.execute_read_graph_source',
                        lambda *_a, **_kw: pytest.fail('source IO must not run for a rejected batch'))
    if consumer == 'ordinary':
        adapter = owner._PolicyExecutionAdapter(service=object(), request=body, world_id=work.world_id,
            work=work, bootstrap=bootstrap, playable_target=None, submitted_intent=None,
            existing_turn=None, budget={})
        adapter.fence = SimpleNamespace(turn=_policy_turn(status='running', completion_present=False).model_copy(
            update={'graph_context_receipt':receipt, 'graph_context_execution':execution}))
    else:
        action = SimpleNamespace(basis=SimpleNamespace(world_id=work.world_id),
                                 consultation=SimpleNamespace(receipt=receipt, execution=execution))
        adapter = ActionPolicyExecutionAdapter(store=object(), action=action, bootstrap=bootstrap,
                                               budget={}, surface_instance_id='synthetic')
        adapter.fence = SimpleNamespace(action=action)
    adapter.last_provider_attempt_id = uuid4()
    reply = adapter.broker_source_read({'toolName':'read_graph_source', 'arguments':{
        'retrievalSessionId':session.id, 'anchorIds':anchor_ids}})
    assert json.loads(reply['resultJson'])['code'] == (
        'graph_revision_conflict' if failure in {'foreign','stale'} else 'source_anchor_not_admitted')


def test_parent_uncapped_related_context_can_read_ninth_passage(monkeypatch):
    from application_state.agent_conversation.types import graph_execution_policy_digest_v2
    fixture = _related_recap_broker_fixture(monkeypatch)
    turn = fixture.adapter.fence.turn
    execution = turn.graph_context_execution
    policy = type(execution.policy).model_validate(execution.policy.model_dump(mode='json', by_alias=True) | {
        'policy_version': 'world_graph_execution_uncapped_v1',
        **dict.fromkeys(('max_provider_attempts', 'max_graph_operations',
            'max_total_provider_input_tokens', 'max_total_provider_output_tokens'))})
    updated = type(execution)(context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=graph_execution_policy_digest_v2(execution.context_receipt_sha256, policy),
        policy=policy, events=[])
    fixture.adapter.fence.turn = turn.model_copy(update={'graph_context_execution': updated})
    for _ in range(9):
        output = fixture.adapter.broker_graph_operation(_related_recap_request(fixture, maxChars=100))
        value = json.loads(output['resultJson'])
        assert value['schema'] != 'dmb_world_graph_retrieval_error_v1', value
    events = fixture.adapter.fence.turn.graph_context_execution.events
    assert sum(event.kind == 'related_recap_context_authorized_v2' for event in events) == 9
    assert sum(event.kind == 'validated_related_recap_context_v2' for event in events) == 9
