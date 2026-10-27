"""Own native object/search lifetimes for acknowledged Plan selections."""
from contextlib import ExitStack, contextmanager
import json

from application_state.agent_conversation.rules_authority_types import canonical_sha256

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


def query_identity(query):
    return " ".join(query.split()).casefold()


def read_subject_labels(adapter):
    """Only validated current object packets supply search labels, never claims."""
    authority = adapter._broker_receipt().graph_authority if adapter.fence is not None else None
    if authority is None:
        return {}
    events = {e.event_id: e for e in adapter._broker_execution().events
              if isinstance(e, t.ValidatedGraphOperationEventV3)}
    labels = {}
    for identity, raw in adapter.operation_payloads.items():
        event = events.get(identity)
        if event is None or event.graph_revision != authority.graph_revision:
            continue
        packet = json.loads(raw)
        canonical = {key: value for key, value in packet.items()
                     if key not in {"retrievalSessionId", "addedClaimIds", "claimLedger"}}
        if canonical_sha256(canonical) != event.result_packet_sha256:
            raise ValueError("Plan subject packet differs from its validated operation")
        snapshot = packet.get("snapshot") or {}
        if (packet.get("operation") != "object" or packet.get("outcome") not in {"enough", "partial", "truncated"}
                or snapshot.get("worldId") != authority.native_world_id
                or snapshot.get("revisionId") != authority.graph_revision):
            continue
        node = packet.get("resolvedNodeId")
        rows = [row for row in packet.get("nodes", []) if row.get("nodeId") == node]
        if node and len(rows) == 1 and isinstance(rows[0].get("label"), str) and rows[0]["label"].strip():
            labels[node] = rows[0]["label"]
    return labels


class SubjectSearch(GraphReadServices):
    def __init__(self, adapter, selection, query):
        super().__init__(adapter.bootstrap.world_scope.world_id, ())
        self.selection_id, self.query = selection.event_id, query
        self.adapter, self.consumed = adapter, False

    def consume(self, request, selection):
        attempted = getattr(self.adapter, "_plan_subject_search_attempts", set())
        key = query_identity(self.query)
        if (self._closed or self.consumed or selection.event_id != self.selection_id
                or request.query_text != self.query or request.targets or request.observation_ids
                or key in attempted):
            raise ValueError("Plan subject search differs from its selected unused query")
        self.consumed = True
        self.adapter._plan_subject_search_attempts = attempted | {key}


@contextmanager
def subject_search_acquisition(adapter, dispatch, handle):
    """Held exact parent proof is valid only for this acknowledged in-process step."""
    selection = current_selection(adapter.fence.turn)
    parent, auth = dispatch.parent, dispatch.authorization
    candidates = [c for c in parent.candidates if c.handle == handle]
    labels = read_subject_labels(adapter)
    node = handle.removeprefix("mentions:")
    if (adapter.failure is not None or auth is None or dispatch.adapter is not adapter
            or getattr(adapter, "_plan_graph_read_services", None) is not None
            or selection.operation != "select_candidates" or handle not in selection.selected_handles
            or not handle.startswith("mentions:") or len(candidates) != 1
            or candidates[0].label != labels.get(node)
            or selection.parent_request_sha256 != parent.digest
            or selection.decision_request_id != parent.request_id
            or selection.controller_attempt_id != auth.provider_attempt_id
            or selection.controller_envelope_sha256 != auth.envelope_sha256):
        raise ValueError("Plan subject search requires its current offered canonical label")
    lifetime = SubjectSearch(adapter, selection, candidates[0].label)
    adapter._plan_graph_read_services = lifetime
    try:
        yield lifetime.query
    finally:
        try:
            lifetime.close()
        finally:
            adapter._plan_graph_read_services = None
