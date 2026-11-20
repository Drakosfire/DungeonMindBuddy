from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.live_control_server.services import guest_release_validation as validation


def test_validation_rechecks_exact_graph_and_citation(monkeypatch):
    release_id, local_node, local_edge, excerpt_id = (uuid4() for _ in range(4))
    source_binding = (excerpt_id, uuid4(), 0, 0, 1, "a" * 64, 0, 4, 2)
    material = {"native_world_id": "native", "binding_version": 3, "graph_revision": "rev",
        "manifest": {"nodes": [], "graph": {"nodes": [{"id": str(local_node), "label": "Node", "kind": "npc"}],
                    "edges": [{"id": str(local_edge), "source": str(local_node), "target": str(local_node),
                               "label": "knows", "citations": [str(excerpt_id)]}]},
                     "sources": [{"id": str(excerpt_id), "text": "safe"}]},
        "node_bindings": [(local_node, "native-node")],
        "evidence_bindings": [(local_edge, "native-edge", "evidence", excerpt_id)],
        "source_bindings": [source_binding]}
    monkeypatch.setattr(validation.guest_release, "validation_material", lambda **_: material)
    node = SimpleNamespace(node_id="native-node", label="Node", kind="npc")
    edge = SimpleNamespace(edge_id="native-edge", source_node_id="native-node", target_node_id="native-node", label="knows")
    projection = SimpleNamespace(snapshot=SimpleNamespace(admissibility="player"), summary=SimpleNamespace(projection_truncated=False),
                                 nodes=[node], relationships=[edge])
    binding = SimpleNamespace(native_world_id="native", binding_version=3)
    access = SimpleNamespace(source_view=SimpleNamespace(epoch=42))
    monkeypatch.setattr(validation, "read_player_graph", lambda **_: (binding, projection, access))
    calls = []
    monkeypatch.setattr(validation, "verify_relationship_citation", lambda **kwargs: calls.append(kwargs))
    assert validation.validate_candidate(world_id="world", subject="owner", release_id=release_id, digest="digest") == 42
    assert calls[0]["source_binding"] == source_binding
    extra_id = uuid4()
    material["manifest"]["sources"].append({"id": str(extra_id), "text": "extra"})
    material["source_bindings"].append((extra_id, uuid4(), 0, 0, 1, "b" * 64, 0, 5, 2))
    with pytest.raises(validation.GuestReleaseValidationError, match="Standalone"):
        validation.validate_candidate(world_id="world", subject="owner", release_id=release_id, digest="digest")
    material["manifest"]["sources"].pop()
    material["source_bindings"].pop()
    edge.label = "changed"
    with pytest.raises(validation.GuestReleaseValidationError):
        validation.validate_candidate(world_id="world", subject="owner", release_id=release_id, digest="digest")
