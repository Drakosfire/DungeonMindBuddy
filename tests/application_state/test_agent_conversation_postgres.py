from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from types import SimpleNamespace
from threading import Barrier
from time import sleep
from uuid import uuid4

import pytest
from starlette.requests import Request

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    ConversationCommand,
    DraftSave,
    HistoricalReference,
    PlanPlayableTargetReceiptV1,
    SubmittedGraphRequestIntentV1,
    SubmittedPlanPlayableTargetV1,
    SubmittedPrimaryWorkIntentV1,
    SubmittedTurnIntentV1,
    TurnProvenance,
    TurnSubmission,
    TurnFailure,
    TurnResult,
    encode_plan_playable_target_reference,
)
from application_state.cli import _current_and_head
from application_state.errors import ApplicationStateConflictError


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


def test_agent_conversation_migration_is_single_current_head(
    application_state_dsn: str,
) -> None:
    current, head = _current_and_head(application_state_dsn)
    assert current == head == "20261003_0014"


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
