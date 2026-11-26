"""Pending Build's App-only discovery, guarded decision and exact saved reads."""
from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

from application_state.agent_conversation import types as ledger
from application_state.agent_conversation.build_related_pages import RelatedPagesSelection, RelatedPageRead, should_read_page
from application_state.agent_conversation.build_source_free import (
    BuildAppPageCatalogObservedV1, effective_pending_app_catalog,
    pending_app_page_selection_input, pending_source_work, pending_work_requests_evidence,
)
from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1
from application_state.agent_conversation.native_execution import BuildAppPageSelectionAuthorizedV1
from .build_jev_driver import DriverDecisionProjection, canonical, digest, sdk_answers
from .build_jev_transitions import DecisionIntent, DecisionQuestion
from .build_jev_dispatch import prepared_driver_view


def _commit(adapter, method, **fields):
    from .agent_turn_service import _require_fresh_execution_append
    adapter.turn = _require_fresh_execution_append(adapter.fence.commit(method, **fields))


def _discover_pending_pages(adapter):
    """Offer the current saved page only at the request's frozen revision."""
    from .build_related_pages import discover
    from application_state.agent_conversation.build_related_pages import PagePointer
    basis = adapter._broker_receipt().work_context.source_basis
    pages = []
    for row in discover(adapter.request, include_current=True):
        pointer = PagePointer.model_validate(row)
        if (str(pointer.document_id) == str(basis.document_id)
                and (pointer.registry_revision != basis.registry_revision
                     or pointer.visibility != basis.visibility)):
            continue  # A newer or reclassified page cannot replace the captured basis.
        pages.append(pointer.model_dump(mode='json'))
    return pages


def _initial_request(adapter):
    """Read the original captured request; never reconstruct today's history."""
    from .agent_prompt_evidence import read_prompt
    receipt = adapter._broker_receipt()
    execution = adapter._broker_execution()
    first = next(event for event in execution.events if isinstance(event, ledger.ProviderAttemptAuthorizedEventV1))
    prompts = [event for event in adapter.context_capture.trace.observations
               if getattr(event, 'kind', None) == 'prompt_reference'
               and event.provider_attempt_id == first.provider_attempt_id]
    if len(prompts) != 1 or prompts[0].payload_sha256 != receipt.assembled_input.assembled_input_sha256:
        raise ValueError('Pending App navigation requires its unique captured initial request')
    return read_prompt(prompts[0])


async def acquire_pending_app_pages(adapter, harness):
    """Run only after evidence-seeking work, before native source preparation."""
    if type(adapter._broker_receipt()) is not BuildPendingContextReceiptV1:
        return
    execution = adapter._broker_execution()
    if any(type(event) is ledger.BuildPriorBodyEvidenceAdmittedV3 for event in execution.events):
        return
    work = [event for event in execution.events if type(event) is ledger.BuildRequestedWorkResolutionV1]
    if len(work) != 1:
        raise ValueError('Pending App navigation requires one admitted work decision')
    work, = work
    if not pending_work_requests_evidence(work, execution.policy):
        return
    if not callable(adapter.pending_build_access) or adapter.fence is None:
        raise ValueError('Pending App navigation requires its live claim and App access owner')
    receipt = adapter._broker_receipt()
    catalog = effective_pending_app_catalog(receipt, execution)
    if catalog is None:
        pending_source_work(execution)
        _commit(adapter, 'observe_pending_build_app_catalog', event_id=uuid4(),
            discover_pages=lambda turn: _discover_pending_pages(adapter),
            authorize_current_access=adapter.pending_build_access)
        catalog = effective_pending_app_catalog(receipt, adapter._broker_execution())
    if not catalog:
        return
    selections = [event for event in adapter._broker_execution().events if type(event) is RelatedPagesSelection]
    if not selections:
        driver = PendingAppPageDriver(adapter, _initial_request(adapter))
        await harness._decide(adapter, driver)
        selections = [event for event in adapter._broker_execution().events if type(event) is RelatedPagesSelection]
    if len(selections) != 1:
        raise ValueError('Pending App navigation has no unique admitted selection')
    from .build_related_pages import materialize
    for document_id in selections[0].document_ids:
        reads = [event for event in adapter._broker_execution().events if type(event) is RelatedPageRead
                 and event.page.document_id == document_id]
        if reads:
            if len(reads) != 1 or reads[0].selection_event_id != selections[0].event_id:
                raise ValueError('Pending App page read differs from its unique selection')
            continue
        _commit(adapter, 'read_pending_app_page', document_id=document_id,
            event_id=uuid4(), read_id=uuid4(), materialize_page=materialize,
            authorize_current_access=adapter.pending_build_access)


class PendingAppPageDriver:
    """An App navigation controller, with no Graph or source read authority."""
    def __init__(self, adapter, initial_request_json):
        self.adapter, self.initial = adapter, initial_request_json
        self.receipt = adapter._broker_receipt()
        self.before = adapter._broker_execution()
        self.wire = pending_app_page_selection_input(self.receipt, self.before, self.initial)
        self.step = DecisionIntent(request_id='pending-app-pages:' + digest(self.wire), phase='navigate',
            state=self.wire['state'], questions=tuple(DecisionQuestion(name=name, kind='choice',
                question=value['instructions'], options=tuple(value['criteria']))
                for name, value in self.wire['questions'].items()))
        self.plan, self.prepared = None, None

    def stage(self):
        if self.plan is not None or self.adapter._broker_execution() != self.before:
            raise ValueError('Pending App navigation changed before staging')
        self.plan = DriverDecisionProjection(canonical(self.wire['state']), canonical(self.wire['questions']),
            self.step.request_id, len(self.before.events), str(self.adapter.last_provider_attempt_id),
            (), (), (), host_phase='navigate')
        return self.plan

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
        catalogs = [event for event in self.before.events if type(event) is BuildAppPageCatalogObservedV1]
        if len(catalogs) != 1:
            return False
        authorization = BuildAppPageSelectionAuthorizedV1(event_id=uuid4(), sequence=len(self.before.events),
            provider_attempt_id=UUID(prepared.attempt_id), envelope_sha256=prepared.body_sha256,
            serializer_version=view['serializerVersion'], provider=view['provider'], model=view['model'],
            api_mode=view['apiMode'], tool_schema_sha256=ledger.canonical_sha256([]),
            input_accounting_kind='estimated_token_count',
            input_estimator=adapter._build_jev_accounting.descriptor['policy'],
            input_tokens=adapter._build_jev_accounting.estimate(json.loads(prepared.body)), output_token_reserve=0,
            included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
            included_graph_event_ids=[], included_source_read_event_ids=[], context_mode=view['contextMode'],
            max_question_input_tokens=view['maxQuestionInputTokens'], dispatch_identity_sha256=view['dispatchIdentitySha256'],
            catalog_event_id=catalogs[0].event_id, admitted_from_revision=adapter.fence.turn.revision)
        _commit(adapter, 'authorize_pending_app_page_selection', authorization=authorization,
            prepared_request_json=prepared.body.decode(), initial_request_json=self.initial,
            authorize_current_access=adapter.pending_build_access)
        adapter.last_provider_attempt_id = authorization.provider_attempt_id
        adapter._prepared_build_decision = prepared
        adapter._capture_prepared_prompt(view, authorization)
        self.prepared = prepared
        return True

    def accept_decision(self, model, answers, *, actual_response):
        adapter = self.adapter
        if (self.prepared is None or str(adapter.last_provider_attempt_id) != self.prepared.attempt_id
                or model != self.wire['model'] or sdk_answers(actual_response) != answers):
            raise ValueError('Pending App navigation requires its actual producing response')
        response = canonical(actual_response.model_dump(mode='json'))
        catalog, = [event for event in adapter._broker_execution().events
                    if type(event) is BuildAppPageCatalogObservedV1]
        chosen = sorted([page.document_id for index, page in enumerate(catalog.pages)
            if should_read_page(page, self.wire['questions'][f'page{index + 1}'],
                actual_response.answers[f'page{index + 1}'], semantic=True)], key=str)
        event = RelatedPagesSelection(event_id=uuid4(), sequence=len(adapter._broker_execution().events),
            controller_attempt_id=UUID(self.prepared.attempt_id),
            controller_envelope_sha256=self.prepared.body_sha256,
            controller_response_sha256=hashlib.sha256(response.encode()).hexdigest(), document_ids=chosen)
        _commit(adapter, 'record_pending_app_page_selection', selection=event,
            producer_proof={'request_json': self.prepared.body.decode(), 'response_json': response,
                'initial_request_json': self.initial}, authorize_current_access=adapter.pending_build_access)
