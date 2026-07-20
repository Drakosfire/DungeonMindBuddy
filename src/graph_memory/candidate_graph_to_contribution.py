"""Map typed CandidateGraphPreview objects into Kernel GraphContribution assertions.

Fail-closed: requires validated preview IR, promote-eligible semantics, evidence
per assertion, and verified source revision digests. Does not resolve identity
or publish.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CandidateEdge,
    CandidateGraphPreview,
    CandidateNode,
    EvidenceRef,
    candidate_graph_preview_from_dict,
    validate_candidate_graph_preview,
)
from graph_memory.candidate_semantic_promote_matrix import (
    CandidateSemanticPromoteError,
    map_candidate_semantics_to_kernel,
    semantic_diagnostics,
)
from graph_memory.kernel.contributions import build_assertion, create_graph_contribution
from graph_memory.kernel.contribution_models import GraphContribution, GraphContributionAssertion
from graph_memory.source_artifact_domains import CAMPAIGN_STABLE_SOURCE_DOMAINS

# Re-export for back-compat with callers that imported from this module.

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
    "combat_encounter": "encounter",
    "quest": "job",
    "clue": "mystery",
    "landmark": "location",
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


def load_typed_candidate_graph(payload: Mapping[str, Any]) -> CandidateGraphPreview:
    """Parse and structurally validate a CandidateGraphPreview IR document."""
    if payload.get("schema") == "dmb_portable_object_demo_candidate_v1":
        raise CandidateGraphMappingError(
            "phase4 portable demo JSON is not a candidate_graph; pass a "
            "dmb_candidate_graph_preview_v0 document"
        )
    if payload.get("schema") != CANDIDATE_GRAPH_PREVIEW_SCHEMA:
        raise CandidateGraphMappingError(
            f"unsupported schema {payload.get('schema')!r}; require "
            f"{CANDIDATE_GRAPH_PREVIEW_SCHEMA}"
        )
    # Detect common category-extractor drift before pydantic-ish dataclass parse.
    nodes = list(payload.get("nodes") or [])
    if nodes and isinstance(nodes[0], dict):
        semantic = nodes[0].get("semantic_state") or {}
        if isinstance(semantic, dict) and "canon_status" in semantic:
            raise CandidateGraphMappingError(
                "candidate graph uses extractor semantic_state aliases "
                "(canon_status/lifecycle/memory_status); promote requires typed "
                "CandidateGraphPreview SemanticState "
                "(canon_state/lifecycle_state/evidence_role/authority_state/"
                "visibility_state). Align the extractor or use a gold IR fixture."
            )
    try:
        preview = candidate_graph_preview_from_dict(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise CandidateGraphMappingError(
            f"candidate graph failed typed parse: {exc}"
        ) from exc
    report = validate_candidate_graph_preview(preview)
    errors = [i for i in report.issues if i.severity == "error"]
    if errors:
        sample = "; ".join(
            f"{i.code}:{i.object_id or ''}:{i.message}" for i in errors[:8]
        )
        raise CandidateGraphMappingError(
            f"candidate graph failed validation ({len(errors)} issues): {sample}"
        )
    return preview


def resolve_source_bytes(source_uri: str, *, repo_root: Path | None = None) -> bytes:
    """Resolve a file path or repo:// URI to source artifact bytes."""
    uri = _require_nonempty(source_uri, field="source_uri")
    if uri.startswith("repo://"):
        rel = uri[len("repo://") :].lstrip("/")
        root = (repo_root or Path.cwd()).resolve()
        path = (root / rel).resolve()
        if not str(path).startswith(str(root)):
            raise CandidateGraphMappingError(
                f"source_uri escapes repo root: {source_uri}"
            )
    else:
        path = Path(uri).expanduser().resolve()
    if not path.is_file():
        raise CandidateGraphMappingError(f"source_uri is not a readable file: {uri}")
    return path.read_bytes()


def verify_source_revision(
    *,
    source_uri: str,
    source_revision_id: str,
    repo_root: Path | None = None,
    disclose_computed_digest: bool = True,
) -> str:
    """Hash source bytes and require source_revision_id == sha256:{digest}.

    When ``disclose_computed_digest`` is False (HTTP boundaries), mismatch
    errors omit the computed digest so callers cannot oracle arbitrary files.
    """
    raw = resolve_source_bytes(source_uri, repo_root=repo_root)
    digest = hashlib.sha256(raw).hexdigest()
    expected = f"sha256:{digest}"
    provided = _require_nonempty(source_revision_id, field="source_revision_id")
    if not provided.startswith("sha256:"):
        provided = f"sha256:{provided}"
    if provided != expected:
        if disclose_computed_digest:
            raise CandidateGraphMappingError(
                f"source_revision_id mismatch: provided={provided} computed={expected}"
            )
        raise CandidateGraphMappingError(
            "source_revision_id does not match the resolved source artifact"
        )
    return expected


def _collect_evidence_artifact_ids(
    nodes: Sequence[CandidateNode],
    edges: Sequence[CandidateEdge],
) -> set[str]:
    ids: set[str] = set()
    for node in nodes:
        for ref in node.evidence_refs:
            aid = (ref.source_artifact_id or "").strip()
            if aid:
                ids.add(aid)
    for edge in edges:
        for ref in edge.evidence_refs:
            aid = (ref.source_artifact_id or "").strip()
            if aid:
                ids.add(aid)
    return ids


def require_single_verified_source_artifact(
    *,
    preview: CandidateGraphPreview,
    verified_artifact_id: str,
    nodes: Sequence[CandidateNode],
    edges: Sequence[CandidateEdge],
) -> None:
    """Until per-artifact URI/revision verification exists, promote only one source.

    Multi-artifact evidence would otherwise inherit the single verified file's
    hash/URI — recording artifact B as having artifact A's bytes.

    Callers must pass the exact selected node-and-edge set being promoted
    (including edges mapped outside ``candidate_graph_to_contribution``).
    """
    verified = _require_nonempty(verified_artifact_id, field="source_artifact_id")
    top_level = {
        str(a).strip() for a in (preview.source_artifact_ids or []) if str(a).strip()
    }
    evidence_ids = _collect_evidence_artifact_ids(nodes, edges)
    combined = top_level | evidence_ids
    if len(combined) > 1:
        raise CandidateGraphMappingError(
            "promotion rejects multi-artifact candidate graphs until per-artifact "
            f"{{artifact_id, URI, revision}} verification exists; found {sorted(combined)}"
        )
    if combined and verified not in combined:
        raise CandidateGraphMappingError(
            f"verified source_artifact_id {verified!r} does not match evidence "
            f"artifacts {sorted(combined)}"
        )
    if evidence_ids and evidence_ids != {verified}:
        raise CandidateGraphMappingError(
            f"evidence source_artifact_ids {sorted(evidence_ids)} must equal "
            f"verified {verified!r}"
        )


def _evidence_ref_payloads(
    evidence_refs: Sequence[EvidenceRef],
    *,
    assertion_key: str,
    default_source_domain: str,
    session_id: str | None,
    verified_source_revision_id: str,
    verified_source_artifact_id: str,
    source_uri: str | None,
    campaign_id: str | None,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    if not evidence_refs:
        raise CandidateGraphMappingError(
            f"assertion {assertion_key!r} has no evidence_refs"
        )
    verified_artifact = _require_nonempty(
        verified_source_artifact_id, field="verified_source_artifact_id"
    )
    evidence_ids: list[str] = []
    embedded: list[dict[str, Any]] = []
    source_artifacts: list[dict[str, Any]] = []
    seen_artifacts: set[str] = set()
    for index, ref in enumerate(evidence_refs):
        span = str(ref.source_span_ref_id or "").strip()
        if not span:
            raise CandidateGraphMappingError(
                f"assertion {assertion_key!r} evidence[{index}] missing source_span_ref_id"
            )
        artifact_id = _require_nonempty(
            ref.source_artifact_id, field=f"{assertion_key}.evidence[{index}].source_artifact_id"
        )
        if artifact_id != verified_artifact:
            raise CandidateGraphMappingError(
                f"assertion {assertion_key!r} evidence[{index}] source_artifact_id "
                f"{artifact_id!r} != verified {verified_artifact!r}"
            )
        evidence_id = f"evidence:{artifact_id}:{span}"
        if evidence_id not in evidence_ids:
            evidence_ids.append(evidence_id)
            payload: dict[str, Any] = {
                "evidence_ref_id": evidence_id,
                "source_artifact_id": artifact_id,
                "source_domain": default_source_domain,
                "source_span_ref_id": span,
            }
            if session_id:
                payload["session_id"] = session_id
            else:
                payload["locator"] = span
            if ref.source_ref_id:
                payload["source_ref_id"] = ref.source_ref_id
            embedded.append(payload)
        if artifact_id not in seen_artifacts:
            seen_artifacts.add(artifact_id)
            source_artifacts.append(
                _source_artifact_payload(
                    source_artifact_id=artifact_id,
                    source_revision_id=verified_source_revision_id,
                    source_domain=default_source_domain,
                    campaign_id=campaign_id,
                    session_id=session_id,
                    source_uri=source_uri,
                )
            )
    return evidence_ids, embedded, source_artifacts


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
        "uri": source_uri or f"repo://extract/{source_artifact_id}",
    }
    if campaign_id:
        payload["campaign_id"] = campaign_id
    # Campaign-stable registries must not stamp the promoting session onto the
    # artifact identity — session-N vs session-N+1 would fail merge equality
    # even when content_sha256 is unchanged.
    if session_id and source_domain not in CAMPAIGN_STABLE_SOURCE_DOMAINS:
        payload["session_id"] = session_id
    return payload


def map_candidate_node_to_assertion(
    node: CandidateNode,
    *,
    source_revision_id: str,
    verified_source_artifact_id: str,
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
    try:
        mapping = map_candidate_semantics_to_kernel(
            object_id=node.node_id,
            semantic=node.semantic_state,
            proposed_action=node.proposed_action,
            confidence=node.confidence,
            warnings=node.warnings,
            acceptance_state=acceptance_state,
        )
    except CandidateSemanticPromoteError as exc:
        raise CandidateGraphMappingError(str(exc)) from exc

    node_id = _require_nonempty(node.node_id, field="node.node_id")
    label = _require_nonempty(node.label or node_id, field="node.label")
    kind = kind_override or kernel_kind_for_node_type(node.node_type)
    evidence_ids, embedded_evidence, source_artifacts = _evidence_ref_payloads(
        node.evidence_refs,
        assertion_key=node_id,
        default_source_domain=source_domain,
        session_id=session_id,
        verified_source_revision_id=source_revision_id,
        verified_source_artifact_id=verified_source_artifact_id,
        source_uri=source_uri,
        campaign_id=campaign_id,
    )
    # Top-level source_artifact_id is the first evidence artifact (not a rewrite of all).
    primary_artifact = source_artifacts[0]["source_artifact_id"]
    summary = (node.description or "").strip() or None
    aliases = [str(a).strip() for a in node.aliases if str(a).strip()]
    value: dict[str, Any] = {
        "kind": kind,
        "role": kind,
        "aliases": aliases if aliases else [label],
        "source_domains": [source_domain],
        "evidence": embedded_evidence,
        "source_artifacts": source_artifacts,
        "canon_state": mapping.canon_state,
        "approval_state": mapping.approval_state,
    }
    if summary:
        value["summary"] = summary
    assertion = build_assertion(
        assertion_kind="node",
        acceptance_state=acceptance_state,
        subject_node_id=subject_node_id_override or node_id,
        label=label,
        value=value,
        evidence_ref_ids=evidence_ids,
        source_artifact_id=primary_artifact,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        epistemic_kind=mapping.epistemic_kind,
        visibility=mapping.visibility,
        identity_resolution_outcome=identity_resolution_outcome,
    )
    return assertion


def map_connect_existing_support_assertions(
    node: CandidateNode,
    *,
    durable_node_id: str,
    source_revision_id: str,
    verified_source_artifact_id: str,
    campaign_scope: str | None,
    source_domain: str = "recap",
    session_id: str | None = None,
    campaign_id: str | None = None,
    source_uri: str | None = None,
    acceptance_state: str = "accepted",
    identity_resolution_outcome: str | None = "resolved_existing",
    predicate: str = "session_observation",
    alias_owners: Mapping[str, str] | None = None,
) -> tuple[list[GraphContributionAssertion], tuple[str, ...]]:
    """Support-only assertions for identity resolutions that connect to an
    already-durable node (``resolved_existing`` / ``human_override``).

    Connect-existing must never emit a competing ``node`` assertion: the
    durable node's role/summary/epistemic payload is authoritative, and a
    second active node assertion with extract-derived semantics leaves two
    disagreeing supports that projection refuses (see
    ``_refuse_disagreeing_active_node_assertion``). Instead this emits
    non-destructive support — an ``attribute`` observation recording this
    session's mention plus ``alias`` assertions for extract-only spellings —
    so the promote is additive rather than silently dropped.
    """
    node_id = _require_nonempty(node.node_id, field="node.node_id")
    durable_id = _require_nonempty(durable_node_id, field="durable_node_id")
    label = _require_nonempty(node.label or node_id, field="node.label")
    evidence_ids, embedded_evidence, source_artifacts = _evidence_ref_payloads(
        node.evidence_refs,
        assertion_key=node_id,
        default_source_domain=source_domain,
        session_id=session_id,
        verified_source_revision_id=source_revision_id,
        verified_source_artifact_id=verified_source_artifact_id,
        source_uri=source_uri,
        campaign_id=campaign_id,
    )
    primary_artifact = source_artifacts[0]["source_artifact_id"]
    summary = (node.description or "").strip() or None

    observation_value: dict[str, Any] = {
        "kind": kernel_kind_for_node_type(node.node_type),
        "extract_node_id": node_id,
        "source_domains": [source_domain],
        "evidence": embedded_evidence,
        "source_artifacts": source_artifacts,
    }
    if summary:
        observation_value["summary"] = summary

    assertions: list[GraphContributionAssertion] = [
        build_assertion(
            assertion_kind="attribute",
            acceptance_state=acceptance_state,
            subject_node_id=durable_id,
            predicate=predicate,
            label=label,
            value=observation_value,
            evidence_ref_ids=evidence_ids,
            source_artifact_id=primary_artifact,
            source_revision_id=source_revision_id,
            campaign_scope=campaign_scope,
            identity_resolution_outcome=identity_resolution_outcome,
        )
    ]

    owners = dict(alias_owners or {})
    skip_diagnostics: list[str] = []
    seen_aliases = {label.casefold()}
    for raw_alias in node.aliases:
        alias = str(raw_alias).strip()
        if not alias or alias.casefold() in seen_aliases:
            continue
        owner = owners.get(alias.casefold())
        if owner is not None and owner != durable_id:
            skip_diagnostics.append(f"alias_ownership_skip:{alias}->{owner}")
            continue
        seen_aliases.add(alias.casefold())
        assertions.append(
            build_assertion(
                assertion_kind="alias",
                acceptance_state=acceptance_state,
                subject_node_id=durable_id,
                label=alias,
                value={
                    "alias": alias,
                    "evidence": embedded_evidence,
                    "source_artifacts": source_artifacts,
                },
                evidence_ref_ids=evidence_ids,
                source_artifact_id=primary_artifact,
                source_revision_id=source_revision_id,
                campaign_scope=campaign_scope,
                identity_resolution_outcome=identity_resolution_outcome,
            )
        )
    return assertions, tuple(skip_diagnostics)


def map_candidate_edge_to_assertion(
    edge: CandidateEdge,
    *,
    source_revision_id: str,
    verified_source_artifact_id: str,
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
    try:
        mapping = map_candidate_semantics_to_kernel(
            object_id=edge.edge_id,
            semantic=edge.semantic_state,
            proposed_action=edge.proposed_action,
            confidence=edge.confidence,
            warnings=edge.warnings,
            acceptance_state=acceptance_state,
        )
    except CandidateSemanticPromoteError as exc:
        raise CandidateGraphMappingError(str(exc)) from exc

    edge_id = _require_nonempty(edge.edge_id, field="edge.edge_id")
    from_id = _require_nonempty(edge.from_node_id, field="edge.from_node_id")
    to_id = _require_nonempty(edge.to_node_id, field="edge.to_node_id")
    id_map = dict(node_id_map or {})
    subject_id = subject_node_id_override or id_map.get(from_id, from_id)
    target_id = target_node_id_override or id_map.get(to_id, to_id)
    predicate = (edge.relationship_type or "related_to").strip() or "related_to"
    label = (edge.label or predicate).strip() or predicate
    evidence_ids, embedded_evidence, source_artifacts = _evidence_ref_payloads(
        edge.evidence_refs,
        assertion_key=edge_id,
        default_source_domain=source_domain,
        session_id=session_id,
        verified_source_revision_id=source_revision_id,
        verified_source_artifact_id=verified_source_artifact_id,
        source_uri=source_uri,
        campaign_id=campaign_id,
    )
    primary_artifact = source_artifacts[0]["source_artifact_id"]
    value: dict[str, Any] = {
        "edge_id": f"edge:{subject_id}:{predicate}:{target_id}",
        "predicate": predicate,
        "source_domains": [source_domain],
        "direction": "outbound",
        "evidence": embedded_evidence,
        "source_artifacts": source_artifacts,
        "canon_state": mapping.canon_state,
        "approval_state": mapping.approval_state,
    }
    if session_id and source_domain not in CAMPAIGN_STABLE_SOURCE_DOMAINS:
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
        source_artifact_id=primary_artifact,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        epistemic_kind=mapping.epistemic_kind,
        visibility=mapping.visibility,
        identity_resolution_outcome=identity_resolution_outcome,
        temporal_scope=(
            {"session_id": session_id}
            if session_id and source_domain not in CAMPAIGN_STABLE_SOURCE_DOMAINS
            else None
        ),
    )


def candidate_graph_to_contribution(
    preview: CandidateGraphPreview,
    *,
    world_id: str,
    source_revision_id: str,
    source_artifact_id: str | None = None,
    campaign_scope: str | None = None,
    extraction_profile: str | None = "current_default",
    authored_by: str | None = "candidate-graph-mapper",
    source_domain: str = "recap",
    source_uri: str | None = None,
    source_kind: str = "source_extraction",
    node_ids: Sequence[str] | None = None,
    include_edges: bool = True,
    proposal_digest: str | None = None,
) -> GraphContribution:
    """Map a typed CandidateGraphPreview into a Kernel contribution."""
    world = _require_nonempty(world_id, field="world_id")
    revision_id = _require_nonempty(source_revision_id, field="source_revision_id")
    if not revision_id.startswith("sha256:"):
        revision_id = f"sha256:{revision_id}"
    kind = _require_nonempty(source_kind, field="source_kind")

    artifact_id = _require_nonempty(
        source_artifact_id
        or (preview.source_artifact_ids[0] if preview.source_artifact_ids else None),
        field="source_artifact_id",
    )
    session_id = preview.session_id
    campaign_id = preview.campaign_id
    scope = campaign_scope or campaign_id

    allow = set(node_ids) if node_ids is not None else None
    nodes = [
        node
        for node in preview.nodes
        if allow is None or node.node_id in allow
    ]
    if not nodes:
        raise CandidateGraphMappingError("candidate graph has no nodes to map")

    mapped_node_ids = {node.node_id for node in nodes}
    edges_in_scope: list[CandidateEdge] = []
    if include_edges:
        edges_in_scope = [
            edge
            for edge in preview.edges
            if edge.from_node_id in mapped_node_ids and edge.to_node_id in mapped_node_ids
        ]

    require_single_verified_source_artifact(
        preview=preview,
        verified_artifact_id=artifact_id,
        nodes=nodes,
        edges=edges_in_scope,
    )

    diagnostics: list[str] = []
    node_assertions: list[GraphContributionAssertion] = []
    for node in nodes:
        diagnostics.extend(semantic_diagnostics(node))
        node_assertions.append(
            map_candidate_node_to_assertion(
                node,
                source_revision_id=revision_id,
                verified_source_artifact_id=artifact_id,
                campaign_scope=scope,
                source_domain=source_domain,
                session_id=session_id,
                campaign_id=campaign_id,
                source_uri=source_uri,
            )
        )

    edge_assertions: list[GraphContributionAssertion] = []
    for edge in edges_in_scope:
        diagnostics.extend(semantic_diagnostics(edge))
        edge_assertions.append(
            map_candidate_edge_to_assertion(
                edge,
                source_revision_id=revision_id,
                verified_source_artifact_id=artifact_id,
                campaign_scope=scope,
                source_domain=source_domain,
                session_id=session_id,
                campaign_id=campaign_id,
                source_uri=source_uri,
            )
        )

    return create_graph_contribution(
        world_id=world,
        source_kind=kind,  # type: ignore[arg-type]
        source_artifact_id=artifact_id,
        source_revision_id=revision_id,
        extraction_profile=extraction_profile,
        campaign_scope=scope,
        authored_by=authored_by,
        candidate_assertions=[*node_assertions, *edge_assertions],
        proposal_digest=proposal_digest,
        diagnostics=[
            *diagnostics,
            f"mapped_nodes:{len(node_assertions)}",
            f"mapped_edges:{len(edge_assertions)}",
            f"preview_id:{preview.preview_id}",
            f"source_kind:{kind}",
        ],
    )
