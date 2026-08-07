"""Exact Buddy world object → DungeonMind v3 conformance bridge.

Builds an ephemeral in-memory ``dm_union_graph_v3`` *conformance snapshot*
for one explicit Buddy world object (Threat, NPC, or PC) and maps every valid
``uses_statblock`` attachment into DungeonMind world-object mechanics bindings
and role-preserving statblock attachments when mechanics-eligible.

This is not a durable graph migration, not product shadow hydration, and not
mechanics authority promotion. Source authority remains the exact immutable
Buddy World Graph revision; target schemas and ID derivation are owned by the
installed ``dungeonmind`` / ``dungeonmind_dnd`` packages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from dungeonmind.application.graph_snapshot import GRAPH_SCHEMA_V3, UnionGraphV3SnapshotReader
from dungeonmind.application.semantic_profiles import descriptor_sha256
from dungeonmind.contracts.graph import StoredGraphRevision, WorldGraphRevision
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.domain.revision_ids import compute_revision_id
from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
from dungeonmind_dnd.application.world_object_mechanics import (
    derive_world_object_mechanics_binding,
)
from dungeonmind_dnd.application.world_object_vocabulary import load_builtin_v3_descriptor
from dungeonmind_dnd.contracts.mechanics_resources import (
    STATBLOCKS_MEDIA_TYPE,
    STATBLOCKS_PROVIDER_ID,
    DndMechanicsResourceRef,
    is_exact_dungeonmind_statblock_resource_ref,
)
from dungeonmind_dnd.contracts.world_object_mechanics import (
    DndStatblockMechanicsAttachment,
    DndWorldObjectMechanicsBinding,
    derive_statblock_mechanics_attachment_id,
    enumerate_statblock_mechanics_attachments,
)
from pydantic import ValidationError

import graph_memory.kernel as kernel
from graph_memory.kernel.world_projection import WorldGraphProjectionError
from graph_memory.union_supergraph.model import (
    UnionSupergraphEdge,
    UnionSupergraphNode,
    UnionSupergraphStore,
)
from graph_memory.union_supergraph.statblock_binding import (
    CONTRACT,
    CONTRACT_VERSION,
    PROVIDER,
    ExactSourceStatblockAttachment,
    compute_binding_id,
    compute_world_object_statblock_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
    normalize_legacy_threat_binding,
    normalize_world_object_binding,
)

BuddyWorldGraphRevision = kernel.WorldGraphRevision

_USES_STATBLOCK = "uses_statblock"
_OBJECT_ID_PREFIX = "obj:dmb:"
_OBJECT_ID_RE = re.compile(r"^obj:[A-Za-z0-9._:-]+$")
_SOURCE_NODE_ID_ALPHABET = re.compile(r"^[A-Za-z0-9._:-]+$")
_SHA256_PREFIXED = re.compile(r"^sha256:([0-9a-f]{64})$")
_BUDDY_PROVIDER = PROVIDER
_BRIDGE_EVIDENCE_DOMAIN = "other"

_BUDDY_KIND_TO_TARGET: dict[str, str] = {
    "threat": "dnd5e:threat",
    "npc": "dnd5e:npc",
    "pc": "dnd5e:player_character",
}
_BRIDGEABLE_BUDDY_KINDS = frozenset(_BUDDY_KIND_TO_TARGET)
_MECHANICS_ELIGIBLE_BUDDY_KINDS = frozenset({"threat", "npc"})
_TARGET_THREAT_KIND = _BUDDY_KIND_TO_TARGET["threat"]

BridgeFailureReason = Literal[
    "exact_revision_missing",
    "source_revision_integrity_failure",
    "world_mismatch",
    "campaign_mismatch",
    "source_threat_missing",
    "source_object_missing",
    "source_object_kind_not_bridgeable",
    "source_object_id_not_representable",
    "source_revision_created_at_unparseable",
    "malformed_uses_statblock_edge",
    "inbound_uses_statblock",
    "missing_threat_statblock_binding",
    "missing_statblock_binding",
    "duplicate_source_binding_identity",
    "duplicate_source_edge_identity",
    "duplicate_semantic_attachment",
    "wrong_external_resource_target",
    "missing_external_resource_node",
    "provider_mismatch",
    "contract_version_mismatch",
    "forged_buddy_binding_id",
    "forged_buddy_edge_id",
    "malformed_definition_digest",
    "target_statblock_resource_rejected",
    "target_binding_identity_mismatch",
    "target_attachment_identity_mismatch",
    "alias_not_representable",
    "duplicate_target_attachment_identity",
    "admitted_uses_statblock_edge_missing",
    "ambiguous_uses_statblock_binding",
    "pc_mechanics_attachment_forbidden",
]


class ThreatConformanceBridgeError(Exception):
    """Fail-closed bridge error with a stable machine reason."""

    def __init__(self, reason: BridgeFailureReason, message: str) -> None:
        super().__init__(message)
        self.reason: BridgeFailureReason = reason
        self.message = message


WorldObjectConformanceBridgeError = ThreatConformanceBridgeError


@dataclass(frozen=True)
class BridgedStatblockAttachment:
    """One Buddy uses_statblock binding mapped to a DungeonMind attachment."""

    source_edge_id: str
    source_binding_id: str
    target_binding_id: str
    target_attachment_id: str
    attachment: DndStatblockMechanicsAttachment


@dataclass(frozen=True)
class DungeonMindWorldObjectConformanceBridgeResult:
    """Internal-only result of an exact Buddy world-object conformance bridge."""

    source_world_id: str
    source_campaign_id: str
    source_revision_id: str
    source_graph_payload_sha256: str
    source_node_id: str
    target_world_id: str
    target_revision: StoredGraphRevision
    target_object_id: str
    target_object_kind: str
    attachments: tuple[BridgedStatblockAttachment, ...]


DungeonMindThreatConformanceBridgeResult = DungeonMindWorldObjectConformanceBridgeResult


def map_buddy_world_object_id(source_node_id: str) -> str:
    """Deterministic reversible Buddy world-object → DungeonMind object identity."""
    if not isinstance(source_node_id, str) or not source_node_id:
        raise ThreatConformanceBridgeError(
            "source_object_id_not_representable",
            "source world-object node id is empty or not a string",
        )
    if not _SOURCE_NODE_ID_ALPHABET.fullmatch(source_node_id):
        raise ThreatConformanceBridgeError(
            "source_object_id_not_representable",
            "source world-object node id is not representable under DungeonMind object-ID alphabet",
        )
    target = f"{_OBJECT_ID_PREFIX}{source_node_id}"
    if not _OBJECT_ID_RE.fullmatch(target):
        raise ThreatConformanceBridgeError(
            "source_object_id_not_representable",
            "mapped object_id fails DungeonMind object-ID grammar",
        )
    return target


def map_buddy_threat_object_id(source_node_id: str) -> str:
    """Deterministic reversible Buddy Threat → DungeonMind object identity."""
    return map_buddy_world_object_id(source_node_id)


def map_buddy_provider_to_dungeonmind_provider_id(provider: str) -> str:
    """Explicit Buddy provider → DungeonMind provider_id compatibility map."""
    if provider != _BUDDY_PROVIDER:
        raise ThreatConformanceBridgeError(
            "provider_mismatch",
            f"unsupported Buddy provider {provider!r}; expected {_BUDDY_PROVIDER!r}",
        )
    return STATBLOCKS_PROVIDER_ID


def convert_buddy_definition_digest(definition_digest: str) -> str:
    """Convert ``sha256:<64 hex>`` to bare lowercase hex. Exactly one prefix."""
    if not isinstance(definition_digest, str):
        raise ThreatConformanceBridgeError(
            "malformed_definition_digest",
            "definition_digest must be a string",
        )
    match = _SHA256_PREFIXED.fullmatch(definition_digest)
    if match is None:
        raise ThreatConformanceBridgeError(
            "malformed_definition_digest",
            "definition_digest must be exactly sha256:<64 lowercase hex>",
        )
    return match.group(1)


def _target_kind_for_buddy_kind(buddy_kind: str) -> str:
    target = _BUDDY_KIND_TO_TARGET.get(buddy_kind)
    if target is None:
        raise ThreatConformanceBridgeError(
            "source_object_kind_not_bridgeable",
            f"source kind {buddy_kind!r} is not an explicit bridgeable Buddy world object",
        )
    return target


def _v3_graph_reader() -> UnionGraphV3SnapshotReader:
    descriptor = load_builtin_v3_descriptor()
    return UnionGraphV3SnapshotReader(
        profile_registry=StaticSemanticProfileRegistry([descriptor])
    )


def _parse_buddy_created_at(value: str) -> datetime:
    try:
        raw = value
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        raise ThreatConformanceBridgeError(
            "source_revision_created_at_unparseable",
            f"source revision created_at is not parseable: {value!r}",
        ) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _bridge_evidence_ids(
    *,
    source_world_id: str,
    source_revision_id: str,
    source_graph_payload_sha256: str,
    source_node_id: str,
) -> tuple[str, str]:
    material = {
        "bridge": "dmb_world_object_conformance_v1",
        "source_world_id": source_world_id,
        "source_revision_id": source_revision_id,
        "source_graph_payload_sha256": source_graph_payload_sha256,
        "source_node_id": source_node_id,
    }
    digest = canonical_sha256(material)
    evidence_ref_id = f"ev:dmb-bridge:{digest[:32]}"
    source_artifact_id = f"src:dmb-world-graph-revision:{source_revision_id}"
    return evidence_ref_id, source_artifact_id


def _alias_assertions(
    aliases: list[str],
    *,
    evidence_ref_id: str,
    source_node_id: str,
) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    for index, alias in enumerate(aliases):
        if not isinstance(alias, str) or not alias.strip():
            raise ThreatConformanceBridgeError(
                "alias_not_representable",
                "source alias cannot be represented as a DungeonMind alias assertion",
            )
        assertion_id = (
            f"alias:dmb-bridge:{canonical_sha256({'node': source_node_id, 'i': index, 'a': alias})[:24]}"
        )
        assertions.append(
            {
                "assertion_id": assertion_id,
                "alias": alias,
                "evidence_ref_ids": [evidence_ref_id],
            }
        )
    return assertions


def _build_conformance_snapshot(
    *,
    source_world_id: str,
    source_revision: BuddyWorldGraphRevision,
    source_node: UnionSupergraphNode,
    target_object_id: str,
    target_object_kind: str,
) -> StoredGraphRevision:
    """Construct an ephemeral DungeonMind v3 conformance snapshot (not durable)."""
    evidence_ref_id, source_artifact_id = _bridge_evidence_ids(
        source_world_id=source_world_id,
        source_revision_id=source_revision.revision_id,
        source_graph_payload_sha256=source_revision.graph_payload_sha256,
        source_node_id=source_node.node_id,
    )
    descriptor = load_builtin_v3_descriptor()
    profile_digest = descriptor_sha256(descriptor)
    evidence = {
        "schema_version": "dm_evidence_ref_v1",
        "evidence_ref_id": evidence_ref_id,
        "source_artifact_id": source_artifact_id,
        "source_revision_id": source_revision.revision_id,
        "source_domain": _BRIDGE_EVIDENCE_DOMAIN,
        "evidence_role": "support",
        "can_open_source": False,
        "can_highlight_span": False,
        "locator": None,
        "uri": None,
    }
    node = {
        "object_id": target_object_id,
        "kind": target_object_kind,
        "label": source_node.label,
        "evidence_ref_ids": [evidence_ref_id],
        "alias_assertions": _alias_assertions(
            list(source_node.aliases),
            evidence_ref_id=evidence_ref_id,
            source_node_id=source_node.node_id,
        ),
        "summary_assertion": None,
    }
    graph_payload: dict[str, Any] = {
        "world_id": source_world_id,
        "semantic_profile": {
            "schema_version": "dm_semantic_profile_ref_v1",
            "profile_id": "dungeonmind.dnd5e",
            "profile_revision": "dnd5e-profile-v3",
            "descriptor_sha256": profile_digest,
        },
        "nodes": [node],
        "relationships": [],
        "evidence_refs": [evidence],
    }
    payload_sha = canonical_sha256(graph_payload)
    operation_ids = [
        f"dmb_bridge:{source_revision.revision_id}:{source_node.node_id}",
    ]
    revision_id = compute_revision_id(
        world_id=source_world_id,
        parent_revision_id=None,
        operation_ids=operation_ids,
        graph_schema=GRAPH_SCHEMA_V3,
        graph_payload_sha256=payload_sha,
    )
    created_at = _parse_buddy_created_at(source_revision.created_at)
    return StoredGraphRevision(
        revision=WorldGraphRevision(
            world_id=source_world_id,
            revision_id=revision_id,
            parent_revision_id=None,
            created_at=created_at,
            operation_ids=operation_ids,
            graph_schema=GRAPH_SCHEMA_V3,
            graph_payload_sha256=payload_sha,
            status="published",
        ),
        graph_payload=graph_payload,
    )


def _map_resource_ref(attachment: ExactSourceStatblockAttachment) -> DndMechanicsResourceRef:
    provider_id = map_buddy_provider_to_dungeonmind_provider_id(attachment.provider)
    if attachment.contract != CONTRACT or attachment.contract_version != CONTRACT_VERSION:
        raise ThreatConformanceBridgeError(
            "contract_version_mismatch",
            "Buddy binding contract/version is not the accepted dungeonbuddy-statblocks identity",
        )
    resource_schema = f"{attachment.contract}.{attachment.contract_version}"
    payload_sha256 = convert_buddy_definition_digest(attachment.definition_digest)
    resource_ref = DndMechanicsResourceRef(
        ruleset_id="dnd5e",
        provider_id=provider_id,
        resource_id=attachment.statblock_id,
        resource_revision=attachment.revision_id,
        resource_schema=resource_schema,
        media_type=STATBLOCKS_MEDIA_TYPE,
        payload_sha256=payload_sha256,
    )
    if not is_exact_dungeonmind_statblock_resource_ref(resource_ref):
        raise ThreatConformanceBridgeError(
            "target_statblock_resource_rejected",
            "mapped resource_ref is not an exact DungeonMind statblock identity",
        )
    return resource_ref


def _recompute_binding_id(
    *,
    attachment: ExactSourceStatblockAttachment,
    source_node_id: str,
) -> str:
    if attachment.source_schema == "legacy_threat":
        return compute_binding_id(
            threat_node_id=source_node_id,
            provider=attachment.provider,
            statblock_id=attachment.statblock_id,
            revision_id=attachment.revision_id,
            contract=attachment.contract,
            contract_version=attachment.contract_version,
            definition_digest=attachment.definition_digest,
            role=attachment.role,
            phase_key=attachment.phase_key,
            variant_label=attachment.variant_label,
        )
    return compute_world_object_statblock_binding_id(
        world_object_node_id=source_node_id,
        world_object_kind=attachment.world_object_kind,
        provider=attachment.provider,
        statblock_id=attachment.statblock_id,
        revision_id=attachment.revision_id,
        contract=attachment.contract,
        contract_version=attachment.contract_version,
        definition_digest=attachment.definition_digest,
        role=attachment.role,
        phase_key=attachment.phase_key,
        variant_label=attachment.variant_label,
    )


def _normalize_edge_attachment(
    *,
    edge: UnionSupergraphEdge,
    source_node_id: str,
    source_kind: str,
) -> ExactSourceStatblockAttachment:
    legacy = edge.threat_statblock_binding
    generic = edge.statblock_binding
    has_legacy = legacy is not None
    has_generic = generic is not None

    if has_legacy and has_generic:
        raise ThreatConformanceBridgeError(
            "ambiguous_uses_statblock_binding",
            f"uses_statblock edge {edge.edge_id!r} carries both legacy and generic bindings",
        )

    if not has_legacy and not has_generic:
        if source_kind == "threat":
            raise ThreatConformanceBridgeError(
                "missing_threat_statblock_binding",
                f"uses_statblock edge {edge.edge_id!r} lacks ThreatStatblockBindingV1",
            )
        raise ThreatConformanceBridgeError(
            "missing_statblock_binding",
            f"uses_statblock edge {edge.edge_id!r} lacks a recognized statblock binding",
        )

    if source_kind == "npc":
        if has_legacy and not has_generic:
            raise ThreatConformanceBridgeError(
                "missing_statblock_binding",
                f"uses_statblock edge {edge.edge_id!r} must use generic statblock_binding for NPC",
            )
        assert generic is not None
        if generic.world_object_kind != "npc":
            raise ThreatConformanceBridgeError(
                "malformed_uses_statblock_edge",
                "generic statblock_binding world_object_kind must match source NPC",
            )
        return normalize_world_object_binding(generic)

    if source_kind == "threat":
        if has_legacy:
            return normalize_legacy_threat_binding(legacy)
        assert generic is not None
        if generic.world_object_kind != "threat":
            raise ThreatConformanceBridgeError(
                "malformed_uses_statblock_edge",
                "generic statblock_binding world_object_kind must match source Threat",
            )
        return normalize_world_object_binding(generic)

    raise ThreatConformanceBridgeError(
        "pc_mechanics_attachment_forbidden",
        "player character nodes must not carry uses_statblock attachments",
    )


def _validate_source_binding_edge(
    *,
    edge: UnionSupergraphEdge,
    source_node_id: str,
    source_kind: str,
    store: UnionSupergraphStore,
    seen_edge_ids: set[str],
    seen_binding_ids: set[str],
) -> ExactSourceStatblockAttachment:
    if edge.edge_id in seen_edge_ids:
        raise ThreatConformanceBridgeError(
            "duplicate_source_edge_identity",
            f"duplicate uses_statblock edge_id {edge.edge_id!r}",
        )
    seen_edge_ids.add(edge.edge_id)

    if edge.source_node_id != source_node_id:
        raise ThreatConformanceBridgeError(
            "inbound_uses_statblock",
            "uses_statblock edge does not source from the selected world object",
        )
    direction = (edge.direction or "").casefold()
    if direction not in {"outbound", "outgoing"}:
        raise ThreatConformanceBridgeError(
            "malformed_uses_statblock_edge",
            f"uses_statblock direction must be outbound/outgoing, got {edge.direction!r}",
        )

    attachment = _normalize_edge_attachment(
        edge=edge,
        source_node_id=source_node_id,
        source_kind=source_kind,
    )

    if attachment.binding_id in seen_binding_ids:
        raise ThreatConformanceBridgeError(
            "duplicate_source_binding_identity",
            f"duplicate uses_statblock binding_id {attachment.binding_id!r}",
        )
    seen_binding_ids.add(attachment.binding_id)

    expected_target = external_statblock_node_id(attachment.statblock_id)
    if edge.target_node_id != expected_target:
        raise ThreatConformanceBridgeError(
            "wrong_external_resource_target",
            "uses_statblock target does not match binding statblock identity",
        )

    resource_node = store.nodes.get(edge.target_node_id)
    if resource_node is None:
        raise ThreatConformanceBridgeError(
            "missing_external_resource_node",
            f"external resource node {edge.target_node_id!r} is missing",
        )
    resource = resource_node.external_resource
    if resource is None:
        raise ThreatConformanceBridgeError(
            "missing_external_resource_node",
            f"node {edge.target_node_id!r} lacks external_resource payload",
        )
    if resource.provider != PROVIDER or resource.resource_id != attachment.statblock_id:
        raise ThreatConformanceBridgeError(
            "provider_mismatch",
            "external resource provider/resource_id disagree with binding",
        )
    if (
        resource.contract != attachment.contract
        or resource.contract_version != attachment.contract_version
    ):
        raise ThreatConformanceBridgeError(
            "contract_version_mismatch",
            "external resource contract/version disagree with binding",
        )

    try:
        recomputed = _recompute_binding_id(
            attachment=attachment,
            source_node_id=source_node_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise ThreatConformanceBridgeError(
            "malformed_uses_statblock_edge",
            f"binding_id recompute failed: {exc}",
        ) from exc
    if recomputed != attachment.binding_id:
        raise ThreatConformanceBridgeError(
            "forged_buddy_binding_id",
            "Buddy binding_id does not recompute from immutable semantic material",
        )
    if edge.edge_id != edge_id_from_binding_id(attachment.binding_id):
        raise ThreatConformanceBridgeError(
            "forged_buddy_edge_id",
            "Buddy edge_id does not match deterministic binding_id",
        )
    return attachment


def _assert_no_pc_mechanics_edges(
    store: UnionSupergraphStore,
    source_node_id: str,
    *,
    admitted_uses_statblock_edge_ids: frozenset[str] | None = None,
) -> None:
    if admitted_uses_statblock_edge_ids is not None:
        if admitted_uses_statblock_edge_ids:
            raise ThreatConformanceBridgeError(
                "pc_mechanics_attachment_forbidden",
                "player character nodes must not carry uses_statblock attachments",
            )
        return

    for edge in store.edges.values():
        involves = edge.predicate == _USES_STATBLOCK and (
            edge.source_node_id == source_node_id
            or edge.target_node_id == source_node_id
        )
        if involves:
            raise ThreatConformanceBridgeError(
                "pc_mechanics_attachment_forbidden",
                "player character nodes must not carry uses_statblock attachments",
            )


def _collect_validated_bindings(
    store: UnionSupergraphStore,
    source_node_id: str,
    source_kind: str,
    *,
    admitted_uses_statblock_edge_ids: frozenset[str] | None = None,
) -> list[tuple[UnionSupergraphEdge, ExactSourceStatblockAttachment]]:
    found: list[tuple[UnionSupergraphEdge, ExactSourceStatblockAttachment]] = []
    seen_edge_ids: set[str] = set()
    seen_binding_ids: set[str] = set()
    seen_semantic_keys: set[tuple[Any, ...]] = set()

    if admitted_uses_statblock_edge_ids is not None:
        missing: list[str] = []
        for edge_id in sorted(admitted_uses_statblock_edge_ids):
            edge = store.edges.get(edge_id)
            if edge is None:
                missing.append(edge_id)
                continue
            if edge.predicate != _USES_STATBLOCK:
                raise ThreatConformanceBridgeError(
                    "malformed_uses_statblock_edge",
                    f"admitted edge {edge_id!r} is not uses_statblock",
                )
            attachment = _validate_source_binding_edge(
                edge=edge,
                source_node_id=source_node_id,
                source_kind=source_kind,
                store=store,
                seen_edge_ids=seen_edge_ids,
                seen_binding_ids=seen_binding_ids,
            )
            semantic_key = attachment.semantic_key()
            if semantic_key in seen_semantic_keys:
                raise ThreatConformanceBridgeError(
                    "duplicate_semantic_attachment",
                    "uses_statblock edges carry duplicate semantic attachment material",
                )
            seen_semantic_keys.add(semantic_key)
            found.append((edge, attachment))
        if missing:
            raise ThreatConformanceBridgeError(
                "admitted_uses_statblock_edge_missing",
                "admitted uses_statblock edge id(s) absent from exact source "
                f"revision: {missing!r}",
            )
    else:
        for edge in store.edges.values():
            involves = edge.predicate == _USES_STATBLOCK and (
                edge.source_node_id == source_node_id
                or edge.target_node_id == source_node_id
            )
            if not involves:
                continue
            attachment = _validate_source_binding_edge(
                edge=edge,
                source_node_id=source_node_id,
                source_kind=source_kind,
                store=store,
                seen_edge_ids=seen_edge_ids,
                seen_binding_ids=seen_binding_ids,
            )
            semantic_key = attachment.semantic_key()
            if semantic_key in seen_semantic_keys:
                raise ThreatConformanceBridgeError(
                    "duplicate_semantic_attachment",
                    "uses_statblock edges carry duplicate semantic attachment material",
                )
            seen_semantic_keys.add(semantic_key)
            found.append((edge, attachment))

    found.sort(
        key=lambda item: (
            item[1].role,
            item[1].binding_id,
            item[0].edge_id,
        )
    )
    return found


def _bridge_buddy_world_object_revision(
    *,
    source_world_id: str,
    source_revision: BuddyWorldGraphRevision,
    source_store: UnionSupergraphStore,
    world_object_node_id: str,
    campaign_id: str | None = None,
    admitted_uses_statblock_edge_ids: frozenset[str] | None = None,
    required_source_kind: str | None = None,
    missing_node_reason: BridgeFailureReason = "source_object_missing",
) -> DungeonMindWorldObjectConformanceBridgeResult:
    """Private helper: bridge from an integrity-attested revision/store pair.

    Not a public entrypoint. Provenance must already be established by
    ``kernel.load_world_graph_revision_with_integrity`` (raw on-disk bytes).
    Do not rehash a post-parse ``model_dump`` — that can drift from immutable
    revision bytes when the store model gains defaults.

    When ``admitted_uses_statblock_edge_ids`` is provided, it is the exact
    selection boundary (e.g. edges already admitted by a scoped World Graph
    projection). Other raw-store ``uses_statblock`` edges are ignored.
    """
    if source_revision.world_id != source_world_id:
        raise ThreatConformanceBridgeError(
            "world_mismatch",
            "requested world_id does not match revision manifest world_id",
        )
    if campaign_id is not None and campaign_id != source_store.campaign_id:
        raise ThreatConformanceBridgeError(
            "campaign_mismatch",
            "requested campaign_id does not match source store campaign_id",
        )

    node = source_store.nodes.get(world_object_node_id)
    if node is None:
        label = "Threat" if missing_node_reason == "source_threat_missing" else "world object"
        raise ThreatConformanceBridgeError(
            missing_node_reason,
            f"{label} node {world_object_node_id!r} is absent from the source revision",
        )

    if node.kind not in _BRIDGEABLE_BUDDY_KINDS:
        raise ThreatConformanceBridgeError(
            "source_object_kind_not_bridgeable",
            f"source kind {node.kind!r} is not an explicit bridgeable Buddy world object",
        )
    if required_source_kind is not None and node.kind != required_source_kind:
        raise ThreatConformanceBridgeError(
            "source_object_kind_not_bridgeable",
            f"source kind {node.kind!r} is not an explicit Buddy {required_source_kind}",
        )

    source_kind = node.kind
    target_object_kind = _target_kind_for_buddy_kind(source_kind)
    target_object_id = map_buddy_world_object_id(world_object_node_id)
    target_revision = _build_conformance_snapshot(
        source_world_id=source_world_id,
        source_revision=source_revision,
        source_node=node,
        target_object_id=target_object_id,
        target_object_kind=target_object_kind,
    )

    relationships = target_revision.graph_payload.get("relationships") or []
    if relationships:
        raise ThreatConformanceBridgeError(
            "malformed_uses_statblock_edge",
            "conformance snapshot unexpectedly contains relationships",
        )

    if source_kind == "pc":
        _assert_no_pc_mechanics_edges(
            source_store,
            world_object_node_id,
            admitted_uses_statblock_edge_ids=admitted_uses_statblock_edge_ids,
        )
        source_bindings: list[tuple[UnionSupergraphEdge, ExactSourceStatblockAttachment]] = []
    else:
        source_bindings = _collect_validated_bindings(
            source_store,
            world_object_node_id,
            source_kind,
            admitted_uses_statblock_edge_ids=admitted_uses_statblock_edge_ids,
        )

    graph_reader = _v3_graph_reader()
    binding_cache: dict[str, DndWorldObjectMechanicsBinding] = {}
    bridged: list[BridgedStatblockAttachment] = []

    for edge, source_attachment in source_bindings:
        resource_ref = _map_resource_ref(source_attachment)
        cache_key = canonical_sha256(resource_ref.model_dump(mode="json"))
        target_binding = binding_cache.get(cache_key)
        if target_binding is None:
            target_binding = derive_world_object_mechanics_binding(
                target_object_id,
                resource_ref,
                graph_revision=target_revision,
                graph_reader=graph_reader,
            )
            binding_cache[cache_key] = target_binding

        expected_attachment_id = derive_statblock_mechanics_attachment_id(
            binding_id=target_binding.binding_id,
            role=source_attachment.role,
            phase_key=source_attachment.phase_key,
            variant_label=source_attachment.variant_label,
        )
        try:
            attachment = DndStatblockMechanicsAttachment(
                attachment_id=expected_attachment_id,
                binding=target_binding,
                role=source_attachment.role,
                phase_key=source_attachment.phase_key,
                variant_label=source_attachment.variant_label,
            )
        except ValidationError as exc:
            message = str(exc)
            if "phase_key" in message:
                raise ThreatConformanceBridgeError(
                    "malformed_uses_statblock_edge",
                    f"statblock attachment role/phase_key rejected: {exc}",
                ) from exc
            raise ThreatConformanceBridgeError(
                "target_attachment_identity_mismatch",
                f"DungeonMind rejected statblock attachment: {exc}",
            ) from exc

        if attachment.attachment_id != expected_attachment_id:
            raise ThreatConformanceBridgeError(
                "target_attachment_identity_mismatch",
                "attachment_id does not match DungeonMind content-address derivation",
            )
        if attachment.binding.binding_id != target_binding.binding_id:
            raise ThreatConformanceBridgeError(
                "target_binding_identity_mismatch",
                "attachment binding_id diverged from derived generic binding",
            )
        if (
            attachment.phase_key != source_attachment.phase_key
            or attachment.variant_label != source_attachment.variant_label
            or attachment.role != source_attachment.role
        ):
            raise ThreatConformanceBridgeError(
                "target_attachment_identity_mismatch",
                "role/phase_key/variant_label were not preserved byte-for-byte",
            )

        bridged.append(
            BridgedStatblockAttachment(
                source_edge_id=edge.edge_id,
                source_binding_id=source_attachment.binding_id,
                target_binding_id=target_binding.binding_id,
                target_attachment_id=attachment.attachment_id,
                attachment=attachment,
            )
        )

    if bridged:
        try:
            enumerate_statblock_mechanics_attachments(
                [item.attachment for item in bridged]
            )
        except ValueError as exc:
            raise ThreatConformanceBridgeError(
                "duplicate_target_attachment_identity",
                f"target attachments are not uniquely enumerable: {exc}",
            ) from exc

    return DungeonMindWorldObjectConformanceBridgeResult(
        source_world_id=source_world_id,
        source_campaign_id=source_store.campaign_id,
        source_revision_id=source_revision.revision_id,
        source_graph_payload_sha256=source_revision.graph_payload_sha256,
        source_node_id=world_object_node_id,
        target_world_id=source_world_id,
        target_revision=target_revision,
        target_object_id=target_object_id,
        target_object_kind=target_object_kind,
        attachments=tuple(bridged),
    )


def _bridge_buddy_threat_revision(
    *,
    source_world_id: str,
    source_revision: BuddyWorldGraphRevision,
    source_store: UnionSupergraphStore,
    threat_node_id: str,
    campaign_id: str | None = None,
    admitted_uses_statblock_edge_ids: frozenset[str] | None = None,
) -> DungeonMindThreatConformanceBridgeResult:
    """Private Threat compatibility wrapper over the shared world-object bridge."""
    return _bridge_buddy_world_object_revision(
        source_world_id=source_world_id,
        source_revision=source_revision,
        source_store=source_store,
        world_object_node_id=threat_node_id,
        campaign_id=campaign_id,
        admitted_uses_statblock_edge_ids=admitted_uses_statblock_edge_ids,
        required_source_kind="threat",
        missing_node_reason="source_threat_missing",
    )


@dataclass(frozen=True)
class _ExactBuddyRevisionBridgeSource:
    """Integrity-attested Buddy revision pair for private package-internal reuse.

    Constructed only by ``_load_exact_buddy_revision_bridge_source``. Not a public
    API and must never be assembled from an arbitrary manifest + store.
    """

    manifest: BuddyWorldGraphRevision
    store: UnionSupergraphStore


def _load_exact_buddy_revision_bridge_source(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
) -> _ExactBuddyRevisionBridgeSource:
    """Integrity-load one exact Buddy revision once (raw on-disk bytes).

    Never consults World Graph head. Never reconstructs payload digests from a
    post-parse ``model_dump``.
    """
    try:
        store = kernel.load_world_graph_revision_with_integrity(
            root, world_id, revision_id
        )
    except WorldGraphProjectionError as exc:
        code = getattr(exc, "code", "") or ""
        if code in {"revision_not_found"}:
            raise ThreatConformanceBridgeError(
                "exact_revision_missing",
                f"exact Buddy revision not found: {revision_id!r}",
            ) from exc
        raise ThreatConformanceBridgeError(
            "source_revision_integrity_failure",
            f"source revision failed integrity validation: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise ThreatConformanceBridgeError(
            "source_revision_integrity_failure",
            f"source revision failed integrity validation: {exc}",
        ) from exc

    try:
        manifest = kernel.load_world_graph_revision_manifest(root, world_id, revision_id)
    except Exception as exc:  # noqa: BLE001
        raise ThreatConformanceBridgeError(
            "source_revision_integrity_failure",
            f"revision manifest could not be loaded after integrity attestation: {exc}",
        ) from exc

    if manifest.world_id != world_id:
        raise ThreatConformanceBridgeError(
            "world_mismatch",
            "requested world_id does not match revision manifest world_id",
        )

    return _ExactBuddyRevisionBridgeSource(manifest=manifest, store=store)


def bridge_exact_buddy_world_object(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    node_id: str,
    campaign_id: str | None = None,
) -> DungeonMindWorldObjectConformanceBridgeResult:
    """Load one exact Buddy revision and bridge an explicit world object node.

    Never consults World Graph head. The supplied ``revision_id`` is authority.
    Owns integrity-attested loading so revision identity and store payload cannot
    be supplied independently at the public boundary.
    """
    source = _load_exact_buddy_revision_bridge_source(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    return _bridge_buddy_world_object_revision(
        source_world_id=world_id,
        source_revision=source.manifest,
        source_store=source.store,
        world_object_node_id=node_id,
        campaign_id=campaign_id,
    )


def bridge_exact_buddy_threat(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    threat_node_id: str,
    campaign_id: str | None = None,
) -> DungeonMindThreatConformanceBridgeResult:
    """Load one exact Buddy revision and bridge an explicit Threat node.

    Never consults World Graph head. The supplied ``revision_id`` is authority.
    Owns integrity-attested loading so revision identity and store payload cannot
    be supplied independently at the public boundary.
    """
    source = _load_exact_buddy_revision_bridge_source(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    return _bridge_buddy_world_object_revision(
        source_world_id=world_id,
        source_revision=source.manifest,
        source_store=source.store,
        world_object_node_id=threat_node_id,
        campaign_id=campaign_id,
        required_source_kind="threat",
        missing_node_reason="source_threat_missing",
    )
