"""DungeonMind kernel conformance adapters (ephemeral, non-product).

These adapters import the real ``dungeonmind`` / ``dungeonmind_dnd`` packages.
They do not own DungeonMind contracts and do not change product hydration.

Public bridge entrypoints are ``bridge_exact_buddy_world_object`` (general) and
``bridge_exact_buddy_threat`` (Threat compatibility). Both own exact revision
loading. Raw store/manifest pairing is intentionally not exported so callers
cannot invent false exact provenance.

``run_dungeonmind_threat_hydration_shadow`` is the optional post-response shadow
entrypoint. It is never authoritative.
"""

from apps.live_control_server.integrations.dungeonmind_kernel.config import (
    dungeonmind_threat_shadow_enabled,
)
from apps.live_control_server.integrations.dungeonmind_kernel.threat_hydration_shadow import (
    run_dungeonmind_threat_hydration_shadow,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA,
    WholeWorldConformanceError,
    WholeWorldConformanceReport,
    analyze_exact_buddy_world_revision,
    build_exact_dungeonmind_adoption_revision,
    inspect_dungeonmind_durable_adoption_seam,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v2 import (
    WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V2,
    WholeWorldConformanceReportV2,
    analyze_exact_buddy_world_revision_v2,
    build_exact_dungeonmind_adoption_revision_v2,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    RELATIONSHIP_RESIDUAL_ADJUDICATION_SCHEMA,
    RELATIONSHIP_RESIDUAL_SOURCE_SEALS_SCHEMA,
    RelationshipResidualAdjudicationReport,
    analyze_eldyrwild_relationship_residual_adjudication,
    compact_relationship_residual_adjudication_report,
    load_residual_source_seals,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v3 import (
    WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V3,
    WholeWorldConformanceReportV3,
    analyze_exact_buddy_world_revision_v3,
    build_exact_dungeonmind_adoption_revision_v3,
)
from apps.live_control_server.integrations.dungeonmind_kernel.world_object_conformance_bridge import (
    BridgedStatblockAttachment,
    DungeonMindThreatConformanceBridgeResult,
    DungeonMindWorldObjectConformanceBridgeResult,
    ThreatConformanceBridgeError,
    bridge_exact_buddy_threat,
    bridge_exact_buddy_world_object,
    convert_buddy_definition_digest,
    map_buddy_provider_to_dungeonmind_provider_id,
    map_buddy_threat_object_id,
    map_buddy_world_object_id,
)

__all__ = [
    "WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA",
    "WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V2",
    "WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V3",
    "RELATIONSHIP_RESIDUAL_ADJUDICATION_SCHEMA",
    "RELATIONSHIP_RESIDUAL_SOURCE_SEALS_SCHEMA",
    "WholeWorldConformanceError",
    "WholeWorldConformanceReport",
    "WholeWorldConformanceReportV2",
    "WholeWorldConformanceReportV3",
    "RelationshipResidualAdjudicationReport",
    "analyze_exact_buddy_world_revision",
    "analyze_exact_buddy_world_revision_v2",
    "analyze_exact_buddy_world_revision_v3",
    "analyze_eldyrwild_relationship_residual_adjudication",
    "compact_relationship_residual_adjudication_report",
    "load_residual_source_seals",
    "build_exact_dungeonmind_adoption_revision",
    "build_exact_dungeonmind_adoption_revision_v2",
    "build_exact_dungeonmind_adoption_revision_v3",
    "inspect_dungeonmind_durable_adoption_seam",
    "snapshot_world_graph_tree_digest",
    "BridgedStatblockAttachment",
    "DungeonMindThreatConformanceBridgeResult",
    "DungeonMindWorldObjectConformanceBridgeResult",
    "ThreatConformanceBridgeError",
    "bridge_exact_buddy_threat",
    "bridge_exact_buddy_world_object",
    "convert_buddy_definition_digest",
    "dungeonmind_threat_shadow_enabled",
    "map_buddy_provider_to_dungeonmind_provider_id",
    "map_buddy_threat_object_id",
    "map_buddy_world_object_id",
    "run_dungeonmind_threat_hydration_shadow",
]
