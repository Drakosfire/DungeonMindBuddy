"""Lazy Plan Rules binding: actual selected question, no invented tool call."""
from application_state.agent_conversation.plan_jev_rules_lookup import prepare_authorization
from application_state.agent_conversation.plan_jev_decision import _owner
from application_state.agent_conversation.rules_authority_plan_packet import build_plan_rules_frame
from application_state.agent_conversation.rules_authority_policy import rules_capability, RulesCapabilityV1
from .native_rules_runtime import NativeRulesRuntime
from . import rules_lookup_broker as broker


class PlanRulesRuntime:
    def __init__(self, adapter, capability):
        self.capability = RulesCapabilityV1.model_validate(capability)
        if (adapter.request.surface.surface_id != "plan" or self.capability != rules_capability(graph=True)
                or adapter.rules_runtime is not None):
            raise ValueError("Plan Rules requires the exact current Graph capability")
        self.adapter, self.native = adapter, None
        self.selected = False
        self.call_ids = ()
        self.authoring = None

    def _initialize(self):
        # The first Jev call establishes the actual Plan claim. No Rules ledger,
        # conversation lookup, corpus read or provider call is needed to offer it.
        if self.native is None:
            if self.adapter.fence is None:
                raise ValueError("Plan Rules must wait for its actual Plan claim")
            _owner(self.adapter.fence.turn)
            self.native = NativeRulesRuntime(self.adapter, self.capability)
            self.adapter.rules_runtime = self
        return self.native

    def lookup_selected(self, parent_request_json):
        if self.selected:
            raise ValueError("Plan Rules cannot repeat the same selected question")
        native = self._initialize()
        a = self.adapter
        with a.fence.renewer._lock:
            turn = native._bind()
            event = prepare_authorization(native.record.execution, turn, parent_request_json)
            native.record = a.service.authorize_plan_jev_rules_lookup(native.record.execution.scope,
                expected_turn_revision=turn.revision, expected_ledger_revision=native.record.revision,
                event=event, parent_request_json=parent_request_json)
            self.selected = True  # a failed/unknown read is not automatically repeated
            delivery = a.service.execute_rules_lookup(native.record.execution.scope,
                expected_turn_revision=turn.revision, call_id=event.call_id,
                local_reader=lambda current: broker.prepare_plan_lookup(current, event.call_id, turn.user_text))
            native.record = delivery.record
            self.call_ids = (event.call_id,)
        return delivery

    def frame(self):
        native = self._initialize()
        with self.adapter.fence.renewer._lock:
            native._bind()
            return build_plan_rules_frame(native.record.execution, self.call_ids)

    def outcome(self, transition):
        if self.native is not None: self.native.outcome(transition)

    def authorize(self, view):
        from uuid import uuid4
        from application_state.agent_conversation.rules_authority_plan_packet import verify_plan_rules_packet_input
        from application_state.agent_conversation.rules_authority_events import (
            RulesPlanPacketProviderAuthorizedV1, RulesPlanPacketProviderIncludedV1)
        a = self.adapter
        native = self._initialize()
        with a.fence.renewer._lock:
            turn = native._bind()
            from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
            if type(turn.graph_context_receipt) is SurfaceNativeContextReceiptV1:
                # The owning APP append already admitted writer + Rules input in
                # one transaction. Read that same ledger, without a second grant.
                native.record=a.service.begin_rules_execution(native.record.execution.scope,expected_turn_revision=turn.revision)
                from application_state.agent_conversation.rules_authority_events import RulesProviderIncludedV1
                if not any(type(e) is RulesProviderIncludedV1 and e.provider_attempt_id==a.last_provider_attempt_id
                        and e.request_envelope_sha256==view['payloadSha256'] for e in native.record.execution.events):
                    raise ValueError('Shared writer has no atomically admitted Rules input')
                native.last_provider={**view,'providerAttemptId':str(a.last_provider_attempt_id)}
                native.last_prepared_json,native.last_reply=view['payloadJson'],None
                return True
            exposure = verify_plan_rules_packet_input(native.record.execution, turn, view["payloadJson"],
                expected_envelope_sha256=view["payloadSha256"])
            execution = native.record.execution
            common = dict(execution_id=execution.scope.execution_id, provider_attempt_id=a.last_provider_attempt_id,
                request_envelope_sha256=view["payloadSha256"], plan_context_receipt_sha256=exposure.plan_context_receipt_sha256,
                matched_outputs=exposure.matched_outputs)
            authorized = RulesPlanPacketProviderAuthorizedV1(kind="plan_packet_provider_authorized", event_id=uuid4(),
                sequence=len(execution.events), declared_support_refs=exposure.support_refs, **common)
            native.record = a.service.append_rules_provider_event(execution.scope, expected_turn_revision=turn.revision,
                expected_ledger_revision=native.record.revision, event=authorized, prepared_request_json=view["payloadJson"])
            included = RulesPlanPacketProviderIncludedV1(kind="plan_packet_provider_included", event_id=uuid4(),
                sequence=len(native.record.execution.events), support_refs=exposure.support_refs, **common)
            native.record = a.service.append_rules_provider_event(execution.scope, expected_turn_revision=turn.revision,
                expected_ledger_revision=native.record.revision, event=included, prepared_request_json=view["payloadJson"])
            native.last_provider = {**view, "providerAttemptId": str(a.last_provider_attempt_id)}
            native.last_prepared_json, native.last_reply = view["payloadJson"], None
        return True

    def capture_reply(self, reply):
        return self._initialize().capture_reply(reply)

    def complete(self, turn, reply, *, work_proof=None):
        if self.authoring is None:
            return self._initialize().complete(turn,reply,work_proof=work_proof)
        from application_state.agent_conversation.plan_authoring import prepare_authoring_proposal
        action,capture=self.authoring
        def accept_base(result,proof,rules_revision):
            proposal=prepare_authoring_proposal(action,capture,turn,result,proof)
            return self.adapter.service.complete_plan_authoring_turn(result,proposal=proposal,
                output_proof=proof,expected_rules_revision=rules_revision,**({'work_proof':work_proof} if work_proof is not None else {}))
        def accept_mixed(result):
            proposal=prepare_authoring_proposal(action,capture,turn,result,result.output_proof)
            return self.adapter.service.complete_plan_authoring_mixed_turn(result,proposal=proposal,**({'work_proof':work_proof} if work_proof is not None else {}))
        return self._initialize().complete(turn,reply,accept_base=accept_base,accept_mixed=accept_mixed,work_proof=work_proof)
