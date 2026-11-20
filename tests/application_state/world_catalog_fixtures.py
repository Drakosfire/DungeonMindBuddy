"""Synthetic World setup through the real APP owner, never a file fallback."""
from pathlib import Path

from application_state.world_catalog import service as catalog
from application_state.world_catalog.types import WorldContainerRecord


def store_world(record: WorldContainerRecord):
    current = catalog.get_world(record.world_id)
    return catalog.save_world(record, expected_revision=current.revision if current else 0).record


def world_snapshot():
    return catalog.list_worlds()


def legacy_world_catalog_path(root: Path) -> Path:
    """Only for proving a retired file is ignored and preserved."""
    return root / "out/registries/world_containers.json"


def change_binding(world_id: str, **changes):
    """Mutate a seeded binding through the real catalog owner."""
    world = catalog.get_world(world_id).record
    binding = world.native_graph_binding.model_copy(update=changes)
    return store_world(world.model_copy(update={"native_graph_binding": binding}))
