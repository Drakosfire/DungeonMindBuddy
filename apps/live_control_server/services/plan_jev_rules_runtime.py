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
