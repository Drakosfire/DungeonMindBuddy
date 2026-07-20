"""Head-pinned identity gate for candidate-graph promotion.

Runs Kernel ``resolve_identity`` against the current World Supergraph store and
emits a sealed promote proposal: accepted proposals, unresolved mentions,
rejected assertions, plus a fixed-candidate scorer report for operator review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from graph_memory import identity_resolution as ir
from graph_memory.candidate_graph_preview import CandidateGraphPreview, CandidateNode
from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    candidate_graph_to_contribution,
    kernel_kind_for_node_type,
    map_candidate_edge_to_assertion,
    map_candidate_node_to_assertion,
    map_connect_existing_support_assertions,
    require_single_verified_source_artifact,
)
from graph_memory.extract_promote_proposal import (
    compute_selection_digest,
    contribution_meta_from_contribution,
    seal_promote_proposal,
)
from graph_memory.kernel import (
    ContributionIdentityMention,
    GraphContribution,
    GraphContributionAssertion,
    IdentityCandidate,
    create_graph_contribution,
    open_current_world_graph,
    resolve_identity,
)
from graph_memory.kernel.world_graph import load_world_graph_revision
from graph_memory.union_supergraph.model import UnionSupergraphStore

_MUTATING_OUTCOMES = frozenset({"resolved_existing", "created_new", "human_override"})
_CONNECT_EXISTING_OUTCOMES = frozenset({"resolved_existing", "human_override"})
_NON_MUTATING_OUTCOMES = frozenset(
    {"ambiguous", "blocked_collision", "rejected", "provisional_new"}
)


def _require_artifact_id(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        raise CandidateGraphMappingError("source_artifact_id is required")
    return text


@dataclass
class IdentityGateResult:
    """Review package produced by identity gating a candidate graph."""

    parent_revision_id: str
    world_id: str
    contribution: GraphContribution
    accepted_proposals: list[GraphContributionAssertion] = field(default_factory=list)
    unresolved_mentions: list[ContributionIdentityMention] = field(default_factory=list)
    rejected_assertions: list[GraphContributionAssertion] = field(default_factory=list)
    scorer_report: dict[str, Any] = field(default_factory=dict)
    node_id_map: dict[str, str] = field(default_factory=dict)
    identity_outcome_snapshot: dict[str, str] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)
    candidate_preview_id: str = ""
    candidate_schema: str = ""
    candidate_version: str = ""
    source_revision_id: str = ""
    source_artifact_id: str = ""
    verified_source_uri: str | None = None

    def to_review_package(
        self,
        *,
        prepared_by: str,
        world_root: str | None = None,
        candidate_graph_path: str | None = None,
    ) -> dict[str, Any]:
        if not (self.verified_source_uri or "").strip():
            raise CandidateGraphMappingError(
                "verified_source_uri is required to seal a promote proposal"
            )
        return seal_promote_proposal(
            world_id=self.world_id,
            parent_revision_id=self.parent_revision_id,
            source_revision_id=self.source_revision_id,
            source_artifact_id=self.source_artifact_id,
            verified_source_uri=str(self.verified_source_uri),
            candidate_preview_id=self.candidate_preview_id,
            candidate_schema=self.candidate_schema,
            candidate_version=self.candidate_version,
            contribution_meta=contribution_meta_from_contribution(self.contribution),
            accepted_proposals=self.accepted_proposals,
            rejected_assertions=self.rejected_assertions,
            unresolved_mentions=self.unresolved_mentions,
            node_id_map=self.node_id_map,
            identity_outcome_snapshot=self.identity_outcome_snapshot,
            prepared_by=prepared_by,
            scorer_report=self.scorer_report,
            diagnostics=self.diagnostics,
            world_root=world_root,
            candidate_graph_path=candidate_graph_path,
        )


def _candidate_aliases(node: CandidateNode) -> list[str]:
    """Deduped surface terms: label first, then extract-only aliases."""
    label = (node.label or node.node_id or "").strip()
    result: list[str] = []
    seen: set[str] = set()
    for term in [label, *node.aliases]:
        text = str(term).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _head_nodes_as_match_dicts(store: UnionSupergraphStore) -> list[dict[str, Any]]:
    return [
        {
            "node_id": node.node_id,
            "label": node.label,
            "node_type": node.kind,
            "aliases": list(node.aliases),
        }
        for node in store.nodes.values()
    ]


def build_fixed_candidate_scorer_report(
    candidate_nodes: Sequence[CandidateNode],
    store: UnionSupergraphStore,
    *,
    threshold: float = 0.6,
) -> dict[str, Any]:
    """Score extract nodes against the fixed head node set (diagnostics only)."""
    head_nodes = _head_nodes_as_match_dicts(store)
    cand_list = [
        {
            "node_id": node.node_id,
            "label": node.label,
            "node_type": node.node_type,
            "aliases": _candidate_aliases(node),
        }
        for node in candidate_nodes
    ]
    pairs = ir.best_match_assignment(
        head_nodes,
        cand_list,
        ir.node_match_score,
        threshold=threshold,
    )
    matched_head = {gi for gi, _ci, _s in pairs}
    matched_cand = {ci for _gi, ci, _s in pairs}
    ambiguous: list[dict[str, Any]] = []
    for ci, cand in enumerate(cand_list):
        rivals = [
            {
                "head_node_id": head_nodes[gi]["node_id"],
                "score": ir.node_match_score(head_nodes[gi], cand),
            }
            for gi, head in enumerate(head_nodes)
            if ir.node_match_score(head, cand) >= threshold
        ]
        rivals.sort(key=lambda item: -float(item["score"]))
        if len(rivals) >= 2:
            ambiguous.append(
                {
                    "candidate_node_id": cand.get("node_id"),
                    "label": cand.get("label"),
                    "rivals": rivals[:5],
                }
            )
    unmatched_candidates = [
        {
            "node_id": cand_list[i].get("node_id"),
            "label": cand_list[i].get("label"),
        }
        for i in range(len(cand_list))
        if i not in matched_cand
    ]
    unmatched_head = [
        {
            "node_id": head_nodes[i]["node_id"],
            "label": head_nodes[i]["label"],
        }
        for i in range(len(head_nodes))
        if i not in matched_head
    ]
    return {
        "threshold": threshold,
        "head_node_count": len(head_nodes),
        "candidate_node_count": len(cand_list),
        "matched": [
            {
                "head_node_id": head_nodes[gi]["node_id"],
                "candidate_node_id": cand_list[ci].get("node_id"),
                "score": score,
            }
            for gi, ci, score in pairs
        ],
        "unresolved_ambiguity": ambiguous,
        "duplicate_risk": ambiguous,
        "unmatched_candidates": unmatched_candidates,
        "unmatched_head_sample": unmatched_head[:25],
    }


def _infer_object_kind(
    node: CandidateNode,
    store: UnionSupergraphStore,
) -> str:
    """Pick Kernel object_kind so same-kind exact match can attach (e.g. pc:caelynn)."""
    base = kernel_kind_for_node_type(node.node_type)
    label = (node.label or "").strip().lower()
    if not label:
        return base
    raw_type = (node.node_type or "").strip().lower()
    if raw_type in {"character", "pc", "npc"}:
        for node_obj in store.nodes.values():
            terms = {node_obj.label.strip().lower(), *[a.strip().lower() for a in node_obj.aliases]}
            if label in terms and node_obj.kind in {"pc", "npc"}:
                return node_obj.kind
    if raw_type in {"collective", "organization", "party"}:
        for node_obj in store.nodes.values():
            terms = {node_obj.label.strip().lower(), *[a.strip().lower() for a in node_obj.aliases]}
            if label in terms and node_obj.kind in {"party", "faction"}:
                return node_obj.kind
    return base


def _durable_node_id(resolution: Any, extract_node_id: str) -> str | None:
    outcome = resolution.outcome
    if outcome == "resolved_existing":
        return resolution.target_node_id
    if outcome == "created_new":
        return resolution.created_node_id or f"node:{extract_node_id}"
    if outcome == "human_override":
        return resolution.target_node_id or resolution.created_node_id
    return None


def gate_candidate_graph_against_head(
    preview: CandidateGraphPreview,
    *,
    root: Path,
    world_id: str,
    source_artifact_id: str | None = None,
    source_revision_id: str,
    campaign_scope: str | None = None,
    extraction_profile: str | None = "current_default",
    authored_by: str | None = "extract-identity-gate",
    source_domain: str = "recap",
    source_uri: str | None = None,
    node_ids: Sequence[str] | None = None,
    include_edges: bool = True,
) -> IdentityGateResult:
    """Map + resolve identity against the pinned head; emit review proposals."""
    if not str(source_revision_id or "").strip():
        raise CandidateGraphMappingError("source_revision_id is required")

    head, _revision, store = open_current_world_graph(root, world_id)
    parent_revision_id = head.head_revision_id

    allow = set(node_ids) if node_ids is not None else None
    nodes = [
        node
        for node in preview.nodes
        if allow is None or node.node_id in allow
    ]
    if not nodes:
        raise CandidateGraphMappingError("candidate graph has no nodes to gate")

    selected_node_ids = {node.node_id for node in nodes}
    edges_in_scope = []
    if include_edges:
        edges_in_scope = [
            edge
            for edge in preview.edges
            if edge.from_node_id in selected_node_ids
            and edge.to_node_id in selected_node_ids
        ]

    # Resolve verified artifact before mapping so edge-only second artifacts
    # cannot bypass the check that runs inside candidate_graph_to_contribution
    # with include_edges=False.
    artifact_id = _require_artifact_id(
        source_artifact_id
        or (preview.source_artifact_ids[0] if preview.source_artifact_ids else None)
    )
    require_single_verified_source_artifact(
        preview=preview,
        verified_artifact_id=artifact_id,
        nodes=nodes,
        edges=edges_in_scope,
    )

    candidate_contribution = candidate_graph_to_contribution(
        preview,
        world_id=world_id,
        source_artifact_id=artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        extraction_profile=extraction_profile,
        authored_by=authored_by,
        source_domain=source_domain,
        source_uri=source_uri,
        node_ids=[n.node_id for n in nodes],
        include_edges=False,
    )

    revision_id = candidate_contribution.source_revision_id or source_revision_id
    session_id = preview.session_id
    campaign_id = preview.campaign_id
    scope = campaign_scope or campaign_id

    scorer_report = build_fixed_candidate_scorer_report(nodes, store)

    accepted_proposals: list[GraphContributionAssertion] = []
    unresolved: list[ContributionIdentityMention] = []
    rejected: list[GraphContributionAssertion] = []
    node_id_map: dict[str, str] = {}
    identity_outcome_snapshot: dict[str, str] = {}
    diagnostics: list[str] = [
        f"parent_revision_id:{parent_revision_id}",
        f"scorer_matched:{len(scorer_report.get('matched') or [])}",
        f"scorer_ambiguity:{len(scorer_report.get('unresolved_ambiguity') or [])}",
    ]

    for node in nodes:
        extract_id = node.node_id
        label = node.label or extract_id
        node_aliases = _candidate_aliases(node)
        object_kind = _infer_object_kind(node, store)
        evidence_refs = [
            str(ref.source_span_ref_id or "")
            for ref in node.evidence_refs
            if str(ref.source_span_ref_id or "").strip()
        ]
        identity_candidate = IdentityCandidate(
            world_id=world_id,
            candidate_id=extract_id,
            label=label,
            object_kind=object_kind,
            aliases=node_aliases,
            evidence_ref_ids=evidence_refs,
            campaign_scope=scope,
            source_artifact_id=artifact_id,
            proposed_node_id=extract_id,
        )
        resolution = resolve_identity(store, identity_candidate)
        identity_outcome_snapshot[extract_id] = resolution.outcome
        diagnostics.append(
            f"identity:{extract_id}:{resolution.outcome}:{resolution.target_node_id or resolution.created_node_id or resolution.provisional_node_id}"
        )

        if resolution.outcome in _NON_MUTATING_OUTCOMES:
            unresolved.append(
                ContributionIdentityMention(
                    mention_id=extract_id,
                    label=label,
                    object_kind=object_kind,
                    aliases=node_aliases,
                    evidence_ref_ids=evidence_refs,
                    identity_resolution_outcome=resolution.outcome,
                    diagnostics=list(resolution.diagnostics),
                    candidate_node_ids=list(resolution.blocked_by)
                    or (
                        [resolution.provisional_node_id]
                        if resolution.provisional_node_id
                        else []
                    ),
                )
            )
            try:
                rejected.append(
                    map_candidate_node_to_assertion(
                        node,
                        source_revision_id=revision_id,
                        verified_source_artifact_id=artifact_id,
                        campaign_scope=scope,
                        source_domain=source_domain,
                        session_id=session_id,
                        campaign_id=campaign_id,
                        source_uri=source_uri,
                        acceptance_state="rejected",
                        identity_resolution_outcome=resolution.outcome,
                        kind_override=object_kind,
                    )
                )
            except CandidateGraphMappingError as exc:
                diagnostics.append(f"reject_map_failed:{extract_id}:{exc}")
            continue

        durable_id = _durable_node_id(resolution, extract_id)
        if not durable_id or resolution.outcome not in _MUTATING_OUTCOMES:
            unresolved.append(
                ContributionIdentityMention(
                    mention_id=extract_id,
                    label=label,
                    object_kind=object_kind,
                    aliases=node_aliases,
                    evidence_ref_ids=evidence_refs,
                    identity_resolution_outcome=resolution.outcome or "unresolved",
                    diagnostics=[*resolution.diagnostics, "no_durable_node_id"],
                    candidate_node_ids=[],
                )
            )
            continue

        node_id_map[extract_id] = durable_id
        # Connect-existing must not emit a full node assertion: extract-derived
        # role/summary/epistemic payloads disagree with seeded PC assertions and
        # leave two active supports that projection refuses. Keep the durable id
        # mapping so edges can attach; emit support-only (attribute + alias)
        # assertions instead of a competing node assert.
        if resolution.outcome in _CONNECT_EXISTING_OUTCOMES:
            diagnostics.append(
                f"connect_existing_support_only:{extract_id}->{durable_id}"
            )
            support_assertions, alias_skip_diagnostics = (
                map_connect_existing_support_assertions(
                    node,
                    durable_node_id=durable_id,
                    source_revision_id=revision_id,
                    verified_source_artifact_id=artifact_id,
                    campaign_scope=scope,
                    source_domain=source_domain,
                    session_id=session_id,
                    campaign_id=campaign_id,
                    source_uri=source_uri,
                    identity_resolution_outcome=resolution.outcome,
                    alias_owners=dict(store.aliases),
                )
            )
            accepted_proposals.extend(support_assertions)
            diagnostics.extend(alias_skip_diagnostics)
            continue
        accepted_proposals.append(
            map_candidate_node_to_assertion(
                node,
                source_revision_id=revision_id,
                verified_source_artifact_id=artifact_id,
                campaign_scope=scope,
                source_domain=source_domain,
                session_id=session_id,
                campaign_id=campaign_id,
                source_uri=source_uri,
                acceptance_state="accepted",
                identity_resolution_outcome=resolution.outcome,
                kind_override=object_kind,
                subject_node_id_override=durable_id,
            )
        )

    if include_edges:
        mapped = set(node_id_map)
        for edge in edges_in_scope:
            from_id = edge.from_node_id
            to_id = edge.to_node_id
            if from_id not in mapped or to_id not in mapped:
                continue
            accepted_proposals.append(
                map_candidate_edge_to_assertion(
                    edge,
                    source_revision_id=revision_id,
                    verified_source_artifact_id=artifact_id,
                    campaign_scope=scope,
                    source_domain=source_domain,
                    session_id=session_id,
                    campaign_id=campaign_id,
                    source_uri=source_uri,
                    acceptance_state="accepted",
                    identity_resolution_outcome="created_new",
                    node_id_map=node_id_map,
                )
            )

    gated_contribution = create_graph_contribution(
        world_id=world_id,
        source_kind="source_extraction",  # type: ignore[arg-type]
        source_artifact_id=artifact_id,
        source_revision_id=revision_id,
        extraction_profile=extraction_profile,
        campaign_scope=scope,
        authored_by=authored_by,
        candidate_assertions=list(candidate_contribution.candidate_assertions),
        accepted_assertions=[],
        rejected_assertions=list(rejected),
        unresolved_mentions=list(unresolved),
        diagnostics=diagnostics,
    )

    return IdentityGateResult(
        parent_revision_id=parent_revision_id,
        world_id=world_id,
        contribution=gated_contribution,
        accepted_proposals=accepted_proposals,
        unresolved_mentions=unresolved,
        rejected_assertions=rejected,
        scorer_report=scorer_report,
        node_id_map=node_id_map,
        identity_outcome_snapshot=identity_outcome_snapshot,
        diagnostics=diagnostics,
        candidate_preview_id=preview.preview_id,
        candidate_schema=preview.schema,
        candidate_version=preview.version,
        source_revision_id=revision_id,
        source_artifact_id=artifact_id,
        verified_source_uri=source_uri,
    )


def _endpoint_available(
    node_id: str,
    *,
    selected_node_subjects: set[str],
    pinned_store: UnionSupergraphStore,
) -> bool:
    if node_id in selected_node_subjects:
        return True
    return node_id in pinned_store.nodes


def build_accepted_contribution_from_proposals(
    gate: IdentityGateResult,
    *,
    root: Path,
    accepted_assertion_ids: Sequence[str] | None = None,
    proposal_digest: str | None = None,
    contribution_meta: Mapping[str, Any] | None = None,
) -> GraphContribution:
    """Build a merge-ready contribution from selected accepted proposals.

    Durable metadata comes from sealed ``contribution_meta`` (or, for unit
    tests that skip sealing, from ``gate.contribution``). Edge endpoints must
    be selected node subjects or present on the exact pinned parent revision.
    """
    allow = set(accepted_assertion_ids) if accepted_assertion_ids is not None else None
    selected = [
        assertion
        for assertion in gate.accepted_proposals
        if allow is None or assertion.assertion_id in allow
    ]
    if not selected:
        raise CandidateGraphMappingError("no accepted proposals selected for merge")

    pinned_store = load_world_graph_revision(
        root, gate.world_id, gate.parent_revision_id
    )
    node_subjects = {
        a.subject_node_id
        for a in selected
        if a.assertion_kind == "node" and a.subject_node_id
    }

    filtered: list[GraphContributionAssertion] = []
    for assertion in selected:
        if assertion.assertion_kind == "edge":
            subject = assertion.subject_node_id
            target = assertion.target_node_id
            if subject is None or target is None:
                raise CandidateGraphMappingError(
                    f"edge assertion {assertion.assertion_id} missing endpoint ids"
                )
            if not _endpoint_available(
                subject,
                selected_node_subjects=node_subjects,
                pinned_store=pinned_store,
            ):
                raise CandidateGraphMappingError(
                    f"edge assertion {assertion.assertion_id} subject endpoint "
                    f"{subject!r} is neither selected nor on pinned parent "
                    f"{gate.parent_revision_id}"
                )
            if not _endpoint_available(
                target,
                selected_node_subjects=node_subjects,
                pinned_store=pinned_store,
            ):
                raise CandidateGraphMappingError(
                    f"edge assertion {assertion.assertion_id} target endpoint "
                    f"{target!r} is neither selected nor on pinned parent "
                    f"{gate.parent_revision_id}"
                )
        filtered.append(assertion)

    meta = dict(contribution_meta) if contribution_meta is not None else (
        contribution_meta_from_contribution(gate.contribution)
    )
    selection_digest = compute_selection_digest(
        [a.assertion_id for a in filtered]
    )
    return create_graph_contribution(
        world_id=gate.world_id,
        source_kind=str(meta["source_kind"]),  # type: ignore[arg-type]
        source_artifact_id=str(meta["source_artifact_id"]),
        source_revision_id=str(meta["source_revision_id"]),
        extraction_profile=str(meta["extraction_profile"]),
        campaign_scope=meta.get("campaign_scope"),
        authored_by=str(meta["authored_by"]),
        accepted_assertions=filtered,
        rejected_assertions=list(gate.rejected_assertions),
        unresolved_mentions=list(gate.unresolved_mentions),
        proposal_digest=proposal_digest,
        selection_digest=selection_digest,
        diagnostics=[
            f"accepted_for_merge:{len(filtered)}",
            f"parent_revision_id:{gate.parent_revision_id}",
            f"selection_digest:{selection_digest}",
            *(
                [f"proposal_digest:{proposal_digest}"]
                if proposal_digest
                else []
            ),
        ],
    )
