"""Focused current-page acquisition and safe no-fallback checks."""
import asyncio
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from apps.live_control_server.services import build_pending_app_pages as direct
from application_state.errors import ApplicationStateNotFoundError
from tests.test_build_source_free_protocol import pending_catalog_case


def test_pending_opening_offers_the_reader_registered_scope():
    from application_state.agent_conversation.build_intentional_response import (
        FUTURE_CURRENT_PAGE_SOURCE_NEED_GUIDANCE, FUTURE_CURRENT_PAGE_SOURCE_NEED_OPTIONS)
    from tests.test_build_source_free_protocol import pending_adapter_driver_case
    adapter, _ = pending_adapter_driver_case()
    question = next(q for q in adapter.create_build_jev_driver().step.questions if q.name == 'source_need')
    assert question.options == FUTURE_CURRENT_PAGE_SOURCE_NEED_OPTIONS
    assert question.question == FUTURE_CURRENT_PAGE_SOURCE_NEED_GUIDANCE


def test_unavailable_action_writer_distinguishes_capability_from_factual_gaps(monkeypatch):
    import json
    from application_state.agent_conversation.native_writer import verify_input_records
    from apps.live_control_server.services import build_jev_dispatch
    from tests.test_build_source_free_protocol import pending_writer_dispatch_case
    monkeypatch.setattr(build_jev_dispatch, 'MODEL', 'jev-1.14.0')
    with pending_writer_dispatch_case(monkeypatch, source_free_work='other_creation',
                                      source_scope='anchored', native_json=True) as (state, adapter, rules, writer, prepared):
        instructions = json.loads(prepared.body)['instructions']
        assert 'An unavailable action is a capability limitation, not missing factual evidence.' in instructions
        assert 'only when the supplied evidence actually lacks a factual detail' in instructions
        assert writer.authorize(prepared)
        turn = state.turn
        verify_input_records(turn.graph_context_receipt, turn.graph_context_execution, writer.authorization,
            prepared.body.decode(), provenance=turn.provenance, idempotency_key=turn.idempotency_key,
            work_proof=writer.proof, world_id=turn.world_id, conversation_id=turn.conversation_id,
            turn_id=turn.turn_id, attempt=turn.attempt)


def test_genuine_missing_factual_detail_remains_a_supported_limitation():
    from application_state.agent_conversation.source_writer_output import project_surface_limitations
    options = dict(user_question='What does the source say?', derive_missing=False,
        host_partial=False, empty_answer=False, strict_gap_array=True, generic_codes_only=True)
    assert not project_surface_limitations([], [], **options)
    limitation, = project_surface_limitations(['missing_requested_details'], [], **options)
    assert limitation.code == 'missing_requested_details'


def _metadata_adapter():
    receipt, _, _, _ = pending_catalog_case()
    basis = receipt.work_context.source_basis
    page = SimpleNamespace(work_object_id=UUID(basis.document_id), world_id=basis.world_id,
        object_revision=basis.registry_revision, status='active', current_revision_id=uuid4(), title='Saved page')
    metadata = SimpleNamespace(visibility_state=basis.visibility, document_class='lore', authority_state='draft')
    return SimpleNamespace(_broker_receipt=lambda: receipt), SimpleNamespace(page=page, metadata=metadata)


def test_direct_lookup_uses_one_exact_page_metadata_request_no_world_inventory(monkeypatch):
    from application_state.content import pages
    from apps.live_control_server.services import build_related_pages
    adapter, state = _metadata_adapter()
    calls = []
    monkeypatch.setattr(pages, 'get_page', lambda document_id, *, world_id: (
        calls.append((document_id, world_id)) or state))
    monkeypatch.setattr(build_related_pages, 'discover', lambda *a, **kw: pytest.fail('World catalog enumerated'))
    result = direct._lookup_current_saved_page(adapter)
    basis = adapter._broker_receipt().work_context.source_basis
    assert calls == [(basis.document_id, basis.world_id)]
    assert len(result) == 1 and result[0]['document_id'] == basis.document_id
    assert result[0]['registry_revision'] == basis.registry_revision


@pytest.mark.parametrize('field,value', [
    ('object_revision', 999), ('world_id', 'another-world'), ('status', 'discarded'),
    ('current_revision_id', None), ('visibility_state', 'player_safe'),
    ('document_class', None), ('authority_state', 'unknown'),
])
def test_direct_lookup_rejects_stale_or_ineligible_metadata(monkeypatch, field, value):
    from application_state.content import pages
    adapter, state = _metadata_adapter()
    target = state.metadata if hasattr(state.metadata, field) else state.page
    setattr(target, field, value)
    monkeypatch.setattr(pages, 'get_page', lambda *a, **kw: state)
    assert direct._lookup_current_saved_page(adapter) == []


def test_direct_lookup_missing_page_does_not_expand_scope(monkeypatch):
    from application_state.content import pages
    adapter, _ = _metadata_adapter()
    def missing(*args, **kwargs):
        raise ApplicationStateNotFoundError('missing')
    monkeypatch.setattr(pages, 'get_page', missing)
    assert direct._lookup_current_saved_page(adapter) == []


@pytest.mark.parametrize('denied', [False, True])
def test_direct_runtime_never_enumerates_when_current_page_is_missing_or_denied(monkeypatch, denied):
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.build_intentional_response import resolution_for
    from apps.live_control_server.services import build_related_pages
    from tests.test_build_source_free_protocol import pending_app_runtime_case
    with pending_app_runtime_case(monkeypatch) as (state, adapter):
        execution = state.turn.graph_context_execution
        work = execution.events[3]
        work = work.model_copy(update={'resolution': resolution_for(execution.policy, 'discuss',
            source_scope='current_saved_page')})
        execution = type(execution).model_validate_json(execution.model_copy(update={
            'events': [*execution.events[:3], work]}).model_dump_json(by_alias=True))
        state.turn = t.Turn.model_validate(state.turn.model_copy(update={'graph_context_execution': execution}))
        adapter.fence.renewer.update_turn(state.turn)
        if denied:
            state.denied = True
            monkeypatch.setattr(direct, '_lookup_current_saved_page', lambda _: pytest.fail('Denied page metadata read'))
        else:
            monkeypatch.setattr(direct, '_lookup_current_saved_page', lambda _: [])
        monkeypatch.setattr(build_related_pages, 'discover', lambda *a, **kw: pytest.fail('World catalog enumerated'))
        if denied:
            from application_state.errors import ApplicationStateConflictError
            with pytest.raises(ApplicationStateConflictError, match='access'):
                asyncio.run(direct.acquire_pending_app_pages(adapter, object()))
        else:
            asyncio.run(direct.acquire_pending_app_pages(adapter, object()))
            assert direct.effective_pending_app_catalog(adapter._broker_receipt(), adapter._broker_execution()) == ()


def test_direct_runtime_selects_and_reads_only_frozen_current_page(monkeypatch):
    import hashlib
    import json
    import httpx2
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.build_intentional_response import resolution_for
    from application_state.agent_conversation.build_related_pages import RelatedPageRead
    from tests.test_build_source_free_routing import seal_pending_receipt
    from application_state.content import pages
    from apps.live_control_server.services import build_jev_dispatch, build_related_pages
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from tests.test_build_source_free_protocol import pending_app_runtime_case
    monkeypatch.setattr(build_jev_dispatch, 'MODEL', 'jev-1.14.0')
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY', 'synthetic-only')
    text = 'The exact saved page records a possible dream.'
    digest = hashlib.sha256(text.encode()).hexdigest()

    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request):
            body = json.loads(request.content)
            return httpx2.Response(200, request=request, json={'model': body['model'], 'usage': {'input_tokens': 23, 'output_tokens': 4},
                'answers': {key: {'type': 'choice', 'choice': 'read', 'confidence': 1,
                    'probabilities': {'read': 1.0, 'skip': 0.0}} for key in body['questions']}})

    with pending_app_runtime_case(monkeypatch) as (state, adapter):
        receipt = state.turn.graph_context_receipt
        data = receipt.model_dump(mode='json', by_alias=True)
        data.pop('context_receipt_sha256')
        data['work_context']['source_basis']['content_sha256'] = digest
        provenance = state.turn.provenance.model_copy(update={'primary_work':
            state.turn.provenance.primary_work.model_copy(update={'content_sha256': digest})})
        data['provenance_sha256'] = t.canonical_sha256(provenance)
        receipt = seal_pending_receipt(data)
        execution = state.turn.graph_context_execution
        intent = execution.policy.action.intent
        intent = intent.model_copy(update={'primary_work': intent.primary_work.model_copy(update={
            'expected_content_sha256': digest})})
        policy = execution.policy.model_copy(update={'action': execution.policy.action.model_copy(update={'intent': intent})})
        events = list(execution.events[:4])
        events[3] = events[3].model_copy(update={'resolution': resolution_for(policy, 'discuss',
            source_scope='current_saved_page')})
        from tests.test_build_source_free_routing import pending_execution
        execution = pending_execution(receipt, policy, events)
        state.turn = t.Turn.model_validate(state.turn.model_copy(update={
            'graph_context_receipt': receipt, 'graph_context_execution': execution, 'provenance': provenance,
            'submitted_intent_fingerprint_v2': t.submitted_turn_intent_fingerprint_v2(intent)}))
        adapter.turn = state.turn
        adapter.fence.renewer.update_turn(state.turn)
        adapter.context_capture.bound_context_receipt_sha256 = receipt.context_receipt_sha256
        basis = receipt.work_context.source_basis
        page = SimpleNamespace(work_object_id=UUID(basis.document_id), world_id=basis.world_id,
            object_revision=basis.registry_revision, status='active', current_revision_id=uuid4(), title='Saved page')
        metadata = SimpleNamespace(visibility_state=basis.visibility, document_class='lore', authority_state='draft')
        monkeypatch.setattr(pages, 'get_page', lambda document_id, *, world_id: SimpleNamespace(page=page, metadata=metadata))
        monkeypatch.setattr(build_related_pages, 'discover', lambda *a, **kw: pytest.fail('World catalog enumerated'))
        monkeypatch.setattr(build_related_pages, 'materialize', lambda pointer: dict(
            pointer.model_dump(mode='json'), content_sha256=digest, markdown=text))
        harness = BuildJevHarness(decision_transport=Transport())
        harness.adapter, harness.calls, harness.timings, harness._inflight = adapter, [], [], {}
        asyncio.run(direct.acquire_pending_app_pages(adapter, harness))
        reads = [event for event in adapter._broker_execution().events if type(event) is RelatedPageRead]
        assert len(reads) == 1 and reads[0].markdown == text
        assert str(reads[0].page.document_id) == basis.document_id
        assert reads[0].page.content_sha256 == basis.content_sha256
