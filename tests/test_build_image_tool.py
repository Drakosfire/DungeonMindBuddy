"""Real Harness image dispatch and APP origin fencing, with no inference."""

import json
from uuid import UUID
import psycopg
import pytest

from application_state.build_proposal.images import BuildImageService
from application_state.build_proposal.service import BuildProposalService
from application_state.errors import ApplicationStateNotFoundError
from apps.live_control_server.services.build_image_tool import (
    BuildImageTool,
    validate_included_results,
)
from apps.live_control_server.services.build_insertion_tool import arguments_digest
from tests.test_build_insertion_tool import request_case as _request_case, setup_tool


def image_tool(request, monkeypatch):
    original, _, wire, turn = setup_tool(request, monkeypatch)
    tool = BuildImageTool(
        original.capability,
        str(original.client_turn_id),
        lambda: turn,
        "local_operator",
    )
    message = {
        "toolName": "prepare_build_image",
        "operationId": "host:image1",
        "arguments": {
            "prompt": "Edge fort, peaceful guards, warm lanterns beside the swamp",
            "alt": "Edge at dusk",
        },
    }
    return tool, message, wire, turn


def test_durable_preparation_reload_and_no_provider(request_case, monkeypatch):
    request, source, root = request_case
    tool, message, wire, _ = image_tool(request, monkeypatch)
    reply = json.loads(tool.dispatch(message)["resultJson"])
    assert reply["status"] == "prepared" and wire.calls == []
    record = BuildImageService().get(UUID(reply["action_id"]), "local_operator")
    assert (
        record.prompt == message["arguments"]["prompt"] and record.alt == "Edge at dusk"
    )
    assert record.reservation.basis.document_id == source.record.document_id
    assert BuildImageService().list(
        "elderwyld", request.conversation_id, "local_operator"
    ) == [record]
    assert BuildProposalService().list("elderwyld", request.conversation_id) == []
    assert (
        json.loads(
            tool.dispatch({**message, "operationId": "host:image2"})["resultJson"]
        )
        == reply
    )
    assert (
        json.loads(
            tool.dispatch(
                {
                    **message,
                    "arguments": {**message["arguments"], "prompt": "Different"},
                }
            )["resultJson"]
        )["status"]
        == "unavailable"
    )
    assert (root / source.record.target_relpath).read_text() == source.markdown
    with pytest.raises(ApplicationStateNotFoundError):
        BuildImageService().get(record.action_id, "foreign-owner")


@pytest.mark.parametrize("failure", ["expired", "attempt", "foreign", "arguments"])
def test_no_preparation_for_lost_claim_or_forged_target(
    request_case, monkeypatch, application_state_dsn, failure
):
    request, _, _ = request_case
    tool, message, wire, turn = image_tool(request, monkeypatch)
    with psycopg.connect(application_state_dsn) as conn:
        if failure == "expired":
            conn.execute(
                "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
                (turn.turn_id,),
            )
        elif failure == "attempt":
            conn.execute(
                "UPDATE agent.turn SET attempt=attempt+1 WHERE turn_id=%s",
                (turn.turn_id,),
            )
        elif failure == "foreign":
            tool.client_turn_id = UUID(int=1)
        else:
            message["arguments"]["document_id"] = "foreign"
    assert json.loads(tool.dispatch(message)["resultJson"])["status"] == "unavailable"
    assert (
        wire.calls == []
        and BuildImageService().list(
            "elderwyld", request.conversation_id, "local_operator"
        )
        == []
    )


def test_parent_result_cannot_be_forged():
    args = {"prompt": "Quiet town", "alt": "Town"}
    output = '{"status":"prepared"}'
    body = {
        "input": [
            {
                "type": "function_call",
                "name": "prepare_build_image",
                "call_id": "1",
                "arguments": json.dumps(args),
            },
            {"type": "function_call_output", "call_id": "1", "output": output},
        ]
    }
    validate_included_results(body, {(arguments_digest(args), output)})
    with pytest.raises(ValueError):
        validate_included_results(body, set())
    body["input"][1]["output"] = '{"status":"generated"}'
    with pytest.raises(ValueError):
        validate_included_results(body, {(arguments_digest(args), output)})


def test_image_tool_crosses_runtime_policy_and_strict_ipc_only_with_captured_capability():
    from dataclasses import replace
    from tests.test_hermes_agent_runtime import (
        _FakeHost,
        _hermes_ok_result,
        _invocation,
    )
    from apps.live_control_server.services.hermes_agent_runtime import (
        HermesAgentRuntimeAdapter,
        map_invocation_to_hermes_request,
    )
    from apps.live_control_server.services.agent_runtime import (
        AgentCapabilityPolicy,
        AgentSurfaceContext,
        AgentCurrentWorkContext,
        WORLD_GRAPH_READ_POLICY,
    )
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        serialize_hermes_graph_agent_turn_request,
        deserialize_hermes_graph_agent_turn_request,
    )
    from apps.live_control_server.services.agent_turn_service import (
        _policy_request_budget,
    )
    from apps.live_control_server.services.hermes_graph_interaction_tools import (
        hermes_model_visible_tool_definitions,
    )

    class CapturingHost(_FakeHost):
        def execute(self, request, **kwargs):
            self.calls.append(request)
            assert callable(kwargs["on_graph_operation"]) and callable(
                kwargs["on_provider_authorization"]
            )
            return self.result

    host = CapturingHost(_hermes_ok_result())
    adapter = HermesAgentRuntimeAdapter(host_factory=lambda: host)
    base = _invocation()
    invocation = replace(
        base,
        capability_policy=AgentCapabilityPolicy(
            policy_id=WORLD_GRAPH_READ_POLICY.policy_id,
            surface_actions=("prepare_build_image",),
        ),
        context_packet=replace(
            base.context_packet,
            surface_context=AgentSurfaceContext(
                surface_id="build",
                current_work=AgentCurrentWorkContext(
                    kind="build", work_object_id="doc", title="Edge", object_revision=1
                ),
            ),
        ),
    )
    adapter.run_with_provider_authorization(
        invocation,
        lambda _: True,
        request_budget=_policy_request_budget(),
        on_graph_operation=lambda _: {},
    )
    request = host.calls[-1]
    assert "prepare_build_image" in request.capability_policy.enabled_tool_names
    assert (
        deserialize_hermes_graph_agent_turn_request(
            serialize_hermes_graph_agent_turn_request(request)
        ).capability_policy
        == request.capability_policy
    )
    assert (
        "prepare_build_image"
        not in map_invocation_to_hermes_request(
            base
        ).capability_policy.enabled_tool_names
    )
    definition = next(
        item
        for item in hermes_model_visible_tool_definitions()
        if item["function"]["name"] == "prepare_build_image"
    )
    assert set(definition["function"]["parameters"]["properties"]) == {"prompt", "alt"}


@pytest.fixture
def request_case(tmp_path, monkeypatch, application_state_dsn):
    return _request_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def _image_broker_worker(request_queue, response_queue):
    import os
    from tests.test_hermes_graph_agent_host import _put_json, _await_proceed_or_shutdown
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
        serialize_hermes_graph_agent_turn_result,
        HermesGraphAgentTurnResult,
    )

    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            return
        if message.get("type") != "execute":
            continue
        request_id = message["requestId"]
        _put_json(response_queue, {"type": "accepted", "requestId": request_id})
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            return
        operation = request_id + ":g1"
        _put_json(
            response_queue,
            {
                "type": "graph_operation_request",
                "requestId": request_id,
                "operationId": operation,
                "toolName": "prepare_build_image",
                "arguments": {
                    "prompt": "Edge beside a quiet swamp",
                    "alt": "Edge at dusk",
                },
            },
        )
        reply = decode_json_wire(request_queue.get(timeout=10))
        result = serialize_hermes_graph_agent_turn_result(
            HermesGraphAgentTurnResult(
                status="ok",
                final_response=reply["resultJson"],
                messages=[],
                hermes_session_id="image-worker",
                tool_events=[],
            )
        )
        _put_json(
            response_queue,
            {"type": "result", "requestId": request_id, "payload": result},
        )


def test_real_parent_ipc_dispatch_persists_image_action(request_case, monkeypatch):
    from tests.test_hermes_graph_agent_host import _request
    from apps.live_control_server.services.hermes_graph_agent_host import (
        HermesGraphAgentHost,
    )
    from apps.live_control_server.services.agent_turn_service import (
        _policy_request_budget,
    )

    request, _, _ = request_case
    tool, _, wire, _ = image_tool(request, monkeypatch)
    host = HermesGraphAgentHost(worker_target=_image_broker_worker)
    try:
        result = host.execute(
            _request(
                provider_authorization_required=True,
                parent_graph_broker_required=True,
                request_budget=_policy_request_budget(),
                retrieval_session_id="image-parent",
                retrieval_session={"retrieval_session_id": "image-parent"},
            ),
            on_provider_authorization=lambda _: True,
            on_graph_operation=tool.dispatch,
        )
        assert result.status == "ok", (result.error_code, result.error_message)
        reply = json.loads(result.final_response)
        assert reply["status"] == "prepared"
        assert (
            BuildImageService().get(UUID(reply["action_id"]), "local_operator").prompt
            == "Edge beside a quiet swamp"
        )
        assert wire.calls == []
    finally:
        host.shutdown()


def test_image_preparation_purpose_is_idempotency_bound(request_case, monkeypatch):
    from application_state.errors import ApplicationStateConflictError
    tool, message, _, _ = image_tool(request_case[0], monkeypatch)
    reply = json.loads(tool.dispatch(message)["resultJson"])
    original = BuildImageService().get(UUID(reply["action_id"]), "local_operator")
    with pytest.raises(ApplicationStateConflictError):
        BuildImageService().prepare(original.reservation, "local_operator", original.prompt,
                                    original.alt, purpose="map")
