"""Present authorized native vNext graph records in Buddy's projection DTO."""

from collections import defaultdict

from dungeonmind.application.vnext.native_source_access import (
    NativeTextSourceAccessContext,
    list_admitted_native_text_sources,
)
from dungeonmind.application.vnext.entity_reads import EntityListWithSupportResult
from dungeonmind.application.vnext.read_context import KnowledgeReadContext

from apps.live_control_server.integrations.dungeonmind.vnext_complete_object import (
    VNextCompleteObjectProjectionError,
    _map_assertion,
    _map_relationship,
    _source_presentation,
    world_object_display_values,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_reads import _expansion_views
from apps.live_control_server.services.native_source_display import source_display_metadata
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionAdjacencyCandidate,
    WorldGraphProjectionAttributeView,
    WorldGraphProjectionEvidenceBadge,
    WorldGraphProjectionEvidenceView,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRelationshipView,
    WorldGraphProjectionSourceArtifactView,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionSummary,
    WorldGraphProjectionTrustBoundary,
    WorldGraphQueryContext,
    rank_search_node_matches,
)


def project_source_views(
    context: KnowledgeReadContext, support: EntityListWithSupportResult,
    *, access: NativeTextSourceAccessContext, managed_world_id: str,
) -> tuple[
    list[WorldGraphProjectionEvidenceView],
    list[WorldGraphProjectionSourceArtifactView],
]:
    """Resolve presentation for admitted artifacts in one bulk read."""
    artifact_ids = tuple(sorted({item.source_artifact_id for item in support.evidence}))
    if not artifact_ids:
        return [], []

    presentation = context.source_reader.get_provenance_snapshot(
        artifact_ids=artifact_ids, revision_ids=()
    )
    selected = list_admitted_native_text_sources(
        access, evidence_ref_ids=[row.evidence_ref_id for row in support.evidence]
    ).sources
    by_evidence = {}
    by_artifact = defaultdict(list)
    for source, display in zip(
        selected, source_display_metadata(selected, managed_world_id), strict=True
    ):
        if display["origin_matches_current_metadata"] is True:
            scope = (display["campaign_id"], display["session_id"])
            by_artifact[source.source_artifact.source_artifact_id].append(scope)
            for evidence_id in source.evidence_ref_ids:
                by_evidence[evidence_id] = scope

    artifacts = {}
    intrinsic_scopes = {}
    for artifact_id in artifact_ids:
        artifact = presentation.get_artifact(artifact_id)
        if artifact is None:
            raise VNextCompleteObjectProjectionError("admitted source disappeared")
        metadata = _source_presentation(artifact)
        intrinsic_scopes[artifact_id] = (metadata.campaign_id, metadata.session_id)
        scopes = set(by_artifact[artifact_id])
        campaign_id, session_id = next(iter(scopes)) if len(scopes) == 1 else (None, None)
        artifacts[artifact_id] = WorldGraphProjectionSourceArtifactView(
            source_artifact_id=artifact_id,
            source_domain=metadata.source_domain,
            uri=artifact.uri or "",
            campaign_id=metadata.campaign_id or campaign_id or "",
            session_id=metadata.session_id or session_id,
        )

    evidence = []
    for item in support.evidence:
        artifact_view = artifacts[item.source_artifact_id]
        campaign_id, session_id = by_evidence.get(item.evidence_ref_id, (None, None))
        intrinsic_campaign, intrinsic_session = intrinsic_scopes[item.source_artifact_id]
        evidence.append(
            WorldGraphProjectionEvidenceView(
                evidence_ref_id=item.evidence_ref_id,
                source_artifact_id=item.source_artifact_id,
                source_domain=artifact_view.source_domain,
                session_id=intrinsic_session or session_id,
                campaign_id=intrinsic_campaign or campaign_id,
                locator=item.locator,
                source_span_ref_id=item.source_span_ref_id,
            )
        )
    return evidence, list(artifacts.values())


def project_assertion_views(context, support, artifacts, evidence):
    """Map the admitted assertions into overview attributes and directed edges."""
    evidence_by_id = {item.evidence_ref_id: item for item in support.evidence}
    source_by_id = {item.source_artifact_id: item for item in artifacts}
    session_by_evidence = {row.evidence_ref_id: row.session_id for row in evidence}
    attributes = []
    relationships = []
    for assertion_id in support.listing.admitted_assertion_ids:
        assertion = context.parsed.get_assertion(assertion_id)
        if assertion is None:
            raise VNextCompleteObjectProjectionError("admitted assertion disappeared")
        if assertion.value.kind == "entity_ref":
            edge = _map_relationship(
                assertion,
                selected_entity_id=assertion.subject_entity_id,
                evidence_by_id=evidence_by_id,
                source_by_id=source_by_id,
            )
            relationships.append(
                WorldGraphProjectionRelationshipView(
                    **edge.model_dump(
                        include=set(WorldGraphProjectionRelationshipView.model_fields),
                        exclude={"session_ids"},
                    ),
                    session_ids=sorted({
                        session_by_evidence[key]
                        for key in edge.evidence_ref_ids
                        if session_by_evidence[key] is not None
                    }),
                    source_domains=sorted({
                        source_by_id[source_id].source_domain
                        for source_id in edge.source_artifact_ids
                    }),
                )
            )
        else:
            attribute = _map_assertion(assertion, evidence_by_id=evidence_by_id)
            attributes.append(
                WorldGraphProjectionAttributeView(
                    **attribute.model_dump(include=set(WorldGraphProjectionAttributeView.model_fields))
                )
            )
    return attributes, relationships


def project_node_views(context, support, attributes, artifacts, evidence):
    """Present each admitted entity with its own evidence and authorized aliases."""
    assertions_by_entity = defaultdict(list)
    for attribute in attributes:
        assertion = context.parsed.get_assertion(attribute.assertion_id)
        assertions_by_entity[attribute.subject_node_id].append(assertion)
    attributes_by_entity = defaultdict(list)
    for attribute in attributes:
        attributes_by_entity[attribute.subject_node_id].append(attribute)
    aliases_by_entity = defaultdict(set)
    for alias in support.aliases:
        aliases_by_entity[alias.entity_id].add(alias.alias_text)
    sources = {item.source_artifact_id: item for item in artifacts}
    evidence_views = {item.evidence_ref_id: item for item in evidence}
    badges = {
        item.evidence_ref_id: WorldGraphProjectionEvidenceBadge(
            evidence_ref_id=item.evidence_ref_id,
            source_artifact_id=item.source_artifact_id,
            source_domain=sources[item.source_artifact_id].source_domain,
            evidence_role=item.evidence_role,
            can_open_source=item.can_open_source,
            can_highlight_span=item.can_highlight_span,
            session_id=evidence_views[item.evidence_ref_id].session_id,
            source_span_ref_id=item.source_span_ref_id,
        )
        for item in support.evidence
    }

    nodes = []
    for entity in support.listing.entities:
        entity_id = entity.entity_id
        label, kind, summary = world_object_display_values(
            assertions_by_entity[entity_id], entity_id
        )
        own_attributes = attributes_by_entity[entity_id]
        evidence_ids = sorted({key for row in own_attributes for key in row.evidence_ref_ids})
        artifact_ids = sorted({key for row in own_attributes for key in row.source_artifact_ids})
        nodes.append(
            WorldGraphProjectionNodeView(
                node_id=entity_id,
                label=label,
                kind=kind,
                role=kind,
                summary=summary,
                aliases=sorted(aliases_by_entity[entity_id]),
                evidence_ref_ids=evidence_ids,
                source_artifact_ids=artifact_ids,
                source_domains=sorted({sources[key].source_domain for key in artifact_ids}),
                evidence_badges=[badges[key] for key in evidence_ids],
            )
        )
    return nodes


def attach_adjacency(
    nodes: list[WorldGraphProjectionNodeView],
    relationships: list[WorldGraphProjectionRelationshipView],
) -> None:
    """Attach each edge from the perspective of both admitted endpoints."""
    by_id = {node.node_id: node for node in nodes}
    for edge in relationships:
        source = by_id[edge.source_node_id]
        target = by_id[edge.target_node_id]
        endpoints = [(source, target, "outgoing")]
        if source.node_id != target.node_id:
            endpoints.append((target, source, "incoming"))
        for node, related, direction in endpoints:
            node.adjacency.append(
                WorldGraphProjectionAdjacencyCandidate(
                    edge_id=edge.edge_id,
                    node_id=related.node_id,
                    label=related.label,
                    kind=related.kind,
                    predicate=edge.predicate,
                    direction=direction,
                    source_domains=edge.source_domains,
                    evidence_ref_ids=edge.evidence_ref_ids,
                    edge_label=edge.label,
                    session_ids=edge.session_ids,
                    campaign_scope=edge.campaign_scope,
                    related_summary=related.summary,
                )
            )


def project_native_world(
    context: KnowledgeReadContext,
    support: EntityListWithSupportResult,
    snapshot: WorldGraphProjectionSnapshot,
    *, access: NativeTextSourceAccessContext, managed_world_id: str,
) -> WorldGraphProjection:
    """Assemble the overview from one pinned, admitted graph read."""
    if support.listing.completeness.status != "complete":
        raise VNextCompleteObjectProjectionError("native projection is incomplete")

    evidence, artifacts = project_source_views(
        context, support, access=access, managed_world_id=managed_world_id
    )
    attributes, relationships = project_assertion_views(context, support, artifacts, evidence)
    nodes = project_node_views(context, support, attributes, artifacts, evidence)
    # Keep display assertions in node evidence, but present them only as node fields.
    attributes = [
        row for row in attributes
        if context.parsed.get_assertion(row.assertion_id).predicate
        not in {"dnd5e:name", "dnd5e:classification", "dnd5e:summary"}
    ]
    attach_adjacency(nodes, relationships)
    degree_by_node = {node.node_id: len(node.adjacency) for node in nodes}
    for node in nodes:
        node.suggested_expansions = _expansion_views(
            node.adjacency, degree_by_node=degree_by_node
        )
    return WorldGraphProjection(
        schema="dmb_world_graph_projection_v1",
        snapshot=snapshot,
        summary=WorldGraphProjectionSummary(
            node_count=len(nodes),
            relationship_count=len(relationships),
            attribute_count=len(attributes),
            evidence_count=len(evidence),
            source_artifact_count=len(artifacts),
        ),
        nodes=nodes,
        relationships=relationships,
        attributes=attributes,
        evidence=evidence,
        source_artifacts=artifacts,
        trust_boundary=WorldGraphProjectionTrustBoundary(
            can_trust=["Admitted records at the requested graph revision."],
            cannot_trust=["Completeness beyond the requested scope."],
        ),
    )


def project_query_context(
    projection: WorldGraphProjection, query_text: str
) -> WorldGraphQueryContext:
    """Rank and narrow only records admitted into the pinned overview."""
    ranked, reasons = rank_search_node_matches(
        projection.nodes, projection.attributes, query_text
    )
    nodes = [node for node, _ in ranked]
    matched_ids = [node.node_id for node in nodes]
    matched = set(matched_ids)
    attributes = [
        row for row in projection.attributes if row.subject_node_id in matched
    ]
    relationships = [
        row for row in projection.relationships
        if row.source_node_id in matched or row.target_node_id in matched
    ]
    evidence_ids = {
        key for row in [*nodes, *attributes, *relationships] for key in row.evidence_ref_ids
    }
    evidence = [row for row in projection.evidence if row.evidence_ref_id in evidence_ids]
    artifact_ids = {row.source_artifact_id for row in evidence}
    return WorldGraphQueryContext(
        snapshot=projection.snapshot,
        revision_id=projection.snapshot.revision_id,
        query_text=query_text,
        matched_node_ids=matched_ids,
        match_reasons={key: reasons[key] for key in matched_ids},
        nodes=nodes,
        attributes=attributes,
        relationships=relationships,
        evidence=evidence,
        source_artifacts=[
            row for row in projection.source_artifacts if row.source_artifact_id in artifact_ids
        ],
    )
