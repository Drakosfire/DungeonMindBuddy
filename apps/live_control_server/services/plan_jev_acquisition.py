"""Own one lazy native object session for an acknowledged Plan selection."""
from contextlib import ExitStack, contextmanager

from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_jev_decision import current_selection


class GraphReadServices:
    def __init__(self, world_id, nodes):
        self.world_id = world_id
        self.services = None
        self.nodes = tuple(nodes)
        self._stack = ExitStack()
        self._bound = None
        self._closed = False

    def resolve(self):
        if self._closed:
            raise RuntimeError("Plan object acquisition is closed")
        # Resolve inside the broker's native_retrieval handler so native failures
        # retain its normal durable interruption/error qualification.
        if self.services is None:
            from apps.live_control_server.integrations.dungeonmind.world_graph_reads import direct_services_from_config
            self.services = direct_services_from_config(self.world_id)
        return self.services

    def for_object(self, request):
        services = self.resolve()
        if self._bound is None:
            from apps.live_control_server.integrations.dungeonmind.object_read_wave import object_read_wave
            self._bound = self._stack.enter_context(object_read_wave(
                services, request, object_ids=self.nodes))
        return self._bound

    def close(self):
        self._closed = True
        try:
            self._stack.close()
        finally:
            self._bound = None
            self.services = None


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
    adapter._plan_graph_read_services = GraphReadServices(adapter.bootstrap.world_scope.world_id, nodes)
    lifetime = adapter._plan_graph_read_services
    try:
        yield
    finally:
        try:
            lifetime.close()
        finally:
            adapter._plan_graph_read_services = None
