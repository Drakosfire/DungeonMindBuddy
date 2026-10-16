"""Parent pages survive the actual Harness reservation and next-request guard."""

from types import SimpleNamespace
import json
from uuid import uuid4

import pytest

from apps.live_control_server.services.graph_tool_presentation import (
    GraphToolPresentation,
)
from apps.live_control_server.services.graph_tool_transport import (
    GraphToolPageCache,
    TransportScope,
)
from apps.live_control_server.services.hermes_graph_agent import (
    _GraphOperationReservation,
    _request_budget_guard,
)
from tests.test_graph_tool_transport import SCOPE, ARGS, _raw


def parent_broker(parent, reads, *, batch=False):
    def broker(tool, args):
        try:
            if "resultPageToken" in args:
                return parent.continuation(tool, args), None
            reads.append(tool)
            raw = (
                _raw()
                if tool == "expand_graph_retrieval"
                else json.dumps(
                    {
                        "schema": "dmb_world_graph_source_anchor_read_v1"
                        if tool == "read_graph_source"
                        else "dmb_related_recap_context_read_v2",
                        "outcome": "truncated",
                        "truncated": True,
                        "content": "qualified passage. " * 1000,
                    }
                )
            )
            if batch and tool == "read_graph_source":
                raw = json.dumps(
                    {
                        "schema": "dmb_read_graph_source_batch_v1",
                        "retrievalSessionId": parent.scope.retrieval_session_id,
                        "reads": [
                            {
                                "schema": "dmb_world_graph_source_anchor_read_v1",
                                "sourceReadId": f"read:{i}",
                                "anchorId": f"anchor:{i}",
                                "outcome": "enough",
                                "truncated": False,
                                "content": "qualified batch passage. " * 300,
                            }
                            for i in range(2)
                        ],
                    }
                )
            return parent.present(tool, args, raw, uuid4()), None
        except ValueError as exc:
            return json.dumps(
                {
                    "schema": "dmb_world_graph_retrieval_error_v1",
                    "code": str(exc),
                    "statusCode": 409,
                }
            ), None

    return broker


@pytest.mark.parametrize(
    "tool",
    ["expand_graph_retrieval", "read_graph_source", "read_related_recap_context"],
)
def test_initial_read_counts_once_continuations_at_cap_never_repeat_io(tool):
    parent = GraphToolPresentation(SCOPE)
    reads = []
    reserve = _GraphOperationReservation(
        1,
        parent_broker(parent, reads),
        source_limit=0 if tool == "expand_graph_retrieval" else 1,
        context_limit=1 if tool == "read_related_recap_context" else 0,
        scope=SCOPE,
    )
    fake_agent = SimpleNamespace(tools=["transport-capable-tool"])
    reserve.agents.append(fake_agent)
    first, _ = reserve(tool, ARGS)
    value = json.loads(first)
    assert not reserve.indeterminate
    assert sum([reserve.count, reserve.source_count, reserve.context_count]) == 1
    assert fake_agent.tools  # Read cap cannot hide still-needed transport pages.
    token = value.get("detailPageToken") or value["nextPageToken"]
    args = {**ARGS, "resultPageToken": token}
    page, _ = reserve(tool, args)
    assert reserve(tool, args)[0] == page
    assert len(reads) == 1 and not reserve.indeterminate
    assert sum([reserve.count, reserve.source_count, reserve.context_count]) == 1
    if tool != "expand_graph_retrieval":
        assert json.loads(page)["coreTruncated"] is True
        assert json.loads(page)["outcome"] == "truncated"
    assert json.loads(reserve(tool, ARGS)[0])["code"] == "graph_operation_over_budget"
    assert fake_agent.tools
    assert reserve(tool, args)[0] == page
    assert len(reads) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("worldId", "foreign"),
        ("revisionId", "foreign"),
        ("retrievalSessionId", "foreign"),
        ("tool", "read_graph_source"),
        ("resultSchema", "unknown"),
        ("resultSchema", {}),
        ("coreTruncated", "false"),
        ("view", []),
        ("resultId", ""),
    ],
)
def test_malformed_or_foreign_wrapper_retains_indeterminate_guard(field, value):
    parent = GraphToolPresentation(SCOPE)
    wrapped = json.loads(
        parent.present("expand_graph_retrieval", ARGS, _raw(), uuid4())
    )
    wrapped[field] = value
    reserve = _GraphOperationReservation(
        1, lambda *_: (json.dumps(wrapped), None), scope=SCOPE
    )
    fake_agent = SimpleNamespace(tools=["tool"])
    reserve.agents.append(fake_agent)
    reserve("expand_graph_retrieval", ARGS)
    assert reserve.indeterminate and not fake_agent.tools and reserve.count == 0


def test_uncertain_broker_failure_still_retires_tools():
    def broker(*_):
        raise OSError("synthetic disconnected broker")

    reserve = _GraphOperationReservation(1, broker, scope=SCOPE)
    fake_agent = SimpleNamespace(tools=["tool"])
    reserve.agents.append(fake_agent)
    with pytest.raises(OSError):
        reserve("expand_graph_retrieval", ARGS)
    assert reserve.indeterminate and not fake_agent.tools


@pytest.mark.parametrize("change", ["expired", "foreign"])
def test_parent_denial_is_feedback_without_new_read_or_uncertainty(change):
    now = [0.0]
    parent = GraphToolPresentation(
        SCOPE, cache=GraphToolPageCache(clock=lambda: now[0], lifetime=1)
    )
    reads = []
    reserve = _GraphOperationReservation(1, parent_broker(parent, reads), scope=SCOPE)
    first = json.loads(reserve("expand_graph_retrieval", ARGS)[0])
    args = {**ARGS, "resultPageToken": first["detailPageToken"]}
    if change == "expired":
        now[0] = 2
    else:
        args["queryText"] = "different"
    result = json.loads(reserve("expand_graph_retrieval", args)[0])
    assert result["statusCode"] == 409 and not reserve.indeterminate
    assert len(reads) == 1 and reserve.count == 1


@pytest.mark.parametrize(
    "kind", ["overview", "source-page", "small", "continuation-at-cap", "source-batch"]
)
def test_actual_reservation_plugin_sdk_and_next_provider_guard(
    tmp_path, monkeypatch, kind
):
    from tests.test_hermes_graph_dispatch_adapter import _agent, _call
    from tests.test_hermes_graph_agent import _default_scope
    from apps.live_control_server.services.hermes_graph_agent import (
        hermes_import_namespace,
    )
    from apps.live_control_server.services.hermes_graph_dispatch_adapter import (
        install_graph_serial_dispatch,
    )
    import graph_memory.hermes_graph_plugin as plugin

    harness = _agent(tmp_path, monkeypatch)
    policy = plugin.default_graph_only_capability_policy(_default_scope())
    scope = TransportScope(
        "session:one", policy.graph_scope.world_id, policy.graph_scope.revision_pin
    )
    parent = GraphToolPresentation(scope)
    reads = []
    broker = parent_broker(parent, reads, batch=kind == "source-batch")
    tool = (
        "read_graph_source"
        if kind in {"source-page", "source-batch"}
        else "expand_graph_retrieval"
    )
    if kind == "small":

        def broker(tool, args):
            reads.append(tool)
            return (
                '{"schema":"dmb_world_graph_retrieval_result_v1","outcome":"empty"}',
                None,
            )

    reserve = _GraphOperationReservation(1, broker, source_limit=1, scope=scope)
    pt = plugin.set_active_capability_policy(policy)
    st = plugin.set_active_retrieval_session_id("session:one")
    bt = plugin.set_parent_graph_broker(reserve, required=True)
    try:
        with hermes_import_namespace():
            import run_agent
            from agent.transports.codex import ResponsesApiTransport

            monkeypatch.setattr(
                run_agent,
                "handle_function_call",
                lambda name, args, *a, **kw: plugin._handler_for(name)(args),
            )
            install_graph_serial_dispatch(harness)
            call = _call(0)
            call.function.name = tool
            assistant = {
                "role": "assistant",
                "content": "",  # Pinned conversation loop normalizes tool-turn content.
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": tool,
                            "arguments": call.function.arguments,
                        },
                    }
                ],
            }
            messages = [assistant]
            harness._execute_tool_calls(
                SimpleNamespace(tool_calls=[call], content=None),
                messages,
                "task:one",
                7,
            )
            if kind == "continuation-at-cap":
                first = json.loads(messages[-1]["content"])
                continuation_call = _call(1)
                continuation_call.function.arguments = json.dumps(
                    {
                        "queryText": "keeper 0",
                        "resultPageToken": first["detailPageToken"],
                    }
                )
                messages.append(
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": continuation_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool,
                                    "arguments": continuation_call.function.arguments,
                                },
                            }
                        ],
                    }
                )
                harness._execute_tool_calls(
                    SimpleNamespace(tool_calls=[continuation_call], content=None),
                    messages,
                    "task:one",
                    7,
                )
                assert reserve.count == 1 and len(reads) == 1
            provider = ResponsesApiTransport().build_kwargs(
                model="gpt-6-luna",
                messages=messages,
                max_tokens=2048,
                replay_encrypted_reasoning=False,  # Actual guarded SDK builder disables opaque replay.
                request_overrides={"parallel_tool_calls": False},
            )
            payload = json.dumps(provider)
            view = SimpleNamespace(
                provider="openai-api",
                model="gpt-6-luna",
                api_mode="codex_responses",
                payload_json=payload,
                payload_utf8_bytes=len(payload.encode()),
            )
            admitted = []
            guard = _request_budget_guard(
                {
                    "provider": "openai-api",
                    "model": "gpt-6-luna",
                    "apiMode": "codex_responses",
                    "estimator": "utf8_json_bytes_plus_64_per_node_v1",
                    "contextLimitTokens": 1000000,
                    "outputReserveTokens": 2048,
                },
                on_provider_authorization=lambda v: admitted.append(v) or True,
                graph_outcome_indeterminate=lambda: reserve.indeterminate,
            )
            allowed = guard(view)
            assert allowed is True and len(admitted) == 1, guard.guard_state
            assert not reserve.indeterminate and len(reads) == 1
            if kind != "small":
                shown = next(
                    item["output"]
                    for item in provider["input"]
                    if item.get("type") == "function_call_output"
                )
                assert parent.inclusion(tool, [shown])
    finally:
        plugin.reset_parent_graph_broker(bt)
        plugin.reset_active_retrieval_session_id(st)
        plugin.reset_active_capability_policy(pt)


def test_real_batch_contract_has_no_aggregate_outcome_and_survives_all_pages():
    parent = GraphToolPresentation(SCOPE)
    reads = []
    reserve = _GraphOperationReservation(
        0,
        parent_broker(parent, reads, batch=True),
        source_limit=1,
        context_limit=0,
        scope=SCOPE,
    )
    first, _ = reserve("read_graph_source", ARGS)
    page = json.loads(first)
    assert page["resultSchema"] == "dmb_read_graph_source_batch_v1"
    assert page["outcome"] is None
    assert reserve.source_count == 1 and not reserve.indeterminate
    pages = [first]
    while page.get("nextPageToken"):
        result, _ = reserve(
            "read_graph_source", {**ARGS, "resultPageToken": page["nextPageToken"]}
        )
        pages.append(result)
        page = json.loads(result)
    assert len(pages) > 1 and len(reads) == 1
    assert reserve.source_count == 1 and not reserve.indeterminate
    assert parent.inclusion("read_graph_source", pages)[0].complete


def test_uncapped_reservations_keep_all_tools_and_count_actual_reads():
    parent = GraphToolPresentation(SCOPE)
    reads = []
    reservation = _GraphOperationReservation(None, parent_broker(parent, reads), source_limit=None, context_limit=None, scope=SCOPE)
    agent = SimpleNamespace(tools=["expand_graph_retrieval", "read_graph_source", "read_related_recap_context"])
    reservation.agents.append(agent)
    for tool in agent.tools:
        for _ in range(10):
            result = json.loads(reservation(tool, ARGS)[0])
            assert result["schema"] in {"dmb_graph_tool_page_v1", "dmb_graph_tool_overview_v1"}
            assert not reservation.indeterminate and len(agent.tools) == 3
    assert (reservation.count, reservation.source_count, reservation.context_count) == (10, 10, 10)
    assert len(reads) == 30
    policy = {
        "provider": "openai-api", "model": "synthetic-model", "apiMode": "chat_completions",
        "estimator": "utf8_json_bytes_plus_64_per_node_v1", "contextLimitTokens": 32768, "outputReserveTokens": 100,
        "maxProviderAttempts": None, "maxToolCapableAttempts": None, "maxGraphOperations": None,
    }
    dispatched = []
    guard = _request_budget_guard(policy, on_provider_authorization=lambda view: dispatched.append(view) or True,
        on_provider_lifecycle=lambda _: True, graph_outcome_indeterminate=lambda: reservation.indeterminate)
    guard.bind_agent.append(agent)
    payload = json.dumps({"model": "synthetic-model", "messages": [{"role": "user", "content": "Continue with tools"}],
        "max_completion_tokens": 100, "tools": [{"type": "function", "function": {"name": "read_graph_source", "parameters": {"type": "object"}}}]})
    view = SimpleNamespace(provider="openai-api", model="synthetic-model", api_mode="chat_completions",
        payload_json=payload, payload_utf8_bytes=len(payload.encode()))
    for _ in range(10):
        assert guard(view)
        assert guard.provider_lifecycle({"transition": "response_received"})
        assert len(agent.tools) == 3
    assert len(dispatched) == 10
    huge = SimpleNamespace(**(vars(view) | {"payload_utf8_bytes": 50000}))
    assert guard(huge) is False
    assert guard.guard_state["last_rejection_reason"] == "context_budget_exceeded"
    assert len(dispatched) == 10
