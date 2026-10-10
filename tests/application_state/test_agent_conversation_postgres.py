from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from time import sleep
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from starlette.requests import Request

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    ConversationCommand,
    DraftSave,
    HistoricalReference,
    PlanContextPolicyV1,
    PlanPlayableTargetReceiptV1,
    PlayRunTurnContextReceiptV1,
    PlanWorldGraphCitationMapV1,
    PlanWorldGraphCitationV1,
    PlanWorldGraphClaimSegmentV1,
    PlanWorldGraphCompletionV1,
    PlanWorldGraphConnectiveSegmentV1,
    PlanWorldGraphContextReceiptV1,
    PlanWorldGraphPlanClaimSegmentV1,
    SubmittedGraphRequestIntentV1,
    SubmittedPlanPlayableTargetV1,
    SubmittedPrimaryWorkIntentV1,
    SubmittedTurnIntentV1,
    SubmittedTurnIntentV2,
    TurnFailure,
    TurnProvenance,
    TurnResult,
    TurnSubmission,
    decode_play_run_turn_context_references,
    encode_play_run_turn_context_references,
    encode_plan_playable_target_reference,
)
from application_state.cli import _current_and_head
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateValidationError,
)


@pytest.fixture(autouse=True)
def _authorize_route_execution(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    """Keep conversation persistence tests independent of local auth setup."""
    from apps.live_control_server.routes import agent as agent_route

    if request.node.name == "test_agent_conversation_history_auth_precedes_world_lookup":
        return
    monkeypatch.setattr(agent_route, "enforce_native_graph_gm", lambda _request: None)


def _reference(kind: str, object_id: str, revision: str, digest: str | None = None):
    return HistoricalReference(
        resolution="resolved",
        kind=kind,
        object_id=object_id,
        revision=revision,
        content_sha256=digest,
    )


def test_play_run_context_complete_tuple_survives_fresh_service(
    application_state_dsn: str,
) -> None:
    writer = AgentConversationService()
    world_id = "play-run-codec-world"
    conversation = _new(writer, world_id)
    receipt = PlayRunTurnContextReceiptV1(
        schema="dmb_play_run_turn_context_receipt_v1",
        run_id="run-7",
        run_revision=3,
        runbook_object_id="runbook-7",
        runbook_object_revision=5,
        runbook_work_revision_id=uuid4(),
        runbook_revision_n=2,
        runbook_content_sha256="b" * 64,
        beat_id="beat:a",
        scene_id="scene:arrival",
    )
    primary, supporting = encode_play_run_turn_context_references(receipt)
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="play",
        primary_work=primary,
        supporting_work=supporting,
        selected_object=HistoricalReference(resolution="absent"),
    )
    writer.accept_turn(
        TurnSubmission(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=1,
            user_text="What happens now?",
            provenance=provenance,
            submitted_intent_v1=SubmittedTurnIntentV1(
                world_id=world_id,
                client_thread_id="play-run-test-thread",
                message="What happens now?",
                surface_id="play",
                surface_instance_id="play-main",
                client_work_state="none",
                primary_work=SubmittedPrimaryWorkIntentV1(
                    kind="run", object_id="run-7", expected_revision=3
                ),
                graph_request=SubmittedGraphRequestIntentV1(mode="none"),
                graph_selection=None,
            ),
        )
    )
    loaded = AgentConversationService().list_turns(
        world_id, conversation.conversation_id
    )[0]
    assert loaded.provenance == provenance
    assert (
        decode_play_run_turn_context_references(
            loaded.provenance.primary_work, loaded.provenance.supporting_work
        )
        == receipt
    )


def _provenance(world_id: str) -> TurnProvenance:
    return TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="index",
        primary_work=_reference("plan", "plan-uuid-1", "work-revision-3"),
        supporting_work=[
            _reference("source_artifact", "source-7", "revision-12", "f" * 64)
        ],
        selected_object=HistoricalReference(resolution="absent"),
    )


def _typed_provenance(world_id: str) -> TurnProvenance:
    digest = "d" * 64
    return TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id="plan-pane-7",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="plan-document-7",
            content_sha256=digest,
            object_revision=9,
            work_revision_id=uuid4(),
            revision_n=4,
        ),
        supporting_work=[
            HistoricalReference(
                resolution="resolved",
                kind="runbook",
                object_id="runbook-2",
                content_sha256="e" * 64,
                object_revision=5,
                work_revision_id=uuid4(),
                revision_n=12,
            )
        ],
        selected_object=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="plan-selection-3",
            content_sha256="f" * 64,
            object_revision=6,
            work_revision_id=uuid4(),
            revision_n=8,
        ),
    )


def _graph_receipt(
    world_id: str,
    plan_revision_id,
    playable_target: PlanPlayableTargetReceiptV1 | None = None,
    *,
    evidence_sufficiency_status: str = "insufficient",
    candidate_assertion_ids: list[str] | None = None,
    candidate_evidence_ref_ids: list[str] | None = None,
    dispatched_assertion_ids: list[str] | None = None,
    dispatched_evidence_ref_ids: list[str] | None = None,
    coverage_status: str = "incomplete",
    truncated: bool = False,
) -> PlanWorldGraphContextReceiptV1:
    candidate_assertion_ids = candidate_assertion_ids or []
    candidate_evidence_ref_ids = candidate_evidence_ref_ids or []
    dispatched_assertion_ids = dispatched_assertion_ids or []
    dispatched_evidence_ref_ids = dispatched_evidence_ref_ids or []
    sufficient = evidence_sufficiency_status == "sufficient"
    has_candidates = bool(candidate_assertion_ids or candidate_evidence_ref_ids)
    payload = {
        "schema": "dmb_agent_plan_world_graph_context_receipt_v1",
        "receipt_serializer_version": "canonical-json-utf8-v1",
        "plan_context_policy": {
            "schema": "dmb_plan_context_policy_v1",
            "policy": "auto_plan_world",
        },
        "plan_basis": {
            "world_id": world_id,
            "document_id": "graph-receipt-plan",
            "object_revision": 3,
            "work_revision_id": str(plan_revision_id),
            "revision_n": 2,
            "content_sha256": "a" * 64,
        },
        "playable_target": (
            None
            if playable_target is None
            else playable_target.model_dump(mode="json", by_alias=True)
        ),
        "graph_authority": {
            "managed_world_id": world_id,
            "native_world_id": "native-world-17",
            "binding_version": 4,
            "scope_mode": "world",
            "campaign_id": None,
            "admissibility_version": "admission-v1",
            "graph_revision": "graph-rev-11",
        },
        "graph_packet": {
            "schema": "dmb_plan_world_graph_packet_v1",
            "packet_serializer_version": "canonical-json-utf8-v1",
            "selection_policy_version": "selection-v1",
            "evidence_sufficiency_policy_version": "sufficiency-v1",
            "retrieval_packet_sha256": "b" * 64,
            "candidate_assertion_ids": candidate_assertion_ids,
            "candidate_relationship_ids": [],
            "candidate_evidence_ref_ids": candidate_evidence_ref_ids,
            "retrieval_status": "complete" if has_candidates else "empty",
            "evidence_sufficiency_status": evidence_sufficiency_status,
            "result_limit": 32,
            "coverage_status": coverage_status,
            "truncated": truncated,
            "omission_reasons": [] if has_candidates else ["no_admissible_evidence"],
        },
        "assembled_input": {
            "assembler_version": "assembler-v1",
            "budget_policy_version": "budget-v1",
            "provider_model_name": "synthetic-model",
            "provider_model_version": "1",
            "tokenizer_name": "synthetic-tokenizer",
            "tokenizer_version": "1",
            "provider_envelope_input_tokens": 12,
            "output_token_reserve": 10,
            "context_window_limit": 100,
            "packet_disposition": "included" if sufficient else "omitted_insufficient",
            "packet_disposition_reason": None if sufficient else "insufficient_evidence",
            "dispatched_packet_sha256": "d" * 64 if sufficient else None,
            "dispatched_assertion_ids": dispatched_assertion_ids,
            "dispatched_relationship_ids": [],
            "dispatched_evidence_ref_ids": dispatched_evidence_ref_ids,
            "source_token_accounting": [],
            "included_history": [],
            "assembled_input_sha256": "c" * 64,
        },
        "evidence_mode": "metadata_only",
        "source_opened": False,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    payload["context_receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    return PlanWorldGraphContextReceiptV1.model_validate(payload)


def _saved_plan_turn_payload(
    *, world_id: str, work_object, work_revision, turn_id: str, message: str
) -> dict[str, object]:
    return {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": "same-browser-thread",
        "turn_id": turn_id,
        "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
        "owner_scope": {"kind": "world", "world_id": world_id},
        "primary_work": {
            "kind": "plan",
            "object_id": str(work_object.work_object_id),
            "expected_revision": work_object.object_revision,
            "expected_revision_n": work_revision.revision_n,
            "expected_content_sha256": work_revision.content_sha256,
        },
        "client_work_state": "saved_clean",
        "graph_request": {"mode": "none"},
        "graph_selection": None,
        "message": message,
    }


def _new(service: AgentConversationService, world_id: str):
    return service.new_conversation(
        ConversationCommand(
            world_id=world_id,
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )


def _accepted_execution_turn(
    service: AgentConversationService,
    world_id: str,
    *,
    max_graph_operations: int = 2,
    candidate_assertion_ids: list[str] | None = None,
) -> tuple[Any, PlanWorldGraphContextReceiptV1, Any, Any]:
    from application_state.agent_conversation.types import (
        GraphExecutionAccountingV1,
        GraphExecutionPolicyV1,
        PlanWorldGraphExecutionV1,
    )

    conversation = _new(service, world_id)
    plan_revision_id = uuid4()
    receipt = _graph_receipt(
        world_id,
        plan_revision_id,
        candidate_assertion_ids=candidate_assertion_ids,
    )
    intent = SubmittedTurnIntentV2(
        world_id=world_id,
        client_thread_id=f"{world_id}-thread",
        message="Ask about this Plan Graph context.",
        surface_id="plan",
        surface_instance_id="plan-execution-test",
        client_work_state="saved_clean",
        primary_work=SubmittedPrimaryWorkIntentV1(
            kind="plan",
            object_id="graph-receipt-plan",
            expected_revision=3,
            expected_revision_n=2,
            expected_content_sha256="a" * 64,
        ),
        plan_context_policy=PlanContextPolicyV1(policy="auto_plan_world"),
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id="plan-execution-test",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="graph-receipt-plan",
            content_sha256="a" * 64,
            object_revision=3,
            work_revision_id=plan_revision_id,
            revision_n=2,
        ),
        selected_object=HistoricalReference(resolution="absent"),
    )
    execution = PlanWorldGraphExecutionV1(
        schema="dmb_agent_plan_world_graph_execution_v1",
        context_receipt_sha256=receipt.context_receipt_sha256,
        policy=GraphExecutionPolicyV1(
            policy_version="test-policy-v1",
            allowed_graph_operations=["search_assertions"],
            max_provider_attempts=2,
            max_graph_operations=max_graph_operations,
            max_results_per_operation=8,
            max_total_provider_input_tokens=200,
            max_total_provider_output_tokens=40,
            provider_input_accounting=GraphExecutionAccountingV1(
                kind="exact_token_count", estimator="synthetic-tokenizer"
            ),
            source_opened=False,
        ),
        events=[],
    )
    accepted = service.accept_turn(
        TurnSubmission(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=1,
            user_text=intent.message,
            provenance=provenance,
            submitted_intent_v2=intent,
            graph_context_receipt=receipt,
            graph_context_execution=execution,
        )
    )
    claimed = service.claim_turn(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
    ).turn
    return conversation, receipt, accepted, claimed


def _provider_authorization_event(
    *,
    attempt_id,
    sequence: int,
    assertions: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    graph_event_ids: list[Any] | None = None,
):
    from application_state.agent_conversation.types import (
        ProviderAttemptAuthorizedEventV1,
    )

    return ProviderAttemptAuthorizedEventV1(
        event_id=uuid4(),
        sequence=sequence,
        kind="provider_attempt_authorized",
        provider_attempt_id=attempt_id,
        envelope_sha256="c" * 64,
        serializer_version="canonical-json-utf8-v1",
        provider="test-provider",
        model="synthetic-model",
        api_mode="messages",
        tool_schema_sha256="5" * 64,
        input_accounting_kind="exact_token_count",
        input_estimator="synthetic-tokenizer",
        input_tokens=12,
        output_token_reserve=10,
        included_assertion_ids=assertions or [],
        included_relationship_ids=[],
        included_evidence_ref_ids=evidence_refs or [],
        included_graph_event_ids=graph_event_ids or [],
    )


def _execution_completion_fixture(
    *,
    evidence_sufficiency_status: str = "sufficient",
    coverage_status: str = "incomplete",
    truncated: bool = False,
):
    from application_state.agent_conversation.types import (
        GraphExecutionAccountingV1,
        GraphExecutionPolicyV1,
        PlanWorldGraphExecutionV1,
        ProviderOutcomeEventV1,
        validate_execution_completion,
    )

    attempt_id = uuid4()
    has_evidence = evidence_sufficiency_status == "sufficient"
    assertion_ids = ["assertion-classification"] if has_evidence else []
    evidence_ref_ids = ["evidence-classification"] if has_evidence else []
    receipt = _graph_receipt(
        "completion-classification-world",
        uuid4(),
        evidence_sufficiency_status=evidence_sufficiency_status,
        candidate_assertion_ids=assertion_ids,
        candidate_evidence_ref_ids=evidence_ref_ids,
        dispatched_assertion_ids=assertion_ids,
        dispatched_evidence_ref_ids=evidence_ref_ids,
        coverage_status=coverage_status,
        truncated=truncated,
    )
    claim = PlanWorldGraphClaimSegmentV1(
        kind="graph_claim",
        claim_id="claim-classification",
        text="Fixed test claim.",
        target_kind="assertion",
        target_id="assertion-classification",
        graph_revision=receipt.graph_authority.graph_revision,
        evidence_ref_ids=["evidence-classification"],
    )
    completion = PlanWorldGraphCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis="committed_plan_plus_world_graph",
        answer_context_status="graph_grounded_partial",
        answer_segments=[claim],
        citation_map=PlanWorldGraphCitationMapV1(
            context_receipt_sha256=receipt.context_receipt_sha256,
            entries=[
                PlanWorldGraphCitationV1(
                    claim_id=claim.claim_id,
                    target_kind=claim.target_kind,
                    target_id=claim.target_id,
                    graph_revision=claim.graph_revision,
                    evidence_ref_ids=claim.evidence_ref_ids,
                    source_opened=False,
                )
            ],
        ),
    )
    authorized = _provider_authorization_event(
        attempt_id=attempt_id,
        sequence=0,
        assertions=assertion_ids,
        evidence_refs=evidence_ref_ids,
    )
    execution = PlanWorldGraphExecutionV1(
        schema="dmb_agent_plan_world_graph_execution_v1",
        context_receipt_sha256=receipt.context_receipt_sha256,
        policy=GraphExecutionPolicyV1(
            policy_version="completion-classification-test-v1",
            allowed_graph_operations=["search_assertions"],
            max_provider_attempts=1,
            max_graph_operations=0,
            max_results_per_operation=8,
            max_total_provider_input_tokens=100,
            max_total_provider_output_tokens=100,
            provider_input_accounting=GraphExecutionAccountingV1(
                kind="exact_token_count",
                estimator="synthetic-tokenizer",
            ),
            source_opened=False,
        ),
        events=[
            authorized,
            ProviderOutcomeEventV1(
                event_id=uuid4(),
                sequence=1,
                kind="provider_outcome",
                provider_attempt_id=attempt_id,
                outcome="sdk_entered",
            ),
            ProviderOutcomeEventV1(
                event_id=uuid4(),
                sequence=2,
                kind="provider_outcome",
                provider_attempt_id=attempt_id,
                outcome="response_received",
                response_sha256="9" * 64,
            ),
        ],
    )
    return receipt, completion, execution, attempt_id, validate_execution_completion


def test_agent_conversation_migration_is_single_current_head(
    application_state_dsn: str,
) -> None:
    current, head = _current_and_head(application_state_dsn)
    assert current == head == "20261008_0019"


def test_completion_validation_codes_are_closed_safe_and_valueerror_compatible() -> (
    None
):
    from application_state.agent_conversation.types import (
        GraphCompletionRejectionCode,
        GraphCompletionValidationError,
        PlanWorldGraphPlanClaimSegmentV1,
        validate_completion_against_receipt,
    )

    receipt, completion, execution, attempt_id, validate_execution = (
        _execution_completion_fixture()
    )
    assert (
        validate_execution(
            completion,
            receipt,
            execution,
            attempt_id,
            {"claim-classification": []},
        )
        is None
    )
    assert validate_completion_against_receipt(completion, receipt) is None

    cases = [
        (
            completion.model_copy(update={"context_receipt_sha256": "f" * 64}),
            receipt,
            execution,
            attempt_id,
            {"claim-classification": []},
            GraphCompletionRejectionCode.RECEIPT_BINDING,
            "completion must bind the exact stored Graph receipt",
        ),
        (
            completion,
            receipt,
            execution,
            uuid4(),
            {"claim-classification": []},
            GraphCompletionRejectionCode.PRODUCING_RESPONSE_MISSING,
            "completion requires a durable response from its producing attempt",
        ),
        (
            completion,
            receipt,
            execution,
            attempt_id,
            {},
            GraphCompletionRejectionCode.CLAIM_BINDING_SET,
            "completion binding must map each Graph claim exactly once",
        ),
        (
            completion.model_copy(update={"citation_map": None}),
            receipt,
            execution,
            attempt_id,
            {"claim-classification": []},
            GraphCompletionRejectionCode.CITATION_MAP_MISSING,
            "Graph claims require a citation map",
        ),
        (
            completion.model_copy(update={"answer_context_status": "graph_grounded"}),
            receipt,
            execution,
            attempt_id,
            {"claim-classification": []},
            GraphCompletionRejectionCode.GROUNDED_STATUS_MISMATCH,
            "Graph grounded status does not match cited execution evidence",
        ),
    ]
    for (
        candidate,
        candidate_receipt,
        candidate_execution,
        producing_id,
        bindings,
        code,
        message,
    ) in cases:
        with pytest.raises(GraphCompletionValidationError) as rejected:
            validate_execution(
                candidate,
                candidate_receipt,
                candidate_execution,
                producing_id,
                bindings,
            )
        assert isinstance(rejected.value, ValueError)
        assert str(rejected.value) == message
        assert rejected.value.rejection_code is code
        assert "assertion-classification" not in rejected.value.rejection_code.value
        assert "evidence-classification" not in rejected.value.rejection_code.value

    plan_only_completion = PlanWorldGraphCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis="committed_plan",
        answer_context_status="plan_only_insufficient_evidence",
        answer_segments=[
            PlanWorldGraphPlanClaimSegmentV1(
                kind="plan_claim",
                text="Fixed Plan test segment.",
                plan_content_sha256=receipt.plan_basis.content_sha256,
            )
        ],
        citation_map=None,
    )
    with pytest.raises(GraphCompletionValidationError) as wrong_plan_only_status:
        validate_execution(
            plan_only_completion,
            receipt,
            execution,
            attempt_id,
            {},
        )
    assert (
        wrong_plan_only_status.value.rejection_code
        is GraphCompletionRejectionCode.PLAN_ONLY_STATUS_MISMATCH
    )

    with pytest.raises(GraphCompletionValidationError) as receipt_rejected:
        validate_completion_against_receipt(
            completion.model_copy(update={"context_receipt_sha256": "f" * 64}),
            receipt,
        )
    assert isinstance(receipt_rejected.value, ValueError)
    assert (
        str(receipt_rejected.value)
        == "completion must bind the exact stored Graph receipt"
    )
    assert (
        receipt_rejected.value.rejection_code
        is GraphCompletionRejectionCode.RECEIPT_BINDING
    )


def test_execution_answer_status_derives_from_validated_producing_evidence() -> None:
    from inspect import signature

    from pydantic import ValidationError

    from application_state.agent_conversation.types import (
        GraphCompletionRejectionCode,
        GraphCompletionValidationError,
        PlanWorldGraphPlanClaimSegmentV1,
        derive_execution_answer_context_status,
        validate_execution_completion,
    )

    receipt, completion, execution, attempt_id, _ = _execution_completion_fixture()
    bindings = {"claim-classification": []}
    model_status_values = (
        "graph_grounded",
        "graph_grounded_partial",
        "plan_only_insufficient_evidence",
        "plan_only_graph_unused",
    )
    assert "answer_context_status" not in signature(
        derive_execution_answer_context_status
    ).parameters

    def derive(candidate, candidate_receipt, candidate_execution, candidate_attempt, bindings):
        # The status is deliberately excluded from the helper input fields.
        return derive_execution_answer_context_status(
            context_receipt_sha256=candidate.context_receipt_sha256,
            answer_segments=candidate.answer_segments,
            citation_map=candidate.citation_map,
            receipt=candidate_receipt,
            execution=candidate_execution,
            producing_provider_attempt_id=candidate_attempt,
            claim_graph_event_ids=bindings,
        )

    assert (
        derive(completion, receipt, execution, attempt_id, bindings)
        == "graph_grounded_partial"
    )

    for model_status in model_status_values:
        status_variant = completion.model_copy(
            update={"answer_context_status": model_status}
        )
        assert (
            derive(status_variant, receipt, execution, attempt_id, bindings)
            == "graph_grounded_partial"
        )

    mislabeled_graph_completion = completion.model_copy(
        update={"answer_context_status": "graph_grounded"}
    )
    with pytest.raises(GraphCompletionValidationError) as graph_status_mismatch:
        validate_execution_completion(
            mislabeled_graph_completion, receipt, execution, attempt_id, bindings
        )
    assert (
        graph_status_mismatch.value.rejection_code
        is GraphCompletionRejectionCode.GROUNDED_STATUS_MISMATCH
    )
    assert (
        str(graph_status_mismatch.value)
        == "Graph grounded status does not match cited execution evidence"
    )

    complete_receipt, complete_completion, complete_execution, complete_attempt, _ = (
        _execution_completion_fixture(coverage_status="complete")
    )
    assert (
        derive(
            complete_completion,
            complete_receipt,
            complete_execution,
            complete_attempt,
            bindings,
        )
        == "graph_grounded"
    )

    truncated_receipt, truncated_completion, truncated_execution, truncated_attempt, _ = (
        _execution_completion_fixture(coverage_status="incomplete", truncated=True)
    )
    assert (
        derive(
            truncated_completion,
            truncated_receipt,
            truncated_execution,
            truncated_attempt,
            bindings,
        )
        == "graph_grounded_partial"
    )

    malformed_status = "graph_grounded_unverified"
    with pytest.raises(ValidationError):
        PlanWorldGraphCompletionV1(
            context_receipt_sha256=receipt.context_receipt_sha256,
            answer_basis=completion.answer_basis,
            answer_context_status=malformed_status,
            answer_segments=completion.answer_segments,
            citation_map=completion.citation_map,
        )

    for sufficiency, expected_status, supplied_status in (
        ("sufficient", "plan_only_graph_unused", "plan_only_insufficient_evidence"),
        ("insufficient", "plan_only_insufficient_evidence", "plan_only_graph_unused"),
    ):
        plan_receipt, _, plan_execution, plan_attempt, _ = _execution_completion_fixture(
            evidence_sufficiency_status=sufficiency
        )
        plan_only = PlanWorldGraphCompletionV1(
            context_receipt_sha256=plan_receipt.context_receipt_sha256,
            answer_basis="committed_plan",
            answer_context_status=supplied_status,
            answer_segments=[
                PlanWorldGraphPlanClaimSegmentV1(
                    kind="plan_claim",
                    text="Fixed Plan status test segment.",
                    plan_content_sha256=plan_receipt.plan_basis.content_sha256,
                )
            ],
            citation_map=None,
        )
        for model_status in model_status_values:
            status_variant = plan_only.model_copy(
                update={"answer_context_status": model_status}
            )
            assert (
                derive(status_variant, plan_receipt, plan_execution, plan_attempt, {})
                == expected_status
            )
        with pytest.raises(GraphCompletionValidationError) as plan_status_mismatch:
            validate_execution_completion(
                plan_only, plan_receipt, plan_execution, plan_attempt, {}
            )
        assert (
            plan_status_mismatch.value.rejection_code
            is GraphCompletionRejectionCode.PLAN_ONLY_STATUS_MISMATCH
        )
        assert (
            str(plan_status_mismatch.value)
            == "Plan-only status does not match evidence in the producing envelope"
        )

    with pytest.raises(GraphCompletionValidationError) as invalid_support:
        derive(
            completion,
            receipt,
            execution,
            attempt_id,
            {"claim-classification": [uuid4()]},
        )
    assert (
        invalid_support.value.rejection_code
        is GraphCompletionRejectionCode.BINDING_EVENT_NOT_IN_ENVELOPE
    )


def test_graph_receipt_and_completion_round_trip_through_fresh_service(
    application_state_dsn: str,
) -> None:
    import psycopg
    from alembic import command
    from pydantic import ValidationError

    from application_state.agent_conversation.types import (
        GraphExecutionAccountingV1,
        GraphExecutionPolicyV1,
        PlanWorldGraphExecutionV1,
        ProviderAttemptAuthorizedEventV1,
        ProviderOutcomeEventV1,
    )
    from application_state.cli import alembic_config

    service = AgentConversationService()
    world_id = "graph-receipt-roundtrip-world"
    conversation = _new(service, world_id)
    plan_revision_id = uuid4()
    playable_target = PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind="beat",
        id="beat:a",
        marker_grammar_version="v2",
    )
    submitted_target = SubmittedPlanPlayableTargetV1(
        schema="dmb_plan_playable_target_v1", kind="beat", id="beat:a"
    )
    receipt = _graph_receipt(world_id, plan_revision_id, playable_target)
    intent = SubmittedTurnIntentV2(
        world_id=world_id,
        client_thread_id="graph-receipt-thread",
        message="Summarize the current plan.",
        surface_id="plan",
        surface_instance_id="plan-pane-4",
        client_work_state="saved_clean",
        primary_work=SubmittedPrimaryWorkIntentV1(
            kind="plan",
            object_id="graph-receipt-plan",
            expected_revision=3,
            expected_revision_n=2,
            expected_content_sha256="a" * 64,
        ),
        plan_context_policy=PlanContextPolicyV1(policy="auto_plan_world"),
        playable_target=submitted_target,
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id="plan-pane-4",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="graph-receipt-plan",
            content_sha256="a" * 64,
            object_revision=3,
            work_revision_id=plan_revision_id,
            revision_n=2,
        ),
        supporting_work=[encode_plan_playable_target_reference(playable_target)],
        selected_object=HistoricalReference(resolution="absent"),
    )
    execution = PlanWorldGraphExecutionV1(
        schema="dmb_agent_plan_world_graph_execution_v1",
        context_receipt_sha256=receipt.context_receipt_sha256,
        policy=GraphExecutionPolicyV1(
            policy_version="test-policy-v1",
            allowed_graph_operations=["search_assertions"],
            max_provider_attempts=2,
            max_graph_operations=0,
            max_results_per_operation=0,
            max_total_provider_input_tokens=100,
            max_total_provider_output_tokens=40,
            provider_input_accounting=GraphExecutionAccountingV1(
                kind="exact_token_count", estimator="synthetic-tokenizer"
            ),
            source_opened=False,
        ),
        events=[],
    )
    submission = TurnSubmission(
        world_id=world_id,
        conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text=intent.message,
        provenance=provenance,
        submitted_intent_v2=intent,
        graph_context_receipt=receipt,
        graph_context_execution=execution,
    )
    accepted = service.accept_turn(submission)
    fresh = AgentConversationService()
    loaded = fresh.list_turns(world_id, conversation.conversation_id)[0]
    assert loaded.graph_context_receipt == receipt
    assert loaded.graph_context_execution == execution
    assert (
        loaded.graph_context_receipt.playable_target.marker_grammar_version == "v2"
    )
    assert fresh.accept_turn(submission) == accepted
    changed_execution = execution.model_copy(
        update={"policy": execution.policy.model_copy(update={"max_provider_attempts": 3})}
    )
    with pytest.raises(ApplicationStateConflictError, match="different submitted intent or Graph receipt"):
        fresh.accept_turn(submission.model_copy(update={"graph_context_execution": changed_execution}))

    with pytest.raises(ValidationError, match="Graph context receipt must match"):
        TurnSubmission(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=1,
            user_text=intent.message,
            provenance=provenance,
            submitted_intent_v2=intent.model_copy(
                update={
                    "playable_target": SubmittedPlanPlayableTargetV1(
                        schema="dmb_plan_playable_target_v1",
                        kind="beat",
                        id="beat:b",
                    )
                }
            ),
            graph_context_receipt=receipt,
        )

    claimed = fresh.claim_turn(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
        lease_seconds=60,
    )
    attempt_id = uuid4()
    authorization_event = ProviderAttemptAuthorizedEventV1(
        event_id=uuid4(), sequence=0, kind="provider_attempt_authorized",
        provider_attempt_id=attempt_id, envelope_sha256="c" * 64,
        serializer_version="canonical-json-utf8-v1", provider="test-provider",
        model="synthetic-model", api_mode="messages", tool_schema_sha256="2" * 64,
        input_accounting_kind="exact_token_count", input_estimator="synthetic-tokenizer",
        input_tokens=12, output_token_reserve=10, included_assertion_ids=[],
        included_relationship_ids=[], included_evidence_ref_ids=[], included_graph_event_ids=[],
    )
    authorized, allowed = fresh.authorize_provider_attempt(
        world_id, conversation.conversation_id, accepted.turn_id,
        expected_revision=claimed.turn.revision, expected_attempt=claimed.turn.attempt,
        provider_attempt_event=authorization_event,
    )
    assert allowed is True
    duplicate_turn, duplicate_allowed = fresh.authorize_provider_attempt(
        world_id, conversation.conversation_id, accepted.turn_id,
        expected_revision=authorized.revision, expected_attempt=claimed.turn.attempt,
        provider_attempt_event=authorization_event,
    )
    assert duplicate_allowed is False
    assert duplicate_turn.graph_context_execution == authorized.graph_context_execution
    with pytest.raises(ApplicationStateConflictError, match="stale claim"):
        fresh.authorize_provider_attempt(
            world_id, conversation.conversation_id, accepted.turn_id,
            expected_revision=claimed.turn.revision, expected_attempt=claimed.turn.attempt,
            provider_attempt_event=authorization_event,
        )
    entered, _ = fresh.record_provider_outcome(
        world_id, conversation.conversation_id, accepted.turn_id,
        expected_revision=authorized.revision, expected_attempt=claimed.turn.attempt,
        outcome=ProviderOutcomeEventV1(
            event_id=uuid4(), sequence=1, kind="provider_outcome",
            provider_attempt_id=attempt_id, outcome="sdk_entered",
        ),
    )
    responded, _ = fresh.record_provider_outcome(
        world_id, conversation.conversation_id, accepted.turn_id,
        expected_revision=entered.revision, expected_attempt=claimed.turn.attempt,
        outcome=ProviderOutcomeEventV1(
            event_id=uuid4(), sequence=2, kind="provider_outcome",
            provider_attempt_id=attempt_id, outcome="response_received",
            response_sha256="3" * 64,
        ),
    )
    completion = PlanWorldGraphCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis="committed_plan",
        answer_context_status="plan_only_insufficient_evidence",
        answer_segments=[
            PlanWorldGraphPlanClaimSegmentV1(
                kind="plan_claim",
                text="The plan is to reach the northern pass.",
                plan_content_sha256="a" * 64,
            )
        ],
        citation_map=None,
    )
    completed = fresh.complete_turn(
        TurnResult(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=responded.revision,
            assistant_text="The plan is to reach the northern pass.",
            completion=completion,
            producing_provider_attempt_id=attempt_id,
            claim_graph_event_ids={},
        )
    )
    reloaded = AgentConversationService().list_turns(
        world_id, conversation.conversation_id
    )[0]
    assert reloaded == completed
    assert reloaded.graph_context_receipt == receipt
    assert reloaded.completion == completion
    assert reloaded.graph_context_execution.events[-1].kind == "completion_binding"
    assert fresh.accept_turn(submission) == completed
    with pytest.raises(ApplicationStateConflictError, match="different recorded result"):
        fresh.complete_turn(
            TurnResult(
                world_id=world_id,
                conversation_id=conversation.conversation_id,
                turn_id=accepted.turn_id,
                expected_revision=responded.revision,
                assistant_text="The plan is to reach the northern pass.",
                completion=completion,
                producing_provider_attempt_id=uuid4(),
                claim_graph_event_ids={},
            )
        )
    assert fresh.claim_turn(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
    ).turn == completed

    # A populated V1 execution row must satisfy the V1 check while 0018 is
    # removed and restored; this exercises the 0017 -> 0018 upgrade path.
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        v1_execution_before = conn.execute(
            "SELECT graph_context_execution FROM agent.turn WHERE turn_id = %s",
            (accepted.turn_id,),
        ).fetchone()[0]
    assert v1_execution_before is not None
    command.downgrade(alembic_config(), "20261005_0017")
    assert _current_and_head(application_state_dsn) == (
        "20261005_0017", "20261008_0019"
    )
    command.upgrade(alembic_config(), "head")
    assert _current_and_head(application_state_dsn) == (
        "20261008_0019", "20261008_0019"
    )
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        assert conn.execute(
            "SELECT graph_context_execution FROM agent.turn WHERE turn_id = %s",
            (accepted.turn_id,),
        ).fetchone()[0] == v1_execution_before

    # Model a populated 0016 row: receipt/completion and legacy fingerprints
    # exist, while the newly introduced execution column is still NULL.
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        conn.execute(
            "UPDATE agent.turn SET graph_context_execution = NULL WHERE turn_id = %s",
            (accepted.turn_id,),
        )
        graph_state_before = conn.execute(
            """SELECT request_fingerprint, idempotency_fingerprint,
                      graph_context_receipt, completion, graph_context_execution
               FROM agent.turn WHERE turn_id = %s""",
            (accepted.turn_id,),
        ).fetchone()
    command.downgrade(alembic_config(), "20261004_0016")
    command.upgrade(alembic_config(), "head")
    assert _current_and_head(application_state_dsn) == (
        "20261008_0019", "20261008_0019"
    )
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        assert conn.execute(
            """SELECT request_fingerprint, idempotency_fingerprint,
                      graph_context_receipt, completion, graph_context_execution
               FROM agent.turn WHERE turn_id = %s""",
            (accepted.turn_id,),
        ).fetchone() == graph_state_before
    migrated = AgentConversationService().list_turns(world_id, conversation.conversation_id)[0]
    assert migrated.graph_context_execution is None
    assert migrated.graph_context_receipt == completed.graph_context_receipt
    assert migrated.completion == completed.completion
    legacy_receipt_replay = submission.model_copy(update={"graph_context_execution": None})
    assert AgentConversationService().accept_turn(legacy_receipt_replay) == migrated

    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute(
                "UPDATE agent.turn SET graph_context_receipt = '{}'::jsonb WHERE turn_id = %s",
                (accepted.turn_id,),
            )
    with pytest.raises(RuntimeError, match="refusing to drop non-null Agent Graph context"):
        command.downgrade(alembic_config(), "20261004_0015")
    assert _current_and_head(application_state_dsn) == (
        "20261008_0019",
        "20261008_0019",
    )


def test_execution_partial_citations_require_sufficient_evidence(
    application_state_dsn: str,
) -> None:
    from application_state.agent_conversation.types import (
        GraphExecutionAccountingV1,
        GraphExecutionPolicyV1,
        PlanWorldGraphExecutionV1,
        ProviderAttemptAuthorizedEventV1,
        ProviderOutcomeEventV1,
        ValidatedGraphOperationEventV1,
    )

    service = AgentConversationService()
    world_id = "graph-execution-citation-sufficiency"
    conversation = _new(service, world_id)
    plan_revision_id = uuid4()
    receipt = _graph_receipt(world_id, plan_revision_id)
    intent = SubmittedTurnIntentV2(
        world_id=world_id,
        client_thread_id="graph-execution-citation-thread",
        message="Describe this Graph evidence.",
        surface_id="plan",
        surface_instance_id="plan-pane-citations",
        client_work_state="saved_clean",
        primary_work=SubmittedPrimaryWorkIntentV1(
            kind="plan",
            object_id="graph-receipt-plan",
            expected_revision=3,
            expected_revision_n=2,
            expected_content_sha256="a" * 64,
        ),
        plan_context_policy=PlanContextPolicyV1(policy="auto_plan_world"),
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id="plan-pane-citations",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="graph-receipt-plan",
            content_sha256="a" * 64,
            object_revision=3,
            work_revision_id=plan_revision_id,
            revision_n=2,
        ),
        selected_object=HistoricalReference(resolution="absent"),
    )
    execution = PlanWorldGraphExecutionV1(
        schema="dmb_agent_plan_world_graph_execution_v1",
        context_receipt_sha256=receipt.context_receipt_sha256,
        policy=GraphExecutionPolicyV1(
            policy_version="test-policy-v1",
            allowed_graph_operations=["search_assertions"],
            max_provider_attempts=1,
            max_graph_operations=2,
            max_results_per_operation=4,
            max_total_provider_input_tokens=100,
            max_total_provider_output_tokens=20,
            provider_input_accounting=GraphExecutionAccountingV1(
                kind="exact_token_count", estimator="synthetic-tokenizer"
            ),
            source_opened=False,
        ),
        events=[],
    )
    accepted = service.accept_turn(
        TurnSubmission(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=1,
            user_text=intent.message,
            provenance=provenance,
            submitted_intent_v2=intent,
            graph_context_receipt=receipt,
            graph_context_execution=execution,
        )
    )
    claimed = service.claim_turn(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
    ).turn
    insufficient = ValidatedGraphOperationEventV1(
        event_id=uuid4(),
        sequence=0,
        kind="validated_graph_operation",
        operation_id=uuid4(),
        operation="search_assertions",
        request_arguments_sha256="1" * 64,
        graph_revision="graph-rev-11",
        result_packet_sha256="2" * 64,
        assertion_ids=["assertion-evidence-1"],
        relationship_ids=[],
        evidence_ref_ids=["evidence-evidence-1"],
        evidence_sufficiency_status="insufficient",
        coverage_status="incomplete",
        truncated=False,
        source_opened=False,
    )
    after_insufficient, _ = service.append_validated_graph_operation(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=claimed.revision,
        expected_attempt=claimed.attempt,
        operation_event=insufficient,
    )
    sufficient_partial = ValidatedGraphOperationEventV1(
        event_id=uuid4(),
        sequence=1,
        kind="validated_graph_operation",
        operation_id=uuid4(),
        operation="search_assertions",
        request_arguments_sha256="3" * 64,
        graph_revision="graph-rev-11",
        result_packet_sha256="4" * 64,
        assertion_ids=["assertion-evidence-1"],
        relationship_ids=[],
        evidence_ref_ids=["evidence-evidence-1"],
        evidence_sufficiency_status="sufficient",
        coverage_status="incomplete",
        truncated=False,
        source_opened=False,
    )
    after_sufficient, _ = service.append_validated_graph_operation(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=after_insufficient.revision,
        expected_attempt=claimed.attempt,
        operation_event=sufficient_partial,
    )
    attempt_id = uuid4()
    authorized, _ = service.authorize_provider_attempt(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=after_sufficient.revision,
        expected_attempt=claimed.attempt,
        provider_attempt_event=ProviderAttemptAuthorizedEventV1(
            event_id=uuid4(),
            sequence=2,
            kind="provider_attempt_authorized",
            provider_attempt_id=attempt_id,
            envelope_sha256="c" * 64,
            serializer_version="canonical-json-utf8-v1",
            provider="test-provider",
            model="synthetic-model",
            api_mode="messages",
            tool_schema_sha256="5" * 64,
            input_accounting_kind="exact_token_count",
            input_estimator="synthetic-tokenizer",
            input_tokens=12,
            output_token_reserve=10,
            included_assertion_ids=["assertion-evidence-1"],
            included_relationship_ids=[],
            included_evidence_ref_ids=["evidence-evidence-1"],
            included_graph_event_ids=[insufficient.event_id, sufficient_partial.event_id],
        ),
    )
    entered, _ = service.record_provider_outcome(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=authorized.revision,
        expected_attempt=claimed.attempt,
        outcome=ProviderOutcomeEventV1(
            event_id=uuid4(), sequence=3, kind="provider_outcome",
            provider_attempt_id=attempt_id, outcome="sdk_entered",
        ),
    )
    responded, _ = service.record_provider_outcome(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=entered.revision,
        expected_attempt=claimed.attempt,
        outcome=ProviderOutcomeEventV1(
            event_id=uuid4(), sequence=4, kind="provider_outcome",
            provider_attempt_id=attempt_id, outcome="response_received",
            response_sha256="6" * 64,
        ),
    )
    claim = PlanWorldGraphClaimSegmentV1(
        kind="graph_claim",
        claim_id="claim-1",
        text="The available assertion is incomplete.",
        target_kind="assertion",
        target_id="assertion-evidence-1",
        graph_revision="graph-rev-11",
        evidence_ref_ids=["evidence-evidence-1"],
    )
    citation = PlanWorldGraphCitationV1(
        claim_id="claim-1",
        target_kind="assertion",
        target_id="assertion-evidence-1",
        graph_revision="graph-rev-11",
        evidence_ref_ids=["evidence-evidence-1"],
        source_opened=False,
    )
    completion = PlanWorldGraphCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis="committed_plan_plus_world_graph",
        answer_context_status="graph_grounded_partial",
        answer_segments=[claim],
        citation_map=PlanWorldGraphCitationMapV1(
            context_receipt_sha256=receipt.context_receipt_sha256,
            entries=[citation],
        ),
    )
    for supporting_events in (
        [insufficient.event_id],
        [insufficient.event_id, sufficient_partial.event_id],
    ):
        with pytest.raises(
            ApplicationStateValidationError,
            match="Graph grounded claims require sufficient cited evidence",
        ):
            service.complete_turn(
                TurnResult(
                    world_id=world_id,
                    conversation_id=conversation.conversation_id,
                    turn_id=accepted.turn_id,
                    expected_revision=responded.revision,
                    assistant_text="Partially grounded answer.",
                    completion=completion,
                    producing_provider_attempt_id=attempt_id,
                    claim_graph_event_ids={"claim-1": supporting_events},
                )
            )
    completed = service.complete_turn(
        TurnResult(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=responded.revision,
            assistant_text="Partially grounded answer.",
            completion=completion,
            producing_provider_attempt_id=attempt_id,
            claim_graph_event_ids={"claim-1": [sufficient_partial.event_id]},
        )
    )
    assert completed.completion == completion


def test_expired_authorized_execution_becomes_unknown_and_cannot_reclaim(
    application_state_dsn: str,
) -> None:
    import psycopg

    service = AgentConversationService()
    world_id = "graph-execution-expired-authorization"
    conversation, _, accepted, claimed = _accepted_execution_turn(service, world_id)
    attempt_id = uuid4()
    authorized, fresh = service.authorize_provider_attempt(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=claimed.revision,
        expected_attempt=claimed.attempt,
        provider_attempt_event=_provider_authorization_event(
            attempt_id=attempt_id, sequence=0
        ),
    )
    assert fresh is True
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            """UPDATE agent.turn SET claim_expires_at = clock_timestamp() - interval '1 second'
               WHERE turn_id = %s""",
            (accepted.turn_id,),
        )
    with pytest.raises(ApplicationStateConflictError, match="recorded as potentially sent"):
        service.claim_turn(
            world_id,
            conversation.conversation_id,
            accepted.turn_id,
            expected_revision=authorized.revision,
        )
    interrupted = service.list_turns(world_id, conversation.conversation_id)[0]
    assert interrupted.status == "interrupted"
    assert interrupted.failure_code == "provider_outcome_unknown"
    assert interrupted.graph_context_execution.events[-1].kind == "provider_outcome"
    assert interrupted.graph_context_execution.events[-1].outcome == "outcome_unknown"
    with pytest.raises(ApplicationStateConflictError, match="prior provider authorization"):
        service.claim_turn(
            world_id,
            conversation.conversation_id,
            accepted.turn_id,
            expected_revision=interrupted.revision,
        )


def test_stale_attempt_cannot_append_provider_outcome(
    application_state_dsn: str,
) -> None:
    from application_state.agent_conversation.types import ProviderOutcomeEventV1

    service = AgentConversationService()
    world_id = "graph-execution-stale-attempt"
    conversation, _, accepted, claimed = _accepted_execution_turn(service, world_id)
    attempt_id = uuid4()
    authorized, _ = service.authorize_provider_attempt(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=claimed.revision,
        expected_attempt=claimed.attempt,
        provider_attempt_event=_provider_authorization_event(
            attempt_id=attempt_id, sequence=0
        ),
    )
    with pytest.raises(ApplicationStateConflictError, match="stale claim"):
        service.record_provider_outcome(
            world_id,
            conversation.conversation_id,
            accepted.turn_id,
            expected_revision=authorized.revision,
            expected_attempt=claimed.attempt + 1,
            outcome=ProviderOutcomeEventV1(
                event_id=uuid4(),
                sequence=1,
                kind="provider_outcome",
                provider_attempt_id=attempt_id,
                outcome="sdk_entered",
            ),
        )
    loaded = service.list_turns(world_id, conversation.conversation_id)[0]
    assert loaded.revision == authorized.revision
    assert [event.kind for event in loaded.graph_context_execution.events] == [
        "provider_attempt_authorized"
    ]


def test_initial_provider_authorization_cannot_include_undispatched_candidates(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    world_id = "graph-execution-undispatched-candidate"
    conversation, receipt, accepted, claimed = _accepted_execution_turn(
        service,
        world_id,
        candidate_assertion_ids=["candidate-only-assertion"],
    )
    assert receipt.assembled_input.dispatched_assertion_ids == []
    attempt_id = uuid4()
    with pytest.raises(
        ApplicationStateValidationError,
        match="provider envelope includes IDs absent from admitted Graph evidence",
    ):
        service.authorize_provider_attempt(
            world_id,
            conversation.conversation_id,
            accepted.turn_id,
            expected_revision=claimed.revision,
            expected_attempt=claimed.attempt,
            provider_attempt_event=_provider_authorization_event(
                attempt_id=attempt_id,
                sequence=0,
                assertions=["candidate-only-assertion"],
            ),
        )
    loaded = service.list_turns(world_id, conversation.conversation_id)[0]
    assert loaded.revision == claimed.revision
    assert loaded.graph_context_execution.events == []


def test_database_enforces_graph_execution_policy_and_storage_limits(
    application_state_dsn: str,
) -> None:
    import psycopg

    service = AgentConversationService()
    world_id = "graph-execution-database-bounds"
    _, _, accepted, _ = _accepted_execution_turn(service, world_id)
    bad_updates = (
        """UPDATE agent.turn
           SET graph_context_execution = jsonb_set(
               graph_context_execution, '{policy,max_provider_attempts}', '0'::jsonb
           ) WHERE turn_id = %s""",
        """UPDATE agent.turn
           SET graph_context_execution = jsonb_set(
               graph_context_execution, '{events}',
               (SELECT jsonb_agg(jsonb_build_object('sequence', n))
                FROM generate_series(1, 2049) AS series(n))
           ) WHERE turn_id = %s""",
        """UPDATE agent.turn
           SET graph_context_execution = jsonb_set(
               graph_context_execution, '{events}',
               jsonb_build_array(jsonb_build_object('padding', repeat('x', 1048576)))
           ) WHERE turn_id = %s""",
    )
    for statement in bad_updates:
        with pytest.raises(psycopg.errors.CheckViolation):
            with psycopg.connect(application_state_dsn) as conn:
                conn.execute(statement, (accepted.turn_id,))


def test_completion_requires_final_attempt_evidence_membership_and_is_atomic(
    application_state_dsn: str,
) -> None:
    import psycopg

    from application_state.agent_conversation.types import (
        ProviderOutcomeEventV1,
        ValidatedGraphOperationEventV1,
    )

    service = AgentConversationService()
    world_id = "graph-execution-final-evidence-membership"
    conversation, receipt, accepted, claimed = _accepted_execution_turn(service, world_id)
    operation = ValidatedGraphOperationEventV1(
        event_id=uuid4(),
        sequence=0,
        kind="validated_graph_operation",
        operation_id=uuid4(),
        operation="search_assertions",
        request_arguments_sha256="1" * 64,
        graph_revision=receipt.graph_authority.graph_revision,
        result_packet_sha256="2" * 64,
        assertion_ids=["assertion-final-evidence"],
        relationship_ids=[],
        evidence_ref_ids=["evidence-final-evidence"],
        evidence_sufficiency_status="sufficient",
        coverage_status="complete",
        truncated=False,
        source_opened=False,
    )
    after_operation, _ = service.append_validated_graph_operation(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=claimed.revision,
        expected_attempt=claimed.attempt,
        operation_event=operation,
    )
    first_attempt_id = uuid4()
    first_authorized, _ = service.authorize_provider_attempt(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=after_operation.revision,
        expected_attempt=claimed.attempt,
        provider_attempt_event=_provider_authorization_event(
            attempt_id=first_attempt_id,
            sequence=1,
            assertions=["assertion-final-evidence"],
            graph_event_ids=[operation.event_id],
        ),
    )
    first_entered, _ = service.record_provider_outcome(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=first_authorized.revision,
        expected_attempt=claimed.attempt,
        outcome=ProviderOutcomeEventV1(
            event_id=uuid4(), sequence=2, kind="provider_outcome",
            provider_attempt_id=first_attempt_id, outcome="sdk_entered",
        ),
    )
    first_response, _ = service.record_provider_outcome(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=first_entered.revision,
        expected_attempt=claimed.attempt,
        outcome=ProviderOutcomeEventV1(
            event_id=uuid4(), sequence=3, kind="provider_outcome",
            provider_attempt_id=first_attempt_id, outcome="response_received",
            response_sha256="3" * 64,
        ),
    )
    claim = PlanWorldGraphClaimSegmentV1(
        kind="graph_claim",
        claim_id="claim-final-evidence",
        text="The cited assertion is supported.",
        target_kind="assertion",
        target_id="assertion-final-evidence",
        graph_revision=receipt.graph_authority.graph_revision,
        evidence_ref_ids=["evidence-final-evidence"],
    )
    completion = PlanWorldGraphCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis="committed_plan_plus_world_graph",
        answer_context_status="graph_grounded",
        answer_segments=[claim],
        citation_map=PlanWorldGraphCitationMapV1(
            context_receipt_sha256=receipt.context_receipt_sha256,
            entries=[PlanWorldGraphCitationV1(
                claim_id=claim.claim_id,
                target_kind="assertion",
                target_id=claim.target_id,
                graph_revision=claim.graph_revision,
                evidence_ref_ids=claim.evidence_ref_ids,
                source_opened=False,
            )],
        ),
    )
    for mapped_ids in ([operation.event_id], [uuid4()]):
        with pytest.raises(ApplicationStateValidationError):
            service.complete_turn(
                TurnResult(
                    world_id=world_id,
                    conversation_id=conversation.conversation_id,
                    turn_id=accepted.turn_id,
                    expected_revision=first_response.revision,
                    assistant_text="The cited assertion is supported.",
                    completion=completion,
                    producing_provider_attempt_id=first_attempt_id,
                    claim_graph_event_ids={claim.claim_id: list(mapped_ids)},
                )
            )
    with psycopg.connect(application_state_dsn) as conn:
        row = conn.execute(
            "SELECT status, completion, graph_context_execution FROM agent.turn WHERE turn_id = %s",
            (accepted.turn_id,),
        ).fetchone()
    assert row[0] == "running"
    assert row[1] is None
    assert not any(
        event["kind"] == "completion_binding"
        for event in row[2]["events"]
    )

    second_attempt_id = uuid4()
    second_authorized, fresh = service.authorize_provider_attempt(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=first_response.revision,
        expected_attempt=claimed.attempt,
        provider_attempt_event=_provider_authorization_event(
            attempt_id=second_attempt_id,
            sequence=4,
            assertions=["assertion-final-evidence"],
            evidence_refs=["evidence-final-evidence"],
            graph_event_ids=[operation.event_id],
        ),
    )
    assert fresh is True
    second_entered, _ = service.record_provider_outcome(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=second_authorized.revision,
        expected_attempt=claimed.attempt,
        outcome=ProviderOutcomeEventV1(
            event_id=uuid4(), sequence=5, kind="provider_outcome",
            provider_attempt_id=second_attempt_id, outcome="sdk_entered",
        ),
    )
    second_response, _ = service.record_provider_outcome(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=second_entered.revision,
        expected_attempt=claimed.attempt,
        outcome=ProviderOutcomeEventV1(
            event_id=uuid4(), sequence=6, kind="provider_outcome",
            provider_attempt_id=second_attempt_id, outcome="response_received",
            response_sha256="4" * 64,
        ),
    )
    completed = service.complete_turn(
        TurnResult(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=second_response.revision,
            assistant_text="The cited assertion is supported.",
            completion=completion,
            producing_provider_attempt_id=second_attempt_id,
            claim_graph_event_ids={claim.claim_id: [operation.event_id]},
        )
    )
    assert completed.completion == completion


@pytest.mark.parametrize(
    ("context_status", "coverage_status", "truncated", "has_graph_claim"),
    [
        ("graph_grounded", "complete", False, True),
        ("graph_grounded_partial", "incomplete", False, True),
        ("plan_only_graph_unused", "complete", False, False),
    ],
)
def test_graph_completion_status_and_citation_membership_persist(
    application_state_dsn: str,
    context_status: str,
    coverage_status: str,
    truncated: bool,
    has_graph_claim: bool,
) -> None:
    service = AgentConversationService()
    world_id = f"graph-completion-{context_status}"
    conversation = _new(service, world_id)
    plan_revision_id = uuid4()
    receipt = _graph_receipt(
        world_id,
        plan_revision_id,
        evidence_sufficiency_status="sufficient",
        candidate_assertion_ids=["assertion-1", "assertion-2"],
        candidate_evidence_ref_ids=["evidence-1", "evidence-2"],
        dispatched_assertion_ids=["assertion-1"],
        dispatched_evidence_ref_ids=["evidence-1"],
        coverage_status=coverage_status,
        truncated=truncated,
    )
    intent = SubmittedTurnIntentV2(
        world_id=world_id,
        client_thread_id="graph-completion-thread",
        message="Describe the available context.",
        surface_id="plan",
        surface_instance_id="plan-pane-5",
        client_work_state="saved_clean",
        primary_work=SubmittedPrimaryWorkIntentV1(
            kind="plan",
            object_id="graph-receipt-plan",
            expected_revision=3,
            expected_revision_n=2,
            expected_content_sha256="a" * 64,
        ),
        plan_context_policy=PlanContextPolicyV1(policy="auto_plan_world"),
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id="plan-pane-5",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="graph-receipt-plan",
            content_sha256="a" * 64,
            object_revision=3,
            work_revision_id=plan_revision_id,
            revision_n=2,
        ),
        selected_object=HistoricalReference(resolution="absent"),
    )
    accepted = service.accept_turn(
        TurnSubmission(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=1,
            user_text=intent.message,
            provenance=provenance,
            submitted_intent_v2=intent,
            graph_context_receipt=receipt,
        )
    )
    claimed = service.claim_turn(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
        lease_seconds=60,
    )

    if has_graph_claim:
        claim = PlanWorldGraphClaimSegmentV1(
            kind="graph_claim",
            claim_id="claim-1",
            text="The dispatched Graph packet names the northern pass.",
            target_kind="assertion",
            target_id="assertion-1",
            graph_revision="graph-rev-11",
            evidence_ref_ids=["evidence-1"],
        )
        citation_map = PlanWorldGraphCitationMapV1(
            context_receipt_sha256=receipt.context_receipt_sha256,
            entries=[
                PlanWorldGraphCitationV1(
                    claim_id="claim-1",
                    target_kind="assertion",
                    target_id="assertion-1",
                    graph_revision="graph-rev-11",
                    evidence_ref_ids=["evidence-1"],
                    source_opened=False,
                )
            ],
        )
        answer_segments = [
            claim,
            PlanWorldGraphConnectiveSegmentV1(
                kind="connective", text="This matches the supplied context."
            ),
        ]
        answer_basis = "committed_plan_plus_world_graph"
        if context_status == "graph_grounded_partial":
            invalid_claim = claim.model_copy(
                update={"evidence_ref_ids": ["evidence-2"]}
            )
            invalid_map = citation_map.model_copy(
                update={
                    "entries": [
                        citation_map.entries[0].model_copy(
                            update={"evidence_ref_ids": ["evidence-2"]}
                        )
                    ]
                }
            )
            invalid_completion = PlanWorldGraphCompletionV1(
                context_receipt_sha256=receipt.context_receipt_sha256,
                answer_basis=answer_basis,
                answer_context_status=context_status,
                answer_segments=[invalid_claim, answer_segments[1]],
                citation_map=invalid_map,
            )
            with pytest.raises(
                ApplicationStateValidationError,
                match="Graph claim evidence refs must be in the dispatched packet",
            ):
                service.complete_turn(
                    TurnResult(
                        world_id=world_id,
                        conversation_id=conversation.conversation_id,
                        turn_id=accepted.turn_id,
                        expected_revision=claimed.turn.revision,
                        assistant_text="invalid citation membership",
                        completion=invalid_completion,
                    )
                )
    else:
        citation_map = None
        answer_segments = [
            PlanWorldGraphPlanClaimSegmentV1(
                kind="plan_claim",
                text="The committed Plan sets out the journey.",
                plan_content_sha256="a" * 64,
            )
        ]
        answer_basis = "committed_plan"

    completion = PlanWorldGraphCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis=answer_basis,
        answer_context_status=context_status,
        answer_segments=answer_segments,
        citation_map=citation_map,
    )
    completed = service.complete_turn(
        TurnResult(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=claimed.turn.revision,
            assistant_text="The stored answer follows the recorded context.",
            completion=completion,
        )
    )
    loaded = AgentConversationService().list_turns(
        world_id, conversation.conversation_id
    )[0]
    assert loaded == completed
    assert loaded.completion.answer_context_status == context_status
    assert loaded.completion.citation_map == citation_map


def test_turn_and_draft_round_trip_exact_typed_provenance(
    application_state_dsn: str,
) -> None:
    writer = AgentConversationService()
    world_id = "typed-provenance-world"
    conversation = _new(writer, world_id)
    provenance = _typed_provenance(world_id)
    intent = SubmittedTurnIntentV1(
        world_id=world_id,
        client_thread_id="typed-provenance-thread",
        message="Ask about the pinned plan.",
        surface_id="plan",
        surface_instance_id="plan-pane-7",
        client_work_state="saved_clean",
        primary_work=SubmittedPrimaryWorkIntentV1(
            kind="plan",
            object_id=provenance.primary_work.object_id,
            expected_revision=provenance.primary_work.object_revision,
            expected_revision_n=provenance.primary_work.revision_n,
            expected_content_sha256=provenance.primary_work.content_sha256,
        ),
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    submission = TurnSubmission(
        world_id=world_id,
        conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="Ask about the pinned plan.",
        provenance=provenance,
        submitted_intent_v1=intent,
    )

    accepted = writer.accept_turn(submission)
    assert writer.accept_turn(submission) == accepted
    recovered = AgentConversationService()
    loaded_turn = recovered.list_turns(world_id, conversation.conversation_id)[0]
    assert loaded_turn.provenance == provenance
    assert loaded_turn.provenance.surface_instance_id == "plan-pane-7"
    assert loaded_turn.provenance.primary_work.object_revision == 9
    assert loaded_turn.provenance.primary_work.work_revision_id == (
        provenance.primary_work.work_revision_id
    )
    assert loaded_turn.provenance.primary_work.revision_n == 4
    assert loaded_turn.provenance.supporting_work == provenance.supporting_work
    assert loaded_turn.provenance.selected_object == provenance.selected_object

    different_instance = provenance.model_copy(
        update={"surface_instance_id": "plan-pane-8"}
    )
    assert recovered.accept_turn(
        submission.model_copy(update={"provenance": different_instance})
    ) == accepted

    changed_submitted_basis = (
        {"expected_revision": intent.primary_work.expected_revision + 1},
        {"expected_revision_n": intent.primary_work.expected_revision_n + 1},
        {"expected_content_sha256": "b" * 64},
    )
    for changed_fields in changed_submitted_basis:
        different_intent = intent.model_copy(
            update={
                "primary_work": intent.primary_work.model_copy(
                    update=changed_fields
                )
            }
        )
        with pytest.raises(
            ApplicationStateConflictError, match="different submitted intent"
        ):
            recovered.accept_turn(
                submission.model_copy(update={"submitted_intent_v1": different_intent})
            )

    save = DraftSave(
        world_id=world_id,
        conversation_id=conversation.conversation_id,
        draft_id=uuid4(),
        expected_revision=0,
        body="A recoverable composer draft.",
        provenance=provenance,
    )
    draft = writer.save_draft(save)
    assert writer.save_draft(save) == draft
    loaded_draft = AgentConversationService().get_draft(
        world_id, conversation.conversation_id, save.draft_id
    )
    assert loaded_draft.provenance == provenance
    assert loaded_draft.provenance.surface_instance_id == "plan-pane-7"


def test_playable_target_receipt_persists_and_replays_immutable_plan_basis(
    application_state_dsn: str,
) -> None:
    writer = AgentConversationService()
    world_id = "playable-target-receipt-world"
    conversation = _new(writer, world_id)
    work_revision_id = uuid4()
    target = SubmittedPlanPlayableTargetV1(
        schema="dmb_plan_playable_target_v1", kind="scene", id="scene:arrival"
    )
    receipt = PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind="scene",
        id="scene:arrival",
        marker_grammar_version="v1",
    )
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id="plan-main",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id="plan-target-1",
            revision="7",
            content_sha256="b" * 64,
            object_revision=7,
            work_revision_id=work_revision_id,
            revision_n=4,
        ),
        supporting_work=[encode_plan_playable_target_reference(receipt)],
        selected_object=HistoricalReference(resolution="absent"),
    )
    intent = SubmittedTurnIntentV1(
        world_id=world_id,
        client_thread_id="target-thread",
        message="What happens at arrival?",
        surface_id="plan",
        surface_instance_id="plan-main",
        client_work_state="saved_dirty",
        primary_work=SubmittedPrimaryWorkIntentV1(
            kind="plan",
            object_id="plan-target-1",
            expected_revision=7,
            expected_revision_n=4,
            expected_content_sha256="b" * 64,
        ),
        playable_target=target,
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    submission = TurnSubmission(
        world_id=world_id,
        conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text=intent.message,
        provenance=provenance,
        submitted_intent_v1=intent,
    )

    accepted = writer.accept_turn(submission)
    recovered = AgentConversationService()
    loaded = recovered.list_turns(world_id, conversation.conversation_id)[0]
    assert loaded.provenance == provenance
    assert loaded.provenance.primary_work.work_revision_id == work_revision_id
    assert loaded.provenance.supporting_work == [encode_plan_playable_target_reference(receipt)]
    assert recovered.reconcile_turn(world_id, submission.idempotency_key, intent) == accepted

    claim = recovered.claim_turn(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
        lease_seconds=60,
    )
    assert claim.disposition == "claimed"
    completed = recovered.complete_turn(TurnResult(
        world_id=world_id,
        conversation_id=conversation.conversation_id,
        turn_id=accepted.turn_id,
        expected_revision=claim.turn.revision,
        assistant_text="The arrival is guarded.",
    ))
    fresh = AgentConversationService()
    replay = fresh.reconcile_turn(world_id, submission.idempotency_key, intent)
    assert replay == completed
    assert replay.provenance == provenance
    for changed_intent in (
        intent.model_copy(update={
            "playable_target": SubmittedPlanPlayableTargetV1(
                schema="dmb_plan_playable_target_v1", kind="scene", id="scene:departure"
            )
        }),
        intent.model_copy(update={
            "primary_work": intent.primary_work.model_copy(
                update={"expected_content_sha256": "c" * 64}
            )
        }),
    ):
        with pytest.raises(ApplicationStateConflictError, match="different submitted intent"):
            fresh.reconcile_turn(world_id, submission.idempotency_key, changed_intent)


def test_fresh_service_instance_reads_committed_world_conversation(
    application_state_dsn: str,
) -> None:
    writer = AgentConversationService()
    receipt = _new(writer, "restart-recovery-world")
    submission = TurnSubmission(
        world_id="restart-recovery-world",
        conversation_id=receipt.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="Keep this after process restart.",
        provenance=_provenance("restart-recovery-world"),
        submitted_intent_v1=SubmittedTurnIntentV1(
            world_id="restart-recovery-world",
            client_thread_id="restart-thread",
            message="Keep this after process restart.",
            surface_id="index",
            surface_instance_id="index-main",
            client_work_state="none",
            primary_work=None,
            graph_request=SubmittedGraphRequestIntentV1(mode="none"),
            graph_selection=None,
        ),
    )
    accepted = writer.accept_turn(submission)

    recovered = AgentConversationService()
    assert (
        recovered.get_active_conversation("restart-recovery-world").conversation_id
        == receipt.conversation_id
    )
    turns = recovered.list_turns("restart-recovery-world", receipt.conversation_id)
    assert len(turns) == 1 and turns[0].turn_id == accepted.turn_id
    assert turns[0].provenance.supporting_work[0].content_sha256 == "f" * 64


def test_distinct_concurrent_new_commands_are_fenced_by_pointer_revision(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    first = _new(service, "concurrent-new-world")
    pointer = service.get_world_pointer("concurrent-new-world")
    requests = [
        ConversationCommand(
            world_id="concurrent-new-world",
            command_id=uuid4(),
            expected_pointer_revision=pointer.revision,
            expected_active_conversation_id=pointer.active_conversation_id,
        )
        for _ in range(2)
    ]

    def run(command: ConversationCommand):
        try:
            return service.new_conversation(command)
        except ApplicationStateConflictError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, requests))
    assert sum(not isinstance(value, Exception) for value in outcomes) == 1
    assert (
        sum(isinstance(value, ApplicationStateConflictError) for value in outcomes) == 1
    )
    active = service.get_active_conversation("concurrent-new-world")
    assert active is not None
    assert active.conversation_id != first.conversation_id
    assert len(service.list_conversations("concurrent-new-world")) == 2


def test_duplicate_turn_submission_concurrent_replay_returns_one_turn(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    conversation = _new(service, "concurrent-turn-replay-world")
    request = TurnSubmission(
        world_id="concurrent-turn-replay-world",
        conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="The same accepted submission.",
        provenance=_provenance("concurrent-turn-replay-world"),
        submitted_intent_v1=SubmittedTurnIntentV1(
            world_id="concurrent-turn-replay-world",
            client_thread_id="concurrent-turn-replay-thread",
            message="The same accepted submission.",
            surface_id="index",
            surface_instance_id="index-main",
            client_work_state="none",
            primary_work=None,
            graph_request=SubmittedGraphRequestIntentV1(mode="none"),
            graph_selection=None,
        ),
    )
    both_missed_receipt = Barrier(2)

    def miss_then_accept(_unused: int):
        assert service.reconcile_turn(
            "concurrent-turn-replay-world",
            request.idempotency_key,
            request.submitted_intent_v1,
        ) is None
        both_missed_receipt.wait()
        return service.accept_turn(request)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(miss_then_accept, range(2)))
    assert results[0].turn_id == results[1].turn_id
    assert results[0].sequence == results[1].sequence == 1
    assert (
        len(
            service.list_turns(
                "concurrent-turn-replay-world", conversation.conversation_id
            )
        )
        == 1
    )


def test_concurrent_both_miss_turn_claim_allows_one_semantic_intent(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    world_id = "concurrent-turn-conflict-world"
    conversation = _new(service, world_id)
    base_intent = SubmittedTurnIntentV1(
        world_id=world_id,
        client_thread_id="race-thread",
        message="First valid intent.",
        surface_id="index",
        surface_instance_id="index-main",
        client_work_state="none",
        primary_work=None,
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    base = TurnSubmission(
        world_id=world_id,
        conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text=base_intent.message,
        provenance=_provenance(world_id),
        submitted_intent_v1=base_intent,
    )
    conflicting_intent = base_intent.model_copy(
        update={"message": "Different valid intent."}
    )
    conflicting = base.model_copy(
        update={
            "user_text": conflicting_intent.message,
            "submitted_intent_v1": conflicting_intent,
        }
    )
    both_missed_receipt = Barrier(2)

    def miss_then_claim(submission: TurnSubmission):
        assert service.reconcile_turn(
            world_id,
            submission.idempotency_key,
            submission.submitted_intent_v1,
        ) is None
        both_missed_receipt.wait()
        try:
            return service.accept_turn(submission)
        except ApplicationStateConflictError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(miss_then_claim, (base, conflicting)))

    assert sum(isinstance(item, ApplicationStateConflictError) for item in outcomes) == 1
    assert sum(not isinstance(item, ApplicationStateConflictError) for item in outcomes) == 1
    turns = service.list_turns(world_id, conversation.conversation_id)
    assert len(turns) == 1
    assert turns[0].user_text in {base_intent.message, conflicting_intent.message}


def test_concurrent_route_both_miss_dispatches_provider_once(
    application_state_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from threading import Barrier, Lock
    from time import sleep

    from fastapi import HTTPException

    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.agent_runtime import (
        AgentRuntimeDescriptor,
        AgentRuntimeResult,
    )
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    world = create_world_container(tmp_path, name="Concurrent Receipt World")
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    service = AgentConversationService()
    both_missed = Barrier(2)
    original_reconcile = service.reconcile_turn

    def synchronized_reconcile(*args: Any, **kwargs: Any):
        receipt = original_reconcile(*args, **kwargs)
        both_missed.wait()
        return receipt

    monkeypatch.setattr(service, "reconcile_turn", synchronized_reconcile)

    class CountingRuntime:
        descriptor = AgentRuntimeDescriptor("fake", "fake", "test", "conversation")

        def __init__(self) -> None:
            self.calls = 0
            self.lock = Lock()

        def run(self, _invocation: Any) -> AgentRuntimeResult:
            with self.lock:
                self.calls += 1
            sleep(0.05)
            return AgentRuntimeResult(
                status="ok", final_text="One durable answer.", runtime_session_id=None
            )

    runtime = CountingRuntime()
    app = SimpleNamespace(
        state=SimpleNamespace(
            agent_conversation_service=service,
            agent_turn_runtime=runtime,
        )
    )
    body = AgentTurnRequest.model_validate(
        {
            "schema": "dmb_agent_turn_request_v1",
            "client_thread_id": "concurrent-route-thread",
            "turn_id": "concurrent-route-turn",
            "surface": {"surface_id": "index", "instance_id": "index-main"},
            "owner_scope": {"kind": "world", "world_id": world.world_id},
            "primary_work": None,
            "client_work_state": "none",
            "graph_request": {"mode": "none"},
            "graph_selection": None,
            "message": "Dispatch this once.",
        }
    )

    def submit(_index: int):
        try:
            return agent_route.post_agent_turn(body, SimpleNamespace(app=app))
        except HTTPException as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(submit, range(2)))

    assert runtime.calls == 1
    assert sum(isinstance(item, HTTPException) for item in outcomes) <= 1
    responses = [item for item in outcomes if not isinstance(item, HTTPException)]
    assert len(responses) >= 1
    assert all(
        item["conversation"]["conversation_id"]
        == responses[0]["conversation"]["conversation_id"]
        for item in responses
    )
    active = service.get_active_conversation(world.world_id)
    assert active is not None
    turns = service.list_turns(world.world_id, active.conversation_id)
    assert len(turns) == 1
    assert turns[0].status == "completed"


def test_agent_route_persists_shared_world_history_and_provider_segments(
    application_state_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.agent_runtime import (
        AgentRuntimeDescriptor,
        AgentRuntimeResult,
    )
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    assert application_state_dsn
    world = create_world_container(tmp_path, name="Conversation Route World")
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    token = "test-local-operator-token-with-adequate-length"
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)

    class RecordingRuntime:
        descriptor = AgentRuntimeDescriptor("fake", "fake", "test", "conversation")

        def __init__(self) -> None:
            self.invocations = []

        def run(self, invocation):
            self.invocations.append(invocation)
            return AgentRuntimeResult(
                status="ok",
                final_text=f"Answer {len(self.invocations)}.",
                runtime_session_id=f"provider-session-{len(self.invocations)}",
            )

    runtime = RecordingRuntime()

    class RuntimeLookupState:
        lookups = 0

        @property
        def agent_turn_runtime(self):
            self.lookups += 1
            return runtime

    state = RuntimeLookupState()
    app = SimpleNamespace(state=state)
    history_request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": f"/api/live/agent/worlds/{world.world_id}/conversation",
            "raw_path": f"/api/live/agent/worlds/{world.world_id}/conversation".encode(),
            "query_string": b"",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
            "client": ("127.0.0.1", 50000),
            "server": ("test", 80),
            "app": app,
        }
    )
    absent_history = agent_route.get_world_conversation_history(
        world.world_id, history_request, limit=50, before_sequence=None
    )
    assert absent_history.conversation_state == "absent"
    assert absent_history.conversation_id is None
    assert absent_history.active_conversation_id is None
    assert absent_history.pointer_revision == 0
    assert absent_history.turns == []
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as foreign_world_error:
        agent_route.get_world_conversation_history(
            "not-a-managed-world", history_request, limit=50, before_sequence=None
        )
    assert foreign_world_error.value.status_code == 404

    def turn_payload(
        *, surface_id: str, instance_id: str, client_thread_id: str, turn_id: str
    ) -> dict[str, object]:
        return {
            "schema": "dmb_agent_turn_request_v1",
            "client_thread_id": client_thread_id,
            "turn_id": turn_id,
            "surface": {"surface_id": surface_id, "instance_id": instance_id},
            "owner_scope": {"kind": "world", "world_id": world.world_id},
            "primary_work": None,
            "client_work_state": "none",
            "graph_request": {"mode": "none"},
            "graph_selection": None,
            "message": f"Question from {surface_id}.",
        }

    first_payload = turn_payload(
        surface_id="index",
        instance_id="index-main",
        client_thread_id="untrusted-thread-one",
        turn_id="world-turn-one",
    )
    first = agent_route.post_agent_turn(
        AgentTurnRequest.model_validate(first_payload), SimpleNamespace(app=app)
    )
    replay_payload = {**first_payload, "client_thread_id": "different-client-thread"}
    replay = agent_route.post_agent_turn(
        AgentTurnRequest.model_validate(replay_payload), SimpleNamespace(app=app)
    )
    assert state.lookups == 1  # A completed receipt replay skips app runtime lookup.
    with pytest.raises(HTTPException) as conflicting_retry:
        agent_route.post_agent_turn(
            AgentTurnRequest.model_validate(
                {
                    **replay_payload,
                    "message": "Changed request under a reused turn ID.",
                }
            ),
            SimpleNamespace(app=app),
        )
    assert conflicting_retry.value.status_code == 409
    second = agent_route.post_agent_turn(
        AgentTurnRequest.model_validate(
            turn_payload(
                surface_id="plan",
                instance_id="plan-main",
                client_thread_id="third-client-thread",
                turn_id="world-turn-two",
            )
        ),
        SimpleNamespace(app=app),
    )
    assert state.lookups == 2

    assert first["conversation"]["conversation_id"] == replay["conversation"]["conversation_id"]
    assert first["conversation"]["conversation_id"] == second["conversation"]["conversation_id"]
    assert replay["answer"]["text"] == "Answer 1."
    assert len(runtime.invocations) == 2
    assert runtime.invocations[0].run_options.runtime_session_id is None
    assert runtime.invocations[1].run_options.runtime_session_id is None

    history = agent_route.get_world_conversation_history(
        world.world_id, history_request, limit=1, before_sequence=None
    )
    assert str(history.conversation_id) == first["conversation"]["conversation_id"]
    assert history.conversation_state == "active"
    assert [turn.sequence for turn in history.turns] == [2]
    assert history.turns[0].user_text == "Question from plan."
    assert history.turns[0].assistant_text == "Answer 2."
    assert history.turns[0].provenance.surface_instance_id == "plan-main"
    assert history.next_before_sequence == 2

    older = agent_route.get_world_conversation_history(
        world.world_id, history_request, limit=1, before_sequence=2
    )
    assert [turn.sequence for turn in older.turns] == [1]
    assert older.turns[0].user_text == "Question from index."
    assert older.turns[0].assistant_text == "Answer 1."
    assert older.turns[0].provenance.surface_instance_id == "index-main"

    import asyncio

    import httpx
    from fastapi import FastAPI

    service = AgentConversationService()
    http_app = FastAPI()
    http_app.include_router(agent_route.router, prefix="/api/live")
    http_app.state.agent_conversation_service = service
    command_id = uuid4()
    read_before_new = None

    async def create_new_conversation_from_history() -> tuple[
        httpx.Response, httpx.Response, httpx.Response, httpx.Response
    ]:
        transport = httpx.ASGITransport(app=http_app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            history_response = await client.get(
                f"/api/live/agent/worlds/{world.world_id}/conversation",
                headers={"Authorization": f"Bearer {token}"},
            )
            history_body = history_response.json()
            command = {
                "command_id": str(command_id),
                "expected_pointer_revision": history_body["pointer_revision"],
                "expected_active_conversation_id": history_body[
                    "active_conversation_id"
                ],
            }
            new_response = await client.post(
                f"/api/live/agent/worlds/{world.world_id}/conversation/new",
                json=command,
                headers={"Authorization": f"Bearer {token}"},
            )
            replay_response = await client.post(
                f"/api/live/agent/worlds/{world.world_id}/conversation/new",
                json=command,
                headers={"Authorization": f"Bearer {token}"},
            )
            stale_response = await client.post(
                f"/api/live/agent/worlds/{world.world_id}/conversation/new",
                json={
                    **command,
                    "command_id": str(uuid4()),
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            return history_response, new_response, replay_response, stale_response

    read_before_new, new_response, replay_response, stale_response = asyncio.run(
        create_new_conversation_from_history()
    )
    assert read_before_new.status_code == 200, read_before_new.text
    new_body = new_response.json()
    assert new_response.status_code == 200, new_response.text
    assert replay_response.status_code == 200, replay_response.text
    assert replay_response.json() == new_body
    assert stale_response.status_code == 409, stale_response.text
    new_conversation = agent_route.AgentNewConversationResponse.model_validate(new_body)
    assert str(new_conversation.conversation_id) != first["conversation"]["conversation_id"]
    assert new_conversation.active_conversation_id == new_conversation.conversation_id
    absent_history = agent_route.get_world_conversation_history(
        world.world_id, history_request, limit=50, before_sequence=None
    )
    assert absent_history.conversation_state == "active"
    assert absent_history.conversation_id == new_conversation.conversation_id
    assert absent_history.active_conversation_id == new_conversation.conversation_id
    assert absent_history.pointer_revision == new_conversation.pointer_revision
    assert absent_history.turns == []
    post_new = agent_route.post_agent_turn(
        AgentTurnRequest.model_validate(
            turn_payload(
                surface_id="index",
                instance_id="index-main",
                client_thread_id="same-old-thread",
                turn_id="world-turn-after-new-conversation",
            )
        ),
        SimpleNamespace(app=app),
    )
    assert post_new["conversation"]["conversation_id"] == str(
        new_conversation.conversation_id
    )
    assert len(runtime.invocations) == 3
    assert runtime.invocations[2].run_options.runtime_session_id is None


def test_agent_conversation_history_auth_precedes_world_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi import HTTPException

    from apps.live_control_server.routes import agent as agent_route

    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv(
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN",
        "test-local-operator-token-with-adequate-length",
    )
    monkeypatch.setattr(
        agent_route,
        "get_world_container",
        lambda *_args: pytest.fail("World lookup must follow authentication"),
    )
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/live/agent/worlds/foreign-world/conversation",
            "raw_path": b"/api/live/agent/worlds/foreign-world/conversation",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 50000),
            "server": ("test", 80),
            "app": SimpleNamespace(state=SimpleNamespace()),
        }
    )
    with pytest.raises(HTTPException) as error:
        agent_route.get_world_conversation_history(
            "foreign-world", request, limit=50, before_sequence=None
        )
    assert error.value.status_code == 401


def test_late_plan_completion_keeps_frozen_revision_and_plan_segment(
    application_state_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from application_state.content.service import commit_plan, create_world_plan
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.agent_runtime import (
        AgentRuntimeDescriptor,
        AgentRuntimeResult,
    )
    from apps.live_control_server.services.agent_turn_service import (
        _provider_segment_thread_id,
    )
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    assert application_state_dsn
    world = create_world_container(tmp_path, name="Late Plan Completion World")
    plan_a = create_world_plan(title="Plan A", world_id=world.world_id)
    plan_b = create_world_plan(title="Plan B", world_id=world.world_id)
    object_a_v1, revision_a_v1 = commit_plan(
        str(plan_a.work_object_id), "# Plan A v1\n", expected_world_id=world.world_id
    )
    object_b_v1, revision_b_v1 = commit_plan(
        str(plan_b.work_object_id), "# Plan B v1\n", expected_world_id=world.world_id
    )
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    conversation_service = AgentConversationService()

    payload_b = _saved_plan_turn_payload(
        world_id=world.world_id,
        work_object=object_b_v1,
        work_revision=revision_b_v1,
        turn_id="late-test-plan-b",
        message="Plan B question.",
    )

    class PlanSwitchRuntime:
        descriptor = AgentRuntimeDescriptor("fake", "fake", "test", "conversation")

        def __init__(self) -> None:
            self.invocations = []
            self.nested_response = None
            self.revised_response = None
            self.revision_a_v2 = None
            self.object_a_v2 = None
            self.app = None

        def run(self, invocation):
            self.invocations.append(invocation)
            active = conversation_service.get_active_conversation(world.world_id)
            assert active is not None
            visible = conversation_service.list_turns(
                world.world_id, active.conversation_id
            )
            assert visible[-1].status == "running"
            assert visible[-1].user_text in {
                "Plan A question.",
                "Plan B question.",
                "Ask under Plan A revision two.",
            }
            if "Plan A question." in invocation.message:
                self.nested_response = agent_route.post_agent_turn(
                    AgentTurnRequest.model_validate(payload_b),
                    SimpleNamespace(app=self.app),
                )
                self.object_a_v2, self.revision_a_v2 = commit_plan(
                    str(plan_a.work_object_id),
                    "# Plan A v2\n",
                    expected_world_id=world.world_id,
                )
                self.revised_response = agent_route.post_agent_turn(
                    AgentTurnRequest.model_validate(
                        _saved_plan_turn_payload(
                            world_id=world.world_id,
                            work_object=self.object_a_v2,
                            work_revision=self.revision_a_v2,
                            turn_id="late-test-plan-a-v2",
                            message="Ask under Plan A revision two.",
                        )
                    ),
                    SimpleNamespace(app=self.app),
                )
                return AgentRuntimeResult(
                    status="ok",
                    final_text="Answer for Plan A.",
                    runtime_session_id="provider-session-a",
                )
            return AgentRuntimeResult(
                status="ok",
                final_text=(
                    "Answer for Plan A v2."
                    if "Ask under Plan A revision two." in invocation.message
                    else "Answer for Plan B."
                ),
                runtime_session_id="provider-session-b",
            )

    runtime = PlanSwitchRuntime()
    app = SimpleNamespace(
        state=SimpleNamespace(
            agent_turn_runtime=runtime,
            agent_conversation_service=conversation_service,
        )
    )


    runtime.app = app
    payload_a = _saved_plan_turn_payload(
        world_id=world.world_id,
        work_object=object_a_v1,
        work_revision=revision_a_v1,
        turn_id="late-test-plan-a",
        message="Plan A question.",
    )
    response_a = agent_route.post_agent_turn(
        AgentTurnRequest.model_validate(payload_a),
        SimpleNamespace(app=app),
    )

    assert runtime.nested_response is not None
    assert runtime.revised_response is not None
    assert runtime.object_a_v2 is not None
    assert runtime.revision_a_v2 is not None
    assert response_a["conversation"]["conversation_id"] == runtime.nested_response[
        "conversation"
    ]["conversation_id"]
    assert len(runtime.invocations) == 3
    assert runtime.invocations[0].run_options.runtime_session_id is None
    assert runtime.invocations[1].run_options.runtime_session_id is None
    assert runtime.invocations[2].run_options.runtime_session_id is None
    active = conversation_service.get_active_conversation(world.world_id)
    assert active is not None
    turns = conversation_service.list_turns(world.world_id, active.conversation_id)
    assert [turn.sequence for turn in turns] == [1, 2, 3]
    assert [turn.status for turn in turns] == ["completed", "completed", "completed"]
    assert [turn.user_text for turn in turns] == [
        "Plan A question.",
        "Plan B question.",
        "Ask under Plan A revision two.",
    ]
    assert [turn.assistant_text for turn in turns] == [
        "Answer for Plan A.",
        "Answer for Plan B.",
        "Answer for Plan A v2.",
    ]
    assert turns[0].provenance.primary_work.object_id == str(plan_a.work_object_id)
    assert turns[1].provenance.primary_work.object_id == str(plan_b.work_object_id)
    assert turns[0].provenance.primary_work.work_revision_id == revision_a_v1.work_revision_id
    assert turns[1].provenance.primary_work.work_revision_id == revision_b_v1.work_revision_id
    assert turns[0].provenance.primary_work.object_revision == object_a_v1.object_revision
    assert turns[0].provenance.primary_work.revision_n == revision_a_v1.revision_n
    assert turns[0].provenance.primary_work.content_sha256 == revision_a_v1.content_sha256
    assert turns[1].provenance.primary_work.object_revision == object_b_v1.object_revision
    assert turns[1].provenance.primary_work.revision_n == revision_b_v1.revision_n
    assert turns[1].provenance.primary_work.content_sha256 == revision_b_v1.content_sha256

    assert runtime.revised_response["conversation"]["conversation_id"] == str(
        active.conversation_id
    )
    assert runtime.invocations[0].thread_id != runtime.invocations[2].thread_id
    turns = conversation_service.list_turns(world.world_id, active.conversation_id)
    assert len(turns) == 3
    assert turns[0].provenance.primary_work.work_revision_id == revision_a_v1.work_revision_id
    assert turns[2].provenance.primary_work.work_revision_id == runtime.revision_a_v2.work_revision_id
    assert turns[2].provenance.primary_work.object_revision == runtime.object_a_v2.object_revision
    assert turns[2].provenance.primary_work.revision_n == runtime.revision_a_v2.revision_n
    assert turns[2].provenance.primary_work.content_sha256 == runtime.revision_a_v2.content_sha256
    assert turns[0].provenance.primary_work.content_sha256 != turns[2].provenance.primary_work.content_sha256

    payload_a_v2 = _saved_plan_turn_payload(
        world_id=world.world_id,
        work_object=runtime.object_a_v2,
        work_revision=runtime.revision_a_v2,
        turn_id="late-test-plan-a-v2",
        message="Ask under Plan A revision two.",
    )
    revised_segment = _provider_segment_thread_id(
        turns[2].provenance, conversation_id=active.conversation_id
    )
    assert HermesSessionPointerStore(tmp_path / "sessions").revoke_structured_after_continuity_failure(
        owner_kind="world",
        owner_id=world.world_id,
        work_kind="agent_conversation_segment",
        work_id=revised_segment,
        agent_thread_id=revised_segment,
        hermes_session_id="provider-session-b",
    )
    replayed_a_v2 = agent_route.post_agent_turn(
        AgentTurnRequest.model_validate(payload_a_v2), SimpleNamespace(app=app)
    )
    assert replayed_a_v2["answer"]["text"] == "Answer for Plan A v2."
    assert replayed_a_v2["conversation"]["conversation_id"] == runtime.revised_response[
        "conversation"
    ]["conversation_id"]
    assert len(runtime.invocations) == 3


def test_interrupted_provider_attempt_can_retry_same_durable_turn(
    application_state_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.agent_runtime import (
        AgentRuntimeDescriptor,
        AgentRuntimeResult,
    )
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    assert application_state_dsn
    world = create_world_container(tmp_path, name="Interrupted Agent Turn World")
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    service = AgentConversationService()
    payload = {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": "retry-thread",
        "turn_id": "retry-turn-after-interruption",
        "surface": {"surface_id": "index", "instance_id": "index-main"},
        "owner_scope": {"kind": "world", "world_id": world.world_id},
        "primary_work": None,
        "client_work_state": "none",
        "graph_request": {"mode": "none"},
        "graph_selection": None,
        "message": "Persist this before a provider interruption.",
    }

    class ToggleRuntime:
        descriptor = AgentRuntimeDescriptor("fake", "fake", "test", "conversation")

        def __init__(self) -> None:
            self.fail = True
            self.invocations = 0

        def run(self, _invocation):
            self.invocations += 1
            if self.fail:
                raise RuntimeError("fake provider interruption")
            return AgentRuntimeResult(
                status="ok", final_text="Recovered answer.", runtime_session_id=None
            )

    runtime = ToggleRuntime()
    app = SimpleNamespace(
        state=SimpleNamespace(
            agent_turn_runtime=runtime,
            agent_conversation_service=service,
        )
    )
    request = AgentTurnRequest.model_validate(payload)
    with pytest.raises(RuntimeError, match="fake provider interruption"):
        agent_route.post_agent_turn(request, SimpleNamespace(app=app))

    active = service.get_active_conversation(world.world_id)
    assert active is not None
    interrupted = service.list_turns(world.world_id, active.conversation_id)
    assert len(interrupted) == 1
    assert interrupted[0].status == "interrupted"
    assert interrupted[0].attempt == 1
    assert interrupted[0].user_text == payload["message"]

    runtime.fail = False
    retry = agent_route.post_agent_turn(request, SimpleNamespace(app=app))
    assert retry["answer"]["text"] == "Recovered answer."
    assert retry["conversation"]["conversation_id"] == str(active.conversation_id)
    turns = service.list_turns(world.world_id, active.conversation_id)
    assert len(turns) == 1
    assert turns[0].status == "completed"
    assert turns[0].attempt == 2
    assert turns[0].sequence == 1
    assert runtime.invocations == 2


def test_turn_claim_renewal_expiry_reclaim_and_stale_fences(
    application_state_dsn: str,
) -> None:
    assert application_state_dsn
    service = AgentConversationService()
    world_id = "claim-renew-reclaim-world"
    conversation = _new(service, world_id)
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="index",
        primary_work=HistoricalReference(resolution="absent"),
        selected_object=HistoricalReference(resolution="absent"),
    )
    intent = SubmittedTurnIntentV1(
        world_id=world_id,
        client_thread_id="claim-test-thread",
        message="Exercise claim fencing.",
        surface_id="index",
        surface_instance_id="index-home",
        client_work_state="none",
        primary_work=None,
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    accepted = service.accept_turn(
        TurnSubmission(
            world_id=world_id,
            conversation_id=conversation.conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=1,
            user_text=intent.message,
            provenance=provenance,
            submitted_intent_v1=intent,
        )
    )

    first_claim = service.claim_turn(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
        lease_seconds=1,
    )
    assert first_claim.disposition == "claimed"
    pending = service.claim_turn(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=first_claim.turn.revision,
        lease_seconds=1,
    )
    assert pending.disposition == "pending"

    renewed = service.renew_turn_claim(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=first_claim.turn.revision,
        lease_seconds=1,
    )
    assert renewed.revision == first_claim.turn.revision + 1
    stale_result = TurnResult(
        world_id=world_id,
        conversation_id=conversation.conversation_id,
        turn_id=accepted.turn_id,
        expected_revision=first_claim.turn.revision,
        assistant_text="Must not commit on a stale fence.",
    )
    stale_failure = TurnFailure(
        world_id=world_id,
        conversation_id=conversation.conversation_id,
        turn_id=accepted.turn_id,
        expected_revision=first_claim.turn.revision,
        failure_code="stale-before-expiry",
    )
    with pytest.raises(ApplicationStateConflictError):
        service.complete_turn(stale_result)
    with pytest.raises(ApplicationStateConflictError):
        service.fail_turn(stale_failure)

    sleep(1.1)
    reclaimed = service.claim_turn(
        world_id,
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=renewed.revision,
        lease_seconds=1,
    )
    assert reclaimed.disposition == "claimed"
    assert reclaimed.turn.revision == renewed.revision + 1
    assert reclaimed.turn.attempt == first_claim.turn.attempt + 1
    stale_after_reclaim = stale_result.model_copy(
        update={"expected_revision": renewed.revision}
    )
    stale_failure_after_reclaim = stale_failure.model_copy(
        update={"expected_revision": renewed.revision}
    )
    with pytest.raises(ApplicationStateConflictError):
        service.complete_turn(stale_after_reclaim)
    with pytest.raises(ApplicationStateConflictError):
        service.fail_turn(stale_failure_after_reclaim)

    completed = service.complete_turn(
        stale_result.model_copy(
            update={"expected_revision": reclaimed.turn.revision}
        )
    )
    assert completed.status == "completed"
    assert completed.assistant_text == stale_result.assistant_text


def test_graph_execution_v2_source_read_receipt_round_trip_through_fresh_service(
    application_state_dsn: str,
) -> None:
    from application_state.agent_conversation.types import (
        GraphExecutionAccountingV1,
        GraphExecutionPolicyV2,
        GraphSourceReadScopeV2,
        GraphSourceScopeAnchorV2,
        PlanWorldGraphExecution,
        PlanWorldGraphExecutionV2,
        SourceReadAnchorReceiptV2,
        SourceReadAuthorizationEventV2,
        ValidatedSourceReadEventV2,
        graph_execution_policy_digest_v2,
    )

    service = AgentConversationService()
    world_id = "graph-source-read-v2-roundtrip-world"
    conversation = _new(service, world_id)
    plan_revision_id = uuid4()
    playable_target = PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind="beat", id="beat:a", marker_grammar_version="v2",
    )
    submitted_target = SubmittedPlanPlayableTargetV1(
        schema="dmb_plan_playable_target_v1", kind="beat", id="beat:a"
    )
    receipt = _graph_receipt(
        world_id, plan_revision_id, playable_target,
        candidate_evidence_ref_ids=["evidence-1"],
    )
    intent = SubmittedTurnIntentV2(
        world_id=world_id, client_thread_id="source-read-v2-thread",
        message="Read the admitted Graph source.", surface_id="plan",
        surface_instance_id="plan-pane-source-read", client_work_state="saved_clean",
        primary_work=SubmittedPrimaryWorkIntentV1(
            kind="plan", object_id="graph-receipt-plan", expected_revision=3,
            expected_revision_n=2, expected_content_sha256="a" * 64,
        ),
        plan_context_policy=PlanContextPolicyV1(policy="auto_plan_world"),
        playable_target=submitted_target,
        graph_request=SubmittedGraphRequestIntentV1(mode="none"), graph_selection=None,
    )
    provenance = TurnProvenance(
        world_id=world_id, surface_resolution="resolved", surface_id="plan",
        surface_instance_id="plan-pane-source-read",
        primary_work=HistoricalReference(
            resolution="resolved", kind="plan", object_id="graph-receipt-plan",
            content_sha256="a" * 64, object_revision=3,
            work_revision_id=plan_revision_id, revision_n=2,
        ),
        supporting_work=[encode_plan_playable_target_reference(playable_target)],
        selected_object=HistoricalReference(resolution="absent"),
    )
    scope = GraphSourceReadScopeV2(
        retrieval_session_id="retrieval-source-read-1", world_id=world_id,
        campaign_id=None, graph_revision="graph-rev-11",
        admitted_anchors=[GraphSourceScopeAnchorV2(
            anchor_id="anchor-1", evidence_ref_id="evidence-1",
            source_artifact_id="artifact-1", source_revision_id="source-revision-1",
        )],
    )
    policy = GraphExecutionPolicyV2(
        policy_version="test-policy-v2", allowed_graph_operations=["search_assertions"],
        max_provider_attempts=2, max_graph_operations=0, max_results_per_operation=0,
        max_total_provider_input_tokens=100, max_total_provider_output_tokens=40,
        provider_input_accounting=GraphExecutionAccountingV1(
            kind="exact_token_count", estimator="synthetic-tokenizer",
        ), source_opened=False, source_read_scope=scope,
        max_source_read_calls=2, max_source_read_anchors=2,
        max_source_read_chars=24000, max_chars_per_source_read=12000,
    )
    execution = PlanWorldGraphExecutionV2(
        schema="dmb_agent_plan_world_graph_execution_v2",
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=graph_execution_policy_digest_v2(
            receipt.context_receipt_sha256, policy
        ), policy=policy, events=[],
    )
    submission = TurnSubmission(
        world_id=world_id, conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(), expected_conversation_revision=1,
        user_text=intent.message, provenance=provenance, submitted_intent_v2=intent,
        graph_context_receipt=receipt, graph_context_execution=execution,
    )
    accepted = service.accept_turn(submission)
    fresh = AgentConversationService()
    loaded = fresh.list_turns(world_id, conversation.conversation_id)[0]
    assert isinstance(loaded.graph_context_execution, PlanWorldGraphExecution)
    assert loaded.graph_context_execution == execution

    claimed = fresh.claim_turn(
        world_id, conversation.conversation_id, accepted.turn_id,
        expected_revision=accepted.revision, lease_seconds=60,
    )
    call_id = uuid4()
    authorization = SourceReadAuthorizationEventV2(
        event_id=uuid4(), sequence=0, kind="source_read_authorized_v2",
        read_call_id=call_id, context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        retrieval_session_id=scope.retrieval_session_id, world_id=world_id,
        campaign_id=None, graph_revision=scope.graph_revision,
        anchors=scope.admitted_anchors, max_chars=12000,
    )
    authorized, fresh_auth = fresh.authorize_source_read(
        world_id, conversation.conversation_id, accepted.turn_id,
        expected_revision=claimed.turn.revision, expected_attempt=claimed.turn.attempt,
        authorization=authorization,
    )
    assert fresh_auth is True
    result_event = ValidatedSourceReadEventV2(
        event_id=uuid4(), sequence=1, kind="validated_source_read_v2",
        read_call_id=call_id, receipts=[SourceReadAnchorReceiptV2(
            source_read_id="source-read:round-trip", anchor_id="anchor-1",
            evidence_ref_id="evidence-1", source_artifact_id="artifact-1",
            source_revision_id="source-revision-1", outcome="partial",
            content_sha256="b" * 64, line_start=3, line_end=7,
            returned_chars=41, truncated=True,
            evidence_sufficiency_status="insufficient",
        )],
    )
    recorded, fresh_result = fresh.record_validated_source_read(
        world_id, conversation.conversation_id, accepted.turn_id,
        expected_revision=authorized.revision, expected_attempt=claimed.turn.attempt,
        receipt=result_event,
    )
    assert fresh_result is True
    duplicate, inserted = fresh.record_validated_source_read(
        world_id, conversation.conversation_id, accepted.turn_id,
        expected_revision=recorded.revision, expected_attempt=claimed.turn.attempt,
        receipt=result_event,
    )
    assert inserted is False
    assert duplicate.graph_context_execution == recorded.graph_context_execution
    reload = AgentConversationService().list_turns(world_id, conversation.conversation_id)[0]
    assert reload.graph_context_execution == recorded.graph_context_execution
    assert reload.graph_context_execution.events[-1] == result_event
    serialized_read = reload.graph_context_execution.model_dump(mode="json", by_alias=True)["events"][-1]["receipts"][0]
    assert "content" not in serialized_read

    from alembic import command

    from application_state.cli import alembic_config
    with pytest.raises(RuntimeError, match="refusing to downgrade while V2 Graph execution"):
        command.downgrade(alembic_config(), "20261005_0017")
    assert _current_and_head(application_state_dsn) == ("20261008_0019", "20261008_0019")
    assert AgentConversationService().list_turns(world_id, conversation.conversation_id)[0] == reload


def test_read_only_reset_receipt_actual_repository_route(application_state_dsn, monkeypatch):
    import asyncio
    import httpx
    import psycopg
    from fastapi import FastAPI
    from application_state.agent_conversation.types import ArchiveCommand, request_fingerprint
    from apps.live_control_server.routes import agent as route
    service = AgentConversationService()
    command = ConversationCommand(world_id="status-world", command_id=uuid4(), expected_pointer_revision=0, expected_active_conversation_id=None)
    first = service.new_conversation(command)
    next_command = ConversationCommand(world_id=command.world_id, command_id=uuid4(), expected_pointer_revision=first.pointer_revision, expected_active_conversation_id=first.conversation_id)
    later = service.new_conversation(next_command)
    assert AgentConversationService().get_new_conversation_receipt(command) == first
    missing = command.model_copy(update={"world_id": "status-missing"})
    assert service.get_new_conversation_receipt(missing) is None
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM agent.world_state WHERE world_id=%s", (missing.world_id,)).fetchone()[0] == 0
    with pytest.raises(ApplicationStateConflictError):
        service.get_new_conversation_receipt(command.model_copy(update={"expected_pointer_revision": 1}))
    with pytest.raises(ApplicationStateConflictError):
        service.get_new_conversation_receipt(command.model_copy(update={"expected_active_conversation_id": uuid4()}))
    assert service.new_conversation(command) == first
    assert service.get_world_pointer(command.world_id).active_conversation_id == later.conversation_id
    archive_command = ArchiveCommand(world_id=command.world_id, command_id=uuid4(), expected_pointer_revision=later.pointer_revision, expected_active_conversation_id=later.conversation_id, conversation_id=later.conversation_id)
    service.archive_conversation(archive_command)
    with pytest.raises(ApplicationStateConflictError):
        service.get_new_conversation_receipt(ConversationCommand(**archive_command.model_dump(exclude={"conversation_id"})))
    monkeypatch.setattr(route, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(route, "_conversation_service", lambda request: AgentConversationService())
    app = FastAPI()
    app.include_router(route.router, prefix="/api/live")
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            url = f"/api/live/agent/worlds/{command.world_id}/conversation/commands/{command.command_id}"
            query = "?expected_pointer_revision=0&expected_active_conversation_id=null"
            response = await client.get(url + query)
            assert response.status_code == 200, response.text
            assert response.json()["request_fingerprint"] == request_fingerprint(command)
            assert response.json()["receipt"]["conversation_id"] == str(first.conversation_id)
            for suffix in ("", query+"&extra=x", query+"&expected_pointer_revision=0", query.replace("null", "invalid")):
                assert (await client.get(url+suffix)).status_code == 422
            assert (await client.get(url+query.replace("revision=0", "revision=1"))).status_code == 409
            assert (await client.get(url.replace(command.world_id, missing.world_id)+query)).json()["status"] == "absent"
    asyncio.run(exercise())


def _resolution_request(command, *, revision=0, conversation=None):
    from application_state.agent_conversation.types import CommandResolutionRequestV1
    return CommandResolutionRequestV1(resolution_operation_id=uuid4(), original_command=command,
        expected_current_pointer_revision=revision, expected_current_active_conversation_id=conversation)


@pytest.mark.parametrize("winner", ["old", "retire"])
def test_terminal_reset_actual_lock_race_and_delayed_post(application_state_dsn, monkeypatch, winner):
    import threading
    import psycopg
    from application_state.agent_conversation import service as owner
    command = ConversationCommand(world_id="terminal-race-world", command_id=uuid4(), expected_pointer_revision=0, expected_active_conversation_id=None)
    request = _resolution_request(command)
    locked, release = threading.Event(), threading.Event()
    original_lock = owner._lock_pointer
    def gated_lock(conn, world):
        pointer = original_lock(conn, world)
        if threading.current_thread().name == winner:
            locked.set()
            assert release.wait(10)
        return pointer
    monkeypatch.setattr(owner, "_lock_pointer", gated_lock)
    def old():
        threading.current_thread().name = "old"
        try:
            return AgentConversationService().new_conversation(command)
        except ApplicationStateConflictError as exc:
            return str(exc)
    def retire():
        threading.current_thread().name = "retire"
        return AgentConversationService().resolve_new_conversation(request, actor="test-gm")
    functions = {"old": old, "retire": retire}
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(functions[winner])
        assert locked.wait(10)
        second = pool.submit(functions["retire" if winner == "old" else "old"])
        release.set()
        values = [first.result(timeout=20), second.result(timeout=20)]
    record = next(value for value in values if hasattr(value, "outcome"))
    service = AgentConversationService()
    pointer = service.get_world_pointer(command.world_id)
    assert record.outcome == ("confirmed" if winner == "old" else "retired")
    assert service.get_command_resolution(request) == record
    assert service.resolve_new_conversation(request, actor="different-later-gm") == record
    if winner == "retire":
        assert "new_conversation_request_retired" in values
        assert pointer.revision == 0 and pointer.active_conversation_id is None
        fresh = service.new_conversation(command.model_copy(update={"command_id": uuid4()}))
        with pytest.raises(ApplicationStateConflictError, match="request_retired"):
            service.new_conversation(command)
        assert service.get_world_pointer(command.world_id).active_conversation_id == fresh.conversation_id
        assert service.resolve_new_conversation(request, actor="test-gm") == record
        different = request.model_copy(update={"resolution_operation_id": uuid4()})
        with pytest.raises(ApplicationStateConflictError, match="use_original_resolution_record"):
            service.resolve_new_conversation(different, actor="test-gm")
        with pytest.raises(ApplicationStateConflictError, match="different binding"):
            service.resolve_new_conversation(request.model_copy(update={"expected_current_pointer_revision": 1}), actor="test-gm")
    else:
        assert pointer.revision == 1
        assert service.new_conversation(command) == record.confirmed_receipt
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM agent.command_resolution WHERE world_id=%s", (command.world_id,)).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM agent.conversation WHERE world_id=%s", (command.world_id,)).fetchone()[0] == 1


@pytest.mark.parametrize("outcome", ["confirmed", "retired", "submitted_binding_blocked"])
def test_terminal_records_fresh_readback_immutable_and_downgrade_refused(application_state_dsn, outcome):
    import psycopg
    from alembic import command as migration
    from application_state.cli import alembic_config
    from pydantic import ValidationError
    service = AgentConversationService()
    original = ConversationCommand(world_id="terminal-record-world", command_id=uuid4(), expected_pointer_revision=0, expected_active_conversation_id=None)
    occupied = None
    if outcome != "retired":
        occupied = service.new_conversation(original)
    submitted = original if outcome != "submitted_binding_blocked" else original.model_copy(update={"expected_pointer_revision": 9})
    request = _resolution_request(submitted)
    record = service.resolve_new_conversation(request, actor="test-gm")
    assert record.outcome == outcome
    assert AgentConversationService().get_command_resolution(request) == record
    assert service.resolve_new_conversation(request, actor="test-gm") == record
    with pytest.raises(ValidationError, match="digest mismatch"):
        type(record).model_validate({**record.model_dump(mode="json", by_alias=True), "actor": "tampered"})
    if occupied:
        assert service.new_conversation(original) == occupied
    if outcome == "submitted_binding_blocked":
        blocked = record.occupied_receipt.model_dump(mode="json")
        assert "conversation_id" not in blocked and "active_conversation_id" not in blocked
        assert str(occupied.conversation_id) not in json.dumps(blocked)
        with pytest.raises(psycopg.Error, match="immutable"):
            with psycopg.connect(application_state_dsn) as conn:
                conn.execute("DELETE FROM agent.command_receipt WHERE world_id=%s AND command_id=%s", (original.world_id, original.command_id))
    for statement in ("DELETE FROM agent.command_resolution", "UPDATE agent.command_resolution SET outcome=outcome"):
        with pytest.raises(psycopg.Error, match="immutable"):
            with psycopg.connect(application_state_dsn) as conn:
                conn.execute(statement)
    with pytest.raises(Exception, match="downgrade refused"):
        migration.downgrade(alembic_config(), "20261007_0018")
    assert _current_and_head(application_state_dsn) == ("20261008_0019", "20261008_0019")
    assert service.get_command_resolution(request) == record


def test_terminal_empty_ledger_downgrade_and_nonterminal_cas_rolls_back(application_state_dsn):
    import psycopg
    from alembic import command as migration
    from application_state.cli import alembic_config
    original = ConversationCommand(world_id="terminal-missing-world", command_id=uuid4(), expected_pointer_revision=0, expected_active_conversation_id=None)
    request = _resolution_request(original, revision=1)
    with pytest.raises(ApplicationStateConflictError, match="changed"):
        AgentConversationService().resolve_new_conversation(request, actor="test-gm")
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM agent.world_state WHERE world_id=%s", (original.world_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM agent.command_resolution").fetchone()[0] == 0
    migration.downgrade(alembic_config(), "20261007_0018")
    assert _current_and_head(application_state_dsn) == ("20261007_0018", "20261008_0019")
    migration.upgrade(alembic_config(), "head")
    assert _current_and_head(application_state_dsn) == ("20261008_0019", "20261008_0019")


def test_terminal_resolution_actual_http_binding_readback_and_auth(application_state_dsn, monkeypatch):
    import asyncio
    import httpx
    from fastapi import FastAPI, HTTPException
    from apps.live_control_server.routes import agent as route
    command = ConversationCommand(world_id="terminal-http-world", command_id=uuid4(), expected_pointer_revision=0, expected_active_conversation_id=None)
    request = _resolution_request(command)
    monkeypatch.setattr(route, "enforce_native_graph_gm", lambda _request: SimpleNamespace(subject="http-gm"))
    monkeypatch.setattr(route, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(route, "_conversation_service", lambda _request: AgentConversationService())
    app = FastAPI()
    app.include_router(route.router, prefix="/api/live")
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            root = f"/api/live/agent/worlds/{command.world_id}/conversation/commands/{command.command_id}"
            query = "?original_pointer_revision=0&original_active_conversation_id=null&current_pointer_revision=0&current_active_conversation_id=null"
            status_url = root + "/resolutions/" + str(request.resolution_operation_id)
            assert (await client.get(status_url+query)).json()["status"] == "absent"
            body = request.model_dump(mode="json", by_alias=True)
            response = await client.post(root+"/resolve", json=body)
            assert response.status_code == 200, response.text
            assert response.json()["record"]["outcome"] == "retired"
            assert (await client.get(status_url+query)).json() == response.json()
            assert (await client.post(root+"/resolve", json=body)).json() == response.json()
            assert (await client.get(status_url+query+"&extra=x")).status_code == 422
            assert (await client.get(status_url+query.replace("revision=0", "revision=1"))).status_code == 409
            different = request.model_copy(update={"resolution_operation_id": uuid4()})
            conflict = await client.post(root+"/resolve", json=different.model_dump(mode="json", by_alias=True))
            assert conflict.status_code == 409 and conflict.json()["detail"]["code"] == "use_original_resolution_record"
            assert (await client.post(root.replace(command.world_id,"other-world")+"/resolve", json=body)).status_code == 422
            old = await client.post(f"/api/live/agent/worlds/{command.world_id}/conversation/new", json={"schema":"dmb_agent_new_conversation_v1", "command_id":str(command.command_id), "expected_pointer_revision":0,"expected_active_conversation_id":None})
            assert old.status_code == 409 and old.json()["detail"]["code"] == "new_conversation_request_retired"
            def reject(_request):
                raise HTTPException(status_code=403, detail="GM required")
            monkeypatch.setattr(route, "enforce_native_graph_gm", reject)
            monkeypatch.setattr(route, "_verified_world_id", lambda _world: pytest.fail("lookup before auth"))
            assert (await client.post(root+"/resolve", json=body)).status_code == 403
            assert (await client.get(status_url+query)).status_code == 403
    asyncio.run(exercise())


@pytest.mark.parametrize("unavailable", [False, True])
def test_selected_source_scope_jsonb_and_legacy_roundtrip(application_state_dsn, tmp_path, monkeypatch, unavailable):
    from tests.test_agent_turn_route import _selected_consumer_context
    from apps.live_control_server.services.agent_turn_service import _conversation_provenance, _submitted_turn_intent
    from application_state.agent_conversation.types import GraphSelectedSourceReadScopeV2, graph_execution_policy_digest_v2
    body, work, bootstrap, receipt, execution, _members = _selected_consumer_context(tmp_path,monkeypatch,unavailable=unavailable)
    service = AgentConversationService()
    conversation = service.new_conversation(ConversationCommand(world_id=work.world_id,command_id=uuid4(),expected_pointer_revision=0,expected_active_conversation_id=None))
    provenance = _conversation_provenance(body,world_id=work.world_id,work=work,graph_scope=bootstrap.world_scope,graph_envelope=bootstrap.graph_envelope)
    request = TurnSubmission(world_id=work.world_id,conversation_id=conversation.conversation_id,idempotency_key=uuid4(),expected_conversation_revision=1,
        user_text=body.message,provenance=provenance,submitted_intent_v2=_submitted_turn_intent(body,world_id=work.world_id),graph_context_receipt=receipt,graph_context_execution=execution)
    accepted = service.accept_turn(request)
    readback = AgentConversationService().list_turns(work.world_id,conversation.conversation_id)[0]
    assert readback.graph_context_execution.model_dump(mode='json',by_alias=True)==execution.model_dump(mode='json',by_alias=True)
    assert isinstance(readback.graph_context_execution.policy.source_read_scope,GraphSelectedSourceReadScopeV2)
    assert service.accept_turn(request).turn_id==accepted.turn_id
    # Legacy scopes must not gain the required selected commitment or change digest.
    from application_state.agent_conversation.types import GraphSourceReadScopeV2, GraphExecutionPolicyV2, GraphExecutionAccountingV1
    old_scope = GraphSourceReadScopeV2(retrieval_session_id='legacy',world_id=work.world_id,campaign_id=None,graph_revision=bootstrap.world_scope.revision_id,
        admitted_anchors=list(bootstrap.source_scope_anchors))
    old_policy = GraphExecutionPolicyV2(policy_version='plan_world_graph_execution_v1',allowed_graph_operations=['expand_graph_retrieval'],
        max_provider_attempts=4,max_graph_operations=8,max_results_per_operation=512,max_total_provider_input_tokens=131072,max_total_provider_output_tokens=8192,
        provider_input_accounting=GraphExecutionAccountingV1(kind='conservative_upper_bound',estimator='utf8_json_bytes_plus_64_per_node_v1'),source_opened=False,
        source_read_scope=old_scope,max_source_read_calls=0 if unavailable else 8,max_source_read_anchors=0 if unavailable else 8,
        max_source_read_chars=0 if unavailable else 96000,max_chars_per_source_read=12000)
    encoded=old_policy.model_dump(mode='json',by_alias=True)
    assert 'selected_index_commitment' not in encoded['source_read_scope']
    restored=GraphExecutionPolicyV2.model_validate(encoded)
    assert restored.model_dump(mode='json',by_alias=True)==encoded
    assert graph_execution_policy_digest_v2(receipt.context_receipt_sha256,old_policy)==graph_execution_policy_digest_v2(receipt.context_receipt_sha256,restored)
    legacy_root = tmp_path/'legacy'
    legacy_root.mkdir()
    legacy_body,legacy_work,legacy_boot,legacy_receipt,legacy_execution,_ = _selected_consumer_context(legacy_root,monkeypatch,legacy=True)
    assert legacy_receipt.graph_packet.selection_policy_version == 'parent_initial_retrieval_with_bounded_source_index_v1'
    active = service.get_active_conversation(legacy_work.world_id)
    if active is None:
        receipt_new = service.new_conversation(ConversationCommand(world_id=legacy_work.world_id,command_id=uuid4(),expected_pointer_revision=0,expected_active_conversation_id=None))
        active = service.get_active_conversation(legacy_work.world_id)
        assert active.conversation_id == receipt_new.conversation_id
    legacy_submission = TurnSubmission(world_id=legacy_work.world_id,conversation_id=active.conversation_id,idempotency_key=uuid4(),expected_conversation_revision=active.revision,
        user_text=legacy_body.message,provenance=_conversation_provenance(legacy_body,world_id=legacy_work.world_id,work=legacy_work,graph_scope=legacy_boot.world_scope,graph_envelope=legacy_boot.graph_envelope),
        submitted_intent_v2=_submitted_turn_intent(legacy_body,world_id=legacy_work.world_id),graph_context_receipt=legacy_receipt,graph_context_execution=legacy_execution)
    legacy_turn = service.accept_turn(legacy_submission)
    legacy_loaded = next(turn for turn in AgentConversationService().list_turns(legacy_work.world_id,active.conversation_id) if turn.turn_id==legacy_turn.turn_id)
    assert legacy_loaded.graph_context_execution.model_dump_json(by_alias=True)==legacy_execution.model_dump_json(by_alias=True)
    assert not isinstance(legacy_loaded.graph_context_execution.policy.source_read_scope,GraphSelectedSourceReadScopeV2)
    assert set(legacy_loaded.graph_context_execution.policy.source_read_scope.model_dump(mode='json',by_alias=True))=={'schema','retrieval_session_id','world_id','campaign_id','graph_revision','admitted_anchors'}
