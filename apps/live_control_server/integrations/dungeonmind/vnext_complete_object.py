"""Dormant Buddy adapter from native vNext complete reads to the World-object DTO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dungeonmind.application.vnext import (
    EntityReadService,
    ParsedAssertion,
    ParsedDomainTemporalScope,
    ParsedEntityRefValue,
    ParsedLabelsAllVisibility,
    ParsedLabelsAnyVisibility,
    ParsedKnowledgeRevision,
    ParsedLiteralValue,
    ParsedPublicVisibility,
    ParsedTermRefValue,
    ParsedTimelessTemporalScope,
    ParsedUnknownTemporalScope,
    ParsedUtcIntervalTemporalScope,
    thaw_json_value,
)
from dungeonmind.application.vnext.ports import KnowledgeSourceReader

from apps.live_control_server.models.world_graph_object_projection import (
    SelectedObjectCompletenessView,
    WorldGraphObjectProjectionAssertion,
    WorldGraphObjectProjectionRelationship,
    WorldGraphObjectProjectionRequest,
    WorldGraphObjectProjectionResult,
    WorldGraphObjectProjectionSourceBinding,
    WorldGraphObjectProjectionTelemetry,
    object_projection_semantic_fingerprint,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjectionAdjacencyCandidate,
    WorldGraphProjectionEvidenceBadge,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionSnapshot,
)
from graph_memory.vnext import (
    DungeonBuddyVNextProjectionInput,
    build_dungeonbuddy_read_context,
)

_CAMPAIGN_SCOPE = "dungeonbuddy.scope:campaign"
_PLAYER_LABEL = "dungeonbuddy.visibility:player"
_GM_LABEL = "dungeonbuddy.visibility:gm"
_SOURCE_CONTEXT_SCHEMA = "dungeonbuddy.source:context_v1"
_CLAIM_MODE_WIRE = {
    "dungeonbuddy.claim:fact": "fact",
    "dungeonbuddy.claim:belief": "belief",
    "dungeonbuddy.claim:rumor": "rumor",
    "dungeonbuddy.claim:plan": "plan",
    "dungeonbuddy.claim:observed_event": "observed_event",
}


class VNextCompleteObjectProjectionError(ValueError):
    """Fail-closed Buddy presentation error for the dormant vNext adapter."""


@dataclass(frozen=True, slots=True)
class DungeonBuddyVNextReadIdentity:
    """Already-selected exact read identity; this value never chooses authority."""

    space_id: str
    revision_id: str
    head_revision_id: str
    is_head: bool


@dataclass(frozen=True, slots=True)
class _SourcePresentation:
    source_domain: str
    campaign_id: str | None
    session_id: str | None


def _wire_term(term: str) -> str:
    return term.removeprefix("dnd5e:") if term.startswith("dnd5e:") else term


def _source_domain(term: str) -> str:
    prefix = "dungeonbuddy.source:"
    return term.removeprefix(prefix) if term.startswith(prefix) else term


def _campaign_scope(assertion: ParsedAssertion) -> str | None:
    values = {
        binding.value
        for binding in assertion.metadata.scope
        if binding.axis == _CAMPAIGN_SCOPE
    }
    if len(values) > 1:
        raise VNextCompleteObjectProjectionError(
            f"assertion {assertion.assertion_id} has conflicting campaign scope"
        )
    return next(iter(values), None)


def _visibility(assertion: ParsedAssertion) -> str:
    visibility = assertion.metadata.visibility
    if isinstance(visibility, ParsedPublicVisibility):
        return "player"
    if isinstance(visibility, ParsedLabelsAnyVisibility):
        labels = set(visibility.labels)
        return "player" if _PLAYER_LABEL in labels else "gm"
    if isinstance(visibility, ParsedLabelsAllVisibility):
        labels = set(visibility.labels)
        return "gm" if _GM_LABEL in labels else "player"
    raise VNextCompleteObjectProjectionError("unsupported vNext visibility")


def _epistemic_kind(assertion: ParsedAssertion) -> str:
    try:
        return _CLAIM_MODE_WIRE[assertion.metadata.claim_mode]
    except KeyError as exc:
        raise VNextCompleteObjectProjectionError(
            f"unsupported Buddy claim mode: {assertion.metadata.claim_mode}"
        ) from exc


def _temporal_scope(assertion: ParsedAssertion) -> dict[str, Any]:
    temporal = assertion.metadata.temporal_scope
    if isinstance(temporal, ParsedTimelessTemporalScope):
        return {"kind": "timeless"}
    if isinstance(temporal, ParsedUnknownTemporalScope):
        return {"kind": "unknown"}
    if isinstance(temporal, ParsedUtcIntervalTemporalScope):
        return {
            "kind": "utc_interval",
            "valid_from": temporal.valid_from.isoformat()
            if temporal.valid_from
            else None,
            "valid_until": temporal.valid_until.isoformat()
            if temporal.valid_until
            else None,
        }
    if isinstance(temporal, ParsedDomainTemporalScope):
        return {
            "kind": "domain_ref",
            "schema": temporal.schema_term,
            "payload": thaw_json_value(temporal.payload),
        }
    raise VNextCompleteObjectProjectionError("unsupported vNext temporal scope")


def _distinct_subject_values(
    assertions: tuple[ParsedAssertion, ...],
    *,
    entity_id: str,
    predicate: str,
    value_kind: type[ParsedLiteralValue] | type[ParsedTermRefValue],
) -> list[str]:
    values: set[str] = set()
    for assertion in assertions:
        if assertion.subject_entity_id != entity_id or assertion.predicate != predicate:
            continue
        value = assertion.value
        if not isinstance(value, value_kind):
            raise VNextCompleteObjectProjectionError(
                f"{predicate} has unsupported value kind on {entity_id}"
            )
        raw = value.value if isinstance(value, ParsedLiteralValue) else value.term
        if not isinstance(raw, str):
            raise VNextCompleteObjectProjectionError(
                f"{predicate} must carry a string on {entity_id}"
            )
        values.add(raw)
    return sorted(values)


def _display_values(
    assertions: tuple[ParsedAssertion, ...], entity_id: str
) -> tuple[str, str, str | None]:
    names = _distinct_subject_values(
        assertions,
        entity_id=entity_id,
        predicate="dnd5e:name",
        value_kind=ParsedLiteralValue,
    )
    if len(names) > 1:
        raise VNextCompleteObjectProjectionError(
            f"ambiguous dnd5e:name for {entity_id}"
        )
    classifications = _distinct_subject_values(
        assertions,
        entity_id=entity_id,
        predicate="dnd5e:classification",
        value_kind=ParsedTermRefValue,
    )
    if len(classifications) > 1:
        raise VNextCompleteObjectProjectionError(
            f"ambiguous dnd5e:classification for {entity_id}"
        )
    summaries = _distinct_subject_values(
        assertions,
        entity_id=entity_id,
        predicate="dnd5e:summary",
        value_kind=ParsedLiteralValue,
    )
    return (
        names[0] if names else entity_id,
        _wire_term(classifications[0]) if classifications else "entity",
        summaries[0] if len(summaries) == 1 else None,
    )


def _source_presentation(artifact: Any) -> _SourcePresentation:
    payloads: list[dict[str, Any]] = []
    for entry in artifact.domain_metadata:
        if entry.schema_term == _SOURCE_CONTEXT_SCHEMA:
            value = thaw_json_value(entry.payload)
            if not isinstance(value, dict):
                raise VNextCompleteObjectProjectionError(
                    f"invalid source context metadata: {artifact.source_artifact_id}"
                )
            payloads.append(value)
    if any(payload != payloads[0] for payload in payloads[1:]):
        raise VNextCompleteObjectProjectionError(
            f"conflicting source context metadata: {artifact.source_artifact_id}"
        )
    payload = payloads[0] if payloads else {}
    campaign_id = payload.get("campaign_id")
    session_id = payload.get("session_id")
    if campaign_id is not None and (
        not isinstance(campaign_id, str) or not campaign_id.strip()
    ):
        raise VNextCompleteObjectProjectionError("source campaign_id must be nonblank")
    if session_id is not None and (
        not isinstance(session_id, str) or not session_id.strip()
    ):
        raise VNextCompleteObjectProjectionError("source session_id must be nonblank")
    return _SourcePresentation(
        source_domain=_source_domain(artifact.source_classification),
        campaign_id=campaign_id,
        session_id=session_id,
    )


def _focus_match(
    request: WorldGraphObjectProjectionRequest,
    source: _SourcePresentation,
) -> bool:
    if request.focus.kind != "session" or source.session_id != request.focus.session_id:
        return False
    focus_campaign = request.focus.campaign_id or request.campaign_id
    return source.campaign_id == focus_campaign


def _evidence_badges(
    evidence_ids: list[str],
    *,
    evidence_by_id: dict[str, Any],
    source_by_id: dict[str, _SourcePresentation],
    request: WorldGraphObjectProjectionRequest,
) -> list[WorldGraphProjectionEvidenceBadge]:
    badges: list[WorldGraphProjectionEvidenceBadge] = []
    for evidence_id in sorted(set(evidence_ids)):
        evidence = evidence_by_id[evidence_id]
        source = source_by_id[evidence.source_artifact_id]
        badges.append(
            WorldGraphProjectionEvidenceBadge(
                evidence_ref_id=evidence.evidence_ref_id,
                source_artifact_id=evidence.source_artifact_id,
                source_domain=source.source_domain,
                evidence_role=evidence.evidence_role,
                is_focus_session_evidence=_focus_match(request, source),
                can_open_source=evidence.can_open_source,
                can_highlight_span=evidence.can_highlight_span,
                session_id=source.session_id,
                source_span_ref_id=evidence.source_span_ref_id,
            )
        )
    return badges


def _assertion_value(assertion: ParsedAssertion) -> tuple[str | None, dict[str, Any]]:
    value = assertion.value
    if isinstance(value, ParsedLiteralValue):
        thawed = thaw_json_value(value.value)
        if isinstance(thawed, str):
            return thawed, {}
        if isinstance(thawed, dict):
            return None, thawed
        raise VNextCompleteObjectProjectionError(
            f"literal cannot be represented losslessly: {assertion.assertion_id}"
        )
    if isinstance(value, ParsedTermRefValue):
        return _wire_term(value.term), {"term": value.term}
    raise VNextCompleteObjectProjectionError(
        f"unsupported property value: {assertion.assertion_id}"
    )


def _source_ids(
    assertion: ParsedAssertion, evidence_by_id: dict[str, Any]
) -> list[str]:
    return sorted(
        {
            evidence_by_id[evidence_id].source_artifact_id
            for evidence_id in assertion.metadata.evidence_ref_ids
        }
    )


def _map_assertion(
    assertion: ParsedAssertion,
    *,
    evidence_by_id: dict[str, Any],
) -> WorldGraphObjectProjectionAssertion:
    text_value, value = _assertion_value(assertion)
    is_summary = assertion.predicate == "dnd5e:summary"
    return WorldGraphObjectProjectionAssertion(
        assertion_id=assertion.assertion_id,
        subject_node_id=assertion.subject_entity_id,
        assertion_kind="summary" if is_summary else "property",
        predicate="summary" if is_summary else _wire_term(assertion.predicate),
        label="summary" if is_summary else assertion.predicate,
        text_value=text_value,
        value=value,
        summary=text_value if is_summary else None,
        epistemic_kind=_epistemic_kind(assertion),
        visibility=_visibility(assertion),
        campaign_scope=_campaign_scope(assertion),
        temporal_scope=_temporal_scope(assertion),
        evidence_ref_ids=list(assertion.metadata.evidence_ref_ids),
        source_artifact_ids=_source_ids(assertion, evidence_by_id),
    )


def _map_relationship(
    assertion: ParsedAssertion,
    *,
    selected_entity_id: str,
    evidence_by_id: dict[str, Any],
    source_by_id: dict[str, _SourcePresentation],
) -> WorldGraphObjectProjectionRelationship:
    value = assertion.value
    if not isinstance(value, ParsedEntityRefValue):
        raise VNextCompleteObjectProjectionError("relationship value is not entity_ref")
    if assertion.subject_entity_id == selected_entity_id:
        direction = "outgoing"
    elif value.entity_id == selected_entity_id:
        direction = "incoming"
    else:
        raise VNextCompleteObjectProjectionError(
            "relationship does not touch selected entity"
        )
    predicate = _wire_term(assertion.predicate)
    session_ids = sorted(
        {
            source_by_id[evidence_by_id[evidence_id].source_artifact_id].session_id
            for evidence_id in assertion.metadata.evidence_ref_ids
            if source_by_id[evidence_by_id[evidence_id].source_artifact_id].session_id
        }
    )
    return WorldGraphObjectProjectionRelationship(
        edge_id=assertion.assertion_id,
        source_node_id=assertion.subject_entity_id,
        target_node_id=value.entity_id,
        predicate=predicate,
        label=predicate.replace("_", " "),
        direction=direction,
        session_ids=session_ids,
        visibility=_visibility(assertion),
        campaign_scope=_campaign_scope(assertion),
        epistemic_kind=_epistemic_kind(assertion),
        temporal_scope=_temporal_scope(assertion),
        evidence_ref_ids=list(assertion.metadata.evidence_ref_ids),
        source_artifact_ids=_source_ids(assertion, evidence_by_id),
    )


def _source_bindings(
    *,
    evidence_by_id: dict[str, Any],
    revisions_by_id: dict[str, Any],
    source_by_id: dict[str, _SourcePresentation],
) -> list[WorldGraphObjectProjectionSourceBinding]:
    rows: list[WorldGraphObjectProjectionSourceBinding] = []
    for evidence_id in sorted(evidence_by_id):
        evidence = evidence_by_id[evidence_id]
        revision = revisions_by_id.get(evidence.source_revision_id)
        digest = revision.content_sha256 if revision is not None else None
        if digest is None:
            status = "source_binding_unavailable"
        elif evidence.source_span_ref_id is None:
            status = "no_source_span"
        else:
            status = "span_unresolvable"
        source = source_by_id[evidence.source_artifact_id]
        rows.append(
            WorldGraphObjectProjectionSourceBinding(
                evidence_ref_id=evidence.evidence_ref_id,
                source_artifact_id=evidence.source_artifact_id,
                source_revision_id=evidence.source_revision_id,
                content_sha256=digest,
                source_span_ref_id=evidence.source_span_ref_id,
                source_domain=source.source_domain,
                session_id=source.session_id,
                provenance_status=status,
                excerpt=None,
            )
        )
    return rows


def project_complete_world_object_vnext(
    *,
    parsed_revision: ParsedKnowledgeRevision,
    source_reader: KnowledgeSourceReader,
    request: WorldGraphObjectProjectionRequest,
    read_identity: DungeonBuddyVNextReadIdentity,
) -> WorldGraphObjectProjectionResult:
    """Project one exact native-vNext complete entity into the existing Buddy DTO."""
    if read_identity.space_id != parsed_revision.space_id:
        raise VNextCompleteObjectProjectionError("read identity space mismatch")
    if read_identity.revision_id != parsed_revision.revision_id:
        raise VNextCompleteObjectProjectionError("read identity revision mismatch")
    if request.world_id != parsed_revision.space_id:
        raise VNextCompleteObjectProjectionError("request world mismatch")
    if request.revision_pin not in {None, parsed_revision.revision_id}:
        raise VNextCompleteObjectProjectionError("request revision pin mismatch")
    if request.admissibility not in {"gm", "player"}:
        raise VNextCompleteObjectProjectionError("unknown admissibility")

    focus_campaign = request.focus.campaign_id or request.campaign_id
    projection_input = DungeonBuddyVNextProjectionInput(
        world_id=request.world_id,
        scope_mode="world",
        role=request.admissibility,
        campaign_id=focus_campaign if request.focus.kind == "session" else None,
        session_id=request.focus.session_id
        if request.focus.kind == "session"
        else None,
        revision_id=parsed_revision.revision_id,
    )
    context = build_dungeonbuddy_read_context(
        parsed_revision=parsed_revision,
        projection_input=projection_input,
        source_reader=source_reader,
    )
    service = EntityReadService()
    complete = service.get_complete_entity(context, request.node_id)
    snapshot = WorldGraphProjectionSnapshot(
        world_id=read_identity.space_id,
        campaign_id=request.campaign_id,
        revision_id=read_identity.revision_id,
        head_revision_id=read_identity.head_revision_id,
        is_head=read_identity.is_head,
        focus=request.focus.to_projection_focus(),
        admissibility=request.admissibility,
        scope_mode="world",
    )
    completeness = SelectedObjectCompletenessView(
        status=complete.completeness.status,
        reason=complete.completeness.reason,
        truncated_fields=[],
    )
    if not complete.found or complete.entity is None:
        return WorldGraphObjectProjectionResult(
            found=False,
            completeness=completeness,
            snapshot=snapshot,
            requested_node_id=request.node_id,
            resolved_node_id=None,
            node=None,
        )

    related_results = {
        entity.entity_id: service.get_entity(context, entity.entity_id)
        for entity in complete.related_entities
    }
    all_evidence = {item.evidence_ref_id: item for item in complete.evidence}
    for result in related_results.values():
        all_evidence.update({item.evidence_ref_id: item for item in result.evidence})
    artifact_ids = sorted({item.source_artifact_id for item in all_evidence.values()})
    revision_ids = sorted(
        {
            item.source_revision_id
            for item in all_evidence.values()
            if item.source_revision_id is not None
        }
    )
    presentation = context.source_reader.get_provenance_snapshot(
        artifact_ids=artifact_ids,
        revision_ids=revision_ids,
    )
    source_by_id = {
        artifact_id: _source_presentation(presentation.get_artifact(artifact_id))
        for artifact_id in artifact_ids
        if presentation.get_artifact(artifact_id) is not None
    }
    if set(source_by_id) != set(artifact_ids):
        raise VNextCompleteObjectProjectionError("admitted source disappeared")
    revisions_by_id = {
        revision_id: presentation.get_revision(revision_id)
        for revision_id in revision_ids
    }

    selected_assertions = tuple(
        item
        for item in complete.assertions
        if item.subject_entity_id == request.node_id
    )
    label, kind, summary = _display_values(selected_assertions, request.node_id)
    relationships = [
        _map_relationship(
            item,
            selected_entity_id=request.node_id,
            evidence_by_id=all_evidence,
            source_by_id=source_by_id,
        )
        for item in complete.assertions
        if isinstance(item.value, ParsedEntityRefValue)
    ]
    assertions = [
        _map_assertion(item, evidence_by_id=all_evidence)
        for item in selected_assertions
        if not isinstance(item.value, ParsedEntityRefValue)
    ]
    node_evidence_ids = sorted(
        {
            evidence_id
            for assertion in selected_assertions
            if not isinstance(assertion.value, ParsedEntityRefValue)
            for evidence_id in assertion.metadata.evidence_ref_ids
        }
        | {
            evidence_id
            for alias in complete.aliases
            for evidence_id in alias.evidence_ref_ids
        }
    )
    node_badges = _evidence_badges(
        node_evidence_ids,
        evidence_by_id=all_evidence,
        source_by_id=source_by_id,
        request=request,
    )

    related_nodes: list[WorldGraphProjectionNodeView] = []
    adjacency: list[WorldGraphProjectionAdjacencyCandidate] = []
    relationship_presentation: dict[str, tuple[bool, list[str]]] = {}
    for relationship in relationships:
        related_id = (
            relationship.target_node_id
            if relationship.direction == "outgoing"
            else relationship.source_node_id
        )
        related_result = related_results[related_id]
        related_label, related_kind, related_summary = _display_values(
            related_result.assertions, related_id
        )
        relationship_badges = _evidence_badges(
            relationship.evidence_ref_ids,
            evidence_by_id=all_evidence,
            source_by_id=source_by_id,
            request=request,
        )
        anchored = any(item.is_focus_session_evidence for item in relationship_badges)
        source_domains = sorted({item.source_domain for item in relationship_badges})
        relationship_presentation[relationship.edge_id] = (anchored, source_domains)
        adjacency_row = WorldGraphProjectionAdjacencyCandidate(
            edge_id=relationship.edge_id,
            node_id=related_id,
            label=related_label,
            kind=related_kind,
            predicate=relationship.predicate,
            direction=relationship.direction,
            anchored_to_focus_session=anchored,
            source_domains=source_domains,
            evidence_ref_ids=list(relationship.evidence_ref_ids),
            edge_label=relationship.label,
            session_ids=list(relationship.session_ids),
            campaign_scope=relationship.campaign_scope,
            related_summary=related_summary,
        )
        adjacency.append(adjacency_row)

    for related_id, related_result in related_results.items():
        related_label, related_kind, related_summary = _display_values(
            related_result.assertions, related_id
        )
        touching = [
            item
            for item in relationships
            if related_id in {item.source_node_id, item.target_node_id}
        ]
        related_evidence_ids = sorted(
            {
                evidence_id
                for assertion in related_result.assertions
                if not isinstance(assertion.value, ParsedEntityRefValue)
                for evidence_id in assertion.metadata.evidence_ref_ids
            }
            | {
                evidence_id
                for relationship in touching
                for evidence_id in relationship.evidence_ref_ids
            }
        )
        badges = _evidence_badges(
            related_evidence_ids,
            evidence_by_id=all_evidence,
            source_by_id=source_by_id,
            request=request,
        )
        anchored = any(item.is_focus_session_evidence for item in badges)
        source_domains = sorted({item.source_domain for item in badges})
        related_nodes.append(
            WorldGraphProjectionNodeView(
                node_id=related_id,
                label=related_label,
                kind=related_kind,
                role=related_kind,
                aliases=[],
                source_domains=source_domains,
                summary=related_summary,
                anchored_to_focus_session=anchored,
                campaign_scope=None,
                evidence_badges=badges,
                adjacency=[
                    WorldGraphProjectionAdjacencyCandidate(
                        edge_id=relationship.edge_id,
                        node_id=request.node_id,
                        label=label,
                        kind=kind,
                        predicate=relationship.predicate,
                        direction=(
                            "incoming"
                            if relationship.direction == "outgoing"
                            else "outgoing"
                        ),
                        anchored_to_focus_session=relationship_presentation[
                            relationship.edge_id
                        ][0],
                        source_domains=relationship_presentation[relationship.edge_id][
                            1
                        ],
                        evidence_ref_ids=list(relationship.evidence_ref_ids),
                        edge_label=relationship.label,
                        session_ids=list(relationship.session_ids),
                        campaign_scope=relationship.campaign_scope,
                        related_summary=summary,
                    )
                    for relationship in touching
                ],
                suggested_expansions=[],
                evidence_ref_ids=related_evidence_ids,
                source_artifact_ids=sorted(
                    {
                        all_evidence[evidence_id].source_artifact_id
                        for evidence_id in related_evidence_ids
                    }
                ),
            )
        )

    source_bindings = _source_bindings(
        evidence_by_id=all_evidence,
        revisions_by_id=revisions_by_id,
        source_by_id=source_by_id,
    )
    node_source_ids = sorted(
        {
            all_evidence[evidence_id].source_artifact_id
            for evidence_id in node_evidence_ids
        }
    )
    node = WorldGraphProjectionNodeView(
        node_id=request.node_id,
        label=label,
        kind=kind,
        role=kind,
        aliases=[
            item.alias_text
            for item in sorted(complete.aliases, key=lambda item: item.alias_id)
        ],
        source_domains=sorted({item.source_domain for item in node_badges}),
        summary=summary,
        anchored_to_focus_session=(
            any(item.is_focus_session_evidence for item in node_badges)
            or any(item.anchored_to_focus_session for item in adjacency)
        ),
        campaign_scope=None,
        evidence_badges=node_badges,
        adjacency=sorted(adjacency, key=lambda item: item.edge_id),
        suggested_expansions=[],
        evidence_ref_ids=node_evidence_ids,
        source_artifact_ids=node_source_ids,
    )
    fingerprint = object_projection_semantic_fingerprint(
        revision_id=snapshot.revision_id,
        node_id=request.node_id,
        admissibility=snapshot.admissibility,
        assertions=assertions,
        relationships=relationships,
        related_node_ids=[item.node_id for item in related_nodes],
        source_bindings=source_bindings,
    )
    return WorldGraphObjectProjectionResult(
        found=True,
        completeness=completeness,
        snapshot=snapshot,
        requested_node_id=request.node_id,
        resolved_node_id=request.node_id,
        node=node,
        related_nodes=sorted(related_nodes, key=lambda item: item.node_id),
        relationships=sorted(relationships, key=lambda item: item.edge_id),
        assertions=sorted(assertions, key=lambda item: item.assertion_id),
        source_bindings=source_bindings,
        semantic_fingerprint=fingerprint,
        telemetry=WorldGraphObjectProjectionTelemetry(
            relationship_count=len(relationships),
            assertion_count=len(assertions),
            evidence_count=len(source_bindings),
            temporally_qualified_fact_count=sum(
                1
                for item in [*assertions, *relationships]
                if item.temporal_scope is not None
            ),
            distinct_source_binding_count=len(
                {
                    (item.source_artifact_id, item.content_sha256)
                    for item in source_bindings
                }
            ),
            completeness=completeness.status,
        ),
    )
