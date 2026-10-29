"""Selection authority through durable ordinary conversation and Harness transport."""

from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    submitted_turn_intent_fingerprint_v1,
)
from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services.agent_runtime import (
    AgentRuntimeDescriptor,
    AgentRuntimeResult,
)
from apps.live_control_server.services.agent_turn_service import (
    AgentTurnServiceError,
    _submitted_turn_intent,
    _turn_idempotency_key,
    execute_agent_turn,
)
from apps.live_control_server.services.hermes_agent_runtime import (
    map_invocation_to_hermes_request,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (
    serialize_hermes_graph_agent_turn_request,
    deserialize_hermes_graph_agent_turn_request,
)
from apps.live_control_server.services.hermes_session_store import (
    HermesSessionPointerStore,
)
from tests import test_ingest_selection_context as selection_fixtures
from tests.test_ingest_selection_context import resolve, rewrite_component

from tests.test_hermes_agent_runtime import _invocation

context = selection_fixtures.context


class RecordingRuntime:
    descriptor = AgentRuntimeDescriptor(
        runtime_id="fixture",
        trace_backend="fixture",
        trace_runtime="test",
        trace_mode="conversation",
    )

    def __init__(self):
        self.invocations = []
        self.requests = []

    def run(self, invocation):
        self.invocations.append(invocation)
        self.requests.append(
            deserialize_hermes_graph_agent_turn_request(
                serialize_hermes_graph_agent_turn_request(
                    map_invocation_to_hermes_request(invocation)
                )
            )
        )
        return AgentRuntimeResult(
            status="ok",
            final_text="Ari visits the warehouse. The annotation is separate.",
            runtime_session_id="synthetic-session",
        )


def request_for(context, **changes):
    payload = dict(
        schema="dmb_agent_turn_request_v1",
        client_thread_id="selection-thread",
        turn_id="selection-turn",
        surface={"surface_id": "ingest", "instance_id": "review"},
        owner_scope={"kind": "world", "world_id": "world-a"},
        primary_work=None,
        client_work_state="none",
        graph_request={"mode": "none"},
        graph_selection=None,
        message="What relationships does the highlighted person have?",
        selected_knowledge={
            "schema": "dmb_agent_native_review_selection_v2",
            "run_id": "test-run",
            "context_request": context.body,
            "expected_context_sha256": resolve(context)["context_sha256"],
        },
    )
    payload.update(changes)
    return AgentTurnRequest.model_validate(payload)


def execute(context, request, runtime, conversation, **changes):
    def no_graph(*args, **kwargs):
        pytest.fail("Selection must not implicitly enable or retarget Graph retrieval")

    kwargs = dict(
        root=context.root,
        pointer_store=HermesSessionPointerStore(context.root / "pointers"),
        owner_resolver=lambda request: {
            "kind": "world",
            "id": "world-a",
            "name": "Test World",
        },
        work_resolver=lambda request, owner: None,
        graph_resolver=no_graph,
        runtime=runtime,
        conversation_service=conversation,
        operator_subject="operator:test",
    )
    kwargs.update(changes)
    return execute_agent_turn(request, **kwargs)


def test_selection_survives_real_app_storage_and_completed_replay(
    context, application_state_dsn, monkeypatch
):
    request = request_for(context)
    runtime = RecordingRuntime()
    response = execute(context, request, runtime, AgentConversationService())
    assert response.answer.status == "ok"
    assert len(runtime.invocations) == 1
    host = runtime.requests[0]
    assert host.input_kind == "server_assembled_saved_work"
    assert "Ari 🐉" in host.question
    assert context.body["annotation"] in host.question
    assert "not admitted World facts" in host.question
    assert "not source quotations" in host.question
    assert "cannot prepare or apply" in host.question
    assert host.world_id is None
    assert not host.capability_policy.enabled_tool_names
    # A fresh service reads PostgreSQL, not the original Python instance.
    fresh = AgentConversationService()
    intent = _submitted_turn_intent(request, world_id="world-a")
    turn = fresh.reconcile_turn(
        "world-a", _turn_idempotency_key("world-a", request.turn_id), intent
    )
    assert turn.status == "completed"
    assert turn.submitted_intent_fingerprint_v1 == submitted_turn_intent_fingerprint_v1(
        intent
    )
    refs = [
        r
        for r in turn.provenance.supporting_work
        if r.kind == "ingest_selection_context"
    ]
    assert len(refs) == 1
    assert (refs[0].object_id, refs[0].revision, refs[0].content_sha256) == (
        "test-run",
        "6",
        request.selected_knowledge.expected_context_sha256,
    )
    # Historical replay must not depend on the run still being current.
    context.run.revision = 7
    def forbidden_read(*args, **kwargs):
        pytest.fail("completed replay consulted current source/run/native authority")

    monkeypatch.setattr(selection_fixtures.service, "get_extraction_run", forbidden_read)
    monkeypatch.setattr(selection_fixtures.service, "resolve_native_review_context", forbidden_read)
    monkeypatch.setattr(selection_fixtures.service, "resolve_managed_world_binding", forbidden_read)
    monkeypatch.setattr(selection_fixtures.service.source_service, "get_source_markdown", forbidden_read)
    replay = execute(context, request, runtime, fresh)
    assert replay.answer.status == "ok"
    assert len(runtime.invocations) == 1
    changed = request.model_dump(by_alias=True)
    changed["selected_knowledge"]["contextRequest"]["annotation"] = (
        "Different annotation"
    )
    with pytest.raises(AgentTurnServiceError) as caught:
        execute(context, AgentTurnRequest.model_validate(changed), runtime, fresh)
    assert caught.value.code == "turn_idempotency_conflict"
    assert len(runtime.invocations) == 1


@pytest.mark.parametrize("change", ["revision", "digest", "source", "annotation", "native_head"])
def test_changed_selection_rejects_before_provider(
    context, application_state_dsn, change, monkeypatch
):
    request = request_for(context)
    if change == "revision":
        context.run.revision = 7
    elif change == "digest":
        request = request.model_copy(
            update={
                "selected_knowledge": request.selected_knowledge.model_copy(
                    update={"expected_context_sha256": "f" * 64}
                )
            }
        )
    elif change == "source":
        context.source.markdown = "changed"
    elif change == "native_head":
        monkeypatch.setattr(selection_fixtures.service, "resolve_native_review_context", lambda **kwargs: {
            "revision_id": "changed-native-revision", "selections": [], "identity_approval": False,
        })
    else:
        request.selected_knowledge.context_request.annotation = (
            "Changed after context preview"
        )
    runtime = RecordingRuntime()
    with pytest.raises(AgentTurnServiceError):
        execute(context, request, runtime, AgentConversationService())
    assert runtime.invocations == []


@pytest.mark.parametrize("missing", ["conversation", "subject"])
def test_selection_requires_durable_authenticated_turn(context, missing):
    request = request_for(context)
    runtime = RecordingRuntime()
    with pytest.raises(AgentTurnServiceError) as caught:
        execute(
            context,
            request,
            runtime,
            None
            if missing == "conversation"
            else SimpleNamespace(reconcile_turn=lambda *args: None),
            operator_subject=None if missing == "subject" else "operator:test",
        )
    assert caught.value.code == "selection_conversation_unavailable"
    assert runtime.invocations == []


@pytest.mark.parametrize(
    "changes",
    [
        {"surface": {"surface_id": "build", "instance_id": "build"}},
        {"owner_scope": None},
        {"owner_scope": {"kind": "world", "world_id": "other-world"}},
    ],
)
def test_selection_scope_contradictions_reject(context, changes):
    with pytest.raises(ValidationError, match="matching World Ingest"):
        request_for(context, **changes)


def test_context_does_not_change_existing_graph_policy_or_scope(context):
    invocation = _invocation(input_kind="server_assembled_saved_work")
    without = map_invocation_to_hermes_request(invocation)
    with_selection = replace(
        invocation,
        context_packet=replace(
            invocation.context_packet, selected_knowledge_context=resolve(context)
        ),
    )
    host = deserialize_hermes_graph_agent_turn_request(
        serialize_hermes_graph_agent_turn_request(
            map_invocation_to_hermes_request(with_selection)
        )
    )
    assert host.world_id == without.world_id
    assert host.revision_pin == without.revision_pin
    assert host.capability_policy == without.capability_policy
    assert host.retrieval_session == without.retrieval_session
    assert host.surface_context_block == without.surface_context_block
    assert "candidate IDs do not retarget" in host.question


def test_no_selection_fingerprint_preserves_existing_authored_intent(context):
    request = request_for(context, selected_knowledge=None)
    intent = _submitted_turn_intent(request, world_id="world-a")
    old = intent.model_dump(
        mode="json",
        by_alias=True,
        exclude={"client_thread_id", "playable_target", "selected_knowledge"},
    )
    expected = hashlib.sha256(
        json.dumps(old, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert submitted_turn_intent_fingerprint_v1(intent) == expected
    selected = _submitted_turn_intent(request_for(context), world_id="world-a")
    assert submitted_turn_intent_fingerprint_v1(selected) != expected


def test_harness_requires_host_assembled_input_and_bounds_context(context):
    invocation = _invocation()
    selected = replace(
        invocation,
        context_packet=replace(
            invocation.context_packet, selected_knowledge_context=resolve(context)
        ),
    )
    with pytest.raises(ValueError, match="trusted saved-work"):
        map_invocation_to_hermes_request(selected)
    oversized = replace(
        selected,
        context_packet=replace(
            selected.context_packet, selected_knowledge_context={"text": "x" * 64001}
        ),
        input_kind="server_assembled_saved_work",
    )
    with pytest.raises(ValueError, match="exceeds its bound"):
        map_invocation_to_hermes_request(oversized)


def test_oversized_resolved_context_rejects_before_model(
    context, application_state_dsn
):
    context.payload["nodes"][0]["description"] = "x" * 64001
    rewrite_component(context, "candidate_graph", "candidate.json", context.payload)
    request = request_for(context)
    runtime = RecordingRuntime()
    with pytest.raises(AgentTurnServiceError) as caught:
        execute(context, request, runtime, AgentConversationService())
    assert caught.value.code == "selection_context_too_large"
    assert runtime.invocations == []


def test_route_propagates_authenticated_annotation_subject(context, monkeypatch):
    from starlette.requests import Request
    from fastapi import FastAPI
    from apps.live_control_server.routes import agent as route

    captured = {}

    def execute(body, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(model_dump=lambda **kwargs: {"synthetic": True})

    monkeypatch.setattr(
        route,
        "enforce_native_graph_gm",
        lambda request: SimpleNamespace(subject="operator:actual"),
    )
    monkeypatch.setattr(route, "execute_agent_turn", execute)
    monkeypatch.setattr(route, "repo_root", lambda: context.root)
    monkeypatch.setattr(route, "session_dir", lambda: context.root)
    monkeypatch.setattr(route, "_conversation_service", lambda request: None)
    request = Request(
        {
            "type": "http",
            "app": FastAPI(),
            "headers": [],
            "method": "POST",
            "path": "/api/live/agent/turn",
        }
    )
    assert route.post_agent_turn(request_for(context), request) == {"synthetic": True}
    assert captured["operator_subject"] == "operator:actual"
