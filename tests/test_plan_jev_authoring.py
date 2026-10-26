"""Plan authoring request capture belongs to its exact ordinary Agent intent."""

from uuid import uuid4
import json
import httpx2

import pytest
from pydantic import ValidationError

from tests.application_state.test_plan_authoring import capture_payload
from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services.agent_turn_service import _submitted_turn_intent
from application_state.agent_conversation.types import (
    submitted_turn_intent_fingerprint_v2,
)


def request_payload():
    return dict(
        schema="dmb_agent_turn_request_v1",
        client_thread_id=str(uuid4()),
        turn_id=str(uuid4()),
        surface=dict(surface_id="plan", instance_id="surface:plan:a"),
        owner_scope=dict(kind="world", world_id="world:a"),
        primary_work=dict(
            kind="plan",
            object_id="page:a",
            expected_revision=3,
            expected_revision_n=3,
            expected_content_sha256="a" * 64,
        ),
        client_work_state="saved_dirty",
        graph_request={"mode": "none"},
        graph_selection=None,
        plan_context_policy={"policy": "auto_plan_world"},
        plan_authoring_capture=capture_payload(),
        message="Now draft this Plan and preserve the current working note.",
    )


def test_plan_live_capture_participates_in_the_exact_turn_identity():
    payload = request_payload()
    first = AgentTurnRequest.model_validate(payload)
    intent = _submitted_turn_intent(first, world_id="world:a")
    assert intent.plan_authoring_capture_sha256 == first.plan_authoring_capture.sha256
    initial = submitted_turn_intent_fingerprint_v2(intent)
    payload["plan_authoring_capture"]["draft_generation"] += 1
    second = _submitted_turn_intent(
        AgentTurnRequest.model_validate(payload), world_id="world:a"
    )
    assert initial != submitted_turn_intent_fingerprint_v2(second)


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["plan_authoring_capture"].update(world_id="world:foreign"),
        lambda p: p["plan_authoring_capture"].update(document_id="page:foreign"),
        lambda p: p["plan_authoring_capture"].update(base_revision=2),
        lambda p: p["plan_authoring_capture"].update(base_content_sha256="b" * 64),
        lambda p: p["surface"].update(surface_id="play"),
        lambda p: p.update(plan_context_policy=None),
    ],
)
def test_foreign_or_stale_plan_capture_is_rejected_before_provider_dispatch(change):
    payload = request_payload()
    change(payload)
    with pytest.raises(ValidationError):
        AgentTurnRequest.model_validate(payload)


# Exercise the real GenerationEngine dispatch gate and disposable APP database;
# synthetic transport supplies only the provider response, never an APP receipt.
pytest_plugins = ("tests.test_plan_jev_dispatch",)


class SemanticWire(httpx2.AsyncBaseTransport):
    def __init__(self, adapter, choice):
        self.adapter, self.choice = adapter, choice

    async def handle_async_request(self, request):
        body = json.loads(request.content)
        assert set(body["state"]) == {
            "user_request",
            "current_page_title",
            "dialogue_reference",
            "edit_target_available",
            "intent_policy",
        }
        assert body["state"]["user_request"] == self.adapter.request.message
        assert body["state"]["edit_target_available"] == (
            self.adapter.request.plan_authoring_capture is not None
        )
        assert set(body["questions"]) == {"requested_work"}
        current = self.adapter.service.list_turns(
            "world:one", self.adapter.turn.conversation_id
        )[0]
        assert current.graph_context_execution.events[-1].outcome == "sdk_entered"
        return httpx2.Response(
            200,
            request=request,
            json={
                "model": "jev-1.14.0",
                "answers": {
                    "requested_work": {
                        "type": "choice",
                        "choice": self.choice,
                        "confidence": 1.0,
                        "probabilities": {
                            name: float(name == self.choice)
                            for name in body["questions"]["requested_work"]["criteria"]
                        },
                    }
                },
                "usage": {"input_tokens": 31, "output_tokens": 7},
            },
        )


@pytest.mark.parametrize(
    "choice", ["discuss", "clarify", "write_current_page", "different_destination"]
)
def test_semantic_destination_is_durable_without_granting_edit_authority(
    plan_adapter, choice
):
    import asyncio
    from application_state.agent_conversation import types as t
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    dispatch = PlanJevDispatch.requested_work(plan_adapter, page_title="Preparation")
    selected, _ = asyncio.run(
        dispatch.run(
            transport=SemanticWire(plan_adapter, choice), api_key="synthetic-not-secret"
        )
    )
    assert selected == choice
    current = plan_adapter.service.list_turns(
        "world:one", plan_adapter.turn.conversation_id
    )[0]
    assert isinstance(current.graph_context_execution.policy, t.PlanAuthoringPolicyV1)
    events = current.graph_context_execution.events
    assert [e.kind for e in events] == [
        "plan_requested_work_authorized_v1",
        "provider_outcome",
        "provider_outcome",
        "plan_requested_work_selected_v1",
    ]
    assert (
        events[-1].requested_work == choice and events[-1].target_capture_sha256 is None
    )
    assert events[-1].actual_input_tokens == 31 and events[-1].actual_output_tokens == 7
    # Missing edit authority is retained as missing; it cannot change write intent
    # to discussion or independently permit a generated placement.
    assert current.status == "running" and current.completion is None
    from tests.test_plan_jev_dispatch import controller, Wire as RetrievalWire

    retrieval = controller(plan_adapter)
    acquired, _ = asyncio.run(
        retrieval.run(
            transport=RetrievalWire(plan_adapter), api_key="synthetic-not-secret"
        )
    )
    assert acquired.operation == "finish_retrieval"
    execution = plan_adapter.fence.turn.graph_context_execution
    if choice == "write_current_page":
        # Even a settled retrieval cannot authorize a writer for a missing target.
        writer = execution.policy.provider_roles.writer
        auth = retrieval.authorization.model_dump(mode="json", by_alias=True)
        for key in ("decision_request_id", "parent_request_sha256"):
            auth.pop(key)
        auth.update(
            kind="plan_jev_writer_authorized_v1",
            sequence=len(execution.events),
            event_id=str(uuid4()),
            provider_attempt_id=str(uuid4()),
            provider=writer.provider,
            model=writer.model,
            api_mode=writer.api_mode,
            frame_sha256="a" * 64,
        )
        payload = execution.model_dump(mode="json", by_alias=True)
        payload["events"].append(auth)
        with pytest.raises(ValueError, match="captured edit target"):
            type(execution).model_validate(payload)
    with pytest.raises(ValueError, match="unique"):
        dispatch.acknowledge(None)


def test_semantic_destination_unknown_outcome_never_resends(plan_adapter):
    import asyncio
    from generationengine import GenerationEngineError
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    class Wire(httpx2.AsyncBaseTransport):
        calls = 0

        async def handle_async_request(self, request):
            self.calls += 1
            raise httpx2.ReadTimeout("synthetic unknown outcome", request=request)

    wire = Wire()
    with pytest.raises(GenerationEngineError):
        asyncio.run(
            PlanJevDispatch.requested_work(plan_adapter, page_title="Plan").run(
                transport=wire, api_key="synthetic-not-secret"
            )
        )
    with pytest.raises(GenerationEngineError):
        asyncio.run(
            PlanJevDispatch.requested_work(plan_adapter, page_title="Plan").run(
                transport=wire, api_key="synthetic-not-secret"
            )
        )
    assert wire.calls == 1
    assert (
        plan_adapter.fence.turn.graph_context_execution.events[-1].outcome
        == "outcome_unknown"
    )


def admitted_authoring(plan_adapter):
    """Use actual Content, conversation and provider owners for a live target."""
    import asyncio
    from dataclasses import replace
    from application_state.content.service import create_world_plan, commit_plan
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.plan_authoring import (
        PlanAuthoringCaptureV1,
    )
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    obj = create_world_plan(title="Preparation", world_id="world:one")
    obj, revision = commit_plan(
        str(obj.work_object_id),
        plan_adapter.work.plan_markdown,
        expected_revision=obj.object_revision,
        expected_world_id="world:one",
    )
    service = plan_adapter.service
    service.new_conversation(
        t.ConversationCommand(
            world_id="world:one",
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )
    pointer = service.get_world_pointer("world:one")
    payload = capture_payload()
    payload.update(
        world_id="world:one",
        document_id=str(obj.work_object_id),
        base_revision=obj.object_revision,
        base_content_sha256=revision.content_sha256,
        conversation_id=str(pointer.active_conversation_id),
        expected_pointer_revision=pointer.revision,
    )
    capture = PlanAuthoringCaptureV1.model_validate(payload)
    basis = plan_adapter.work.content_basis.model_copy(
        update={
            "document_id": str(obj.work_object_id),
            "object_revision": obj.object_revision,
            "work_revision_id": str(revision.work_revision_id),
            "revision_n": revision.revision_n,
            "content_sha256": revision.content_sha256,
        }
    )
    plan_adapter.work = replace(
        plan_adapter.work,
        object_id=str(obj.work_object_id),
        revision=obj.object_revision,
        content_basis=basis,
    )
    primary = plan_adapter.request.primary_work.model_copy(
        update={
            "object_id": str(obj.work_object_id),
            "expected_revision": obj.object_revision,
            "expected_revision_n": revision.revision_n,
            "expected_content_sha256": revision.content_sha256,
        }
    )
    plan_adapter.request = plan_adapter.request.model_copy(
        update={"primary_work": primary, "plan_authoring_capture": capture}
    )
    plan_adapter.submitted_intent = _submitted_turn_intent(
        plan_adapter.request, world_id="world:one"
    )
    dispatch = PlanJevDispatch.requested_work(plan_adapter, page_title="Preparation")
    asyncio.run(
        dispatch.run(
            transport=SemanticWire(plan_adapter, "write_current_page"),
            api_key="synthetic-not-secret",
        )
    )
    return capture, plan_adapter.fence.turn


def test_agent_reservation_marks_both_owners_before_commit_and_replays_exactly(
    plan_adapter,
):
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from application_state.errors import ApplicationStateValidationError

    capture, turn = admitted_authoring(plan_adapter)
    action, fresh = plan_adapter.service.reserve_plan_authoring_action(
        capture=capture, turn_id=turn.turn_id, expected_revision=turn.revision
    )
    assert fresh and action.status == "pending"
    assert action.authoring_origin.turn_id == turn.turn_id
    assert action.authoring_origin.capture_sha256 == capture.sha256
    assert action.authoring_origin.conversation_id == capture.conversation_id
    duplicate, second_fresh = plan_adapter.service.reserve_plan_authoring_action(
        capture=capture, turn_id=turn.turn_id, expected_revision=turn.revision
    )
    assert not second_fresh and duplicate == action
    with pytest.raises(
        ApplicationStateValidationError, match="atomic turn finalization"
    ):
        PlanActionDialogueService().finish(
            action_id=action.action_id,
            token=action.dispatch_token,
            fence=action.fence,
            status="completed",
            summary="Wrong owner",
        )
    assert (
        plan_adapter.service.list_turns("world:one", turn.conversation_id)[0].status
        == "running"
    )


@pytest.mark.parametrize("mutation", ["content", "turn_revision", "capture", "pointer"])
def test_rejected_authoring_reservation_rolls_back_its_pending_action(
    plan_adapter, application_state_dsn, mutation
):
    import psycopg
    from application_state.errors import (
        ApplicationStateConflictError,
        ApplicationStateValidationError,
    )
    from application_state.agent_conversation import types as t
    from application_state.content.service import commit_plan

    capture, turn = admitted_authoring(plan_adapter)
    expected = turn.revision
    if mutation == "content":
        commit_plan(
            capture.document_id,
            "A newer saved Plan.",
            expected_revision=capture.base_revision,
            expected_world_id=capture.world_id,
        )
    elif mutation == "turn_revision":
        expected -= 1
    elif mutation == "capture":
        capture = capture.model_copy(
            update={"draft_generation": capture.draft_generation + 1}
        )
    else:
        plan_adapter.service.new_conversation(
            t.ConversationCommand(
                world_id=capture.world_id,
                command_id=uuid4(),
                expected_pointer_revision=capture.expected_pointer_revision,
                expected_active_conversation_id=capture.conversation_id,
            )
        )
    with pytest.raises(
        (ApplicationStateConflictError, ApplicationStateValidationError)
    ):
        plan_adapter.service.reserve_plan_authoring_action(
            capture=capture, turn_id=turn.turn_id, expected_revision=expected
        )
    with psycopg.connect(application_state_dsn) as conn:
        assert (
            conn.execute("SELECT count(*) FROM plan_action.action").fetchone()[0] == 0
        )


def test_competing_authoring_reservations_share_one_immutable_action(plan_adapter):
    from concurrent.futures import ThreadPoolExecutor

    capture, turn = admitted_authoring(plan_adapter)

    def reserve(_):
        return plan_adapter.service.reserve_plan_authoring_action(
            capture=capture, turn_id=turn.turn_id, expected_revision=turn.revision
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, range(2)))
    assert sum(fresh for _, fresh in results) == 1
    assert results[0][0].action_id == results[1][0].action_id
    assert results[0][0].authoring_origin == results[1][0].authoring_origin


@pytest.mark.parametrize(
    "change",
    [
        {"requested_work": "write_current_page"},
        {"target_capture_sha256": "a" * 64},
        {"actual_input_tokens": 32},
    ],
)
def test_semantic_projection_cannot_change_the_captured_provider_answer(
    plan_adapter, change
):
    import asyncio
    from application_state.errors import ApplicationStateValidationError
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    dispatch = PlanJevDispatch.requested_work(plan_adapter, page_title="Preparation")
    _, result = asyncio.run(
        dispatch.run(
            transport=SemanticWire(plan_adapter, "discuss"),
            api_key="synthetic-not-secret",
        )
    )
    turn = plan_adapter.fence.turn
    event = turn.graph_context_execution.events[-1].model_copy(
        update=change
        | {"event_id": uuid4(), "sequence": len(turn.graph_context_execution.events)}
    )
    with pytest.raises(ApplicationStateValidationError, match="exact typed"):
        plan_adapter.service.record_plan_requested_work_selection(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            selection=event,
            producer_proof={
                "parent_request_json": dispatch.parent.model_dump_json(by_alias=True),
                "request_json": dispatch.prepared.body.decode(),
                "response_json": result.model_dump_json(),
            },
        )
    assert (
        plan_adapter.service.list_turns(turn.world_id, turn.conversation_id)[0].revision
        == turn.revision
    )
