import json
import os

import pytest

from apps.live_control_server.services.hermes_graph_agent_contract import (
    HermesGraphAgentTurnResult, decode_json_wire, encode_json_wire, serialize_hermes_graph_agent_turn_result,
)
from apps.live_control_server.services.hermes_graph_agent_host import HermesGraphAgentHost
from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter
from tests.test_hermes_graph_agent_host import _request, _synthetic_request_budget


def _context_worker(request_queue, response_queue):
    def send(value):
        response_queue.put(encode_json_wire(value))
    send({"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            return
        if message.get("type") != "execute":
            continue
        request_id = message["requestId"]
        send({"type": "accepted", "requestId": request_id})
        proceed = decode_json_wire(request_queue.get())
        if proceed.get("type") == "shutdown":
            return
        if proceed.get("type") != "proceed":
            continue
        from apps.live_control_server.services.agent_context_compaction_report import compaction_report
        from apps.live_control_server.services.agent_conversation_context import compact_conversation_context
        history = [{"role": "user", "content": "Tell me about Mirathorn."},
                   {"role": "assistant", "content": "An established communications fact."}]
        report = compaction_report(history, compact_conversation_context(history)).model_dump(mode="json")
        if os.environ.get("DMB_TEST_CONTEXT_REPORT_MALFORMED") == "1":
            report["unrecognized"] = "unexpected"
        operation_id = f"{request_id}:g1"
        send({"type": "graph_operation_request", "requestId": request_id, "operationId": operation_id,
              "toolName": "observe_context_compaction", "arguments": report})
        reply = decode_json_wire(request_queue.get(timeout=10))
        ok = reply.get("operationId") == operation_id and json.loads(reply["resultJson"]).get("schema") == "dmb_context_compaction_ack_v1"
        result = HermesGraphAgentTurnResult(status="ok" if ok else "error", final_response="observed" if ok else None,
            messages=[], hermes_session_id="synthetic-context-worker", tool_events=[],
            error_code=None if ok else "observation_unavailable", error_message=None if ok else "invalid acknowledgement")
        send({"type": "result", "requestId": request_id, "payload": serialize_hermes_graph_agent_turn_result(result)})


@pytest.mark.parametrize("malformed", [False, True])
def test_real_worker_delivers_compaction_to_parent_without_provider_or_graph_authority(monkeypatch, malformed):
    monkeypatch.setenv("DMB_CONTEXT_TRACE_CAPTURE", "1")
    monkeypatch.setenv("DMB_TEST_CONTEXT_REPORT_MALFORMED", "1" if malformed else "0")
    adapter = _PolicyExecutionAdapter.__new__(_PolicyExecutionAdapter)
    adapter.fence = None
    adapter.context_compaction_report = None
    adapter.context_compaction_unavailable = False
    budget = {**_synthetic_request_budget(), "maxProviderAttempts": 4,
              "maxToolCapableAttempts": 3, "maxGraphOperations": 8}
    host = HermesGraphAgentHost(worker_target=_context_worker)
    try:
        result = host.execute(_request(provider_authorization_required=True, parent_graph_broker_required=True,
            request_budget=budget, retrieval_session_id="parent-session", retrieval_session={"retrieval_session_id": "parent-session"}),
            on_provider_authorization=lambda view: pytest.fail("observation must not dispatch a provider"),
            on_graph_operation=adapter.broker_graph_operation)
        assert result.status == "ok", (result.error_code, result.error_message)
        assert adapter.fence is None
        assert adapter.context_compaction_unavailable == malformed
        if malformed:
            assert adapter.context_compaction_report is None
        else:
            assert adapter.context_compaction_report.before_visible[0].text == "Tell me about Mirathorn."
            assert adapter.context_compaction_report.after_visible[-1].text == "An established communications fact."
    finally:
        host.shutdown()
