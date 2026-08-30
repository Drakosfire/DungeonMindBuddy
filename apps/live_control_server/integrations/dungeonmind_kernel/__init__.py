"""DungeonMind kernel conformance adapters (ephemeral, non-product).

Submodules may import Buddy graph packages. This package ``__init__`` is
intentionally import-light so mounted product can load ``config`` /
``world_graph_authority`` helpers without pulling UnionSupergraph/Kernel
(CUTOVER D.3A). Prefer ``from ...dungeonmind_kernel.<module> import ...``.
Package-level names remain available via lazy ``__getattr__``.
"""

from __future__ import annotations

from typing import Any

_EXPORTS: dict[str, str] = {
    "BridgedStatblockAttachment": ".world_object_conformance_bridge",
    "DungeonMindThreatConformanceBridgeResult": ".world_object_conformance_bridge",
    "DungeonMindWorldObjectConformanceBridgeResult": ".world_object_conformance_bridge",
    "RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1": ".relationship_adjudication_continuity_v1",
    "RELATIONSHIP_EFFECTIVE_CONFORMANCE_SCHEMA_V1": ".relationship_effective_conformance_v1",
    "RELATIONSHIP_EXPLICIT_ADAPTER_CATALOG_SCHEMA_V1": ".relationship_explicit_adapters_v1",
    "RELATIONSHIP_EXPLICIT_ADAPTER_CONFORMANCE_SCHEMA_V1": ".relationship_explicit_adapter_conformance_v1",
    "RELATIONSHIP_RESIDUAL_ADJUDICATION_SCHEMA": ".relationship_residual_adjudication",
    "RELATIONSHIP_RESIDUAL_SOURCE_SEALS_SCHEMA": ".relationship_residual_adjudication",
    "RelationshipAdjudicationContinuityReportV1": ".relationship_adjudication_continuity_v1",
    "RelationshipEffectiveConformanceReportV1": ".relationship_effective_conformance_v1",
    "RelationshipExplicitAdapterCatalogV1": ".relationship_explicit_adapters_v1",
    "RelationshipExplicitAdapterConformanceReportV1": ".relationship_explicit_adapter_conformance_v1",
    "RelationshipExplicitAdapterIntegrityError": ".relationship_explicit_adapters_v1",
    "RelationshipResidualAdjudicationReport": ".relationship_residual_adjudication",
    "ResolvedRelationshipExplicitAdapterV1": ".relationship_explicit_adapters_v1",
    "ThreatConformanceBridgeError": ".world_object_conformance_bridge",
    "WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA": ".whole_world_conformance",
    "WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V2": ".whole_world_conformance_v2",
    "WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V3": ".whole_world_conformance_v3",
    "WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V4": ".whole_world_conformance_v4",
    "WholeWorldConformanceError": ".whole_world_conformance",
    "WholeWorldConformanceReport": ".whole_world_conformance",
    "WholeWorldConformanceReportV2": ".whole_world_conformance_v2",
    "WholeWorldConformanceReportV3": ".whole_world_conformance_v3",
    "WholeWorldConformanceReportV4": ".whole_world_conformance_v4",
    "analyze_eldyrwild_relationship_residual_adjudication": ".relationship_residual_adjudication",
    "analyze_exact_buddy_world_revision": ".whole_world_conformance",
    "analyze_exact_buddy_world_revision_v2": ".whole_world_conformance_v2",
    "analyze_exact_buddy_world_revision_v3": ".whole_world_conformance_v3",
    "analyze_exact_buddy_world_revision_v4": ".whole_world_conformance_v4",
    "analyze_relationship_adjudication_continuity_v1": ".relationship_adjudication_continuity_v1",
    "analyze_relationship_effective_conformance_v1": ".relationship_effective_conformance_v1",
    "analyze_relationship_explicit_adapter_conformance_v1": ".relationship_explicit_adapter_conformance_v1",
    "bridge_exact_buddy_threat": ".world_object_conformance_bridge",
    "bridge_exact_buddy_world_object": ".world_object_conformance_bridge",
    "build_exact_dungeonmind_adoption_revision": ".whole_world_conformance",
    "build_exact_dungeonmind_adoption_revision_v2": ".whole_world_conformance_v2",
    "build_exact_dungeonmind_adoption_revision_v3": ".whole_world_conformance_v3",
    "build_exact_dungeonmind_adoption_revision_v4": ".whole_world_conformance_v4",
    "compact_relationship_adjudication_continuity_report_v1": ".relationship_adjudication_continuity_v1",
    "compact_relationship_effective_conformance_report_v1": ".relationship_effective_conformance_v1",
    "compact_relationship_explicit_adapter_conformance_report_v1": ".relationship_explicit_adapter_conformance_v1",
    "compact_relationship_residual_adjudication_report": ".relationship_residual_adjudication",
    "continuity_active_edge_ids_v1": ".relationship_adjudication_continuity_v1",
    "continuity_invalidated_edge_ids_v1": ".relationship_adjudication_continuity_v1",
    "convert_buddy_definition_digest": ".world_object_conformance_bridge",
    "dungeonmind_threat_shadow_enabled": ".config",
    "inspect_dungeonmind_durable_adoption_seam": ".whole_world_conformance",
    "load_eldyrwild_relationship_explicit_adapter_catalog_v1": ".relationship_explicit_adapters_v1",
    "load_residual_source_seals": ".relationship_residual_adjudication",
    "map_buddy_provider_to_dungeonmind_provider_id": ".world_object_conformance_bridge",
    "map_buddy_threat_object_id": ".world_object_conformance_bridge",
    "map_buddy_world_object_id": ".world_object_conformance_bridge",
    "prove_revision_is_anchor_or_descendant_v1": ".relationship_adjudication_continuity_v1",
    "resolve_carried_relationship_explicit_adapter_v1": ".relationship_effective_conformance_v1",
    "resolve_relationship_explicit_adapter_v1": ".relationship_explicit_adapters_v1",
    "run_dungeonmind_threat_hydration_shadow": ".threat_hydration_shadow",
    "snapshot_world_graph_tree_digest": ".whole_world_conformance",
}

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

def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib
    module = importlib.import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value

