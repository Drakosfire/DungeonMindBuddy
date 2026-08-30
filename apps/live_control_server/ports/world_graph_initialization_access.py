"""Resolve the World Graph initialization implementation for the current process.

Product services depend on this factory, not DungeonMind or PostgreSQL types.
Mounted production is DungeonMind-only (CUTOVER D.3A).
"""

from __future__ import annotations

from pathlib import Path

from apps.live_control_server.ports.world_graph_initialization import (
    WorldGraphInitializationAuthority,
)


def get_world_graph_initialization_authority(
    *,
    world_root: Path | None = None,
) -> WorldGraphInitializationAuthority:
    """Return the mounted first-world initialization authority."""
    from apps.live_control_server.config import require_mounted_dungeonmind_world_graph
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )

    require_mounted_dungeonmind_world_graph(world_root=world_root)
    return DungeonMindWorldGraphInitializationAdapter()
