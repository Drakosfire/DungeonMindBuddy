"""Whole Buddy World Graph → DungeonMind adoption-readiness analyzer.

Inventories one exact immutable Buddy World Graph revision, classifies every
durable semantic element against pinned DungeonMind contracts, and emits a
machine-readable adoption disposition. This is diagnostic infrastructure — not
a per-kind bridge, not product hydration, and not durable graph migration.
"""

from __future__ import annotations

import hashlib
import inspect
from collections import Counter, defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from dungeonmind.application.repositories import WorldGraphRepository
from dungeonmind.application.semantic_profiles import descriptor_sha256
from dungeonmind.contracts.graph import StoredGraphRevision
from dungeonmind.contracts.vocabulary import CanonState, EpistemicKind, Visibility
from dungeonmind_dnd.application.world_object_vocabulary import (
    WORLD_OBJECT_VOCABULARY_ID,
    WORLD_OBJECT_VOCABULARY_REVISION,
    load_builtin_v3_descriptor,
    load_builtin_world_object_vocabulary,
    vocabulary_sha256,
)
from pydantic import BaseModel, ConfigDict, Field

import graph_memory.kernel as kernel
from graph_memory.kernel.world_projection import WorldGraphProjectionError
from graph_memory.union_supergraph.model import (
    UnionSupergraphEdge,
    UnionSupergraphNode,
    UnionSupergraphStore,
)

WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA = "dmb_dungeonmind_whole_world_conformance_report_v1"
_DUNGEONMIND_DEPENDENCY_REF = "8095321ed011b8a38640615a90cbc9efaf385e8c"
_REPRESENTATIVE_ID_LIMIT = 5
_BUDDY_TO_DM_KIND: dict[str, str] = {
    "threat": "dnd5e:threat",
    "npc": "dnd5e:npc",
    "pc": "dnd5e:player_character",
    "creature": "dnd5e:creature",
    "location": "dnd5e:location",
    "faction": "dnd5e:faction",
    "encounter": "dnd5e:encounter",
}
_SEMANTIC_GAP_KINDS = frozenset({"item", "mystery", "group", "party", "event"})
_BUDDY_PREDICATE_TO_DM: dict[str, str] = {
    "member_of": "dnd5e:member_of",
    "participates_in": "dnd5e:participates_in",
    "threatens": "dnd5e:threatens",
}
_USES_STATBLOCK = "uses_statblock"
_LOCATED_IN = "located_in"


class SemanticClassification(StrEnum):
    EXACTLY_REPRESENTABLE = "EXACTLY_REPRESENTABLE"
    REPRESENTABLE_BY_EXPLICIT_ADAPTER = "REPRESENTABLE_BY_EXPLICIT_ADAPTER"
    DUNGEONMIND_SEMANTIC_CONTRACT_GAP = "DUNGEONMIND_SEMANTIC_CONTRACT_GAP"
    DUNGEONMIND_DURABILITY_CONTRACT_GAP = "DUNGEONMIND_DURABILITY_CONTRACT_GAP"
    SOURCE_MIGRATION_HISTORY = "SOURCE_MIGRATION_HISTORY"
    BUDDY_OPERATIONAL_ONLY = "BUDDY_OPERATIONAL_ONLY"
    INVALID_SOURCE = "INVALID_SOURCE"


class BlockerClass(StrEnum):
    WORLD_OBJECT_KIND = "WORLD_OBJECT_KIND"
    RELATIONSHIP_PREDICATE = "RELATIONSHIP_PREDICATE"
    ATTRIBUTE_ASSERTION = "ATTRIBUTE_ASSERTION"
    EVIDENCE_PROVENANCE = "EVIDENCE_PROVENANCE"
    CAMPAIGN_SCOPE = "CAMPAIGN_SCOPE"
    VISIBILITY_ADMISSIBILITY = "VISIBILITY_ADMISSIBILITY"
    EPISTEMIC_STATE = "EPISTEMIC_STATE"
    FICTIONAL_TIME = "FICTIONAL_TIME"
    IDENTITY_HISTORY = "IDENTITY_HISTORY"
    CONTRIBUTION_HISTORY = "CONTRIBUTION_HISTORY"
    MECHANICS_ATTACHMENT = "MECHANICS_ATTACHMENT"
    DUNGEONMIND_PROFILE = "DUNGEONMIND_PROFILE"
    DUNGEONMIND_GRAPH_SCHEMA = "DUNGEONMIND_GRAPH_SCHEMA"
    DURABLE_ADOPTION_BOUNDARY = "DURABLE_ADOPTION_BOUNDARY"
    POSTGRES_ADOPTION = "POSTGRES_ADOPTION"
    SOURCE_INTEGRITY = "SOURCE_INTEGRITY"


WholeWorldDisposition = Literal[
    "WHOLE_GRAPH_ADOPTION_READY",
    "WHOLE_GRAPH_ADOPTION_NOT_READY",
]
DurableAdoptionSeamStatus = Literal["DURABLE_ADOPTION_BOUNDARY_MISSING"]
PostgresAdoptionStatus = Literal["NOT_EXERCISED", "BLOCKED"]


class WholeWorldConformanceError(Exception):
    """Fail-closed whole-graph adoption error."""

    def __init__(self, message: str, *, report: WholeWorldConformanceReport | None = None) -> None:
        super().__init__(message)
        self.report = report


class InventoryCountRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    count: int


class ClassifiedElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    element_family: str
    classification: SemanticClassification
    blocker_class: BlockerClass | None = None
    note: str | None = None


class MappingBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: SemanticClassification
    element_family: str
    count: int
    representative_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AdoptionBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocker_class: BlockerClass
    count: int
    examples: list[str] = Field(default_factory=list)
    responsible_repo: Literal["DungeonMind", "DungeonMindBuddy"]
    smallest_next_change: str


class DurableAdoptionSeamStatusReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: DurableAdoptionSeamStatus
    rationale: str
    world_graph_repository_methods: list[str] = Field(default_factory=list)
    missing_public_adoption_service: bool = True


class WholeWorldConformanceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_dungeonmind_whole_world_conformance_report_v1"] = (
        WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA
    )
    source_world_id: str
    source_revision_id: str
    source_graph_payload_sha256: str
    source_campaign_id: str
    dungeonmind_dependency_ref: str
    semantic_profile_id: str
    semantic_profile_revision: str
    semantic_profile_descriptor_sha256: str
    world_object_vocabulary_id: str
    world_object_vocabulary_revision: str
    world_object_vocabulary_sha256: str
    inventory: dict[str, int]
    kind_inventory: list[InventoryCountRow]
    predicate_inventory: list[InventoryCountRow]
    state_family_inventory: list[InventoryCountRow]
    mapping_buckets: list[MappingBucket]
    blockers: list[AdoptionBlocker]
    disposition: WholeWorldDisposition
    durable_adoption_seam: DurableAdoptionSeamStatusReport
    postgres_status: PostgresAdoptionStatus
    mechanics_specialization_retained: bool = True
    adoption_genesis_policy_note: str
    unaccounted_durable_elements: int
    classified_elements_count: int
    uses_statblock_mechanics_count: int
    located_in_gap_count: int


def snapshot_world_graph_tree_digest(root: Path, world_id: str) -> str:
    """Deterministic digest of the on-disk world storage tree (read-only proof)."""
    world_root = (root / "graph_memory" / "worlds" / world_id).resolve()
    if not world_root.is_dir():
        # Legacy/test layouts occasionally omit the graph_memory prefix.
        world_root = (root / "worlds" / world_id).resolve()
    digest = hashlib.sha256()
    if not world_root.is_dir():
        digest.update(b"missing-world-tree")
        return digest.hexdigest()
    for path in sorted(p for p in world_root.rglob("*") if p.is_file()):
        rel = path.relative_to(world_root).as_posix().encode("utf-8")
        digest.update(rel)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def inspect_dungeonmind_durable_adoption_seam() -> DurableAdoptionSeamStatusReport:
    """Inspect pinned DungeonMind public contracts for governed whole-world adoption."""
    repo_methods = [
        name
        for name, member in inspect.getmembers(WorldGraphRepository)
        if not name.startswith("_")
    ]
    public_methods = sorted(
        {
            "get_head",
            "get_revision",
            "publish_revision",
            "rollback_head",
        }
    )
    missing_adopt = not any(
        token in name.lower()
        for name in repo_methods
        for token in ("adopt", "bootstrap_complete", "import_existing")
    )
    return DurableAdoptionSeamStatusReport(
        status="DURABLE_ADOPTION_BOUNDARY_MISSING",
        rationale=(
            "Pinned DungeonMind exposes WorldGraphRepository get/put-style publication "
            "only; there is no public governed adopt-existing-world or "
            "bootstrap-complete-revision service for pre-existing Buddy worlds."
        ),
        world_graph_repository_methods=public_methods,
        missing_public_adoption_service=missing_adopt,
    )


def _load_exact_buddy_revision(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
) -> tuple[kernel.WorldGraphRevision, UnionSupergraphStore]:
    try:
        store = kernel.load_world_graph_revision_with_integrity(root, world_id, revision_id)
    except WorldGraphProjectionError as exc:
        code = getattr(exc, "code", "") or ""
        if code in {"revision_not_found"}:
            raise WholeWorldConformanceError(
                f"exact Buddy revision not found: {revision_id!r}",
            ) from exc
        raise WholeWorldConformanceError(
            f"source revision failed integrity validation: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise WholeWorldConformanceError(
            f"source revision failed integrity validation: {exc}",
        ) from exc

    try:
        manifest = kernel.load_world_graph_revision_manifest(root, world_id, revision_id)
    except Exception as exc:  # noqa: BLE001
        raise WholeWorldConformanceError(
            f"revision manifest could not be loaded after integrity attestation: {exc}",
        ) from exc

    if manifest.world_id != world_id:
        raise WholeWorldConformanceError(
            "requested world_id does not match revision manifest world_id",
        )
    return manifest, store


def _map_buddy_node_kind(node: UnionSupergraphNode) -> tuple[SemanticClassification, BlockerClass | None, str]:
    kind = node.kind
    if not isinstance(kind, str) or not kind.strip():
        return SemanticClassification.INVALID_SOURCE, BlockerClass.WORLD_OBJECT_KIND, "empty kind"
    if kind == "external_resource":
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "mechanics resource locator via #521 adapter; not a world-object kind",
        )
    if kind in _SEMANTIC_GAP_KINDS:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.WORLD_OBJECT_KIND,
            f"Buddy kind {kind!r} has no world-object-v1 term",
        )
    if kind in _BUDDY_TO_DM_KIND:
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            f"explicit adapter {_BUDDY_TO_DM_KIND[kind]}",
        )
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.WORLD_OBJECT_KIND,
        f"unknown Buddy kind {kind!r}",
    )


def _dm_kind_for_buddy_kind(buddy_kind: str) -> str | None:
    return _BUDDY_TO_DM_KIND.get(buddy_kind)


def _endpoint_dm_kinds(
    store: UnionSupergraphStore,
    node_id: str,
) -> tuple[str | None, str | None]:
    node = store.nodes.get(node_id)
    if node is None:
        return None, "missing_node"
    if node.kind == "external_resource":
        return None, "external_resource"
    dm_kind = _dm_kind_for_buddy_kind(node.kind)
    if dm_kind is None and node.kind in _SEMANTIC_GAP_KINDS:
        return None, node.kind
    return dm_kind, node.kind


def _predicate_allowed_endpoints(
    dm_predicate: str,
    vocabulary: Any,
) -> tuple[frozenset[str], frozenset[str]] | None:
    for predicate in vocabulary.predicates:
        if predicate.term == dm_predicate:
            return frozenset(predicate.subject_kinds), frozenset(predicate.object_kinds)
    return None


def _classify_edge(
    edge: UnionSupergraphEdge,
    store: UnionSupergraphStore,
    vocabulary: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    predicate = edge.predicate
    if predicate == _USES_STATBLOCK:
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "uses_statblock mechanics specialization (#521 retained; not dnd5e:threatens)",
        )
    if predicate == _LOCATED_IN:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            "located_in has no accepted rename contract to dnd5e:located_at",
        )
    dm_predicate = _BUDDY_PREDICATE_TO_DM.get(predicate)
    if dm_predicate is None:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            f"predicate {predicate!r} has no explicit DM adapter",
        )

    allowed = _predicate_allowed_endpoints(dm_predicate, vocabulary)
    if allowed is None:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            f"DM vocabulary missing predicate {dm_predicate}",
        )
    subject_kinds, object_kinds = allowed
    src_dm, src_note = _endpoint_dm_kinds(store, edge.source_node_id)
    tgt_dm, tgt_note = _endpoint_dm_kinds(store, edge.target_node_id)
    if src_dm is None or tgt_dm is None:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            f"{predicate} endpoint kind mismatch ({src_note} -> {tgt_note})",
        )
    if src_dm not in subject_kinds or tgt_dm not in object_kinds:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            f"{predicate} endpoint kinds {src_dm}/{tgt_dm} not admitted for {dm_predicate}",
        )
    return (
        SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
        None,
        f"explicit adapter {dm_predicate}",
    )


def _classify_state_field(field: str, value: Any) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field == "visibility":
        if value in {Visibility.GM.value, Visibility.PLAYER.value}:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM Visibility"
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.VISIBILITY_ADMISSIBILITY,
            f"unknown visibility {value!r}",
        )
    if field == "canon_state":
        if value in {CanonState.CANONICAL.value, CanonState.PROVISIONAL.value, CanonState.RETRACTED.value}:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM CanonState"
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.ATTRIBUTE_ASSERTION,
            f"unknown canon_state {value!r}",
        )
    if field == "epistemic_kind":
        if value in {EpistemicKind.ASSERTED.value, EpistemicKind.INFERRED.value, EpistemicKind.SPECULATIVE.value}:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM EpistemicKind"
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.EPISTEMIC_STATE,
            f"Buddy epistemic vocabulary {value!r} is not coerced into DM EpistemicKind",
        )
    if field == "campaign_scope":
        if isinstance(value, str) and value.strip():
            return (
                SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
                BlockerClass.CAMPAIGN_SCOPE,
                "Buddy campaign_scope lacks explicit DM campaign/scope field contract",
            )
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.CAMPAIGN_SCOPE,
            "empty campaign_scope",
        )
    if field in {
        "approval_state",
        "memory_state",
        "support_state",
        "identity_canon_state",
        "introduced_by_contribution_id",
    }:
        return (
            SemanticClassification.SOURCE_MIGRATION_HISTORY,
            None,
            "contribution/reconstruction lifecycle field",
        )
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.ATTRIBUTE_ASSERTION,
        f"unclassified state field {field!r}",
    )


def _classify_evidence(evidence: Any) -> tuple[SemanticClassification, BlockerClass | None, str]:
    role = getattr(evidence, "evidence_role", None)
    if role == "contribution_support":
        note = "contribution_support→support adapter acceptable with evidence_ref preservation"
        classification = SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER
    elif role in {"support", "contradiction", "context"}:
        classification = SemanticClassification.EXACTLY_REPRESENTABLE
        note = "DM EvidenceRole"
    else:
        classification = SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP
        note = f"unknown evidence_role {role!r}"

    missing: list[str] = []
    for field in ("evidence_ref_id", "source_artifact_id"):
        if not getattr(evidence, field, None):
            missing.append(field)
    buddy_only = ("session_id", "source_span_ref_id", "line_ref", "source_locator")
    for field in buddy_only:
        if getattr(evidence, field, None) is not None:
            missing.append(f"buddy_field:{field}")
    if missing:
        return (
            SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            f"evidence field gap: {', '.join(missing)}",
        )
    if classification == SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP:
        return classification, BlockerClass.EVIDENCE_PROVENANCE, note
    return classification, None, note


def _classify_alias(alias_label: str, node_id: str) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if not alias_label.strip() or not node_id.strip():
        return SemanticClassification.INVALID_SOURCE, BlockerClass.EVIDENCE_PROVENANCE, "empty alias entry"
    return (
        SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        "Buddy label→node_id aliases lack per-object alias_assertions with evidence_ref_ids",
    )


def _append_classification(
    *,
    classified: list[ClassifiedElement],
    buckets: dict[tuple[SemanticClassification, str], MappingBucket],
    element_id: str,
    element_family: str,
    classification: SemanticClassification,
    blocker_class: BlockerClass | None,
    note: str | None,
) -> None:
    classified.append(
        ClassifiedElement(
            element_id=element_id,
            element_family=element_family,
            classification=classification,
            blocker_class=blocker_class,
            note=note,
        )
    )
    key = (classification, element_family)
    bucket = buckets.get(key)
    if bucket is None:
        bucket = MappingBucket(
            classification=classification,
            element_family=element_family,
            count=0,
        )
        buckets[key] = bucket
    bucket.count += 1
    if len(bucket.representative_ids) < _REPRESENTATIVE_ID_LIMIT:
        bucket.representative_ids.append(element_id)
    if note and note not in bucket.notes:
        bucket.notes.append(note)


def _inventory_state_fields(store: UnionSupergraphStore) -> Counter[str]:
    counter: Counter[str] = Counter()
    for node in store.nodes.values():
        for field in (node.state or {}).keys():
            counter[f"node.state.{field}"] += 1
    for edge in store.edges.values():
        for field in (edge.state or {}).keys():
            counter[f"edge.state.{field}"] += 1
        if edge.session_ids:
            counter["edge.session_ids"] += 1
    return counter


_BLOCKING_CLASSIFICATIONS = frozenset(
    {
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
        SemanticClassification.INVALID_SOURCE,
    }
)


def _build_blockers(classified: list[ClassifiedElement]) -> list[AdoptionBlocker]:
    grouped: dict[BlockerClass, list[str]] = defaultdict(list)
    for item in classified:
        if item.blocker_class is None:
            continue
        # Only gap/invalid classifications become element-level blockers.
        # Adapters and migration-history are accounted without blocking inflation.
        if item.classification not in _BLOCKING_CLASSIFICATIONS:
            continue
        grouped[item.blocker_class].append(item.element_id)

    responsible: dict[BlockerClass, tuple[str, str]] = {
        BlockerClass.WORLD_OBJECT_KIND: (
            "DungeonMind",
            "Extend world-object-v1 or publish explicit Buddy→DM kind adapters with ADR.",
        ),
        BlockerClass.RELATIONSHIP_PREDICATE: (
            "DungeonMind",
            "Add governed predicate contracts or explicit rename adapters.",
        ),
        BlockerClass.ATTRIBUTE_ASSERTION: (
            "DungeonMindBuddy",
            "Materialize attribute values or document DM assertion transport.",
        ),
        BlockerClass.EVIDENCE_PROVENANCE: (
            "DungeonMind",
            "Preserve Buddy evidence_ref/source span fields in DM evidence contracts.",
        ),
        BlockerClass.CAMPAIGN_SCOPE: (
            "DungeonMind",
            "Define DM campaign/scope field for Buddy campaign_scope.",
        ),
        BlockerClass.VISIBILITY_ADMISSIBILITY: (
            "DungeonMindBuddy",
            "Normalize visibility values before adoption.",
        ),
        BlockerClass.EPISTEMIC_STATE: (
            "DungeonMind",
            "Add Buddy epistemic vocabulary mapping or extend DM EpistemicKind.",
        ),
        BlockerClass.FICTIONAL_TIME: (
            "DungeonMind",
            "Define durable fictional-time transport for edge session_ids.",
        ),
        BlockerClass.IDENTITY_HISTORY: (
            "DungeonMindBuddy",
            "Expose governed identity migration replay at adoption seam.",
        ),
        BlockerClass.CONTRIBUTION_HISTORY: (
            "DungeonMind",
            "Add durable adopt-existing-world seam with contribution genesis policy.",
        ),
        BlockerClass.MECHANICS_ATTACHMENT: (
            "DungeonMindBuddy",
            "Retain #521 mechanics bindings via explicit adapter (already bridged per-object).",
        ),
        BlockerClass.DUNGEONMIND_PROFILE: (
            "DungeonMind",
            "Publish semantic profile / vocabulary revisions with migration notes.",
        ),
        BlockerClass.DUNGEONMIND_GRAPH_SCHEMA: (
            "DungeonMind",
            "Define whole-graph payload schema for adopted revisions.",
        ),
        BlockerClass.DURABLE_ADOPTION_BOUNDARY: (
            "DungeonMind",
            "Add public adopt-existing-world / bootstrap-complete-revision service.",
        ),
        BlockerClass.POSTGRES_ADOPTION: (
            "DungeonMind",
            "Exercise Postgres adoption only after public seam exists.",
        ),
        BlockerClass.SOURCE_INTEGRITY: (
            "DungeonMindBuddy",
            "Repair source revision integrity before adoption.",
        ),
    }

    blockers: list[AdoptionBlocker] = []
    for blocker_class, examples in sorted(grouped.items(), key=lambda item: item[0].value):
        repo, next_change = responsible[blocker_class]
        blockers.append(
            AdoptionBlocker(
                blocker_class=blocker_class,
                count=len(examples),
                examples=examples[:_REPRESENTATIVE_ID_LIMIT],
                responsible_repo=repo,  # type: ignore[arg-type]
                smallest_next_change=next_change,
            )
        )
    return blockers


def analyze_exact_buddy_world_revision(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
) -> WholeWorldConformanceReport:
    """Inventory and classify one exact Buddy World Graph revision."""
    manifest, store = _load_exact_buddy_revision(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    profile = load_builtin_v3_descriptor()
    vocabulary = load_builtin_world_object_vocabulary()
    seam = inspect_dungeonmind_durable_adoption_seam()

    classified: list[ClassifiedElement] = []
    buckets: dict[tuple[SemanticClassification, str], MappingBucket] = {}
    expected_counts: Counter[str] = Counter()

    for node_id, node in store.nodes.items():
        expected_counts["node"] += 1
        classification, blocker, note = _map_buddy_node_kind(node)
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=node_id,
            element_family="node",
            classification=classification,
            blocker_class=blocker,
            note=note,
        )
        for field, value in (node.state or {}).items():
            field_id = f"node:{node_id}:state:{field}"
            expected_counts["node_state"] += 1
            f_class, f_blocker, f_note = _classify_state_field(field, value)
            _append_classification(
                classified=classified,
                buckets=buckets,
                element_id=field_id,
                element_family="node_state",
                classification=f_class,
                blocker_class=f_blocker,
                note=f_note,
            )

    for edge_id, edge in store.edges.items():
        expected_counts["edge"] += 1
        classification, blocker, note = _classify_edge(edge, store, vocabulary)
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=edge_id,
            element_family="edge",
            classification=classification,
            blocker_class=blocker,
            note=note,
        )
        for field, value in (edge.state or {}).items():
            field_id = f"edge:{edge_id}:state:{field}"
            expected_counts["edge_state"] += 1
            f_class, f_blocker, f_note = _classify_state_field(field, value)
            _append_classification(
                classified=classified,
                buckets=buckets,
                element_id=field_id,
                element_family="edge_state",
                classification=f_class,
                blocker_class=f_blocker,
                note=f_note,
            )
        if edge.session_ids:
            sid = f"edge:{edge_id}:session_ids"
            expected_counts["edge_temporal"] += 1
            _append_classification(
                classified=classified,
                buckets=buckets,
                element_id=sid,
                element_family="edge_temporal",
                classification=SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
                blocker_class=BlockerClass.FICTIONAL_TIME,
                note="durable session-bound relationship scope on edge.session_ids",
            )

    for evidence_id, evidence in store.evidence.items():
        expected_counts["evidence"] += 1
        classification, blocker, note = _classify_evidence(evidence)
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=evidence_id,
            element_family="evidence",
            classification=classification,
            blocker_class=blocker,
            note=note,
        )

    for artifact_id in store.source_artifacts:
        expected_counts["source_artifact"] += 1
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=artifact_id,
            element_family="source_artifact",
            classification=SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            blocker_class=None,
            note="source artifact identity is adapter-representable; body authority stays with Buddy URIs",
        )

    for alias_label, node_id in store.aliases.items():
        alias_id = f"alias:{alias_label}"
        expected_counts["alias"] += 1
        classification, blocker, note = _classify_alias(alias_label, node_id)
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=alias_id,
            element_family="alias",
            classification=classification,
            blocker_class=blocker,
            note=note,
        )

    for support_id in store.assertion_support:
        expected_counts["assertion_support"] += 1
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=support_id,
            element_family="assertion_support",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
            note="assertion_support is reconstruction ledger; survival requires genesis policy + adoption seam",
        )

    for index, entry in enumerate(store.contribution_replay_manifest):
        entry_id = f"contribution_replay:{entry.contribution_id}:{index}"
        expected_counts["contribution_replay"] += 1
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=entry_id,
            element_family="contribution_replay",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
            note="historical contribution chain cannot be silently discarded at adoption",
        )

    for contribution_id in store.contribution_source_payload_sha256:
        cid = f"contribution_source_payload:{contribution_id}"
        expected_counts["contribution_source_payload"] += 1
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=cid,
            element_family="contribution_source_payload",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
            note="contribution source digest participates in genesis vs history policy",
        )

    for index, redirect in enumerate(store.identity_redirects):
        rid = f"identity_redirect:{getattr(redirect, 'redirect_id', index)}:{index}"
        expected_counts["identity_redirect"] += 1
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=rid,
            element_family="identity_redirect",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
            note="identity redirect history",
        )

    for index, record in enumerate(store.identity_merge_records):
        mid = f"identity_merge:{getattr(record, 'merge_record_id', index)}:{index}"
        expected_counts["identity_merge"] += 1
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=mid,
            element_family="identity_merge",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
            note="identity merge history",
        )

    for index, decision in enumerate(store.identity_decisions):
        if isinstance(decision, dict):
            decision_key = decision.get("decision_id", index)
        else:
            decision_key = getattr(decision, "decision_id", index)
        did = f"identity_decision:{decision_key}:{index}"
        expected_counts["identity_decision"] += 1
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=did,
            element_family="identity_decision",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
            note="identity decision history",
        )

    top_level_fields: list[tuple[str, Any, SemanticClassification, BlockerClass | None, str]] = [
        (
            "focus_session_id",
            store.focus_session_id,
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "session is an operational lens, not durable fictional time",
        ),
        (
            "adjacency",
            store.adjacency,
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "derived adjacency index",
        ),
        (
            "diagnostics",
            store.diagnostics,
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "operational diagnostics envelope",
        ),
        (
            "initialization_plan_digest",
            store.initialization_plan_digest,
            SemanticClassification.SOURCE_MIGRATION_HISTORY,
            None,
            "initialization digests are migration history",
        ),
        (
            "initialization_attestation_digest",
            store.initialization_attestation_digest,
            SemanticClassification.SOURCE_MIGRATION_HISTORY,
            None,
            "initialization digests are migration history",
        ),
        (
            "initialization_contribution_ids",
            store.initialization_contribution_ids,
            SemanticClassification.SOURCE_MIGRATION_HISTORY,
            None,
            "initialization contribution membership is migration history",
        ),
        (
            "graph_id",
            store.graph_id,
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "nullable graph_id is operational metadata",
        ),
        (
            "graph_domains",
            store.graph_domains,
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "empty graph_domains list is operational metadata",
        ),
        (
            "source_domains",
            store.source_domains,
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "empty source_domains list is operational metadata",
        ),
    ]
    for field_name, _value, classification, blocker, note in top_level_fields:
        field_id = f"store:{field_name}"
        expected_counts["store_field"] += 1
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=field_id,
            element_family="store_field",
            classification=classification,
            blocker_class=blocker,
            note=note,
        )

    classified_counts = Counter(item.element_family for item in classified)
    unaccounted = sum(
        max(0, expected_counts[family] - classified_counts.get(family, 0))
        for family in expected_counts
    ) + sum(
        max(0, classified_counts[family] - expected_counts.get(family, 0))
        for family in classified_counts
        if family not in expected_counts
    )

    kind_counter = Counter(node.kind for node in store.nodes.values())
    predicate_counter = Counter(edge.predicate for edge in store.edges.values())
    state_counter = _inventory_state_fields(store)

    blockers = _build_blockers(classified)
    history_count = sum(
        1
        for item in classified
        if item.classification == SemanticClassification.SOURCE_MIGRATION_HISTORY
    )
    if history_count:
        blockers.append(
            AdoptionBlocker(
                blocker_class=BlockerClass.CONTRIBUTION_HISTORY,
                count=history_count,
                examples=[
                    item.element_id
                    for item in classified
                    if item.classification == SemanticClassification.SOURCE_MIGRATION_HISTORY
                ][:_REPRESENTATIVE_ID_LIMIT],
                responsible_repo="DungeonMind",
                smallest_next_change=(
                    "Decide genesis policy A/B/C and add a durable adoption seam that "
                    "preserves Buddy contribution/assertion reconstruction history."
                ),
            )
        )
    if seam.status == "DURABLE_ADOPTION_BOUNDARY_MISSING":
        blockers.append(
            AdoptionBlocker(
                blocker_class=BlockerClass.DURABLE_ADOPTION_BOUNDARY,
                count=1,
                examples=["WorldGraphRepository lacks adopt-existing-world API"],
                responsible_repo="DungeonMind",
                smallest_next_change=(
                    "Add public governed adopt-existing-world / bootstrap-complete-revision service."
                ),
            )
        )
        blockers.append(
            AdoptionBlocker(
                blocker_class=BlockerClass.POSTGRES_ADOPTION,
                count=1,
                examples=["Postgres adoption not exercised"],
                responsible_repo="DungeonMind",
                smallest_next_change="Exercise Postgres adoption only after public seam exists.",
            )
        )

    blocking = any(
        item.classification in _BLOCKING_CLASSIFICATIONS for item in classified
    ) or seam.status == "DURABLE_ADOPTION_BOUNDARY_MISSING"
    disposition: WholeWorldDisposition = (
        "WHOLE_GRAPH_ADOPTION_NOT_READY" if blocking or unaccounted else "WHOLE_GRAPH_ADOPTION_READY"
    )

    uses_statblock_count = sum(
        1 for edge in store.edges.values() if edge.predicate == _USES_STATBLOCK
    )
    located_in_gap_count = sum(
        1 for edge in store.edges.values() if edge.predicate == _LOCATED_IN
    )

    return WholeWorldConformanceReport(
        source_world_id=world_id,
        source_revision_id=manifest.revision_id,
        source_graph_payload_sha256=manifest.graph_payload_sha256,
        source_campaign_id=store.campaign_id,
        dungeonmind_dependency_ref=_DUNGEONMIND_DEPENDENCY_REF,
        semantic_profile_id=profile.profile_id,
        semantic_profile_revision=profile.profile_revision,
        semantic_profile_descriptor_sha256=descriptor_sha256(profile),
        world_object_vocabulary_id=WORLD_OBJECT_VOCABULARY_ID,
        world_object_vocabulary_revision=WORLD_OBJECT_VOCABULARY_REVISION,
        world_object_vocabulary_sha256=vocabulary_sha256(vocabulary),
        inventory={
            "nodes": len(store.nodes),
            "edges": len(store.edges),
            "evidence": len(store.evidence),
            "source_artifacts": len(store.source_artifacts),
            "aliases": len(store.aliases),
            "assertion_support": len(store.assertion_support),
            "contribution_replay_manifest": len(store.contribution_replay_manifest),
        },
        kind_inventory=[
            InventoryCountRow(key=kind, count=count)
            for kind, count in sorted(kind_counter.items())
        ],
        predicate_inventory=[
            InventoryCountRow(key=predicate, count=count)
            for predicate, count in sorted(predicate_counter.items())
        ],
        state_family_inventory=[
            InventoryCountRow(key=field, count=count)
            for field, count in sorted(state_counter.items())
        ],
        mapping_buckets=sorted(
            buckets.values(),
            key=lambda bucket: (bucket.classification.value, bucket.element_family),
        ),
        blockers=sorted(blockers, key=lambda blocker: blocker.blocker_class.value),
        disposition=disposition,
        durable_adoption_seam=seam,
        postgres_status="BLOCKED",
        mechanics_specialization_retained=True,
        adoption_genesis_policy_note=(
            "Genesis policies A/B/C remain undecided for execution. Option B "
            "(versioned one-time adoption record + new DM contribution chain) is "
            "the likely future policy, but historical Buddy contribution chains "
            "cannot be silently discarded. Full adoption is blocked today by "
            "semantic gaps, alias/evidence durability gaps, and the missing "
            "DungeonMind durable adoption seam."
        ),
        unaccounted_durable_elements=unaccounted,
        classified_elements_count=len(classified),
        uses_statblock_mechanics_count=uses_statblock_count,
        located_in_gap_count=located_in_gap_count,
    )


def build_exact_dungeonmind_adoption_revision(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
) -> StoredGraphRevision:
    """Build a DM StoredGraphRevision only when whole-graph adoption is READY.

    This PR refuses lossy/partial construction. When the analyzer reports
    ``WHOLE_GRAPH_ADOPTION_READY``, complete ``dm_union_graph_v3`` construction
    still requires a follow-on mapper that preserves every accounted family;
    until that exists we fail closed rather than emit a misleading stub graph.
    """
    report = analyze_exact_buddy_world_revision(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    if report.disposition != "WHOLE_GRAPH_ADOPTION_READY":
        raise WholeWorldConformanceError(
            "whole-graph adoption is NOT_READY; refusing partial adoption revision",
            report=report,
        )
    raise WholeWorldConformanceError(
        "WHOLE_GRAPH_ADOPTION_READY was reported but complete dm_union_graph_v3 "
        "target construction is not implemented in this diagnostic PR; refusing "
        "lossy partial construction",
        report=report,
    )
