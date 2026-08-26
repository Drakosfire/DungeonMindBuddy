"""Resolve the World Graph initialization implementation for the current process.

Product services depend on this factory, not DungeonMind or PostgreSQL types.
Selection matches existing-parent World Graph authority: production dungeonmind
mode on the production root uses the DungeonMind adapter. Explicit buddy_files,
quiesced mode, or a non-production root uses the named file adapter.
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
    """Return the mounted first-world initialization authority for this process."""
    from apps.live_control_server.config import world_graph_native_production_read

    if world_graph_native_production_read(world_root):
        from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
            DungeonMindWorldGraphInitializationAdapter,
        )

        return DungeonMindWorldGraphInitializationAdapter()
    from apps.live_control_server.integrations.buddy_files.world_graph_initialization_adapter import (
        BuddyFilesWorldGraphInitializationAdapter,
    )

    return BuddyFilesWorldGraphInitializationAdapter(world_root)
