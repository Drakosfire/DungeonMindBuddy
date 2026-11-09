"""Plan-owned actual Jev dispatch. Host bindings never enter model state."""
from hashlib import sha256
from contextlib import nullcontext
import json
from generationengine import GenerationEngineError
from time import perf_counter
from uuid import UUID, uuid4

from application_state.agent_conversation import types as t
from application_state.agent_conversation.jev_retrieval_contract import (
    MODEL, PROVIDER, RetrievalDecisionInput, PlanSourceRetrievalDecisionInputV1, decode_selection,
    prepare_decision, validate_prepared_decision, validate_wire_body,
)
from application_state.agent_conversation.plan_jev_decision import scope_digest
from application_state.agent_conversation.plan_authoring import (
    PlanRequestedWorkInputV1, decode_requested_work_decision, prepare_requested_work_decision,
    validate_prepared_requested_work, validate_requested_work_wire,
)

from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV2, PlanRequestedWorkInputV7, PlanRequestedWorkInputV8, work_choice


def request_budget():
    from .agent_turn_service import _policy_request_budget
    budget = _policy_request_budget()
    return budget | {"provider": PROVIDER, "model": MODEL, "apiMode": "decision",
        "providerRoles": {
            "controller": {"provider": PROVIDER, "model": MODEL, "api_mode": "decision"},
            "writer": {"provider": "openai", "model": budget["model"], "api_mode": "responses"},
        }}


def decision_client(*, authorize, record, transport=None, api_key=None, select_context=None):
    from generationengine import GenerationClient
    from generationengine.decision_dispatch import DecisionDispatchGate
    from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
    options = {"dispatch_gate": DecisionDispatchGate(authorize, record, select_context), "transport": transport}
    if api_key is not None: options["api_key"] = api_key
    return GenerationClient(decision_providers={PROVIDER: TypeSafeDecisionProvider(**options)})


def verify_initial_input(view, request, work, parent):
    from .agent_turn_service import _governed_graph_turn
    from application_state.agent_conversation.jev_retrieval_contract import NativePlayRetrievalDecisionInputV1
    if request.surface.surface_id=='play':
        if (type(parent) is not NativePlayRetrievalDecisionInputV1 or not _governed_graph_turn(request)
                or work.play_context_receipt is None or parent.question!=request.message
                or (view.get('provider'),view.get('model'),view.get('apiMode'))!=(PROVIDER,MODEL,'decision')):
            raise ValueError('Play Jev requires its exact governed Run question and provider')
        raw=view['payloadJson'].encode()
        if len(raw)!=view['payloadUtf8Bytes'] or sha256(raw).hexdigest()!=view['payloadSha256']:
            raise ValueError('Play Jev wire bytes changed before claim')
        validate_wire_body(parent,raw)
        return
    if (not isinstance(parent, (RetrievalDecisionInput, PlanSourceRetrievalDecisionInputV1, PlanRequestedWorkInputV1)) or request.surface.surface_id != "plan"
            or not _governed_graph_turn(request) or work.content_basis is None
            or not isinstance(work.plan_markdown, str) or parent.question != request.message
            or (view.get("provider"), view.get("model"), view.get("apiMode")) != (PROVIDER, MODEL, "decision")):
        raise ValueError("Plan Jev requires its exact governed Plan question and provider")
    raw = view["payloadJson"].encode()
    if len(raw) != view["payloadUtf8Bytes"] or sha256(raw).hexdigest() != view["payloadSha256"]:
        raise ValueError("Plan Jev wire bytes changed before claim")
    (validate_requested_work_wire if isinstance(parent, PlanRequestedWorkInputV1) else validate_wire_body)(parent, raw)


class PlanJevDispatch:
    """One actual GE call, durable dispatch gate and typed-result admission.

    No retries or fallback. The parent creates the candidate catalog; neither
    returned labels nor model choices create evidence or authorize a source read.
    """
    def __init__(self, adapter, candidates, *, dialogue=(), examined_candidates=(), allowed_operations=("select_candidates", "discover_more", "finish_retrieval")):
        self.adapter = adapter
        fields = dict(request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256="0" * 64,
            question=adapter.request.message, dialogue=tuple(dialogue), candidates=tuple(candidates),
            examined_candidates=tuple(examined_candidates), allowed_operations=tuple(allowed_operations))
        receipt = adapter.fence.turn.graph_context_receipt if adapter.fence is not None else None
        authority = getattr(adapter, "native_source_authority", None)
        if adapter.request.surface.surface_id=='play' and authority is not None:
            from application_state.agent_conversation.jev_retrieval_contract import NativePlayRetrievalDecisionInputV1
            from application_state.agent_conversation.native_play_work import project_work
            from application_state.agent_conversation.native_context import PlayWorkContextV1
            from .plan_source_turn import play_work_proof
            from .agent_turn_service import _conversation_provenance,_turn_idempotency_key
            proof=play_work_proof(adapter.request,adapter.work,dialogue)
            frame=t.PlaySourceFrameV1.model_validate_json(json.dumps(proof['source_frame']))
            work=PlayWorkContextV1(play_basis=adapter.work.play_context_receipt,
                play_sources=frame.manifest,play_source_frame_sha256=t.canonical_sha256(frame))
            provenance=(adapter.fence.turn.provenance if adapter.fence is not None else
                _conversation_provenance(adapter.request,world_id=adapter.world_id,work=adapter.work,
                    playable_target=adapter.playable_target))
            from application_state.agent_conversation.native_corpus import NativeCorpusAuthorityV1
            from application_state.agent_conversation.native_plan_statements import NativePlanQueryV1
            available=isinstance(authority,NativeCorpusAuthorityV1)
            query=adapter.native_query
            pins=dict(source_authority_status='available' if available else 'unavailable',
                source_revision=authority.revision_id if available else None,
                graph_revision=query.authority.revision_id if isinstance(query,NativePlanQueryV1) else None)
            self.parent=NativePlayRetrievalDecisionInputV1(**fields,**pins,play_work=project_work(
                work,provenance,_turn_idempotency_key(adapter.world_id,adapter.request.turn_id),proof))
        elif type(receipt) is t.SurfaceNativeContextReceiptV1:
            from application_state.agent_conversation.native_retrieval import source_pins
            from application_state.agent_conversation.jev_retrieval_contract import NativeRetrievalDecisionInputV2, NativeBuildRetrievalDecisionInputV4
            codec = (NativeBuildRetrievalDecisionInputV4
                if receipt.work_context.surface_id == "build" else NativeRetrievalDecisionInputV2)
            self.parent = codec(**fields,**source_pins(receipt))
        elif authority is not None:
            from application_state.agent_conversation.native_corpus import NativeCorpusAuthorityV1
            available = isinstance(authority, NativeCorpusAuthorityV1)
            from application_state.agent_conversation.plan_jev_decision import _source_pins
            pins = (_source_pins(adapter.fence.turn.graph_context_receipt)
                if adapter.fence is not None else dict(
                    source_authority_status="available" if available else "unavailable",
                    source_revision=authority.revision_id if available else None,
                    graph_revision=adapter.bootstrap.world_scope.revision_id if adapter.bootstrap is not None else None))
            self.parent = PlanSourceRetrievalDecisionInputV1(**fields,**pins)
        else:
            self.parent = RetrievalDecisionInput(**fields, revision=adapter.bootstrap.world_scope.revision_id)
        self.prepared = None
        self.authorization = None
        self.selection = None
        self.call = None

    @classmethod
    def requested_work(cls, adapter, *, page_title, dialogue=()):
        """Use the same one-shot provider gate for the separate destination choice."""
        dispatch = cls(adapter, (), dialogue=dialogue)
        capture = adapter.request.plan_authoring_capture
        references = adapter.request.authored_references
        operation = adapter.request.plan_requested_operation
        parent_type = PlanRequestedWorkInputV8 if isinstance(adapter.request.plan_context_policy,t.PlanContextPolicyV2) else PlanRequestedWorkInputV7
        dispatch.parent = parent_type(
            plan_requested_operation=operation, authored_references=references,
            request_id=uuid4(), parent_attempt_id=uuid4(),
            scope_sha256='0' * 64, question=adapter.request.message, page_title=page_title,
            dialogue=tuple(row.model_dump() if hasattr(row, 'model_dump') else row for row in dialogue),
            target_capture_sha256=capture.sha256 if capture is not None else None,
            target_available=capture is not None, placement_catalog=adapter.request.plan_placement_catalog, original_capture=capture)
        return dispatch

    def _native_accounting(self):
        if self.adapter.fence is None:
            return None
        from application_state.agent_conversation.native_retrieval import controller_accounting
        return controller_accounting(self.adapter.fence.turn.graph_context_execution)

    def _host_phase(self):
        from application_state.agent_conversation.jev_retrieval_contract import NativeBuildRetrievalDecisionInputV3
        return "navigate" if isinstance(self.parent, NativeBuildRetrievalDecisionInputV3) else None

    async def select_context(self, prepared):
        from generationengine.decision_dispatch import DecisionContextMode
        if self._native_accounting() is None:
            return DecisionContextMode.DEFAULT
        accounting = self.adapter._build_jev_accounting
        if accounting.descriptor != self._native_accounting():
            raise ValueError("Native Build decision counter differs from its actual policy")
        return DecisionContextMode(accounting.context_mode(json.loads(prepared.body), host_phase=self._host_phase()))

    def authorize(self, prepared):
        trace = getattr(self.adapter, "trace", None)
        with trace.measure_host_work('controller_authorization') if trace is not None else nullcontext():
            from .agent_turn_service import AgentTurnServiceError, _json_node_count, _require_fresh_execution_append
            semantic = isinstance(self.parent, PlanRequestedWorkInputV1)
            if semantic:
                validate_prepared_requested_work(self.parent,prepared)
            else:
                validate_prepared_decision(self.parent,prepared,controller_accounting=self._native_accounting())
            a = self.adapter
            if (a.failure is not None or self.prepared is not None
                    or getattr(a, "_build_native_acquisition_services", None) is not None
                    or getattr(a, "_plan_graph_read_services", None) is not None):
                return False
            native_build = self._native_accounting() is not None
            view = {"provider": PROVIDER, "model": MODEL, "apiMode": "decision",
                "payloadJson": prepared.body.decode(), "payloadSha256": prepared.body_sha256,
                "payloadUtf8Bytes": prepared.body_size}
            if native_build:
                from .build_jev_dispatch import prepared_view
                if a._build_jev_accounting.descriptor != self._native_accounting():
                    raise ValueError("Native Build decision counter differs from its actual policy")
                view=prepared_view(prepared,json.loads(prepared.body)["state"],accounting=a._build_jev_accounting,host_phase=self._host_phase())
            else:
                a._active_plan_jev_request = self.parent
                try:
                    a._ensure_claimed(view)
                except AgentTurnServiceError as exc:
                    a.failure = exc
                    raise
                finally:
                    a._active_plan_jev_request = None
            if a.request.surface.surface_id=='play' and not any(isinstance(e,t.ProviderAttemptAuthorizedEventV1)
                    for e in a.fence.turn.graph_context_execution.events):
                from .native_authored_references import acquire
                acquire(a)
            turn = a.fence.turn
            execution = turn.graph_context_execution
            native = not semantic and type(turn.graph_context_receipt) is t.SurfaceNativeContextReceiptV1
            if native:
                from application_state.agent_conversation.native_retrieval import scope_digest as selected_scope
            else:
                selected_scope = scope_digest
            self.parent = self.parent.model_copy(update={"parent_attempt_id": UUID(prepared.attempt_id),
                "scope_sha256": selected_scope(turn)})
            raw = view["payloadJson"]
            estimate = (a._build_jev_accounting.estimate(json.loads(raw)) if native_build else
                len(raw.encode()) + 64 * (1 + _json_node_count(json.loads(raw))))
            if not native_build and a.budget["contextLimitTokens"] is not None and estimate + a.budget["outputReserveTokens"] > a.budget["contextLimitTokens"]:
                raise ValueError("Plan Jev actual request exceeds the existing provider context allowance")
            from application_state.agent_conversation.native_retrieval import NativeRetrievalAuthorizedV1
            auth_type = t.PlanRequestedWorkAuthorizedV2 if isinstance(self.parent, PlanRequestedWorkInputV2) else t.PlanRequestedWorkAuthorizedV1 if semantic else NativeRetrievalAuthorizedV1 if native else t.PlanJevProviderAuthorizedV1
            build_context = dict(context_mode=view["contextMode"],context_phase=view["contextPhase"],
                max_question_input_tokens=view["maxQuestionInputTokens"],dispatch_identity_sha256=view["dispatchIdentitySha256"]) if native_build else None
            auth = auth_type(kind='plan_requested_work_authorized_v2' if isinstance(self.parent, PlanRequestedWorkInputV2) else 'plan_requested_work_authorized_v1' if semantic else 'native_retrieval_authorized_v1' if native else 'plan_jev_provider_authorized_v1', event_id=uuid4(),
                sequence=len(execution.events), provider_attempt_id=UUID(prepared.attempt_id),
                decision_request_id=self.parent.request_id, parent_request_sha256=self.parent.digest,
                envelope_sha256=prepared.body_sha256, serializer_version="typesafe-sdk-json-v1",
                provider=PROVIDER, model=MODEL, api_mode=view["apiMode"], tool_schema_sha256=sha256(b"[]").hexdigest(),
                input_accounting_kind="estimated_token_count" if native_build else "conservative_upper_bound",
                input_estimator=execution.policy.controller_continuation_accounting.policy if native_build else a.budget["estimator"],
                input_tokens=estimate, output_token_reserve=0 if native_build else a.budget["outputReserveTokens"],
                included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
                included_graph_event_ids=[], included_source_read_event_ids=[],**({"build_context":build_context} if native else {}))
            a.turn = _require_fresh_execution_append(a.fence.append("authorize_plan_jev_provider", "authorization", auth,
                producer_proof={"parent_request_json": self.parent.model_dump_json(by_alias=True), "request_json": raw}))
            a.last_provider_attempt_id = auth.provider_attempt_id
            a._capture_prepared_prompt(view, auth)
            self.prepared, self.authorization = prepared, auth
            return True

    def record(self, event):
        trace = getattr(self.adapter, "trace", None)
        with trace.measure_host_work('controller_lifecycle_acknowledgement') if trace is not None else nullcontext():
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
        trace = getattr(self.adapter, "trace", None)
        with trace.measure_host_work('controller_selection_acknowledgement') if trace is not None else nullcontext():
            from .agent_turn_service import _require_fresh_execution_append
            if self.prepared is None or self.authorization is None or self.selection is not None:
                raise ValueError("Plan decision has no unique actual authorized producer")
            a = self.adapter
            raw = result.model_dump_json()
            from application_state.agent_conversation.native_retrieval import NativeRetrievalAuthorizedV1, NativeRetrievalSelectedV1
            native = type(self.authorization) is NativeRetrievalAuthorizedV1
            capture_name = "unvalidated-native-retrieval-result" if native else "unvalidated-plan-jev-result"
            a.context_capture.observe({"kind": "context_snapshot", "stage": "after", "materials": [{
                "item_id": f"{capture_name}:{self.authorization.provider_attempt_id}",
                "state": "model_context", "role": "assistant", "text": raw}]})
            semantic = isinstance(self.parent, PlanRequestedWorkInputV1)
            selected = (decode_requested_work_decision if semantic else decode_selection)(self.parent, result)
            turn = a.fence.turn
            execution = turn.graph_context_execution
            placement = isinstance(self.parent, PlanRequestedWorkInputV2)
            selected_fields = (work_choice(self.parent, selected) | {
                'original_capture_sha256': self.parent.target_capture_sha256,
                'original_capture': self.parent.original_capture.model_dump(mode='json',by_alias=True) if self.parent.original_capture is not None else None,
                'placement_catalog': self.parent.placement_catalog.model_dump(mode='json',by_alias=True) if self.parent.placement_catalog is not None else None,
                'placement_catalog_sha256': self.parent.placement_catalog.sha256 if self.parent.placement_catalog is not None else None,
            }) if placement else {'requested_work': selected, 'target_capture_sha256': self.parent.target_capture_sha256} if semantic else {'operation': selected.operation, 'selected_handles': list(selected.selected_handles)}
            from application_state.agent_conversation.native_execution import NativePlanRequestedWorkSelectedV3
            current_work = isinstance(self.parent, PlanRequestedWorkInputV8)
            event_type = NativePlanRequestedWorkSelectedV3 if current_work else t.PlanRequestedWorkSelectedV2 if placement else t.PlanRequestedWorkSelectedV1 if semantic else NativeRetrievalSelectedV1 if native else t.PlanJevRetrievalSelectionV1
            event = event_type(kind='plan_requested_work_selected_v3' if current_work else 'plan_requested_work_selected_v2' if placement else 'plan_requested_work_selected_v1' if semantic else 'native_retrieval_selected_v1' if native else 'plan_jev_retrieval_selected_v1', event_id=uuid4(),
                sequence=len(execution.events), context_receipt_sha256=execution.context_receipt_sha256,
                execution_policy_sha256=execution.execution_policy_sha256,
                controller_attempt_id=self.authorization.provider_attempt_id, decision_request_id=self.parent.request_id,
                controller_envelope_sha256=self.prepared.body_sha256, parent_request_sha256=self.parent.digest,
                controller_response_sha256=sha256(raw.encode()).hexdigest(),
                **selected_fields,
                actual_input_tokens=result.observation.input_tokens,
                actual_output_tokens=result.observation.output_tokens)
            a.turn = _require_fresh_execution_append(a.fence.append('record_plan_requested_work_selection' if semantic else 'record_plan_jev_retrieval_selection', "selection", event,
                producer_proof={"parent_request_json": self.parent.model_dump_json(by_alias=True),
                    "request_json": self.prepared.body.decode(), "response_json": raw}))
            if not semantic and selected.operation == "finish_retrieval" and result.answers["operation"].selected == "finish_with_gaps":
                a.context_capture.observe({"kind": "failure", "phase": "graph_retrieval",
                                           "code": "controller_finished_with_gaps"})
            self.selection_event = event
            self.selection = selected_fields["requested_work"] if placement else selected
            return self.selection

    async def run(self, *, transport=None, api_key=None, client=None):
        trace = getattr(self.adapter, "trace", None)
        with trace.measure_host_work('controller_round') if trace is not None else nullcontext():
            async def authorize(prepared): return self.authorize(prepared)
            async def record(event): return self.record(event)
            owns_client = client is None
            if owns_client:
                client = decision_client(authorize=authorize, record=record, transport=transport, api_key=api_key,select_context=self.select_context)
            started = perf_counter()
            try:
                prepare = prepare_requested_work_decision if isinstance(self.parent, PlanRequestedWorkInputV1) else prepare_decision
                result = await client.decide(prepare(self.parent) if isinstance(self.parent,PlanRequestedWorkInputV1)
                    else prepare(self.parent,controller_accounting=self._native_accounting()))
                observation = result.observation
                if self.call is not None:
                    counts = {"input_tokens": observation.input_tokens, "output_tokens": observation.output_tokens}
                    usage = {"status": "reported" if any(value is not None for value in counts.values()) else "unavailable", **counts}
                    if all(value is not None for value in counts.values()): usage["total_tokens"] = sum(counts.values())
                    self.call.update(status="ok", response_model=observation.response_model, usage=usage)
                return self.acknowledge(result), result
            except GenerationEngineError as exc:
                # A trusted host rejection retains its public code; an SDK failure
                # cannot invent one from exception text or response bodies.
                from .agent_turn_service import AgentTurnServiceError
                rejection = self.adapter.failure
                if self.adapter.context_capture is not None:
                    self.adapter.context_capture.observe({"kind": "failure",
                        "phase": "context_build" if isinstance(rejection, AgentTurnServiceError) else "provider",
                        "code": rejection.code if isinstance(rejection, AgentTurnServiceError)
                            else "plan_jev_" + exc.failure.code.value.lower()})
                if isinstance(rejection, AgentTurnServiceError):
                    raise rejection from exc
                raise
            finally:
                try:
                    if self.call is not None:
                        self.call["duration_ms"] = (perf_counter() - started) * 1000
                        self.adapter.context_capture.provider_usage([self.call])
                finally:
                    if owns_client: await client.aclose()
