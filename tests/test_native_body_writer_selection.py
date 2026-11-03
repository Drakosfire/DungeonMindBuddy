"""Acquired native bodies share the existing selector, writer and citation owner."""
import asyncio
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t, native_corpus as bodies
from application_state.agent_conversation import writer_evidence_selection as selection
from application_state.agent_conversation.native_writer import model_frame, model_work_frame, verify_input_records, body_handle
from application_state.agent_conversation.native_completion import normalize_output
from tests.test_native_corpus_source_access import lane as lane
from tests.test_surface_native_writer import body_case, actual_sdk_request, authorize, work_submission, BODY
from tests.test_surface_native_execution import execution
from tests.test_surface_native_completion import producing_case, answer


def two_reads(lane):
    context, record, first = body_case('build', lane)
    events = list(record.events[:-1])  # Preserve the old V1 vote separately below.
    old_vote = record.events[-1]
    search = next(e for e in events if isinstance(e, bodies.NativeBodySearchObservedV1))
    catalog = search.catalogs[0]
    full = bodies.native_full_document_handle(catalog.catalog_sha256)
    decision_index = next(i for i, e in enumerate(events) if isinstance(e, t.PlanJevRetrievalSelectionV1)
                          and bodies.native_body_handle(catalog.catalog_sha256, catalog.sections[0].section_id) in e.selected_handles)
    events[decision_index] = events[decision_index].model_copy(update={
        'selected_handles': [*events[decision_index].selected_handles, full]})
    index = events.index(first) + 1
    grant = bodies.NativeBodyReadAuthorizedV1(event_id=uuid4(), sequence=index,
        provider_attempt_id=events[decision_index].controller_attempt_id, search_event_id=search.event_id,
        catalog_sha256=catalog.catalog_sha256, retrieval_kind='full_document', section_id=None)
    second = bodies.NativeBodyReadObservedV1(event_id=uuid4(), sequence=index+1,
        authorization_event_id=grant.event_id, excerpt=bodies.select_native_full_document(catalog, BODY), failure_code=None)
    events[index:index] = [grant, second]
    events = [e.model_copy(update={'sequence': i}) for i, e in enumerate(events)]
    record = execution(context.context_receipt_sha256, record.policy, events)
    return context, record, first, second, old_vote


def settle(context, record, old_vote, judgments):
    catalog = selection.acquired_catalog(record, {'capture_status': 'recording'})
    vote = t.BuildWriterEvidenceSelectionV2(**(old_vote.model_dump() | dict(
        kind='build_writer_evidence_selection_v2', policy=selection.NATIVE_POLICY, sequence=len(record.events),
        judgments=judgments, catalog_sha256=selection.digest(catalog), **selection.close_selection(catalog, judgments))))
    return execution(context.context_receipt_sha256, record.policy, [*record.events, vote]), vote


@pytest.mark.parametrize('judgment', ['direct_support', 'qualification_or_conflict', 'uncertain'])
def test_native_body_selection_preserves_exact_catalog_and_sdk_citation_boundary(lane, judgment):
    context, record, first, second, old = two_reads(lane)
    catalog = selection.acquired_catalog(record, {'capture_status': 'recording'})
    assert set(catalog) == {bodies.body_selection_unit_id(first), bodies.body_selection_unit_id(second)}
    for read in (first, second):
        unit = catalog[bodies.body_selection_unit_id(read)]
        assert unit['passage']['text'] == read.excerpt.text
        assert unit['extent'] == read.excerpt.section.model_dump(mode='json')
        assert unit['catalog_sha256'] == read.excerpt.catalog_sha256
    wire = selection.source_projection(catalog)
    assert len(wire['source_origins']) == 1 and len(wire['sources']) == 2
    judgments = {bodies.body_selection_unit_id(first): judgment, bodies.body_selection_unit_id(second): 'irrelevant'}
    chosen, vote = settle(context, record, old, judgments)
    assert bodies.acquired_body_reads(chosen) == bodies.acquired_body_reads(record)
    assert bodies.selected_body_reads(chosen) == (first,)
    assert not vote.source_event_ids  # Native reads never impersonate classic source receipts.
    assert type(chosen).model_validate_json(chosen.model_dump_json(by_alias=True)) == chosen
    frame = model_frame(context, chosen)
    work = work_submission(context, chosen)
    raw = asyncio.run(actual_sdk_request(frame, work_frame=model_work_frame(context, chosen, **work)))
    sent_frame = json.loads(json.loads(raw)['input'][0]['content'])
    assert sent_frame['native_body_evidence']['excerpts'][0]['text'] == first.excerpt.text
    assert 'Unselected private context.' not in raw
    stored, auth = authorize(context, chosen, raw, frame)
    support = verify_input_records(context, stored, auth, raw, **work)
    assert [s.read.event_id for s in support.body_excerpts] == [first.event_id]
    assert set(auth.native_read_event_ids) == {first.event_id, second.event_id}  # Acquisition history retained.
    candidate = answer([dict(kind='native_body_claim', text='The check revealed another plane.',
                             excerpt_handles=[body_handle(first)])])
    stored, auth, proof = producing_case(context, chosen, candidate)
    completed = normalize_output(context, stored, auth, **proof)
    assert completed.native_body_citations[0].read_event_id == first.event_id
    candidate['answer_segments'][0]['excerpt_handles'] = [body_handle(second)]
    stored, auth, proof = producing_case(context, chosen, candidate)
    with pytest.raises(ValueError):
        normalize_output(context, stored, auth, **proof)


def test_historical_v1_keeps_both_native_body_inputs_and_catalog_meaning(lane):
    context, record, first, second, old = two_reads(lane)
    old = old.model_copy(update={'sequence': len(record.events)})
    historical = execution(context.context_receipt_sha256, record.policy, [*record.events, old])
    assert selection.acquired_catalog(historical, {'capture_status': 'recording'}) == {}
    assert bodies.selected_body_reads(historical) == (first, second)
    assert 'Unselected private context.' in str(model_frame(context, historical))


@pytest.mark.parametrize('mutation', ['unknown', 'missing', 'excluded_included', 'late_read', 'text'])
def test_native_body_selection_rejects_changed_acquisition_and_closure(lane, mutation):
    context, record, first, second, old = two_reads(lane)
    judgments = {bodies.body_selection_unit_id(first): 'uncertain', bodies.body_selection_unit_id(second): 'irrelevant'}
    chosen, vote = settle(context, record, old, judgments)
    events = list(chosen.events)
    if mutation == 'unknown':
        vote = vote.model_copy(update={'judgments': judgments | {'body:'+str(uuid4()): 'direct_support'}})
    elif mutation == 'missing':
        vote = vote.model_copy(update={'judgments': {bodies.body_selection_unit_id(first): 'uncertain'}})
    elif mutation == 'excluded_included':
        vote = vote.model_copy(update={'expanded_unit_ids': list(judgments)})
    elif mutation == 'late_read':
        events.append(first.model_copy(update={'event_id': uuid4(), 'sequence': len(events)}))
    else:
        i = next(i for i,e in enumerate(events) if e.event_id == first.event_id)
        events[i] = first.model_copy(update={'excerpt': first.excerpt.model_copy(update={'text': 'Forged'})})
    events[vote.sequence] = vote
    with pytest.raises(ValueError):
        changed = execution(context.context_receipt_sha256, record.policy, events)
        model_frame(context, changed)


def test_failed_acquisitions_remain_partial_and_are_not_selector_units(lane):
    context, record, read = body_case('build', lane, failed=True)
    before = record.model_copy(update={'events': record.events[:-1]})
    chosen, _ = settle(context, before, record.events[-1], {})
    assert selection.acquired_catalog(chosen, {'capture_status': 'recording'}) == {}
    assert bodies.acquired_body_reads(chosen) == ()
    assert model_frame(context, chosen)['input_status'] == 'partial'
    assert any(e.event_id == read.event_id for e in chosen.events)
