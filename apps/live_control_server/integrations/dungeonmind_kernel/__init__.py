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
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_explicit_adapter_conformance_v1 import (
    RELATIONSHIP_EXPLICIT_ADAPTER_CONFORMANCE_SCHEMA_V1,
    RelationshipExplicitAdapterConformanceReportV1,
    analyze_relationship_explicit_adapter_conformance_v1,
    compact_relationship_explicit_adapter_conformance_report_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_explicit_adapters_v1 import (
    RELATIONSHIP_EXPLICIT_ADAPTER_CATALOG_SCHEMA_V1,
    RelationshipExplicitAdapterCatalogV1,
    RelationshipExplicitAdapterIntegrityError,
    ResolvedRelationshipExplicitAdapterV1,
    load_eldyrwild_relationship_explicit_adapter_catalog_v1,
    resolve_relationship_explicit_adapter_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_continuity_v1 import (
    RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1,
    RelationshipAdjudicationContinuityReportV1,
    analyze_relationship_adjudication_continuity_v1,
    compact_relationship_adjudication_continuity_report_v1,
    continuity_active_edge_ids_v1,
    continuity_invalidated_edge_ids_v1,
    prove_revision_is_anchor_or_descendant_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    RELATIONSHIP_EFFECTIVE_CONFORMANCE_SCHEMA_V1,
    RelationshipEffectiveConformanceReportV1,
    analyze_relationship_effective_conformance_v1,
    compact_relationship_effective_conformance_report_v1,
    resolve_carried_relationship_explicit_adapter_v1,
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
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V4,
    WholeWorldConformanceReportV4,
    analyze_exact_buddy_world_revision_v4,
    build_exact_dungeonmind_adoption_revision_v4,
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
    "WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V4",
    "RELATIONSHIP_RESIDUAL_ADJUDICATION_SCHEMA",
    "RELATIONSHIP_RESIDUAL_SOURCE_SEALS_SCHEMA",
    "RELATIONSHIP_EXPLICIT_ADAPTER_CATALOG_SCHEMA_V1",
    "RELATIONSHIP_EXPLICIT_ADAPTER_CONFORMANCE_SCHEMA_V1",
    "RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1",
    "RELATIONSHIP_EFFECTIVE_CONFORMANCE_SCHEMA_V1",
    "WholeWorldConformanceError",
    "WholeWorldConformanceReport",
    "WholeWorldConformanceReportV2",
    "WholeWorldConformanceReportV3",
    "WholeWorldConformanceReportV4",
    "RelationshipResidualAdjudicationReport",
    "RelationshipExplicitAdapterCatalogV1",
    "RelationshipExplicitAdapterConformanceReportV1",
    "RelationshipExplicitAdapterIntegrityError",
    "ResolvedRelationshipExplicitAdapterV1",
    "RelationshipAdjudicationContinuityReportV1",
    "RelationshipEffectiveConformanceReportV1",
    "analyze_exact_buddy_world_revision",
    "analyze_exact_buddy_world_revision_v2",
    "analyze_exact_buddy_world_revision_v3",
    "analyze_exact_buddy_world_revision_v4",
    "analyze_eldyrwild_relationship_residual_adjudication",
    "analyze_relationship_explicit_adapter_conformance_v1",
    "analyze_relationship_adjudication_continuity_v1",
    "analyze_relationship_effective_conformance_v1",
    "compact_relationship_residual_adjudication_report",
    "compact_relationship_explicit_adapter_conformance_report_v1",
    "compact_relationship_adjudication_continuity_report_v1",
    "compact_relationship_effective_conformance_report_v1",
    "continuity_active_edge_ids_v1",
    "continuity_invalidated_edge_ids_v1",
    "load_eldyrwild_relationship_explicit_adapter_catalog_v1",
    "load_residual_source_seals",
    "prove_revision_is_anchor_or_descendant_v1",
    "resolve_relationship_explicit_adapter_v1",
    "resolve_carried_relationship_explicit_adapter_v1",
    "build_exact_dungeonmind_adoption_revision",
    "build_exact_dungeonmind_adoption_revision_v2",
    "build_exact_dungeonmind_adoption_revision_v3",
    "build_exact_dungeonmind_adoption_revision_v4",
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
