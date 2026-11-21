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


def composed_snapshot(*, selected=False, wrong_slot=False, source=None):
    from application_state.agent_conversation.plan_authoring import PlanAuthoringComposedSnapshotV1
    from tests.application_state.test_plan_authoring_review import ENDING, LEFT, RIGHT, composed_plan

    markdown, layout, editor = source or composed_plan([LEFT], [RIGHT], ENDING)
    start = len(LEFT[1]) + 7 if selected else 1
    end = start + len(RIGHT[1]) if selected else start
    selection = json.dumps({"type": "text", "anchor": start, "head": end})
    slot = None if not selected else {
        "row_index": 0, "row_id": "row", "slot_index": 0 if wrong_slot else 1,
        "slot_id": "left" if wrong_slot else "right", "child_index": 0,
        "block_id": "left-block" if wrong_slot else "right-block",
    }
    return PlanAuthoringComposedSnapshotV1.model_validate(capture_payload() | {
        "schema": "dmb_plan_authoring_composed_snapshot_v1",
        "target_kind": "offer_slot_placement", "editor_json": editor, "editor_sha256": text_digest(editor),
        "draft_markdown": markdown, "draft_sha256": text_digest(markdown),
        "base_page_presentation_sha256": layout.fingerprint(),
        "draft_page_presentation": layout, "draft_page_presentation_sha256": layout.fingerprint(),
        "selection_json": selection, "selection_sha256": text_digest(selection),
        "from": start, "to": end, "selection_witness_text": RIGHT[1] if selected else "",
        "selected_paragraph": slot,
    })


def test_composed_catalog_keeps_identical_paragraph_occurrences_separate():
    from application_state.agent_conversation.plan_composed_targeting import (
        ComposedPlanNominationV1, ComposedPlanPlacementCatalogV1, resolve_composed_plan_nomination,
    )

    snapshot = composed_snapshot()
    catalog = ComposedPlanPlacementCatalogV1.freeze(snapshot)
    assert len(catalog.paragraphs) == 2
    assert catalog.paragraphs[0].text == catalog.paragraphs[1].text
    assert [row.column for row in catalog.paragraphs] == ["left column", "right column"]
    unscoped = ComposedPlanNominationV1(confirmed_work="write_current_page", relation="after",
        scope="unscoped", passages=("passage0",), scopes=("location1",))
    baseline = resolve_composed_plan_nomination(snapshot, catalog, "write_current_page", unscoped)
    assert (baseline.work, baseline.resolution, baseline.capture) == ("clarify", "ambiguous", None)
    qualified = ComposedPlanNominationV1(confirmed_work="write_current_page", relation="before", scope="qualified",
        passages=("passage0",), scopes=("location1",))
    outcome = resolve_composed_plan_nomination(snapshot, catalog, "write_current_page", qualified)
    assert outcome.capture.slot_address.model_dump() == {
        "row_index": 0, "row_id": "row", "slot_index": 1, "slot_id": "right",
        "child_index": 0, "block_id": "right-block", "relation": "before",
    }
    assert outcome.capture.draft_page_presentation == snapshot.draft_page_presentation
    assert outcome.capture.selection_json == snapshot.selection_json
    for author_intent in ("discuss", "clarify", "different_destination"):
        safe = resolve_composed_plan_nomination(snapshot, catalog, author_intent, qualified)
        assert (safe.work, safe.capture) == (author_intent, None)
    conflicting = qualified.model_copy(update={"confirmed_work": "discuss"})
    declined = resolve_composed_plan_nomination(snapshot, catalog, "write_current_page", conflicting)
    assert (declined.work, declined.resolution, declined.capture) == ("clarify", "unresolved", None)
    with pytest.raises(ValueError, match="complete frozen editor"):
        resolve_composed_plan_nomination(snapshot, catalog.model_copy(update={"paragraphs": catalog.paragraphs[1:]}),
            "write_current_page", qualified)


def test_composed_explicit_selection_requires_exact_text_in_the_addressed_slot():
    from application_state.agent_conversation.plan_composed_targeting import (
        ComposedPlanNominationV1, ComposedPlanPlacementCatalogV1, resolve_composed_plan_nomination,
    )

    nomination = ComposedPlanNominationV1(confirmed_work="write_current_page", relation="after", scope="selected_paragraph")
    plain = composed_snapshot()
    missing = resolve_composed_plan_nomination(plain, ComposedPlanPlacementCatalogV1.freeze(plain),
        "write_current_page", nomination)
    assert (missing.work, missing.resolution, missing.capture) == ("clarify", "missing", None)
    snapshot = composed_snapshot(selected=True)
    selected = resolve_composed_plan_nomination(snapshot, ComposedPlanPlacementCatalogV1.freeze(snapshot),
        "write_current_page", nomination)
    assert selected.capture.slot_address.slot_id == "right"
    assert selected.capture.slot_address.relation == "after"
    assert selected.capture.from_ == snapshot.from_
    with pytest.raises(ValueError, match="selected text does not match"):
        composed_snapshot(selected=True, wrong_slot=True)


def test_composed_nomination_offers_semantics_and_never_host_metadata():
    from application_state.agent_conversation.plan_authoring import PlanRequestedWorkInputV1
    from application_state.agent_conversation.plan_composed_targeting import (
        ComposedPlanPlacementCatalogV1, prepare_composed_plan_nomination,
    )

    snapshot = composed_snapshot(selected=True)
    catalog = ComposedPlanPlacementCatalogV1.freeze(snapshot)
    author = PlanRequestedWorkInputV1(
        request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256="f" * 64,
        question="Add a short warning after the gate in the right column.",
        page_title="Preparation notes", target_available=False,
    )
    prepared = prepare_composed_plan_nomination(author, snapshot, catalog)
    assert [location["description"] for location in prepared.state["locations"]] == [
        "left column of the first row on the page",
        "right column of the first row on the page",
    ]
    assert all(location["row_under_page_heading"] == "first row" for location in prepared.state["locations"])
    assert prepared.state["explicitly_selected_text"] == "The gate is locked."
    rendered = json.dumps(prepared.state) + "\n" + "\n".join(q.question for q in prepared.questions)
    for protected in (
        snapshot.world_id, snapshot.document_id, str(snapshot.conversation_id), str(snapshot.idempotency_key),
        snapshot.sha256, snapshot.editor_sha256, snapshot.draft_page_presentation_sha256, "left-block",
        "right-block", "row_index", "slot_index", "child_index", "selection_json", "byte_start",
    ):
        assert protected not in rendered


def test_composed_later_row_keeps_page_and_slot_headings_distinct():
    from application_state.agent_conversation.plan_authoring import PlanRequestedWorkInputV1
    from application_state.agent_conversation.plan_composed_targeting import (
        ComposedPlanPlacementCatalogV1, prepare_composed_plan_nomination,
    )
    from application_state.content.markdown_source_blocks import source_block_spans
    from application_state.content.page_presentation import PagePresentation
    from tests.application_state.test_plan_authoring_review import LEFT, RIGHT, composed_plan

    heading = ("page-heading", "## Arrival")
    slot_heading = ("slot-heading", "## Local desk")
    passage = ("later-note", "Keep the shutters closed.")
    other = ("later-right-note", "Keep one lantern ready.")
    ending = ("later-ending", "Unrelated ending.")
    _, first, first_editor = composed_plan([LEFT], [RIGHT], heading)
    _, second, second_editor = composed_plan([slot_heading, passage], [other], ending)
    blocks = [heading, LEFT, RIGHT, slot_heading, passage, other, ending]
    markdown = "\n\n".join(text for _, text in blocks) + "\n"
    raw = markdown.encode("utf-8")
    bindings = {
        identity: dict(kind="block", id=identity, byte_start=start, byte_end=end,
            sha256=text_digest(raw[start:end].decode("utf-8")))
        for (identity, _), (start, end) in zip(blocks, source_block_spans(markdown), strict=True)
    }
    rows = []
    editor_rows = []
    for index, (layout, raw_editor) in enumerate(((first, first_editor), (second, second_editor))):
        row = layout.items[0].model_dump(mode="python")
        node = json.loads(raw_editor)["content"][0]
        row["id"] = node["attrs"]["id"] = f"host-row-{index}"
        for slot, slot_node in zip(row["slots"], node["content"], strict=True):
            slot["id"] = slot_node["attrs"]["id"] = f"{slot['id']}-{index}"
            slot["blocks"] = [bindings[block["id"]] for block in slot["blocks"]]
        rows.append(row)
        editor_rows.append(node)
    layout = PagePresentation.model_validate({
        "markdown_sha256": text_digest(markdown), "items": [bindings[heading[0]], *rows, bindings[ending[0]]],
    })
    editor_json = json.dumps({"type": "doc", "content": [
        json.loads(first_editor)["content"][-1], *editor_rows, json.loads(second_editor)["content"][-1],
    ]})
    snapshot = composed_snapshot(source=(markdown, layout, editor_json))
    catalog = ComposedPlanPlacementCatalogV1.freeze(snapshot)
    author = PlanRequestedWorkInputV1(request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256="0" * 64,
        question="Add a warning next to the Local desk note.", page_title="Preparation", target_available=False)
    locations = prepare_composed_plan_nomination(author, snapshot, catalog).state["locations"]
    desk = next(row for row in locations if row["containing_headings"] == ["Arrival", "Local desk"])
    assert desk["page_headings"] == ["Arrival"]
    assert desk["description"] == "left column of the second row on the page"
    assert desk["row_under_page_heading"] == "second row"


@pytest.mark.parametrize("selected", [False, True])
def test_bound_selected_rewrite_requires_an_actual_selection(selected):
    from types import SimpleNamespace
    from application_state.agent_conversation.native_plan_opening import NativePlanAuthorScopeObservationV1
    from application_state.agent_conversation.plan_author_location import UnscopedLocation
    from application_state.agent_conversation.plan_contextual_targets import target_questions

    capture, catalog = captured_catalog(selected=selected)
    observation = NativePlanAuthorScopeObservationV1(
        relation="replace_explicit_selection", selected_alias="none", scope=UnscopedLocation())
    request = SimpleNamespace(original_capture=capture, placement_catalog=catalog,
        author_scope_binding=SimpleNamespace(observation=observation), page_title="A page",
        question="Could you rewrite this selected paragraph to add a warning?")
    answers = {question.name: question.options[0] for question in target_questions(request)}
    answers["placement_relation"] = "captured"
    answers["anchor_0"] = "include"
    assert compatible_selectors(request, answers) == (("captured",) if selected else ())


def family_catalog(nodes, *, with_headings=False):
    """Occurrence geometry fixture; production compiler parity is checked separately."""
    def size(node):
        if node['type'] == 'text':
            return len(node['text'].encode('utf-16-le')) // 2
        if node['type'] == 'hardBreak':
            return 1
        return 2 + sum(size(child) for child in node.get('content', []))
    editor = json.dumps(dict(type='doc', content=nodes), separators=(',', ':'))
    selection = json.dumps(dict(type='text', anchor=1, head=1), separators=(',', ':'))
    markdown = '\n\n'.join(''.join(child.get('text', '') for child in node.get('content', [])) for node in nodes)
    capture = PlanAuthoringCaptureV1.model_validate(capture_payload() | dict(
        editor_json=editor, editor_sha256=text_digest(editor), selection_json=selection,
        selection_sha256=text_digest(selection), draft_markdown=markdown, draft_sha256=text_digest(markdown),
        target_kind='insert_at_caret', selected_text='', **{'from': 1, 'to': 1}))
    entries = [PlanPlacementOptionV2(selector='captured', kind='captured_target', label='At the captured text caret',
        source_root_index=None, root_boundary=None, position=None, target_capture_sha256=capture.sha256)]
    if with_headings:
        from application_state.agent_conversation.plan_placement import _placement_headings
        for source in _placement_headings(nodes):
            boundary = source['index'] + 1
            row = PlanPlacementOptionV2(selector=f'place{len(entries)}', kind='after_heading',
                label=f"Directly below the heading {source['label']}, before its existing body",
                source_root_index=source['index'], root_boundary=boundary,
                position=sum(size(n) for n in nodes[:boundary]), target_capture_sha256='0' * 64)
            entries.append(row.model_copy(update={'target_capture_sha256': row.derived_target(capture).sha256}))
    for index, node in enumerate(nodes):
        if node['type'] != 'paragraph':
            continue
        for kind, boundary in [('before_paragraph', index), ('after_paragraph', index + 1)]:
            row = PlanPlacementOptionV2(selector=f'place{len(entries)}', kind=kind,
                label=paragraph_placement_label(nodes, index, kind), source_root_index=index,
                root_boundary=boundary, position=sum(size(n) for n in nodes[:boundary]), target_capture_sha256='0' * 64)
            entries.append(row.model_copy(update={'target_capture_sha256': row.derived_target(capture).sha256}))
    catalog = PlanPlacementCatalogV2(original_capture_sha256=capture.sha256,
        editor_sha256=capture.editor_sha256, entries=tuple(entries))
    catalog.require_original(capture)
    return capture, catalog


def prose(text):
    return dict(type='paragraph', content=[dict(type='text', text=text)])


def heading(text, level=2):
    return dict(type='heading', attrs=dict(level=level), content=[dict(type='text', text=text)])


def component_result(capture, catalog, *, scope='unscoped', path=None, relation='after_paragraph'):
    from application_state.agent_conversation.plan_contextual_targets import component_inventory, resolve_component_targets
    inventory = component_inventory(capture, catalog)
    sections = tuple(entry['view']['selector'] for entry in inventory['sections']
        if entry['view']['title'] in {p[-1] for p in (path or [])})
    parents = [p[:-1] for p in (path or []) if len(p) > 1]
    ancestors = tuple(entry['view']['selector'] for entry in inventory['ancestors']
        if entry['view']['heading_path'] in parents)
    return resolve_component_targets(capture, catalog, 'write_current_page', relation, scope, (),
        (inventory['passages'][0]['view']['selector'],), sections,
        'named' if parents else 'none', ancestors)


@pytest.mark.parametrize('path, relation, result, boundary', [
    ('Mill / Equipment', 'after_paragraph', 'missing', None),
    ('Atrium / Equipment', 'after_paragraph', 'unique', 3),
    ('Equipment', 'after_paragraph', 'ambiguous', None),
    ('Atrium / Equipment', 'before_paragraph', 'missing', None),
])
def test_author_scope_placement_joins_complete_path_and_agreed_relation(path, relation, result, boundary):
    from application_state.agent_conversation.native_plan_opening import NativePlanAuthorScopeObservationV1
    from application_state.agent_conversation.plan_author_location import literal_reference
    from application_state.agent_conversation.plan_contextual_targets import (
        component_inventory, resolve_author_scope_targets,
    )

    capture, catalog = family_catalog([heading('Atrium', 1), heading('Equipment'), prose('Shared.'),
        heading('Loft', 1), heading('Equipment'), prose('Shared.')])
    inventory = component_inventory(capture, catalog)
    observation = NativePlanAuthorScopeObservationV1(relation='after_paragraph', selected_alias='scope0',
        scope=literal_reference(path, path='/' in path))
    resolved = resolve_author_scope_targets(capture, catalog, 'write_current_page', relation,
        observation, (), (inventory['passages'][0]['view']['selector'],), document_title='Atrium')
    assert resolved['target_resolution'] == result
    if boundary is None:
        assert resolved['requested_work'] == 'clarify'
        assert resolved['target_capture_sha256'] is None
    else:
        assert resolved['requested_work'] == 'write_current_page'
        assert catalog.resolve(capture, resolved['placement_selector']).root_boundary == boundary


def test_described_scope_votes_join_only_the_nominated_heading_occurrence():
    from application_state.agent_conversation.native_plan_opening import (
        NativePlanAuthorScopeObservationV1, NativePlanOpeningInputV2, NativePlanOpeningScopeBindingV1,
    )
    from application_state.agent_conversation.plan_author_location import DescribedScopeName, NamedScopePath
    from application_state.agent_conversation.plan_contextual_targets import (
        contextual_work_choice, description_factors, prepare_contextual_work, target_answer_keys,
    )

    capture, catalog = family_catalog([heading('Workshop'), prose('Clay is fired.'), prose('Pack the tile.'),
        heading('Workshop'), prose('Wood is sawn.'), prose('Pack the tile.')])
    observation = NativePlanAuthorScopeObservationV1(relation='after_paragraph', selected_alias='scope0',
        scope=NamedScopePath(names=(DescribedScopeName(text='fired ceramics'),)))
    base_request = request_for(capture, catalog)
    fields = {name: getattr(base_request, name)
              for name in PlanRequestedWorkInputV9.model_fields if name != 'schema_'}
    fields.update(question='Add a warning after the tile step in the section about fired ceramics.',
        page_title='Workshop notes', author_scope_binding=NativePlanOpeningScopeBindingV1(
            observation_event_id=uuid4(), observation=observation))
    request = NativePlanOpeningInputV2.model_construct(**fields)
    descriptions, headings = description_factors(request)
    assert descriptions == {'description_positive_0': 'fired ceramics'}
    assert headings == [
        {'selector': 'heading0', 'path': ['Workshop'], 'passages': ['Clay is fired.', 'Pack the tile.']},
        {'selector': 'heading1', 'path': ['Workshop'], 'passages': ['Wood is sawn.', 'Pack the tile.']},
    ]
    prepared = prepare_contextual_work(request)
    questions = prepared.questions[1:]
    assert {question.name for question in questions} == target_answer_keys(request)
    answers = {question.name: question.options[-1] for question in questions}
    answers.update(placement_relation='after_paragraph', paragraph_scope='named', scope_qualifier='none',
        passage_1='include', description_positive_0_heading0='include')
    result = contextual_work_choice(request, 'write_current_page', answers)
    assert result['scope_description_matches'] == {0: ('heading0',)}
    assert catalog.resolve(capture, result['placement_selector']).root_boundary == 3
    unresolved_scope = contextual_work_choice(request, 'write_current_page', answers | {'paragraph_scope': 'unresolved'})
    assert unresolved_scope['requested_work'] == 'clarify'
    assert unresolved_scope['target_capture_sha256'] is None
    answers['description_positive_0_heading1'] = 'include'
    assert contextual_work_choice(request, 'write_current_page', answers)['target_resolution'] == 'ambiguous'
    del answers['description_positive_0_heading0']
    with pytest.raises(ValueError, match='Incomplete or foreign'):
        contextual_work_choice(request, 'write_current_page', answers)


@pytest.mark.parametrize('scope', ['either Records or Dispatch', 'both Records and Dispatch', 'A / B / C / D / E / F / G'])
def test_explicit_unsupported_scope_cannot_be_dropped_by_agreeing_models(scope):
    from types import SimpleNamespace
    from application_state.agent_conversation.native_plan_opening import NativePlanAuthorScopeObservationV1
    from application_state.agent_conversation.plan_author_location import UnscopedLocation
    from application_state.agent_conversation.plan_contextual_targets import (
        clarification_question, contextual_work_choice, target_questions,
    )

    capture, catalog = captured_catalog()
    observation = NativePlanAuthorScopeObservationV1(
        relation='after_paragraph', selected_alias='none', scope=UnscopedLocation())
    request = SimpleNamespace(question=f'Add a warning after the Alpha paragraph in {scope}.',
        original_capture=capture, placement_catalog=catalog, page_title='Notes',
        author_scope_binding=SimpleNamespace(observation=observation))
    answers = {question.name: question.options[-1] for question in target_questions(request)}
    answers.update(placement_relation='after_paragraph', paragraph_scope='unscoped',
        scope_qualifier='none', passage_0='include')
    resolved = contextual_work_choice(request, 'write_current_page', answers)
    assert resolved['requested_work'] == 'clarify'
    assert resolved['target_capture_sha256'] is None
    assert resolved['requested_placement_relation'] == 'after_paragraph'
    assert resolved['requested_paragraph_scope'] == 'unresolved'
    assert clarification_question(SimpleNamespace(**resolved)) == (
        'Could you select the intended paragraph, or name one unambiguous section path for it?')


def test_explicit_paragraph_locator_requires_direct_passage_nomination():
    from types import SimpleNamespace
    from application_state.agent_conversation.native_plan_opening import NativePlanAuthorScopeObservationV1
    from application_state.agent_conversation.plan_author_location import literal_reference
    from application_state.agent_conversation.plan_contextual_targets import (
        contextual_work_choice, paragraph_locator, target_questions,
    )

    capture, catalog = family_catalog([heading('Preparation'), prose('The gate is locked.'),
        prose('Pack two lanterns.')])
    observation = NativePlanAuthorScopeObservationV1(relation='before_paragraph', selected_alias='scope0',
        scope=literal_reference('Preparation', path=False))
    request = SimpleNamespace(question='Add a warning before the Preparation paragraph about the locked gate.',
        original_capture=capture, placement_catalog=catalog, page_title='Notes',
        author_scope_binding=SimpleNamespace(observation=observation))
    assert paragraph_locator(request) == 'the locked gate'
    answers = {question.name: question.options[-1] for question in target_questions(request)}
    answers.update(placement_relation='before_paragraph', paragraph_scope='named',
        scope_qualifier='none', passage_1='include')
    missing = contextual_work_choice(request, 'write_current_page', answers)
    assert missing['requested_work'] == 'clarify'
    assert not missing['locator_passage_selectors']
    matched = contextual_work_choice(request, 'write_current_page', answers | {'locator_passage_0': 'include'})
    assert matched['locator_passage_selectors'] != matched['compatible_passage_selectors']
    assert catalog.resolve(capture, matched['placement_selector']).root_boundary == 1


def test_quoted_locator_preserves_all_frozen_matching_occurrences_and_refuses_near_matches():
    from types import SimpleNamespace
    from application_state.agent_conversation.native_plan_opening import NativePlanAuthorScopeObservationV1
    from application_state.agent_conversation.plan_author_location import UnscopedLocation
    from application_state.agent_conversation.plan_contextual_targets import contextual_work_choice, target_questions

    capture, catalog = family_catalog([prose('Check the dial.'), prose('First, check the dial.'),
        prose('Before sunset, Check the dial. Then record the reading.')])
    observation = NativePlanAuthorScopeObservationV1(
        relation='after_paragraph', selected_alias='none', scope=UnscopedLocation())
    request = SimpleNamespace(question='After the paragraph containing “Check the dial.”, add a note.',
        original_capture=capture, placement_catalog=catalog, page_title='Notes',
        author_scope_binding=SimpleNamespace(observation=observation))
    answers = {question.name: question.options[-1] for question in target_questions(request)}
    answers.update(placement_relation='after_paragraph', paragraph_scope='unscoped', scope_qualifier='none',
        locator_passage_0='include')
    duplicate = contextual_work_choice(request, 'write_current_page', answers)
    assert duplicate['literal_paragraph_excerpt'] == 'Check the dial.'
    assert duplicate['target_resolution'] == 'ambiguous'
    assert len(duplicate['compatible_placement_selectors']) == 2
    wrong = contextual_work_choice(request, 'write_current_page',
        answers | {'locator_passage_0': 'exclude', 'locator_passage_1': 'include'})
    assert wrong['requested_work'] == 'clarify' and wrong['target_capture_sha256'] is None


def test_passage_families_expand_all_occurrences_before_named_scope_filters():
    capture, catalog = family_catalog([heading('Preparation'), prose('Shared.'), heading('Rumours'), prose('Shared.')])
    result = component_result(capture, catalog)
    assert result['target_resolution'] == 'ambiguous' and len(result['compatible_anchor_selectors']) == 2
    assert len(result['compatible_passage_selectors']) == 1
    result = component_result(capture, catalog, scope='named', path=[['Preparation']])
    assert result['requested_work'] == 'write_current_page'
    assert catalog.resolve(capture, result['placement_selector']).root_boundary == 2
    missing = component_result(capture, catalog, scope='named', path=[['Absent']])
    assert missing['target_resolution'] == 'missing' and missing['placement_selector'] is None


def test_duplicate_section_paths_expand_their_ranges_instead_of_picking_one():
    from application_state.agent_conversation.plan_contextual_targets import component_inventory
    capture, catalog = family_catalog([heading('Preparation'), prose('Shared.'), heading('Preparation'), prose('Shared.')])
    inventory = component_inventory(capture, catalog)
    assert len(inventory['sections']) == 1 and len(inventory['sections'][0]['anchors']) == 2
    result = component_result(capture, catalog, scope='named', path=[['Preparation']])
    assert result['requested_work'] == 'clarify' and result['target_resolution'] == 'ambiguous'


def test_direct_heading_occurrence_labels_remain_available_for_legacy_disambiguation():
    from application_state.agent_conversation.plan_contextual_targets import component_inventory, resolve_component_targets
    capture, catalog = family_catalog([heading('Preparation'), prose('One.'), heading('Preparation'), prose('Two.')], with_headings=True)
    headings = [entry for entry in component_inventory(capture, catalog)['direct'] if entry['view']['kind'] == 'heading']
    assert [entry['view']['label'] for entry in headings] == ['Preparation · 1 of 2', 'Preparation · 2 of 2']
    second = resolve_component_targets(capture, catalog, 'write_current_page', 'after_heading', 'not_applicable',
        (headings[1]['view']['selector'],), (), ())
    assert catalog.resolve(capture, second['placement_selector']).root_boundary == 3


def test_named_table_caption_is_not_promoted_to_a_paragraph_scope():
    from application_state.agent_conversation.plan_contextual_targets import component_inventory
    table = dict(type='table', content=[dict(type='tableRow', content=[dict(type='tableCell',
        attrs=dict(colspan=1, rowspan=1), content=[prose('Loot.')])])])
    capture, catalog = family_catalog([heading('Treasure'), table, prose('Shared.')])
    assert component_inventory(capture, catalog)['sections'] == []
    assert component_result(capture, catalog, scope='named')['requested_work'] == 'clarify'


def test_nested_scope_uses_complete_title_arrays_and_actual_containment():
    capture, catalog = family_catalog([heading('Chapter One', 1), heading('Preparation'), prose('Shared.'),
        heading('Reports'), prose('Shared.'), heading('Chapter Two', 1), heading('Preparation'), prose('Shared.')])
    assert component_result(capture, catalog, scope='named', path=[['Chapter One']])['target_resolution'] == 'ambiguous'
    child = component_result(capture, catalog, scope='named', path=[['Chapter One', 'Preparation']])
    assert child['requested_work'] == 'write_current_page'
    assert catalog.resolve(capture, child['placement_selector']).root_boundary == 3
    abbreviated = component_result(capture, catalog, scope='named',
        path=[['Chapter One', 'Preparation'], ['Chapter Two', 'Preparation']])
    assert abbreviated['target_resolution'] == 'ambiguous'
    unknown_child = component_result(capture, catalog, scope='named', path=[['Chapter One', 'Absent']])
    assert unknown_child['target_resolution'] == 'missing'


def test_primary_title_without_ancestor_expands_every_parent_and_duplicate_path():
    capture, catalog = family_catalog([heading('North', 1), heading('Supplies'), prose('Shared.'),
        heading('South', 1), heading('Supplies'), prose('Shared.'), heading('Supplies'), prose('Shared.')])
    all_parents = component_result(capture, catalog, scope='named', path=[['Supplies']])
    assert all_parents['target_resolution'] == 'ambiguous'
    assert len(all_parents['compatible_anchor_selectors']) == 3
    north = component_result(capture, catalog, scope='named', path=[['North', 'Supplies']])
    assert catalog.resolve(capture, north['placement_selector']).root_boundary == 3
    south = component_result(capture, catalog, scope='named', path=[['South', 'Supplies']])
    assert south['target_resolution'] == 'ambiguous'
    assert len(south['compatible_anchor_selectors']) == 2


def test_missing_ancestor_and_primary_cannot_drop_the_unsatisfied_constraint():
    capture, catalog = family_catalog([heading('Garden', 1), heading('Shed'), prose('Shared.')])
    for path in ([['Orchard', 'Shed']], [['Garden', 'Missing']]):
        result = component_result(capture, catalog, scope='named', path=path)
        assert result['requested_work'] == 'clarify' and result['target_resolution'] == 'missing'
        assert result['placement_selector'] is None and result['target_capture_sha256'] is None


def test_ancestor_join_uses_primary_occurrence_not_overlapping_paragraph_ranges():
    capture, catalog = family_catalog([heading('Archive', 1), heading('Other'), prose('Shared.')])
    # Other has Archive ancestry; Archive itself does not. Its broad range must
    # not borrow the descendant's ancestry merely because both contain Shared.
    impossible = component_result(capture, catalog, scope='named', path=[['Archive', 'Archive']])
    assert impossible['target_resolution'] == 'missing' and impossible['placement_selector'] is None
    same_named, same_catalog = family_catalog([heading('Archive', 1), heading('Archive'), prose('Shared.')])
    valid = component_result(same_named, same_catalog, scope='named', path=[['Archive', 'Archive']])
    assert valid['requested_work'] == 'write_current_page'
    assert same_catalog.resolve(same_named, valid['placement_selector']).root_boundary == 3


@pytest.mark.parametrize('relation,direct', [('captured', 'direct0'), ('after_heading', 'direct1')])
def test_nonparagraph_authority_ignores_but_retains_noisy_paragraph_factors(relation, direct):
    from application_state.agent_conversation.plan_contextual_targets import resolve_component_targets
    capture, catalog = family_catalog([heading('Only'), prose('Unique.')], with_headings=True)
    result = resolve_component_targets(capture, catalog, 'write_current_page', relation,
        'unresolved', (direct,), ('passage0',), ('section0',), 'unresolved')
    assert result['requested_work'] == 'write_current_page' and result['target_resolution'] == 'unique'
    assert result['compatible_passage_selectors'] == ('passage0',)
    assert result['compatible_section_selectors'] == ('section0',)
    assert result['requested_scope_qualifier'] == 'unresolved'
    target = catalog.resolve(capture, result['placement_selector'])
    if relation == 'captured':
        assert target.sha256 == capture.sha256
    else:
        assert target.root_boundary == 1


def test_delimiter_in_heading_title_does_not_merge_a_distinct_structured_path():
    from application_state.agent_conversation.plan_contextual_targets import component_inventory
    capture, catalog = family_catalog([heading('A / B', 1), prose('Shared.'), heading('A', 1), heading('B'), prose('Shared.')])
    inventory = component_inventory(capture, catalog)
    assert {'A / B', 'A', 'B'} == {entry['view']['title'] for entry in inventory['sections']}
    assert [entry['view']['heading_path'] for entry in inventory['ancestors']] == [['A']]
    result = component_result(capture, catalog, scope='named', path=[['A / B']])
    assert catalog.resolve(capture, result['placement_selector']).root_boundary == 2


def test_title_families_preserve_case_whitespace_and_structured_ancestor_paths():
    from application_state.agent_conversation.plan_contextual_targets import component_inventory
    capture, catalog = family_catalog([heading('Prep'), prose('Shared.'),
        heading(' Prep'), prose('Shared.'), heading('prep'), prose('Shared.')])
    assert [row['view']['title'] for row in component_inventory(capture, catalog)['sections']] == ['Prep', ' Prep', 'prep']
    nested, nested_catalog = family_catalog([heading('A / B', 1), heading('Target', 3), prose('Shared.'),
        heading('A', 1), heading('B', 2), heading('Target', 3), prose('Shared.')])
    paths = [row['view']['heading_path'] for row in component_inventory(nested, nested_catalog)['ancestors']]
    assert ['A / B'] in paths and ['A', 'B'] in paths
    literal = component_result(nested, nested_catalog, scope='named', path=[['A / B', 'Target']])
    assert nested_catalog.resolve(nested, literal['placement_selector']).root_boundary == 3
    hierarchy = component_result(nested, nested_catalog, scope='named', path=[['A', 'B', 'Target']])
    assert nested_catalog.resolve(nested, hierarchy['placement_selector']).root_boundary == 7


def test_root_prose_is_not_silently_included_by_a_named_section():
    capture, catalog = family_catalog([prose('Shared.'), heading('Later'), prose('Shared.')])
    assert component_result(capture, catalog)['target_resolution'] == 'ambiguous'
    named = component_result(capture, catalog, scope='named', path=[['Later']])
    assert catalog.resolve(capture, named['placement_selector']).root_boundary == 3
    root, root_catalog = family_catalog([prose('Root only.')])
    assert component_result(root, root_catalog)['requested_work'] == 'write_current_page'
    assert component_result(root, root_catalog, scope='named')['target_resolution'] == 'missing'


def test_equal_visible_text_keeps_inline_structure_and_every_capture_identity():
    from application_state.agent_conversation.plan_contextual_targets import component_inventory
    first = prose('Shared.')
    second = dict(type='paragraph', content=[dict(type='text', text='Shared.',
        marks=[dict(type='link', attrs=dict(href='https://example.test/source')), dict(type='bold')])])
    capture, catalog = family_catalog([first, second])
    before = capture.editor_json
    assert len(component_inventory(capture, catalog)['passages']) == 1
    result = component_result(capture, catalog)
    assert result['target_resolution'] == 'ambiguous' and len(result['compatible_placement_selectors']) == 2
    assert capture.editor_json == before
    a, b = (catalog.resolve(capture, key) for key in result['compatible_placement_selectors'])
    assert a.sha256 != b.sha256 and a.editor_json == b.editor_json == before


def test_passage_equality_preserves_case_whitespace_and_projected_hard_breaks():
    from application_state.agent_conversation.plan_contextual_targets import component_inventory
    split = dict(type='paragraph', content=[dict(type='text', text='A'), dict(type='hardBreak'), dict(type='text', text='B')])
    capture, catalog = family_catalog([prose('A\nB'), split, prose('a\nB'), prose(' A\nB')])
    passages = component_inventory(capture, catalog)['passages']
    assert [entry['view']['text'] for entry in passages] == ['A\nB', 'a\nB', ' A\nB']
    assert len(passages[0]['anchors']) == 2


def test_unresolved_scope_and_inconsistent_factors_cannot_acquire_a_target():
    from application_state.agent_conversation.plan_contextual_targets import resolve_component_targets
    capture, catalog = family_catalog([heading('Only'), prose('Unique.')])
    unresolved = component_result(capture, catalog, scope='unresolved', path=[['Only']])
    assert unresolved['requested_work'] == 'clarify' and unresolved['target_capture_sha256'] is None
    for relation, scope, direct, passages, sections in [
        ('after_paragraph', 'unscoped', (), ('passage0',), ('section0',)),
        ('after_paragraph', 'not_applicable', (), ('passage0',), ()),
        ('after_paragraph', 'unscoped', ('direct0',), ('passage0',), ()),
    ]:
        result = resolve_component_targets(capture, catalog, 'write_current_page', relation, scope, direct, passages, sections)
        assert result['requested_work'] == 'clarify' and result['target_capture_sha256'] is None
    for passages, sections in [(('passage0',), ('foreign',)), (('passage0', 'passage0'), ())]:
        with pytest.raises(ValueError):
            resolve_component_targets(capture, catalog, 'write_current_page', 'after_paragraph', 'named', (), passages, sections)


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


def test_capture_only_questions_cannot_offer_a_paragraph_scope():
    from application_state.agent_conversation.plan_contextual_targets import (
        contextual_work_choice, prepare_contextual_work, target_answer_keys)
    capture, catalog = captured_catalog(selected=True)
    request = request_for(capture, catalog)
    prepared = prepare_contextual_work(request)
    scope = next(q for q in prepared.questions if q.name == 'paragraph_scope')
    assert scope.options == ('not_applicable', 'unresolved')
    assert set(prepared.state['paragraph_scope_modes']) == {'not_applicable', 'unresolved'}
    answers = {key: 'exclude' for key in target_answer_keys(request)} | {
        'placement_relation': 'captured', 'paragraph_scope': 'not_applicable',
        'scope_qualifier': 'none', 'anchor_0': 'include'}
    resolved = contextual_work_choice(request, 'write_current_page', answers)
    assert resolved['target_capture_sha256'] == capture.sha256
    with pytest.raises(ValueError, match='scope was not offered'):
        contextual_work_choice(request, 'write_current_page', answers | {'paragraph_scope': 'unscoped'})


def test_location_votes_are_complete_and_model_view_contains_no_host_bindings():
    capture, catalog = captured_catalog()
    request = request_for(capture, catalog)
    from application_state.agent_conversation.plan_contextual_targets import target_answer_keys
    answers = {key: 'exclude' for key in target_answer_keys(request)} | {
        'placement_relation': 'after_paragraph', 'paragraph_scope': 'unscoped', 'scope_qualifier': 'none'}
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


@pytest.mark.parametrize('relation,anchors', [('unresolved', ('anchor1',)),
    ('after_paragraph', ('anchor1', 'anchor2'))])
def test_raw_content_clarification_is_not_overridden_by_host_target_question(relation, anchors):
    from types import SimpleNamespace
    from application_state.agent_conversation.plan_contextual_targets import clarification_question
    capture, catalog = captured_catalog()
    fields = resolve_anchor_targets(capture, catalog, 'clarify', relation, anchors)
    assert clarification_question(SimpleNamespace(**fields)) is None
    fields = resolve_anchor_targets(capture, catalog, 'write_current_page', relation, anchors)
    assert clarification_question(SimpleNamespace(**fields, original_capture=capture.model_dump(mode='json', by_alias=True),
        placement_catalog=catalog.model_dump(mode='json', by_alias=True)))


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
    selection = SimpleNamespace(requested_intent='write_current_page', requested_work='clarify', target_resolution='ambiguous',
        original_capture=capture.model_dump(mode='json', by_alias=True),
        placement_catalog=catalog.model_dump(mode='json', by_alias=True),
        compatible_placement_selectors=('place1', 'place2'))
    assert clarification_question(selection) == (
        'Several locations fit. Which section or paragraph do you mean? You can select the intended text.')


@pytest.mark.parametrize('duplicate', [False, True])
def test_conflicting_unscoped_votes_offer_only_multiple_question_alternatives(duplicate):
    from types import SimpleNamespace
    from application_state.agent_conversation.plan_contextual_targets import (
        clarification_question, resolve_component_targets,
    )
    capture, catalog = family_catalog([
        heading('Preparation'), prose('The gate is locked.'),
        heading('Rumours'), prose('The gate is locked.' if duplicate else 'Another passage.'),
    ])
    result = resolve_component_targets(capture, catalog, 'write_current_page',
        'after_paragraph', 'unscoped', (), ('passage0',), ('section0',))
    assert result['requested_work'] == 'clarify'
    assert result['target_resolution'] == 'missing'
    assert result['compatible_placement_selectors'] == ()
    assert result['placement_selector'] is None
    assert result['target_capture_sha256'] is None
    question = clarification_question(SimpleNamespace(**result,
        original_capture=capture.model_dump(mode='json', by_alias=True),
        placement_catalog=catalog.model_dump(mode='json', by_alias=True)))
    if duplicate:
        assert question.startswith('Which location do you mean: ')
        assert 'Preparation' in question and 'Rumours' in question
    else:
        assert 'couldn’t identify' in question


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
    from application_state.agent_conversation.native_plan_opening import validate_request_admission
    execution = turn.graph_context_execution
    assert execution.policy.action.document_title == 'Synthetic park Plan'
    assert validate_request_admission(turn.graph_context_receipt, execution)
    changed_action = execution.policy.action.model_copy(update={'document_title': 'Foreign title'})
    changed_policy = execution.policy.model_copy(update={'action': changed_action})
    with pytest.raises(ValueError, match='manifest differs'):
        validate_request_admission(turn.graph_context_receipt,
            execution.model_copy(update={'policy': changed_policy}))
    selection = next(e for e in turn.graph_context_execution.events if type(e) is NativePlanOpeningSelectedV2)
    assert selection.requested_intent == 'write_current_page'
    assert selection.requested_work == 'clarify' and selection.target_resolution == 'ambiguous'
    assert selection.compatible_placement_selectors == ('place1', 'place2')
    assert selection.placement_selector is None and selection.target_capture_sha256 is None
    for fields in ({'target_resolution': 'unique'}, {'requested_work': 'write_current_page'},
                   {'compatible_placement_selectors': ('place1',)},
                   {'compatible_placement_selectors': ('foreign',)},
                   {'requested_placement_relation': 'before_paragraph'},
                   {'compatible_anchor_selectors': ('anchor0',)},
                   {'requested_paragraph_scope': 'not_applicable'},
                   {'compatible_passage_selectors': ('foreign',)},
                   {'compatible_ancestor_selectors': ('foreign',)},
                   {'requested_scope_qualifier': 'unresolved'},
                   {'direct_anchor_selectors': ('direct0',)}):
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
