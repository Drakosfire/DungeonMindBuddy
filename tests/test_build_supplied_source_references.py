"""Exact SDK source selections replace regenerated quote witnesses, not source authority."""
from copy import deepcopy
import json
import pytest
from jsonschema import Draft202012Validator
from application_state.agent_conversation import types as t
from application_state.agent_conversation import build_related_pages as related
from application_state.agent_conversation.native_build_work_view import semantic_frame, selection_aliases
from application_state.agent_conversation.native_writer import model_work_frame, model_frame, verify_input_records
from application_state.agent_conversation.native_completion import normalize_output, verify_completion
from application_state.agent_conversation.plan_writer_output_schema import native_output_format
from tests.test_surface_native_related_pages import case, BODY
from tests.test_surface_native_work_input import produce
from tests.test_surface_native_execution import execution
from tests.test_surface_native_completion import answer
from tests.test_plan_writer_output_schema import rules


def proof_case(*, historical=False, edit=None, selector='related', quotes=False):
    context, record, work = case(draft=False)
    host = model_work_frame(context, record, **work)
    view = semantic_frame(host, record, supplied_source_references=not historical)
    aliases = selection_aliases(host)
    rid = host['related_authored_pages']['pages'][0]['read_id']
    if selector == 'related':
        claim = dict(kind='related_page_claim', text='The saved neighbour proposes a lamp repair.', read_id=aliases[rid])
    else:
        claim = dict(kind='saved_source_claim', text='The selected saved section is authored context.',
                     section_read_ids=[aliases[host['artifact_under_edit']['sections'][0]['read_id']]])
    if quotes:
        claim['supporting_quotes'] = ['“A copper lamp awaits repair. 🌸”']
    if edit:
        edit(claim, host)
    candidate = answer([claim])
    if not historical:
        Draft202012Validator(native_output_format(model_frame(context, record), rules(), host | view, build_local=True)['schema']).validate(candidate)
    def project(value):
        value.clear(); value.update(deepcopy(view))
    stored, old, proof, _ = produce(context, record, work, mutate=project, candidate=candidate)
    from application_state.agent_conversation.native_execution import NativeBuildWriterAuthorizedV2
    auth = NativeBuildWriterAuthorizedV2.model_validate_json(json.dumps(old.model_dump(mode='json', by_alias=True) | {
        'kind': 'native_build_writer_authorized_v2', 'work_frame_sha256': t.canonical_sha256(host)}))
    stored = execution(context.context_receipt_sha256, stored.policy,
        [auth if event.event_id == auth.event_id else event for event in stored.events])
    return context, stored, auth, proof, work, host, view


@pytest.mark.parametrize('selector', ['related', 'saved'])
def test_actual_sdk_selected_reference_binds_existing_exact_owner(selector):
    context, stored, auth, proof, work, host, view = proof_case(selector=selector)
    evidence = verify_input_records(context, stored, auth, proof['prepared_request_json'], **work)
    assert evidence.supplied_source_references
    result = normalize_output(context, stored, auth, **proof)
    assert verify_completion(result, context, stored, auth, **proof) == result
    claim, = result.answer_segments
    if selector == 'related':
        assert claim.page == evidence.related_pages[0].page
        assert evidence.related_pages[0].markdown == BODY
    else:
        assert claim.content_sha256 == host['source_basis']['content_sha256']
        assert len(result.saved_source_citations) == 1


def test_historical_quoted_contract_still_refuses_added_punctuation():
    context, stored, auth, proof, work, host, view = proof_case(historical=True, quotes=True)
    with pytest.raises(ValueError, match='quote is absent'):
        normalize_output(context, stored, auth, **proof)


@pytest.mark.parametrize('change', ['unknown', 'wrong_kind', 'host_identity', 'extra_quotes'])
def test_finite_schema_refuses_unknown_cross_kind_host_ids_and_copied_quotes(change):
    def edit(claim, host):
        if change == 'unknown': claim['read_id'] = 'source999'
        elif change == 'wrong_kind': claim['read_id'] = selection_aliases(host)[host['artifact_under_edit']['sections'][0]['read_id']]
        elif change == 'host_identity': claim['read_id'] = host['related_authored_pages']['pages'][0]['read_id']
        else: claim['supporting_quotes'] = ['arbitrary']
    from jsonschema import ValidationError
    with pytest.raises(ValidationError):
        proof_case(edit=edit)


@pytest.mark.parametrize('kind', ['saved_source_claim', 'related_page_claim'])
@pytest.mark.parametrize('selection', ['unknown', 'wrong_kind', 'duplicate', 'empty'])
def test_normalization_independently_refuses_unadmitted_and_mixed_source_choices(kind, selection):
    from application_state.agent_conversation.build_draft_answer import normalize_native_segment
    from application_state.agent_conversation.build_primary_context import records
    context, record, work = case(draft=False)
    from application_state.agent_conversation.native_build_work_view import resolve_selectors
    host = model_work_frame(context, record, **work)
    pages = related.records(record)
    sections = records(record, context.work_context.source_basis)
    actual = str(pages[0].read_id) if kind == 'related_page_claim' else str(sections[0].read_id)
    wrong = str(sections[0].read_id) if kind == 'related_page_claim' else str(pages[0].read_id)
    if kind == 'related_page_claim' and selection in {'duplicate', 'empty'}:
        value = [] if selection == 'empty' else [actual, actual]
    else:
        value = 'unadmitted' if selection == 'unknown' else wrong if selection == 'wrong_kind' else actual
    claim = dict(kind=kind, text='A proposed authored detail.')
    if kind == 'related_page_claim': claim['read_id'] = value
    else: claim['section_read_ids'] = [] if selection == 'empty' else [value, value] if selection == 'duplicate' else [value]
    with pytest.raises(ValueError):
        normalize_native_segment(claim, draft_record=None, saved_sections=sections, related_pages=pages,
            source_basis=context.work_context.source_basis, index=0, supplied_source_references=True)


@pytest.mark.parametrize('quote', [None, [], ['“Formatted quote”']])
def test_new_policy_never_infers_or_repairs_model_quote_witnesses(quote):
    from application_state.agent_conversation.build_draft_answer import normalize_native_segment
    context, record, work = case(draft=False)
    pages = related.records(record)
    with pytest.raises(ValueError, match='cannot carry regenerated quotes'):
        normalize_native_segment(dict(kind='related_page_claim', text='An authored claim.',
            read_id=str(pages[0].read_id), supporting_quotes=quote), draft_record=None,
            saved_sections=[], related_pages=pages, source_basis=context.work_context.source_basis,
            index=0, supplied_source_references=True)
