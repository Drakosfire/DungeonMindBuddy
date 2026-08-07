"""Whole Buddy World Graph → DungeonMind adoption-readiness analyzer.

Inventories one exact immutable Buddy World Graph revision, classifies every
durable semantic element against pinned DungeonMind contracts, and emits a
machine-readable adoption disposition. This is diagnostic infrastructure — not
a per-kind bridge, not product hydration, and not durable graph migration.

Completeness is derived from the serialized source payload: every durable JSON
path must receive an explicit disposition. Unknown Pydantic extras remain
unaccounted and force ``WHOLE_GRAPH_ADOPTION_NOT_READY``.
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
from dungeonmind.contracts.evidence import SourceDomain as DmSourceDomain
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
from graph_memory.evidence.source_domain import KNOWN_SOURCE_DOMAINS
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

_NODE_DECLARED_FIELDS = frozenset(
    {
        "node_id",
        "label",
        "kind",
        "role",
        "aliases",
        "source_domains",
        "evidence_ref_ids",
        "state",
        "external_resource",
    }
)
_EDGE_DECLARED_FIELDS = frozenset(
    {
        "edge_id",
        "source_node_id",
        "target_node_id",
        "predicate",
        "label",
        "direction",
        "source_domains",
        "session_ids",
        "evidence_ref_ids",
        "state",
        "threat_statblock_binding",
        "statblock_binding",
    }
)
_EVIDENCE_DECLARED_FIELDS = frozenset(
    {
        "evidence_ref_id",
        "source_artifact_id",
        "source_domain",
        "evidence_role",
        "can_open_source",
        "can_highlight_span",
        "session_id",
        "source_span_ref_id",
        "locator",
        "uri",
        "source_locator",
        "line_ref",
    }
)
_ARTIFACT_DECLARED_FIELDS = frozenset(
    {
        "schema_version",
        "source_artifact_id",
        "source_domain",
        "campaign_id",
        "session_id",
        "uri",
        "content_sha256",
        "artifact_kind",
        "document_class",
        "authority_state",
        "visibility_state",
        "world_id",
        "workspace_document_id",
        "workspace_document_revision",
        "lineage",
        "status",
        "created_at",
        "updated_at",
    }
)
_STORE_COLLECTION_KEYS = frozenset(
    {
        "nodes",
        "edges",
        "evidence",
        "source_artifacts",
        "aliases",
        "identity_redirects",
        "identity_merge_records",
        "identity_decisions",
        "assertion_support",
        "contribution_source_payload_sha256",
        "contribution_replay_manifest",
        "adjacency",
        "initialization_contribution_ids",
    }
)
_STORE_SCALAR_KEYS = frozenset(
    {
        "schema",
        "version",
        "campaign_id",
        "graph_id",
        "graph_domains",
        "source_domains",
        "focus_session_id",
        "diagnostics",
        "initialization_plan_digest",
        "initialization_attestation_digest",
    }
)
_DM_SOURCE_DOMAINS = frozenset(item.value for item in DmSourceDomain)


class SemanticClassification(StrEnum):
    EXACTLY_REPRESENTABLE = "EXACTLY_REPRESENTABLE"
    REPRESENTABLE_BY_EXPLICIT_ADAPTER = "REPRESENTABLE_BY_EXPLICIT_ADAPTER"
    DUNGEONMIND_SEMANTIC_CONTRACT_GAP = "DUNGEONMIND_SEMANTIC_CONTRACT_GAP"
    DUNGEONMIND_DURABILITY_CONTRACT_GAP = "DUNGEONMIND_DURABILITY_CONTRACT_GAP"
    SOURCE_MIGRATION_HISTORY = "SOURCE_MIGRATION_HISTORY"
    BUDDY_OPERATIONAL_ONLY = "BUDDY_OPERATIONAL_ONLY"
    INVALID_SOURCE = "INVALID_SOURCE"


# Late-bind domain map classifications now that the enum exists.
_BUDDY_TO_DM_SOURCE_DOMAIN = {
    "recap": ("session_recap", SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER),
    "worldbuilding": ("worldbuilding", SemanticClassification.EXACTLY_REPRESENTABLE),
    "manual_seed": ("manual", SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER),
}


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


# Observed durable extras (Pydantic extra="allow") with explicit dispositions.
# Truly unknown extras remain enumerated but unclassified → unaccounted > 0.
_KNOWN_NODE_EXTRA_FIELDS: dict[str, tuple[SemanticClassification, BlockerClass | None, str]] = {
    "description": (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.ATTRIBUTE_ASSERTION,
        "Buddy node.description free-text has no DM world-object prose field",
    ),
}
_KNOWN_EDGE_EXTRA_FIELDS: dict[str, tuple[SemanticClassification, BlockerClass | None, str]] = {}
_KNOWN_EVIDENCE_EXTRA_FIELDS: dict[str, tuple[SemanticClassification, BlockerClass | None, str]] = {}
_KNOWN_ARTIFACT_EXTRA_FIELDS: dict[str, tuple[SemanticClassification, BlockerClass | None, str]] = {
    "ingest_run_bundle_uri": (
        SemanticClassification.BUDDY_OPERATIONAL_ONLY,
        None,
        "ingest_run_bundle_uri is Buddy ingest operational locator",
    ),
    "provenance_index_uri": (
        SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        "provenance_index_uri has no DM SourceArtifact/SourceRevision peer",
    ),
    "source_sha256": (
        SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
        None,
        "Buddy source_sha256 → DM SourceRevision.content_sha256 adapter",
    ),
    "source_span_index_uri": (
        SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        "source_span_index_uri has no DM evidence span-index peer",
    ),
}


WholeWorldDisposition = Literal[
    "WHOLE_GRAPH_ADOPTION_READY",
    "WHOLE_GRAPH_ADOPTION_NOT_READY",
]
DurableAdoptionSeamStatus = Literal[
    "DURABLE_ADOPTION_BOUNDARY_MISSING",
    "DURABLE_ADOPTION_BOUNDARY_PRESENT",
]
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
    artifact_source_domain_inventory: list[InventoryCountRow] = Field(default_factory=list)
    evidence_source_domain_inventory: list[InventoryCountRow] = Field(default_factory=list)
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
    """Inspect pinned DungeonMind public WorldGraphRepository for adoption APIs.

    Status is derived from introspected public callables on the repository
    protocol — not hardcoded. On the current pin this correctly resolves to
    ``DURABLE_ADOPTION_BOUNDARY_MISSING`` because only get/publish/rollback
    methods exist.
    """
    repo_methods = sorted(
        name
        for name, member in inspect.getmembers(WorldGraphRepository)
        if not name.startswith("_") and callable(member)
    )
    adopt_tokens = ("adopt", "bootstrap_complete", "import_existing")
    has_adopt = any(
        any(token in name.lower() for token in adopt_tokens) for name in repo_methods
    )
    if has_adopt:
        return DurableAdoptionSeamStatusReport(
            status="DURABLE_ADOPTION_BOUNDARY_PRESENT",
            rationale=(
                "Pinned DungeonMind WorldGraphRepository exposes a public adoption/"
                "bootstrap callable; durable adoption proof may proceed against that seam."
            ),
            world_graph_repository_methods=repo_methods,
            missing_public_adoption_service=False,
        )
    return DurableAdoptionSeamStatusReport(
        status="DURABLE_ADOPTION_BOUNDARY_MISSING",
        rationale=(
            "Pinned DungeonMind WorldGraphRepository public callables are "
            f"{repo_methods}; none match adopt/bootstrap_complete/import_existing. "
            "There is no public governed adopt-existing-world service for "
            "pre-existing Buddy worlds."
        ),
        world_graph_repository_methods=repo_methods,
        missing_public_adoption_service=True,
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


def _dump_record(record: Any) -> dict[str, Any]:
    if hasattr(record, "model_dump"):
        return record.model_dump(mode="python", by_alias=True)
    if isinstance(record, dict):
        return dict(record)
    raise TypeError(f"cannot dump durable record of type {type(record)!r}")


def enumerate_durable_element_ids(store: UnionSupergraphStore) -> set[str]:
    """Enumerate durable atomic element IDs from the serialized store payload.

    Declared fields and known collections are expanded. Unknown Pydantic extras
    on nodes/edges/evidence/artifacts/store become durable paths that must be
    classified; leaving them unclassified yields ``unaccounted_durable_elements > 0``.
    """
    ids: set[str] = set()
    payload = store.model_dump(mode="python", by_alias=True)

    for key in payload:
        if key in _STORE_COLLECTION_KEYS or key in _STORE_SCALAR_KEYS:
            continue
        ids.add(f"store:extra:{key}")

    for field in _STORE_SCALAR_KEYS:
        if field in payload:
            ids.add(f"store:field:{field}")

    for node_id, node in (payload.get("nodes") or {}).items():
        for key, value in node.items():
            if key == "state":
                for state_key in (value or {}):
                    ids.add(f"node:{node_id}:state:{state_key}")
            elif key in _NODE_DECLARED_FIELDS:
                ids.add(f"node:{node_id}:field:{key}")
            else:
                ids.add(f"node:{node_id}:extra:{key}")

    for edge_id, edge in (payload.get("edges") or {}).items():
        for key, value in edge.items():
            if key == "state":
                for state_key in (value or {}):
                    ids.add(f"edge:{edge_id}:state:{state_key}")
            elif key == "session_ids":
                ids.add(f"edge:{edge_id}:field:session_ids")
            elif key in _EDGE_DECLARED_FIELDS:
                ids.add(f"edge:{edge_id}:field:{key}")
            else:
                ids.add(f"edge:{edge_id}:extra:{key}")

    for evidence_id, evidence in (payload.get("evidence") or {}).items():
        for key in evidence:
            if key in _EVIDENCE_DECLARED_FIELDS:
                ids.add(f"evidence:{evidence_id}:field:{key}")
            else:
                ids.add(f"evidence:{evidence_id}:extra:{key}")

    for artifact_id, artifact in (payload.get("source_artifacts") or {}).items():
        for key in artifact:
            if key in _ARTIFACT_DECLARED_FIELDS:
                ids.add(f"source_artifact:{artifact_id}:field:{key}")
            else:
                ids.add(f"source_artifact:{artifact_id}:extra:{key}")

    for alias_label in payload.get("aliases") or {}:
        ids.add(f"alias:{alias_label}")

    for support_id in payload.get("assertion_support") or {}:
        ids.add(f"assertion_support:{support_id}")

    for index, entry in enumerate(payload.get("contribution_replay_manifest") or []):
        contribution_id = entry.get("contribution_id", index) if isinstance(entry, dict) else index
        ids.add(f"contribution_replay:{contribution_id}:{index}")

    for contribution_id in payload.get("contribution_source_payload_sha256") or {}:
        ids.add(f"contribution_source_payload:{contribution_id}")

    for index, redirect in enumerate(payload.get("identity_redirects") or []):
        redirect_id = redirect.get("redirect_id", index) if isinstance(redirect, dict) else index
        ids.add(f"identity_redirect:{redirect_id}:{index}")

    for index, record in enumerate(payload.get("identity_merge_records") or []):
        merge_id = record.get("merge_record_id", index) if isinstance(record, dict) else index
        ids.add(f"identity_merge:{merge_id}:{index}")

    for index, decision in enumerate(payload.get("identity_decisions") or []):
        if isinstance(decision, dict):
            decision_key = decision.get("decision_id", index)
        else:
            decision_key = index
        ids.add(f"identity_decision:{decision_key}:{index}")

    for node_id in payload.get("adjacency") or {}:
        ids.add(f"store:adjacency:{node_id}")

    for index, contribution_id in enumerate(payload.get("initialization_contribution_ids") or []):
        ids.add(f"store:initialization_contribution_id:{contribution_id}:{index}")

    return ids


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


def _classify_edge_predicate(
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


def _classify_source_domain(domain: Any) -> tuple[SemanticClassification, BlockerClass | None, str]:
    value = str(domain) if domain is not None else ""
    if not value.strip():
        return (
            SemanticClassification.INVALID_SOURCE,
            BlockerClass.EVIDENCE_PROVENANCE,
            "empty source_domain",
        )
    if value in _BUDDY_TO_DM_SOURCE_DOMAIN:
        dm_domain, classification = _BUDDY_TO_DM_SOURCE_DOMAIN[value]
        if classification == SemanticClassification.EXACTLY_REPRESENTABLE:
            return classification, None, f"DM SourceDomain.{dm_domain}"
        return (
            classification,
            None,
            f"explicit adapter Buddy source_domain {value!r} → DM {dm_domain}",
        )
    if value in _DM_SOURCE_DOMAINS:
        return (
            SemanticClassification.EXACTLY_REPRESENTABLE,
            None,
            f"DM SourceDomain.{value}",
        )
    if value in KNOWN_SOURCE_DOMAINS:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            f"Buddy source_domain {value!r} has no DM SourceDomain mapping "
            f"(DM admits {sorted(_DM_SOURCE_DOMAINS)})",
        )
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        f"unknown Buddy source_domain {value!r}",
    )


def _classify_alias(alias_label: str, node_id: str) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if not alias_label.strip() or not node_id.strip():
        return SemanticClassification.INVALID_SOURCE, BlockerClass.EVIDENCE_PROVENANCE, "empty alias entry"
    return (
        SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        "Buddy label→node_id aliases lack per-object alias_assertions with evidence_ref_ids",
    )


def _classify_node_field(
    field: str,
    value: Any,
    node: UnionSupergraphNode,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field == "kind":
        return _map_buddy_node_kind(node)
    if field == "node_id":
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "Buddy node_id → DM world-object id via explicit adapter",
        )
    if field == "label":
        if isinstance(value, str) and value.strip():
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "display label"
        return SemanticClassification.INVALID_SOURCE, BlockerClass.ATTRIBUTE_ASSERTION, "empty label"
    if field == "role":
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.ATTRIBUTE_ASSERTION,
            f"Buddy role {value!r} has no DM world-object role contract",
        )
    if field == "aliases":
        return (
            SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            "node.aliases list is not DM alias_assertions-with-evidence",
        )
    if field == "source_domains":
        if not value:
            return (
                SemanticClassification.BUDDY_OPERATIONAL_ONLY,
                None,
                "empty node.source_domains",
            )
        # Worst disposition across listed domains; detailed domain gaps also
        # appear on evidence/artifact source_domain fields.
        worst = SemanticClassification.EXACTLY_REPRESENTABLE
        notes: list[str] = []
        blocker: BlockerClass | None = None
        order = [
            SemanticClassification.INVALID_SOURCE,
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            SemanticClassification.EXACTLY_REPRESENTABLE,
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            SemanticClassification.SOURCE_MIGRATION_HISTORY,
        ]
        for domain in value:
            classification, domain_blocker, note = _classify_source_domain(domain)
            notes.append(note)
            if order.index(classification) < order.index(worst):
                worst = classification
                blocker = domain_blocker
        return worst, blocker, "; ".join(notes[:3])
    if field == "evidence_ref_ids":
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "evidence_ref_ids preserved if evidence records migrate",
        )
    if field == "external_resource":
        if value is None:
            return (
                SemanticClassification.BUDDY_OPERATIONAL_ONLY,
                None,
                "absent external_resource",
            )
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "external_resource mechanics locator via #521 adapter",
        )
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.ATTRIBUTE_ASSERTION,
        f"unclassified node field {field!r}",
    )


def _classify_edge_field(
    field: str,
    value: Any,
    edge: UnionSupergraphEdge,
    store: UnionSupergraphStore,
    vocabulary: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field == "predicate":
        return _classify_edge_predicate(edge, store, vocabulary)
    if field in {"edge_id", "source_node_id", "target_node_id"}:
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            f"edge identity field {field}",
        )
    if field == "label":
        return SemanticClassification.EXACTLY_REPRESENTABLE, None, "edge display label"
    if field == "direction":
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "Buddy edge.direction → DM relationship direction adapter",
        )
    if field == "source_domains":
        if not value:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "empty edge.source_domains"
        worst = SemanticClassification.EXACTLY_REPRESENTABLE
        blocker: BlockerClass | None = None
        notes: list[str] = []
        order = [
            SemanticClassification.INVALID_SOURCE,
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            SemanticClassification.EXACTLY_REPRESENTABLE,
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            SemanticClassification.SOURCE_MIGRATION_HISTORY,
        ]
        for domain in value:
            classification, domain_blocker, note = _classify_source_domain(domain)
            notes.append(note)
            if order.index(classification) < order.index(worst):
                worst = classification
                blocker = domain_blocker
        return worst, blocker, "; ".join(notes[:3])
    if field == "session_ids":
        if value:
            return (
                SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
                BlockerClass.FICTIONAL_TIME,
                "durable session-bound relationship scope on edge.session_ids",
            )
        return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "empty edge.session_ids"
    if field == "evidence_ref_ids":
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "edge evidence_ref_ids preserved if evidence records migrate",
        )
    if field in {"threat_statblock_binding", "statblock_binding"}:
        if value is None:
            return (
                SemanticClassification.BUDDY_OPERATIONAL_ONLY,
                None,
                f"absent {field}",
            )
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            f"{field} mechanics specialization (#521 retained)",
        )
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.RELATIONSHIP_PREDICATE,
        f"unclassified edge field {field!r}",
    )


def _classify_evidence_field(
    field: str,
    value: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field == "evidence_ref_id":
        if value:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM EvidenceRef.evidence_ref_id"
        return SemanticClassification.INVALID_SOURCE, BlockerClass.EVIDENCE_PROVENANCE, "empty evidence_ref_id"
    if field == "source_artifact_id":
        if value:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM EvidenceRef.source_artifact_id"
        return (
            SemanticClassification.INVALID_SOURCE,
            BlockerClass.EVIDENCE_PROVENANCE,
            "empty source_artifact_id",
        )
    if field == "source_domain":
        return _classify_source_domain(value)
    if field == "evidence_role":
        if value == "contribution_support":
            return (
                SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
                None,
                "contribution_support→support adapter with evidence_ref preservation",
            )
        if value in {"support", "contradiction", "context"}:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM EvidenceRole"
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            f"unknown evidence_role {value!r}",
        )
    if field in {"can_open_source", "can_highlight_span"}:
        return SemanticClassification.EXACTLY_REPRESENTABLE, None, f"DM EvidenceRef.{field}"
    if field in {"locator", "uri"}:
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"absent optional {field}"
        return SemanticClassification.EXACTLY_REPRESENTABLE, None, f"DM EvidenceRef.{field}"
    if field in {"session_id", "source_span_ref_id", "source_locator", "line_ref"}:
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"absent Buddy-only {field}"
        return (
            SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            f"Buddy evidence.{field} has no DM EvidenceRef peer",
        )
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        f"unclassified evidence field {field!r}",
    )


def _classify_artifact_field(
    field: str,
    value: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field == "schema_version":
        return (
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "Buddy dmb_source_artifact_v1 schema marker",
        )
    if field == "source_artifact_id":
        if value:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM SourceArtifact.source_artifact_id"
        return (
            SemanticClassification.INVALID_SOURCE,
            BlockerClass.EVIDENCE_PROVENANCE,
            "empty source_artifact_id",
        )
    if field == "source_domain":
        return _classify_source_domain(value)
    if field in {"campaign_id", "session_id", "uri", "world_id"}:
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"absent optional {field}"
        return SemanticClassification.EXACTLY_REPRESENTABLE, None, f"DM SourceArtifact.{field}"
    if field == "content_sha256":
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "absent content_sha256"
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "Buddy content_sha256 lives on DM SourceRevision, not SourceArtifact",
        )
    if field in {"artifact_kind", "document_class"}:
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"absent {field}"
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            f"Buddy artifact.{field} has no DM SourceArtifact peer",
        )
    if field == "authority_state":
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "absent authority_state"
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "Buddy authority_state → DM SourceArtifact.authority (string) adapter",
        )
    if field == "visibility_state":
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "absent visibility_state"
        # Buddy: internal|player_safe ; DM Visibility: gm|player
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.VISIBILITY_ADMISSIBILITY,
            f"Buddy visibility_state {value!r} ≠ DM Visibility gm/player",
        )
    if field in {"workspace_document_id", "workspace_document_revision"}:
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"absent {field}"
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            f"Buddy {field} is workspace-lineage metadata with no DM SourceArtifact peer",
        )
    if field == "lineage":
        if not value:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "empty lineage"
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            "Buddy artifact.lineage has no DM SourceArtifact peer",
        )
    if field == "status":
        if value in {"active", "superseded"}:
            return (
                SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
                None,
                "Buddy status ⊂ DM SourceStatus (DM also admits retracted)",
            )
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            f"unknown artifact status {value!r}",
        )
    if field == "created_at":
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "absent created_at"
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "Buddy created_at string → DM datetime adapter",
        )
    if field == "updated_at":
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "absent updated_at"
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            "Buddy updated_at has no DM SourceArtifact peer",
        )
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        f"unclassified source_artifact field {field!r}",
    )


def _classify_store_scalar(
    field: str,
    value: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field in {"schema", "version"}:
        return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"store {field} marker"
    if field == "campaign_id":
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.CAMPAIGN_SCOPE,
            "store.campaign_id lacks explicit DM campaign ownership contract at adoption",
        )
    if field == "focus_session_id":
        return (
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "session is an operational lens, not durable fictional time",
        )
    if field == "adjacency":
        return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "derived adjacency index"
    if field == "diagnostics":
        return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "operational diagnostics envelope"
    if field in {
        "initialization_plan_digest",
        "initialization_attestation_digest",
        "initialization_contribution_ids",
    }:
        return (
            SemanticClassification.SOURCE_MIGRATION_HISTORY,
            None,
            "initialization digests/membership are migration history",
        )
    if field in {"graph_id", "graph_domains", "source_domains"}:
        return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"store.{field} operational metadata"
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.DUNGEONMIND_GRAPH_SCHEMA,
        f"unclassified store field {field!r}",
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
            "Preserve Buddy evidence_ref/source span/domain fields in DM evidence contracts.",
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
            "Classify or remove unknown durable extras before adoption.",
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

    expected_ids = enumerate_durable_element_ids(store)
    classified: list[ClassifiedElement] = []
    buckets: dict[tuple[SemanticClassification, str], MappingBucket] = {}

    store_payload = store.model_dump(mode="python", by_alias=True)

    for node_id, node in store.nodes.items():
        node_dump = _dump_record(node)
        for field, value in node_dump.items():
            if field == "state":
                for state_key, state_value in (value or {}).items():
                    element_id = f"node:{node_id}:state:{state_key}"
                    f_class, f_blocker, f_note = _classify_state_field(state_key, state_value)
                    _append_classification(
                        classified=classified,
                        buckets=buckets,
                        element_id=element_id,
                        element_family="node_state",
                        classification=f_class,
                        blocker_class=f_blocker,
                        note=f_note,
                    )
                continue
            if field in _NODE_DECLARED_FIELDS:
                element_id = f"node:{node_id}:field:{field}"
                f_class, f_blocker, f_note = _classify_node_field(field, value, node)
                _append_classification(
                    classified=classified,
                    buckets=buckets,
                    element_id=element_id,
                    element_family="node_field",
                    classification=f_class,
                    blocker_class=f_blocker,
                    note=f_note,
                )
                continue
            if field in _KNOWN_NODE_EXTRA_FIELDS:
                f_class, f_blocker, f_note = _KNOWN_NODE_EXTRA_FIELDS[field]
                _append_classification(
                    classified=classified,
                    buckets=buckets,
                    element_id=f"node:{node_id}:extra:{field}",
                    element_family="node_extra",
                    classification=f_class,
                    blocker_class=f_blocker,
                    note=f_note,
                )
            # else: unknown extra stays unaccounted

    for edge_id, edge in store.edges.items():
        edge_dump = _dump_record(edge)
        for field, value in edge_dump.items():
            if field == "state":
                for state_key, state_value in (value or {}).items():
                    element_id = f"edge:{edge_id}:state:{state_key}"
                    f_class, f_blocker, f_note = _classify_state_field(state_key, state_value)
                    _append_classification(
                        classified=classified,
                        buckets=buckets,
                        element_id=element_id,
                        element_family="edge_state",
                        classification=f_class,
                        blocker_class=f_blocker,
                        note=f_note,
                    )
                continue
            if field in _EDGE_DECLARED_FIELDS:
                element_id = f"edge:{edge_id}:field:{field}"
                f_class, f_blocker, f_note = _classify_edge_field(
                    field, value, edge, store, vocabulary
                )
                family = "edge_temporal" if field == "session_ids" and value else "edge_field"
                _append_classification(
                    classified=classified,
                    buckets=buckets,
                    element_id=element_id,
                    element_family=family,
                    classification=f_class,
                    blocker_class=f_blocker,
                    note=f_note,
                )
                continue
            if field in _KNOWN_EDGE_EXTRA_FIELDS:
                f_class, f_blocker, f_note = _KNOWN_EDGE_EXTRA_FIELDS[field]
                _append_classification(
                    classified=classified,
                    buckets=buckets,
                    element_id=f"edge:{edge_id}:extra:{field}",
                    element_family="edge_extra",
                    classification=f_class,
                    blocker_class=f_blocker,
                    note=f_note,
                )

    for evidence_id, evidence in store.evidence.items():
        evidence_dump = _dump_record(evidence)
        for field, value in evidence_dump.items():
            if field in _EVIDENCE_DECLARED_FIELDS:
                element_id = f"evidence:{evidence_id}:field:{field}"
                f_class, f_blocker, f_note = _classify_evidence_field(field, value)
                _append_classification(
                    classified=classified,
                    buckets=buckets,
                    element_id=element_id,
                    element_family="evidence_field",
                    classification=f_class,
                    blocker_class=f_blocker,
                    note=f_note,
                )
                continue
            if field in _KNOWN_EVIDENCE_EXTRA_FIELDS:
                f_class, f_blocker, f_note = _KNOWN_EVIDENCE_EXTRA_FIELDS[field]
                _append_classification(
                    classified=classified,
                    buckets=buckets,
                    element_id=f"evidence:{evidence_id}:extra:{field}",
                    element_family="evidence_extra",
                    classification=f_class,
                    blocker_class=f_blocker,
                    note=f_note,
                )

    for artifact_id, artifact in store.source_artifacts.items():
        artifact_dump = _dump_record(artifact)
        for field, value in artifact_dump.items():
            if field in _ARTIFACT_DECLARED_FIELDS:
                element_id = f"source_artifact:{artifact_id}:field:{field}"
                f_class, f_blocker, f_note = _classify_artifact_field(field, value)
                _append_classification(
                    classified=classified,
                    buckets=buckets,
                    element_id=element_id,
                    element_family="source_artifact_field",
                    classification=f_class,
                    blocker_class=f_blocker,
                    note=f_note,
                )
                continue
            if field in _KNOWN_ARTIFACT_EXTRA_FIELDS:
                f_class, f_blocker, f_note = _KNOWN_ARTIFACT_EXTRA_FIELDS[field]
                _append_classification(
                    classified=classified,
                    buckets=buckets,
                    element_id=f"source_artifact:{artifact_id}:extra:{field}",
                    element_family="source_artifact_extra",
                    classification=f_class,
                    blocker_class=f_blocker,
                    note=f_note,
                )

    for alias_label, node_id in store.aliases.items():
        alias_id = f"alias:{alias_label}"
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
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=f"assertion_support:{support_id}",
            element_family="assertion_support",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
            note="assertion_support is reconstruction ledger; survival requires genesis policy + adoption seam",
        )

    for index, entry in enumerate(store.contribution_replay_manifest):
        entry_id = f"contribution_replay:{entry.contribution_id}:{index}"
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
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=f"contribution_source_payload:{contribution_id}",
            element_family="contribution_source_payload",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
            note="contribution source digest participates in genesis vs history policy",
        )

    for index, redirect in enumerate(store.identity_redirects):
        redirect_key = getattr(redirect, "redirect_id", None)
        if redirect_key is None and isinstance(redirect, dict):
            redirect_key = redirect.get("redirect_id", index)
        rid = f"identity_redirect:{redirect_key}:{index}"
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
        merge_key = getattr(record, "merge_record_id", None)
        if merge_key is None and isinstance(record, dict):
            merge_key = record.get("merge_record_id", index)
        mid = f"identity_merge:{merge_key}:{index}"
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
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=did,
            element_family="identity_decision",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
            note="identity decision history",
        )

    for field_name in _STORE_SCALAR_KEYS:
        if field_name not in store_payload:
            continue
        value = store_payload[field_name]
        classification, blocker, note = _classify_store_scalar(field_name, value)
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=f"store:field:{field_name}",
            element_family="store_field",
            classification=classification,
            blocker_class=blocker,
            note=note,
        )

    for node_id in store.adjacency:
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=f"store:adjacency:{node_id}",
            element_family="store_field",
            classification=SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            blocker_class=None,
            note="derived adjacency index entry",
        )

    for index, contribution_id in enumerate(store.initialization_contribution_ids):
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=f"store:initialization_contribution_id:{contribution_id}:{index}",
            element_family="store_field",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
            note="initialization contribution membership is migration history",
        )

    classified_ids = {item.element_id for item in classified}
    unaccounted_ids = sorted(expected_ids - classified_ids)
    orphan_classified = sorted(classified_ids - expected_ids)
    unaccounted = len(unaccounted_ids) + len(orphan_classified)

    kind_counter = Counter(node.kind for node in store.nodes.values())
    predicate_counter = Counter(edge.predicate for edge in store.edges.values())
    state_counter = _inventory_state_fields(store)
    artifact_domain_counter = Counter(
        str(getattr(artifact, "source_domain", "")) for artifact in store.source_artifacts.values()
    )
    evidence_domain_counter = Counter(
        str(getattr(evidence, "source_domain", "")) for evidence in store.evidence.values()
    )

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
    if unaccounted_ids or orphan_classified:
        blockers.append(
            AdoptionBlocker(
                blocker_class=BlockerClass.SOURCE_INTEGRITY,
                count=unaccounted,
                examples=(unaccounted_ids + orphan_classified)[:_REPRESENTATIVE_ID_LIMIT],
                responsible_repo="DungeonMindBuddy",
                smallest_next_change=(
                    "Every durable serialized path must receive an explicit disposition; "
                    "unknown extras cannot remain unaccounted."
                ),
            )
        )
    if seam.status == "DURABLE_ADOPTION_BOUNDARY_MISSING":
        blockers.append(
            AdoptionBlocker(
                blocker_class=BlockerClass.DURABLE_ADOPTION_BOUNDARY,
                count=1,
                examples=[
                    "WorldGraphRepository methods: "
                    + ", ".join(seam.world_graph_repository_methods)
                ],
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
    ) or seam.status == "DURABLE_ADOPTION_BOUNDARY_MISSING" or unaccounted > 0
    disposition: WholeWorldDisposition = (
        "WHOLE_GRAPH_ADOPTION_NOT_READY" if blocking else "WHOLE_GRAPH_ADOPTION_READY"
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
            "durable_element_paths": len(expected_ids),
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
        artifact_source_domain_inventory=[
            InventoryCountRow(key=domain, count=count)
            for domain, count in sorted(artifact_domain_counter.items())
        ],
        evidence_source_domain_inventory=[
            InventoryCountRow(key=domain, count=count)
            for domain, count in sorted(evidence_domain_counter.items())
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
            "semantic gaps (including source_domain vocabulary), alias/evidence "
            "durability gaps, contribution history, and the missing DungeonMind "
            "durable adoption seam."
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
