from uuid import uuid4
from types import SimpleNamespace

import pytest

from application_state.errors import ApplicationStateUnavailableError
from apps.live_control_server.services.guest_release_preparation import ReleaseSelection, prepare
from apps.live_control_server.services import guest_release_preparation as assembly


def test_preparation_fails_closed_until_native_release_path_is_qualified():
    selection = ReleaseSelection(graph_revision='revision', node_ids=[], relationships=[], sources=[], asset_ids=[])
    with pytest.raises(ApplicationStateUnavailableError):
        prepare(world_id='world', subject='owner', selection=selection)


def test_experimental_assembly_passes_sanitized_bytes_and_verified_bindings(monkeypatch):
    monkeypatch.setattr(assembly.guest_release, "owner_generation", lambda **_: 4)
    monkeypatch.setattr(assembly, "read_player_graph", lambda **_: (SimpleNamespace(native_world_id="native", binding_version=2), "graph", "access"))
    excerpt_id, asset_id, doc_id = uuid4(), uuid4(), uuid4()
    source_binding = (excerpt_id, doc_id, 0, 0, 1, "a" * 64, 0, 4, 3)
    monkeypatch.setattr(assembly, "selected_page_excerpt", lambda **_: ({"id": str(excerpt_id), "text": "safe"}, source_binding))
    seen = {}
    monkeypatch.setattr(assembly, "project_selected_graph", lambda *a, **k: seen.update(k) or {"nodes": [], "edges": []})
    monkeypatch.setattr(assembly.media, "read_staged_bytes", lambda *a: b"original")
    monkeypatch.setattr(assembly, "sanitize_release_image", lambda _: ("image/png", b"sanitized"))
    monkeypatch.setattr(assembly.guest_release, "stage", lambda **k: seen.update(staged=k) or (uuid4(), "digest"))
    selection = assembly.ReleaseSelection(graph_revision="revision", node_ids=["node"],
        relationships=[assembly.RelationshipSelection(edge_id="edge", evidence_id="evidence", source_index=0)],
        sources=[assembly.SourceSelection(document_id=doc_id, revision_n=1, sha256="a" * 64, start=0, end=4, excerpt="safe")],
        asset_ids=[asset_id])
    assembly._prepare_candidate(world_id="world", subject="owner", selection=selection)
    assert seen["citation_selections"]["edge"][2] == source_binding
    assert seen["staged"]["assets"][0][2] == b"sanitized"
    assert str(asset_id) not in str(seen["staged"]["manifest"])
    assert seen["staged"]["expected_owner_generation"] == 4
