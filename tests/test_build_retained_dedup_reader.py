"""Reader-first presentation of duplicate retained native reads."""
from types import SimpleNamespace
from uuid import uuid4
import asyncio
import json

import httpx
import pytest
from jsonschema import Draft202012Validator

from application_state.agent_conversation import native_corpus as corpus, retained_conversation as retained
from application_state.agent_conversation import types as t
from tests.test_build_retained_conversation import capture, fixture_closure
from tests.test_native_corpus_source_access import admit, capture as capture_sources, lane as lane
from tests.test_surface_native_writer import BODY, body_case


def _closure(lane, policy):
    _receipt, execution, read = body_case('build', lane)
    catalog = corpus.acquired_body_catalogs(execution)[read.excerpt.catalog_sha256]
    current, turns = fixture_closure(count=2)
    value = capture(current, turns)
    occurrence = t.RetainedContextOccurrenceV1(turn_id=turns[0].turn_id,
        attempt=turns[0].attempt, event_id=read.event_id)
    other_read = read.model_copy(update={'event_id': uuid4()})
    other_occurrence = occurrence.model_copy(update={'event_id': other_read.event_id})
    rows = (t.RetainedNativeContextV1(catalog=catalog, read=read, occurrences=(occurrence,)),
        t.RetainedNativeContextV1(catalog=catalog, read=other_read, occurrences=(other_occurrence,)))
    value = value.model_copy(update={'world_id': 'managed', 'authored_context': (),
        'native_context': rows, 'presentation_policy': policy})
    value = type(value).model_validate_json(value.model_dump_json(by_alias=True))
    return value, catalog, read, occurrence, execution


def test_v5_deduplicates_writer_rows_without_dropping_closure_or_history(lane):
    v4, _catalog, _read, _occurrence, _execution = _closure(lane, 'retained_conversation_semantic_v4')
    v5 = type(v4).model_validate_json(v4.model_copy(update={
        'presentation_policy': 'retained_conversation_semantic_v5'}).model_dump_json(by_alias=True))
    old, new = SimpleNamespace(events=(v4,)), SimpleNamespace(events=(v5,))
    assert len(retained.writer_native_supports(old)) == 2
    assert len(retained.writer_native_supports(new)) == 1
    assert len(retained.native_supports(new)) == 2
    assert retained.dialogue_messages(old) == retained.dialogue_messages(new)
    assert v5.native_context == v4.native_context and v5.history == v4.history
    assert retained.writer_native_supports(new)[0].read.event_id == v5.native_context[0].read.event_id
    old_rows = retained.native_frame_rows(old, _catalog.authority, lambda read: str(read.event_id))
    new_rows = retained.native_frame_rows(new, _catalog.authority, lambda read: str(read.event_id))
    assert len(old_rows) == 2 and new_rows == old_rows[:1]


def test_v5_never_deduplicates_different_authorized_access_spans(lane):
    value, catalog, read, occurrence, _execution = _closure(lane, 'retained_conversation_semantic_v5')
    source = catalog.source.model_copy(update={'access_span_id': catalog.source.access_span_id + '-different'})
    other_catalog = corpus.build_native_body_catalog(catalog.authority, source, BODY)
    other_read = read.model_copy(update={'event_id': uuid4(), 'excerpt':
        corpus.select_native_body_excerpt(other_catalog, BODY, other_catalog.sections[0].section_id)})
    other_occurrence = occurrence.model_copy(update={'event_id': other_read.event_id})
    different = t.RetainedNativeContextV1(catalog=other_catalog, read=other_read,
        occurrences=(other_occurrence,))
    value = value.model_copy(update={'native_context': (value.native_context[0], different)})
    assert len(retained.writer_native_supports(SimpleNamespace(events=(value,)))) == 2


def test_v5_reuses_same_exact_source_across_access_epochs(lane):
    value, catalog, read, occurrence, _execution = _closure(lane, 'retained_conversation_semantic_v5')
    epoch = max(catalog.authority.acquisition_epoch, catalog.source.proof_epoch) + 1
    authority = catalog.authority.model_copy(update={'acquisition_epoch': epoch})
    source = catalog.source.model_copy(update={'proof_epoch': epoch})
    other_catalog = corpus.build_native_body_catalog(authority, source, BODY)
    other_read = read.model_copy(update={'event_id': uuid4(), 'excerpt':
        corpus.select_native_body_excerpt(other_catalog, BODY, other_catalog.sections[0].section_id)})
    other_occurrence = occurrence.model_copy(update={'event_id': other_read.event_id})
    refreshed = t.RetainedNativeContextV1(catalog=other_catalog, read=other_read,
        occurrences=(other_occurrence,))
    value = value.model_copy(update={'native_context': (value.native_context[0], refreshed)})
    execution = SimpleNamespace(events=(value,))
    assert len(retained.native_supports(execution)) == 2
    assert len(retained.writer_native_supports(execution)) == 1
    rows = retained.native_frame_rows(execution, catalog.authority, lambda read: str(read.event_id))
    assert len(rows) == 1 and rows[0]['text'] == read.excerpt.text
    section = read.excerpt.section
    citation = t.NativeBodyExcerptCitationV1(segment_index=0, text_sha256='a' * 64,
        provider_attempt_id=uuid4(), envelope_sha256='b' * 64, read_event_id=read.event_id,
        catalog_sha256=catalog.catalog_sha256,
        source_artifact_id=catalog.source.artifact.source_artifact_id,
        native_source_revision_id=catalog.source.revision.source_revision_id,
        content_sha256=catalog.source.revision.content_sha256, excerpt_sha256=read.excerpt.excerpt_sha256,
        section_id=section.section_id, selector_policy=read.excerpt.selector_policy,
        source_name=corpus.body_source_name(catalog), section_title=section.label,
        line_start=section.line_start, line_end=section.line_end)
    resolved_catalog, resolved_section, resolved_text = corpus.resolve_retained_body_citation(execution, citation)
    assert (resolved_catalog, resolved_section, resolved_text) == (catalog, section, read.excerpt.text)


def test_v5_keeps_identical_text_from_distinct_sources(lane):
    value, _catalog, read, occurrence, _execution = _closure(lane, 'retained_conversation_semantic_v5')
    second = admit(lane, name='other', body=BODY)
    sources = capture_sources(lane)
    source = next(member for member in sources.members
                  if member.artifact.source_artifact_id == second.source_artifact_id)
    catalog = corpus.build_native_body_catalog(sources.authority, source, BODY)
    read = read.model_copy(update={'event_id': uuid4(), 'excerpt':
        corpus.select_native_body_excerpt(catalog, BODY, catalog.sections[0].section_id)})
    occurrence = occurrence.model_copy(update={'event_id': read.event_id})
    other = t.RetainedNativeContextV1(catalog=catalog, read=read, occurrences=(occurrence,))
    value = value.model_copy(update={'native_context': (value.native_context[0], other)})
    assert len(retained.writer_native_supports(SimpleNamespace(events=(value,)))) == 2


def test_v5_keeps_same_source_from_different_graph_revisions(lane):
    value, catalog, read, occurrence, _execution = _closure(lane, 'retained_conversation_semantic_v5')
    authority = catalog.authority.model_copy(update={'revision_id': catalog.authority.revision_id + '-different'})
    other_catalog = corpus.build_native_body_catalog(authority, catalog.source, BODY)
    other_read = read.model_copy(update={'event_id': uuid4(), 'excerpt':
        corpus.select_native_body_excerpt(other_catalog, BODY, other_catalog.sections[0].section_id)})
    other_occurrence = occurrence.model_copy(update={'event_id': other_read.event_id})
    other = t.RetainedNativeContextV1(catalog=other_catalog, read=other_read,
        occurrences=(other_occurrence,))
    value = value.model_copy(update={'native_context': (value.native_context[0], other)})
    assert len(retained.writer_native_supports(SimpleNamespace(events=(value,)))) == 2


def test_v5_keeps_different_extents_of_the_same_authorized_body(lane):
    value, catalog, read, occurrence, _execution = _closure(lane, 'retained_conversation_semantic_v5')
    assert len(catalog.sections) > 1
    other_read = read.model_copy(update={'event_id': uuid4(), 'excerpt':
        corpus.select_native_body_excerpt(catalog, BODY, catalog.sections[1].section_id)})
    other_occurrence = occurrence.model_copy(update={'event_id': other_read.event_id})
    other = t.RetainedNativeContextV1(catalog=catalog, read=other_read, occurrences=(other_occurrence,))
    value = value.model_copy(update={'native_context': (value.native_context[0], other)})
    assert len(retained.writer_native_supports(SimpleNamespace(events=(value,)))) == 2


def test_v5_keeps_same_text_with_different_session_scope(lane):
    value, catalog, read, occurrence, _execution = _closure(lane, 'retained_conversation_semantic_v5')
    scope = 999 if catalog.source.session_scope != 999 else 998
    source = catalog.source.model_copy(update={'session_scope': scope})
    other_catalog = corpus.build_native_body_catalog(catalog.authority, source, BODY)
    other_read = read.model_copy(update={'event_id': uuid4(), 'excerpt':
        corpus.select_native_body_excerpt(other_catalog, BODY, other_catalog.sections[0].section_id)})
    other = t.RetainedNativeContextV1(catalog=other_catalog, read=other_read, occurrences=(
        occurrence.model_copy(update={'event_id': other_read.event_id}),))
    value = value.model_copy(update={'native_context': (value.native_context[0], other)})
    assert len(retained.writer_native_supports(SimpleNamespace(events=(value,)))) == 2


def test_v5_keeps_distinct_planning_metadata(lane):
    value, catalog, read, occurrence, _execution = _closure(lane, 'retained_conversation_semantic_v5')
    line = read.excerpt.section.line_start
    excerpt = read.excerpt.model_copy(update={
        'planning_ranges': corpus.NativeCorpusPlanningRangesV1(lines=((line, line),))})
    excerpt = type(excerpt).model_validate(excerpt.model_dump(mode='python'))
    other_read = read.model_copy(update={'event_id': uuid4(), 'excerpt': excerpt})
    other = t.RetainedNativeContextV1(catalog=catalog, read=other_read, occurrences=(
        occurrence.model_copy(update={'event_id': other_read.event_id}),))
    value = value.model_copy(update={'native_context': (value.native_context[0], other)})
    assert len(retained.writer_native_supports(SimpleNamespace(events=(value,)))) == 2


@pytest.mark.parametrize('forged', [False, True])
def test_v5_actual_writer_admits_only_offered_duplicate_and_reopens_citation(lane, monkeypatch, forged):
    from apps.live_control_server.services import build_jev_dispatch
    from tests.test_build_source_free_protocol import pending_writer_completion_case

    _receipt, source_execution, original_read = body_case('build', lane)
    original_catalog = corpus.acquired_body_catalogs(source_execution)[original_read.excerpt.catalog_sha256]
    original_search = next(event for event in source_execution.events
                           if isinstance(event, corpus.NativeBodySearchObservedV1))
    original_capture = retained.capture
    ids = (uuid4(), uuid4())

    def capture_v5(current, turns, **kwargs):
        # Two distinct previously admitted records of the same bytes, at two
        # source-view epochs, carried by a real pending writer fixture.
        authority = original_catalog.authority.model_copy(update={'managed_world_id': current.world_id})
        first = corpus.build_native_body_catalog(authority, original_catalog.source, BODY)
        next_epoch = max(authority.acquisition_epoch, first.source.proof_epoch) + 1
        second = corpus.build_native_body_catalog(authority.model_copy(update={'acquisition_epoch': next_epoch}),
            first.source.model_copy(update={'proof_epoch': next_epoch}), BODY)
        events = []
        for catalog, event_id in zip((first, second), ids):
            search = original_search.model_copy(update={'event_id': uuid4(), 'catalogs': (catalog,)})
            read = original_read.model_copy(update={'event_id': event_id, 'excerpt':
                corpus.select_native_body_excerpt(catalog, BODY, catalog.sections[0].section_id)})
            events.extend((search, read))
        turns[0].graph_context_execution.events += tuple(events)
        return original_capture(current, turns, **kwargs).model_copy(update={
            'presentation_policy': 'retained_conversation_semantic_v5'})

    monkeypatch.setattr(retained, 'capture', capture_v5)
    monkeypatch.setattr(build_jev_dispatch, 'MODEL', 'jev-1.14.0')
    calls = []

    def respond(request):
        body = json.loads(request.content)
        calls.append(body)
        schema = body['text']['format']['schema']
        variants = schema['properties']['answer_segments']['items']['anyOf']
        claim = next(row for row in variants if row['properties']['kind'].get('const') == 'native_body_claim')
        aliases = claim['properties']['excerpt_handles']['items']['enum']
        assert len(aliases) == 1
        validator = Draft202012Validator(claim)
        text = 'The check revealed another plane.'
        assert validator.is_valid({'kind': 'native_body_claim', 'text': text, 'excerpt_handles': aliases})
        assert not validator.is_valid({'kind': 'native_body_claim', 'text': text, 'excerpt_handles': ['body1']})
        candidate = {'answer_segments': [{'kind': 'native_body_claim', 'text': text,
                      'excerpt_handles': ['body1'] if forged else aliases}], 'limitations': []}
        if 'collaboration' in schema['properties']:
            candidate['collaboration'] = None
        return httpx.Response(200, request=request, json={'id': 'resp_dedup', 'object': 'response',
            'created_at': 1, 'model': body['model'], 'status': 'completed', 'output': [{
                'type': 'message', 'id': 'msg_dedup', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}]})

    with pending_writer_completion_case(monkeypatch) as (state, _adapter, _rules, writer, _prepared):
        if forged:
            from generationengine.types import GenerationEngineError
            with pytest.raises(GenerationEngineError, match='did not satisfy'):
                asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
            assert state.completions == 0
            return
        completed = asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
        assert completed.status == 'completed' and len(calls) == 1 and state.materialized == 0
        assert len(retained.admission(completed.graph_context_execution).native_context) == 2
        citation, = completed.completion.native_body_citations
        assert citation.read_event_id == ids[0]
        _catalog, _section, text = corpus.resolve_retained_body_citation(completed.graph_context_execution, citation)
        assert text == original_read.excerpt.text
        from dataclasses import replace
        from application_state.agent_conversation.surface_evidence_answer import native_fact_segment
        from application_state.agent_conversation.native_plan_assertions import POLICY
        selected = retained.writer_native_supports(completed.graph_context_execution)
        evidence = SimpleNamespace(body_excerpts=(replace(selected[0], handle='body0'),))
        auth = SimpleNamespace(provider_attempt_id=uuid4(), envelope_sha256='b' * 64)
        with pytest.raises(ValueError, match='excerpt selections'):
            native_fact_segment({'kind': 'native_body_claim', 'text': 'Unsupported', 'excerpt_handles': ['body1']},
                policy=POLICY, receipt=None, auth=auth, support=evidence, index=0)
