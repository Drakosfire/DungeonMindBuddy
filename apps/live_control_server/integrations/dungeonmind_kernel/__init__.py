"""DungeonMind kernel conformance adapters (ephemeral, non-product).

These adapters import the real ``dungeonmind`` / ``dungeonmind_dnd`` packages.
They do not own DungeonMind contracts and do not change product hydration.

The only public Threat bridge entrypoint is ``bridge_exact_buddy_threat``, which
owns exact revision loading. Raw store/manifest pairing is intentionally not
exported so callers cannot invent false exact provenance.

``run_dungeonmind_threat_hydration_shadow`` is the optional post-response shadow
entrypoint. It is never authoritative.
"""

from apps.live_control_server.integrations.dungeonmind_kernel.config import (
    dungeonmind_threat_shadow_enabled,
)
from apps.live_control_server.integrations.dungeonmind_kernel.threat_hydration_shadow import (
    run_dungeonmind_threat_hydration_shadow,
)
from apps.live_control_server.integrations.dungeonmind_kernel.world_object_conformance_bridge import (
    BridgedStatblockAttachment,
    DungeonMindThreatConformanceBridgeResult,
    ThreatConformanceBridgeError,
    bridge_exact_buddy_threat,
    convert_buddy_definition_digest,
    map_buddy_provider_to_dungeonmind_provider_id,
    map_buddy_threat_object_id,
)

__all__ = [
    "BridgedStatblockAttachment",
    "DungeonMindThreatConformanceBridgeResult",
    "ThreatConformanceBridgeError",
    "bridge_exact_buddy_threat",
    "convert_buddy_definition_digest",
    "dungeonmind_threat_shadow_enabled",
    "map_buddy_provider_to_dungeonmind_provider_id",
    "map_buddy_threat_object_id",
    "run_dungeonmind_threat_hydration_shadow",
]
