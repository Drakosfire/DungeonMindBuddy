"""Seal the exact Eldyrwild ``dm_existing_world_adoption_bundle_v2``.

Current assertion-supported semantic relationships materialize into
``dm_union_graph_v6``. Contradicted/retracted/unsupported stored edges remain
inspectable as raw history and are preserved through v2 contribution/correction
ledgers. This producer does not mutate Buddy World Graph state and does not
invoke DungeonMind adoption persistence.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from dungeonmind.application.existing_world_adoption import (
    parse_existing_world_adoption_bundle,
)
from dungeonmind.application.graph_snapshot import (
    GRAPH_SCHEMA_V6,
    RELATIONSHIP_ENDPOINT_ASPECT_SCHEMA,
    VersionedUnionGraphSnapshotReader,
)
from dungeonmind.application.graph_snapshot_v4 import AliasAssertionV4Record
from dungeonmind.application.graph_snapshot_v6 import (
    GraphObjectV6Record,
    GraphRelationshipV6Record,
    ObjectAspectAssertionV6Record,
    UnionGraphV6Payload,
)
from dungeonmind.application.semantic_profiles import descriptor_sha256
from dungeonmind.contracts.contribution import (
    AcceptanceState,
    ContributionSourceKind,
    ContributionStatus,
    GraphContributionAssertionCorrection,
    GraphContributionAssertionCorrectionKind,
    GraphContributionAssertionV2,
    GraphContributionV2,
)
from dungeonmind.contracts.evidence import (
    EvidenceRef,
    EvidenceRefV2,
    EvidenceRole,
    SourceArtifactV2,
    SourceDomain,
    SourceRevision,
    SourceReviewState,
    SourceStatus,
    WorkspaceDocumentRefV1,
)
from dungeonmind.contracts.existing_world_adoption import (
    EXISTING_WORLD_ADOPTION_BUNDLE_V2_SCHEMA,
    ExistingWorldAdoptionAuthorityRefV1,
    ExistingWorldAdoptionBundleV2,
    ExistingWorldAdoptionSourceProvenanceV1,
    existing_world_adoption_bundle_v2_canonical_bytes,
)
from dungeonmind.contracts.identity import (
    IdentityAliasMapRewrite,
    IdentityDecisionKind,
    IdentityDecisionRecordV2,
    IdentityDecisionStatus,
    IdentityMergeSideEffects,
    IdentityOutcome,
)
from dungeonmind.contracts.knowledge_assertion import (
    EpistemicKindV2,
    KnowledgeAssertionMetadataV1,
    TemporalScopeKind,
    TemporalScopeRefV1,
)
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vocabulary import (
    CanonState,
    ContributionEpistemicKind,
    Visibility,
)
from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_v3_descriptor,
    load_builtin_world_object_v5_vocabulary,
    vocabulary_sha256,
)
from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_dual_sense_decomposition_v1 import (
    DualSenseDecompositionPackageV1,
    EndpointAssignmentV1,
    admit_edge_under_dm_kinds,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_explicit_adapters_v1 import (
    load_eldyrwild_relationship_explicit_adapter_catalog_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _load_exact_buddy_revision,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
    PredicateDisposition,
    _USES_STATBLOCK,
    _classify_edge_predicate_v4,
    _current_relationship_edge_ids,
    _edge_has_current_semantic_support,
    resolve_buddy_predicate_mapping_v4,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v5 import (
    analyze_exact_buddy_world_revision_v5,
)
from apps.live_control_server.services.cutover_relationship_dual_sense_decomposition_after_alias_package import (
    LOCKED_PACKAGE_SHA256 as DUAL_SENSE_LOCKED_SHA256,
    MANIFEST_RELPATH as DUAL_SENSE_MANIFEST_RELPATH,
)
from apps.live_control_server.services.eldyrwild_relationship_node_kind_source_repair import (
    DEFERRED_RESIDUAL_EDGE_IDS,
    KIND_REPAIR_SPECS,
    LOCKED_MANIFEST_SHA256 as KIND_REPAIR_LOCKED_SHA256,
    STAGE_B_REMAINING_RESIDUAL_EDGE_IDS,
)
from apps.live_control_server.services.eldyrwild_relationship_node_kind_source_repair import (
    _overlay_store,
)
from graph_memory.kernel.contribution_models import GraphContribution as BuddyGraphContribution
from graph_memory.kernel.identity_models import IdentityDecisionRecord as BuddyIdentityDecision
from graph_memory.union_supergraph.model import UnionSupergraphEdge, UnionSupergraphStore
from graph_memory.world_supergraph.contribution_store import list_contribution_records
from graph_memory.world_supergraph.identity_decision_store import (
    list_identity_decision_records,
)

WORLD_ID = "eldyrwild"
CANONICAL_REVISION_ID = "rev:0c644e56b45bcaac709012206e3e41c2"
CANONICAL_GRAPH_PAYLOAD_SHA256 = (
    "0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2"
)
DUNGEONMIND_PIN = "f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92"
BUDDY_BASE_SHA = "26ddd83ddbec381c816fbd2ede891aa5d816b9e1"
WORLD_OBJECT_V5_SHA256 = (
    "f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8"
)
EXPECTED_RAW_NODE_COUNT = 472
EXPECTED_RAW_EDGE_COUNT = 376
EXPECTED_CURRENT_SEMANTIC = 323
EXPECTED_REPRESENTED = 314
EXPECTED_RESIDUAL = 9
EXPECTED_MECHANICS = 3
EXPECTED_HISTORY_ONLY = 50
EXPECTED_AFTER_KIND_REPAIR_REPRESENTED = 318
EXPECTED_AFTER_KIND_REPAIR_RESIDUAL = 5
MAX_BUNDLE_BYTES = 50 * 1024 * 1024
BUNDLE_RELPATH = Path(
    "graph_data/approved_existing_world_adoptions/eldyrwild/dungeonmind-v6/bundle.json"
)
ADOPTION_ID = f"adoption:{WORLD_ID}:dungeonmind-v6:{CANONICAL_REVISION_ID}"
PRODUCER_ID = "dungeonmindbuddy.eldyrwild_existing_world_adoption_bundle_v2"
KIND_REPAIR_EDGE_IDS = frozenset(
    edge_id
    for spec in KIND_REPAIR_SPECS
    for edge_id in spec["affected_deferred_edge_ids"]
)
FALSE_STOP_EDGE_IDS: tuple[str, ...] = (
    "edge:faction:town-guards-mireward-gate:reports_threat_in:mystery:session25:west-wall-screaming-and-dark-shapes-below",
    "edge:node:torvak_hempdealer:reports_threat_in:mystery:session4:hempholm-moving-tree",
    "edge:group_session24_refugees_of_edge:part_of_group:mystery_7",
    "edge:item:crossbow_bolt_light_source:controls_comms_with:loc:north-road",
    "edge:npc_lysandra:controls_comms_with:loc:mirathorn_gate:may-close-gate",
    "edge:pc:ephanna:controls_comms_with:item:mage_hand_lasso",
    "edge:item_glowkindle_help_request:mission_targets:group_mercenaries",
    "edge:loc:stormspire-academy:objective_of:mystery:session7:glowing_mushrooms",
    "edge:node:fey_entity:objective_of:node:torbin:offers-torbin-over-as-part-of-the-bargain",
    "edge:node:berin_ironfoot:carries_report_to:loc:stormspire-academy:sends-meat-sample-for-analysis",
    "edge:node:hesta-bramblewood:governs:organization:merchant-s-crossroads-apothecary",
    "edge:node:thrin-branchborn:caused_by:mystery:session25:thrin-ambush-by-hybrid-creatures",
    "edge:pc:ephanna:hires:node:thrin-branchborn",
    "edge:node:torbin:identified_as:mystery:session8:torbin-oily-eyes:begins-showing-oily-eye-symptoms",
    "edge:npc:bill_the_belly:identified_as:mystery:session8:oil-eyed-guards:shows-oily-eye-symptoms",
    "edge:obj:session9:oil:identified_as:node:wolf",
)
_SOURCE_KIND_MAP = {
    "source_extraction": ContributionSourceKind.EXTRACTION,
    "standing_context": ContributionSourceKind.STANDING_CONTEXT,
    "graph_review_authored_assertion": ContributionSourceKind.GRAPH_REVIEW,
    "identity_decision": ContributionSourceKind.IDENTITY_DECISION,
    "manual_import": ContributionSourceKind.MANUAL_IMPORT,
}
_SOURCE_DOMAIN_MAP = {
    "recap": SourceDomain.SESSION_RECAP,
    "session_recap": SourceDomain.SESSION_RECAP,
    "worldbuilding": SourceDomain.WORLDBUILDING,
    "rulebook": SourceDomain.RULEBOOK,
    "prep": SourceDomain.PREP,
    "manual": SourceDomain.MANUAL,
}
_EVIDENCE_ROLE_MAP = {
    "support": EvidenceRole.SUPPORT,
    "contribution_support": EvidenceRole.SUPPORT,
    "contradiction": EvidenceRole.CONTRADICTION,
    "context": EvidenceRole.CONTEXT,
}
_CONTRIBUTION_EPISTEMIC_DIRECT = {
    "asserted": ContributionEpistemicKind.ASSERTED,
    "inferred": ContributionEpistemicKind.INFERRED,
    "speculative": ContributionEpistemicKind.SPECULATIVE,
    "source_derived_candidate": ContributionEpistemicKind.SOURCE_DERIVED_CANDIDATE,
}


class EldyrwildAdoptionBundleV2Error(RuntimeError):
    """Fail-closed producer STOP."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(message: str, code: str) -> EldyrwildAdoptionBundleV2Error:
    return EldyrwildAdoptionBundleV2Error(message, code=code)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EdgePartitionV2(_Model):
    current_semantic_ids: list[str]
    mechanics_ids: list[str]
    history_ids: list[str]


class FalseStopEdgeReportV2(_Model):
    edge_id: str
    raw_stored: bool
    current_support_state: str | None
    active_supporting_contribution_ids: list[str] = Field(default_factory=list)
    correction_contribution_ids: list[str] = Field(default_factory=list)
    correction_kinds: list[str] = Field(default_factory=list)
    current_semantic: bool
    final_disposition: Literal["SOURCE_MIGRATION_HISTORY"]


class MechanicsBindingProofV2(_Model):
    edge_id: str
    provider: str
    statblock_id: str
    revision_id: str
    definition_digest: str
    disposition: Literal["A"] = "A"


class MappedRelationshipV2(_Model):
    edge_id: str
    source_object_id: str
    target_object_id: str
    predicate: str
    reverse_endpoints: bool = False
    resolution: Literal["direct_or_governed", "kind_repair", "aspect_selection"]
    source_aspect_assertion_id: str | None = None
    target_aspect_assertion_id: str | None = None


@dataclass(frozen=True)
class EldyrwildAdoptionBundleV2Build:
    bundle: ExistingWorldAdoptionBundleV2
    canonical_bytes: bytes
    partition: EdgePartitionV2
    false_stop_reports: list[FalseStopEdgeReportV2]
    mechanics_proofs: list[MechanicsBindingProofV2]
    mapped_relationships: list[MappedRelationshipV2]
    raw_node_count: int
    raw_edge_count: int
    current_semantic_count: int
    represented_before_projections: int
    residual_before_projections: int
    represented_after_kind_repair: int
    residual_after_kind_repair: int
    history_only_count: int
    contribution_count: int
    assertion_count: int
    correction_count: int
    identity_decision_count: int
    v6_object_count: int
    v6_relationship_count: int
    secondary_aspect_count: int
    aspect_selected_relationship_count: int
    current_unrepresentable_count: int
    world_graph_digest: str
    expected_published_revision_id: str


def partition_raw_stored_edges(store: UnionSupergraphStore) -> EdgePartitionV2:
    """Partition raw stored edge IDs into current / mechanics / history."""
    raw_ids = set(store.edges)
    current_ids = _current_relationship_edge_ids(store)
    mechanics_ids = {
        edge.edge_id
        for edge in store.edges.values()
        if edge.predicate == _USES_STATBLOCK
    }
    current_semantic_ids = current_ids - mechanics_ids
    history_ids = raw_ids - current_semantic_ids - mechanics_ids
    if current_semantic_ids & mechanics_ids:
        raise _fail("current semantic overlapped mechanics specialization", "partition_overlap")
    if current_semantic_ids & history_ids:
        raise _fail("current semantic overlapped history-only storage", "partition_overlap")
    if mechanics_ids & history_ids:
        raise _fail("mechanics overlapped history-only storage", "partition_overlap")
    if current_semantic_ids | mechanics_ids | history_ids != raw_ids:
        raise _fail("raw/current/mechanics partition omitted stored edge IDs", "partition_omission")
    if mechanics_ids - current_ids:
        raise _fail("uses_statblock rows lacked current semantic support", "mechanics_not_current")
    return EdgePartitionV2(
        current_semantic_ids=sorted(current_semantic_ids),
        mechanics_ids=sorted(mechanics_ids),
        history_ids=sorted(history_ids),
    )


def _support_rows_for_edge(store: UnionSupergraphStore, edge_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for support in store.assertion_support.values():
        payload = support if isinstance(support, dict) else dict(support)
        if payload.get("graph_object_id") == edge_id:
            rows.append(payload)
    return rows


def evaluate_false_stop_edges(
    store: UnionSupergraphStore,
    *,
    contributions: list[BuddyGraphContribution],
) -> list[FalseStopEdgeReportV2]:
    assertions_by_id: dict[str, str] = {}
    corrections_by_assertion: dict[str, list[tuple[str, str]]] = {}
    for contribution in contributions:
        for assertion in (
            *contribution.candidate_assertions,
            *contribution.accepted_assertions,
            *contribution.rejected_assertions,
        ):
            assertions_by_id[assertion.assertion_id] = contribution.contribution_id
        for correction in contribution.assertion_corrections:
            corrections_by_assertion.setdefault(correction.target_assertion_id, []).append(
                (contribution.contribution_id, correction.correction_kind)
            )
    reports: list[FalseStopEdgeReportV2] = []
    for edge_id in FALSE_STOP_EDGE_IDS:
        if edge_id not in store.edges:
            raise _fail(f"false-STOP edge missing from raw storage: {edge_id}", "false_stop_missing")
        if _edge_has_current_semantic_support(store, edge_id):
            raise _fail(
                f"false-STOP edge is current-supported: {edge_id}",
                "false_stop_is_current",
            )
        rows = _support_rows_for_edge(store, edge_id)
        states = sorted({str(row.get("support_state") or "") for row in rows if row.get("support_state")})
        active: list[str] = []
        assertion_ids: list[str] = []
        for row in rows:
            active.extend(str(item) for item in (row.get("active_contribution_ids") or []) if item)
            assertion_id = row.get("assertion_id")
            if assertion_id:
                assertion_ids.append(str(assertion_id))
        correction_pairs = [
            pair
            for assertion_id in assertion_ids
            for pair in corrections_by_assertion.get(assertion_id, [])
        ]
        reports.append(
            FalseStopEdgeReportV2(
                edge_id=edge_id,
                raw_stored=True,
                current_support_state=states[0] if len(states) == 1 else (",".join(states) or None),
                active_supporting_contribution_ids=sorted(set(active)),
                correction_contribution_ids=sorted({pair[0] for pair in correction_pairs}),
                correction_kinds=sorted({pair[1] for pair in correction_pairs}),
                current_semantic=False,
                final_disposition="SOURCE_MIGRATION_HISTORY",
            )
        )
    return reports


def _mechanics_proofs(store: UnionSupergraphStore, mechanics_ids: list[str]) -> list[MechanicsBindingProofV2]:
    proofs: list[MechanicsBindingProofV2] = []
    for edge_id in mechanics_ids:
        edge = store.edges[edge_id]
        binding = edge.statblock_binding or edge.threat_statblock_binding
        if binding is None:
            raise _fail(f"uses_statblock missing binding: {edge_id}", "mechanics_binding_missing")
        provider = str(getattr(binding, "provider", "") or "")
        statblock_id = str(getattr(binding, "statblock_id", "") or "")
        revision_id = str(getattr(binding, "revision_id", "") or "")
        digest = str(getattr(binding, "definition_digest", "") or "")
        if provider != "dungeonmind" or not statblock_id or not revision_id or not digest:
            raise _fail(f"uses_statblock is not disposition A: {edge_id}", "mechanics_not_disposition_a")
        proofs.append(
            MechanicsBindingProofV2(
                edge_id=edge_id,
                provider=provider,
                statblock_id=statblock_id,
                revision_id=revision_id,
                definition_digest=digest,
            )
        )
    return proofs


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _parse_aware(value: str | None, *, field_name: str) -> datetime:
    if not value or not str(value).strip():
        raise _fail(f"{field_name} is missing a timestamp", "timestamp_missing")
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _parse_optional_aware(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    return _parse_aware(value, field_name="optional_timestamp")


def _load_dual_sense_package(repo: Path) -> DualSenseDecompositionPackageV1:
    path = repo / DUAL_SENSE_MANIFEST_RELPATH
    raw = path.read_bytes()
    digest = _sha256_bytes(raw)
    if digest != DUAL_SENSE_LOCKED_SHA256:
        raise _fail(
            f"dual-sense package digest drifted: {digest}",
            "dual_sense_package_tampered",
        )
    package = DualSenseDecompositionPackageV1.model_validate(json.loads(raw.decode("utf-8")))
    if (
        package.canonical_revision_id != CANONICAL_REVISION_ID
        or package.canonical_graph_payload_sha256 != CANONICAL_GRAPH_PAYLOAD_SHA256
    ):
        raise _fail("dual-sense package is not bound to the attested revision", "dual_sense_pin_mismatch")
    if len(package.endpoint_assignments) != 5 or len(package.decomposition_rows) != 3:
        raise _fail("dual-sense package assignment/row counts drifted", "dual_sense_shape_drift")
    if {row.edge_id for row in package.endpoint_assignments} != set(STAGE_B_REMAINING_RESIDUAL_EDGE_IDS):
        raise _fail("dual-sense assignments drifted from sealed residual five", "dual_sense_set_mismatch")
    return package


def _kind_for(store: UnionSupergraphStore, node_id: str) -> str:
    node = store.nodes.get(node_id)
    if node is None:
        raise _fail(f"relationship endpoint missing: {node_id}", "endpoint_missing")
    return node.kind


def _dm_kind(buddy_kind: str) -> str:
    mapped = CURRENT_V5_TARGET.buddy_to_dm_kind.get(buddy_kind)
    if mapped is None:
        raise _fail(f"Buddy kind has no DungeonMind mapping: {buddy_kind}", "kind_unmapped")
    return mapped


def _map_catalog_or_classified(
    edge: UnionSupergraphEdge,
    overlay: UnionSupergraphStore,
    catalog_by_id: dict[str, Any],
) -> tuple[str, bool, Literal["direct_or_governed", "kind_repair"]]:
    record = catalog_by_id.get(edge.edge_id)
    if record is not None:
        if (
            edge.predicate != record.expected_buddy_predicate
            or edge.source_node_id != record.expected_source_node_id
            or edge.target_node_id != record.expected_target_node_id
        ):
            raise _fail(
                f"explicit adapter catalog shape drifted: {edge.edge_id}",
                "explicit_adapter_shape_drift",
            )
        resolution: Literal["direct_or_governed", "kind_repair"] = (
            "kind_repair" if edge.edge_id in KIND_REPAIR_EDGE_IDS else "direct_or_governed"
        )
        return record.dungeonmind_term, bool(record.reverse_endpoints), resolution
    vocabulary = CURRENT_V5_TARGET.world_object_loader()
    _classification, _blocker, _note, disposition, mapped, reverse = _classify_edge_predicate_v4(
        edge,
        overlay,
        vocabulary,
        adjudication_domain=True,
        target=CURRENT_V5_TARGET,
    )
    if disposition != PredicateDisposition.EXISTING_EXPLICIT_ADAPTER or not mapped:
        raise _fail(
            f"current semantic relationship remains unrepresentable: {edge.edge_id}",
            "current_unrepresentable",
        )
    resolution = "kind_repair" if edge.edge_id in KIND_REPAIR_EDGE_IDS else "direct_or_governed"
    return mapped, bool(reverse), resolution


def _map_current_relationships(
    store: UnionSupergraphStore,
    overlay: UnionSupergraphStore,
    partition: EdgePartitionV2,
    package: DualSenseDecompositionPackageV1,
) -> list[MappedRelationshipV2]:
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    catalog_by_id = {record.edge_id: record for record in catalog.records}
    assignments = {row.edge_id: row for row in package.endpoint_assignments}
    mapped: list[MappedRelationshipV2] = []
    unrepresentable: list[str] = []
    for edge_id in partition.current_semantic_ids:
        edge = store.edges[edge_id]
        assignment = assignments.get(edge_id)
        if assignment is not None:
            mapped.append(_map_aspect_assignment(edge, overlay, assignment))
            continue
        try:
            predicate, reverse, resolution = _map_catalog_or_classified(edge, overlay, catalog_by_id)
        except EldyrwildAdoptionBundleV2Error as exc:
            if exc.code == "current_unrepresentable":
                unrepresentable.append(edge_id)
                continue
            raise
        source_id, target_id = edge.source_node_id, edge.target_node_id
        if reverse:
            source_id, target_id = target_id, source_id
        mapped.append(
            MappedRelationshipV2(
                edge_id=edge_id,
                source_object_id=source_id,
                target_object_id=target_id,
                predicate=predicate,
                reverse_endpoints=reverse,
                resolution=resolution,
            )
        )
    if unrepresentable:
        raise _fail(
            "current semantic relationships remain unrepresentable: "
            + ",".join(unrepresentable[:8]),
            "current_unrepresentable",
        )
    if len(mapped) != EXPECTED_CURRENT_SEMANTIC:
        raise _fail(
            f"mapped current semantic count {len(mapped)} != {EXPECTED_CURRENT_SEMANTIC}",
            "current_semantic_count_mismatch",
        )
    return mapped


def _map_aspect_assignment(
    edge: UnionSupergraphEdge,
    overlay: UnionSupergraphStore,
    assignment: EndpointAssignmentV1,
) -> MappedRelationshipV2:
    if (
        edge.predicate != assignment.buddy_predicate
        or edge.source_node_id != assignment.source_node_id
        or edge.target_node_id != assignment.target_node_id
    ):
        raise _fail(f"dual-sense assignment changed edge shape: {edge.edge_id}", "edge_shape_mutation")
    source_dm = _dm_kind(_kind_for(overlay, assignment.source_node_id))
    target_dm = _dm_kind(_kind_for(overlay, assignment.target_node_id))
    projected = assignment.aspect_ref.projected_dm_kind
    source_aspect_id = None
    target_aspect_id = None
    if assignment.assigned_endpoint == "source":
        if assignment.aspect_ref.source_node_id != assignment.source_node_id:
            raise _fail(f"aspect is not the assigned source: {edge.edge_id}", "aspect_endpoint_mismatch")
        source_dm = projected
        source_aspect_id = _aspect_assertion_id(
            assignment.aspect_ref.source_node_id, assignment.aspect_ref.aspect_key
        )
    else:
        if assignment.aspect_ref.source_node_id != assignment.target_node_id:
            raise _fail(f"aspect is not the assigned target: {edge.edge_id}", "aspect_endpoint_mismatch")
        target_dm = projected
        target_aspect_id = _aspect_assertion_id(
            assignment.aspect_ref.source_node_id, assignment.aspect_ref.aspect_key
        )
    admission = admit_edge_under_dm_kinds(
        edge,
        source_dm_kind=source_dm,
        target_dm_kind=target_dm,
        target=CURRENT_V5_TARGET,
    )
    if not admission.admitted or not admission.dm_predicate:
        raise _fail(
            f"dual-sense assignment is not admitted under v5: {edge.edge_id}",
            "aspect_not_admitted",
        )
    return MappedRelationshipV2(
        edge_id=edge.edge_id,
        source_object_id=edge.source_node_id,
        target_object_id=edge.target_node_id,
        predicate=admission.dm_predicate,
        resolution="aspect_selection",
        source_aspect_assertion_id=source_aspect_id,
        target_aspect_assertion_id=target_aspect_id,
    )


def _object_assertion_id(node_id: str) -> str:
    return f"ka:object:{node_id}"


def _alias_assertion_id(node_id: str, alias: str) -> str:
    digest = hashlib.sha256(alias.encode("utf-8")).hexdigest()[:16]
    return f"ka:alias:{node_id}:{digest}"


def _aspect_assertion_id(node_id: str, aspect_key: str) -> str:
    return f"ka:aspect:{node_id}:{aspect_key}"


def _relationship_assertion_id(edge_id: str) -> str:
    return f"ka:rel:{edge_id}"


def _knowledge_metadata(
    *,
    assertion_id: str,
    campaign_scope: str | None,
    evidence_ref_ids: list[str],
    session_refs: list[str],
    canon_state: CanonState,
) -> KnowledgeAssertionMetadataV1:
    if not evidence_ref_ids:
        raise _fail(f"assertion {assertion_id} has no evidence", "assertion_evidence_missing")
    return KnowledgeAssertionMetadataV1(
        assertion_id=assertion_id,
        campaign_scope=campaign_scope,
        visibility=Visibility.GM,
        epistemic_kind=EpistemicKindV2.FACT,
        canon_state=canon_state,
        evidence_ref_ids=list(dict.fromkeys(evidence_ref_ids)),
        session_refs=list(dict.fromkeys(session_refs)),
        temporal_scope=TemporalScopeRefV1(kind=TemporalScopeKind.UNKNOWN),
    )


def _node_canon(node: Any) -> CanonState:
    raw = (node.state or {}).get("canon_state") if isinstance(node.state, dict) else None
    if raw == "canonical":
        return CanonState.CANONICAL
    if raw == "provisional":
        return CanonState.PROVISIONAL
    if raw == "retracted":
        return CanonState.RETRACTED
    return CanonState.CANONICAL


def _map_source_domain(raw: str) -> SourceDomain | None:
    return _SOURCE_DOMAIN_MAP.get(raw)


def _map_evidence_role(raw: str) -> EvidenceRole:
    mapped = _EVIDENCE_ROLE_MAP.get(raw)
    if mapped is None:
        raise _fail(f"unsupported Buddy evidence role {raw!r}", "evidence_role_unmapped")
    return mapped


def _revision_id_for_artifact(artifact_id: str, content_sha256: str) -> str:
    digest = content_sha256.removeprefix("sha256:")
    return f"rev:{artifact_id}:{digest}"


def _history_artifact_domain_key(artifact_id: str) -> str:
    if artifact_id.startswith("threat-publication-"):
        return "threat_publication"
    if artifact_id.startswith("graph-native:"):
        return "graph_native"
    return "other"


def _synthetic_source_artifact(artifact_id: str, *, campaign_id: str | None) -> SourceArtifactV2:
    return SourceArtifactV2(
        source_artifact_id=artifact_id,
        source_domain_key=_history_artifact_domain_key(artifact_id),
        source_domain=SourceDomain.OTHER,
        world_id=WORLD_ID,
        campaign_id=campaign_id,
        session_id=None,
        uri=None,
        current_revision_id=None,
        authority=None,
        visibility=None,
        artifact_kind=None,
        document_class=None,
        review_state=None,
        source_visibility_state=None,
        workspace_document_ref=None,
        lineage={"producer_reconstruction": "contribution_history_identity_only"},
        status=SourceStatus.ACTIVE,
        created_at=None,
        updated_at=None,
    )


def _contribution_artifact_ids(
    contributions: list[BuddyGraphContribution],
) -> dict[str, str | None]:
    campaign_by_artifact: dict[str, str | None] = {}
    for contribution in contributions:
        ids = [contribution.source_artifact_id]
        for assertion in (
            *contribution.candidate_assertions,
            *contribution.accepted_assertions,
            *contribution.rejected_assertions,
        ):
            ids.append(assertion.source_artifact_id)
        for artifact_id in ids:
            if not artifact_id:
                continue
            campaign_by_artifact.setdefault(artifact_id, contribution.campaign_scope)
    return campaign_by_artifact


def _map_source_artifacts(
    store: UnionSupergraphStore,
    *,
    extra_artifact_campaigns: dict[str, str | None] | None = None,
) -> tuple[list[SourceArtifactV2], list[SourceRevision], dict[str, str | None]]:
    artifacts: list[SourceArtifactV2] = []
    revisions: list[SourceRevision] = []
    current_by_artifact: dict[str, str | None] = {}
    for artifact in store.source_artifacts.values():
        domain_key = str(artifact.source_domain)
        domain = _map_source_domain(domain_key)
        if domain is None:
            domain = SourceDomain.OTHER
        current_revision_id = None
        if artifact.content_sha256:
            current_revision_id = _revision_id_for_artifact(
                artifact.source_artifact_id, artifact.content_sha256
            )
            created_at = _parse_optional_aware(artifact.created_at) or _parse_optional_aware(
                artifact.updated_at
            )
            if created_at is None:
                created_at = datetime(1970, 1, 1, tzinfo=UTC)
            revisions.append(
                SourceRevision(
                    source_revision_id=current_revision_id,
                    source_artifact_id=artifact.source_artifact_id,
                    content_sha256=artifact.content_sha256.removeprefix("sha256:"),
                    body_storage="external",
                    locator=artifact.uri,
                    created_at=created_at,
                )
            )
        workspace_ref = None
        if artifact.workspace_document_id is not None:
            workspace_ref = WorkspaceDocumentRefV1(
                document_id=artifact.workspace_document_id,
                revision=int(artifact.workspace_document_revision or 1),
            )
        review_state = None
        if artifact.authority_state in {"draft", "reviewed", "canonical"}:
            review_state = SourceReviewState(artifact.authority_state)
        artifacts.append(
            SourceArtifactV2(
                source_artifact_id=artifact.source_artifact_id,
                source_domain_key=domain_key,
                source_domain=domain,
                world_id=artifact.world_id or WORLD_ID,
                campaign_id=artifact.campaign_id,
                session_id=artifact.session_id,
                uri=artifact.uri,
                current_revision_id=current_revision_id,
                authority=None,
                visibility=None,
                artifact_kind=artifact.artifact_kind,
                document_class=artifact.document_class,
                review_state=review_state,
                source_visibility_state=artifact.visibility_state,
                workspace_document_ref=workspace_ref,
                lineage=dict(artifact.lineage or {}),
                status=SourceStatus(artifact.status),
                created_at=_parse_optional_aware(artifact.created_at),
                updated_at=_parse_optional_aware(artifact.updated_at),
            )
        )
        current_by_artifact[artifact.source_artifact_id] = current_revision_id
    for artifact_id, campaign_id in sorted((extra_artifact_campaigns or {}).items()):
        if artifact_id in current_by_artifact:
            continue
        artifacts.append(_synthetic_source_artifact(artifact_id, campaign_id=campaign_id))
        current_by_artifact[artifact_id] = None
    return artifacts, revisions, current_by_artifact


def _map_graph_evidence(
    store: UnionSupergraphStore,
    current_by_artifact: dict[str, str | None],
    required_ids: set[str],
) -> list[EvidenceRefV2]:
    refs: list[EvidenceRefV2] = []
    for evidence_id in sorted(required_ids):
        evidence = store.evidence.get(evidence_id)
        if evidence is None:
            raise _fail(f"graph evidence missing: {evidence_id}", "evidence_missing")
        domain_key = str(evidence.source_domain)
        domain = _map_source_domain(domain_key) or SourceDomain.OTHER
        artifact_id = evidence.source_artifact_id
        refs.append(
            EvidenceRefV2(
                evidence_ref_id=evidence.evidence_ref_id,
                source_artifact_id=artifact_id,
                source_revision_id=current_by_artifact.get(artifact_id),
                source_domain_key=domain_key,
                source_domain=domain,
                evidence_role=_map_evidence_role(str(evidence.evidence_role)),
                can_open_source=bool(evidence.can_open_source),
                can_highlight_span=bool(evidence.can_highlight_span),
                session_id=evidence.session_id,
                source_span_ref_id=evidence.source_span_ref_id,
                locator=evidence.locator,
                uri=evidence.uri,
                source_locator=evidence.source_locator,
                line_ref=evidence.line_ref,
            )
        )
    return refs


def _map_contribution_evidence_ref(
    store: UnionSupergraphStore,
    evidence_ref_id: str,
    *,
    fallback_source_artifact_id: str | None,
) -> EvidenceRef:
    evidence = store.evidence.get(evidence_ref_id)
    if evidence is not None:
        domain_key = str(evidence.source_domain)
        domain = _map_source_domain(domain_key) or SourceDomain.OTHER
        return EvidenceRef(
            evidence_ref_id=evidence.evidence_ref_id,
            source_artifact_id=evidence.source_artifact_id,
            source_revision_id=None,
            source_domain=domain,
            evidence_role=_map_evidence_role(str(evidence.evidence_role)),
            can_open_source=bool(evidence.can_open_source),
            can_highlight_span=bool(evidence.can_highlight_span),
            locator=evidence.locator,
            uri=evidence.uri,
        )
    if not fallback_source_artifact_id:
        raise _fail(f"contribution evidence missing: {evidence_ref_id}", "evidence_missing")
    return EvidenceRef(
        evidence_ref_id=evidence_ref_id,
        source_artifact_id=fallback_source_artifact_id,
        source_revision_id=None,
        source_domain=SourceDomain.OTHER,
        evidence_role=EvidenceRole.SUPPORT,
        can_open_source=False,
        can_highlight_span=False,
        locator=None,
        uri=None,
    )


def _map_visibility(raw: str | None) -> Visibility:
    if raw in (None, "", "gm"):
        return Visibility.GM
    if raw == "player":
        return Visibility.PLAYER
    raise _fail(f"unsupported visibility {raw!r}", "visibility_unmapped")


def _map_contribution_epistemic(raw: str | None) -> tuple[ContributionEpistemicKind, str | None]:
    if raw in _CONTRIBUTION_EPISTEMIC_DIRECT:
        return _CONTRIBUTION_EPISTEMIC_DIRECT[raw], None
    if raw == "fact":
        return ContributionEpistemicKind.ASSERTED, "fact"
    if raw is None:
        return ContributionEpistemicKind.ASSERTED, "null"
    raise _fail(f"unsupported Buddy epistemic kind {raw!r}", "epistemic_unmapped")


def _map_acceptance(raw: str) -> AcceptanceState:
    if raw == "accepted":
        return AcceptanceState.ACCEPTED
    if raw == "rejected":
        return AcceptanceState.REJECTED
    if raw == "candidate":
        return AcceptanceState.CANDIDATE
    raise _fail(f"unsupported acceptance state {raw!r}", "acceptance_unmapped")


def _map_identity_outcome(raw: str | None) -> IdentityOutcome | None:
    if raw is None:
        return None
    try:
        return IdentityOutcome(raw)
    except ValueError as exc:
        raise _fail(f"unsupported identity outcome {raw!r}", "identity_outcome_unmapped") from exc


def _map_contributions(
    store: UnionSupergraphStore,
    contributions: list[BuddyGraphContribution],
) -> list[GraphContributionV2]:
    mapped: list[GraphContributionV2] = []
    for contribution in contributions:
        assertions: list[GraphContributionAssertionV2] = []
        epistemic_history: dict[str, str | None] = {}
        assertion_source_revisions: dict[str, str] = {}
        for assertion, _partition in (
            *((item, "candidate") for item in contribution.candidate_assertions),
            *((item, "accepted") for item in contribution.accepted_assertions),
            *((item, "rejected") for item in contribution.rejected_assertions),
        ):
            epistemic, original = _map_contribution_epistemic(assertion.epistemic_kind)
            if original is not None:
                epistemic_history[assertion.assertion_id] = None if original == "null" else original
            if assertion.source_revision_id:
                assertion_source_revisions[assertion.assertion_id] = assertion.source_revision_id
            assertions.append(
                GraphContributionAssertionV2(
                    assertion_id=assertion.assertion_id,
                    assertion_kind=str(assertion.assertion_kind),
                    subject_object_id=assertion.subject_node_id,
                    object_object_id=assertion.target_node_id,
                    predicate=assertion.predicate,
                    label=assertion.label,
                    value=_canonical_json(assertion.value) if assertion.value else None,
                    evidence_refs=[
                        _map_contribution_evidence_ref(
                            store,
                            evidence_id,
                            fallback_source_artifact_id=assertion.source_artifact_id,
                        )
                        for evidence_id in assertion.evidence_ref_ids
                    ],
                    source_artifact_id=assertion.source_artifact_id,
                    source_revision_id=None,
                    campaign_scope=assertion.campaign_scope,
                    temporal_scope=assertion.temporal_scope,
                    visibility=_map_visibility(assertion.visibility),
                    epistemic_kind=epistemic,
                    acceptance_state=_map_acceptance(assertion.acceptance_state),
                    identity_resolution_outcome=_map_identity_outcome(
                        assertion.identity_resolution_outcome
                    ),
                )
            )
        corrections = [
            GraphContributionAssertionCorrection(
                correction_kind=GraphContributionAssertionCorrectionKind(item.correction_kind),
                target_contribution_id=item.target_contribution_id,
                target_assertion_id=item.target_assertion_id,
                replacement_assertion_id=item.replacement_assertion_id,
            )
            for item in contribution.assertion_corrections
        ]
        diagnostics: dict[str, Any] = {}
        if contribution.diagnostics:
            diagnostics["buddy_diagnostics"] = list(contribution.diagnostics)
        if epistemic_history:
            diagnostics["buddy_assertion_epistemic"] = epistemic_history
        if contribution.source_revision_id:
            diagnostics["buddy_source_revision_id"] = contribution.source_revision_id
        if assertion_source_revisions:
            diagnostics["buddy_assertion_source_revision_id"] = assertion_source_revisions
        mapped.append(
            GraphContributionV2(
                contribution_id=contribution.contribution_id,
                world_id=contribution.world_id,
                source_kind=_SOURCE_KIND_MAP[contribution.source_kind],
                source_artifact_id=contribution.source_artifact_id,
                source_revision_id=None,
                extraction_profile=contribution.extraction_profile,
                produced_at=_parse_aware(contribution.produced_at, field_name="produced_at"),
                campaign_scope=contribution.campaign_scope,
                status=ContributionStatus(contribution.status),
                supersedes_contribution_id=contribution.supersedes_contribution_id,
                assertions=assertions,
                unresolved_mentions=[
                    _canonical_json(mention.model_dump(mode="json"))
                    for mention in contribution.unresolved_mentions
                ],
                identity_decision_ids=list(contribution.identity_decision_ids),
                authored_by=contribution.authored_by,
                diagnostics=diagnostics,
                assertion_corrections=corrections,
            )
        )
    return mapped


def _map_identity_decisions(
    decisions: list[BuddyIdentityDecision],
) -> list[IdentityDecisionRecordV2]:
    mapped: list[IdentityDecisionRecordV2] = []
    for decision in decisions:
        kind = IdentityDecisionKind(decision.decision_kind)
        if kind is IdentityDecisionKind.MERGE:
            subjects = list(decision.affected_node_ids)
            if decision.subject_node_id and decision.subject_node_id not in subjects:
                subjects.insert(0, decision.subject_node_id)
            if decision.target_node_id and decision.target_node_id not in subjects:
                subjects.append(decision.target_node_id)
            targets = [decision.target_node_id] if decision.target_node_id else []
            side_effects = None
            if decision.merge_side_effects is not None:
                mse = decision.merge_side_effects
                side_effects = IdentityMergeSideEffects(
                    aliases_added_to_target=list(mse.aliases_added_to_target),
                    evidence_ref_ids_added_to_target=list(mse.evidence_ref_ids_added_to_target),
                    source_domains_added_to_target=list(mse.source_domains_added_to_target),
                    alias_map_rewrites=[
                        IdentityAliasMapRewrite(
                            alias_key=rewrite.alias_key,
                            prior_owner_node_id=rewrite.prior_owner_node_id,
                            new_owner_node_id=rewrite.new_owner_node_id,
                        )
                        for rewrite in mse.alias_map_rewrites
                    ],
                )
        else:
            subjects = [decision.subject_node_id] if decision.subject_node_id else list(
                decision.affected_node_ids
            )
            targets = [decision.target_node_id] if decision.target_node_id else []
            side_effects = None
        mapped.append(
            IdentityDecisionRecordV2(
                decision_id=decision.decision_id,
                world_id=decision.world_id,
                decision_kind=kind,
                subject_object_ids=subjects,
                target_object_ids=targets,
                alias=decision.alias,
                actor=decision.actor,
                reason=decision.reason,
                reversible=decision.reversible,
                supersedes_decision_ids=list(decision.supersedes_decision_ids),
                status=IdentityDecisionStatus(decision.status),
                created_at=_parse_aware(decision.created_at, field_name="identity.created_at"),
                merge_side_effects=side_effects,
            )
        )
    return mapped


def _build_graph_payload(
    store: UnionSupergraphStore,
    overlay: UnionSupergraphStore,
    mapped_relationships: list[MappedRelationshipV2],
    package: DualSenseDecompositionPackageV1,
    artifacts: list[SourceArtifactV2],
    revisions: list[SourceRevision],
    current_by_artifact: dict[str, str | None],
) -> dict[str, Any]:
    descriptor = load_builtin_v3_descriptor()
    profile = SemanticProfileRef(
        profile_id=descriptor.profile_id,
        profile_revision=descriptor.profile_revision,
        descriptor_sha256=descriptor_sha256(descriptor),
    )
    aspects_by_node = {
        row.source_node_id: (row.aspect_key, row.projected_dm_kind)
        for row in package.decomposition_rows
    }
    objects: list[GraphObjectV6Record] = []
    required_evidence: set[str] = set()
    for node_id, overlay_node in sorted(overlay.nodes.items()):
        if overlay_node.kind == "external_resource":
            continue
        source_node = store.nodes[node_id]
        required_evidence.update(source_node.evidence_ref_ids)
        canon = _node_canon(source_node)
        aliases = [
            AliasAssertionV4Record(
                value=alias,
                assertion_metadata=_knowledge_metadata(
                    assertion_id=_alias_assertion_id(node_id, alias),
                    campaign_scope=None,
                    evidence_ref_ids=list(source_node.evidence_ref_ids),
                    session_refs=[],
                    canon_state=canon,
                ),
            )
            for alias in source_node.aliases
            if alias and alias.strip() and alias != source_node.label
        ]
        aspect_records: list[ObjectAspectAssertionV6Record] = []
        aspect = aspects_by_node.get(node_id)
        if aspect is not None:
            aspect_key, projected_kind = aspect
            aspect_records.append(
                ObjectAspectAssertionV6Record(
                    aspect_key=aspect_key,
                    kind=projected_kind,
                    assertion_metadata=_knowledge_metadata(
                        assertion_id=_aspect_assertion_id(node_id, aspect_key),
                        campaign_scope=None,
                        evidence_ref_ids=list(source_node.evidence_ref_ids),
                        session_refs=[],
                        canon_state=canon,
                    ),
                )
            )
        objects.append(
            GraphObjectV6Record(
                object_id=node_id,
                kind=_dm_kind(overlay_node.kind),
                label=source_node.label,
                assertion_metadata=_knowledge_metadata(
                    assertion_id=_object_assertion_id(node_id),
                    campaign_scope=None,
                    evidence_ref_ids=list(source_node.evidence_ref_ids),
                    session_refs=[],
                    canon_state=canon,
                ),
                aliases=aliases,
                summary=None,
                properties=[],
                aspects=aspect_records,
            )
        )
    relationships: list[GraphRelationshipV6Record] = []
    for item in mapped_relationships:
        edge = store.edges[item.edge_id]
        required_evidence.update(edge.evidence_ref_ids)
        relationships.append(
            GraphRelationshipV6Record(
                relationship_id=item.edge_id,
                source_object_id=item.source_object_id,
                target_object_id=item.target_object_id,
                predicate=item.predicate,
                assertion_metadata=_knowledge_metadata(
                    assertion_id=_relationship_assertion_id(item.edge_id),
                    campaign_scope=None,
                    evidence_ref_ids=list(edge.evidence_ref_ids),
                    session_refs=list(edge.session_ids),
                    canon_state=CanonState.CANONICAL,
                ),
                source_aspect_assertion_id=item.source_aspect_assertion_id,
                target_aspect_assertion_id=item.target_aspect_assertion_id,
            )
        )
    evidence_refs = _map_graph_evidence(store, current_by_artifact, required_evidence)
    payload = UnionGraphV6Payload(
        world_id=WORLD_ID,
        semantic_profile=profile,
        relationship_endpoint_aspect_schema=RELATIONSHIP_ENDPOINT_ASPECT_SCHEMA,
        objects=objects,
        relationships=relationships,
        evidence_refs=evidence_refs,
    )
    dumped = payload.model_dump(mode="json")
    _ = artifacts, revisions
    return dumped


def _verify_pinned_inventories(
    *,
    store: UnionSupergraphStore,
    partition: EdgePartitionV2,
    v5_semantic: int,
    v5_represented: int,
    v5_residual: int,
    effective_represented: int,
    effective_residual: int,
    effective_residual_ids: set[str],
) -> None:
    if len(store.nodes) != EXPECTED_RAW_NODE_COUNT:
        raise _fail(f"raw node count drifted: {len(store.nodes)}", "raw_node_count_mismatch")
    if len(store.edges) != EXPECTED_RAW_EDGE_COUNT:
        raise _fail(f"raw edge count drifted: {len(store.edges)}", "raw_edge_count_mismatch")
    if v5_semantic != EXPECTED_CURRENT_SEMANTIC:
        raise _fail(f"v5 semantic count drifted: {v5_semantic}", "current_semantic_count_mismatch")
    if len(partition.current_semantic_ids) != EXPECTED_CURRENT_SEMANTIC:
        raise _fail("partition current semantic count drifted", "current_semantic_count_mismatch")
    if len(partition.mechanics_ids) != EXPECTED_MECHANICS:
        raise _fail("mechanics count drifted", "mechanics_count_mismatch")
    if len(partition.history_ids) != EXPECTED_HISTORY_ONLY:
        raise _fail("history-only count drifted", "history_count_mismatch")
    if effective_represented != EXPECTED_REPRESENTED or effective_residual != EXPECTED_RESIDUAL:
        raise _fail(
            f"effective inventory drifted: {effective_represented}/{effective_residual}",
            "effective_inventory_mismatch",
        )
    if effective_residual_ids != set(DEFERRED_RESIDUAL_EDGE_IDS):
        raise _fail("canonical residual nine drifted", "residual_set_mismatch")
    if v5_represented + v5_residual != v5_semantic:
        raise _fail("v5 represented+residual != semantic", "v5_inventory_arithmetic")


def build_eldyrwild_existing_world_adoption_bundle_v2(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> EldyrwildAdoptionBundleV2Build:
    world_root = (root or world_graph_root()).resolve()
    repository = (repo or repo_root()).resolve()
    digest_before = snapshot_world_graph_tree_digest(world_root, WORLD_ID)
    vocab = load_builtin_world_object_v5_vocabulary()
    if vocabulary_sha256(vocab) != WORLD_OBJECT_V5_SHA256:
        raise _fail("world-object-v5 catalog digest drifted", "world_object_catalog_drift")
    manifest, store = _load_exact_buddy_revision(
        root=world_root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
    )
    if manifest.graph_payload_sha256 != CANONICAL_GRAPH_PAYLOAD_SHA256:
        raise _fail("source graph payload SHA drifted", "source_revision_drift")
    v5 = analyze_exact_buddy_world_revision_v5(
        root=world_root, world_id=WORLD_ID, revision_id=CANONICAL_REVISION_ID
    )
    effective = analyze_relationship_effective_conformance_v1(
        root=world_root, world_id=WORLD_ID, revision_id=CANONICAL_REVISION_ID
    )
    partition = partition_raw_stored_edges(store)
    _verify_pinned_inventories(
        store=store,
        partition=partition,
        v5_semantic=v5.relationship_semantic_count,
        v5_represented=v5.relationship_represented_count,
        v5_residual=v5.relationship_residual_count,
        effective_represented=effective.relationship_effectively_represented_count,
        effective_residual=effective.relationship_effective_residual_count,
        effective_residual_ids=set(effective.remaining_residual_edge_ids),
    )
    contributions = list_contribution_records(world_root, WORLD_ID)
    identity_decisions = list_identity_decision_records(world_root, WORLD_ID)
    false_stop = evaluate_false_stop_edges(store, contributions=contributions)
    if len(false_stop) != 16 or any(item.current_semantic for item in false_stop):
        raise _fail("prior false-STOP 16 are not all history-only", "false_stop_not_history")
    if set(item.edge_id for item in false_stop) - set(partition.history_ids):
        raise _fail("false-STOP 16 escaped history partition", "false_stop_not_history")
    mechanics = _mechanics_proofs(store, partition.mechanics_ids)
    overlay = _overlay_store(store)
    package = _load_dual_sense_package(repository)
    mapped = _map_current_relationships(store, overlay, partition, package)
    kind_repair_count = sum(1 for item in mapped if item.resolution == "kind_repair")
    aspect_count = sum(1 for item in mapped if item.resolution == "aspect_selection")
    direct_count = sum(1 for item in mapped if item.resolution == "direct_or_governed")
    if kind_repair_count != 4:
        raise _fail(f"kind-repair mapped count drifted: {kind_repair_count}", "kind_repair_count_mismatch")
    if aspect_count != 5:
        raise _fail(f"aspect-selected count drifted: {aspect_count}", "aspect_count_mismatch")
    if direct_count != EXPECTED_REPRESENTED:
        raise _fail(f"direct/governed count drifted: {direct_count}", "direct_count_mismatch")
    if KIND_REPAIR_EDGE_IDS - {item.edge_id for item in mapped if item.resolution == "kind_repair"}:
        raise _fail("kind-repair edge set drifted", "kind_repair_set_mismatch")
    residual_after_kind = set(partition.current_semantic_ids) - {
        item.edge_id for item in mapped if item.resolution != "aspect_selection"
    }
    if residual_after_kind != set(STAGE_B_REMAINING_RESIDUAL_EDGE_IDS):
        raise _fail("post-#566 residual five drifted", "post_kind_repair_residual_mismatch")
    artifacts, revisions, current_by_artifact = _map_source_artifacts(
        store,
        extra_artifact_campaigns=_contribution_artifact_ids(contributions),
    )
    graph_payload = _build_graph_payload(
        store,
        overlay,
        mapped,
        package,
        artifacts,
        revisions,
        current_by_artifact,
    )
    dm_contributions = _map_contributions(store, contributions)
    dm_identities = _map_identity_decisions(identity_decisions)
    assertion_count = sum(len(item.assertions) for item in dm_contributions)
    correction_count = sum(len(item.assertion_corrections) for item in dm_contributions)
    producer_revision = BUDDY_BASE_SHA
    bundle = ExistingWorldAdoptionBundleV2(
        schema_version=EXISTING_WORLD_ADOPTION_BUNDLE_V2_SCHEMA,
        adoption_id=ADOPTION_ID,
        world_id=WORLD_ID,
        source_provenance=ExistingWorldAdoptionSourceProvenanceV1(
            producer_id=PRODUCER_ID,
            producer_revision=producer_revision,
            source_world_revision_id=CANONICAL_REVISION_ID,
            source_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
            authority_refs=[
                ExistingWorldAdoptionAuthorityRefV1(
                    schema="dmb_world_graph_payload",
                    identifier=f"{WORLD_ID}:{CANONICAL_REVISION_ID}",
                    sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
                ),
                ExistingWorldAdoptionAuthorityRefV1(
                    schema="dmb_relationship_dual_sense_decomposition_v1",
                    identifier="relationship-dual-sense-decomposition-v1",
                    sha256=DUAL_SENSE_LOCKED_SHA256,
                ),
                ExistingWorldAdoptionAuthorityRefV1(
                    schema="dmb_eldyrwild_relationship_node_kind_source_repair_v1",
                    identifier="eldyrwild-relationship-node-kind-source-repair-v1",
                    sha256=KIND_REPAIR_LOCKED_SHA256,
                ),
                ExistingWorldAdoptionAuthorityRefV1(
                    schema="dungeonmind.dnd5e.world_object",
                    identifier="world-object-v5",
                    sha256=WORLD_OBJECT_V5_SHA256,
                ),
            ],
        ),
        graph_schema=GRAPH_SCHEMA_V6,
        graph_payload=graph_payload,
        source_artifacts=artifacts,
        source_revisions=revisions,
        contributions=dm_contributions,
        identity_decisions=dm_identities,
    )
    canonical = existing_world_adoption_bundle_v2_canonical_bytes(bundle)
    if len(canonical) > MAX_BUNDLE_BYTES:
        raise _fail(f"bundle exceeds 50 MiB: {len(canonical)}", "bundle_too_large")
    descriptor = load_builtin_v3_descriptor()
    reader = VersionedUnionGraphSnapshotReader(StaticSemanticProfileRegistry([descriptor]))
    parsed = parse_existing_world_adoption_bundle(canonical, graph_reader=reader)
    if parsed.schema_version != EXISTING_WORLD_ADOPTION_BUNDLE_V2_SCHEMA:
        raise _fail("parsed bundle schema drifted", "bundle_schema_mismatch")
    graph_relationships = list(graph_payload["relationships"])
    if len(graph_relationships) != EXPECTED_CURRENT_SEMANTIC:
        raise _fail("v6 relationship count drifted", "v6_relationship_count_mismatch")
    graph_ids = {item["relationship_id"] for item in graph_relationships}
    if graph_ids != set(partition.current_semantic_ids):
        raise _fail("v6 relationships are not exactly CURRENT_SEMANTIC", "graph_not_current_semantic")
    if graph_ids & set(partition.history_ids):
        raise _fail("history-only edge materialized in v6 graph", "history_in_graph")
    if graph_ids & set(partition.mechanics_ids):
        raise _fail("mechanics specialization coerced into generic relationships", "mechanics_in_graph")
    digest_after = snapshot_world_graph_tree_digest(world_root, WORLD_ID)
    if digest_before != digest_after:
        raise _fail("producer mutated Buddy World Graph storage", "buddy_graph_mutated")
    from dungeonmind.domain.canonical import canonical_sha256
    from dungeonmind.domain.revision_ids import compute_revision_id

    expected_revision = compute_revision_id(
        world_id=WORLD_ID,
        parent_revision_id=None,
        operation_ids=[ADOPTION_ID],
        graph_schema=GRAPH_SCHEMA_V6,
        graph_payload_sha256=canonical_sha256(graph_payload),
    )
    return EldyrwildAdoptionBundleV2Build(
        bundle=bundle,
        canonical_bytes=canonical,
        partition=partition,
        false_stop_reports=false_stop,
        mechanics_proofs=mechanics,
        mapped_relationships=mapped,
        raw_node_count=len(store.nodes),
        raw_edge_count=len(store.edges),
        current_semantic_count=len(partition.current_semantic_ids),
        represented_before_projections=effective.relationship_effectively_represented_count,
        residual_before_projections=effective.relationship_effective_residual_count,
        represented_after_kind_repair=EXPECTED_AFTER_KIND_REPAIR_REPRESENTED,
        residual_after_kind_repair=EXPECTED_AFTER_KIND_REPAIR_RESIDUAL,
        history_only_count=len(partition.history_ids),
        contribution_count=len(dm_contributions),
        assertion_count=assertion_count,
        correction_count=correction_count,
        identity_decision_count=len(dm_identities),
        v6_object_count=len(graph_payload["objects"]),
        v6_relationship_count=len(graph_relationships),
        secondary_aspect_count=sum(len(obj.get("aspects") or []) for obj in graph_payload["objects"]),
        aspect_selected_relationship_count=aspect_count,
        current_unrepresentable_count=0,
        world_graph_digest=digest_after,
        expected_published_revision_id=expected_revision,
    )


def bundle_artifact_path(repo: Path | None = None) -> Path:
    return (repo or repo_root()).resolve() / BUNDLE_RELPATH


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def write_eldyrwild_existing_world_adoption_bundle_v2(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> EldyrwildAdoptionBundleV2Build:
    built = build_eldyrwild_existing_world_adoption_bundle_v2(root=root, repo=repo)
    _write_bytes_atomic(bundle_artifact_path(repo), built.canonical_bytes)
    return built


def check_eldyrwild_existing_world_adoption_bundle_v2(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> EldyrwildAdoptionBundleV2Build:
    path = bundle_artifact_path(repo)
    if not path.is_file():
        raise _fail(f"adoption bundle artifact is missing: {path}", "artifact_missing")
    on_disk = path.read_bytes()
    built = build_eldyrwild_existing_world_adoption_bundle_v2(root=root, repo=repo)
    if on_disk != built.canonical_bytes:
        raise _fail("adoption bundle artifact is not canonical", "artifact_not_canonical")
    return built


def raw_edges_would_create_vocabulary_blockers(store: UnionSupergraphStore) -> list[str]:
    """Reproduce the invalid raw-store completeness scan that caused the STOP."""
    blockers: list[str] = []
    for edge in store.edges.values():
        if edge.predicate == _USES_STATBLOCK:
            continue
        if resolve_buddy_predicate_mapping_v4(edge.predicate) is None:
            blockers.append(edge.edge_id)
    return sorted(blockers)
