from uuid import uuid4
from types import SimpleNamespace

import pytest

from application_state.errors import ApplicationStateUnavailableError
from apps.live_control_server.services.guest_release_preparation import ReleaseSelection, prepare
from apps.live_control_server.services import guest_release_preparation as assembly


def test_preparation_fails_closed_until_native_release_path_is_qualified(monkeypatch):
    monkeypatch.delenv("DMB_GUEST_RELEASE_PREPARE_ENABLED", raising=False)
    selection = ReleaseSelection(graph_revision='revision', nodes=[], relationships=[], sources=[], asset_ids=[])
    with pytest.raises(ApplicationStateUnavailableError):
        prepare(world_id='world', subject='owner', selection=selection)


def test_experimental_assembly_passes_sanitized_bytes_and_verified_bindings(monkeypatch):
    monkeypatch.setattr(assembly.guest_release, "owner_generation", lambda **_: 4)
    monkeypatch.setattr(assembly, "read_owner_graph", lambda **_: (SimpleNamespace(native_world_id="native", binding_version=2), "context", SimpleNamespace(listing=SimpleNamespace(admitted_assertion_ids=[])), "access"))
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
