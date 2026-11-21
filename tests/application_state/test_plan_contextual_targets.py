"""Complete semantic nominations grant at most one frozen edit destination."""
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation.plan_authoring import PlanAuthoringCaptureV1, text_digest
from application_state.agent_conversation.plan_contextual_targets import (
    resolve_targets, contextual_anchors, focused_target, compatible_selectors, resolve_anchor_targets,
)
from application_state.agent_conversation.plan_placement import (
    PlanPlacementCatalogV2, PlanPlacementOptionV2, PlanRequestedWorkInputV9,
    paragraph_placement_label,
)
from tests.application_state.test_plan_authoring import capture_payload
from tests.test_plan_jev_dispatch import plan_adapter as plan_adapter
from tests.test_plan_jev_harness import unavailable_native_sources as unavailable_native_sources


def captured_catalog(*, selected=False, duplicate=False):
    paragraphs = ["Alpha.", "Alpha." if selected or duplicate else "Beta."]
    nodes = [dict(type="paragraph", content=[dict(type="text", text=text)]) for text in paragraphs]
    editor = json.dumps(dict(type="doc", content=nodes), separators=(",", ":"))
    selection = json.dumps(dict(type="text", anchor=1, head=7 if selected else 1), separators=(",", ":"))
    markdown = "\n\n".join(paragraphs)
    payload = capture_payload() | dict(editor_json=editor, editor_sha256=text_digest(editor),
        selection_json=selection, selection_sha256=text_digest(selection), draft_markdown=markdown,
        draft_sha256=text_digest(markdown), target_kind="replace_selection" if selected else "insert_at_caret",
        selected_text="Alpha." if selected else "", **{"from": 1, "to": 7 if selected else 1})
    capture = PlanAuthoringCaptureV1.model_validate(payload)
    entries = [PlanPlacementOptionV2(selector="captured", kind="captured_target",
        label="Replace only the captured selection" if selected else "At the captured text caret",
        source_root_index=None, root_boundary=None, position=None, target_capture_sha256=capture.sha256)]
    if not selected:
        for selector, kind, index, boundary, position in (
            ("place1", "after_paragraph", 0, 1, 8),
            ("place2", "before_paragraph", 1, 1, 8),
            ("place3", "after_paragraph", 1, 2, 16 if duplicate else 15),
        ):
            row = PlanPlacementOptionV2(selector=selector, kind=kind,
                label=paragraph_placement_label(nodes, index, kind), source_root_index=index,
                root_boundary=boundary, position=position, target_capture_sha256="0" * 64)
            entries.append(row.model_copy(update={"target_capture_sha256": row.derived_target(capture).sha256}))
    catalog = PlanPlacementCatalogV2(original_capture_sha256=capture.sha256,
        editor_sha256=capture.editor_sha256, entries=tuple(entries))
    catalog.require_original(capture)
    return capture, catalog


def request_for(capture, catalog):
    return PlanRequestedWorkInputV9(request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256="0" * 64,
        question="Add a note after Alpha.", page_title="A page", dialogue=(),
        target_capture_sha256=capture.sha256, target_available=True,
        original_capture=capture, placement_catalog=catalog, authored_references=None,
        plan_requested_operation=None)


def test_equivalent_aliases_resolve_one_capture_without_discarding_nominations():
    capture, catalog = captured_catalog()
    result = resolve_targets(capture, catalog, "write_current_page", ("place2", "place1"))
    assert result["compatible_placement_selectors"] == ("place1", "place2")
    assert result["target_resolution"] == "unique"
    assert result["requested_work"] == "write_current_page"
    assert result["target_capture_sha256"] == catalog.resolve(capture, "place2").sha256


@pytest.mark.parametrize("selectors,resolution", [((), "missing"), (("place1", "place3"), "ambiguous")])
def test_no_unique_destination_cannot_become_writing(selectors, resolution):
    capture, catalog = captured_catalog()
    result = resolve_targets(capture, catalog, "write_current_page", selectors)
    assert result["requested_intent"] == "write_current_page"
    assert result["requested_work"] == "clarify" and result["target_resolution"] == resolution
    assert result["placement_selector"] is None and result["target_capture_sha256"] is None


@pytest.mark.parametrize("selectors", [("foreign",), ("place1", "place1")])
def test_unknown_or_duplicate_location_is_not_an_edit_authority(selectors):
    capture, catalog = captured_catalog()
    with pytest.raises(ValueError):
        resolve_targets(capture, catalog, "write_current_page", selectors)


def test_deliberate_selection_remains_exclusive_despite_duplicate_source_text():
    capture, catalog = captured_catalog(selected=True)
    result = resolve_targets(capture, catalog, "write_current_page", ("captured",))
    assert result["target_capture_sha256"] == capture.sha256
    focus = focused_target(request_for(capture, catalog))
    assert focus["kind"] == "replace_selection" and focus["selected_text"] == "Alpha."
    encoded = json.dumps(focus)
    assert capture.sha256 not in encoded and capture.world_id not in encoded
    assert "from" not in focus and "to" not in focus


def test_location_votes_are_complete_and_model_view_contains_no_host_bindings():
    capture, catalog = captured_catalog()
    request = request_for(capture, catalog)
    answers = {'placement_relation': 'after_paragraph', **{f'anchor_{i}': 'exclude'
        for i in range(len(contextual_anchors(request)))}}
    assert compatible_selectors(request, answers) == ()
    with pytest.raises(ValueError):
        compatible_selectors(request, answers | {'anchor_99': 'include'})
    answers.pop('anchor_0')
    with pytest.raises(ValueError):
        compatible_selectors(request, answers)
    from application_state.agent_conversation.plan_contextual_targets import prepare_contextual_work
    prepared = prepare_contextual_work(request)
    encoded = json.dumps({'state': prepared.state,
        'questions': [question.model_dump() for question in prepared.questions]})
    for forbidden in (capture.world_id, capture.document_id, capture.sha256, "source_root_index", "root_boundary"):
        assert forbidden not in encoded


def test_anchor_relation_maps_only_its_frozen_kind_and_keeps_duplicate_occurrences():
    capture, catalog = captured_catalog(duplicate=True)
    anchors = contextual_anchors(request_for(capture, catalog))
    assert [anchor['text'] for anchor in anchors if anchor['kind'] == 'paragraph'] == ['Alpha.', 'Alpha.']
    result = resolve_anchor_targets(capture, catalog, 'write_current_page', 'after_paragraph', ('anchor1',))
    assert result['compatible_placement_selectors'] == ('place1',)
    assert result['target_resolution'] == 'unique'
    ambiguous = resolve_anchor_targets(capture, catalog, 'write_current_page', 'after_paragraph', ('anchor1', 'anchor2'))
    assert ambiguous['target_resolution'] == 'ambiguous' and ambiguous['requested_work'] == 'clarify'
    for relation, nominated in [('after_paragraph', ('anchor0',)), ('after_heading', ('anchor1',)),
                               ('after_paragraph', ('foreign',)), ('after_paragraph', ('anchor1', 'anchor1'))]:
        with pytest.raises(ValueError):
            resolve_anchor_targets(capture, catalog, 'write_current_page', relation, nominated)


def test_unresolved_relation_retains_anchor_but_cannot_authorize_partial_placement():
    from types import SimpleNamespace
    from application_state.agent_conversation.plan_contextual_targets import clarification_question
    capture, catalog = captured_catalog()
    fields = resolve_anchor_targets(capture, catalog, 'write_current_page', 'unresolved', ('anchor1',))
    assert fields['requested_work'] == 'clarify' and fields['compatible_placement_selectors'] == ()
    assert fields['target_capture_sha256'] is None
    assert clarification_question(SimpleNamespace(**fields)) == (
        'Should I place the fragment before or after the identified text, or use another location?')


@pytest.mark.parametrize('selected', [False, True])
def test_unresolved_captured_relation_never_offers_unavailable_before_after_operations(selected):
    from types import SimpleNamespace
    from application_state.agent_conversation.plan_contextual_targets import clarification_question
    capture, catalog = captured_catalog(selected=selected)
    fields = resolve_anchor_targets(capture, catalog, 'write_current_page', 'unresolved', ('anchor0',))
    question = clarification_question(SimpleNamespace(**fields,
        original_capture=capture.model_dump(mode='json', by_alias=True),
        placement_catalog=catalog.model_dump(mode='json', by_alias=True)))
    assert 'before or after' not in question
    assert ('replace the current selection' if selected else 'current caret') in question


def test_indistinguishable_target_labels_ask_for_selection_instead_of_identical_alternatives():
    from types import SimpleNamespace
    from application_state.agent_conversation.plan_contextual_targets import clarification_question
    capture, catalog = captured_catalog(duplicate=True)
    # Two equal source passages at different document boundaries.
    rows = []
    for i, position in enumerate((8, 16)):
        row = PlanPlacementOptionV2(selector=f'place{i + 1}', kind='after_paragraph',
            label=paragraph_placement_label(json.loads(capture.editor_json)['content'], i, 'after_paragraph'),
            source_root_index=i, root_boundary=i + 1, position=position,
            target_capture_sha256='0' * 64)
        rows.append(row.model_copy(update={'target_capture_sha256': row.derived_target(capture).sha256}))
    catalog = catalog.model_copy(update={'entries': (catalog.entries[0], *rows)})
    selection = SimpleNamespace(requested_work='clarify', target_resolution='ambiguous',
        original_capture=capture.model_dump(mode='json', by_alias=True),
        placement_catalog=catalog.model_dump(mode='json', by_alias=True),
        compatible_placement_selectors=('place1', 'place2'))
    assert clarification_question(selection) == (
        'Several locations fit. Which section or paragraph do you mean? You can select the intended text.')


def two_native_locations(capture):
    from tests.application_state.test_plan_placement import native_paragraph_placement_fixture
    original, catalog = native_paragraph_placement_fixture(capture)
    nodes = json.loads(original.editor_json)['content']
    other = next(i for i, node in enumerate(nodes) if node['type'] == 'paragraph' and i != 2)
    def size(node):
        return (len(node.get('text', '').encode('utf-16-le')) // 2 if node['type'] == 'text'
            else 2 + sum(size(child) for child in node.get('content', [])))
    position = sum(size(node) for node in nodes[:other + 1])
    entry = PlanPlacementOptionV2(selector='place2', kind='after_paragraph',
        label=paragraph_placement_label(nodes, other, 'after_paragraph'), source_root_index=other,
        root_boundary=other + 1, position=position, target_capture_sha256='0' * 64)
    entry = entry.model_copy(update={'target_capture_sha256': entry.derived_target(original).sha256})
    return original, catalog.model_copy(update={'entries': (*catalog.entries, entry)})


@pytest.mark.parametrize('routing', ['write', 'clarify', 'discuss'])
def test_contextual_completion_binds_sdk_final_instead_of_aggregate_commentary(
    plan_adapter, tmp_path, monkeypatch, application_state_dsn, routing,
):
    from tests.test_plan_jev_writer import WriterWire, phase_message
    from tests.test_plan_jev_authoring import _shared_plan_authoring_case
    from tests.application_state.test_plan_placement import native_paragraph_placement_fixture
    original = WriterWire.handle_async_request

    async def phased(writer, request):
        writer.phase = 'final_answer'
        writer.extra_output = (phase_message('commentary', '{"unvalidated":"commentary"}<fim_suffix>'),)
        return await original(writer, request)

    monkeypatch.setattr(WriterWire, 'handle_async_request', phased)
    result = _shared_plan_authoring_case(plan_adapter, tmp_path, monkeypatch, 'place1', 'base',
        routing=None if routing == 'write' else routing, dsn=application_state_dsn,
        placement_factory=native_paragraph_placement_fixture)
    if result is not None and result.plan_proposal is not None:
        assert '<fim_suffix>' not in result.plan_proposal.replacement_markdown


def test_actual_model_multiple_nominations_clarify_without_reservation_or_factual_answer(
    plan_adapter, tmp_path, monkeypatch, application_state_dsn,
):
    import psycopg
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.native_execution import NativePlanOpeningSelectedV2
    from application_state.agent_conversation.plan_contextual_questions import decode_question, output_format
    from tests.test_plan_jev_authoring import _shared_plan_authoring_case

    _shared_plan_authoring_case(plan_adapter, tmp_path, monkeypatch, 'place1', 'base', routing='clarify',
        dsn=application_state_dsn, placement_factory=two_native_locations,
        semantic_intent='write_current_page', semantic_compatible=('place1', 'place2'))
    service = AgentConversationService()
    pointer = service.get_world_pointer('world:one')
    turn = service.list_turns('world:one', pointer.active_conversation_id)[-1]
    selection = next(e for e in turn.graph_context_execution.events if type(e) is NativePlanOpeningSelectedV2)
    assert selection.requested_intent == 'write_current_page'
    assert selection.requested_work == 'clarify' and selection.target_resolution == 'ambiguous'
    assert selection.compatible_placement_selectors == ('place1', 'place2')
    assert selection.placement_selector is None and selection.target_capture_sha256 is None
    for fields in ({'target_resolution': 'unique'}, {'requested_work': 'write_current_page'},
                   {'compatible_placement_selectors': ('place1',)},
                   {'compatible_placement_selectors': ('foreign',)},
                   {'requested_placement_relation': 'before_paragraph'},
                   {'compatible_anchor_selectors': ('anchor0',)}):
        with pytest.raises(ValueError):
            NativePlanOpeningSelectedV2.model_validate(selection.model_dump() | fields)
    expected = output_format(turn.graph_context_execution)['schema']['properties']['question']['enum'][0]
    assert turn.completion.answer_segments[0].text == expected
    assert len(turn.completion.answer_segments) == 1
    assert decode_question({'question': expected}, turn.graph_context_execution) == expected
    for invalid in ({'question': 'Quoted alternatives without a question'}, {'question': ''},
                    {'answer_segments': [{'text': 'An excerpt'}]}):
        with pytest.raises(ValueError):
            decode_question(invalid, turn.graph_context_execution)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM plan_action.action').fetchone()[0] == 0
