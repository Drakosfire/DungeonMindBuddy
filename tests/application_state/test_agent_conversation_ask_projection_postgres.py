from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import repository as repo
from application_state.agent_conversation import service as service_module
from application_state.agent_conversation.types import (
    ConversationCommand,
    PlanContextPolicyV1,
    PlanPlayableTargetReceiptV1,
    PlanWorldGraphCitationMapV1,
    PlanWorldGraphCitationV1,
    PlanWorldGraphClaimSegmentV1,
    PlanWorldGraphCompletionV1,
    PlanWorldGraphContextReceiptV1,
    HistoricalReference,
    PlanAskContextBasis,
    SubmittedPlanPlayableTargetV1,
    SubmittedPrimaryWorkIntentV1,
    SubmittedTurnIntentV2,
    SubmittedGraphRequestIntentV1,
    SubmittedTurnIntentV1,
    TurnFailure,
    TurnProvenance,
    TurnResult,
    TurnSubmission,
    encode_plan_playable_target_reference,
)
from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateValidationError,
)


def _basis(world_id: str = "ask-projection-world") -> PlanAskContextBasis:
    return PlanAskContextBasis(
        world_id=world_id,
        document_id="plan-document-7",
        object_revision=9,
        work_revision_id=uuid4(),
        revision_n=4,
        content_sha256="d" * 64,
    )


def _reference(basis: PlanAskContextBasis) -> HistoricalReference:
    return HistoricalReference(
        resolution="resolved",
        kind="plan",
        object_id=basis.document_id,
        content_sha256=basis.content_sha256,
        object_revision=basis.object_revision,
        work_revision_id=basis.work_revision_id,
        revision_n=basis.revision_n,
    )


def _new_conversation(service: AgentConversationService, world_id: str):
    return service.new_conversation(
        ConversationCommand(
            world_id=world_id,
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )


def _add_turn(
    service: AgentConversationService,
    world_id: str,
    conversation_id,
    basis: PlanAskContextBasis,
    *,
    sequence: int,
    question: str,
    primary: HistoricalReference | None = None,
    supporting: list[HistoricalReference] | None = None,
    surface_resolution: str = "resolved",
    surface_id: str | None = "plan",
    complete: bool = True,
    fail: bool = False,
    running: bool = False,
):
    primary_reference = primary or _reference(basis)
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution=surface_resolution,
        surface_id=surface_id,
        primary_work=primary_reference,
        supporting_work=supporting or [],
        selected_object=HistoricalReference(resolution="absent"),
    )
    intent = SubmittedTurnIntentV1(
        world_id=world_id,
        client_thread_id="ask-projection-test-thread",
        message=question,
        surface_id=surface_id or "index",
        surface_instance_id="ask-projection-test-pane",
        client_work_state="saved_clean" if surface_id == "plan" else "none",
        primary_work=(
            SubmittedPrimaryWorkIntentV1(
                kind="plan",
                object_id=basis.document_id,
                expected_revision=basis.object_revision,
                expected_revision_n=basis.revision_n,
                expected_content_sha256=basis.content_sha256,
            )
            if surface_id == "plan"
            else None
        ),
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    turn = service.accept_turn(
        TurnSubmission(
            world_id=world_id,
            conversation_id=conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=sequence,
            user_text=question,
            provenance=provenance,
            submitted_intent_v1=intent,
        )
    )
    if complete or fail or running:
        claimed = service.begin_turn(
            world_id,
            conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
        )
        if fail:
            return service.fail_turn(
                TurnFailure(
                    world_id=world_id,
                    conversation_id=conversation_id,
                    turn_id=turn.turn_id,
                    expected_revision=claimed.revision,
                    failure_code="test-failure",
                )
            )
        if running:
            return claimed
        if not complete:
            return claimed
        return service.complete_turn(
            TurnResult(
                world_id=world_id,
                conversation_id=conversation_id,
                turn_id=turn.turn_id,
                expected_revision=claimed.revision,
                assistant_text=f"Answer for {question}",
            )
        )
    return turn


def _graph_receipt(
    basis: PlanAskContextBasis,
    target: PlanPlayableTargetReceiptV1,
    *,
    assertion_id: str,
    evidence_ref_id: str,
) -> PlanWorldGraphContextReceiptV1:
    payload = {
        "schema": "dmb_agent_plan_world_graph_context_receipt_v1",
        "receipt_serializer_version": "canonical-json-utf8-v1",
        "context_receipt_sha256": "0" * 64,
        "plan_context_policy": {
            "schema": "dmb_plan_context_policy_v1",
            "policy": "auto_plan_world",
        },
        "plan_basis": basis.model_dump(mode="json"),
        "playable_target": target.model_dump(mode="json", by_alias=True),
        "graph_authority": {
            "managed_world_id": basis.world_id,
            "native_world_id": "native-world-ask-history",
            "binding_version": 1,
            "scope_mode": "world",
            "campaign_id": None,
            "admissibility_version": "ask-history-test-v1",
            "graph_revision": "ask-history-graph-rev-1",
        },
        "graph_packet": {
            "schema": "dmb_plan_world_graph_packet_v1",
            "packet_serializer_version": "canonical-json-utf8-v1",
            "selection_policy_version": "ask-history-selection-v1",
            "evidence_sufficiency_policy_version": "ask-history-sufficiency-v1",
            "retrieval_packet_sha256": "1" * 64,
            "candidate_assertion_ids": [assertion_id],
            "candidate_relationship_ids": [],
            "candidate_evidence_ref_ids": [evidence_ref_id],
            "retrieval_status": "complete",
            "evidence_sufficiency_status": "sufficient",
            "result_limit": 8,
            "coverage_status": "incomplete",
            "truncated": False,
            "omission_reasons": [],
        },
        "assembled_input": {
            "assembler_version": "ask-history-assembler-v1",
            "budget_policy_version": "ask-history-budget-v1",
            "provider_model_name": "synthetic-model",
            "provider_model_version": "1",
            "tokenizer_name": "synthetic-tokenizer",
            "tokenizer_version": "1",
            "provider_envelope_input_tokens": 10,
            "output_token_reserve": 8,
            "context_window_limit": 100,
            "packet_disposition": "included",
            "packet_disposition_reason": None,
            "dispatched_packet_sha256": "2" * 64,
            "dispatched_assertion_ids": [assertion_id],
            "dispatched_relationship_ids": [],
            "dispatched_evidence_ref_ids": [evidence_ref_id],
            "source_token_accounting": [],
            "included_history": [],
            "assembled_input_sha256": "3" * 64,
        },
        "evidence_mode": "metadata_only",
        "source_opened": False,
    }
    encoded = json.dumps(
        {
            key: value
            for key, value in payload.items()
            if key != "context_receipt_sha256"
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    payload["context_receipt_sha256"] = hashlib.sha256(encoded).hexdigest()
    return PlanWorldGraphContextReceiptV1.model_validate(payload)


def _add_graph_ask(
    service: AgentConversationService,
    basis: PlanAskContextBasis,
    conversation_id,
    *,
    sequence: int,
    target_id: str,
    question: str,
    answer: str,
):
    target = PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind="beat",
        id=target_id,
        marker_grammar_version="v2",
    )
    assertion_id = f"assertion-{sequence}"
    evidence_ref_id = f"evidence-{sequence}"
    receipt = _graph_receipt(
        basis,
        target,
        assertion_id=assertion_id,
        evidence_ref_id=evidence_ref_id,
    )
    surface_instance_id = f"plan-ask-pane-{sequence}"
    intent = SubmittedTurnIntentV2(
        world_id=basis.world_id,
        client_thread_id="ask-history-test-thread",
        message=question,
        surface_id="plan",
        surface_instance_id=surface_instance_id,
        client_work_state="saved_clean",
        primary_work=SubmittedPrimaryWorkIntentV1(
            kind="plan",
            object_id=basis.document_id,
            expected_revision=basis.object_revision,
            expected_revision_n=basis.revision_n,
            expected_content_sha256=basis.content_sha256,
        ),
        plan_context_policy=PlanContextPolicyV1(policy="auto_plan_world"),
        playable_target=SubmittedPlanPlayableTargetV1(
            schema="dmb_plan_playable_target_v1", kind="beat", id=target_id
        ),
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    provenance = TurnProvenance(
        world_id=basis.world_id,
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id=surface_instance_id,
        primary_work=_reference(basis),
        supporting_work=[encode_plan_playable_target_reference(target)],
        selected_object=HistoricalReference(resolution="absent"),
    )
    accepted = service.accept_turn(
        TurnSubmission(
            world_id=basis.world_id,
            conversation_id=conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=sequence,
            user_text=question,
            provenance=provenance,
            submitted_intent_v2=intent,
            graph_context_receipt=receipt,
        )
    )
    claimed = service.claim_turn(
        basis.world_id,
        conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
    ).turn
    completion = PlanWorldGraphCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis="committed_plan_plus_world_graph",
        answer_context_status="graph_grounded_partial",
        answer_segments=[
            PlanWorldGraphClaimSegmentV1(
                kind="graph_claim",
                claim_id=f"claim-{sequence}",
                text=answer,
                target_kind="assertion",
                target_id=assertion_id,
                graph_revision="ask-history-graph-rev-1",
                evidence_ref_ids=[evidence_ref_id],
            )
        ],
        citation_map=PlanWorldGraphCitationMapV1(
            context_receipt_sha256=receipt.context_receipt_sha256,
            entries=[
                PlanWorldGraphCitationV1(
                    claim_id=f"claim-{sequence}",
                    target_kind="assertion",
                    target_id=assertion_id,
                    graph_revision="ask-history-graph-rev-1",
                    evidence_ref_ids=[evidence_ref_id],
                    source_opened=False,
                )
            ],
        ),
    )
    return service.complete_turn(
        TurnResult(
            world_id=basis.world_id,
            conversation_id=conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=claimed.revision,
            assistant_text=answer,
            completion=completion,
        )
    )


def _set_accepted_at(application_state_dsn: str, turn_id, accepted_at: datetime) -> None:
    import psycopg

    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET accepted_at = %s WHERE turn_id = %s",
            (accepted_at, turn_id),
        )


def test_exact_basis_filters_every_field_before_limit_and_returns_safe_pairs(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)

    expected_ids = []
    for sequence, question in enumerate(("older match", "newer match"), start=1):
        turn = _add_turn(
            service,
            basis.world_id,
            conversation.conversation_id,
            basis,
            sequence=sequence,
            question=question,
        )
        expected_ids.append(turn.turn_id)

    mismatches = (
        {"document_id": "another-document"},
        {"object_revision": basis.object_revision + 1},
        {"work_revision_id": uuid4()},
        {"revision_n": basis.revision_n + 1},
        {"content_sha256": "e" * 64},
    )
    for offset, changes in enumerate(mismatches, start=3):
        mismatched_basis = basis.model_copy(update=changes)
        _add_turn(
            service,
            basis.world_id,
            conversation.conversation_id,
            basis,
            sequence=offset,
            question=f"mismatch {offset}",
            primary=_reference(mismatched_basis),
        )

    pairs = service.list_completed_plan_ask_context(basis.world_id, basis, limit=2)
    assert [pair.source_record_id for pair in pairs] == expected_ids
    assert [pair.question for pair in pairs] == ["older match", "newer match"]
    assert [pair.source_kind for pair in pairs] == ["ask", "ask"]
    assert [pair.source_sequence for pair in pairs] == [1, 2]
    assert all(pair.answer.startswith("Answer for ") for pair in pairs)
    assert set(pairs[0].model_dump()) == {
        "source_kind",
        "source_sequence",
        "source_record_id",
        "accepted_at",
        "question",
        "answer",
        "history_attribution",
    }
    assert pairs[0].history_attribution is None


def test_scene_a_graph_ask_stays_attributed_when_next_proposal_targets_scene_b(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    scene_a = _add_graph_ask(
        service,
        basis,
        conversation.conversation_id,
        sequence=1,
        target_id="beat:scene-a",
        question="What happened in scene A?",
        answer="Scene A exposed the hidden route.",
    )
    next_proposal_target = "beat:scene-b"

    pairs = AgentConversationService().list_completed_plan_ask_context(
        basis.world_id, basis
    )

    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.source_record_id == scene_a.turn_id
    assert pair.question == "What happened in scene A?"
    assert pair.answer == "Scene A exposed the hidden route."
    attribution = pair.history_attribution
    assert attribution is not None
    assert attribution.source_turn_id == scene_a.turn_id
    assert attribution.source_conversation_id == conversation.conversation_id
    assert attribution.surface_id == "plan"
    assert attribution.surface_instance_id == "plan-ask-pane-1"
    assert attribution.plan_basis == basis
    assert attribution.playable_target is not None
    assert attribution.playable_target.id == "beat:scene-a"
    assert attribution.playable_target.id != next_proposal_target
    assert attribution.answer_basis == "committed_plan_plus_world_graph"
    assert attribution.answer_context_status == "graph_grounded_partial"
    assert attribution.answer_segments[0].text == pair.answer
    assert attribution.citation_map is not None
    assert (
        attribution.citation_map.context_receipt_sha256
        == attribution.context_receipt_sha256
    )
    assert attribution.citation_map.entries[0].target_id == "assertion-1"


@pytest.mark.parametrize("corruption", ["receipt_plan_basis", "target_identity"])
def test_invalid_graph_ask_authority_fails_closed(
    application_state_dsn: str, corruption: str
) -> None:
    import psycopg

    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    turn = _add_graph_ask(
        service,
        basis,
        conversation.conversation_id,
        sequence=1,
        target_id="beat:scene-a",
        question="What happened in scene A?",
        answer="Scene A exposed the hidden route.",
    )
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        if corruption == "receipt_plan_basis":
            from psycopg.types.json import Jsonb

            receipt, completion = conn.execute(
                """
                SELECT graph_context_receipt, completion
                FROM agent.turn
                WHERE turn_id = %s
                """,
                (turn.turn_id,),
            ).fetchone()
            receipt["plan_basis"]["document_id"] = "another-plan-document"
            canonical_receipt = {
                key: value
                for key, value in receipt.items()
                if key != "context_receipt_sha256"
            }
            new_receipt_digest = hashlib.sha256(
                json.dumps(
                    canonical_receipt,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
            receipt["context_receipt_sha256"] = new_receipt_digest
            completion["context_receipt_sha256"] = new_receipt_digest
            completion["citation_map"]["context_receipt_sha256"] = new_receipt_digest
            conn.execute(
                """
                UPDATE agent.turn
                SET graph_context_receipt = %s, completion = %s
                WHERE turn_id = %s
                """,
                (Jsonb(receipt), Jsonb(completion), turn.turn_id),
            )
        else:
            conn.execute(
                """
                UPDATE agent.turn_reference
                SET object_id = %s
                WHERE turn_id = %s
                  AND reference_role = 'supporting'
                  AND kind = 'dmb_plan_playable_target_v1'
                """,
                ("beat:scene-b", turn.turn_id),
            )

    with pytest.raises(ApplicationStateIntegrityError):
        AgentConversationService().list_completed_plan_ask_context(
            basis.world_id, basis
        )


def test_newer_exact_basis_rows_in_another_world_do_not_consume_source_cap(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    target_conversation = _new_conversation(service, basis.world_id)
    target_turns = [
        _add_turn(
            service,
            basis.world_id,
            target_conversation.conversation_id,
            basis,
            sequence=sequence,
            question=f"target world {sequence}",
        )
        for sequence in range(1, 3)
    ]

    other_world_id = "ask-projection-other-world"
    other_basis = basis.model_copy(update={"world_id": other_world_id})
    other_conversation = _new_conversation(service, other_world_id)
    for sequence in range(1, 5):
        other_turn = _add_turn(
            service,
            other_world_id,
            other_conversation.conversation_id,
            other_basis,
            sequence=sequence,
            question=f"other world {sequence}",
        )
        _set_accepted_at(
            application_state_dsn,
            other_turn.turn_id,
            datetime.now(UTC) + timedelta(days=1, seconds=sequence),
        )

    pairs = service.list_completed_plan_ask_context(basis.world_id, basis, limit=2)
    assert [pair.source_record_id for pair in pairs] == [
        turn.turn_id for turn in target_turns
    ]
    assert [pair.question for pair in pairs] == ["target world 1", "target world 2"]


def test_eligibility_precedes_cap_and_newest_six_are_returned_oldest_first(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    now = datetime.now(UTC)

    older_eligible = _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=1,
        question="eligible one",
    )
    _set_accepted_at(application_state_dsn, older_eligible.turn_id, now)
    failed = _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=2,
        question="failed newer",
        fail=True,
    )
    _set_accepted_at(application_state_dsn, failed.turn_id, now + timedelta(seconds=10))
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=3,
        question="accepted newer",
        complete=False,
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=4,
        question="running newer",
        running=True,
    )
    for sequence in range(5, 12):
        turn = _add_turn(
            service,
            basis.world_id,
            conversation.conversation_id,
            basis,
            sequence=sequence,
            question=f"eligible {sequence}",
        )
        _set_accepted_at(
            application_state_dsn,
            turn.turn_id,
            now + timedelta(seconds=sequence),
        )

    pairs = service.list_completed_plan_ask_context(basis.world_id, basis)
    assert len(pairs) == 6
    assert [pair.question for pair in pairs] == [
        "eligible 6",
        "eligible 7",
        "eligible 8",
        "eligible 9",
        "eligible 10",
        "eligible 11",
    ]
    assert [pair.source_sequence for pair in pairs] == [6, 7, 8, 9, 10, 11]


def test_pointer_rotation_and_empty_pointer_never_create_or_leak_history(
    application_state_dsn: str,
) -> None:
    import psycopg

    service = AgentConversationService()
    basis = _basis()
    first = _new_conversation(service, basis.world_id)
    archived_turn = _add_turn(
        service,
        basis.world_id,
        first.conversation_id,
        basis,
        sequence=1,
        question="archived pair",
    )
    second = service.new_conversation(
        ConversationCommand(
            world_id=basis.world_id,
            command_id=uuid4(),
            expected_pointer_revision=1,
            expected_active_conversation_id=first.conversation_id,
        )
    )
    assert service.list_completed_plan_ask_context(basis.world_id, basis) == []
    assert service.get_active_conversation(basis.world_id).conversation_id == second.conversation_id

    empty_world = "ask-projection-no-pointer"
    with psycopg.connect(application_state_dsn) as conn:
        before = conn.execute(
            "SELECT count(*) FROM agent.world_state WHERE world_id = %s", (empty_world,)
        ).fetchone()[0]
    assert service.list_completed_plan_ask_context(
        empty_world, _basis(empty_world)
    ) == []
    with psycopg.connect(application_state_dsn) as conn:
        after = conn.execute(
            "SELECT count(*) FROM agent.world_state WHERE world_id = %s", (empty_world,)
        ).fetchone()[0]
    assert before == after == 0
    assert archived_turn.turn_id not in {
        pair.source_record_id
        for pair in service.list_completed_plan_ask_context(basis.world_id, basis)
    }


def test_equal_acceptance_times_are_stably_ordered_by_source_sequence(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    turns = [
        _add_turn(
            service,
            basis.world_id,
            conversation.conversation_id,
            basis,
            sequence=sequence,
            question=f"tied {sequence}",
        )
        for sequence in range(1, 4)
    ]
    tied_at = datetime(2026, 10, 3, tzinfo=UTC)
    for turn in turns:
        _set_accepted_at(application_state_dsn, turn.turn_id, tied_at)

    pairs = service.list_completed_plan_ask_context(basis.world_id, basis)
    assert [pair.source_sequence for pair in pairs] == [1, 2, 3]
    assert [pair.source_record_id for pair in pairs] == [turn.turn_id for turn in turns]


def test_supporting_only_incomplete_unresolved_and_wrong_surface_are_excluded(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    basis = _basis()
    conversation = _new_conversation(service, basis.world_id)
    nonmatching_primary = HistoricalReference(
        resolution="unresolved",
        kind="plan",
        object_id=basis.document_id,
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=1,
        question="supporting only",
        primary=nonmatching_primary,
        supporting=[_reference(basis)],
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=2,
        question="absent primary",
        primary=HistoricalReference(resolution="absent"),
    )
    incomplete_primary = HistoricalReference(
        resolution="resolved",
        kind="plan",
        object_id=basis.document_id,
        content_sha256=basis.content_sha256,
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=3,
        question="incomplete typed basis",
        primary=incomplete_primary,
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=4,
        question="wrong surface",
        surface_id="index",
    )
    _add_turn(
        service,
        basis.world_id,
        conversation.conversation_id,
        basis,
        sequence=5,
        question="unresolved surface",
        surface_resolution="unresolved",
        surface_id=None,
    )
    assert service.list_completed_plan_ask_context(basis.world_id, basis) == []


def test_world_mismatch_and_invalid_limits_fail_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AgentConversationService()
    basis = _basis()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("database access must not occur after invalid input")

    monkeypatch.setattr(service_module, "_ready_dsn", fail_if_called)
    with pytest.raises(ApplicationStateValidationError, match="must match"):
        service.list_completed_plan_ask_context("different-world", basis)
    for limit in (0, 7, True, 1.5):
        with pytest.raises(ApplicationStateValidationError, match="between 1 and 6"):
            service.list_completed_plan_ask_context(basis.world_id, basis, limit=limit)


def test_repository_projection_uses_one_unlocked_select(monkeypatch: pytest.MonkeyPatch) -> None:
    statements: list[str] = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, statement, _params):
            statements.append(statement)

        def fetchall(self):
            return []

    class Connection:
        def cursor(self, **_kwargs):
            return Cursor()

    result = repo.list_completed_plan_ask_context(
        Connection(), "ask-projection-world", _basis(), limit=6
    )
    assert result == []
    assert len(statements) == 1
    normalized = " ".join(statements[0].lower().split())
    assert normalized.startswith("select ")
    assert " for update" not in normalized
    assert " for share" not in normalized
    assert "t.sequence desc" in normalized
    assert "t.turn_id desc" in normalized
