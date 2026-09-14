from types import SimpleNamespace

from apps.live_control_server.models.world_graph_mutation_context import (
    WorldGraphMutationContext,
)
from src.graph_memory.extract_identity_gate import _infer_object_kind


def _context() -> WorldGraphMutationContext:
    return WorldGraphMutationContext(
        world_id="eldyrwild",
        revision_id="rev:a",
        head_revision_id="rev:a",
        objects={},
    )


def test_resolved_pc_corpus_ref_overrides_generic_character_kind() -> None:
    node = SimpleNamespace(
        node_type="character",
        label="Karsemine",
        corpus_ref=SimpleNamespace(type="pc"),
    )
    assert _infer_object_kind(node, _context()) == "pc"


def test_unknown_character_remains_npc() -> None:
    node = SimpleNamespace(node_type="character", label="Grishna", corpus_ref=None)
    assert _infer_object_kind(node, _context()) == "npc"
