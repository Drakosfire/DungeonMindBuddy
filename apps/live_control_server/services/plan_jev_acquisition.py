"""Reuse a native dependency bundle within one selected acquisition, never read results."""
from contextlib import contextmanager

from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_jev_decision import current_selection


class GraphReadServices:
    def __init__(self, world_id):
        self.world_id = world_id
        self.services = None

    def resolve(self):
        # Resolve inside the broker's native_retrieval handler so native failures
        # retain its normal durable interruption/error qualification.
        if self.services is None:
            from apps.live_control_server.integrations.dungeonmind.world_graph_reads import direct_services_from_config
            self.services = direct_services_from_config(self.world_id)
        return self.services


@contextmanager
def graph_acquisition(adapter, nodes):
    nodes = tuple(nodes)
    if not nodes:
        yield
        return
    execution = adapter._broker_execution() if adapter.fence is not None else None
    if (adapter.failure is not None or adapter.fence is None
            or not isinstance(execution, t.PlanWorldGraphExecutionV3)
            or not isinstance(execution.policy, t.PlanJevRetrievalPolicyV1)
            or getattr(adapter, "_plan_graph_read_services", None) is not None):
        raise ValueError("Plan acquisition requires its current decision")
    selection = current_selection(adapter.fence.turn)
    expected = {handle for handle in selection.selected_handles if handle.startswith("node:")}
    if (selection.operation != "select_candidates" or len(nodes) != len(set(nodes))
            or {f"node:{node}" for node in nodes} != expected):
        raise ValueError("Plan acquisition differs from its selected targets")
    adapter._plan_graph_read_services = GraphReadServices(adapter.bootstrap.world_scope.world_id)
    try:
        yield
    finally:
        adapter._plan_graph_read_services = None
