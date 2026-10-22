"""Overlap independent native reads; admit their results sequentially in the parent."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_jev_decision import current_selection
from graph_memory.retrieval.models import WorldGraphObjectRequest


def object_request(adapter, node):
    return WorldGraphObjectRequest.model_validate({
        "schema": "dmb_world_graph_object_request_v1",
        "worldId": adapter.bootstrap.world_scope.world_id, "campaignId": "", "scopeMode": "world",
        "focus": {"kind": "none", "sessionId": None, "campaignId": None},
        "admissibility": "gm", "revisionPin": adapter.bootstrap.world_scope.revision_id, "nodeId": node,
    })


class ObjectAcquisition:
    def __init__(self, futures):
        self.futures = futures

    def consume(self, request):
        # No fallback read: a wrong request or second consumption is a host defect.
        key = request.model_dump_json(by_alias=True)
        if key not in self.futures:
            raise ValueError("Plan object acquisition differs from its selected request")
        return self.futures.pop(key).result()


def _read(request):
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        direct_services_from_config, get_object_with_reviewed_sources_direct_v3,
    )
    services = direct_services_from_config(request.world_id)
    return services, get_object_with_reviewed_sources_direct_v3(services, request)


@contextmanager
def object_acquisition(adapter, nodes):
    nodes = tuple(nodes)
    if not nodes:
        yield
        return
    execution = adapter._broker_execution() if adapter.fence is not None else None
    if (adapter.failure is not None or adapter.fence is None
            or not isinstance(execution, t.PlanWorldGraphExecutionV3)
            or not isinstance(execution.policy, t.PlanJevRetrievalPolicyV1)
            or getattr(adapter, "_plan_object_acquisition", None) is not None):
        raise ValueError("Plan object acquisition requires its current decision")
    selection = current_selection(adapter.fence.turn)
    expected = {handle for handle in selection.selected_handles if handle.startswith("node:")}
    if (selection.operation != "select_candidates" or len(nodes) != len(set(nodes))
            or {f"node:{node}" for node in nodes} != expected):
        raise ValueError("Plan object acquisition differs from its selected targets")
    requests = [object_request(adapter, node) for node in nodes]
    # Workers only do native IO. All APP events and session mutations remain on
    # the calling thread, in the original selected order. Shutdown always joins.
    wave = ObjectAcquisition({})
    adapter._plan_object_acquisition = wave
    try:
        # Resource scheduling for the 8 GB client target; every selected read is
        # queued, with no limit on candidate or evidence content.
        with ThreadPoolExecutor(max_workers=min(4, len(requests)), thread_name_prefix="plan-native-read") as executor:
            wave.futures.update({request.model_dump_json(by_alias=True): executor.submit(_read, request)
                                 for request in requests})
            yield
    finally:
        # The executor has joined even on an exception before reopening inference.
        adapter._plan_object_acquisition = None
