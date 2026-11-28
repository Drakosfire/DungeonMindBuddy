"""Run the saved Build intent's source ballot without acquiring sources."""
import json
from uuid import UUID, uuid4

from application_state.agent_conversation import types as ledger
from application_state.agent_conversation.build_intentional_response import (
    UnresolvedDiscussionSource, build_source_followup_wire, verify_build_source_followup,
)
from application_state.agent_conversation.native_execution import BuildSourceScopeAuthorizedV1

from .build_jev_accounting import DecisionCapacityError
from .build_jev_dispatch import prepared_driver_view
from .build_jev_driver import DriverDecisionProjection, canonical, digest, sdk_answers
from .build_jev_transitions import DecisionIntent, DecisionQuestion
from .build_pending_app_pages import _commit


class PendingBuildSourceScopeDriver:
    def __init__(self, adapter, opening_request, opening_response):
        self.adapter = adapter
        self.before = adapter._broker_execution()
        self.opening_request = opening_request
        self.opening_response = opening_response
        self.opening_wire = json.loads(opening_request)
        self.intent = self.before.events[-1]
        if type(self.intent) is not ledger.BuildOpeningIntentSelectedV1:
            raise ValueError("Build source scope needs its saved opening intent")
        self.menu = self.before.policy.action.requested_work_menu_sha256
        self.wire = build_source_followup_wire(
            self.opening_wire["state"], self.intent.requested_work, menu_digest=self.menu,
            write_capability=self.before.policy.action.write_capability,
        )
        self.step = DecisionIntent(
            request_id="build-source-scope:" + digest(self.wire), phase="source_scope",
            state=self.wire["state"],
            questions=tuple(DecisionQuestion(name=name, kind="choice",
                question=ballot["instructions"], options=tuple(ballot["criteria"]))
                for name, ballot in self.wire["questions"].items()),
        )
        self.plan = self.prepared = self.result = self.response = None

    def stage(self):
        if self.plan is not None or self.adapter._broker_execution() != self.before:
            raise ValueError("Build source scope changed before staging")
        self.plan = DriverDecisionProjection(
            canonical(self.wire["state"]), canonical(self.wire["questions"]),
            self.step.request_id, len(self.before.events), str(self.adapter.last_provider_attempt_id),
            (), (), (), host_phase="source_scope",
        )
        return self.plan

    def authorize(self, prepared):
        adapter = self.adapter
        if (self.plan is None or self.prepared is not None or adapter.failure is not None
                or adapter._broker_execution() != self.before):
            return False
        try:
            view = prepared_driver_view(prepared, self.plan, accounting=adapter._build_jev_accounting)
        except DecisionCapacityError as exc:
            self.admission_failure = exc
            return False
        auth = BuildSourceScopeAuthorizedV1(
            event_id=uuid4(), sequence=len(self.before.events),
            provider_attempt_id=UUID(prepared.attempt_id), envelope_sha256=prepared.body_sha256,
            serializer_version=view["serializerVersion"], provider=view["provider"], model=view["model"],
            api_mode=view["apiMode"], tool_schema_sha256=ledger.canonical_sha256([]),
            input_accounting_kind="estimated_token_count", input_estimator=adapter._build_jev_accounting.descriptor["policy"],
            input_tokens=adapter._build_jev_accounting.estimate(json.loads(prepared.body)), output_token_reserve=0,
            included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
            included_graph_event_ids=[], included_source_read_event_ids=[], context_mode=view["contextMode"],
            max_question_input_tokens=view["maxQuestionInputTokens"], dispatch_identity_sha256=view["dispatchIdentitySha256"],
            opening_intent_event_id=self.intent.event_id,
        )
        access = getattr(adapter, "build_intent_access", None) or adapter.pending_build_access
        if not callable(access):
            raise ValueError("Build source scope requires its current World access owner")
        _commit(adapter, "authorize_pending_build_source_scope", authorization=auth,
            request_json=prepared.body.decode(), initial_request_json=self.opening_request,
            authorize_current_access=access)
        adapter.last_provider_attempt_id = auth.provider_attempt_id
        adapter._prepared_build_decision = prepared
        adapter._capture_prepared_prompt(view, auth)
        self.prepared = prepared
        return True

    def accept_decision(self, model, answers, *, actual_response):
        if (self.prepared is None or str(self.adapter.last_provider_attempt_id) != self.prepared.attempt_id
                or model != self.wire["model"] or sdk_answers(actual_response) != answers):
            raise ValueError("Build source scope requires its actual producing response")
        try:
            scope = verify_build_source_followup(
                self.opening_wire, self.opening_response, menu_digest=self.menu,
                wire=json.loads(self.prepared.body), response=actual_response.model_dump(mode="json"),
                write_capability=self.before.policy.action.write_capability,
            )
        except UnresolvedDiscussionSource as exc:
            from .agent_turn_service import AgentTurnServiceError

            raise AgentTurnServiceError(
                str(exc), code="build_discussion_source_uncertain", status_code=409,
            ) from exc
        self.result = scope
        self.response = canonical(actual_response.model_dump(mode="json"))
