"""Map category candidate graphs into Kernel GraphContribution assertions.

Preview extracts use ``node_type`` / ``description`` / span evidence. Kernel
merge expects ``kind`` / ``role`` / ``aliases`` / ``source_domains`` plus
embedded evidence/source-artifact payloads (PR006 shape). This module is the
fail-closed bridge; it does not resolve identity or publish.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from graph_memory.kernel.contributions import build_assertion, create_graph_contribution
from graph_memory.kernel.contribution_models import GraphContribution, GraphContributionAssertion

_NODE_TYPE_TO_KIND: dict[str, str] = {
    "character": "npc",
    "pc": "pc",
    "npc": "npc",
    "item": "item",
    "object": "item",
    "location": "location",
    "place": "location",
    "party": "party",
    "collective": "party",
    "organization": "party",
    "faction": "faction",
    "event": "event",
    "beat": "event",
    "threat": "threat",
    "mystery": "mystery",
    "thread": "thread",
    "job": "job",
    "encounter": "encounter",
}


class CandidateGraphMappingError(ValueError):
    """Raised when a candidate graph cannot be mapped fail-closed."""


def kernel_kind_for_node_type(node_type: str | None) -> str:
    raw = (node_type or "").strip().lower()
    if not raw:
        return "npc"
    return _NODE_TYPE_TO_KIND.get(raw, raw)


def _require_nonempty(value: str | None, *, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise CandidateGraphMappingError(f"{field} is required")
    return text


def _evidence_ref_payloads(
    evidence_refs: Sequence[Mapping[str, Any]] | None,
    *,
    assertion_key: str,
    source_artifact_id: str,
    source_domain: str,
    session_id: str | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    refs = list(evidence_refs or [])
    if not refs:
        raise CandidateGraphMappingError(
            f"assertion {assertion_key!r} has no evidence_refs"
        )
    evidence_ids: list[str] = []
    embedded: list[dict[str, Any]] = []
    for index, ref in enumerate(refs):
        span = str(ref.get("source_span_ref_id") or "").strip()
        if not span:
            raise CandidateGraphMappingError(
                f"assertion {assertion_key!r} evidence[{index}] missing source_span_ref_id"
            )
        evidence_id = f"evidence:{source_artifact_id}:{span}"
        if evidence_id in evidence_ids:
            continue
        evidence_ids.append(evidence_id)
        payload: dict[str, Any] = {
            "evidence_ref_id": evidence_id,
            "source_artifact_id": source_artifact_id,
            "source_domain": source_domain,
            "source_span_ref_id": span,
        }
        if session_id:
            payload["session_id"] = session_id
        else:
            payload["locator"] = span
        embedded.append(payload)
    return evidence_ids, embedded


def _source_artifact_payload(
    *,
    source_artifact_id: str,
    source_revision_id: str,
    source_domain: str,
    campaign_id: str | None,
    session_id: str | None,
    source_uri: str | None,
) -> dict[str, Any]:
    digest = source_revision_id.removeprefix("sha256:")
    payload: dict[str, Any] = {
        "source_artifact_id": source_artifact_id,
        "source_domain": source_domain,
        "content_sha256": digest,
        "uri": source_uri
        or f"repo://extract/{source_artifact_id}",
    }
    if campaign_id:
        payload["campaign_id"] = campaign_id
    if session_id:
        payload["session_id"] = session_id
    return payload


def map_candidate_node_to_assertion(
    node: Mapping[str, Any],
    *,
    source_artifact_id: str,
    source_revision_id: str,
    campaign_scope: str | None,
    source_domain: str = "recap",
    session_id: str | None = None,
    campaign_id: str | None = None,
    source_uri: str | None = None,
    acceptance_state: str = "candidate",
    identity_resolution_outcome: str | None = "unresolved",
    kind_override: str | None = None,
    subject_node_id_override: str | None = None,
) -> GraphContributionAssertion:
    node_id = _require_nonempty(str(node.get("node_id") or ""), field="node.node_id")
    label = _require_nonempty(str(node.get("label") or node_id), field="node.label")
    kind = kind_override or kernel_kind_for_node_type(str(node.get("node_type") or ""))
    evidence_ids, embedded_evidence = _evidence_ref_payloads(
        node.get("evidence_refs"),
        assertion_key=node_id,
        source_artifact_id=source_artifact_id,
        source_domain=source_domain,
        session_id=session_id,
    )
    aliases = [label]
    summary = str(node.get("description") or "").strip() or None
    value: dict[str, Any] = {
        "kind": kind,
        "role": kind,
        "aliases": aliases,
        "source_domains": [source_domain],
        "evidence": embedded_evidence,
        "source_artifacts": [
            _source_artifact_payload(
                source_artifact_id=source_artifact_id,
                source_revision_id=source_revision_id,
                source_domain=source_domain,
                campaign_id=campaign_id,
                session_id=session_id,
                source_uri=source_uri,
            )
        ],
        "canon_state": "canonical",
        "approval_state": "accepted" if acceptance_state == "accepted" else "candidate",
    }
    if summary:
        value["summary"] = summary
    return build_assertion(
        assertion_kind="node",
        acceptance_state=acceptance_state,
        subject_node_id=subject_node_id_override or node_id,
        label=label,
        value=value,
        evidence_ref_ids=evidence_ids,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        epistemic_kind="source_derived_candidate",
        visibility="gm",
        identity_resolution_outcome=identity_resolution_outcome,
    )


def map_candidate_edge_to_assertion(
    edge: Mapping[str, Any],
    *,
    source_artifact_id: str,
    source_revision_id: str,
    campaign_scope: str | None,
    source_domain: str = "recap",
    session_id: str | None = None,
    campaign_id: str | None = None,
    source_uri: str | None = None,
    acceptance_state: str = "candidate",
    identity_resolution_outcome: str | None = "unresolved",
    subject_node_id_override: str | None = None,
    target_node_id_override: str | None = None,
    node_id_map: Mapping[str, str] | None = None,
) -> GraphContributionAssertion:
    edge_id = _require_nonempty(str(edge.get("edge_id") or ""), field="edge.edge_id")
    from_id = _require_nonempty(
        str(edge.get("from_node_id") or ""), field="edge.from_node_id"
    )
    to_id = _require_nonempty(str(edge.get("to_node_id") or ""), field="edge.to_node_id")
    id_map = dict(node_id_map or {})
    subject_id = subject_node_id_override or id_map.get(from_id, from_id)
    target_id = target_node_id_override or id_map.get(to_id, to_id)
    predicate = (
        str(edge.get("relationship_type") or edge.get("predicate") or "related_to").strip()
        or "related_to"
    )
    label = str(edge.get("label") or predicate).strip() or predicate
    evidence_ids, embedded_evidence = _evidence_ref_payloads(
        edge.get("evidence_refs"),
        assertion_key=edge_id,
        source_artifact_id=source_artifact_id,
        source_domain=source_domain,
        session_id=session_id,
    )
    value: dict[str, Any] = {
        "edge_id": f"edge:{subject_id}:{predicate}:{target_id}",
        "predicate": predicate,
        "predicate_family": edge.get("predicate_family"),
        "source_domains": [source_domain],
        "direction": "outbound",
        "evidence": embedded_evidence,
        "source_artifacts": [
            _source_artifact_payload(
                source_artifact_id=source_artifact_id,
                source_revision_id=source_revision_id,
                source_domain=source_domain,
                campaign_id=campaign_id,
                session_id=session_id,
                source_uri=source_uri,
            )
        ],
        "canon_state": "canonical",
        "approval_state": "accepted" if acceptance_state == "accepted" else "candidate",
    }
    if session_id:
        value["session_ids"] = [session_id]
    return build_assertion(
        assertion_kind="edge",
        acceptance_state=acceptance_state,
        subject_node_id=subject_id,
        target_node_id=target_id,
        predicate=predicate,
        label=label,
        value=value,
        evidence_ref_ids=evidence_ids,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        epistemic_kind="source_derived_candidate",
        visibility="gm",
        identity_resolution_outcome=identity_resolution_outcome,
        temporal_scope={"session_id": session_id} if session_id else None,
    )


def candidate_graph_to_contribution(
    candidate_graph: Mapping[str, Any],
    *,
    world_id: str,
    source_artifact_id: str | None = None,
    source_revision_id: str | None = None,
    campaign_scope: str | None = None,
    extraction_profile: str | None = "current_default",
    authored_by: str | None = "candidate-graph-mapper",
    source_domain: str = "recap",
    source_uri: str | None = None,
    node_ids: Sequence[str] | None = None,
    include_edges: bool = True,
) -> GraphContribution:
    """Map a candidate graph into a source_extraction contribution (candidates only)."""
    world = _require_nonempty(world_id, field="world_id")
    artifact_id = _require_nonempty(
        source_artifact_id
        or (
            (candidate_graph.get("source_artifact_ids") or [None])[0]
            if isinstance(candidate_graph.get("source_artifact_ids"), list)
            else None
        ),
        field="source_artifact_id",
    )
    revision_id = _require_nonempty(source_revision_id, field="source_revision_id")
    if not revision_id.startswith("sha256:"):
        revision_id = f"sha256:{revision_id}"

    session_id = str(candidate_graph.get("session_id") or "").strip() or None
    campaign_id = str(candidate_graph.get("campaign_id") or "").strip() or None
    scope = campaign_scope or campaign_id

    allow = set(node_ids) if node_ids is not None else None
    nodes = [
        node
        for node in list(candidate_graph.get("nodes") or [])
        if isinstance(node, dict)
        and (allow is None or str(node.get("node_id") or "") in allow)
    ]
    if not nodes:
        raise CandidateGraphMappingError("candidate graph has no nodes to map")

    node_assertions: list[GraphContributionAssertion] = [
        map_candidate_node_to_assertion(
            node,
            source_artifact_id=artifact_id,
            source_revision_id=revision_id,
            campaign_scope=scope,
            source_domain=source_domain,
            session_id=session_id,
            campaign_id=campaign_id,
            source_uri=source_uri,
        )
        for node in nodes
    ]

    edge_assertions: list[GraphContributionAssertion] = []
    if include_edges:
        mapped_node_ids = {str(node.get("node_id") or "") for node in nodes}
        for edge in list(candidate_graph.get("edges") or []):
            if not isinstance(edge, dict):
                continue
            from_id = str(edge.get("from_node_id") or "")
            to_id = str(edge.get("to_node_id") or "")
            if from_id not in mapped_node_ids or to_id not in mapped_node_ids:
                continue
            edge_assertions.append(
                map_candidate_edge_to_assertion(
                    edge,
                    source_artifact_id=artifact_id,
                    source_revision_id=revision_id,
                    campaign_scope=scope,
                    source_domain=source_domain,
                    session_id=session_id,
                    campaign_id=campaign_id,
                    source_uri=source_uri,
                )
            )

    return create_graph_contribution(
        world_id=world,
        source_kind="source_extraction",
        source_artifact_id=artifact_id,
        source_revision_id=revision_id,
        extraction_profile=extraction_profile,
        campaign_scope=scope,
        authored_by=authored_by,
        candidate_assertions=[*node_assertions, *edge_assertions],
        diagnostics=[
            f"mapped_nodes:{len(node_assertions)}",
            f"mapped_edges:{len(edge_assertions)}",
        ],
    )
