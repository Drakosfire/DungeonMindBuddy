"""Plan-owned actual Jev dispatch. Host bindings never enter model state."""
from hashlib import sha256
from contextlib import nullcontext
import json
import httpx2
from generationengine import GenerationEngineError
from time import perf_counter
from uuid import UUID, uuid4

from .agent_turn_trace import host_work_observer

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


class _ObservedJevTransport(httpx2.AsyncBaseTransport):
    """Observe entry to the existing wire transport, behind the SDK dispatch gate."""

    def __init__(self, transport, on_dispatch):
        self.transport = transport
        self.on_dispatch = on_dispatch

    async def handle_async_request(self, request):
        self.on_dispatch()
        return await self.transport.handle_async_request(request)

    async def aclose(self):
        await self.transport.aclose()


def decision_client(*, authorize, record, transport=None, api_key=None, select_context=None, on_dispatch=None):
    from generationengine import GenerationClient
    from generationengine.decision_dispatch import DecisionDispatchGate
    from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
    if on_dispatch is not None:
        transport = _ObservedJevTransport(transport or httpx2.AsyncHTTPTransport(retries=0), on_dispatch)
    options = {"dispatch_gate": DecisionDispatchGate(authorize, record, select_context), "transport": transport}
    if api_key is not None: options["api_key"] = api_key
    return GenerationClient(decision_providers={PROVIDER: TypeSafeDecisionProvider(**options)})


def verify_initial_input(view, request, work, parent):
    from .agent_turn_service import _governed_graph_turn
    from application_state.agent_conversation.jev_retrieval_contract import NativePlayRetrievalDecisionInputV1
    if request.surface.surface_id=='play':
        if (not isinstance(parent, NativePlayRetrievalDecisionInputV1) or not _governed_graph_turn(request)
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
    def __init__(self, adapter, candidates, *, dialogue=(), examined_candidates=(), allowed_operations=("select_candidates", "discover_more", "finish_retrieval"), play_intent_opening=False):
        self.adapter = adapter
        fields = dict(request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256="0" * 64,
            question=adapter.request.message, dialogue=tuple(dialogue), candidates=tuple(candidates),
            examined_candidates=tuple(examined_candidates), allowed_operations=tuple(allowed_operations))
        receipt = adapter.fence.turn.graph_context_receipt if adapter.fence is not None else None
        authority = getattr(adapter, "native_source_authority", None)
        if adapter.request.surface.surface_id=='play' and authority is not None:
            from application_state.agent_conversation.jev_retrieval_contract import (
                NativePlayIntentDecisionInputV1, NativePlayRetrievalDecisionInputV1,
            )
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
            codec = NativePlayIntentDecisionInputV1 if play_intent_opening else NativePlayRetrievalDecisionInputV1
            self.parent=codec(**fields,**pins,play_work=project_work(
                work,provenance,_turn_idempotency_key(adapter.world_id,adapter.request.turn_id),proof))
        elif type(receipt) is t.SurfaceNativeContextReceiptV1:
            from application_state.agent_conversation.native_retrieval import source_expansion_selected, source_pins
            from application_state.agent_conversation.jev_retrieval_contract import NativeRetrievalDecisionInputV2, NativeBuildRetrievalDecisionInputV4
            codec = (NativeBuildRetrievalDecisionInputV4
                if receipt.work_context.surface_id == "build" else NativeRetrievalDecisionInputV2)
            from application_state.agent_conversation.native_corpus import initial_source_discovery_enabled
            if initial_source_discovery_enabled(adapter.fence.turn.graph_context_execution):
                from application_state.agent_conversation.jev_retrieval_contract import NativePlanBatchDecisionInputV3
                codec = NativePlanBatchDecisionInputV3
                fields['graph_relevance_version'] = 'v1'
                if source_expansion_selected(adapter.fence.turn):
                    fields['expanded_relevance_version'] = 'v1'
            self.parent = codec(**fields,**source_pins(receipt, adapter.fence.turn.graph_context_execution))
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
    def requested_work(cls, adapter, *, page_title, dialogue=(), candidates=(), examined_candidates=(),
            allowed_operations=('select_candidates', 'finish_retrieval'), author_scope=None):
        """Prepare the one actual opening producer selected by its admission codec."""
        dispatch = cls(adapter, (), dialogue=dialogue)
        capture = adapter.request.plan_authoring_capture
        references = adapter.request.authored_references
        operation = adapter.request.plan_requested_operation
        parent_type = PlanRequestedWorkInputV8 if isinstance(adapter.request.plan_context_policy,t.PlanContextPolicyV2) else PlanRequestedWorkInputV7
        from application_state.agent_conversation.native_context import NativePlanRequestAdmissionV1
        from application_state.agent_conversation.native_plan_opening import (
            NativePlanAuthorScopeObservedV1, NativePlanOpeningInputV2, NativePlanOpeningInputV3,
            bind_opening_author_scope, opening_input_type,
        )
        from application_state.agent_conversation.native_retrieval import source_pins
        opening = adapter.fence is not None and type(adapter.fence.turn.graph_context_receipt.assembled_input) is NativePlanRequestAdmissionV1
        if opening:
            parent_type = opening_input_type(adapter.fence.turn.graph_context_execution.policy.action)
            if parent_type in (NativePlanOpeningInputV2, NativePlanOpeningInputV3):
                page_title = adapter.fence.turn.graph_context_execution.policy.action.document_title or ''
        navigation = dict(candidates=tuple(candidates), examined_candidates=tuple(examined_candidates),
            allowed_operations=tuple(allowed_operations), **source_pins(adapter.fence.turn.graph_context_receipt)) if opening else {}
        if parent_type is NativePlanOpeningInputV2:
            navigation['evidence_relevance_version'] = 'v1'
            navigation['opening_graph_relevance_version'] = 'v1'
            navigation['implicit_caret_version'] = 'v1'
        elif parent_type is NativePlanOpeningInputV3:
            navigation['column_scope_version'] = 'v1'
            navigation['implicit_caret_version'] = 'v1'
        if author_scope is not None:
            if parent_type not in (NativePlanOpeningInputV2, NativePlanOpeningInputV3) or type(author_scope) is not NativePlanAuthorScopeObservedV1:
                raise ValueError('Bound opening requires its actual contextual author scope observation')
            navigation['author_scope_binding'] = bind_opening_author_scope(
                adapter.fence.turn.graph_context_execution,
                author_scope.event_id, author_scope.scope_observation)
        dispatch.parent = parent_type(
            plan_requested_operation=operation, authored_references=references,
            request_id=uuid4(), parent_attempt_id=uuid4(),
            scope_sha256='0' * 64, question=adapter.request.message, page_title=page_title,
            dialogue=tuple(row.model_dump() if hasattr(row, 'model_dump') else row for row in dialogue),
            target_capture_sha256=capture.sha256 if capture is not None else None,
            target_available=capture is not None, placement_catalog=adapter.request.plan_placement_catalog, original_capture=capture,
            **navigation)
        return dispatch

    def _native_accounting(self):
        if self.adapter.fence is None:
            return None
        from application_state.agent_conversation.native_retrieval import controller_accounting
        return controller_accounting(self.adapter.fence.turn.graph_context_execution)

    @classmethod
    def author_scope(cls, adapter, *, dialogue=(), prior_scope=None, review_scope=(), intent_opening=False):
        from application_state.agent_conversation.native_context import NativePlanRequestAdmissionV1, NativePlanSourcePendingV1
        from application_state.agent_conversation.native_execution import NativePlanActionV2, NativePlanActionV3
        from application_state.agent_conversation.native_plan_opening import (
            NativePlanAuthorScopeObservedV1, NativePlanAuthorScopeParentV1,
            NativePlanOpeningInputV2, NativePlanOpeningInputV3, NativePlanOpeningScopeBindingV1, opening_input_type,
            author_editor_focus, plan_intent_input, require_retained_author_scope,
        )

        turn = adapter.fence.turn
        admission = turn.graph_context_receipt.assembled_input
        if (type(admission) is not NativePlanRequestAdmissionV1
                or type(turn.graph_context_execution.policy.action) not in (
                    (NativePlanActionV2, NativePlanActionV3) if intent_opening else (NativePlanActionV3,)
                )):
            raise ValueError('Author scope requires an admitted contextual Plan turn')
        if prior_scope is not None and review_scope:
            raise ValueError('Author scope recheck and review require separate stages')
        for event in (prior_scope,) if prior_scope is not None else review_scope:
            if type(event) is not NativePlanAuthorScopeObservedV1:
                raise ValueError('Author scope follow-up requires the actual prior observation')
            require_retained_author_scope(turn.graph_context_execution,
                event.event_id, event.scope_observation)
        review = tuple(NativePlanOpeningScopeBindingV1(
            observation_event_id=event.event_id, observation=event.scope_observation) for event in review_scope)
        dispatch = cls(adapter, (), dialogue=dialogue)
        editor_focus = author_editor_focus(turn.graph_context_execution.policy.action)
        dispatch.parent = NativePlanAuthorScopeParentV1(
            question=turn.user_text, dialogue=tuple(dialogue), quote_context=prior_scope is not None,
            assess_page_edit=not review,
            selection_reference_version='v1',
            editor_focus=editor_focus,
            caret_guidance_version='v2' if editor_focus == 'caret' else None,
            implicit_caret_version=('v1' if opening_input_type(turn.graph_context_execution.policy.action)
                in (NativePlanOpeningInputV2, NativePlanOpeningInputV3) else None),
            requested_operation=adapter.request.plan_requested_operation if not review else None,
            max_span_attempts=2048, request_id=uuid4(), parent_attempt_id=uuid4(),
            scope_sha256=scope_digest(turn), request_manifest_sha256=admission.manifest_sha256,
            prior_scope_event_id=prior_scope.event_id if prior_scope is not None else None,
            scope_review=review or None,
            intent_opening=plan_intent_input(turn.graph_context_execution.policy.action, dialogue,
                source_use_version=('v2' if type(turn.graph_context_receipt.source_authority)
                                    is NativePlanSourcePendingV1 else None)) if intent_opening else None)
        return dispatch

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
            from application_state.agent_conversation.native_plan_opening import NativePlanAuthorScopeParentV1

            author_scope = type(self.parent) is NativePlanAuthorScopeParentV1
            semantic = author_scope or isinstance(self.parent, PlanRequestedWorkInputV1)
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
            elif not author_scope:
                a._active_plan_jev_request = self.parent
                try:
                    a._ensure_claimed(view)
                except AgentTurnServiceError as exc:
                    a.failure = exc
                    raise
                finally:
                    a._active_plan_jev_request = None
            from application_state.agent_conversation.jev_retrieval_contract import NativePlayIntentDecisionInputV1

            play_opening = type(self.parent) is NativePlayIntentDecisionInputV1
            if a.request.surface.surface_id == "play" and not play_opening and not any(
                isinstance(e, t.ProviderAttemptAuthorizedEventV1)
                for e in a.fence.turn.graph_context_execution.events
            ):
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
            from application_state.agent_conversation.native_retrieval import NativeRetrievalAuthorizedV1, NativePlanOpeningAuthorizedV1
            from application_state.agent_conversation.native_retrieval import NativePlanAuthorScopeAuthorizedV1
            from application_state.agent_conversation.native_plan_opening import NATIVE_PLAN_OPENING_INPUT_TYPES
            opening = type(self.parent) in NATIVE_PLAN_OPENING_INPUT_TYPES
            auth_type = NativePlanOpeningAuthorizedV1 if opening else t.PlanRequestedWorkAuthorizedV2 if isinstance(self.parent, PlanRequestedWorkInputV2) else t.PlanRequestedWorkAuthorizedV1 if semantic else NativeRetrievalAuthorizedV1 if native else t.PlanJevProviderAuthorizedV1
            build_context = dict(context_mode=view["contextMode"],context_phase=view["contextPhase"],
                max_question_input_tokens=view["maxQuestionInputTokens"],dispatch_identity_sha256=view["dispatchIdentitySha256"]) if native_build else None
            auth_kind = 'native_plan_opening_authorized_v1' if opening else 'plan_requested_work_authorized_v2' if isinstance(self.parent, PlanRequestedWorkInputV2) else 'plan_requested_work_authorized_v1' if semantic else 'native_retrieval_authorized_v1' if native else 'plan_jev_provider_authorized_v1'
            if author_scope:
                auth_type, auth_kind = NativePlanAuthorScopeAuthorizedV1, 'native_plan_author_scope_authorized_v1'
            scope_binding = getattr(self.parent, 'author_scope_binding', None)
            opening_fields = {'author_scope_event_id': scope_binding.observation_event_id} if scope_binding else {}
            if play_opening:
                opening_fields["play_intent_opening"] = True
            if author_scope and self.parent.intent_opening is not None:
                opening_fields["intent_opening"] = True
            if author_scope and self.parent.prior_scope_event_id is not None:
                opening_fields['prior_scope_event_id'] = self.parent.prior_scope_event_id
            if author_scope and self.parent.scope_review is not None:
                opening_fields['scope_review_event_ids'] = tuple(row.observation_event_id for row in self.parent.scope_review)
            auth = auth_type(kind=auth_kind, event_id=uuid4(),
                sequence=len(execution.events), provider_attempt_id=UUID(prepared.attempt_id),
                decision_request_id=self.parent.request_id, parent_request_sha256=self.parent.digest,
                envelope_sha256=prepared.body_sha256, serializer_version="typesafe-sdk-json-v1",
                provider=PROVIDER, model=MODEL, api_mode=view["apiMode"], tool_schema_sha256=sha256(b"[]").hexdigest(),
                input_accounting_kind="estimated_token_count" if native_build else "conservative_upper_bound",
                input_estimator=execution.policy.controller_continuation_accounting.policy if native_build else a.budget["estimator"],
                input_tokens=estimate, output_token_reserve=0 if native_build else a.budget["outputReserveTokens"],
                included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
                included_graph_event_ids=[], included_source_read_event_ids=[],
                **({"build_context":build_context} if native else {}), **opening_fields)
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
            from application_state.agent_conversation.native_retrieval import (
                NativePlanAuthorScopeAuthorizedV1, NativePlanOpeningAuthorizedV1,
            )
            entry_binding = ({'opening_authorization': self.authorization}
                if transition == 'sdk_entered' and type(self.authorization) in (
                    NativePlanOpeningAuthorizedV1, NativePlanAuthorScopeAuthorizedV1) else {})
            acknowledged = transition is not None and self.adapter.record_lifecycle({"transition": transition, "statusCode": event.http_status,
                "runtimeApiRequestId": f"generationengine:{self.prepared.attempt_id}"}, **entry_binding)
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
            from application_state.agent_conversation.native_retrieval import NativeRetrievalAuthorizedV1, NativeRetrievalSelectedV1, NativeRetrievalSelectedV2
            native = type(self.authorization) is NativeRetrievalAuthorizedV1
            capture_name = "unvalidated-native-retrieval-result" if native else "unvalidated-plan-jev-result"
            a.context_capture.observe({"kind": "context_snapshot", "stage": "after", "materials": [{
                "item_id": f"{capture_name}:{self.authorization.provider_attempt_id}",
                "state": "model_context", "role": "assistant", "text": raw}]})
            from application_state.agent_conversation.native_retrieval import NativePlanAuthorScopeAuthorizedV1
            if type(self.authorization) is NativePlanAuthorScopeAuthorizedV1:
                return self._acknowledge_author_scope(result, raw)
            semantic = isinstance(self.parent, PlanRequestedWorkInputV1)
            from application_state.agent_conversation.native_plan_opening import (
                NATIVE_PLAN_OPENING_INPUT_TYPES, NativePlanOpeningInputV2, NativePlanOpeningInputV3,
                composed_opening_fields, decode_opening_decision,
            )
            opening = type(self.parent) in NATIVE_PLAN_OPENING_INPUT_TYPES
            contextual = type(self.parent) is NativePlanOpeningInputV2
            composed = type(self.parent) is NativePlanOpeningInputV3
            if opening:
                selected, first_batch = decode_opening_decision(self.parent, result)
            else:
                selected = (decode_requested_work_decision if semantic else decode_selection)(self.parent, result)
            execution = a.fence.plan_execution_checkpoint()
            placement = isinstance(self.parent, PlanRequestedWorkInputV2)
            if composed:
                resolved = composed_opening_fields(self.parent, result) | {
                    'author_scope_binding': self.parent.author_scope_binding,
                    'author_operation': self.parent.plan_requested_operation,
                    'scope_document_title': self.parent.page_title,
                }
            elif placement:
                resolved = work_choice(self.parent, selected, **({'contextual_answers':
                    {k: v.selected for k, v in result.answers.items()}} if contextual else {}))
            else:
                resolved = {}
            selected_fields = (resolved | {
                'original_capture_sha256': self.parent.target_capture_sha256,
                'original_capture': self.parent.original_capture.model_dump(mode='json',by_alias=True) if self.parent.original_capture is not None else None,
                'placement_catalog': self.parent.placement_catalog.model_dump(mode='json',by_alias=True) if self.parent.placement_catalog is not None else None,
                'placement_catalog_sha256': self.parent.placement_catalog.sha256 if self.parent.placement_catalog is not None else None,
            }) if placement else {'requested_work': selected, 'target_capture_sha256': self.parent.target_capture_sha256} if semantic else {'operation': selected.operation, 'selected_handles': list(selected.selected_handles)}
            from application_state.agent_conversation.native_execution import (
                NativePlanRequestedWorkSelectedV3, NativePlanOpeningSelectedV1,
                NativePlanOpeningSelectedV2, NativePlanOpeningSelectedV3,
            )
            from application_state.agent_conversation.jev_retrieval_contract import NativePlanBatchDecisionInputV3
            from application_state.agent_conversation.jev_retrieval_contract import NativePlayIntentDecisionInputV1
            planned = type(self.parent) is NativePlanBatchDecisionInputV3
            if planned:
                selected_fields['post_read_plan'] = selected.post_read_plan
            if opening:
                selected_fields.update(operation=first_batch.operation if first_batch is not None else None,
                    selected_handles=list(first_batch.selected_handles) if first_batch is not None else [],
                    post_read_plan=first_batch.post_read_plan if first_batch is not None else None)
            if opening or not semantic:
                from application_state.agent_conversation.jev_retrieval_contract import retrieval_exclusions_for_replay
                selected_fields["exclusion_replay"] = retrieval_exclusions_for_replay(
                    self.parent, result, requested_work=selected_fields.get("requested_work") if opening else None,
                )
            current_work = isinstance(self.parent, PlanRequestedWorkInputV8)
            if composed:
                event_type, kind = NativePlanOpeningSelectedV3, 'native_plan_opening_selected_v3'
            elif contextual:
                event_type, kind = NativePlanOpeningSelectedV2, 'native_plan_opening_selected_v2'
            elif opening:
                event_type, kind = NativePlanOpeningSelectedV1, 'native_plan_opening_selected_v1'
            elif current_work:
                event_type, kind = NativePlanRequestedWorkSelectedV3, 'plan_requested_work_selected_v3'
            elif placement:
                event_type, kind = t.PlanRequestedWorkSelectedV2, 'plan_requested_work_selected_v2'
            elif semantic:
                event_type, kind = t.PlanRequestedWorkSelectedV1, 'plan_requested_work_selected_v1'
            elif type(self.parent) is NativePlayIntentDecisionInputV1:
                from application_state.agent_conversation.native_play_opening import decode_play_opening
                from application_state.agent_conversation.native_retrieval import NativePlayIntentSelectedV1

                selected_fields["requested_work"] = decode_play_opening(result)
                event_type, kind = NativePlayIntentSelectedV1, 'native_play_intent_selected_v1'
            elif planned:
                event_type, kind = NativeRetrievalSelectedV2, 'native_retrieval_selected_v2'
            elif native:
                event_type, kind = NativeRetrievalSelectedV1, 'native_retrieval_selected_v1'
            else:
                event_type, kind = t.PlanJevRetrievalSelectionV1, 'plan_jev_retrieval_selected_v1'
            event = event_type(kind=kind, event_id=uuid4(),
                sequence=execution.sequence, context_receipt_sha256=execution.context_receipt_sha256,
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
            fallback = result.answers.get("operation")
            if (not semantic and selected.operation == "finish_retrieval"
                    and fallback is not None and fallback.selected == "finish_with_gaps"):
                a.context_capture.observe({"kind": "failure", "phase": "graph_retrieval",
                                           "code": "controller_finished_with_gaps"})
            self.selection_event = event
            self.selection = selected_fields["requested_work"] if placement else selected
            return self.selection

    def _acknowledge_author_scope(self, result, raw):
        from .agent_turn_service import _require_fresh_execution_append
        from application_state.agent_conversation.native_plan_opening import (
            NativePlanAuthorScopeObservedV1, decode_author_scope_decision,
        )

        adapter = self.adapter
        execution = adapter.fence.plan_execution_checkpoint()
        observation = decode_author_scope_decision(self.parent, result)
        event = NativePlanAuthorScopeObservedV1(event_id=uuid4(), sequence=execution.sequence,
            decision_request_id=self.parent.request_id, controller_attempt_id=self.authorization.provider_attempt_id,
            context_receipt_sha256=execution.context_receipt_sha256,
            execution_policy_sha256=execution.execution_policy_sha256,
            parent_request_sha256=self.parent.digest, controller_envelope_sha256=self.prepared.body_sha256,
            controller_response_sha256=sha256(raw.encode()).hexdigest(), scope_observation=observation,
            actual_input_tokens=result.observation.input_tokens, actual_output_tokens=result.observation.output_tokens)
        adapter.turn = _require_fresh_execution_append(adapter.fence.append(
            'record_plan_author_scope_observation', 'observation', event,
            producer_proof={'parent_request_json': self.parent.model_dump_json(by_alias=True),
                'request_json': self.prepared.body.decode(), 'response_json': raw}))
        self.selection_event, self.selection = event, observation
        return observation

    async def run(self, *, transport=None, api_key=None, client=None):
        trace = getattr(self.adapter, "trace", None)
        detailed = trace is not None and host_work_observer.get() is not None
        with trace.measure_host_work('controller_round') if trace is not None else nullcontext():
            async def authorize(prepared): return self.authorize(prepared)
            async def record(event): return self.record(event)
            owns_client = client is None
            if owns_client:
                with trace.measure_host_work("plan_jev_client_setup") if detailed else nullcontext():
                    client = decision_client(authorize=authorize, record=record, transport=transport, api_key=api_key, select_context=self.select_context,
                        on_dispatch=getattr(trace, "mark_first_jev_dispatch", None))
            started = perf_counter()
            try:
                with trace.measure_host_work("plan_jev_request_preparation") if detailed else nullcontext():
                    from application_state.agent_conversation.native_plan_opening import (
                        NativePlanAuthorScopeParentV1, prepare_author_scope_decision,
                    )
                    if type(self.parent) is NativePlanAuthorScopeParentV1:
                        request = prepare_author_scope_decision(self.parent)
                    else:
                        request = (prepare_requested_work_decision(self.parent)
                            if isinstance(self.parent, PlanRequestedWorkInputV1)
                            else prepare_decision(self.parent, controller_accounting=self._native_accounting()))
                result = await client.decide(request)
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
