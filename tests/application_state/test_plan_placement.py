"""Frozen placement membership is separate from browser-owned PM positions."""
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from tests.application_state.test_plan_authoring import capture_payload
from application_state.agent_conversation.plan_authoring import (
    PlanAuthoringCaptureV1, PlanAuthoringBoundaryCaptureV1, text_digest,
)
from application_state.agent_conversation.plan_placement import (
    PlanPlacementCatalogV1, PlanPlacementOptionV1,
)


def original_capture():
    payload = capture_payload()
    content = [
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Objective"}]},
        {"type": "paragraph", "content": [{"type": "text", "text": "Keep the alternatives open."}]},
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Beat"}]},
    ]
    editor = json.dumps({"type": "doc", "content": content}, separators=(",", ":"))
    payload.update(editor_json=editor, editor_sha256=text_digest(editor))
    return PlanAuthoringCaptureV1.model_validate(payload)


def catalog_for(original):
    captured = PlanPlacementOptionV1(selector="captured", kind="captured_target", label="Captured caret",
        root_boundary=None, position=None, target_capture_sha256=original.sha256)
    boundary = PlanPlacementOptionV1(selector="after:0", kind="after_section", label="After Objective",
        root_boundary=2, position=39, target_capture_sha256="0" * 64)
    boundary = boundary.model_copy(update={"target_capture_sha256": boundary.derived_target(original).sha256})
    return PlanPlacementCatalogV1(original_capture_sha256=original.sha256,
        editor_sha256=original.editor_sha256, entries=(captured, boundary))


def test_frozen_catalog_resolves_host_target_without_overwriting_original_caret():
    original = original_capture()
    catalog = catalog_for(original)
    resolved = catalog.resolve(original, "after:0")
    assert isinstance(resolved, PlanAuthoringBoundaryCaptureV1)
    assert resolved.target_kind == "insert_at_boundary"
    assert resolved.root_boundary == 2
    assert resolved.from_ == resolved.to == 39
    assert original.from_ == original.to == 14
    assert resolved.selection_json == original.selection_json
    assert resolved.editor_json == original.editor_json
    assert resolved.draft_markdown == original.draft_markdown
    assert catalog.resolve(original, "captured") == original
    assert catalog.sha256 != original.sha256 != resolved.sha256
    assert catalog.model_choices() == [
        {"selector": "captured", "label": "Captured caret"},
        {"selector": "after:0", "label": "After Objective"},
    ]


@pytest.mark.parametrize("field,value", [
    ("world_id", "foreign"), ("document_id", "other"), ("base_revision", 4),
    ("conversation_id", str(uuid4())), ("draft_generation", 9),
])
def test_catalog_cannot_transfer_to_another_original_owner_or_snapshot(field, value):
    original = original_capture()
    payload = original.model_dump(mode="json", by_alias=True)
    payload[field] = value
    changed = PlanAuthoringCaptureV1.model_validate(payload)
    with pytest.raises(ValueError, match="original captured page"):
        catalog_for(original).resolve(changed, "after:0")


@pytest.mark.parametrize("change", [
    {"position": 1}, {"root_boundary": 1}, {"target_capture_sha256": "f" * 64},
])
def test_catalog_rejects_substituted_target_not_only_foreign_selector(change):
    original = original_capture()
    payload = catalog_for(original).model_dump(mode="json", by_alias=True)
    payload["entries"][1].update(change)
    with pytest.raises(ValueError, match="offered digest"):
        PlanPlacementCatalogV1.model_validate(payload).resolve(original, "after:0")


def test_unknown_selector_and_duplicate_or_missing_original_are_refused():
    original = original_capture()
    catalog = catalog_for(original)
    with pytest.raises(ValueError, match="not offered"):
        catalog.resolve(original, "after:99")
    payload = catalog.model_dump(mode="json", by_alias=True)
    payload["entries"].append(payload["entries"][0])
    with pytest.raises(ValidationError, match="unique captured target"):
        PlanPlacementCatalogV1.model_validate(payload)
    payload["entries"] = payload["entries"][1:2]
    with pytest.raises(ValidationError, match="unique captured target"):
        PlanPlacementCatalogV1.model_validate(payload)


def test_boundary_capture_has_no_replacement_or_playable_authority():
    original = original_capture()
    boundary = catalog_for(original).resolve(original, "after:0")
    for change in ({"selected_text": "Replace me"}, {"to": 40}, {"root_boundary": 4}):
        payload = boundary.model_dump(mode="json", by_alias=True)
        payload.update(change)
        with pytest.raises(ValidationError):
            PlanAuthoringBoundaryCaptureV1.model_validate(payload)
    with pytest.raises(ValueError, match="original captured page"):
        catalog_for(original).require_original(boundary)


def test_boundary_catalog_cannot_broaden_exact_reverse_selection():
    payload = original_capture().model_dump(mode="json", by_alias=True)
    selection = '{"type":"text","anchor":8,"head":1}'
    payload.update(selection_json=selection, selection_sha256=text_digest(selection),
        target_kind="replace_selection", selected_text="Objecti", **{"from": 1, "to": 8})
    replacement = PlanAuthoringCaptureV1.model_validate(payload)
    source = catalog_for(original_capture()).model_dump(mode="json", by_alias=True)
    source.update(original_capture_sha256=replacement.sha256, editor_sha256=replacement.editor_sha256)
    with pytest.raises(ValueError, match="Replacement authority"):
        PlanPlacementCatalogV1.model_validate(source).require_original(replacement)


def test_retained_v1_capture_keeps_exact_old_digest_and_text_selection_rules():
    original = original_capture()
    assert PlanAuthoringCaptureV1.model_validate_json(original.model_dump_json(by_alias=True)).sha256 == original.sha256
    payload = original.model_dump(mode="json", by_alias=True)
    payload["from"] = payload["to"] = 39
    with pytest.raises(ValidationError, match="directional selection"):
        PlanAuthoringCaptureV1.model_validate(payload)


def test_current_intent_projection_preserves_frozen_v2_wire_and_location_choices():
    from pathlib import Path
    from hashlib import sha256
    from application_state.agent_conversation.plan_authoring import (
        CURRENT_REQUEST_INTENT_POLICY, prepare_requested_work_decision,
        validate_requested_work_wire, validate_prepared_requested_work,
    )
    from application_state.agent_conversation.plan_placement import (
        PlanRequestedWorkInputV2, PlanRequestedWorkInputV3,
    )
    frozen = json.loads((Path(__file__).parents[1] / "fixtures/plan_requested_work_v2_wire.json").read_text())
    raw = frozen["wire_json"].encode()
    assert sha256(raw).hexdigest() == frozen["wire_sha256"]
    old = PlanRequestedWorkInputV2.model_validate(frozen["parent"])
    validate_requested_work_wire(old, raw)
    current = PlanRequestedWorkInputV3.model_validate(frozen["parent"] | {"schema": "dmb_plan_requested_work_input_v3"})
    projected = prepare_requested_work_decision(current)
    wire = json.loads(raw)
    assert projected.state == wire["state"] | {"intent_policy": CURRENT_REQUEST_INTENT_POLICY}
    assert projected.questions[0].options == tuple(wire["questions"]["requested_work"]["criteria"])
    wire["state"] = projected.state
    current_raw = json.dumps(wire).encode()
    validate_requested_work_wire(current, current_raw)
    for parent, substituted in ((old, current_raw), (current, raw)):
        with pytest.raises(ValueError, match="wire differs"):
            validate_requested_work_wire(parent, substituted)
    with pytest.raises(ValueError, match="requires the V3"):
        validate_prepared_requested_work(old, None)


def under_heading_catalog(original, root_boundary=1):
    captured = catalog_for(original).entries[0]
    entry = PlanPlacementOptionV1(selector="under:0", kind="after_heading",
        label="Directly below the heading Objective, before its existing body",
        root_boundary=root_boundary, position=11, target_capture_sha256="0" * 64)
    entry = entry.model_copy(update={"target_capture_sha256": entry.derived_target(original).sha256})
    return PlanPlacementCatalogV1(original_capture_sha256=original.sha256,
        editor_sha256=original.editor_sha256, entries=(captured, entry))


def test_under_heading_resolves_inside_section_and_preserves_frozen_original():
    original = original_capture()
    catalog = under_heading_catalog(original)
    resolved = catalog.resolve(original, "under:0")
    assert resolved.root_boundary == 1
    assert resolved.from_ == resolved.to == 11
    assert resolved.editor_json == original.editor_json
    assert resolved.selection_json == original.selection_json
    assert original.from_ == original.to == 14
    assert catalog.resolve(original, "captured") == original
    assert PlanPlacementCatalogV1.model_validate_json(catalog.model_dump_json(by_alias=True)).sha256 == catalog.sha256


@pytest.mark.parametrize("root_boundary", [0, 2, 3])
def test_under_heading_cannot_substitute_before_or_after_whole_section_even_with_matching_digest(root_boundary):
    original = original_capture()
    with pytest.raises(ValueError, match="captured root heading"):
        under_heading_catalog(original, root_boundary).require_original(original)


@pytest.mark.parametrize("selector", ["after:0", "under:00", "under:-1", "under:1"])
def test_under_heading_rejects_wrong_selector_or_nonheading(selector):
    original = original_capture()
    payload = under_heading_catalog(original).model_dump(mode="json", by_alias=True)
    payload["entries"][1]["selector"] = selector
    with pytest.raises(ValueError):
        catalog = PlanPlacementCatalogV1.model_validate(payload)
        entry = catalog.entries[1]
        entry = entry.model_copy(update={"target_capture_sha256": entry.derived_target(original).sha256})
        catalog.model_copy(update={"entries": (catalog.entries[0], entry)}).require_original(original)


def test_under_heading_decision_exposes_exact_location_without_offsets_or_new_save_authority():
    from application_state.agent_conversation.plan_authoring import prepare_requested_work_decision
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV3, work_choice
    from pathlib import Path
    frozen = json.loads((Path(__file__).parents[1] / "fixtures/plan_requested_work_v2_wire.json").read_text())
    original = original_capture()
    catalog = under_heading_catalog(original)
    parent = frozen["parent"] | {"schema": "dmb_plan_requested_work_input_v3",
        "original_capture": original.model_dump(mode="json", by_alias=True),
        "target_capture_sha256": original.sha256,
        "placement_catalog": catalog.model_dump(mode="json", by_alias=True)}
    request = PlanRequestedWorkInputV3.model_validate(parent)
    decision = prepare_requested_work_decision(request)
    assert "write:under:0" in decision.questions[0].options
    assert "inside that section before its existing body" in decision.state["placement_policy"]
    assert all(set(row) == {"selector", "label"} for row in decision.state["offered_page_locations"])
    choice = work_choice(request, "write:under:0")
    assert choice["placement_selector"] == "under:0"
    assert choice["target_capture_sha256"] == catalog.resolve(original, "under:0").sha256


@pytest.mark.parametrize('operation',['discuss','write_current_page'])
def test_explicit_operation_restricts_actual_sdk_choices_and_rejects_wire_substitution(operation):
    from pathlib import Path
    from application_state.agent_conversation.plan_authoring import prepare_requested_work_decision, validate_requested_work_wire
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV5
    frozen=json.loads((Path(__file__).parents[1]/'fixtures/plan_requested_work_v2_wire.json').read_text())
    parent=PlanRequestedWorkInputV5.model_validate(frozen['parent'] | {
        'schema':'dmb_plan_requested_work_input_v5','plan_requested_operation':operation,'authored_references':None})
    prepared=prepare_requested_work_decision(parent)
    choices=prepared.questions[0].options
    if operation=='discuss':
        assert choices==('discuss','clarify')
    else:
        assert 'discuss' not in choices
        assert {'clarify','different_destination'} <= set(choices)
        assert any(choice.startswith('write:') for choice in choices)
    assert prepared.state['plan_requested_operation']==operation
    with pytest.raises(ValueError,match='wire differs'):
        validate_requested_work_wire(parent,frozen['wire_json'].encode())


@pytest.mark.parametrize("operation",[None,"discuss","write_current_page"])
@pytest.mark.parametrize("extent",["section","full_document"])
def test_current_plan_reference_wire_keeps_semantics_and_host_binding_separate(operation,extent):
    from pathlib import Path
    from application_state.agent_conversation.authored_graph_references import (
        AuthoredGraphReferenceV1, AuthoredSourceReferenceV1, AuthoredReferencesV2)
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV6, PlanRequestedWorkInputV5
    from application_state.agent_conversation.plan_authoring import prepare_requested_work_decision, validate_requested_work_wire
    shared=dict(managed_world_id="managed-world-SENTINEL",native_world_id="native-world-SENTINEL",binding_version=42)
    graph=AuthoredGraphReferenceV1(**shared,graph_revision="graph-revision-SENTINEL",node_id="node-SENTINEL",label="The Exchange")
    source=AuthoredSourceReferenceV1(**shared,knowledge_revision="knowledge-SENTINEL",source_artifact_id="source-SENTINEL",
        source_revision_id="source-revision-SENTINEL",evidence_ref_id="evidence-SENTINEL",content_sha256="e"*64,
        selection_kind=extent,section_id="f"*64 if extent=="section" else None,label="Session 20 recap")
    references=AuthoredReferencesV2(references=(graph,graph.model_copy(update={"node_id":"another-node-SENTINEL"}),source))
    frozen=json.loads((Path(__file__).parents[1]/"fixtures/plan_requested_work_v2_wire.json").read_text())
    values=frozen["parent"] | dict(schema="dmb_plan_requested_work_input_v6",plan_requested_operation=operation,
        authored_references=references.model_dump(mode="json",by_alias=True))
    parent=PlanRequestedWorkInputV6.model_validate(values)
    prepared=prepare_requested_work_decision(parent)
    assert prepared.state["author_selected_references"]==[
        {"kind":"graph_object","label":"The Exchange"},{"kind":"graph_object","label":"The Exchange"},
        {"kind":"source","label":"Session 20 recap","selection_kind":extent}]
    raw=json.dumps(dict(model=prepared.model,state=prepared.state,questions={
        q.name:dict(type="choice",instructions=q.question,criteria=dict.fromkeys(q.options)) for q in prepared.questions})).encode()
    assert b"SENTINEL" not in raw
    assert ("e"*64).encode() not in raw and ("f"*64).encode() not in raw
    validate_requested_work_wire(parent,raw)
    retained=PlanRequestedWorkInputV6.model_validate_json(parent.model_dump_json(by_alias=True))
    assert retained.authored_references==references
    # Identity is still committed by the parent although labels/semantic wire match.
    changed=parent.model_copy(update={"authored_references":references.model_copy(update={"references":(
        graph.model_copy(update={"graph_revision":"changed-host-pin"}),references.references[1],source)})})
    assert changed.digest!=parent.digest
    assert prepare_requested_work_decision(changed).state==prepared.state
    old=PlanRequestedWorkInputV5.model_validate(values | dict(schema="dmb_plan_requested_work_input_v5",plan_requested_operation=operation or "discuss"))
    assert prepare_requested_work_decision(old).state["author_selected_references"]==references.model_dump(mode="json",by_alias=True)
    with pytest.raises(ValueError,match="wire differs"):
        validate_requested_work_wire(old,raw)


@pytest.mark.parametrize("operation", [None, "discuss", "write_current_page"])
def test_intent_first_revision_preserves_old_wire_and_writing_options(operation):
    from pathlib import Path
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV6, PlanRequestedWorkInputV7
    from application_state.agent_conversation.plan_authoring import (
        CURRENT_REQUEST_INTENT_POLICY, QUESTION_FIRST_INTENT_POLICY,
        prepare_requested_work_decision, validate_requested_work_wire)

    frozen = json.loads((Path(__file__).parents[1] / "fixtures/plan_requested_work_v2_wire.json").read_text())
    values = frozen["parent"] | dict(schema="dmb_plan_requested_work_input_v6",
        authored_references=None, plan_requested_operation=operation)
    old = PlanRequestedWorkInputV6.model_validate(values)
    new = PlanRequestedWorkInputV7.model_validate(values | dict(schema="dmb_plan_requested_work_input_v7"))
    before, after = prepare_requested_work_decision(old), prepare_requested_work_decision(new)
    assert before.state["intent_policy"] == CURRENT_REQUEST_INTENT_POLICY
    assert after.state["intent_policy"] == QUESTION_FIRST_INTENT_POLICY
    assert before.questions == after.questions
    assert {k:v for k,v in before.state.items() if k not in {"intent_policy", "placement_policy"}} == {
        k:v for k,v in after.state.items() if k not in {"intent_policy", "placement_policy"}}
    for parent, prepared in [(old,before),(new,after)]:
        raw = json.dumps(dict(model=prepared.model,state=prepared.state,questions={
            q.name:dict(type="choice",instructions=q.question,criteria=dict.fromkeys(q.options))
            for q in prepared.questions})).encode()
        validate_requested_work_wire(parent,raw)
        other = new if parent is old else old
        with pytest.raises(ValueError,match="wire differs"):
            validate_requested_work_wire(other,raw)
    assert PlanRequestedWorkInputV7.model_validate_json(new.model_dump_json(by_alias=True)) == new


@pytest.mark.parametrize('operation',[None,'discuss','write_current_page'])
def test_connected_page_choice_is_explicit_and_cannot_override_interface_operation(operation):
    from pathlib import Path
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV7,PlanRequestedWorkInputV8,work_choice
    from application_state.agent_conversation.plan_authoring import prepare_requested_work_decision
    frozen=json.loads((Path(__file__).parents[1]/'fixtures/plan_requested_work_v2_wire.json').read_text())
    values=frozen['parent']|dict(schema='dmb_plan_requested_work_input_v8',authored_references=None,plan_requested_operation=operation)
    current=PlanRequestedWorkInputV8.model_validate(values)
    old=PlanRequestedWorkInputV7.model_validate(values|dict(schema='dmb_plan_requested_work_input_v7'))
    before,after=prepare_requested_work_decision(old),prepare_requested_work_decision(current)
    assert 'review_connected_page' not in before.questions[0].options
    assert ('review_connected_page' in after.questions[0].options)==(operation is None)
    assert set(after.questions[0].options)-{'review_connected_page'}==set(before.questions[0].options)
    assert PlanRequestedWorkInputV8.model_validate_json(current.model_dump_json(by_alias=True))==current
    with pytest.raises(ValueError):work_choice(old,'review_connected_page')
    if operation is not None:
        with pytest.raises(ValueError):work_choice(current,'review_connected_page')
    else:
        assert work_choice(current,'review_connected_page')==dict(requested_work='review_connected_page',placement_selector=None,target_capture_sha256=None)
