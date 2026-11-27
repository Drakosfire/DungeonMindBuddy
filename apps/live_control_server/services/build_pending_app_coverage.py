"""Actual App evidence assessment, without preparing any native source."""
from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

from application_state.agent_conversation import types as ledger
from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1
from application_state.agent_conversation.build_pending_app_coverage import (
    BuildAppCoverageAuthorizedV1, BuildAppCoverageDecidedV1,
    pending_app_coverage_input, pending_app_coverage_reads,
)
from application_state.agent_conversation.build_intentional_response import _selected_choice
from .build_pending_app_pages import PendingAppPageDriver, _commit, _initial_request
from .build_jev_driver import canonical, digest, sdk_answers
from .build_jev_transitions import DecisionIntent, DecisionQuestion
from .build_jev_dispatch import prepared_driver_view


def _stored_proof(adapter, authorization, initial):
    from .agent_prompt_evidence import read_prompt
    receipt = adapter._broker_receipt()
    observations = adapter.context_capture.trace.observations
    prompts = [row for row in observations if getattr(row, 'kind', None) == 'prompt_reference'
        and row.provider_attempt_id == authorization.provider_attempt_id]
    item_id = f'unvalidated-controller-decision:{authorization.provider_attempt_id}:{receipt.context_receipt_sha256}'
    materials = [material for row in observations if getattr(row, 'kind', None) == 'context_snapshot'
        for material in row.materials if material.item_id == item_id]
    if len(prompts) != 1 or len(materials) != 1:
        raise ValueError('Stored App coverage lacks its unique protected request and response')
    return {'request_json': read_prompt(prompts[0]), 'response_json': materials[0].text,
        'initial_request_json': initial}


async def assess_pending_app_coverage(adapter, harness):
    if type(adapter._broker_receipt()) is not BuildPendingContextReceiptV1:
        return None
    execution = adapter._broker_execution()
    if not any(type(row) is ledger.RelatedPageRead for row in execution.events):
        return None
    if not callable(adapter.pending_build_access) or adapter.fence is None:
        raise ValueError('App coverage requires its actual current claim and access owner')
    if getattr(adapter, 'prepare_deferred_build_query', None) is not None:
        raise ValueError('App coverage cannot race a deferred native-source preparation')
    auths = [row for row in execution.events if type(row) is BuildAppCoverageAuthorizedV1]
    decisions = [row for row in execution.events if type(row) is BuildAppCoverageDecidedV1]
    initial = _initial_request(adapter)
    if decisions:
        if len(auths) != 1 or len(decisions) != 1:
            raise ValueError('Stored App coverage is not unique')
        proof = _stored_proof(adapter, auths[0], initial)
        turn, fresh = adapter.fence.commit('record_pending_app_coverage', decision=decisions[0],
            producer_proof=proof, authorize_current_access=adapter.pending_build_access)
        if fresh is not False:
            raise ValueError('Stored App coverage reentry cannot admit a new verdict')
        adapter.turn = turn
        return decisions[0].verdict
    if auths:
        raise ValueError('App coverage dispatch is unresolved; it cannot be resent')
    driver = PendingAppCoverageDriver(adapter, initial)
    await harness._decide(adapter, driver)
    decisions = [row for row in adapter._broker_execution().events if type(row) is BuildAppCoverageDecidedV1]
    if len(decisions) != 1:
        raise ValueError('App coverage has no unique admitted producing verdict')
    return decisions[0].verdict


class PendingAppCoverageDriver(PendingAppPageDriver):
    def __init__(self, adapter, initial_request_json):
        self.adapter, self.initial = adapter, initial_request_json
        self.receipt, self.before = adapter._broker_receipt(), adapter._broker_execution()
        self.wire = pending_app_coverage_input(self.receipt, self.before, self.initial)
        self.step = DecisionIntent(request_id='pending-app-coverage:' + digest(self.wire), phase='navigate',
            state=self.wire['state'], questions=tuple(DecisionQuestion(name=name, kind='choice',
                question=value['instructions'], options=tuple(value['criteria']))
                for name, value in self.wire['questions'].items()))
        self.plan, self.prepared = None, None

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
        work, = [row for row in self.before.events if type(row) is ledger.BuildRequestedWorkResolutionV1]
        reads = pending_app_coverage_reads(self.receipt, self.before)
        auth = BuildAppCoverageAuthorizedV1(event_id=uuid4(), sequence=len(self.before.events),
            provider_attempt_id=UUID(prepared.attempt_id), envelope_sha256=prepared.body_sha256,
            serializer_version=view['serializerVersion'], provider=view['provider'], model=view['model'],
            api_mode=view['apiMode'], tool_schema_sha256=ledger.canonical_sha256([]),
            input_accounting_kind='estimated_token_count', input_estimator=adapter._build_jev_accounting.descriptor['policy'],
            input_tokens=adapter._build_jev_accounting.estimate(json.loads(prepared.body)), output_token_reserve=0,
            included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
            included_graph_event_ids=[], included_source_read_event_ids=[], context_mode=view['contextMode'],
            max_question_input_tokens=view['maxQuestionInputTokens'], dispatch_identity_sha256=view['dispatchIdentitySha256'],
            work_event_id=work.event_id, read_event_ids=tuple(row.event_id for row in reads),
            admitted_from_revision=adapter.fence.turn.revision)
        _commit(adapter, 'authorize_pending_app_coverage', authorization=auth,
            prepared_request_json=prepared.body.decode(), initial_request_json=self.initial,
            authorize_current_access=adapter.pending_build_access)
        adapter.last_provider_attempt_id = auth.provider_attempt_id
        adapter._prepared_build_decision = prepared
        adapter._capture_prepared_prompt(view, auth)
        self.prepared = prepared
        return True

    def accept_decision(self, model, answers, *, actual_response):
        adapter = self.adapter
        if (self.prepared is None or str(adapter.last_provider_attempt_id) != self.prepared.attempt_id
                or model != self.wire['model'] or sdk_answers(actual_response) != answers):
            raise ValueError('App coverage requires its actual producing SDK response')
        response = canonical(actual_response.model_dump(mode='json'))
        vote = actual_response.answers['source_requirement'].model_dump(mode='json')
        verdict = _selected_choice(vote, self.wire['questions']['source_requirement']['criteria'])
        decision = BuildAppCoverageDecidedV1(event_id=uuid4(), sequence=len(adapter._broker_execution().events),
            controller_attempt_id=UUID(self.prepared.attempt_id), controller_envelope_sha256=self.prepared.body_sha256,
            controller_response_sha256=hashlib.sha256(response.encode()).hexdigest(), verdict=verdict)
        _commit(adapter, 'record_pending_app_coverage', decision=decision, producer_proof={
            'request_json': self.prepared.body.decode(), 'response_json': response, 'initial_request_json': self.initial},
            authorize_current_access=adapter.pending_build_access)
