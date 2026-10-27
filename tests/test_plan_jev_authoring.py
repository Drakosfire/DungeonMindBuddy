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


def admitted_authoring(plan_adapter, *, admit=True):
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
    if not admit:
        return capture, None
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


def authoring_writer(plan_adapter, *, rules_used=False, graph_used=True):
    import asyncio
    from application_state.agent_conversation.rules_authority_policy import (
        rules_capability,
    )
    from graph_memory.interaction.session import GraphReferent
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import (
        PlanRulesRuntime,
    )
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from tests.test_plan_jev_driver import Decisions, fixture_reads

    if rules_used:
        from tests.test_rules_lookup_broker import args

        plan_adapter.request = plan_adapter.request.model_copy(
            update={"message": args().question}
        )
    capture, turn = admitted_authoring(plan_adapter)
    action, _ = plan_adapter.service.reserve_plan_authoring_action(
        capture=capture, turn_id=turn.turn_id, expected_revision=turn.revision
    )
    if graph_used:
        plan_adapter.bootstrap.retrieval_session.referents = [
            GraphReferent(id="pond", label="Park pond")
        ]
        fixture_reads(plan_adapter)
    rules = PlanRulesRuntime(plan_adapter, rules_capability(graph=True))
    rules.authoring = (action, capture)
    driver = PlanJevDriver(plan_adapter, rules=rules if rules_used else None)
    proof = asyncio.run(
        driver.run(transport=Decisions(), api_key="synthetic-not-secret")
    )
    return PlanJevWriter(plan_adapter, proof, rules), action, capture


@pytest.mark.parametrize("mode", ["base", "rules_only", "mixed"])
def test_one_writer_atomically_stores_plan_result_and_exact_replay(
    plan_adapter, mode, monkeypatch
):
    import asyncio
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.rules_authority_reads import (
        MixedCompletedTurnV1,
    )
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from application_state.agent_conversation.plan_authoring import (
        PlanActionAuthoringResultV1,
    )
    from application_state.content.service import commit_plan
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, capture = authoring_writer(
        plan_adapter, rules_used=mode != "base", graph_used=mode != "rules_only"
    )
    answer = graph_answer()
    answer["answer_segments"].append(
        {
            "kind": "proposal",
            "label": "invented_idea",
            "text": "## Possible approach\n\n| Lead | Follow-up |\n| --- | --- |\n| Pond | Ask about access. |",
        }
    )
    if mode != "base":
        support = writer.rules.frame().supports[0]
        answer = {
            "schema": "dmb_rules_mixed_answer_v1",
            "base_output": None if mode == "rules_only" else answer,
            "rules_segments": [
                {
                    "kind": "rules_claim",
                    "text": support.excerpt_text,
                    "support_ids": [str(support.support_id)],
                }
            ],
            "ordered_refs": (
                [{"domain": "base", "segment_index": None}] if mode == "mixed" else []
            )
            + [{"domain": "rules", "segment_index": 0}],
        }
    method = (
        "complete_plan_authoring_turn"
        if mode == "base"
        else "complete_plan_authoring_mixed_turn"
    )
    original = getattr(plan_adapter.service, method)
    accepted = []

    def complete(result, **kwargs):
        accepted.append((result, kwargs))
        return original(result, **kwargs)

    monkeypatch.setattr(plan_adapter.service, method, complete)
    wire = WriterWire(plan_adapter, json.dumps(answer))
    completed = asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    assert len(wire.calls) == 1 and len(accepted) == 1
    actual_request = json.loads(wire.calls[0].content)
    frame = json.loads(actual_request["input"][0]["content"])
    assert frame["current_page_draft"] == {
        "state": "unsaved_working_draft",
        "primary_authoring_context": True,
        "markdown": capture.draft_markdown,
    }
    assert frame["focused_edit_target"] == {"kind": "insert_at_caret"}
    assert actual_request["input"][0]["content"].count(capture.draft_markdown) == 1
    assert (
        "Prepare only the requested editable Plan fragment"
        in actual_request["instructions"]
    )
    assert "No edit or generation happened." not in actual_request["instructions"]
    envelope = (
        completed.envelope if isinstance(completed, MixedCompletedTurnV1) else completed
    )
    assert envelope.status == "completed"
    stored = PlanActionDialogueService().get_by_key(
        capture.world_id, capture.idempotency_key
    )
    assert stored.status == "completed" and isinstance(
        stored.authoring_origin, PlanActionAuthoringResultV1
    )
    assert stored.authoring_origin.expected_turn_revision + 1 == envelope.revision
    proposal = plan_adapter.service.get_plan_authoring_proposal(
        capture.world_id, action.action_id
    )
    from apps.live_control_server.services.agent_turn_service import (
        project_plan_authoring_proposal,
    )

    assert (
        project_plan_authoring_proposal(completed, service=plan_adapter.service)
        == proposal
    )
    assert proposal == accepted[0][1]["proposal"]
    assert proposal.capture == capture
    from apps.live_control_server.routes import agent as agent_route

    monkeypatch.setattr(agent_route, "enforce_native_graph_gm", lambda request: None)
    monkeypatch.setattr(agent_route, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(
        agent_route, "_conversation_service", lambda request: plan_adapter.service
    )
    history = agent_route.get_world_conversation_history(
        capture.world_id,
        None,
        limit=10,
        before_sequence=None,
        include_turn_correlation=True,
    )
    assert history.turns[0].plan_proposal == proposal
    assert history.turns[0].turn_id == envelope.turn_id
    if mode == "rules_only":
        assert (
            isinstance(completed, MixedCompletedTurnV1)
            and completed.base_projection.kind == "unclaimed"
        )
        assert proposal.replacement_markdown == support.excerpt_text
    else:
        assert "| Lead | Follow-up |" in proposal.replacement_markdown
        assert "\n\n## Possible approach" in proposal.replacement_markdown
    # Exact result replay remains available after the author moves on. It is not
    # another dispatch, an edit to the newer Plan, or a requirement to reactivate
    # the archived conversation.
    plan_adapter.service.new_conversation(
        t.ConversationCommand(
            world_id=capture.world_id,
            command_id=uuid4(),
            expected_pointer_revision=capture.expected_pointer_revision,
            expected_active_conversation_id=capture.conversation_id,
        )
    )
    commit_plan(
        capture.document_id,
        "A newer saved Plan.",
        expected_revision=capture.base_revision,
        expected_world_id=capture.world_id,
    )
    assert original(accepted[0][0], **accepted[0][1]) == completed
    assert (
        project_plan_authoring_proposal(completed, service=plan_adapter.service)
        == proposal
    )
    assert (
        plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
        == proposal
    )
    assert len(wire.calls) == 1


@pytest.mark.parametrize(
    "case",
    [
        "terminal_cas",
        "generic_finish",
        "later_save",
        "switch_chat",
        "stale_before_send",
    ],
)
def test_authoring_failure_and_navigation_boundaries_keep_ownership(
    plan_adapter, application_state_dsn, monkeypatch, case
):
    import asyncio
    import psycopg
    from application_state.agent_conversation import types as t
    from application_state.content.service import commit_plan, snapshot_content
    from application_state.errors import (
        ApplicationStateConflictError,
        ApplicationStateValidationError,
    )
    from application_state.plan_action_dialogue import repository as actions
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, capture = authoring_writer(plan_adapter)
    if case == "terminal_cas":
        original = actions.finish_authoring_result

        def lose_fence(conn, *args):
            conn.execute(
                "UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s",
                (action.action_id,),
            )
            return original(conn, *args)

        monkeypatch.setattr(actions, "finish_authoring_result", lose_fence)
    elif case == "generic_finish":

        def wrong_owner(result, *, proposal, output_proof, expected_rules_revision):
            return plan_adapter.service.complete_native_base_turn(
                result,
                output_proof=output_proof,
                expected_rules_revision=expected_rules_revision,
            )

        monkeypatch.setattr(
            plan_adapter.service, "complete_plan_authoring_turn", wrong_owner
        )

    def newer_plan():
        commit_plan(
            capture.document_id,
            "A newer author edit.",
            expected_revision=capture.base_revision,
            expected_world_id=capture.world_id,
        )

    if case == "stale_before_send":
        newer_plan()

    class Wire(WriterWire):
        async def handle_async_request(self, request):
            if case == "later_save":
                newer_plan()
            elif case == "switch_chat":
                plan_adapter.service.new_conversation(
                    t.ConversationCommand(
                        world_id=capture.world_id,
                        command_id=uuid4(),
                        expected_pointer_revision=capture.expected_pointer_revision,
                        expected_active_conversation_id=capture.conversation_id,
                    )
                )
            return await super().handle_async_request(request)

    wire = Wire(plan_adapter, json.dumps(graph_answer()))
    if case in {"terminal_cas", "generic_finish", "stale_before_send"}:
        # The real GenEngine gate wraps pre-send authorization errors; post-send
        # atomic failures retain their actual APP error.
        if case == "stale_before_send":
            from generationengine import GenerationEngineError

            expected = (GenerationEngineError, ApplicationStateConflictError)
        else:
            expected = (ApplicationStateConflictError, ApplicationStateValidationError)
        with pytest.raises(expected):
            asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
        assert len(wire.calls) == (0 if case == "stale_before_send" else 1)
        assert (
            plan_adapter.service.list_turns(capture.world_id, capture.conversation_id)[
                0
            ].status
            == "running"
        )
        assert (
            plan_adapter.service.get_plan_authoring_proposal(
                capture.world_id, action.action_id
            )
            is None
        )
        with psycopg.connect(application_state_dsn) as conn:
            # A terminal-CAS failure must roll back the earlier Agent completion
            # and closing of its Rules ledger on this same connection.
            assert (
                conn.execute(
                    "SELECT count(*) FROM agent.turn WHERE status='completed'"
                ).fetchone()[0]
                == 0
            )
            assert (
                conn.execute(
                    "SELECT count(*) FROM agent.turn_rules_execution WHERE payload->>'state'='active'"
                ).fetchone()[0]
                == 1
            )
    else:
        completed = asyncio.run(
            writer.run(transport=wire, api_key="synthetic-not-secret")
        )
        assert completed.status == "completed" and len(wire.calls) == 1
        proposal = plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
        assert proposal.capture == capture
        assert (
            proposal.replacement_markdown
            == graph_answer()["answer_segments"][0]["text"]
        )
    stored = PlanActionDialogueService().get_by_key(
        capture.world_id, capture.idempotency_key
    )
    assert stored.status == (
        "completed" if case in {"later_save", "switch_chat"} else "pending"
    )
    if case in {"later_save", "stale_before_send"}:
        assert snapshot_content(capture.document_id).markdown == "A newer author edit."


def test_unvalidated_fragment_cannot_be_attached_after_grounding(
    plan_adapter, monkeypatch
):
    import asyncio
    from application_state.agent_conversation.plan_authoring import (
        PlanAuthoredProposalV1,
        text_digest,
    )
    from application_state.errors import ApplicationStateValidationError
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, capture = authoring_writer(plan_adapter)
    original = plan_adapter.service.complete_plan_authoring_turn

    def inject(result, *, proposal, **kwargs):
        payload = proposal.model_dump(mode="json", by_alias=True)
        payload["replacement_markdown"] += "\n\nAn unrelated unvalidated assertion."
        payload["origin"]["replacement_markdown_sha256"] = text_digest(
            payload["replacement_markdown"]
        )
        return original(
            result, proposal=PlanAuthoredProposalV1.model_validate(payload), **kwargs
        )

    monkeypatch.setattr(plan_adapter.service, "complete_plan_authoring_turn", inject)
    wire = WriterWire(plan_adapter, json.dumps(graph_answer()))
    with pytest.raises(ApplicationStateValidationError, match="literal output"):
        asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    assert len(wire.calls) == 1
    assert (
        plan_adapter.service.list_turns(capture.world_id, capture.conversation_id)[
            0
        ].status
        == "running"
    )
    assert (
        plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
        is None
    )


def test_mixed_rules_acceptance_rolls_back_with_plan_terminal_cas(
    plan_adapter, application_state_dsn, monkeypatch
):
    import asyncio
    import psycopg
    from application_state.errors import ApplicationStateConflictError
    from application_state.plan_action_dialogue import repository as actions
    from tests.test_plan_jev_writer import WriterWire

    writer, action, capture = authoring_writer(
        plan_adapter, rules_used=True, graph_used=False
    )
    support = writer.rules.frame().supports[0]
    answer = {
        "schema": "dmb_rules_mixed_answer_v1",
        "base_output": None,
        "rules_segments": [
            {
                "kind": "rules_claim",
                "text": support.excerpt_text,
                "support_ids": [str(support.support_id)],
            }
        ],
        "ordered_refs": [{"domain": "rules", "segment_index": 0}],
    }
    original = actions.finish_authoring_result

    def lose_fence(conn, *args):
        conn.execute(
            "UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s",
            (action.action_id,),
        )
        return original(conn, *args)

    monkeypatch.setattr(actions, "finish_authoring_result", lose_fence)
    wire = WriterWire(plan_adapter, json.dumps(answer))
    with pytest.raises(ApplicationStateConflictError, match="atomic result completion"):
        asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    with psycopg.connect(application_state_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM agent.turn WHERE status='completed'"
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM agent.turn_rules_execution WHERE payload->>'state'='active' AND accepted_binding IS NULL AND accepted_binding_sha256 IS NULL"
            ).fetchone()[0]
            == 1
        )
    assert len(wire.calls) == 1
    assert (
        plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
        is None
    )


def test_plan_result_readback_rejects_a_mismatched_completed_owner(
    plan_adapter, application_state_dsn
):
    import asyncio
    import psycopg
    from application_state.errors import ApplicationStateIntegrityError
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, capture = authoring_writer(plan_adapter)
    wire = WriterWire(plan_adapter, json.dumps(graph_answer()))
    asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    # A syntactically valid seal cannot stand in for the actual paired result.
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE plan_action.action SET authoring_origin=jsonb_set(authoring_origin,'{agent_result_sha256}',to_jsonb(%s::text)) WHERE action_id=%s",
            ("0" * 64, action.action_id),
        )
    with pytest.raises(ApplicationStateIntegrityError, match="do not match"):
        plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
    assert len(wire.calls) == 1


def test_live_agent_claim_keeps_authoring_action_fence_past_fixed_lease(
    plan_adapter, application_state_dsn
):
    import asyncio
    import psycopg
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, capture = authoring_writer(plan_adapter)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s",
            (action.action_id,),
        )
    reconciled = PlanActionDialogueService().get_by_key(
        capture.world_id, capture.idempotency_key
    )
    assert reconciled.status == "pending" and reconciled.fence == action.fence
    assert reconciled.dispatch_token == action.dispatch_token
    wire = WriterWire(plan_adapter, json.dumps(graph_answer()))
    completed = asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    assert completed.status == "completed" and len(wire.calls) == 1
    assert (
        plan_adapter.service.get_plan_authoring_proposal(
            capture.world_id, action.action_id
        )
        is not None
    )


@pytest.mark.parametrize("loss", ["expired", "interrupted", "different_attempt"])
def test_authoring_action_never_renews_a_lost_agent_claim(
    plan_adapter, application_state_dsn, loss
):
    import psycopg
    from application_state.agent_conversation.types import TurnFailure
    from application_state.plan_action_dialogue.service import PlanActionDialogueService

    writer, action, capture = authoring_writer(plan_adapter)
    turn = plan_adapter.fence.turn
    if loss == "interrupted":
        plan_adapter.service.fail_turn(
            TurnFailure(
                world_id=turn.world_id,
                conversation_id=turn.conversation_id,
                turn_id=turn.turn_id,
                expected_revision=turn.revision,
                failure_code="synthetic_interruption",
            ),
            interrupted=True,
        )
    else:
        with psycopg.connect(application_state_dsn) as conn:
            if loss == "expired":
                conn.execute(
                    "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
                    (turn.turn_id,),
                )
            else:
                conn.execute(
                    "UPDATE agent.turn SET attempt=attempt+1 WHERE turn_id=%s",
                    (turn.turn_id,),
                )
    reconciled = PlanActionDialogueService().get_by_key(
        capture.world_id, capture.idempotency_key
    )
    assert reconciled.status == "indeterminate" and reconciled.fence == action.fence + 1
    assert reconciled.dispatch_token is None and reconciled.lease_expires_at is None


def test_action_expiry_waits_for_concurrent_agent_claim_renewal(
    plan_adapter, application_state_dsn
):
    import psycopg
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    from threading import Event
    from application_state.plan_action_dialogue.service import PlanActionDialogueService

    _, action, capture = authoring_writer(plan_adapter)
    turn = plan_adapter.fence.turn
    plan_adapter.fence.renewer.stop_and_join()
    with psycopg.connect(application_state_dsn) as expiry:
        expiry.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (turn.turn_id,),
        )
        expiry.execute(
            "UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s",
            (action.action_id,),
        )
    started = Event()
    with psycopg.connect(application_state_dsn) as renewal:
        renewal.execute("SET LOCAL lock_timeout='5s'")
        renewal.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()+interval '120 seconds' WHERE turn_id=%s",
            (turn.turn_id,),
        )

        def reconcile():
            started.set()
            return PlanActionDialogueService().get_by_key(
                capture.world_id, capture.idempotency_key
            )

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(reconcile)
            try:
                assert started.wait(5)
                # A nonlocking read would see the committed expired deadline and
                # fence valid work. Reconciliation must wait for renewal here.
                with pytest.raises(TimeoutError):
                    pending.result(timeout=0.2)
                renewal.commit()
            finally:
                renewal.rollback()
            result = pending.result(timeout=10)
    assert result.status == "pending" and result.fence == action.fence
    assert result.dispatch_token == action.dispatch_token


@pytest.mark.parametrize(
    "choice", ["discuss", "clarify", "write_current_page", "different_destination"]
)
def test_ordinary_plan_harness_respects_semantic_destination(
    plan_adapter, tmp_path, choice
):
    from tests.test_plan_jev_harness import route_case, Finish
    from apps.live_control_server.services.agent_turn_service import (
        execute_agent_turn,
        AgentTurnServiceError,
    )

    capture, _ = admitted_authoring(plan_adapter, admit=False)
    harness, _, wire, kwargs = route_case(plan_adapter, tmp_path)

    class Choices(Finish):
        async def handle_async_request(self, request):
            if "requested_work" in json.loads(request.content)["questions"]:
                self.calls.append(request)
                return await SemanticWire(wire.adapter, choice).handle_async_request(
                    request
                )
            return await super().handle_async_request(request)

    decisions = Choices()
    harness.decision_transport = decisions
    if choice == "different_destination":
        with pytest.raises(AgentTurnServiceError) as failed:
            execute_agent_turn(plan_adapter.request, **kwargs)
        assert failed.value.code == "plan_authoring_destination_unavailable"
        assert len(decisions.calls) == 1 and not wire.calls
        current = kwargs["conversation_service"].list_turns(
            capture.world_id, capture.conversation_id
        )[0]
        assert (
            current.failure_code == failed.value.code
            and current.user_text == plan_adapter.request.message
        )
        return
    response = execute_agent_turn(plan_adapter.request, **kwargs)
    assert len(decisions.calls) == 2 and len(wire.calls) == 1
    assert (response.plan_proposal is not None) == (choice == "write_current_page")
    if response.plan_proposal is not None:
        assert response.plan_proposal.capture == capture
        assert response.plan_proposal.origin.turn_id == wire.adapter.turn.turn_id
    else:
        assert "plan_proposal" not in response.model_dump(mode="json")
    replay = execute_agent_turn(plan_adapter.request, **kwargs)
    assert replay.plan_proposal == response.plan_proposal
    assert len(decisions.calls) == 2 and len(wire.calls) == 1


def test_ordinary_plan_missing_capture_retains_write_intent_without_writer(
    plan_adapter, tmp_path
):
    from tests.test_plan_jev_harness import route_case, Finish
    from apps.live_control_server.services.agent_turn_service import (
        execute_agent_turn,
        AgentTurnServiceError,
    )

    harness, _, wire, kwargs = route_case(plan_adapter, tmp_path)

    class Choices(Finish):
        async def handle_async_request(self, request):
            self.calls.append(request)
            return await SemanticWire(
                wire.adapter, "write_current_page"
            ).handle_async_request(request)

    decisions = Choices()
    harness.decision_transport = decisions
    with pytest.raises(AgentTurnServiceError) as failed:
        execute_agent_turn(plan_adapter.request, **kwargs)
    assert failed.value.code == "plan_authoring_target_unavailable"
    assert len(decisions.calls) == 1 and not wire.calls
    turn = kwargs["conversation_service"].list_turns(
        plan_adapter.world_id, wire.adapter.turn.conversation_id
    )[0]
    assert (
        turn.failure_code == failed.value.code
        and turn.user_text == plan_adapter.request.message
    )
    assert (
        turn.graph_context_execution.events[-1].requested_work == "write_current_page"
    )


def test_completed_writing_cannot_silently_lose_its_plan_result(
    plan_adapter, application_state_dsn
):
    import asyncio
    import psycopg
    from application_state.errors import ApplicationStateIntegrityError
    from apps.live_control_server.services.agent_turn_service import (
        project_plan_authoring_proposal,
    )
    from tests.test_plan_jev_writer import WriterWire, graph_answer

    writer, action, _ = authoring_writer(plan_adapter)
    completed = asyncio.run(
        writer.run(
            transport=WriterWire(plan_adapter, json.dumps(graph_answer())),
            api_key="synthetic",
        )
    )
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "DELETE FROM plan_action.action WHERE action_id=%s", (action.action_id,)
        )
    with pytest.raises(ApplicationStateIntegrityError, match="paired Plan proposal"):
        project_plan_authoring_proposal(completed, service=plan_adapter.service)


def test_ordinary_plan_reports_target_change_after_retrieval_without_writer(plan_adapter, tmp_path):
    from tests.test_plan_jev_harness import route_case, Finish
    from application_state.content.service import commit_plan
    from apps.live_control_server.services.agent_turn_service import execute_agent_turn, AgentTurnServiceError
    capture, _ = admitted_authoring(plan_adapter, admit=False)
    harness, _, wire, kwargs = route_case(plan_adapter, tmp_path)
    class Choices(Finish):
        async def handle_async_request(self, request):
            if 'requested_work' in json.loads(request.content)['questions']:
                self.calls.append(request)
                return await SemanticWire(wire.adapter, 'write_current_page').handle_async_request(request)
            commit_plan(capture.document_id, 'Newer author note.', expected_revision=capture.base_revision,
                expected_world_id=capture.world_id)
            return await super().handle_async_request(request)
    decisions = Choices()
    harness.decision_transport = decisions
    with pytest.raises(AgentTurnServiceError) as failed:
        execute_agent_turn(plan_adapter.request, **kwargs)
    assert failed.value.code == 'plan_authoring_target_changed'
    assert len(decisions.calls) == 2 and not wire.calls
    current = kwargs['conversation_service'].list_turns(capture.world_id, capture.conversation_id)[0]
    assert current.failure_code == failed.value.code and current.user_text == plan_adapter.request.message
    assert not any(event.kind.startswith('plan_jev_writer_authorized') for event in current.graph_context_execution.events)


@pytest.mark.parametrize('status,expected', [(400,'invalid_request'),(429,'rate_limited'),(503,'provider_unavailable'),(None,'provider_timeout')])
def test_plan_decision_failure_retains_normalized_cause_without_sdk_text(plan_adapter,status,expected):
    import asyncio
    from generationengine import GenerationEngineError
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch

    class FailedWire(httpx2.AsyncBaseTransport):
        calls=0
        async def handle_async_request(self,request):
            self.calls+=1
            if status is None:
                raise httpx2.ReadTimeout('DO_NOT_CAPTURE_PRIVATE_TRANSPORT_DETAIL',request=request)
            return httpx2.Response(status,request=request,json={'error':{'message':'DO_NOT_CAPTURE_PRIVATE_TRANSPORT_DETAIL'}})

    wire=FailedWire()
    with pytest.raises(GenerationEngineError):
        asyncio.run(PlanJevDispatch.requested_work(plan_adapter,page_title='Plan').run(transport=wire,api_key='synthetic-not-secret'))
    assert wire.calls==1
    trace=plan_adapter.context_capture.trace
    failures=[event for event in trace.observations if event.kind=='failure']
    assert failures[-1].code=='plan_jev_'+expected and failures[-1].phase=='provider'
    assert 'DO_NOT_CAPTURE_PRIVATE_TRANSPORT_DETAIL' not in trace.model_dump_json()
    execution=plan_adapter.fence.turn.graph_context_execution
    assert any(event.kind=='plan_requested_work_authorized_v1' for event in execution.events)
    assert not any(event.kind=='plan_requested_work_selected_v1' for event in execution.events)
