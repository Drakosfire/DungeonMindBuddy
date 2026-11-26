"""Future current-only evidence must never be presented as a World catalog."""
from uuid import uuid4

import pytest

from application_state.agent_conversation.build_pending_app_coverage import pending_related_pages_project
from application_state.agent_conversation.build_source_free import BuildAppPageCatalogObservedV1
from application_state.agent_conversation.native_build_work_view import semantic_frame
from application_state.agent_conversation.build_primary_context import NATIVE_WORK_SCHEMA
from tests.test_build_source_free_routing import pending_execution, pending_execution_pair, pending_work_prefix


def _project(scope, *, wrong=False, empty=False):
    receipt, policy = pending_execution_pair()
    current_id = str(uuid4())
    intent = policy.action.intent
    intent = intent.model_copy(update={'primary_work': intent.primary_work.model_copy(update={'object_id': current_id})})
    policy = policy.model_copy(update={'action': policy.action.model_copy(update={'intent': intent})})
    events = pending_work_prefix(policy, scope=scope)
    basis = receipt.work_context.source_basis
    pointer = {'world_id': basis.world_id, 'document_id': str(uuid4()) if wrong else current_id,
        'registry_revision': basis.registry_revision, 'title': 'Saved page', 'visibility': basis.visibility}
    event = BuildAppPageCatalogObservedV1.model_validate({
        'event_id': uuid4(), 'sequence': len(events), 'work_event_id': events[-1].event_id,
        'pending_context_receipt_sha256': receipt.context_receipt_sha256,
        'admitted_from_revision': 1, 'pages': [] if empty else [pointer]})
    execution = pending_execution(receipt, policy, [*events, event])
    return pending_related_pages_project(execution), execution


def test_future_scope_projects_only_current_page_and_explicit_absence_limit():
    related, execution = _project('current_saved_page')
    assert related['catalog_scope'] == 'exact_current_saved_page_only'
    assert related['absence_authority'] == 'not_proven_by_this_saved_page_catalog'
    host = {'schema': NATIVE_WORK_SCHEMA, 'source_basis': {'visibility': 'internal'},
            'artifact_under_edit': {'sections': []}, 'related_authored_pages': related}
    frame = semantic_frame(host, execution)['build_work']
    assert frame['related_page_scope'] == 'Only the requested current saved page was eligible for this offer; other saved pages were not inventoried.'
    assert frame['related_page_absence'] == 'This catalog does not prove that other pages do not exist.'


def test_historical_catalog_scope_is_unchanged():
    related, execution = _project('source_lookup')
    assert related['catalog_scope'] == 'active_committed_worldbuilding_pages_in_this_world_including_current'
    host = {'schema': NATIVE_WORK_SCHEMA, 'source_basis': {'visibility': 'internal'},
            'artifact_under_edit': {'sections': []}, 'related_authored_pages': related}
    assert semantic_frame(host, execution)['build_work']['related_page_scope'] == (
        'Saved active worldbuilding pages in this World, including the current page when offered.')


def test_future_scope_cannot_project_a_different_page():
    with pytest.raises(ValueError, match='cannot project another page'):
        _project('current_saved_page', wrong=True)


def test_empty_current_scope_does_not_claim_a_page_was_offered():
    related, execution = _project('current_saved_page', empty=True)
    assert related['availability'] == [] and related['pages'] == []
    host = {'schema': NATIVE_WORK_SCHEMA, 'source_basis': {'visibility': 'internal'},
            'artifact_under_edit': {'sections': []}, 'related_authored_pages': related}
    frame = semantic_frame(host, execution)['build_work']
    assert frame['related_page_availability'] == []
    assert 'eligible for this offer' in frame['related_page_scope']


def test_future_projection_preserves_the_actual_acquired_body_and_citation_alias():
    from application_state.agent_conversation.build_intentional_response import resolution_for
    from tests.test_build_source_free_protocol import pending_page_phase_case
    receipt, policy, events = pending_page_phase_case()
    page_id = str(events[-1].page.document_id)
    intent = policy.action.intent
    intent = intent.model_copy(update={'primary_work': intent.primary_work.model_copy(update={'object_id': page_id})})
    policy = policy.model_copy(update={'action': policy.action.model_copy(update={'intent': intent})})
    events[3] = events[3].model_copy(update={'resolution': resolution_for(
        policy, 'discuss', source_scope='current_saved_page')})
    execution = pending_execution(receipt, policy, events)
    related = pending_related_pages_project(execution)
    assert related['pages'][0]['markdown'] == events[-1].markdown
    assert related['pages'][0]['read_id'] == str(events[-1].read_id)
    host = {'schema': NATIVE_WORK_SCHEMA, 'source_basis': {'visibility': 'internal'},
            'artifact_under_edit': {'sections': []}, 'related_authored_pages': related}
    frame = semantic_frame(host, execution)['build_work']
    assert frame['related_pages'][0]['selection'] == 'source0'
    assert frame['related_pages'][0]['markdown'] == events[-1].markdown
    assert str(events[-1].read_id) not in str(frame)
