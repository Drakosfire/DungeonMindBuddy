from uuid import UUID, uuid4
from types import SimpleNamespace
from pathlib import Path
import json

import pytest

from application_state.errors import ApplicationStateUnavailableError
from application_state.errors import ApplicationStateValidationError
from application_state.guest_release_example import validate_example
from apps.live_control_server.services.guest_release_preparation import ReleaseSelection, prepare
from apps.live_control_server.services import guest_release_preparation as assembly


def test_preparation_fails_closed_until_native_release_path_is_qualified(monkeypatch):
    monkeypatch.delenv("DMB_GUEST_RELEASE_PREPARE_ENABLED", raising=False)
    selection = ReleaseSelection(graph_revision='revision', nodes=[], relationships=[], sources=[], asset_ids=[])
    with pytest.raises(ApplicationStateUnavailableError):
        prepare(world_id='world', subject='owner', selection=selection)


def test_experimental_assembly_passes_sanitized_bytes_and_verified_bindings(monkeypatch):
    monkeypatch.setattr(assembly.guest_release, "owner_generation", lambda **_: 4)
    monkeypatch.setattr(assembly, "read_owner_graph", lambda **_: (SimpleNamespace(native_world_id="native", binding_version=2), "context", SimpleNamespace(listing=SimpleNamespace(admitted_assertion_ids=[])), SimpleNamespace(parsed=SimpleNamespace(get_evidence=lambda _: SimpleNamespace(evidence_role="support")))))
    excerpt_id, asset_id, doc_id = uuid4(), uuid4(), uuid4()
    source_binding = (excerpt_id, doc_id, 0, 0, 1, "a" * 64, 0, 4, 3, "internal")
    monkeypatch.setattr(assembly, "selected_page_excerpt", lambda **_: ({"id": str(excerpt_id), "text": "safe"}, source_binding))
    monkeypatch.setattr(assembly, "verify_source_citation", lambda **_: str(excerpt_id))
    seen = {}
    monkeypatch.setattr(assembly, "select_node", lambda **k: (seen.update(node=k) or {"id": str(uuid4())}, ()))
    monkeypatch.setattr(assembly, "select_relationship", lambda **k: (seen.update(edge=k) or {}, ()))
    monkeypatch.setattr(assembly.media, "read_staged_bytes", lambda *a: b"original")
    monkeypatch.setattr(assembly, "sanitize_release_image", lambda _: ("image/png", b"sanitized"))
    monkeypatch.setattr(assembly.guest_release, "stage", lambda **k: seen.update(staged=k) or (uuid4(), "digest"))
    selection = assembly.ReleaseSelection(graph_revision="revision", nodes=[assembly.NodeSelection(entity_id="node", name_assertion_id="name", kind_assertion_id="kind", name_source_index=0, kind_source_index=0)],
        relationships=[assembly.RelationshipSelection(assertion_id="edge", subject_id="node", predicate="dnd5e:knows", evidence_id="evidence", source_index=0)],
        sources=[assembly.SourceSelection(document_id=doc_id, revision_n=1, sha256="a" * 64, start=0, end=4, excerpt="safe", evidence_id="evidence")],
        asset_ids=[asset_id])
    assembly._prepare_candidate(world_id="world", subject="owner", selection=selection)
    assert seen["edge"]["evidence"][2] == source_binding[:9]
    assert seen["node"]["name_evidence"][2] == source_binding[:9]
    assert seen["staged"]["assets"][0][2] == b"sanitized"
    assert str(asset_id) not in str(seen["staged"]["manifest"])
    assert seen["staged"]["expected_owner_generation"] == 4
    assert seen["staged"]["source_bindings"][0][-1] == "evidence"


def test_saved_example_closes_references_and_preserves_old_copies():
    first, second, asset, page = uuid4(), uuid4(), uuid4(), uuid4()
    bindings = [(first, page, 0, 0, 1, "a" * 64, 0, 4),
                (second, page, 0, 0, 1, "a" * 64, 5, 9)]
    manifest = {"sources": [{"id": str(first)}, {"id": str(second)}],
                "assets": [{"id": str(asset)}]}
    validate_example(manifest, bindings)  # Existing snapshots need no new field.
    example = {"version": "owner_saved_scene_v1", "title": "A scene", "body": "First line\nSecond line",
               "references": [str(first), str(second)], "image": {"id": str(asset), "description": "A red tent"}}
    manifest["saved_example"] = example
    validate_example(manifest, bindings)
    for changes in ({"references": [str(first), str(first)]}, {"references": [str(first), str(uuid4())]},
                    {"body": "Look at https://example.com"}, {"title": "\u202eevil"},
                    {"image": {"id": str(uuid4()), "description": "tent"}}, {"extra": "hidden"}):
        manifest["saved_example"] = {**example, **changes}
        with pytest.raises(ApplicationStateValidationError):
            validate_example(manifest, bindings)
    manifest["saved_example"] = example
    repeated_span = [bindings[0], (second, page, 0, 0, 1, "a" * 64, 0, 4)]
    with pytest.raises(ApplicationStateValidationError, match="distinct spans"):
        validate_example(manifest, repeated_span)


def test_preparation_localizes_saved_example_references_and_image(monkeypatch):
    monkeypatch.setattr(assembly.guest_release, "owner_generation", lambda **_: 1)
    access = SimpleNamespace(parsed=SimpleNamespace(get_evidence=lambda _: SimpleNamespace(evidence_role="context")))
    monkeypatch.setattr(assembly, "read_owner_graph", lambda **_: (SimpleNamespace(native_world_id="native", binding_version=1), None, SimpleNamespace(listing=SimpleNamespace(admitted_assertion_ids=[])), access))
    documents, image = [uuid4(), uuid4()], uuid4()
    local_excerpts = [uuid4(), uuid4()]
    def excerpt(**kwargs):
        index = documents.index(UUID(kwargs["document_id"]))
        return {"id": str(local_excerpts[index]), "text": "safe"}, (local_excerpts[index], documents[index], 0, 0, 1, "a" * 64, 0, 4, 1, "internal")
    monkeypatch.setattr(assembly, "selected_page_excerpt", excerpt)
    monkeypatch.setattr(assembly, "verify_source_citation", lambda **_: None)
    monkeypatch.setattr(assembly.media, "read_staged_bytes", lambda *args: b"raw")
    monkeypatch.setattr(assembly, "sanitize_release_image", lambda _: ("image/png", b"clean"))
    staged = {}
    monkeypatch.setattr(assembly.guest_release, "stage", lambda **kwargs: staged.update(kwargs) or (uuid4(), "digest"))
    sources = [assembly.SourceSelection(document_id=doc, revision_n=1, sha256="a" * 64, start=0, end=4, excerpt="safe", evidence_id=f"e{i}") for i, doc in enumerate(documents)]
    selection = assembly.ReleaseSelection(graph_revision="revision", nodes=[], relationships=[], sources=sources, asset_ids=[image],
        saved_example=assembly.SavedExampleSelection(title="Scene", body="A saved scene", source_indexes=[1, 0], asset_id=image, image_description="A tent"),
        saved_choice=assembly.SavedChoiceSelection(prompt="What next", options=[
            assembly.SavedChoiceOption(label="Enter", outcome="A bell rings"),
            assembly.SavedChoiceOption(label="Wait", outcome="A lantern flickers")]))
    assembly._prepare_candidate(world_id="world", subject="owner", selection=selection)
    example = staged["manifest"]["saved_example"]
    assert example["references"] == [str(local_excerpts[1]), str(local_excerpts[0])]
    assert example["image"]["id"] == staged["manifest"]["assets"][0]["id"] != str(image)
    assert all(str(doc) not in str(example) for doc in documents)
    assert staged["manifest"]["saved_choice"] == {"version": "owner_saved_choice_v1", "prompt": "What next",
        "options": [{"label": "Enter", "outcome": "A bell rings"}, {"label": "Wait", "outcome": "A lantern flickers"}]}
    validate_example(staged["manifest"], staged["source_bindings"])
    bad = selection.model_copy(update={"saved_example": selection.saved_example.model_copy(update={"asset_id": uuid4()})})
    with pytest.raises(assembly.GuestReleasePreparationError):
        assembly._prepare_candidate(world_id="world", subject="owner", selection=bad)
    missing_example = selection.model_copy(update={"saved_example": None})
    with pytest.raises(assembly.GuestReleasePreparationError, match="requires a saved example"):
        assembly._prepare_candidate(world_id="world", subject="owner", selection=missing_example)


def test_saved_choice_is_closed_bounded_and_requires_a_valid_example():
    first, second, page = uuid4(), uuid4(), uuid4()
    bindings = [(first, page, 0, 0, 1, "a" * 64, 0, 4), (second, page, 0, 0, 1, "a" * 64, 5, 9)]
    example = {"version": "owner_saved_scene_v1", "title": "Scene", "body": "A scene",
               "references": [str(first), str(second)], "image": None}
    choice = {"version": "owner_saved_choice_v1", "prompt": "What next", "options": [
        {"label": "Enter", "outcome": "A bell rings"}, {"label": "Wait", "outcome": "A lantern flickers"}]}
    manifest = {"saved_example": example, "saved_choice": choice, "assets": []}
    validate_example(manifest, bindings)
    invalid_choices = [None, {**choice, "version": "unknown"}, {**choice, "extra": "hidden"},
        {**choice, "prompt": "Look at https://example.com"}, {**choice, "options": choice["options"][:1]},
        {**choice, "options": [{"label": " Enter ", "outcome": "One"}, {"label": "enter", "outcome": "Two"}]},
        {**choice, "options": [{"label": "Enter", "outcome": "x" * 2001}, {"label": "Wait", "outcome": "Two"}]},
        {**choice, "options": [{"label": "Enter", "outcome": "\u202eevil"}, {"label": "Wait", "outcome": "Two"}]}]
    for invalid in invalid_choices:
        with pytest.raises(ApplicationStateValidationError):
            validate_example({**manifest, "saved_choice": invalid}, bindings)
    with pytest.raises(ApplicationStateValidationError, match="requires a saved example"):
        validate_example({"saved_choice": choice, "assets": []}, bindings)


def test_saved_choice_unicode_contract_matches_frontend_fixtures():
    cases = json.loads((Path(__file__).resolve().parents[1] / "apps/live-control-ui/src/guestRelease/savedChoiceParity.json").read_text())
    first, second, page = uuid4(), uuid4(), uuid4()
    bindings = [(first, page, 0, 0, 1, "a" * 64, 0, 4), (second, page, 0, 0, 1, "a" * 64, 5, 9)]
    example = {"version": "owner_saved_scene_v1", "title": "Scene", "body": "Scene", "references": [str(first), str(second)], "image": None}
    for case in cases:
        labels = case["labels"][:]
        labels[0] *= case.get("repeat", 1)
        choice = {"version": "owner_saved_choice_v1", "prompt": "What next", "options": [
            {"label": labels[0], "outcome": "One"}, {"label": labels[1], "outcome": "Two"}]}
        manifest = {"saved_example": example, "saved_choice": choice, "assets": []}
        if case["valid"]:
            validate_example(manifest, bindings)
        else:
            with pytest.raises(ApplicationStateValidationError):
                validate_example(manifest, bindings)
