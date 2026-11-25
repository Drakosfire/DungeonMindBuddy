"""Acquired native bodies share the existing selector, writer and citation owner."""
import asyncio
import json
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t, native_corpus as bodies
from application_state.agent_conversation import authored_graph_references
from application_state.agent_conversation import writer_evidence_selection as selection
from application_state.agent_conversation.native_retrieval import (
    NativeRetrievalAuthorizedV1, NativeRetrievalSelectedV1, NativeRetrievalSelectedV2,
)
from application_state.agent_conversation.build_primary_context import NATIVE_WORK_SCHEMA
from application_state.agent_conversation.model_markdown import project_model_markdown
from application_state.agent_conversation.native_build_work_view import semantic_frame
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


def test_semantic_selection_slots_preserve_distinct_same_origin_text_and_no_host_ids(lane):
    from types import SimpleNamespace
    context,record,first,second,_=two_reads(lane)
    catalog=selection.acquired_catalog(record,{'capture_status':'recording'})
    turn=SimpleNamespace(graph_context_receipt=context,graph_context_execution=record,
        user_text='Preserve literal context_accounting and phase in my request.')
    state=selection.semantic_state(turn,catalog)
    wire=selection.canonical(dict(state=state,questions=selection.questions(catalog,semantic=True)))
    assert list(state['sources'])==['s0','s1']
    assert state['sources']['s0']['source_name']==state['sources']['s1']['source_name']
    assert 'context_accounting and phase' in state['user_question']
    assert set(row['text'] for row in state['sources'].values())=={first.excerpt.text,second.excerpt.text}
    for key,unit in catalog.items():
        assert key not in wire and unit['catalog_sha256'] not in wire
        assert unit['passage']['source_artifact_id'] not in wire
        assert unit['passage']['source_revision_id'] not in wire
    assert 'Classify source s0' in wire and 'Classify source s1' in wire


def test_projects_managed_images_and_preserves_source_line_addresses():
    source = (
        "# Survey\r\n"
        "\r\n"
        "Before ![North *gate*](dmb-media:private-asset\r\n"
        ' "dmb-image:v1 width=80 collapsed=false") after.\r\n'
        "\r\n"
        "![South door][survey-image]\r\n"
        "\r\n"
        "[survey-image]: dmb-media&#58;second-private-asset\r\n"
        "\r\n"
        "Last source line.\r\n"
    )

    assert project_model_markdown(source) == (
        "# Survey\r\n"
        "\r\n"
        "Before [Image: North gate] after.\r\n"
        "\r\n"
        "\r\n"
        "[Image: South door]\r\n"
        "\r\n"
        "\r\n"
        "\r\n"
        "Last source line.\r\n"
    )


def test_preserves_literal_documentation_and_plain_markdown():
    source = (
        "Keep **these words** and [the reference](https://example.org).\n\n"
        "`![Example](dmb-media:literal)`\n\n"
        "![Public](https://example.org/image.png)\n"
    )

    assert project_model_markdown(source) == source


def test_native_selection_binds_projected_bytes_before_dispatch(monkeypatch):
    text = "![Survey](dmb-media:private-asset)\n"
    catalog = {"host-source": {"kind": "saved_section", "section": {
        "text": text, "source_class": "authored", "line_start": 11, "line_end": 11,
    }}}
    turn = SimpleNamespace(
        user_text="What does the survey show?",
        graph_context_execution=SimpleNamespace(policy=object()),
    )
    monkeypatch.setattr(bodies, "acquired_body_catalogs", lambda _: {})
    monkeypatch.setattr(selection, "native_build", lambda _: True)
    monkeypatch.setattr(selection, "enabled", lambda _: True)
    monkeypatch.setattr(selection, "acquired_catalog", lambda *args, **kwargs: catalog)
    monkeypatch.setattr(selection, "selection_history", lambda *args: {})
    monkeypatch.setattr(selection, "native_terminal", lambda *args, **kwargs: {})

    def request(*, retained_raw_markdown=False):
        wire = selection.canonical({
            "model": "test-model",
            "state": selection.semantic_state(turn, catalog, retained_raw_markdown=retained_raw_markdown),
            "questions": selection.questions(catalog, semantic=True),
        })
        return wire, SimpleNamespace(model="test-model", sequence=2, envelope_sha256=sha256(wire.encode()).hexdigest())

    projected, authorization = request()
    admitted, acquired = selection.validate_prepared_selection(turn, authorization, projected, {})
    assert admitted["state"]["sources"]["s0"]["text"] == "[Image: Survey]\n"
    assert admitted["state"]["sources"]["s0"]["line_start"] == 11
    assert acquired["host-source"]["section"]["text"] == text

    historical, historical_authorization = request(retained_raw_markdown=True)
    with pytest.raises(ValueError, match="catalog"):
        selection.validate_prepared_selection(turn, historical_authorization, historical, {})
    selection.validate_prepared_selection(
        turn, historical_authorization, historical, {}, retained_proof=True,
    )


def test_build_writer_keeps_source_aliases_and_projects_author_visible_images(monkeypatch):
    monkeypatch.setattr(authored_graph_references, "model_reference_choices", lambda _: None)
    source = "![Survey](dmb-media:private-asset)\n"
    host = {
        "schema": NATIVE_WORK_SCHEMA,
        "source_basis": {"visibility": "internal"},
        "artifact_under_edit": {"sections": [
            {"read_id": str(uuid4()), "line_start": 7, "line_end": 7, "text": source},
        ]},
        "working_draft_context": {"record_id": str(uuid4()), "draft_markdown": source},
        "captured_editor": {"basis": {}, "draft_markdown": source},
        "related_authored_pages": {"availability": [], "pages": [
            {"read_id": str(uuid4()), "page": {"title": "Second survey", "visibility": "internal"},
             "markdown": source},
        ]},
    }

    current = semantic_frame(host, None)["build_work"]
    retained = semantic_frame(host, None, retained_raw_markdown=True)["build_work"]
    assert current["saved_sections"] == [
        {**retained["saved_sections"][0], "text": "[Image: Survey]\n"},
    ]
    assert current["current_draft"] == {"selection": "draft0", "markdown": "[Image: Survey]\n"}
    assert current["editor_markdown"] == "[Image: Survey]\n"
    assert current["related_pages"][0] == {**retained["related_pages"][0], "markdown": "[Image: Survey]\n"}
    assert host["artifact_under_edit"]["sections"][0]["text"] == source


def source_only_route_case():
    """Eligibility inputs only; live admission/codec checks use ordinary HTTP."""
    from tests.test_surface_native_execution import component
    context, record = component('build')
    query = t.NativePlanQueryUnavailableV1(managed_world_id='world-one',
        reason='native_graph_binding_unavailable')
    receipt = SimpleNamespace(native_query=query, source_authority=context.source_authority)
    return receipt, record


def test_conversation_route_can_reuse_source_support_without_active_graph():
    receipt, record = source_only_route_case()
    assert bodies.conversation_route_can_admit(receipt, record)


@pytest.mark.parametrize('boundary', ['head', 'source', 'query_world', 'source_world',
    'intent_world', 'plan', 'reviewed', 'reference', 'revision_pin', 'settled'])
def test_source_only_conversation_route_refuses_unproved_context(boundary):
    from application_state.agent_conversation.native_execution import NativeBuildQuerySettledV1
    from tests.test_surface_native_execution import component
    receipt, record = source_only_route_case()
    if boundary == 'head':
        receipt.native_query = receipt.native_query.model_copy(update={'reason':'native_graph_head_unavailable'})
    elif boundary == 'source':
        receipt.source_authority = t.NativeCorpusUnavailableV1(managed_world_id='world-one',
            failure_code='native_source_head_unavailable')
    elif boundary == 'query_world':
        receipt.native_query = receipt.native_query.model_copy(update={'managed_world_id':'foreign'})
    elif boundary == 'source_world':
        receipt.source_authority = receipt.source_authority.model_copy(update={'managed_world_id':'foreign'})
    elif boundary == 'plan':
        _, record = component('plan')
    elif boundary == 'settled':
        # The eligibility guard must reject the marker before inspecting payload.
        record = record.model_copy(update={'events':[NativeBuildQuerySettledV1.model_construct()]})
    else:
        intent = record.policy.action.intent
        if boundary == 'intent_world':
            intent = intent.model_copy(update={'world_id':'foreign'})
        elif boundary == 'reviewed':
            intent = intent.model_copy(update={'reviewed_step':object()})
        elif boundary == 'reference':
            intent = intent.model_copy(update={'authored_references':object()})
        else:
            intent = intent.model_copy(update={'graph_request':intent.graph_request.model_copy(
                update={'revision_pin':'rev:unproved'})})
        action = record.policy.action.model_copy(update={'intent':intent})
        record = record.model_copy(update={'policy':record.policy.model_copy(update={'action':action})})
    assert not bodies.conversation_route_can_admit(receipt, record)


@pytest.mark.parametrize('event_type', [*t.NATIVE_BODY_EVENTS, t.RelatedPageRead,
    NativeRetrievalAuthorizedV1, NativeRetrievalSelectedV1, NativeRetrievalSelectedV2])
def test_source_only_conversation_route_refuses_new_acquisition_after_admission(event_type):
    receipt, record = source_only_route_case()
    # Presence is the invariant; malformed payloads cannot make a forbidden
    # acquisition marker eligible before the full typed owner rejects them.
    events = [t.BuildPriorBodyEvidenceAdmittedV1.model_construct(), event_type.model_construct()]
    record = record.model_copy(update={'events':events})
    assert not bodies.conversation_route_can_admit(receipt, record)


def test_source_only_conversation_reader_fence_refuses_downgrade():
    from importlib import import_module
    fence = import_module('application_state.migrations.versions.20261122_0187_source_only_conversation_fence')
    assert fence.down_revision == '20261122_0186'
    with pytest.raises(RuntimeError, match='Use forward recovery'):
        fence.downgrade()
