import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from application_state.agent_conversation.context_trace import TraceGraphTool, TraceSourcePassage, TurnContextTraceV1
from apps.live_control_server.services import agent_replay_assertion as replay
from apps.live_control_server.services.agent_context_trace_projection import graph_operation_observation
from tests.test_agent_context_trace_projection import fixture as graph_fixture, request as graph_request
from apps.live_control_server.routes import agent


@pytest.fixture
def trace_api(monkeypatch):
    token = "context-trace-local-test-token-" * 2
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    world = "world-one"
    turn_id = uuid4()
    calls = []
    attempts = []

    def read(**binding):
        calls.append(binding)
        return attempts

    monkeypatch.setattr(agent, "_verified_world_id", lambda value: value)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: SimpleNamespace(list_context_trace_attempts=read))
    app = FastAPI()
    app.include_router(agent.router, prefix="/api/live")

    async def get(*, authorized=True, query=""):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)), base_url="http://test") as client:
            return await client.get(f"/api/live/agent/worlds/{world}/conversation/turns/{turn_id}/context-trace{query}",
                                    headers={"Authorization": f"Bearer {token}"} if authorized else {})

    return SimpleNamespace(world=world, turn_id=turn_id, calls=calls, attempts=attempts, get=get)


def test_historical_turn_without_trace_returns_explicit_empty_attempts(trace_api):
    response = asyncio.run(trace_api.get())
    assert response.status_code == 200
    assert response.json()["attempts"] == []
    assert trace_api.calls == [{"world_id": trace_api.world, "turn_id": trace_api.turn_id}]


def test_opt_in_trace_read_returns_exact_captured_passage(trace_api):
    text = "Complete recorded passage. " * 100
    passage = TraceSourcePassage(sequence=0, elapsed_ms=1, source_read_event_id=uuid4(), read_call_id=uuid4(),
        world_id=trace_api.world, graph_revision="revision", source_read_id="read", anchor_id="anchor",
        evidence_ref_id="evidence", source_artifact_id="source", source_revision_id="source-revision",
        outcome="enough", returned_chars=len(text), content_sha256=sha256(text.encode()).hexdigest(), text=text)
    trace_api.attempts.append(TurnContextTraceV1(trace_id=uuid4(), world_id=trace_api.world,
        conversation_id=uuid4(), turn_id=trace_api.turn_id, attempt=1, execution_start_sequence=0,
        started_at=datetime.now(UTC), observations=[passage]))
    response = asyncio.run(trace_api.get())
    assert response.status_code == 200
    assert response.json()["schema"] == "dmb_agent_turn_context_trace_response_v1"
    assert response.json()["attempts"][0]["observations"][0]["text"] == text


def test_trace_read_authentication_precedes_storage(trace_api):
    response = asyncio.run(trace_api.get(authorized=False))
    assert response.status_code == 401
    assert trace_api.calls == []


def test_wrong_world_trace_binding_is_not_exposed(trace_api):
    trace_api.attempts.append(TurnContextTraceV1(trace_id=uuid4(), world_id="other-world",
        conversation_id=uuid4(), turn_id=trace_api.turn_id, attempt=1, execution_start_sequence=0,
        started_at=datetime.now(UTC), observations=[]))
    response = asyncio.run(trace_api.get())
    assert response.status_code == 409
    assert "other-world" not in response.text
    assert "attempts" not in response.text


def test_trace_read_rejects_extra_selectors(trace_api):
    response = asyncio.run(trace_api.get(query="?world=other-world"))
    assert response.status_code == 422
    assert trace_api.calls == []


def test_replay_assertion_route_authenticates_before_read_and_disables_caching(trace_api, monkeypatch):
    handler = Mock(return_value={"schema": "dmb_replay_assertion_v1"})
    monkeypatch.setattr(replay, "open_replay_assertion", handler)
    trace_id = uuid4()
    path = f"/{trace_id}/steps/2/assertion?assertion_id=claim%3A0"
    assert asyncio.run(trace_api.get(authorized=False, query=path)).status_code == 401
    assert asyncio.run(trace_api.get(query=path + "&assertion_id=other")).status_code == 422
    handler.assert_not_called()
    response = asyncio.run(trace_api.get(query=path))
    assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
    assert handler.call_args.kwargs["assertion_id"] == "claim:0"
    assert handler.call_args.kwargs["trace_id"] == trace_id


@pytest.fixture
def saved_lookup():
    result, payload, execution = graph_fixture()
    step = TraceGraphTool.model_validate(graph_operation_observation(
        request=graph_request("search"), result=result, result_payload=payload,
        execution_event=execution, sequence=2, elapsed_ms=0, duration_ms=1,
    ))
    trace = SimpleNamespace(trace_id=uuid4(), world_id="world", turn_id=uuid4(),
                            conversation_id=uuid4(), observations=[step])
    authority = SimpleNamespace(managed_world_id="world", native_world_id="native",
                                binding_version=3, graph_revision="rev")
    turn = SimpleNamespace(world_id="world", turn_id=trace.turn_id, conversation_id=trace.conversation_id,
                           graph_context_receipt=SimpleNamespace(graph_authority=authority))
    service = Mock()
    service.list_context_trace_attempts.return_value = [trace]
    service.inspect_turn.return_value = turn
    return trace, authority, service


def test_writer_marker_uses_completed_writer_and_respects_attempt_bounds(saved_lookup):
    from application_state.agent_conversation.context_trace import TraceSourcePassage
    from application_state.agent_conversation.context_trace_store import _writer_evidence_sequences

    trace, _, _ = saved_lookup
    trace.terminal_status = "completed"
    trace.execution_start_sequence = 5
    graph_id = str(trace.observations[0].execution_event_id)
    source_id = uuid4()
    trace.observations.append(TraceSourcePassage.model_construct(sequence=3, source_read_event_id=source_id))
    trace.observations.append(TraceSourcePassage.model_construct(sequence=4, source_read_event_id=uuid4()))
    writer = {"kind": "plan_jev_writer_authorized_v2", "sequence": 6,
              "provider_attempt_id": "writer", "included_graph_event_ids": [graph_id],
              "included_source_read_event_ids": [str(source_id)]}
    completion = {"kind": "completion_binding", "sequence": 8, "provider_attempt_id": "writer"}
    execution = {"events": [writer, completion]}
    assert _writer_evidence_sequences(trace, execution, 9) == [2, 3]
    assert _writer_evidence_sequences(trace, execution, 8) is None
    completion["provider_attempt_id"] = "different-writer"
    assert _writer_evidence_sequences(trace, execution, None) is None


@pytest.mark.parametrize(("sequence", "stop", "expected"), [
    (4, None, "another attempt"),
    (8, 8, "another attempt"),
    (6, None, "not enough values to unpack"),
])
def test_scoped_native_read_rejects_wrong_attempt_or_missing_record(monkeypatch, sequence, stop, expected):
    from contextlib import nullcontext
    from application_state import unit_of_work
    from application_state.agent_conversation import context_trace_store, service
    from application_state.agent_conversation.native_replay import load_native_replay_read

    trace = SimpleNamespace(world_id="world", turn_id=uuid4(), conversation_id=uuid4(),
                            trace_id=uuid4(), attempt=1, execution_start_sequence=5)
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = (
        trace.conversation_id, "base", {}, {"events": []}, trace.attempt, {}, stop,
    )
    monkeypatch.setattr(unit_of_work, "unit_of_work", lambda _: nullcontext(conn))
    monkeypatch.setattr(service, "_ready_dsn", lambda: "test")
    monkeypatch.setattr(context_trace_store, "_load_trace", lambda _: trace)
    with pytest.raises(ValueError, match=expected):
        load_native_replay_read(world_id=trace.world_id, turn_id=trace.turn_id,
                               trace_id=trace.trace_id, sequence=sequence, assertion_id="claim")
    assert conn.execute.call_args.args[1] == (trace.world_id, trace.turn_id, trace.trace_id)


def test_native_replay_projects_only_the_attempt_and_writer_inclusion():
    from application_state.agent_conversation.native_replay import native_assertion_steps

    read = {"kind": "native_plan_assertion_read_observed_v2", "sequence": 6, "event_id": "read",
            "reads": [{"assertion": {"assertion_id": "assertion", "subject_entity_id": "subject",
                                     "predicate": "dnd5e:classification",
                                     "value": {"kind": "term_ref", "term": "dnd5e:character"}}},
                      {"assertion": {"assertion_id": "connection", "subject_entity_id": "subject",
                                     "predicate": "dungeonbuddy:works_with",
                                     "value": {"kind": "entity_ref", "entity_id": "other"}}}],
            "unavailable_assertion_ids": ["missing"]}
    writer = {"kind": "native_writer_authorized_v1", "sequence": 8, "provider_attempt_id": "writer",
              "native_read_event_ids": ["read"]}
    completion = {"kind": "completion_binding", "sequence": 9, "provider_attempt_id": "writer"}
    execution = {"events": [read, writer, completion]}
    receipt = {"native_query": {"authority": {"revision_id": "pinned"},
                                "object_matches": [{"entity_id": "subject", "label": "Caelynn"},
                                                   {"entity_id": "other", "label": "Not read"}]}}
    steps = native_assertion_steps(execution, receipt, start=5, stop=None)
    assert [step.model_dump() for step in steps] == [
        {"sequence": 6, "revision_id": "pinned", "assertion_ids": ["assertion", "connection"],
         "subject_ids": ["subject"], "assertion_ids_by_subject": {"subject": ["connection", "assertion"]}, "subject_labels": {"subject": "Caelynn"}, "subject_kinds": {"subject": "character"},
         "related_labels": {"other": "Not read"}, "unavailable_count": 1, "writer_evidence": True}
    ]
    assert not native_assertion_steps(execution, receipt, start=5, stop=9)[0].writer_evidence
    assert native_assertion_steps(execution, receipt, start=7, stop=None) == []


def test_replay_assertion_uses_exact_saved_graph_pin(saved_lookup, monkeypatch):
    trace, _, service = saved_lookup
    read = Mock(return_value={"assertion": {"assertion_id": "claim:0"}})
    monkeypatch.setattr(replay, "read_assertion", read)
    principal = object()
    response = replay.open_replay_assertion(service=service, principal=principal, world_id="world",
        turn_id=trace.turn_id, trace_id=trace.trace_id, sequence=2, assertion_id="claim:0")
    pin, caller, identity = read.call_args.args
    assert (pin.managed_world_id, pin.native_world_id, pin.binding_version, pin.revision_id) == ("world", "native", 3, "rev")
    assert caller is principal and identity == "claim:0"
    assert response["assertion"]["assertion_id"] == "claim:0"


@pytest.mark.parametrize("change", ["trace", "step", "claim", "world", "revision"])
def test_replay_rejects_mismatch_before_graph_read(saved_lookup, monkeypatch, change):
    trace, authority, service = saved_lookup
    read = Mock()
    monkeypatch.setattr(replay, "read_assertion", read)
    arguments = dict(service=service, principal=object(), world_id="world", turn_id=trace.turn_id,
                     trace_id=trace.trace_id, sequence=2, assertion_id="claim:0")
    if change == "revision":
        authority.graph_revision = "later"
    else:
        name, value = {"trace": ("trace_id", uuid4()), "step": ("sequence", 1),
                       "claim": ("assertion_id", "foreign"), "world": ("world_id", "foreign")}[change]
        arguments[name] = value
    with pytest.raises(replay.InspectionUnavailable):
        replay.open_replay_assertion(**arguments)
    read.assert_not_called()
