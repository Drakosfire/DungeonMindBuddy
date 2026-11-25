"""Pending Build's actual native controller, using its own admitted source owner.

This driver grants no Core access. Selected IO stays with the existing guarded
native read owners; source preparation/discovery is never repeated here.
"""
from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

from application_state.agent_conversation import types as ledger
from application_state.agent_conversation.native_retrieval import (
    NativeBuildDecisionContextV1, NativeRetrievalAuthorizedV1, NativeRetrievalSelectedV1,
    owner, scope_digest, source_pins, controller_accounting,
)
from application_state.agent_conversation.jev_retrieval_contract import (
    NativeBuildRetrievalDecisionInputV3, prepare_decision, decode_selection,
)
from .build_pending_app_pages import PendingAppPageDriver, _commit
from .build_jev_driver import canonical, sdk_answers
from .build_jev_transitions import DecisionIntent, DecisionQuestion
from .build_jev_dispatch import prepared_driver_view


class PendingNativeRetrievalDriver(PendingAppPageDriver):
    """One exact controller attempt; no retry, hidden search or legacy identity."""
    def __init__(self, adapter, candidates, *, dialogue=(), examined_candidates=(),
                 allowed_operations=('select_candidates', 'discover_more', 'finish_retrieval')):
        self.adapter = adapter
        self.receipt, self.before = owner(adapter.fence.turn)
        if getattr(adapter, 'prepare_deferred_build_query', None) is not None:
            raise ValueError('Pending retrieval cannot race deferred source preparation')
        self.parent = NativeBuildRetrievalDecisionInputV3(
            request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256=scope_digest(adapter.fence.turn),
            question=self.before.policy.action.intent.message, dialogue=tuple(dialogue),
            candidates=tuple(candidates), examined_candidates=tuple(examined_candidates),
            allowed_operations=tuple(allowed_operations), **source_pins(self.receipt, self.before))
        request = prepare_decision(self.parent, controller_accounting=controller_accounting(self.before))
        self.wire = {'model': request.model, 'state': request.state, 'questions': {
            q.name: {'type': 'choice', 'instructions': q.question, 'criteria': dict.fromkeys(q.options)}
            for q in request.questions}}
        self.step = DecisionIntent(request_id=str(self.parent.request_id), phase='navigate',
            state=request.state, questions=tuple(DecisionQuestion(name=q.name, kind='choice',
                question=q.question, options=q.options) for q in request.questions))
        self.plan = self.prepared = self.selection = self.proof = None

    def authorize(self, prepared):
        adapter = self.adapter
        if (self.plan is None or self.prepared is not None or adapter.failure is not None
                or adapter._broker_execution() != self.before):
            return False
        from .build_jev_accounting import DecisionCapacityError
        try:
            view = prepared_driver_view(prepared, self.plan, accounting=adapter._build_jev_accounting)
        except DecisionCapacityError as exc:
            self.admission_failure = exc
            return False
        self.parent = self.parent.model_copy(update={'parent_attempt_id': UUID(prepared.attempt_id)})
        auth = NativeRetrievalAuthorizedV1(event_id=uuid4(), sequence=len(self.before.events),
            provider_attempt_id=UUID(prepared.attempt_id), decision_request_id=self.parent.request_id,
            parent_request_sha256=self.parent.digest, envelope_sha256=prepared.body_sha256,
            serializer_version=view['serializerVersion'], provider=view['provider'], model=view['model'],
            api_mode=view['apiMode'], tool_schema_sha256=ledger.canonical_sha256([]),
            input_accounting_kind='estimated_token_count', input_estimator=adapter._build_jev_accounting.descriptor['policy'],
            input_tokens=adapter._build_jev_accounting.estimate(json.loads(prepared.body)), output_token_reserve=0,
            included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
            included_graph_event_ids=[], included_source_read_event_ids=[],
            build_context=NativeBuildDecisionContextV1(context_mode=view['contextMode'], context_phase='navigate',
                max_question_input_tokens=view['maxQuestionInputTokens'], dispatch_identity_sha256=view['dispatchIdentitySha256']))
        self.proof = {'parent_request_json': self.parent.model_dump_json(by_alias=True),
            'request_json': prepared.body.decode()}
        _commit(adapter, 'authorize_pending_native_retrieval', authorization=auth,
            prepared_input_proof=self.proof, authorize_current_access=adapter.pending_build_access)
        adapter.last_provider_attempt_id = auth.provider_attempt_id
        adapter._prepared_build_decision = prepared
        adapter._capture_prepared_prompt(view, auth)
        self.prepared = prepared
        return True

    def accept_decision(self, model, answers, *, actual_response):
        adapter = self.adapter
        if (self.prepared is None or str(adapter.last_provider_attempt_id) != self.prepared.attempt_id
                or model != self.wire['model'] or sdk_answers(actual_response) != answers):
            raise ValueError('Pending native retrieval requires its actual producing SDK response')
        selected = decode_selection(self.parent, actual_response)
        response = canonical(actual_response.model_dump(mode='json'))
        adapter.context_capture.observe({'kind': 'context_snapshot', 'stage': 'after', 'materials': [{
            'item_id': f'unvalidated-native-retrieval-result:{self.prepared.attempt_id}',
            'state': 'model_context', 'role': 'assistant', 'text': response}]})
        event = NativeRetrievalSelectedV1(event_id=uuid4(), sequence=len(adapter._broker_execution().events),
            context_receipt_sha256=self.receipt.context_receipt_sha256,
            execution_policy_sha256=self.before.execution_policy_sha256,
            decision_request_id=self.parent.request_id, controller_attempt_id=UUID(self.prepared.attempt_id),
            controller_envelope_sha256=self.prepared.body_sha256,
            controller_response_sha256=hashlib.sha256(response.encode()).hexdigest(),
            parent_request_sha256=self.parent.digest, operation=selected.operation,
            selected_handles=list(selected.selected_handles), actual_input_tokens=actual_response.observation.input_tokens,
            actual_output_tokens=actual_response.observation.output_tokens)
        proof = self.proof | {'response_json': response}
        _commit(adapter, 'record_pending_native_selection', selection=event,
            producer_proof=proof, authorize_current_access=adapter.pending_build_access)
        self.selection, self.proof = event, proof
