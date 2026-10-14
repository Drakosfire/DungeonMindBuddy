"""Deterministic claim authority classification from retrieval / preflight packets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from graph_memory.interaction.claims import (
    ClaimAuthorityClass,
    ClaimSupport,
    ClaimSupportState,
    GraphClaim,
)


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _get(obj: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in obj:
            return obj[key]
    return None


def classify_authority_for_attribute(attribute: Mapping[str, Any]) -> ClaimAuthorityClass:
    """Classify an attribute/assertion row without inventing authorship.

    Explicit projection authority wins. Legacy provenance signals can classify
    known graph-review and source-derived rows, but absent provenance is
    ``unknown`` rather than accepted GM canon.
    """
    source_kind = str(
        _get(attribute, "source_kind", "sourceKind", "epistemic_kind", "epistemicKind")
        or ""
    ).lower()
    support_state = str(
        _get(attribute, "support_state", "supportState") or ""
    ).lower()
    explicit_authority = str(
        _get(attribute, "authority_class", "authorityClass") or ""
    ).strip().lower()
    known_authorities = {
        "governed_identity_decision",
        "gm_authored_accepted_assertion",
        "source_derived_accepted_assertion",
        "accepted_relationship",
        "accepted_explicit_attribute",
        "derived_summary",
        "inferred_relationship",
        "provisional_or_disputed",
        "generated_prep_suggestion",
        "unknown",
    }
    if support_state in {"provisional", "disputed"}:
        return "provisional_or_disputed"
    if explicit_authority in known_authorities:
        return cast(ClaimAuthorityClass, explicit_authority)
    if "graph_review" in source_kind or "gm_authored" in source_kind:
        return "gm_authored_accepted_assertion"
    # Accepted attributes with evidence refs are treated as source-linked graph claims.
    evidence_ids = _get(attribute, "evidence_ref_ids", "evidenceRefIds") or []
    if evidence_ids:
        return "source_derived_accepted_assertion"
    return "unknown"


def support_from_anchors(
    anchors: Sequence[Mapping[str, Any]] | None,
    *,
    supporting_ids: Sequence[str] | None = None,
) -> ClaimSupport:
    if not anchors:
        return ClaimSupport(state="graph_accepted")
    readable: list[str] = []
    unreadable: list[str] = []
    available: list[str] = []
    opened: list[str] = []
    id_filter = set(supporting_ids or [])
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            continue
        anchor_id = _get(anchor, "anchor_id", "anchorId", "id")
        if not isinstance(anchor_id, str) or not anchor_id:
            continue
        support_objs = (
            _get(
                anchor,
                "supporting_assertion_ids",
                "supportingAssertionIds",
                "supporting_graph_object_ids",
                "supportingGraphObjectIds",
            )
            or []
        )
        if id_filter and not (
            anchor_id in id_filter
            or any(str(item) in id_filter for item in support_objs)
        ):
            continue
        available.append(anchor_id)
        if bool(_get(anchor, "opened") or False):
            opened.append(anchor_id)
        elif bool(_get(anchor, "readable") is True):
            readable.append(anchor_id)
        else:
            # Missing readable defaults to unreadable for honesty.
            if _get(anchor, "readable") is False or _get(anchor, "readable") is None:
                unreadable.append(anchor_id)
            else:
                readable.append(anchor_id)
    state: ClaimSupportState
    if opened:
        state = "source_opened"
    elif unreadable and not readable:
        state = "source_anchor_unreadable"
    elif available:
        state = "source_anchor_available"
    else:
        state = "graph_accepted"
    return ClaimSupport(
        state=state,
        source_anchor_ids=list(dict.fromkeys(available)),
        source_read_ids=list(dict.fromkeys(opened)),
        readable_anchor_ids=list(dict.fromkeys(readable)),
        unreadable_anchor_ids=list(dict.fromkeys(unreadable)),
    )


def _relationship_evidence_ids(value: Any) -> list[str]:
    """Accept only complete, nonblank evidence-ref lists from a retrieval row."""
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() or item != item.strip()
        for item in value
    ):
        return []
    return list(dict.fromkeys(value))


def _relationship_support_from_evidence(
    anchors: Sequence[Mapping[str, Any]],
    *,
    evidence_ref_ids: Sequence[str],
    revision_id: str,
) -> ClaimSupport:
    """Bind only same-result, same-revision anchors with exact evidence refs.

    Retrieval anchors are provenance metadata, not source-open receipts.
    """
    accepted_ids = set(evidence_ref_ids)
    if not accepted_ids:
        return ClaimSupport(state="graph_accepted")
    matching = [
        {**anchor, "opened": False}
        for anchor in anchors
        if isinstance(_get(anchor, "evidence_ref_id", "evidenceRefId"), str)
        and _get(anchor, "evidence_ref_id", "evidenceRefId") in accepted_ids
        and _get(anchor, "revision_id", "revisionId") == revision_id
    ]
    return support_from_anchors(matching)


def claims_from_retrieval_result(
    result: Mapping[str, Any],
    *,
    revision_id: str,
    include_attribute_evidence_refs: bool = False,
) -> list[GraphClaim]:
    """Project a PR010A retrieval result into graph claims (no derived summaries)."""
    claims: list[GraphClaim] = []
    anchors_raw = result.get("sourceAnchors") or result.get("source_anchors") or []
    anchors = [a for a in anchors_raw if isinstance(a, Mapping)]

    for node in result.get("nodes") or []:
        node_map = _as_mapping(node)
        if node_map is None:
            continue
        node_id = str(_get(node_map, "node_id", "nodeId") or "")
        if not node_id:
            continue
        label = _get(node_map, "label")
        claims.append(
            GraphClaim(
                claim_id=f"identity:{node_id}",
                claim_kind="identity",
                subject_node_id=node_id,
                subject_label=None if label is None else str(label),
                predicate="identity",
                value_text=None if label is None else str(label),
                revision_id=revision_id,
                authority_class="governed_identity_decision",
                support=support_from_anchors(anchors, supporting_ids=[node_id]),
            )
        )

    for rel in result.get("relationships") or []:
        rel_map = _as_mapping(rel)
        if rel_map is None:
            continue
        edge_id = str(_get(rel_map, "edge_id", "edgeId") or "")
        if not edge_id:
            continue
        predicate = _get(rel_map, "predicate")
        evidence_ids = _relationship_evidence_ids(
            _get(rel_map, "evidence_ref_ids", "evidenceRefIds")
        )
        claims.append(
            GraphClaim(
                claim_id=edge_id,
                claim_kind="relationship",
                subject_node_id=(
                    None
                    if _get(rel_map, "source_node_id", "sourceNodeId") is None
                    else str(_get(rel_map, "source_node_id", "sourceNodeId"))
                ),
                object_node_id=(
                    None
                    if _get(rel_map, "target_node_id", "targetNodeId") is None
                    else str(_get(rel_map, "target_node_id", "targetNodeId"))
                ),
                predicate=None if predicate is None else str(predicate),
                value_text=None if _get(rel_map, "label") is None else str(_get(rel_map, "label")),
                epistemic_kind=(
                    None
                    if _get(rel_map, "epistemic_kind", "epistemicKind") is None
                    else str(_get(rel_map, "epistemic_kind", "epistemicKind"))
                ),
                visibility=(
                    None
                    if _get(rel_map, "visibility") is None
                    else str(_get(rel_map, "visibility"))
                ),
                campaign_scope=(
                    None
                    if _get(rel_map, "campaign_scope", "campaignScope") is None
                    else str(_get(rel_map, "campaign_scope", "campaignScope"))
                ),
                revision_id=revision_id,
                authority_class="accepted_relationship",
                evidence_ref_ids=evidence_ids,
                support=_relationship_support_from_evidence(
                    anchors, evidence_ref_ids=evidence_ids, revision_id=revision_id
                ),
            )
        )

    for attribute in result.get("attributes") or []:
        attr_map = _as_mapping(attribute)
        if attr_map is None:
            continue
        assertion_id = str(_get(attr_map, "assertion_id", "assertionId") or "")
        if not assertion_id:
            continue
        authority = classify_authority_for_attribute(attr_map)
        text_value = _get(attr_map, "text_value", "textValue")
        attribute_anchors = anchors
        evidence_ids: list[str] = []
        if include_attribute_evidence_refs:
            declared_evidence = set(_relationship_evidence_ids(
                _get(attr_map, "evidence_ref_ids", "evidenceRefIds")
            ))
            attribute_anchors = []
            for anchor in anchors:
                supporting = _get(
                    anchor, "supporting_assertion_ids", "supportingAssertionIds",
                    "supporting_graph_object_ids", "supportingGraphObjectIds",
                )
                anchor_id = _get(anchor, "anchor_id", "anchorId")
                evidence_id = _get(anchor, "evidence_ref_id", "evidenceRefId")
                if (
                    not isinstance(supporting, list) or assertion_id not in supporting
                    or not isinstance(anchor_id, str) or not anchor_id
                    or not isinstance(evidence_id, str) or evidence_id not in declared_evidence
                    or _get(anchor, "revision_id", "revisionId") != revision_id
                ):
                    continue
                attribute_anchors.append({**anchor, "opened": False})
            evidence_ids = sorted({
                _get(anchor, "evidence_ref_id", "evidenceRefId")
                for anchor in attribute_anchors
            })
        claims.append(
            GraphClaim(
                claim_id=assertion_id,
                claim_kind="attribute",
                subject_node_id=(
                    None
                    if _get(attr_map, "subject_node_id", "subjectNodeId") is None
                    else str(_get(attr_map, "subject_node_id", "subjectNodeId"))
                ),
                predicate=(
                    None
                    if _get(attr_map, "predicate") is None
                    else str(_get(attr_map, "predicate"))
                ),
                value_text=None if text_value is None else str(text_value),
                epistemic_kind=(
                    None
                    if _get(attr_map, "epistemic_kind", "epistemicKind") is None
                    else str(_get(attr_map, "epistemic_kind", "epistemicKind"))
                ),
                visibility=(
                    None
                    if _get(attr_map, "visibility") is None
                    else str(_get(attr_map, "visibility"))
                ),
                campaign_scope=(
                    None
                    if _get(attr_map, "campaign_scope", "campaignScope") is None
                    else str(_get(attr_map, "campaign_scope", "campaignScope"))
                ),
                acceptance_state="accepted",
                revision_id=revision_id,
                authority_class=authority,
                evidence_ref_ids=evidence_ids,
                support=support_from_anchors(attribute_anchors, supporting_ids=[assertion_id]),
            )
        )
    for observation in (
        result.get("reviewedSourceObservations")
        or result.get("reviewed_source_observations")
        or []
    ):
        row = _as_mapping(observation)
        if row is None:
            continue
        observation_kind = str(_get(row, "observation_kind", "observationKind") or "")
        if observation_kind not in {"session_observation", "worldbuilding_observation"}:
            continue
        assertion_id = str(_get(row, "assertion_id", "assertionId") or "").strip()
        evidence_ids = _get(row, "evidence_ref_ids", "evidenceRefIds") or []
        if (
            not assertion_id or not isinstance(evidence_ids, list) or not evidence_ids
            or any(not isinstance(item, str) or not item.strip() for item in evidence_ids)
        ):
            continue
        anchored_evidence = {
            _get(anchor, "evidence_ref_id", "evidenceRefId")
            for anchor in anchors
            if assertion_id in (
                _get(anchor, "supporting_assertion_ids", "supportingAssertionIds") or []
            )
        }
        if not set(evidence_ids).issubset(anchored_evidence):
            continue
        claims.append(
            GraphClaim(
                claim_id=assertion_id,
                claim_kind="source_observation",
                subject_node_id=str(
                    _get(row, "subject_node_id", "subjectNodeId") or ""
                ),
                predicate=observation_kind,
                value_text=str(_get(row, "text") or ""),
                epistemic_kind=str(_get(row, "epistemic_kind", "epistemicKind") or ""),
                visibility=str(_get(row, "visibility") or ""),
                campaign_scope=_get(row, "campaign_scope", "campaignScope"),
                acceptance_state="accepted",
                revision_id=revision_id,
                authority_class="source_derived_accepted_assertion",
                source_assertion_id=assertion_id,
                observation_kind=observation_kind,
                temporal_scope=_get(row, "temporal_scope", "temporalScope"),
                review_id=_get(row, "review_id", "reviewId"),
                contribution_id=_get(row, "contribution_id", "contributionId"),
                publication_revision_id=_get(
                    row, "publication_revision_id", "publicationRevisionId"
                ),
                source_artifact_id=_get(row, "source_artifact_id", "sourceArtifactId"),
                source_revision_id=_get(row, "source_revision_id", "sourceRevisionId"),
                evidence_ref_ids=[str(item) for item in evidence_ids],
                support=support_from_anchors(anchors, supporting_ids=[assertion_id]),
            )
        )
    return claims


def claims_from_preflight_envelope(envelope: Mapping[str, Any]) -> list[GraphClaim]:
    """Project the PR008B agent preflight envelope into claim ledger entries."""
    revision_id = str(envelope.get("revision_id") or "").strip()
    if not revision_id:
        return []
    nodes = list(envelope.get("nodes") or [])
    # Matched durable IDs are authoritative even when the projection omitted node rows.
    matched_ids = [
        str(item)
        for item in (envelope.get("matched_node_ids") or envelope.get("matchedNodeIds") or [])
        if str(item).strip()
    ]
    nodes_by_id = {
        str(_get(node, "node_id", "nodeId")): node
        for node in nodes
        if isinstance(node, Mapping) and _get(node, "node_id", "nodeId")
    }
    for node_id in matched_ids:
        if node_id in nodes_by_id:
            continue
        nodes.append({"node_id": node_id, "nodeId": node_id, "label": node_id})
    # Preflight lacks sourceAnchors; support starts as graph_accepted.
    synthetic_result = {
        "nodes": nodes,
        "relationships": envelope.get("relationships") or [],
        "attributes": envelope.get("attributes") or [],
        "sourceAnchors": [],
    }
    return claims_from_retrieval_result(synthetic_result, revision_id=revision_id)


def factual_claim_ids(claims: Sequence[GraphClaim]) -> list[str]:
    return [claim.claim_id for claim in claims if claim.may_state_as_campaign_fact()]


__all__ = [
    "claims_from_preflight_envelope",
    "claims_from_retrieval_result",
    "classify_authority_for_attribute",
    "factual_claim_ids",
    "support_from_anchors",
]
