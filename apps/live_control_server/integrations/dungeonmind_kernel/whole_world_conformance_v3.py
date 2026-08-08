"""Whole Buddy World Graph → DungeonMind v5 adoption-readiness analyzer (v3).

Post-v28 pin against ``dm_union_graph_v5``, world-object-v3 vocabulary,
world-property-v1, and v2 evidence/source-artifact contracts. Additive vs v2 —
diagnostic infrastructure only; not migration.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from dungeonmind.application.graph_snapshot import GRAPH_SCHEMA_V5
from dungeonmind.application.semantic_profiles import descriptor_sha256
from dungeonmind.contracts.evidence import (
    EVIDENCE_REF_V2_SCHEMA,
    SOURCE_ARTIFACT_V2_SCHEMA,
    SourceReviewState,
)
from dungeonmind.contracts.knowledge_assertion import (
    KNOWLEDGE_ASSERTION_METADATA_SCHEMA,
    EpistemicKindV2,
)
from dungeonmind.contracts.vocabulary import CanonState, Visibility
from dungeonmind_dnd.application.world_object_vocabulary import (
    builtin_world_object_v3_vocabulary_ref,
    load_builtin_v3_descriptor,
    load_builtin_world_object_v3_vocabulary,
    vocabulary_sha256,
)
from dungeonmind_dnd.application.world_property_vocabulary import (
    builtin_world_property_vocabulary_ref,
    load_builtin_world_property_vocabulary,
    validate_world_property_assignment,
    world_property_vocabulary_sha256,
)
from dungeonmind_dnd.domain.errors import DndCandidateValidationError
from pydantic import BaseModel, ConfigDict, Field

from graph_memory.evidence.source_domain import KNOWN_SOURCE_DOMAINS
from graph_memory.union_supergraph.model import (
    UnionSupergraphEdge,
    UnionSupergraphNode,
    UnionSupergraphStore,
)

from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    AdoptionBlocker,
    BlockerClass,
    ClassifiedElement,
    DurableAdoptionSeamStatusReport,
    InventoryCountRow,
    MappingBucket,
    PostgresAdoptionStatus,
    SemanticClassification,
    WholeWorldConformanceError,
    _ARTIFACT_DECLARED_FIELDS,
    _EDGE_DECLARED_FIELDS,
    _EVIDENCE_DECLARED_FIELDS,
    _KNOWN_ARTIFACT_EXTRA_FIELDS,
    _KNOWN_EDGE_EXTRA_FIELDS,
    _KNOWN_EVIDENCE_EXTRA_FIELDS,
    _KNOWN_NODE_EXTRA_FIELDS,
    _NODE_DECLARED_FIELDS,
    _REPRESENTATIVE_ID_LIMIT,
    _STORE_SCALAR_KEYS,
    _append_classification,
    _build_blockers,
    _dump_record,
    _inventory_state_fields,
    _load_exact_buddy_revision,
    _predicate_allowed_endpoints,
    enumerate_durable_element_ids,
    inspect_dungeonmind_durable_adoption_seam,
)

WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V3 = (
    "dmb_dungeonmind_whole_world_conformance_report_v3"
)
_DUNGEONMIND_DEPENDENCY_REF_V3 = "03ec801db99959153283312b72c13fafe56c54d1"

_BUDDY_TO_DM_KIND: dict[str, str] = {
    "threat": "dnd5e:threat",
    "npc": "dnd5e:npc",
    "pc": "dnd5e:player_character",
    "creature": "dnd5e:creature",
    "location": "dnd5e:location",
    "faction": "dnd5e:faction",
    "encounter": "dnd5e:encounter",
    "item": "dnd5e:item",
    "mystery": "dnd5e:mystery",
    "group": "dnd5e:group",
    "party": "dnd5e:party",
    "event": "dnd5e:event",
}

# Direct Buddy predicate → dnd5e:<same> (no generic f"dnd5e:{pred}" fallback).
_DIRECT_PREDICATE_MAP: frozenset[str] = frozenset(
    {
        "allied_with",
        "associated_with",
        "attacks",
        "aware_of",
        "carries",
        "causes",
        "commands",
        "contains",
        "cooperates_with",
        "displaced_from",
        "holds",
        "knows_about",
        "leads",
        "leads_to",
        "located_in",
        "member_of",
        "near",
        "owns",
        "parent_of",
        "part_of",
        "participates_in",
        "possesses",
        "present_at",
        "pursues",
        "recruits_for",
        "rivals",
        "serves",
        "south_of",
        "suspects",
        "threatens",
        "travels_to",
        "trusts",
        "works_with",
    }
)

_RENAME_PREDICATE_MAP: dict[str, str] = {
    "appeared_in": "dnd5e:present_at",
    "linked_to": "dnd5e:associated_with",
    "occurred_at": "dnd5e:occurs_at",
    "participated_in": "dnd5e:participates_in",
    "path_to": "dnd5e:leads_to",
    "results_in": "dnd5e:causes",
    "routes_to": "dnd5e:leads_to",
    "sublocation_of": "dnd5e:part_of",
    "within": "dnd5e:located_in",
}

# Buddy pred → (dm_term, reverse_endpoints). Only belongs_to uses reverse.
_REVERSE_ENDPOINT_PREDICATE_MAP: dict[str, tuple[str, bool]] = {
    "belongs_to": ("dnd5e:owns", True),
}

_INTENTIONALLY_UNRESOLVED_PREDICATES: frozenset[str] = frozenset(
    {
        "carries_report_to",
        "controls_comms_with",
        "defends_weakened_location",
        "identified_as",
        "mission_targets",
        "objective_of",
        "part_of_group",
        "reports_threat_in",
        "same_as",
    }
)

_USES_STATBLOCK = "uses_statblock"

# Known exception: must remain residual even if endpoints admit.
_KNOWN_RESIDUAL_EXCEPTION_EDGE_IDS: frozenset[str] = frozenset(
    {
        "edge:npc_lysandra:threatens:node:cultists_of_longmont:is-threatened-by-cultists",
    }
)

# Full-edge direction audit: reverse-qualifier patterns in edge_id (casefold).
_DIRECTION_REVERSE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "threatens": (
        re.compile(r"is-threatened-by", re.IGNORECASE),
        re.compile(r"threatened-by", re.IGNORECASE),
    ),
    "attacks": (
        re.compile(r"is-attacked-by", re.IGNORECASE),
        re.compile(r"attacked-by", re.IGNORECASE),
    ),
    "owns": (
        re.compile(r"is-owned-by", re.IGNORECASE),
        re.compile(r"owned-by", re.IGNORECASE),
    ),
    "contains": (
        re.compile(r"is-contained-in", re.IGNORECASE),
        re.compile(r"is-contained-by", re.IGNORECASE),
    ),
    "leads": (
        re.compile(r"is-led-by", re.IGNORECASE),
        re.compile(r"led-by", re.IGNORECASE),
    ),
    "commands": (
        re.compile(r"is-commanded-by", re.IGNORECASE),
        re.compile(r"commanded-by", re.IGNORECASE),
    ),
    "serves": (
        re.compile(r"is-served-by", re.IGNORECASE),
        re.compile(r"served-by", re.IGNORECASE),
    ),
    "parent_of": (
        re.compile(r"is-child-of", re.IGNORECASE),
        re.compile(r"child-of", re.IGNORECASE),
    ),
    "causes": (
        re.compile(r"is-caused-by", re.IGNORECASE),
        re.compile(r"caused-by", re.IGNORECASE),
    ),
}

_EPISTEMIC_KIND_V2_VALUES = frozenset(item.value for item in EpistemicKindV2)
_AUTHORITY_REVIEW_VALUES = frozenset(item.value for item in SourceReviewState)

_BUDDY_TO_DM_SOURCE_DOMAIN_V3: dict[str, tuple[str, SemanticClassification]] = {
    "recap": ("session_recap", SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER),
    "worldbuilding": ("worldbuilding", SemanticClassification.EXACTLY_REPRESENTABLE),
    "manual_seed": ("manual", SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER),
}

_PRESERVE_KEY_NULL_DOMAIN = frozenset({"statblock", "party_registry"})


class PredicateDisposition(StrEnum):
    EXISTING_EXPLICIT_ADAPTER = "EXISTING_EXPLICIT_ADAPTER"
    MECHANICS_SPECIALIZATION = "MECHANICS_SPECIALIZATION"
    ENDPOINT_ADMISSION_GAP = "ENDPOINT_ADMISSION_GAP"
    SEMANTIC_ADJUDICATION_REQUIRED = "SEMANTIC_ADJUDICATION_REQUIRED"
    INVALID_SOURCE = "INVALID_SOURCE"


WholeWorldDispositionV3 = Literal[
    "WHOLE_GRAPH_ADOPTION_READY",
    "WHOLE_GRAPH_ADOPTION_NOT_READY",
]


class RelationshipEndpointPairInventoryRowV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_buddy_kind: str
    target_buddy_kind: str
    count: int
    target_dungeonmind_term: str | None = None
    reverse_endpoints: bool = False
    represented_count: int = 0
    residual_count: int = 0
    representative_edge_ids: list[str] = Field(default_factory=list)


class RelationshipPredicateInventoryRowV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    buddy_predicate: str
    count: int
    represented_count: int = 0
    residual_count: int = 0
    mechanics_count: int = 0
    endpoint_pairs: list[RelationshipEndpointPairInventoryRowV3] = Field(default_factory=list)


class PropertyGapValueCountRowV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    count: int


class PropertyGapObjectKindCountRowV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_kind: str
    count: int


class PropertyGapInventoryRowV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str
    value_counts: list[PropertyGapValueCountRowV1] = Field(default_factory=list)
    object_kind_counts: list[PropertyGapObjectKindCountRowV1] = Field(default_factory=list)


class WholeWorldConformanceReportV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_dungeonmind_whole_world_conformance_report_v3"] = (
        WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V3
    )
    source_world_id: str
    source_revision_id: str
    source_graph_payload_sha256: str
    source_campaign_id: str
    dungeonmind_dependency_ref: str
    target_graph_schema: str
    source_artifact_schema: str
    evidence_schema: str
    assertion_metadata_schema: str
    semantic_profile_id: str
    semantic_profile_revision: str
    semantic_profile_descriptor_sha256: str
    world_object_vocabulary_id: str
    world_object_vocabulary_revision: str
    world_object_vocabulary_sha256: str
    world_property_vocabulary_id: str
    world_property_vocabulary_revision: str
    world_property_vocabulary_sha256: str
    inventory: dict[str, int]
    kind_inventory: list[InventoryCountRow]
    predicate_inventory: list[InventoryCountRow]
    relationship_predicate_inventory: list[RelationshipPredicateInventoryRowV3]
    residual_by_predicate: list[InventoryCountRow] = Field(default_factory=list)
    state_family_inventory: list[InventoryCountRow]
    artifact_source_domain_inventory: list[InventoryCountRow] = Field(default_factory=list)
    evidence_source_domain_inventory: list[InventoryCountRow] = Field(default_factory=list)
    property_gap_inventory: list[PropertyGapInventoryRowV1] = Field(default_factory=list)
    classification_inventory: list[InventoryCountRow] = Field(default_factory=list)
    mapping_buckets: list[MappingBucket] = Field(default_factory=list)
    blockers: list[AdoptionBlocker]
    disposition: WholeWorldDispositionV3
    durable_adoption_seam: DurableAdoptionSeamStatusReport
    postgres_status: PostgresAdoptionStatus
    mechanics_specialization_retained: bool = True
    adoption_genesis_policy_note: str
    unaccounted_durable_elements: int
    classified_elements_count: int
    relationship_semantic_count: int
    relationship_represented_count: int
    relationship_residual_count: int
    uses_statblock_mechanics_count: int
    role_field_count: int
    role_property_adapter_count: int
    role_external_resource_count: int
    role_residual_count: int


def compact_whole_world_conformance_report_v3(
    report: WholeWorldConformanceReportV3,
) -> dict[str, Any]:
    """Durable diagnostic JSON: full residual ledger without mapping_buckets."""
    payload = report.model_dump(mode="json")
    payload.pop("mapping_buckets", None)
    return payload


def resolve_buddy_predicate_mapping_v3(
    buddy_predicate: str,
) -> tuple[str | None, bool] | None:
    """Return (dm_term, reverse_endpoints) for an explicit v3 map, else None.

    Intentionally unresolved / mechanics / unknown predicates return None.
    Does not invent ``dnd5e:{pred}`` or ``dnd5e:related_to``.
    """
    if buddy_predicate == _USES_STATBLOCK:
        return None
    if buddy_predicate in _INTENTIONALLY_UNRESOLVED_PREDICATES:
        return None
    if buddy_predicate in _REVERSE_ENDPOINT_PREDICATE_MAP:
        return _REVERSE_ENDPOINT_PREDICATE_MAP[buddy_predicate]
    if buddy_predicate in _RENAME_PREDICATE_MAP:
        return _RENAME_PREDICATE_MAP[buddy_predicate], False
    if buddy_predicate in _DIRECT_PREDICATE_MAP:
        return f"dnd5e:{buddy_predicate}", False
    return None


def edge_has_reverse_direction_qualifier_v3(
    *,
    buddy_predicate: str,
    edge_id: str,
) -> bool:
    """True when edge_id contains a reverse-qualifier pattern for the Buddy predicate."""
    patterns = _DIRECTION_REVERSE_PATTERNS.get(buddy_predicate)
    if not patterns:
        return False
    return any(pattern.search(edge_id) for pattern in patterns)


def _classification_inventory(
    classified: list[ClassifiedElement],
) -> list[InventoryCountRow]:
    counter = Counter(item.classification.value for item in classified)
    return [
        InventoryCountRow(key=key, count=count)
        for key, count in sorted(counter.items())
    ]


def _dm_kind_for_buddy_kind(buddy_kind: str) -> str | None:
    return _BUDDY_TO_DM_KIND.get(buddy_kind)


def _endpoint_dm_kinds(
    store: UnionSupergraphStore,
    node_id: str,
) -> tuple[str | None, str]:
    node = store.nodes.get(node_id)
    if node is None:
        return None, "missing_node"
    if node.kind == "external_resource":
        return None, "external_resource"
    dm_kind = _dm_kind_for_buddy_kind(node.kind)
    if dm_kind is None:
        return None, node.kind
    return dm_kind, node.kind


def _map_buddy_node_kind_v3(
    node: UnionSupergraphNode,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    kind = node.kind
    if not isinstance(kind, str) or not kind.strip():
        return SemanticClassification.INVALID_SOURCE, BlockerClass.WORLD_OBJECT_KIND, "empty kind"
    if kind == "external_resource":
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "mechanics resource locator via #521 adapter; not a world-object kind",
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


def _classify_state_field_v3(
    field: str,
    value: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field == "visibility":
        if value in {Visibility.GM.value, Visibility.PLAYER.value}:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM Visibility"
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.VISIBILITY_ADMISSIBILITY,
            f"unknown operational visibility {value!r}",
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
        if value in _EPISTEMIC_KIND_V2_VALUES:
            return (
                SemanticClassification.EXACTLY_REPRESENTABLE,
                None,
                f"DM EpistemicKindV2.{value} (no coercion from v1 enum)",
            )
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.EPISTEMIC_STATE,
            f"unknown epistemic_kind {value!r} for EpistemicKindV2",
        )
    if field == "campaign_scope":
        if value is None:
            return (
                SemanticClassification.EXACTLY_REPRESENTABLE,
                None,
                "Buddy campaign_scope=null → KnowledgeAssertionMetadataV1.campaign_scope=null "
                "(world-universal)",
            )
        if isinstance(value, str) and value.strip():
            return (
                SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
                None,
                "Buddy campaign_scope → KnowledgeAssertionMetadataV1.campaign_scope",
            )
        return (
            SemanticClassification.INVALID_SOURCE,
            BlockerClass.CAMPAIGN_SCOPE,
            "empty or malformed campaign_scope",
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


def _classify_source_domain_v3(
    domain: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    value = str(domain) if domain is not None else ""
    if not value.strip():
        return (
            SemanticClassification.INVALID_SOURCE,
            BlockerClass.EVIDENCE_PROVENANCE,
            "empty source_domain",
        )
    if value in _PRESERVE_KEY_NULL_DOMAIN:
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            f"source_domain_key={value!r}; source_domain=null (v2 lossless; no domain=other)",
        )
    if value in _BUDDY_TO_DM_SOURCE_DOMAIN_V3:
        dm_domain, classification = _BUDDY_TO_DM_SOURCE_DOMAIN_V3[value]
        if classification == SemanticClassification.EXACTLY_REPRESENTABLE:
            return (
                classification,
                None,
                f"source_domain_key={value!r}; DM SourceDomain.{dm_domain}",
            )
        return (
            classification,
            None,
            f"source_domain_key={value!r}; explicit adapter → DM {dm_domain}",
        )
    if value in KNOWN_SOURCE_DOMAINS:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            f"preserve source_domain_key={value!r}; no accepted generic source_domain adapter",
        )
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        f"unknown Buddy source_domain {value!r}; preserve key if adopted",
    )


def _classify_edge_predicate_v3(
    edge: UnionSupergraphEdge,
    store: UnionSupergraphStore,
    vocabulary: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str, PredicateDisposition, str | None, bool]:
    """Classify one edge predicate.

    Returns classification, blocker, note, disposition, mapped_dm_term, reverse_endpoints.
    """
    predicate = edge.predicate
    if predicate == _USES_STATBLOCK:
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "uses_statblock mechanics specialization (#521 retained; not a DM relationship)",
            PredicateDisposition.MECHANICS_SPECIALIZATION,
            None,
            False,
        )

    if edge.edge_id in _KNOWN_RESIDUAL_EXCEPTION_EDGE_IDS:
        mapped = resolve_buddy_predicate_mapping_v3(predicate)
        mapped_term = mapped[0] if mapped else None
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            (
                f"known residual exception {edge.edge_id!r}: reverse-looking "
                f"{predicate} requires SEMANTIC_ADJUDICATION_REQUIRED"
            ),
            PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED,
            mapped_term,
            False,
        )

    if predicate in _INTENTIONALLY_UNRESOLVED_PREDICATES:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            f"intentionally unresolved predicate {predicate!r}; no target DM term",
            PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED,
            None,
            False,
        )

    mapping = resolve_buddy_predicate_mapping_v3(predicate)
    if mapping is None:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            f"predicate {predicate!r} has no explicit DM adapter "
            "(no generic dnd5e: fallback)",
            PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED,
            None,
            False,
        )

    dm_predicate, reverse_endpoints = mapping

    # Direction audit for edges selected for automatic translation.
    if (
        edge.edge_id not in _KNOWN_RESIDUAL_EXCEPTION_EDGE_IDS
        and edge_has_reverse_direction_qualifier_v3(
            buddy_predicate=predicate,
            edge_id=edge.edge_id,
        )
    ):
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            (
                f"edge_id {edge.edge_id!r} has reverse-direction qualifier for "
                f"{predicate}; SEMANTIC_ADJUDICATION_REQUIRED"
            ),
            PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED,
            dm_predicate,
            reverse_endpoints,
        )

    allowed = _predicate_allowed_endpoints(dm_predicate, vocabulary)
    if allowed is None:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            f"world-object-v3 vocabulary missing predicate {dm_predicate}",
            PredicateDisposition.SEMANTIC_ADJUDICATION_REQUIRED,
            dm_predicate,
            reverse_endpoints,
        )
    subject_kinds, object_kinds = allowed
    src_dm, src_note = _endpoint_dm_kinds(store, edge.source_node_id)
    tgt_dm, tgt_note = _endpoint_dm_kinds(store, edge.target_node_id)
    if reverse_endpoints:
        # item belongs_to npc → check npc owns item (swap admission endpoints).
        admit_src, admit_tgt = tgt_dm, src_dm
        admit_src_note, admit_tgt_note = tgt_note, src_note
    else:
        admit_src, admit_tgt = src_dm, tgt_dm
        admit_src_note, admit_tgt_note = src_note, tgt_note

    if admit_src is None or admit_tgt is None:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            (
                f"{predicate}→{dm_predicate} endpoint kind mismatch "
                f"({admit_src_note} -> {admit_tgt_note})"
                + (" [reverse_endpoints]" if reverse_endpoints else "")
            ),
            PredicateDisposition.ENDPOINT_ADMISSION_GAP,
            dm_predicate,
            reverse_endpoints,
        )
    if admit_src not in subject_kinds or admit_tgt not in object_kinds:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.RELATIONSHIP_PREDICATE,
            (
                f"{predicate}→{dm_predicate} endpoint kinds {admit_src}/{admit_tgt} "
                f"not admitted"
                + (" [reverse_endpoints]" if reverse_endpoints else "")
            ),
            PredicateDisposition.ENDPOINT_ADMISSION_GAP,
            dm_predicate,
            reverse_endpoints,
        )
    note = f"explicit adapter {dm_predicate}"
    if reverse_endpoints:
        note = f"explicit reverse-endpoint adapter {predicate}→{dm_predicate}"
    return (
        SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
        None,
        note,
        PredicateDisposition.EXISTING_EXPLICIT_ADAPTER,
        dm_predicate,
        reverse_endpoints,
    )


def _classify_node_role_v3(
    node: UnionSupergraphNode,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    kind = node.kind
    role_value = node.role

    if kind == "external_resource":
        external = node.external_resource
        resource_type = getattr(external, "resource_type", None) if external is not None else None
        if (
            role_value == "statblock"
            and external is not None
            and resource_type == "statblock"
        ):
            return (
                SemanticClassification.BUDDY_OPERATIONAL_ONLY,
                None,
                "external_resource role=statblock duplicates mechanics resource_type; "
                "no dnd5e:role emitted",
            )
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.ATTRIBUTE_ASSERTION,
            (
                f"external_resource role/resource_type mismatch "
                f"(role={role_value!r}, resource_type={resource_type!r}); fail closed"
            ),
        )

    dm_kind = _dm_kind_for_buddy_kind(kind)
    if dm_kind is None:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.ATTRIBUTE_ASSERTION,
            f"Buddy role {role_value!r} on unmapped kind {kind!r}",
        )

    try:
        validate_world_property_assignment(
            property_term="dnd5e:role",
            subject_kind=dm_kind,
            value=role_value,
        )
    except DndCandidateValidationError as exc:
        return (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            BlockerClass.ATTRIBUTE_ASSERTION,
            f"dnd5e:role validation failed for {dm_kind}: {exc}",
        )
    return (
        SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
        None,
        f"Buddy role → dnd5e:role exact string on {dm_kind} (no normalization)",
    )


def _classify_node_field_v3(
    field: str,
    value: Any,
    node: UnionSupergraphNode,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field == "kind":
        return _map_buddy_node_kind_v3(node)
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
        return _classify_node_role_v3(node)
    if field == "aliases":
        return _classify_node_aliases_field_v3(node)
    if field == "source_domains":
        if not value:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "empty node.source_domains"
        return _worst_domain_classification(value, _classify_source_domain_v3)
    if field == "evidence_ref_ids":
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "evidence_ref_ids preserved if evidence records migrate",
        )
    if field == "external_resource":
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "absent external_resource"
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


def _worst_domain_classification(
    domains: list[Any],
    classifier: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
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
    for domain in domains:
        classification, domain_blocker, note = classifier(domain)
        notes.append(note)
        if order.index(classification) < order.index(worst):
            worst = classification
            blocker = domain_blocker
    return worst, blocker, "; ".join(notes[:3])


def _classify_edge_field_v3(
    field: str,
    value: Any,
    edge: UnionSupergraphEdge,
    store: UnionSupergraphStore,
    vocabulary: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field == "predicate":
        classification, blocker, note, _, _, _ = _classify_edge_predicate_v3(
            edge, store, vocabulary
        )
        return classification, blocker, note
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
        return _worst_domain_classification(value, _classify_source_domain_v3)
    if field == "session_ids":
        if value:
            return (
                SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
                None,
                "edge.session_ids → KnowledgeAssertionMetadataV1.session_refs "
                "(real-world sessions; temporal_scope remains unknown)",
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
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"absent {field}"
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


def _classify_evidence_field_v3(
    field: str,
    value: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field == "evidence_ref_id":
        if value:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM EvidenceRefV2.evidence_ref_id"
        return SemanticClassification.INVALID_SOURCE, BlockerClass.EVIDENCE_PROVENANCE, "empty evidence_ref_id"
    if field == "source_artifact_id":
        if value:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM EvidenceRefV2.source_artifact_id"
        return (
            SemanticClassification.INVALID_SOURCE,
            BlockerClass.EVIDENCE_PROVENANCE,
            "empty source_artifact_id",
        )
    if field == "source_domain":
        return _classify_source_domain_v3(value)
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
        return SemanticClassification.EXACTLY_REPRESENTABLE, None, f"DM EvidenceRefV2.{field}"
    if field in {"locator", "uri", "session_id", "source_span_ref_id", "source_locator", "line_ref"}:
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"absent optional {field}"
        return SemanticClassification.EXACTLY_REPRESENTABLE, None, f"DM EvidenceRefV2.{field}"
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        f"unclassified evidence field {field!r}",
    )


def _classify_artifact_field_v3(
    field: str,
    value: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field == "schema_version":
        return (
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "Buddy dmb_source_artifact_v1 schema marker (v2 target dm_source_artifact_v2)",
        )
    if field == "source_artifact_id":
        if value:
            return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM SourceArtifactV2.source_artifact_id"
        return (
            SemanticClassification.INVALID_SOURCE,
            BlockerClass.EVIDENCE_PROVENANCE,
            "empty source_artifact_id",
        )
    if field == "source_domain":
        return _classify_source_domain_v3(value)
    if field in {"campaign_id", "session_id", "uri", "world_id"}:
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"absent optional {field}"
        return SemanticClassification.EXACTLY_REPRESENTABLE, None, f"DM SourceArtifactV2.{field}"
    if field == "content_sha256":
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "absent content_sha256"
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            "Buddy content_sha256 → DM SourceRevision.content_sha256 adapter",
        )
    if field in {"artifact_kind", "document_class"}:
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"absent {field}"
        return SemanticClassification.EXACTLY_REPRESENTABLE, None, f"DM SourceArtifactV2.{field}"
    if field == "authority_state":
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "absent authority_state"
        if value in _AUTHORITY_REVIEW_VALUES:
            return (
                SemanticClassification.EXACTLY_REPRESENTABLE,
                None,
                f"Buddy authority_state {value!r} → SourceArtifactV2.review_state (SourceReviewState)",
            )
        return (
            SemanticClassification.INVALID_SOURCE,
            BlockerClass.EVIDENCE_PROVENANCE,
            f"unknown authority_state {value!r}",
        )
    if field == "visibility_state":
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "absent visibility_state"
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            f"Buddy visibility_state {value!r} → SourceArtifactV2.source_visibility_state "
            "(not DM Visibility gm/player)",
        )
    if field in {"workspace_document_id", "workspace_document_revision"}:
        if value is None:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"absent {field}"
        return (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            None,
            f"Buddy {field} → WorkspaceDocumentRefV1 adapter",
        )
    if field == "lineage":
        if not value:
            return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, "empty lineage"
        return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM SourceArtifactV2.lineage"
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
        return SemanticClassification.EXACTLY_REPRESENTABLE, None, "DM SourceArtifactV2.updated_at"
    return (
        SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        f"unclassified source_artifact field {field!r}",
    )


def _classify_store_scalar_v3(
    field: str,
    value: Any,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    if field in {"schema", "version"}:
        return SemanticClassification.BUDDY_OPERATIONAL_ONLY, None, f"store {field} marker"
    if field == "campaign_id":
        return (
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "store.campaign_id is Buddy container/routing metadata; not graph ownership "
            "and not KnowledgeAssertionMetadata.campaign_scope",
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


def _node_alias_strings(node: UnionSupergraphNode) -> list[str]:
    return [
        str(alias)
        for alias in (node.aliases or [])
        if isinstance(alias, str) and alias.strip()
    ]


def _substantive_node_aliases(node: UnionSupergraphNode) -> list[str]:
    """Aliases that are not canonical-label materialization duplicates."""
    label_key = (node.label or "").strip().casefold()
    return [
        alias
        for alias in _node_alias_strings(node)
        if alias.strip().casefold() != label_key
    ]


def _classify_node_aliases_field_v3(
    node: UnionSupergraphNode,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    """Classify node.aliases without treating label materialization as unsupported.

    Contribution merge defaults missing aliases to ``[label]`` and mirrors that into
    ``store.aliases``. Those are lookup material, not authored AliasAssertionRecords.
    """
    aliases = _node_alias_strings(node)
    if not aliases:
        return (
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "empty node.aliases",
        )
    substantive = _substantive_node_aliases(node)
    if not substantive:
        return (
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "node.aliases duplicates canonical label via contribution materialization; "
            "not an authored AliasAssertionRecord",
        )
    return (
        SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        "substantive node.aliases lack recoverable assertion-grain evidence_ref_ids "
        "for DM AliasAssertionRecord "
        f"(aliases={substantive!r})",
    )


def _classify_alias_v3(
    alias_label: str,
    node_id: str,
    store: UnionSupergraphStore,
) -> tuple[SemanticClassification, BlockerClass | None, str]:
    """Classify store.aliases entries without double-counting derivable index keys."""
    if not alias_label.strip() or not node_id.strip():
        return (
            SemanticClassification.INVALID_SOURCE,
            BlockerClass.EVIDENCE_PROVENANCE,
            "empty alias entry",
        )
    node = store.nodes.get(node_id)
    if node is None:
        return (
            SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
            BlockerClass.EVIDENCE_PROVENANCE,
            f"store.aliases entry {alias_label!r} targets missing node {node_id!r}",
        )
    key = alias_label.casefold()
    label_key = (node.label or "").strip().casefold()
    node_alias_keys = {alias.casefold() for alias in _node_alias_strings(node)}
    if key == label_key or key in node_alias_keys:
        return (
            SemanticClassification.BUDDY_OPERATIONAL_ONLY,
            None,
            "store.aliases lookup index entry derived from node label/aliases; "
            "not an independent authored assertion",
        )
    return (
        SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
        BlockerClass.EVIDENCE_PROVENANCE,
        f"non-derivable store.aliases entry {alias_label!r}; not reconstructable from "
        "node label/aliases as AliasAssertionRecord",
    )


_ALIAS_EVIDENCE_PATH_NOTE = (
    "Reconstruct assertion-grain AliasAssertionRecord evidence only for "
    "substantive Buddy aliases (and non-derivable store.aliases entries). "
    "Canonical-label materialization and derivable lookup-index keys are not "
    "DM evidence-contract gaps; DungeonMind already admits alias_assertions."
)
_DEFAULT_EVIDENCE_PROVENANCE_REPO = "DungeonMind"
_DEFAULT_EVIDENCE_PROVENANCE_NOTE = (
    "Preserve Buddy evidence_ref/source span/domain fields in DM evidence contracts."
)


def _is_alias_evidence_provenance_path(element_id: str) -> bool:
    """True for node.aliases fields and store.aliases index entries."""
    if element_id.startswith("alias:"):
        return True
    return ":field:aliases" in element_id


def _evidence_provenance_element_ids(
    classified: list[ClassifiedElement],
) -> list[str]:
    return [
        item.element_id
        for item in classified
        if item.blocker_class == BlockerClass.EVIDENCE_PROVENANCE
        and item.classification
        in {
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP,
            SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
            SemanticClassification.INVALID_SOURCE,
        }
    ]


def _rewrite_evidence_provenance_blocker_v3(
    blockers: list[AdoptionBlocker],
    classified: list[ClassifiedElement],
) -> None:
    """Specialize EP remediation by cause; split mixed residuals by owner.

    Alias-only residuals get Buddy alias reconstruction ownership. Non-alias-only
    residuals keep the generic DungeonMind evidence-contract diagnosis. Mixed
    residuals become two ``EVIDENCE_PROVENANCE`` blockers so ``responsible_repo``
    stays singular and accurate.
    """
    ep_ids = _evidence_provenance_element_ids(classified)
    if not ep_ids:
        return
    alias_ids = [eid for eid in ep_ids if _is_alias_evidence_provenance_path(eid)]
    non_alias_ids = [eid for eid in ep_ids if not _is_alias_evidence_provenance_path(eid)]

    ep_indexes = [
        index
        for index, blocker in enumerate(blockers)
        if blocker.blocker_class == BlockerClass.EVIDENCE_PROVENANCE
    ]
    if not ep_indexes:
        return

    if alias_ids and non_alias_ids:
        # Replace the aggregated EP blocker with cause-specific entries.
        for index in reversed(ep_indexes):
            blockers.pop(index)
        blockers.append(
            AdoptionBlocker(
                blocker_class=BlockerClass.EVIDENCE_PROVENANCE,
                count=len(alias_ids),
                examples=alias_ids[:_REPRESENTATIVE_ID_LIMIT],
                responsible_repo="DungeonMindBuddy",
                smallest_next_change=_ALIAS_EVIDENCE_PATH_NOTE,
            )
        )
        blockers.append(
            AdoptionBlocker(
                blocker_class=BlockerClass.EVIDENCE_PROVENANCE,
                count=len(non_alias_ids),
                examples=non_alias_ids[:_REPRESENTATIVE_ID_LIMIT],
                responsible_repo=_DEFAULT_EVIDENCE_PROVENANCE_REPO,  # type: ignore[arg-type]
                smallest_next_change=_DEFAULT_EVIDENCE_PROVENANCE_NOTE,
            )
        )
        return

    for index in ep_indexes:
        blocker = blockers[index]
        if alias_ids and not non_alias_ids:
            blocker.responsible_repo = "DungeonMindBuddy"  # type: ignore[assignment]
            blocker.smallest_next_change = _ALIAS_EVIDENCE_PATH_NOTE
            blocker.count = len(alias_ids)
            blocker.examples = alias_ids[:_REPRESENTATIVE_ID_LIMIT]
        else:
            blocker.responsible_repo = _DEFAULT_EVIDENCE_PROVENANCE_REPO  # type: ignore[assignment]
            blocker.smallest_next_change = _DEFAULT_EVIDENCE_PROVENANCE_NOTE
            blocker.count = len(non_alias_ids)
            blocker.examples = non_alias_ids[:_REPRESENTATIVE_ID_LIMIT]


def _build_relationship_predicate_inventory_v3(
    store: UnionSupergraphStore,
    vocabulary: Any,
) -> tuple[
    list[RelationshipPredicateInventoryRowV3],
    list[InventoryCountRow],
    int,
    int,
    int,
    int,
]:
    by_predicate: dict[str, list[UnionSupergraphEdge]] = defaultdict(list)
    for edge in store.edges.values():
        by_predicate[edge.predicate].append(edge)

    rows: list[RelationshipPredicateInventoryRowV3] = []
    residual_counter: Counter[str] = Counter()
    total_represented = 0
    total_residual = 0
    total_mechanics = 0
    total_semantic = 0

    for buddy_predicate in sorted(by_predicate):
        edges = by_predicate[buddy_predicate]
        # Key: (src_kind, tgt_kind, mapped_term, reverse_endpoints)
        endpoint_stats: dict[
            tuple[str, str, str | None, bool],
            dict[str, Any],
        ] = {}

        represented = 0
        residual = 0
        mechanics = 0

        for edge in sorted(edges, key=lambda item: item.edge_id):
            (
                _classification,
                _blocker,
                _note,
                edge_disposition,
                edge_mapped_term,
                reverse_endpoints,
            ) = _classify_edge_predicate_v3(edge, store, vocabulary)

            src_node = store.nodes.get(edge.source_node_id)
            tgt_node = store.nodes.get(edge.target_node_id)
            src_buddy = src_node.kind if src_node else "missing_node"
            tgt_buddy = tgt_node.kind if tgt_node else "missing_node"
            key = (src_buddy, tgt_buddy, edge_mapped_term, reverse_endpoints)
            if key not in endpoint_stats:
                endpoint_stats[key] = {
                    "count": 0,
                    "represented": 0,
                    "residual": 0,
                    "edge_ids": [],
                }
            endpoint_stats[key]["count"] += 1
            endpoint_stats[key]["edge_ids"].append(edge.edge_id)

            if edge_disposition == PredicateDisposition.MECHANICS_SPECIALIZATION:
                mechanics += 1
            elif edge_disposition == PredicateDisposition.EXISTING_EXPLICIT_ADAPTER:
                represented += 1
                endpoint_stats[key]["represented"] += 1
                total_semantic += 1
            else:
                residual += 1
                endpoint_stats[key]["residual"] += 1
                residual_counter[buddy_predicate] += 1
                total_semantic += 1

        total_represented += represented
        total_residual += residual
        total_mechanics += mechanics

        endpoint_pairs = [
            RelationshipEndpointPairInventoryRowV3(
                source_buddy_kind=pair[0],
                target_buddy_kind=pair[1],
                count=stats["count"],
                target_dungeonmind_term=pair[2],
                reverse_endpoints=pair[3],
                represented_count=stats["represented"],
                residual_count=stats["residual"],
                representative_edge_ids=sorted(stats["edge_ids"])[:_REPRESENTATIVE_ID_LIMIT],
            )
            for pair, stats in sorted(
                endpoint_stats.items(),
                key=lambda item: (item[0][0], item[0][1], item[0][2] or "", item[0][3]),
            )
        ]

        rows.append(
            RelationshipPredicateInventoryRowV3(
                buddy_predicate=buddy_predicate,
                count=len(edges),
                represented_count=represented,
                residual_count=residual,
                mechanics_count=mechanics,
                endpoint_pairs=endpoint_pairs,
            )
        )

    residual_by_predicate = [
        InventoryCountRow(key=predicate, count=count)
        for predicate, count in sorted(residual_counter.items())
    ]
    return (
        rows,
        residual_by_predicate,
        total_semantic,
        total_represented,
        total_residual,
        total_mechanics,
    )


def _build_property_gap_inventory_v3(
    store: UnionSupergraphStore,
) -> list[PropertyGapInventoryRowV1]:
    """Inventory description gaps only; adapted roles are not property gaps."""
    rows: list[PropertyGapInventoryRowV1] = []
    for field_name in ("description",):
        value_counter: Counter[str] = Counter()
        kind_counter: Counter[str] = Counter()
        for node in store.nodes.values():
            dump = _dump_record(node)
            raw = dump.get("description")
            if raw is None:
                continue
            if isinstance(raw, str) and not raw.strip():
                continue
            value_counter[str(raw)] += 1
            kind_counter[node.kind] += 1
        if value_counter:
            rows.append(
                PropertyGapInventoryRowV1(
                    field_name=f"node.{field_name}",
                    value_counts=[
                        PropertyGapValueCountRowV1(value=value, count=count)
                        for value, count in value_counter.most_common(20)
                    ],
                    object_kind_counts=[
                        PropertyGapObjectKindCountRowV1(object_kind=kind, count=count)
                        for kind, count in sorted(kind_counter.items())
                    ],
                )
            )
    return rows


def _append_identity_history_blocker(
    blockers: list[AdoptionBlocker],
    store: UnionSupergraphStore,
) -> None:
    identity_count = (
        len(store.identity_redirects)
        + len(store.identity_merge_records)
        + len(store.identity_decisions)
    )
    if not identity_count:
        return
    examples: list[str] = []
    for index, redirect in enumerate(store.identity_redirects):
        redirect_key = getattr(redirect, "redirect_id", None)
        if redirect_key is None and isinstance(redirect, dict):
            redirect_key = redirect.get("redirect_id", index)
        examples.append(f"identity_redirect:{redirect_key}:{index}")
    blockers.append(
        AdoptionBlocker(
            blocker_class=BlockerClass.IDENTITY_HISTORY,
            count=identity_count,
            examples=examples[:_REPRESENTATIVE_ID_LIMIT],
            responsible_repo="DungeonMindBuddy",
            smallest_next_change=(
                "Expose governed identity migration replay at adoption seam."
            ),
        )
    )


def _role_summary_counts(
    store: UnionSupergraphStore,
) -> tuple[int, int, int, int]:
    role_field_count = 0
    adapter = 0
    external_op = 0
    residual = 0
    for node in store.nodes.values():
        role_field_count += 1
        classification, _, _ = _classify_node_role_v3(node)
        if classification == SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER:
            adapter += 1
        elif classification == SemanticClassification.BUDDY_OPERATIONAL_ONLY:
            external_op += 1
        else:
            residual += 1
    return role_field_count, adapter, external_op, residual


def analyze_exact_buddy_world_revision_v3(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
) -> WholeWorldConformanceReportV3:
    """Inventory and classify one exact Buddy World Graph revision against v5/v3 contracts."""
    manifest, store = _load_exact_buddy_revision(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    profile = load_builtin_v3_descriptor()
    vocabulary = load_builtin_world_object_v3_vocabulary()
    vocab_ref = builtin_world_object_v3_vocabulary_ref()
    property_vocab = load_builtin_world_property_vocabulary()
    property_ref = builtin_world_property_vocabulary_ref()
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
                    f_class, f_blocker, f_note = _classify_state_field_v3(state_key, state_value)
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
                f_class, f_blocker, f_note = _classify_node_field_v3(field, value, node)
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

    for edge_id, edge in store.edges.items():
        edge_dump = _dump_record(edge)
        for field, value in edge_dump.items():
            if field == "state":
                for state_key, state_value in (value or {}).items():
                    element_id = f"edge:{edge_id}:state:{state_key}"
                    f_class, f_blocker, f_note = _classify_state_field_v3(state_key, state_value)
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
                f_class, f_blocker, f_note = _classify_edge_field_v3(
                    field, value, edge, store, vocabulary
                )
                family = "edge_session_refs" if field == "session_ids" and value else "edge_field"
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
                f_class, f_blocker, f_note = _classify_evidence_field_v3(field, value)
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
                f_class, f_blocker, f_note = _classify_artifact_field_v3(field, value)
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

    for alias_label, target_node_id in store.aliases.items():
        classification, blocker, note = _classify_alias_v3(
            alias_label, target_node_id, store
        )
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=f"alias:{alias_label}",
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
        classification, blocker, note = _classify_store_scalar_v3(field_name, value)
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=f"store:field:{field_name}",
            element_family="store_field",
            classification=classification,
            blocker_class=blocker,
            note=note,
        )

    for adjacency_node_id in store.adjacency:
        _append_classification(
            classified=classified,
            buckets=buckets,
            element_id=f"store:adjacency:{adjacency_node_id}",
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

    (
        relationship_predicate_inventory,
        residual_by_predicate,
        relationship_semantic_count,
        relationship_represented_count,
        relationship_residual_count,
        uses_statblock_count,
    ) = _build_relationship_predicate_inventory_v3(store, vocabulary)
    property_gap_inventory = _build_property_gap_inventory_v3(store)
    (
        role_field_count,
        role_property_adapter_count,
        role_external_resource_count,
        role_residual_count,
    ) = _role_summary_counts(store)

    blockers = _build_blockers(classified)
    _rewrite_evidence_provenance_blocker_v3(blockers, classified)
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
    _append_identity_history_blocker(blockers, store)

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

    disposition: WholeWorldDispositionV3 = (
        "WHOLE_GRAPH_ADOPTION_READY" if not blockers else "WHOLE_GRAPH_ADOPTION_NOT_READY"
    )

    return WholeWorldConformanceReportV3(
        source_world_id=world_id,
        source_revision_id=manifest.revision_id,
        source_graph_payload_sha256=manifest.graph_payload_sha256,
        source_campaign_id=store.campaign_id,
        dungeonmind_dependency_ref=_DUNGEONMIND_DEPENDENCY_REF_V3,
        target_graph_schema=GRAPH_SCHEMA_V5,
        source_artifact_schema=SOURCE_ARTIFACT_V2_SCHEMA,
        evidence_schema=EVIDENCE_REF_V2_SCHEMA,
        assertion_metadata_schema=KNOWLEDGE_ASSERTION_METADATA_SCHEMA,
        semantic_profile_id=profile.profile_id,
        semantic_profile_revision=profile.profile_revision,
        semantic_profile_descriptor_sha256=descriptor_sha256(profile),
        world_object_vocabulary_id=vocab_ref.vocabulary_id,
        world_object_vocabulary_revision=vocab_ref.vocabulary_revision,
        world_object_vocabulary_sha256=vocabulary_sha256(vocabulary),
        world_property_vocabulary_id=property_ref.vocabulary_id,
        world_property_vocabulary_revision=property_ref.vocabulary_revision,
        world_property_vocabulary_sha256=world_property_vocabulary_sha256(property_vocab),
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
        relationship_predicate_inventory=relationship_predicate_inventory,
        residual_by_predicate=residual_by_predicate,
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
        property_gap_inventory=property_gap_inventory,
        classification_inventory=_classification_inventory(classified),
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
            "Genesis policies A/B/C remain undecided for execution. Post-v28 world-object-v3 "
            "and world-property-v1 close relationship/role adapter surface vs v2. Canonical "
            "label→alias index materialization is operational, not an evidence-contract gap. "
            "Adoption remains blocked by residual relationship adjudication, contribution/"
            "identity history, the missing durable adoption seam, and any remaining "
            "substantive-alias assertion-grain residuals."
        ),
        unaccounted_durable_elements=unaccounted,
        classified_elements_count=len(classified),
        relationship_semantic_count=relationship_semantic_count,
        relationship_represented_count=relationship_represented_count,
        relationship_residual_count=relationship_residual_count,
        uses_statblock_mechanics_count=uses_statblock_count,
        role_field_count=role_field_count,
        role_property_adapter_count=role_property_adapter_count,
        role_external_resource_count=role_external_resource_count,
        role_residual_count=role_residual_count,
    )


def build_exact_dungeonmind_adoption_revision_v3(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
) -> Any:
    """Build a DM StoredGraphRevision only when whole-graph v5 adoption is READY."""
    report = analyze_exact_buddy_world_revision_v3(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    if report.disposition != "WHOLE_GRAPH_ADOPTION_READY":
        raise WholeWorldConformanceError(
            "whole-graph adoption is NOT_READY for dm_union_graph_v5; "
            "refusing partial adoption revision",
            report=report,  # type: ignore[arg-type]
        )
    raise WholeWorldConformanceError(
        "WHOLE_GRAPH_ADOPTION_READY was reported but complete dm_union_graph_v5 "
        "target construction is not implemented in this diagnostic PR; refusing "
        "lossy partial construction",
        report=report,  # type: ignore[arg-type]
    )
