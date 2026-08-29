"""Resolve the World Graph source-admission implementation for the current process.

D.2C4 is DungeonMind-only. There is no buddy_files branch.
Product services depend on this factory, not DungeonMind or PostgreSQL types.
"""

from __future__ import annotations

from apps.live_control_server.ports.world_graph_source_admission import (
    WorldGraphSourceAdmissionAuthority,
)


def get_world_graph_source_admission_authority() -> WorldGraphSourceAdmissionAuthority:
    """Return the mounted DungeonMind source-admission authority."""
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )

    return DungeonMindWorldGraphSourceAdmissionAdapter()
