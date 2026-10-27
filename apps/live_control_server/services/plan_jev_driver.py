"""Plan parent owns acquisitions; Jev selects semantic catalog entries only."""
import json

from application_state.agent_conversation import types as t
from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
from application_state.agent_conversation.plan_jev_rules_lookup import rules_candidate
from application_state.agent_conversation.plan_jev_decision import current_selection
from .plan_jev_dispatch import PlanJevDispatch, decision_client

_RUNTIME_GRAPH_FIELDS = {"retrievalSessionId", "addedClaimIds", "claimLedger"}


class PlanJevDriver:
    def __init__(self, adapter, *, dialogue=(), rules=None, retained_navigation=()):
        self.adapter, self.rules = adapter, rules
        from .native_source_navigation import navigator
        self.native_sources = navigator(adapter)
        self.dialogue = [{"role": item["role"], "content": item["content"]} for item in dialogue]
        self.catalog = {}
        self.node_kinds = {}
        self._remember_node_kinds(adapter.bootstrap.graph_envelope.get("nodes", []), "node_id")
        self.attempted_nodes, self.attempted_anchors = set(), set()
        self.discovered = adapter.bootstrap.completed_discovery_query == adapter.request.message
        from .plan_jev_acquisition import query_identity
        self.attempted_queries = ({query_identity(adapter.bootstrap.completed_discovery_query)}
            if adapter.bootstrap.completed_discovery_query else set())
        self.finished = False
        self.calls = []
        self.gaps = []
        self.current = None
        self._collect_candidates(adapter.bootstrap.retrieval_session.project_for_hermes())
        self._collect_candidates({"candidates": [{"kind": "node", "id": node, "label": label}
            for node, label in adapter.bootstrap.navigation_candidates]})
        for subject in retained_navigation:
            self.catalog.setdefault(f"node:{subject.node_id}", (subject.node_id, RetrievalCandidate(
                handle=f"node:{subject.node_id}", label=subject.label,
                kind=f"Previously explored {subject.kind}; navigation only, not current evidence")))

    def _remember_node_kinds(self, nodes, id_key):
        """Navigation metadata only; kinds never supply claims or read authority."""
        for node in nodes:
            node_id, kind = node.get(id_key), node.get("kind")
            if node_id and isinstance(kind, str) and kind.strip():
                self.node_kinds[node_id] = kind

    def _collect_candidates(self, session):
        for row in session.get("candidates", []):
            if row.get("kind") != "node" or not row.get("label") or not row.get("id"):
                continue
            node = row["id"]
            handle = f"node:{node}"
            kind = self.node_kinds.get(node)
            if handle not in self.catalog or kind is not None:
                self.catalog[handle] = (node, RetrievalCandidate(
                    handle=handle, label=row["label"],
                    kind=f"World entity: {kind}" if kind is not None else "World entity"))

    def offered(self):
        if self.finished:return ()
        result = [candidate for node, candidate in self.catalog.values() if node not in self.attempted_nodes]
        from .plan_jev_acquisition import query_identity, read_subject_labels
        seen = set(self.attempted_queries)
        for node, label in read_subject_labels(self.adapter).items():
            key = query_identity(label)
            if key not in seen:
                result.append(RetrievalCandidate(handle=f"mentions:{node}", label=label,
                    kind="Search other mentions of this explored World subject"))
                seen.add(key)
        if self.rules is not None and not self.rules.selected:
            result.append(rules_candidate())
        result.extend(self.native_sources.offered())
        return tuple(result)

    def _graph_read(self, operation, node=None, *, query=None):
        a = self.adapter
        arguments = {"retrievalSessionId": a.bootstrap.retrieval_session.id, "operation": operation}
        if node is not None: arguments["targets"] = [{"kind": "node", "id": node}]
        else: arguments["queryText"] = a.request.message if query is None else query
        before = set(a.operation_payloads)
        reply = a.broker_graph_operation({"toolName": "expand_graph_retrieval", "arguments": arguments})
        if a.failure is not None: raise a.failure
        if isinstance(reply.get("retrievalSession"), dict): self._collect_candidates(reply["retrievalSession"])
        added = set(a.operation_payloads) - before
        for identity in added:
            packet = json.loads(a.operation_payloads[identity])
            self._remember_node_kinds(packet.get("nodes", []), "nodeId")
            self._collect_candidates({"candidates": [{"kind": "node", "id": node.get("nodeId"),
                "label": node.get("label")} for node in packet.get("nodes", [])]})
        if len(added) != 1:
            self.gaps.append(json.loads(reply["resultJson"]).get("code", "graph_read_unavailable"))
        return added

    def _read_new_sources(self, operations):
        from .world_source_acquisition import read_operation_sources
        return read_operation_sources(self.adapter, operations, self.attempted_anchors, self.gaps)

    def apply(self, dispatch):
        if self.finished or dispatch is not self.current or dispatch.selection is None:
            raise ValueError("Plan acquisition requires its current acknowledged decision")
        admitted = current_selection(self.adapter.fence.turn)
        if (admitted.controller_attempt_id != dispatch.authorization.provider_attempt_id
                or admitted.decision_request_id != dispatch.parent.request_id
                or admitted.parent_request_sha256 != dispatch.parent.digest
                or admitted.controller_envelope_sha256 != dispatch.authorization.envelope_sha256
                or admitted.operation != dispatch.selection.operation
                or tuple(admitted.selected_handles) != dispatch.selection.selected_handles):
            raise ValueError("Plan acquisition decision is no longer current")
        selected = dispatch.selection
        self.current = None
        if selected.operation == "finish_retrieval":
            self.finished = True
            return
        from application_state.errors import ApplicationStateValidationError
        operations = set()
        if selected.operation == "discover_more":
            if self.discovered: raise ValueError("Plan discovery cannot repeat the same query")
            self.discovered = True
            from .plan_jev_acquisition import query_identity
            self.attempted_queries.add(query_identity(self.adapter.request.message))
            operations.update(self._graph_read("search"))
        else:
            offered = {candidate.handle for candidate in dispatch.parent.candidates}
            if not set(selected.selected_handles) <= offered:
                raise ValueError("Plan selection changed its offered catalog")
            native_handles = {candidate.handle for candidate in self.native_sources.offered()}
            nodes = [self.catalog[handle][0] for handle in selected.selected_handles
                     if handle.startswith("node:")]
            if any(node in self.attempted_nodes for node in nodes):
                raise ValueError("Plan object cannot be reacquired")
            with self.adapter.plan_graph_acquisition(nodes):
                for handle in selected.selected_handles:
                    if not handle.startswith("node:"):
                        continue
                    node, _ = self.catalog[handle]
                    if node in self.attempted_nodes: raise ValueError("Plan object cannot be reacquired")
                    self.attempted_nodes.add(node)  # mark before IO, including failures
                    operations.update(self._graph_read("object", node))
            self._read_new_sources(operations)
            from .plan_jev_acquisition import query_identity, subject_search_acquisition
            for handle in selected.selected_handles:
                if not handle.startswith("mentions:"):
                    continue
                with subject_search_acquisition(self.adapter, dispatch, handle) as query:
                    key = query_identity(query)
                    if key in self.attempted_queries:
                        raise ValueError("Plan subject query cannot repeat")
                    self.attempted_queries.add(key)  # consume even when IO fails
                    self._graph_read("search", query=query)
            for handle in selected.selected_handles:
                if handle in native_handles:
                    try:
                        self.native_sources.select([handle])
                    except (ValueError, ApplicationStateValidationError):
                        self.native_sources.unavailable('source_navigation_unavailable')
                elif handle == rules_candidate().handle:
                    if self.rules is None or self.rules.selected: raise ValueError("Plan Rules offer was already used")
                    self.rules.lookup_selected(dispatch.parent.model_dump_json(by_alias=True))
            return
        self._read_new_sources(operations)

    async def run(self, *, transport=None, api_key=None):
        async def authorize(prepared):
            return self.current.authorize(prepared) if self.current is not None else False
        async def record(event):
            return self.current.record(event) if self.current is not None else False
        client = decision_client(authorize=authorize, record=record, transport=transport, api_key=api_key)
        try:
            while not self.finished:
                operations = (("select_candidates", "finish_retrieval") if self.discovered else
                              ("select_candidates", "discover_more", "finish_retrieval"))
                examined = [candidate for node, candidate in self.catalog.values() if node in self.attempted_nodes]
                if self.rules is not None and self.rules.selected:
                    examined.append(rules_candidate())
                examined.extend(self.native_sources.examined())
                dispatch = PlanJevDispatch(self.adapter, self.offered(), dialogue=self.dialogue,
                    examined_candidates=examined, allowed_operations=operations)
                self.current = dispatch
                try:
                    await dispatch.run(client=client)
                finally:
                    if dispatch.call is not None: self.calls.append(dispatch.call)
                self.apply(dispatch)
            return self.proof()
        finally:
            await client.aclose()

    def proof(self):
        if not self.finished or self.adapter.failure is not None:
            raise ValueError("Plan writer cannot use unfinished acquisition")
        a = self.adapter
        names = {}
        for event in a._broker_execution().events:
            if not isinstance(event, t.SOURCE_PASSAGE_EVENTS) or event.event_id not in a.source_payloads:
                continue
            payload = json.loads(a.source_payloads[event.event_id])
            rows = payload.get("reads", [payload])
            titles = {row["anchorId"]: row.get("sourceName") for row in rows}
            for receipt in event.receipts:
                title = titles.get(receipt.anchor_id)
                if receipt.returned_chars and isinstance(title, str) and title.strip(): names[receipt.source_read_id] = title
        # Only strip known parent-added runtime fields. The canonical remainder
        # must still match the owning durable Graph operation digest at admission.
        packets = {identity: json.dumps({key: value for key, value in json.loads(raw).items()
            if key not in _RUNTIME_GRAPH_FIELDS}, ensure_ascii=False, separators=(",", ":"))
            for identity, raw in a.operation_payloads.items()}
        sessions = (a.work.session_evidence or {}).get("sessions", [])
        proof={"graph_packets": packets, "source_names": names, "plan_markdown": a.work.plan_markdown,
                "session_evidence": sessions, "dialogue": self.dialogue}
        if isinstance(a.fence.turn.graph_context_execution.policy,t.PlanAuthoringPolicyV1):
            proof['authoring_capture']=(a.request.plan_authoring_capture.model_dump(mode='json',by_alias=True)
                if a.request.plan_authoring_capture is not None else None)
        return proof
