"""Resolve the World Graph authority implementation for the current process.

Product services depend on this factory, not DungeonMind or PostgreSQL types.
"""

from __future__ import annotations

from pathlib import Path

from apps.live_control_server.ports.world_graph_authority import WorldGraphAuthority


def get_world_graph_authority(*, world_root: Path | None = None) -> WorldGraphAuthority:
    """Return the mounted World Graph authority for this process.

    ``dungeonmind`` production reads/writes use the DungeonMind adapter.
    Any explicit non-production root, or buddy_files/quiesced mode, uses the
    named file adapter (D.3 deletion owner).
    """
    from apps.live_control_server.config import world_graph_native_production_read

    if world_graph_native_production_read(world_root):
        from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
            DungeonMindWorldGraphAuthorityAdapter,
        )

        return DungeonMindWorldGraphAuthorityAdapter()
    from apps.live_control_server.integrations.buddy_files.world_graph_authority_adapter import (
        BuddyFilesWorldGraphAuthorityAdapter,
    )

    return BuddyFilesWorldGraphAuthorityAdapter(world_root)
