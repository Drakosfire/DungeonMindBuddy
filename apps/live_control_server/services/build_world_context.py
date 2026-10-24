"""Typed Build adapter over the shared parent Graph/source brokers."""
import json

from application_state.agent_conversation import types as t
from application_state.agent_conversation.build_world_context import POLICY
from .build_jev_driver import AcquisitionBinding
from .build_jev_transitions import WorldReadAction
from .world_source_acquisition import read_operation_sources


class BuildWorldContext:
    def __init__(self, adapter):
        self.adapter = adapter
        self.actions = {}
        self.attempted_pins, self.gaps = set(), []
        self.discovered = adapter.bootstrap.completed_discovery_query == adapter.request.message
        self.collect(adapter.bootstrap.retrieval_session.project_for_hermes())
        self.collect({"candidates": [{"kind": "node", "id": identity, "label": label}
                                     for identity, label in adapter.bootstrap.navigation_candidates]})
        if not self.discovered:
            self.actions["world-search"] = WorldReadAction(id="world-search", kind="world_search",
                label="Search the current World for other locations, people and source context requested in the question")

    def collect(self, payload):
        candidates = payload.get("candidates", []) + [{"kind": "node", "id": n.get("nodeId"), "label": n.get("label")}
                                                      for n in payload.get("nodes", [])]
        for row in candidates:
            if row.get("kind") != "node" or not row.get("id") or not row.get("label"):
                continue
            identity = "world-object:" + row["id"]
            self.actions.setdefault(identity, WorldReadAction(id=identity, kind="world_object",
                label="World entity: " + row["label"] + "; open its actual source passages"))

    def arguments(self, action):
        args = {"retrievalSessionId": self.adapter.bootstrap.retrieval_session.id,
                "operation": "search" if action.kind == "world_search" else "object"}
        if action.kind == "world_search":
            args["queryText"] = self.adapter.request.message
        else:
            args["targets"] = [{"kind": "node", "id": action.id.removeprefix("world-object:")}]
        return args

    def acquire(self, actions):
        adapter = self.adapter
        execution = adapter._broker_execution()
        if getattr(execution.policy, "world_context_policy", None) != POLICY:
            raise ValueError("World read requires its explicit frozen Build capability")
        selections = [e for e in execution.events if isinstance(e, t.BuildWorldReadSelectionV1)]
        selected = selections[-1] if selections else None
        if selected is None or selected.controller_attempt_id != adapter.last_provider_attempt_id:
            raise ValueError("World read requires its current admitted controller choice")
        targets = {a.action_id: a for a in selected.actions}
        if {a.id for a in actions} != set(targets):
            raise ValueError("World read actions differ from the admitted selected wave")
        bindings = {}
        for action in actions:
            args = self.arguments(action)
            if t.canonical_sha256(args) != targets[action.id].request_arguments_sha256:
                raise ValueError("World read executable arguments changed")
            before = set(adapter.operation_payloads)
            reply = adapter.broker_graph_operation({"toolName": "expand_graph_retrieval", "arguments": args})
            if adapter.failure is not None:
                raise adapter.failure
            added = set(adapter.operation_payloads) - before
            if len(added) != 1:
                self.gaps.append(json.loads(reply["resultJson"]).get("code", "world_read_unavailable"))
            if isinstance(reply.get("retrievalSession"), dict):
                self.collect(reply["retrievalSession"])
            for identity in added:
                self.collect(json.loads(adapter.operation_payloads[identity]))
            if action.kind == "world_search":
                self.discovered = True
                bindings[action.id] = AcquisitionBinding(world_operation_ids=tuple(sorted(map(str, added))))
                continue
            # Reuse exact pins already attempted by primary-page reads in this turn.
            for event in adapter._broker_execution().events:
                if isinstance(event, t.ValidatedSourceReadEventV2):
                    self.attempted_pins.update((r.anchor_id, r.evidence_ref_id, r.source_artifact_id, r.source_revision_id)
                                               for r in event.receipts)
            read_operation_sources(adapter, added, self.attempted_pins, self.gaps)
            pins = {p.anchor_id for event in adapter._broker_execution().events if str(event.event_id) in set(map(str, added))
                    for p in getattr(event, "returned_source_pins", [])}
            reads = [str(e.event_id) for e in adapter._broker_execution().events
                     if isinstance(e, t.ValidatedSourceReadEventV2)
                     and e.receipts and all(r.outcome == "enough" and not r.truncated and r.evidence_sufficiency_status == "sufficient" for r in e.receipts)
                     and any(r.anchor_id in pins for r in e.receipts)]
            bindings[action.id] = AcquisitionBinding(world_operation_ids=tuple(sorted(map(str, added))),
                                                     source_event_ids=tuple(sorted(reads)))
        return bindings


def record_selection(driver, plan, prepared, response, actions):
    from uuid import uuid4
    from application_state.agent_conversation.build_world_context import scope_digest
    from .build_jev_driver import canonical, digest
    from .agent_turn_service import _require_fresh_execution_append
    from generationengine.types import DecisionResult
    a = driver._adapter
    if not isinstance(response, DecisionResult):
        raise ValueError("World action requires its actual typed controller result")
    raw = canonical(response.model_dump(mode="json"))
    a.context_capture.controller_decision_response(raw, producing_provider_attempt_id=a.last_provider_attempt_id)
    execution = a._broker_execution()
    authorization = next(e for e in execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV3)
                         and e.provider_attempt_id == a.last_provider_attempt_id)
    event = t.BuildWorldReadSelectionV1(kind="build_world_read_selected_v1", event_id=uuid4(), sequence=len(execution.events),
        context_receipt_sha256=execution.context_receipt_sha256, execution_policy_sha256=execution.execution_policy_sha256,
        controller_attempt_id=authorization.provider_attempt_id, controller_envelope_sha256=authorization.envelope_sha256,
        controller_response_sha256=digest(response.model_dump(mode="json")), machine_request_id=plan.request_id,
        scope_sha256=scope_digest(a.fence.turn), actions=[t.BuildWorldActionTargetV1(action_id=action.id,
            operation="search" if action.kind == "world_search" else "object",
            node_id=action.id.removeprefix("world-object:") if action.kind == "world_object" else None,
            request_arguments_sha256=digest(driver._world.arguments(action))) for action in actions])
    a.turn = _require_fresh_execution_append(a.fence.append("record_build_world_read_selection", "selection", event,
        producer_proof={"request_json": prepared.body.decode(), "response_json": raw}))
