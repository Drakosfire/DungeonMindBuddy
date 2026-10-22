"""Plan-owned actual Jev dispatch. Host bindings never enter model state."""
from hashlib import sha256
import json
from time import perf_counter
from uuid import UUID, uuid4

from application_state.agent_conversation import types as t
from application_state.agent_conversation.jev_retrieval_contract import (
    MODEL, PROVIDER, RetrievalDecisionInput, decode_selection,
    prepare_decision, validate_prepared_decision, validate_wire_body,
)
from application_state.agent_conversation.plan_jev_decision import scope_digest


def request_budget():
    from .agent_turn_service import _policy_request_budget
    budget = _policy_request_budget()
    return budget | {"provider": PROVIDER, "model": MODEL, "apiMode": "decision",
        "providerRoles": {
            "controller": {"provider": PROVIDER, "model": MODEL, "api_mode": "decision"},
            "writer": {"provider": "openai", "model": budget["model"], "api_mode": "responses"},
        }}


def decision_client(*, authorize, record, transport=None, api_key=None):
    from generationengine import GenerationClient
    from generationengine.decision_dispatch import DecisionDispatchGate
    from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
    options = {"dispatch_gate": DecisionDispatchGate(authorize, record), "transport": transport}
    if api_key is not None: options["api_key"] = api_key
    return GenerationClient(decision_providers={PROVIDER: TypeSafeDecisionProvider(**options)})


def verify_initial_input(view, request, work, parent):
    from .agent_turn_service import _governed_graph_turn
    if (not isinstance(parent, RetrievalDecisionInput) or request.surface.surface_id != "plan"
            or not _governed_graph_turn(request) or work.content_basis is None
            or not isinstance(work.plan_markdown, str) or parent.question != request.message
            or (view.get("provider"), view.get("model"), view.get("apiMode")) != (PROVIDER, MODEL, "decision")):
        raise ValueError("Plan Jev requires its exact governed Plan question and provider")
    raw = view["payloadJson"].encode()
    if len(raw) != view["payloadUtf8Bytes"] or sha256(raw).hexdigest() != view["payloadSha256"]:
        raise ValueError("Plan Jev wire bytes changed before claim")
    validate_wire_body(parent, raw)


class PlanJevDispatch:
    """One actual GE call, durable dispatch gate and typed-result admission.

    No retries or fallback. The parent creates the candidate catalog; neither
    returned labels nor model choices create evidence or authorize a source read.
    """
    def __init__(self, adapter, candidates, *, dialogue=(), examined_candidates=(), allowed_operations=("select_candidates", "discover_more", "finish_retrieval")):
        self.adapter = adapter
        self.parent = RetrievalDecisionInput(request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256="0" * 64,
            revision=adapter.bootstrap.world_scope.revision_id, question=adapter.request.message,
            dialogue=tuple(dialogue), candidates=tuple(candidates), examined_candidates=tuple(examined_candidates),
            allowed_operations=tuple(allowed_operations))
        self.prepared = None
        self.authorization = None
        self.selection = None
        self.call = None

    def authorize(self, prepared):
        from .agent_turn_service import _json_node_count, _require_fresh_execution_append
        validate_prepared_decision(self.parent, prepared)
        a = self.adapter
        if (a.failure is not None or self.prepared is not None
                or getattr(a, "_build_native_acquisition_services", None) is not None
                or getattr(a, "_plan_object_acquisition", None) is not None):
            return False
        view = {"provider": PROVIDER, "model": MODEL, "apiMode": "decision",
            "payloadJson": prepared.body.decode(), "payloadSha256": prepared.body_sha256,
            "payloadUtf8Bytes": prepared.body_size}
        a._active_plan_jev_request = self.parent
        try:
            a._ensure_claimed(view)
        finally:
            a._active_plan_jev_request = None
        turn = a.fence.turn
        execution = turn.graph_context_execution
        self.parent = self.parent.model_copy(update={"parent_attempt_id": UUID(prepared.attempt_id),
            "scope_sha256": scope_digest(turn)})
        raw = view["payloadJson"]
        estimate = len(raw.encode()) + 64 * (1 + _json_node_count(json.loads(raw)))
        if estimate + a.budget["outputReserveTokens"] > a.budget["contextLimitTokens"]:
            raise ValueError("Plan Jev actual request exceeds the existing provider context allowance")
        auth = t.PlanJevProviderAuthorizedV1(kind="plan_jev_provider_authorized_v1", event_id=uuid4(),
            sequence=len(execution.events), provider_attempt_id=UUID(prepared.attempt_id),
            decision_request_id=self.parent.request_id, parent_request_sha256=self.parent.digest,
            envelope_sha256=prepared.body_sha256, serializer_version="typesafe-sdk-json-v1",
            provider=PROVIDER, model=MODEL, api_mode="decision", tool_schema_sha256=sha256(b"[]").hexdigest(),
            input_accounting_kind="conservative_upper_bound", input_estimator=a.budget["estimator"],
            input_tokens=estimate, output_token_reserve=a.budget["outputReserveTokens"],
            included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
            included_graph_event_ids=[], included_source_read_event_ids=[])
        a.turn = _require_fresh_execution_append(a.fence.append("authorize_plan_jev_provider", "authorization", auth,
            producer_proof={"parent_request_json": self.parent.model_dump_json(by_alias=True), "request_json": raw}))
        a.last_provider_attempt_id = auth.provider_attempt_id
        a._capture_prepared_prompt(view, auth)
        self.prepared, self.authorization = prepared, auth
        return True

    def record(self, event):
        if self.prepared is None or event.request != self.prepared:
            return False
        transition = {"sending": "sdk_entered", "known_not_sent": "known_not_sent",
            "response_received": "response_received", "outcome_unknown": "outcome_unknown"}.get(event.outcome)
        acknowledged = transition is not None and self.adapter.record_lifecycle({"transition": transition, "statusCode": event.http_status,
            "runtimeApiRequestId": f"generationengine:{self.prepared.attempt_id}"})
        if acknowledged and transition == "sdk_entered":
            self.call = {"provider": PROVIDER, "requested_model": MODEL,
                "runtime_api_request_id": f"generationengine:{self.prepared.attempt_id}",
                "status": "error", "usage": {"status": "unavailable"}}
        return acknowledged

    def acknowledge(self, result):
        from .agent_turn_service import _require_fresh_execution_append
        if self.prepared is None or self.authorization is None or self.selection is not None:
            raise ValueError("Plan decision has no unique actual authorized producer")
        a = self.adapter
        raw = result.model_dump_json()
        a.context_capture.observe({"kind": "context_snapshot", "stage": "after", "materials": [{
            "item_id": f"unvalidated-plan-jev-result:{self.authorization.provider_attempt_id}",
            "state": "model_context", "role": "assistant", "text": raw}]})
        selected = decode_selection(self.parent, result)
        turn = a.fence.turn
        execution = turn.graph_context_execution
        event = t.PlanJevRetrievalSelectionV1(kind="plan_jev_retrieval_selected_v1", event_id=uuid4(),
            sequence=len(execution.events), context_receipt_sha256=execution.context_receipt_sha256,
            execution_policy_sha256=execution.execution_policy_sha256,
            controller_attempt_id=self.authorization.provider_attempt_id, decision_request_id=self.parent.request_id,
            controller_envelope_sha256=self.prepared.body_sha256, parent_request_sha256=self.parent.digest,
            controller_response_sha256=sha256(raw.encode()).hexdigest(), operation=selected.operation,
            selected_handles=list(selected.selected_handles), actual_input_tokens=result.observation.input_tokens,
            actual_output_tokens=result.observation.output_tokens)
        a.turn = _require_fresh_execution_append(a.fence.append("record_plan_jev_retrieval_selection", "selection", event,
            producer_proof={"parent_request_json": self.parent.model_dump_json(by_alias=True),
                "request_json": self.prepared.body.decode(), "response_json": raw}))
        if selected.operation == "finish_retrieval" and result.answers["operation"].selected == "finish_with_gaps":
            a.context_capture.observe({"kind": "failure", "phase": "graph_retrieval",
                                       "code": "controller_finished_with_gaps"})
        self.selection = selected
        return selected

    async def run(self, *, transport=None, api_key=None, client=None):
        async def authorize(prepared): return self.authorize(prepared)
        async def record(event): return self.record(event)
        owns_client = client is None
        if owns_client:
            client = decision_client(authorize=authorize, record=record, transport=transport, api_key=api_key)
        started = perf_counter()
        try:
            result = await client.decide(prepare_decision(self.parent))
            observation = result.observation
            if self.call is not None:
                counts = {"input_tokens": observation.input_tokens, "output_tokens": observation.output_tokens}
                usage = {"status": "reported" if any(value is not None for value in counts.values()) else "unavailable", **counts}
                if all(value is not None for value in counts.values()): usage["total_tokens"] = sum(counts.values())
                self.call.update(status="ok", response_model=observation.response_model, usage=usage)
            return self.acknowledge(result), result
        finally:
            try:
                if self.call is not None:
                    self.call["duration_ms"] = (perf_counter() - started) * 1000
                    self.adapter.context_capture.provider_usage([self.call])
            finally:
                if owns_client: await client.aclose()
