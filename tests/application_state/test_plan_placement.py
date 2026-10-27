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
