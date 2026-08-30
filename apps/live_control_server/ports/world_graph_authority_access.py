"""Resolve the World Graph authority implementation for the current process.

Product services depend on this factory, not DungeonMind or PostgreSQL types.
Mounted production is DungeonMind-only (CUTOVER D.3A).
"""

from __future__ import annotations

from pathlib import Path

from apps.live_control_server.ports.world_graph_authority import WorldGraphAuthority


def get_world_graph_authority(*, world_root: Path | None = None) -> WorldGraphAuthority:
    """Return the mounted DungeonMind World Graph authority.

    Retired ``buddy_files`` / ``quiesced`` modes and alternate ``world_root``
    values fail closed. Unmounted tooling may construct the named BuddyFiles
    adapter directly; this factory must not.
    """
    from apps.live_control_server.config import require_mounted_dungeonmind_world_graph
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )

    require_mounted_dungeonmind_world_graph(world_root=world_root)
    return DungeonMindWorldGraphAuthorityAdapter()
