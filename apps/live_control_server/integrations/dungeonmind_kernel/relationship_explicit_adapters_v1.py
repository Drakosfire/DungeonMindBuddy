"""Governed Eldyrwild explicit relationship adapters (PR #526 Buddy slice).

Three adjudicated ``EXPLICIT_ADAPTER_CANDIDATE`` edges are representable via
existing ``world-object-v4`` terms after an explicit rename and/or endpoint
reversal. Adapters are catalog-bound and domain-bound — never global by
Buddy predicate name, edge-label text, or edge-id suffix.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_world_object_v4_vocabulary,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _predicate_allowed_endpoints,
)
from graph_memory.union_supergraph.model import (
    UnionSupergraphEdge,
    UnionSupergraphStore,
)

RELATIONSHIP_EXPLICIT_ADAPTER_CATALOG_SCHEMA_V1 = (
    "dmb_dungeonmind_relationship_explicit_adapter_catalog_v1"
)
_ADJUDICATION_SCHEMA = "dmb_dungeonmind_relationship_residual_adjudication_v1"

_CATALOG_WORLD_ID = "eldyrwild"
_CATALOG_CAMPAIGN_ID = "longmont-c2"
_CATALOG_REVISION_ID = "rev:3413bf6f5044cf2680233f5e37c90dcf"
_CATALOG_GRAPH_PAYLOAD_SHA256 = (
    "346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa"
)

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


class RelationshipExplicitAdapterIntegrityError(RuntimeError):
    """Raised when a catalog edge ID is present but its durable shape drifted."""


class RelationshipExplicitAdapterV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    expected_buddy_predicate: str
    expected_source_node_id: str
    expected_source_buddy_kind: str
    expected_target_node_id: str
    expected_target_buddy_kind: str
    dungeonmind_term: str
    reverse_endpoints: bool
    adjudication_disposition: Literal["EXPLICIT_ADAPTER_CANDIDATE"]
    adjudication_reason_code: str
    requires_source_mutation: Literal[False]
    adjudication_schema: str = _ADJUDICATION_SCHEMA
    grounding_evidence_ref_id: str | None = None
    grounding_source_artifact_id: str | None = None
    grounding_artifact_content_sha256: str | None = None
    grounding_source_span_ref_id: str | None = None
    grounding_locator_kind: str | None = None
    grounding_locator: str | None = None
    grounding_excerpt_sha256: str | None = None


class RelationshipExplicitAdapterCatalogV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = RELATIONSHIP_EXPLICIT_ADAPTER_CATALOG_SCHEMA_V1
    world_id: str
    campaign_id: str
    source_revision_id: str
    source_graph_payload_sha256: str
    adjudication_schema: str = _ADJUDICATION_SCHEMA
    records: list[RelationshipExplicitAdapterV1] = Field(default_factory=list)


class ResolvedRelationshipExplicitAdapterV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    dungeonmind_term: str
    reverse_endpoints: bool
    effective_subject_node_id: str
    effective_object_node_id: str
    effective_subject_dm_kind: str
    effective_object_dm_kind: str
    expected_buddy_predicate: str
    adjudication_reason_code: str


def _catalog_records() -> list[RelationshipExplicitAdapterV1]:
    """Immutable Eldyrwild explicit-adapter catalog (exactly three rows)."""
    return [
        RelationshipExplicitAdapterV1(
            edge_id="edge:item:session17:seed:located_in:pc:stafl",
            expected_buddy_predicate="located_in",
            expected_source_node_id="item:session17:seed",
            expected_source_buddy_kind="item",
            expected_target_node_id="pc:stafl",
            expected_target_buddy_kind="pc",
            dungeonmind_term="dnd5e:holds",
            reverse_endpoints=True,
            adjudication_disposition="EXPLICIT_ADAPTER_CANDIDATE",
            adjudication_reason_code="REVERSE_ENDPOINT_FORM",
            requires_source_mutation=False,
            grounding_evidence_ref_id=(
                "evidence:artifact:recap:longmont-c1:session-17:"
                "session-17:recap:paragraph:008"
            ),
            grounding_source_artifact_id="artifact:recap:longmont-c1:session-17",
            grounding_artifact_content_sha256=(
                "90823bf0610beca9fee22df4806a318b1f892c3c194a434563f6f37250b0690f"
            ),
            grounding_source_span_ref_id="session-17:recap:paragraph:008",
            grounding_locator_kind="paragraph",
            grounding_locator="paragraph:008",
            grounding_excerpt_sha256=(
                "77e26f31ebf8253a2dafbf3eb6d1a1514cb4c96ced996d0da63c7c2a3921f461"
            ),
        ),
        RelationshipExplicitAdapterV1(
            edge_id="edge:node:cultists_of_longmont:part_of:node:lesandra:led-by",
            expected_buddy_predicate="part_of",
            expected_source_node_id="node:cultists_of_longmont",
            expected_source_buddy_kind="faction",
            expected_target_node_id="node:lesandra",
            expected_target_buddy_kind="npc",
            dungeonmind_term="dnd5e:leads",
            reverse_endpoints=True,
            adjudication_disposition="EXPLICIT_ADAPTER_CANDIDATE",
            adjudication_reason_code="REVERSE_ENDPOINT_FORM",
            requires_source_mutation=False,
            grounding_evidence_ref_id=(
                "evidence:artifact:recap:longmont-c1:session-17:"
                "session-17:recap:paragraph:015"
            ),
            grounding_source_artifact_id="artifact:recap:longmont-c1:session-17",
            grounding_artifact_content_sha256=(
                "90823bf0610beca9fee22df4806a318b1f892c3c194a434563f6f37250b0690f"
            ),
            grounding_source_span_ref_id="session-17:recap:paragraph:015",
            grounding_locator_kind="paragraph",
            grounding_locator="paragraph:015",
            grounding_excerpt_sha256=(
                "f9abc60ff4f7fcf05a30c58f7e6029c3af23844a3dcd76857e18fc593b02a0d1"
            ),
        ),
        RelationshipExplicitAdapterV1(
            edge_id="edge:node:pippa:leads_to:loc:stone_bridge",
            expected_buddy_predicate="leads_to",
            expected_source_node_id="node:pippa",
            expected_source_buddy_kind="npc",
            expected_target_node_id="loc:stone_bridge",
            expected_target_buddy_kind="location",
            dungeonmind_term="dnd5e:travels_to",
            reverse_endpoints=False,
            adjudication_disposition="EXPLICIT_ADAPTER_CANDIDATE",
            adjudication_reason_code="EXPLICIT_RENAME_TO_EXISTING",
            requires_source_mutation=False,
            grounding_evidence_ref_id=(
                "evidence:artifact:recap:longmont-c1:session-3:"
                "session-3:recap:paragraph:017"
            ),
            grounding_source_artifact_id="artifact:recap:longmont-c1:session-3",
            grounding_artifact_content_sha256=(
                "4bf9af0ca38f99e41fee48df1b881c1094568a9d02baa1644b27e42bb65ed107"
            ),
            grounding_source_span_ref_id="session-3:recap:paragraph:017",
            grounding_locator_kind="paragraph",
            grounding_locator="paragraph:017",
            grounding_excerpt_sha256=(
                "ebdd6b5edb7de8d328b71c232edd32973af6985baae104adefc0896673f6b1e4"
            ),
        ),
    ]


def load_eldyrwild_relationship_explicit_adapter_catalog_v1() -> (
    RelationshipExplicitAdapterCatalogV1
):
    """Load the immutable Eldyrwild explicit-adapter catalog and validate endpoints."""
    catalog = RelationshipExplicitAdapterCatalogV1(
        schema_version=RELATIONSHIP_EXPLICIT_ADAPTER_CATALOG_SCHEMA_V1,
        world_id=_CATALOG_WORLD_ID,
        campaign_id=_CATALOG_CAMPAIGN_ID,
        source_revision_id=_CATALOG_REVISION_ID,
        source_graph_payload_sha256=_CATALOG_GRAPH_PAYLOAD_SHA256,
        adjudication_schema=_ADJUDICATION_SCHEMA,
        records=_catalog_records(),
    )
    validate_explicit_adapter_catalog_endpoints_v1(catalog)
    return catalog


def matches_explicit_adapter_domain_v1(
    *,
    world_id: str,
    revision_id: str,
    graph_payload_sha256: str,
) -> bool:
    return (
        world_id == _CATALOG_WORLD_ID
        and revision_id == _CATALOG_REVISION_ID
        and graph_payload_sha256 == _CATALOG_GRAPH_PAYLOAD_SHA256
    )


def _dm_kind_for_buddy_kind(buddy_kind: str) -> str | None:
    return _BUDDY_TO_DM_KIND.get(buddy_kind)


def _node_buddy_kind(store: UnionSupergraphStore, node_id: str) -> str | None:
    node = store.nodes.get(node_id)
    if node is None:
        return None
    kind = node.kind
    if not isinstance(kind, str) or not kind.strip():
        return None
    return kind


def validate_explicit_adapter_catalog_endpoints_v1(
    catalog: RelationshipExplicitAdapterCatalogV1,
    *,
    vocabulary: Any | None = None,
) -> None:
    """Fail closed if any catalog row's effective endpoints are not admitted by v4."""
    vocab = vocabulary if vocabulary is not None else load_builtin_world_object_v4_vocabulary()
    if getattr(vocab, "vocabulary_revision", None) != "world-object-v4":
        raise RelationshipExplicitAdapterIntegrityError(
            f"explicit adapters require world-object-v4; got "
            f"{getattr(vocab, 'vocabulary_revision', None)!r}"
        )
    for record in catalog.records:
        if record.requires_source_mutation:
            raise RelationshipExplicitAdapterIntegrityError(
                f"adapter {record.edge_id!r} requires_source_mutation=true"
            )
        allowed = _predicate_allowed_endpoints(record.dungeonmind_term, vocab)
        if allowed is None:
            raise RelationshipExplicitAdapterIntegrityError(
                f"world-object-v4 missing predicate {record.dungeonmind_term!r}"
            )
        subject_kinds, object_kinds = allowed
        src_dm = _dm_kind_for_buddy_kind(record.expected_source_buddy_kind)
        tgt_dm = _dm_kind_for_buddy_kind(record.expected_target_buddy_kind)
        if src_dm is None or tgt_dm is None:
            raise RelationshipExplicitAdapterIntegrityError(
                f"adapter {record.edge_id!r} has unmapped Buddy kinds "
                f"{record.expected_source_buddy_kind!r}/"
                f"{record.expected_target_buddy_kind!r}"
            )
        if record.reverse_endpoints:
            admit_src, admit_tgt = tgt_dm, src_dm
        else:
            admit_src, admit_tgt = src_dm, tgt_dm
        if admit_src not in subject_kinds or admit_tgt not in object_kinds:
            raise RelationshipExplicitAdapterIntegrityError(
                f"adapter {record.edge_id!r} effective endpoints "
                f"{admit_src} --{record.dungeonmind_term}--> {admit_tgt} "
                f"not admitted by world-object-v4"
            )


def _assert_shape_matches_catalog(
    record: RelationshipExplicitAdapterV1,
    *,
    edge: UnionSupergraphEdge,
    store: UnionSupergraphStore,
) -> None:
    mismatches: list[str] = []
    if edge.predicate != record.expected_buddy_predicate:
        mismatches.append(
            f"predicate expected {record.expected_buddy_predicate!r} "
            f"got {edge.predicate!r}"
        )
    if edge.source_node_id != record.expected_source_node_id:
        mismatches.append(
            f"source_node_id expected {record.expected_source_node_id!r} "
            f"got {edge.source_node_id!r}"
        )
    if edge.target_node_id != record.expected_target_node_id:
        mismatches.append(
            f"target_node_id expected {record.expected_target_node_id!r} "
            f"got {edge.target_node_id!r}"
        )
    source_kind = _node_buddy_kind(store, edge.source_node_id)
    target_kind = _node_buddy_kind(store, edge.target_node_id)
    if source_kind != record.expected_source_buddy_kind:
        mismatches.append(
            f"source_buddy_kind expected {record.expected_source_buddy_kind!r} "
            f"got {source_kind!r}"
        )
    if target_kind != record.expected_target_buddy_kind:
        mismatches.append(
            f"target_buddy_kind expected {record.expected_target_buddy_kind!r} "
            f"got {target_kind!r}"
        )
    if mismatches:
        raise RelationshipExplicitAdapterIntegrityError(
            f"explicit adapter integrity failure for {record.edge_id}: "
            + "; ".join(mismatches)
        )


def resolve_relationship_explicit_adapter_v1(
    *,
    world_id: str,
    revision_id: str,
    graph_payload_sha256: str,
    edge: UnionSupergraphEdge,
    store: UnionSupergraphStore,
    catalog: RelationshipExplicitAdapterCatalogV1 | None = None,
    vocabulary: Any | None = None,
) -> ResolvedRelationshipExplicitAdapterV1 | None:
    """Resolve a catalog-bound explicit adapter, or ``None`` outside domain/catalog.

    Raises ``RelationshipExplicitAdapterIntegrityError`` when the edge ID is in
    the catalog but the durable shape drifted, or when endpoints are not admitted.
    """
    if not matches_explicit_adapter_domain_v1(
        world_id=world_id,
        revision_id=revision_id,
        graph_payload_sha256=graph_payload_sha256,
    ):
        return None

    loaded = catalog if catalog is not None else load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    by_id = {record.edge_id: record for record in loaded.records}
    record = by_id.get(edge.edge_id)
    if record is None:
        return None

    _assert_shape_matches_catalog(record, edge=edge, store=store)
    validate_explicit_adapter_catalog_endpoints_v1(
        RelationshipExplicitAdapterCatalogV1(
            schema_version=loaded.schema_version,
            world_id=loaded.world_id,
            campaign_id=loaded.campaign_id,
            source_revision_id=loaded.source_revision_id,
            source_graph_payload_sha256=loaded.source_graph_payload_sha256,
            adjudication_schema=loaded.adjudication_schema,
            records=[record],
        ),
        vocabulary=vocabulary,
    )

    if record.reverse_endpoints:
        subject_id = edge.target_node_id
        object_id = edge.source_node_id
        subject_buddy = record.expected_target_buddy_kind
        object_buddy = record.expected_source_buddy_kind
    else:
        subject_id = edge.source_node_id
        object_id = edge.target_node_id
        subject_buddy = record.expected_source_buddy_kind
        object_buddy = record.expected_target_buddy_kind

    subject_dm = _dm_kind_for_buddy_kind(subject_buddy)
    object_dm = _dm_kind_for_buddy_kind(object_buddy)
    assert subject_dm is not None and object_dm is not None

    return ResolvedRelationshipExplicitAdapterV1(
        edge_id=edge.edge_id,
        dungeonmind_term=record.dungeonmind_term,
        reverse_endpoints=record.reverse_endpoints,
        effective_subject_node_id=subject_id,
        effective_object_node_id=object_id,
        effective_subject_dm_kind=subject_dm,
        effective_object_dm_kind=object_dm,
        expected_buddy_predicate=record.expected_buddy_predicate,
        adjudication_reason_code=record.adjudication_reason_code,
    )


def catalog_edge_ids_v1(
    catalog: RelationshipExplicitAdapterCatalogV1 | None = None,
) -> list[str]:
    loaded = catalog if catalog is not None else load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    return [record.edge_id for record in loaded.records]
