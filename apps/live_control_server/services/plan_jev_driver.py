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
        self.attempted_nodes, self.attempted_anchors = set(), set()
        self.discovered = adapter.bootstrap.completed_discovery_query == adapter.request.message
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

    def _collect_candidates(self, session):
        for row in session.get("candidates", []):
            if row.get("kind") != "node" or not row.get("label") or not row.get("id"):
                continue
            node = row["id"]
            self.catalog.setdefault(f"node:{node}", (node, RetrievalCandidate(
                handle=f"node:{node}", label=row["label"], kind="World entity")))

    def offered(self):
        if self.finished:return ()
        result = [candidate for node, candidate in self.catalog.values() if node not in self.attempted_nodes]
        if self.rules is not None and not self.rules.selected:
            result.append(rules_candidate())
        result.extend(self.native_sources.offered())
        return tuple(result)

    def _graph_read(self, operation, node=None):
        a = self.adapter
        arguments = {"retrievalSessionId": a.bootstrap.retrieval_session.id, "operation": operation}
        if node is not None: arguments["targets"] = [{"kind": "node", "id": node}]
        else: arguments["queryText"] = a.request.message
        before = set(a.operation_payloads)
        reply = a.broker_graph_operation({"toolName": "expand_graph_retrieval", "arguments": arguments})
        if a.failure is not None: raise a.failure
        if isinstance(reply.get("retrievalSession"), dict): self._collect_candidates(reply["retrievalSession"])
        added = set(a.operation_payloads) - before
        for identity in added:
            packet = json.loads(a.operation_payloads[identity])
            self._collect_candidates({"candidates": [{"kind": "node", "id": node.get("nodeId"),
                "label": node.get("label")} for node in packet.get("nodes", [])]})
        if len(added) != 1:
            self.gaps.append(json.loads(reply["resultJson"]).get("code", "graph_read_unavailable"))
        return added

    def _read_new_sources(self, operations):
        """Union overlapping object anchors before IO; every exact pin is tried once.

        Source batches retain the current owner's existing cardinality and text
        allowances. A partial/unknown read is never silently retried as complete.
        """
        a = self.adapter
        pins = a._broker_execution().effective_source_pins()
        pending = {}
        for event_id in operations:
            packet = json.loads(a.operation_payloads[event_id])
            for row in packet.get("sourceAnchors", []):
                anchor = row.get("anchorId")
                if not row.get("readable") or anchor not in pins:
                    continue
                pin = pins[anchor]
                identity = (pin.anchor_id, pin.evidence_ref_id, pin.source_artifact_id, pin.source_revision_id)
                if identity not in self.attempted_anchors: pending[anchor] = identity
        anchors = sorted(pending)
        if not anchors:
            return
        def exhausted(unread):
            # A host refusal is terminal for these exact pins in this turn.
            # Persist its qualification through the same protected trace the
            # writer uses; an in-memory diagnostic is not producing authority.
            self.attempted_anchors.update(pending[anchor] for anchor in unread)
            if "source_read_over_budget" not in self.gaps:
                self.gaps.append("source_read_over_budget")
                a.context_capture.observe({"kind": "failure", "phase": "source_read",
                                           "code": "source_read_over_budget"})
        execution = a._broker_execution()
        if t.source_read_character_usage(execution.policy, execution.events) >= execution.policy.max_source_read_chars:
            exhausted(anchors)
            return
        with a.source_read_acquisition(anchors):
            while anchors:
                execution = a._broker_execution()
                remaining = execution.policy.max_source_read_chars - t.source_read_character_usage(
                    execution.policy, execution.events)
                if remaining <= 0:
                    exhausted(anchors)
                    break
                max_chars = min(execution.policy.max_chars_per_source_read, remaining)
                count = min(8, len(anchors), remaining // max_chars)
                batch, anchors = anchors[:count], anchors[count:]
                self.attempted_anchors.update(pending[anchor] for anchor in batch)
                before = set(a.source_payloads)
                reply = a.broker_source_read({"toolName": "read_graph_source", "arguments": {
                    "retrievalSessionId": a.bootstrap.retrieval_session.id, "anchorIds": batch,
                    "maxChars": max_chars}}, bundle_internal=True)
                if a.failure is not None: raise a.failure
                if not set(a.source_payloads) - before:
                    self.gaps.append(json.loads(reply["resultJson"]).get("code", "source_read_unavailable"))

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
            operations.update(self._graph_read("search"))
        else:
            offered = {candidate.handle for candidate in dispatch.parent.candidates}
            if not set(selected.selected_handles) <= offered:
                raise ValueError("Plan selection changed its offered catalog")
            native_handles = {candidate.handle for candidate in self.native_sources.offered()}
            nodes = [self.catalog[handle][0] for handle in selected.selected_handles
                     if handle != rules_candidate().handle and handle not in native_handles]
            if any(node in self.attempted_nodes for node in nodes):
                raise ValueError("Plan object cannot be reacquired")
            with self.adapter.plan_graph_acquisition(nodes):
                for handle in selected.selected_handles:
                    if handle in native_handles:
                        try:
                            self.native_sources.select([handle])
                        except (ValueError,ApplicationStateValidationError):
                            self.native_sources.unavailable('source_navigation_unavailable')
                        continue
                    if handle == rules_candidate().handle:
                        if self.rules is None or self.rules.selected: raise ValueError("Plan Rules offer was already used")
                        self.rules.lookup_selected(dispatch.parent.model_dump_json(by_alias=True))
                        continue
                    node, _ = self.catalog[handle]
                    if node in self.attempted_nodes: raise ValueError("Plan object cannot be reacquired")
                    self.attempted_nodes.add(node)  # mark before IO, including failures
                    operations.update(self._graph_read("object", node))
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
        return {"graph_packets": packets, "source_names": names, "plan_markdown": a.work.plan_markdown,
                "session_evidence": sessions, "dialogue": self.dialogue}
