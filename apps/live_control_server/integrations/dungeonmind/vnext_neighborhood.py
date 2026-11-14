"""Public result bounding for Core-authorized native neighborhood reads."""

from dataclasses import dataclass
from typing import Literal

from dungeonmind.application.vnext.neighborhood import NeighborhoodResult
from dungeonmind.application.vnext.records import ParsedAssertion, ParsedEntityRefValue

from graph_memory.retrieval.models import WorldGraphRetrievalBounds


@dataclass(frozen=True, slots=True)
class BoundedNeighborhood:
    node_ids: tuple[str, ...]
    edges: tuple[ParsedAssertion, ...]
    nodes_truncated: bool
    relationships_truncated: bool


def bound_neighborhood(
    result: NeighborhoodResult, seed_node_ids: list[str], bounds: WorldGraphRetrievalBounds
) -> BoundedNeighborhood:
    found = set(result.found_seed_entity_ids)
    seeds = tuple(dict.fromkeys(seed for seed in seed_node_ids if seed in found))
    remaining = max(bounds.max_nodes - len(seeds), 0)
    expanded = sorted(
        (depth, entity_id) for entity_id, depth in result.entity_depths if entity_id not in found
    )
    selected_ids = (*seeds, *(entity_id for _, entity_id in expanded[:remaining]))
    selected = set(selected_ids)
    edges = sorted(
        (
            edge for edge in result.traversal_assertions
            if isinstance(edge.value, ParsedEntityRefValue)
            and edge.subject_entity_id in selected
            and edge.value.entity_id in selected
        ),
        key=lambda edge: edge.assertion_id,
    )
    edge_limit = bounds.max_relationships
    return BoundedNeighborhood(
        node_ids=selected_ids,
        edges=tuple(edges[:edge_limit]),
        nodes_truncated=len(expanded) > remaining,
        relationships_truncated=len(edges) > edge_limit,
    )


def read_neighborhood(
    context, seed_node_ids: list[str], depth: Literal[1, 2], bounds: WorldGraphRetrievalBounds
) -> tuple[NeighborhoodResult, BoundedNeighborhood]:
    from dungeonmind.application.vnext.neighborhood import NeighborhoodReadService

    result = NeighborhoodReadService().get_neighborhood(
        context, seed_node_ids, depth, require_admitted_seeds=True
    )
    return result, bound_neighborhood(result, seed_node_ids, bounds)


def map_relationships(context, result: NeighborhoodResult, bounded: BoundedNeighborhood):
    """Present retained edges using only their admitted evidence."""
    from graph_memory.retrieval.models import WorldGraphRetrievalRelationship

    from .vnext_complete_object import _map_relationship, _source_presentation

    evidence = {row.evidence_ref_id: row for row in result.evidence}
    needed = {
        key for edge in bounded.edges for key in edge.metadata.evidence_ref_ids
    }
    if not bounded.edges:
        return []
    selected_evidence = {key: evidence[key] for key in needed}
    artifact_ids = tuple(sorted({row.source_artifact_id for row in selected_evidence.values()}))
    sources = {}
    if artifact_ids:
        snapshot = context.source_reader.get_provenance_snapshot(
            artifact_ids=artifact_ids, revision_ids=()
        )
        sources = {
            key: _source_presentation(snapshot.artifacts_by_id[key]) for key in artifact_ids
        }

    edges = []
    for assertion in bounded.edges:
        edge = _map_relationship(
            assertion,
            selected_entity_id=assertion.subject_entity_id,
            evidence_by_id=selected_evidence,
            source_by_id=sources,
        )
        edges.append(WorldGraphRetrievalRelationship(
            **edge.model_dump(include=set(WorldGraphRetrievalRelationship.model_fields)),
            direction_from_node_id=edge.source_node_id,
            source_domains=sorted({sources[key].source_domain for key in edge.source_artifact_ids}),
        ))
    return edges


def map_nodes(context, bounded: BoundedNeighborhood):
    """Resolve display claims only for entities retained in the response."""
    from dungeonmind.application.vnext import EntityReadService
    from graph_memory.retrieval.models import WorldGraphRetrievalNode

    from .vnext_complete_object import world_object_display_values

    reader = EntityReadService()
    nodes = []
    for entity_id in bounded.node_ids:
        result = reader.get_entity(context, entity_id)
        label, kind, summary = world_object_display_values(result.assertions, entity_id)
        nodes.append(WorldGraphRetrievalNode(
            node_id=entity_id, label=label, kind=kind, role=kind, summary=summary,
            evidence_ref_ids=[item.evidence_ref_id for item in result.evidence],
            source_artifact_ids=sorted({item.source_artifact_id for item in result.evidence}),
        ))
    return nodes


def native_anchor_id(assertion_id: str, evidence_ref_id: str) -> str:
    """Encode a source selector. Opening it still requires admission at the request pin."""
    from base64 import urlsafe_b64encode
    from json import dumps

    payload = dumps([assertion_id, evidence_ref_id], separators=(",", ":")).encode()
    return "native-neighborhood:" + urlsafe_b64encode(payload).decode("ascii")


def native_anchor_selection(anchor_id: str) -> tuple[str, str]:
    from base64 import b64decode
    from json import loads

    prefix, _, encoded = anchor_id.partition(":")
    if prefix != "native-neighborhood" or not 0 < len(encoded) <= 4096:
        raise ValueError("invalid native neighborhood anchor")
    try:
        fields = loads(b64decode(encoded, altchars=b"-_", validate=True))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid native neighborhood anchor") from exc
    if (
        not isinstance(fields, list)
        or len(fields) != 2
        or any(not isinstance(value, str) or not value.strip() for value in fields)
        or native_anchor_id(*fields) != anchor_id
    ):
        raise ValueError("invalid native neighborhood anchor")
    return fields[0], fields[1]
