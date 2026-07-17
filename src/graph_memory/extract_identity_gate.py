"""Head-pinned identity gate for candidate-graph promotion.

Runs Kernel ``resolve_identity`` against the current World Supergraph store and
emits a review package: accepted proposals, unresolved mentions, rejected
assertions, plus a fixed-candidate scorer report for operator review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from graph_memory import identity_resolution as ir
from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    candidate_graph_to_contribution,
    kernel_kind_for_node_type,
    map_candidate_edge_to_assertion,
    map_candidate_node_to_assertion,
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
from graph_memory.union_supergraph.model import UnionSupergraphStore

_MUTATING_OUTCOMES = frozenset({"resolved_existing", "created_new", "human_override"})
_NON_MUTATING_OUTCOMES = frozenset(
    {"ambiguous", "blocked_collision", "rejected", "provisional_new"}
)


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
    diagnostics: list[str] = field(default_factory=list)

    def to_review_package(self) -> dict[str, Any]:
        return {
            "schema": "dmb_extract_identity_gate_review_v1",
            "world_id": self.world_id,
            "parent_revision_id": self.parent_revision_id,
            "node_id_map": dict(self.node_id_map),
            "scorer_report": dict(self.scorer_report),
            "diagnostics": list(self.diagnostics),
            "accepted_proposals": [
                a.model_dump(mode="json") for a in self.accepted_proposals
            ],
            "unresolved_mentions": [
                m.model_dump(mode="json") for m in self.unresolved_mentions
            ],
            "rejected_assertions": [
                a.model_dump(mode="json") for a in self.rejected_assertions
            ],
            "contribution_candidate": self.contribution.model_dump(mode="json"),
        }


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
    candidate_nodes: Sequence[Mapping[str, Any]],
    store: UnionSupergraphStore,
    *,
    threshold: float = 0.6,
) -> dict[str, Any]:
    """Score extract nodes against the fixed head node set (diagnostics only)."""
    head_nodes = _head_nodes_as_match_dicts(store)
    cand_list = [dict(node) for node in candidate_nodes]
    pairs = ir.best_match_assignment(
        head_nodes,
        cand_list,
        ir.node_match_score,
        threshold=threshold,
    )
    matched_head = {gi for gi, _ci, _s in pairs}
    matched_cand = {ci for _gi, ci, _s in pairs}
    # Ambiguity: a candidate with 2+ head partners above threshold.
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
    node: Mapping[str, Any],
    store: UnionSupergraphStore,
) -> str:
    """Pick Kernel object_kind so same-kind exact match can attach (e.g. pc:caelynn)."""
    base = kernel_kind_for_node_type(str(node.get("node_type") or ""))
    label = str(node.get("label") or "").strip().lower()
    if not label:
        return base
    raw_type = str(node.get("node_type") or "").strip().lower()
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
    candidate_graph: Mapping[str, Any],
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
        for node in list(candidate_graph.get("nodes") or [])
        if isinstance(node, dict)
        and (allow is None or str(node.get("node_id") or "") in allow)
    ]
    if not nodes:
        raise CandidateGraphMappingError("candidate graph has no nodes to gate")

    candidate_contribution = candidate_graph_to_contribution(
        candidate_graph,
        world_id=world_id,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        extraction_profile=extraction_profile,
        authored_by=authored_by,
        source_domain=source_domain,
        source_uri=source_uri,
        node_ids=[str(n.get("node_id") or "") for n in nodes],
        include_edges=False,
    )

    artifact_id = candidate_contribution.source_artifact_id or ""
    revision_id = candidate_contribution.source_revision_id or source_revision_id
    session_id = str(candidate_graph.get("session_id") or "").strip() or None
    campaign_id = str(candidate_graph.get("campaign_id") or "").strip() or None
    scope = campaign_scope or campaign_id

    scorer_report = build_fixed_candidate_scorer_report(nodes, store)

    accepted_proposals: list[GraphContributionAssertion] = []
    unresolved: list[ContributionIdentityMention] = []
    rejected: list[GraphContributionAssertion] = []
    node_id_map: dict[str, str] = {}
    diagnostics: list[str] = [
        f"parent_revision_id:{parent_revision_id}",
        f"scorer_matched:{len(scorer_report.get('matched') or [])}",
        f"scorer_ambiguity:{len(scorer_report.get('unresolved_ambiguity') or [])}",
    ]

    for node in nodes:
        extract_id = str(node.get("node_id") or "")
        label = str(node.get("label") or extract_id)
        object_kind = _infer_object_kind(node, store)
        evidence_refs = [
            str(ref.get("source_span_ref_id") or "")
            for ref in list(node.get("evidence_refs") or [])
            if isinstance(ref, dict) and str(ref.get("source_span_ref_id") or "").strip()
        ]
        identity_candidate = IdentityCandidate(
            world_id=world_id,
            candidate_id=extract_id,
            label=label,
            object_kind=object_kind,
            aliases=[label],
            evidence_ref_ids=evidence_refs,
            campaign_scope=scope,
            source_artifact_id=artifact_id,
            proposed_node_id=extract_id,
        )
        resolution = resolve_identity(store, identity_candidate)
        diagnostics.append(
            f"identity:{extract_id}:{resolution.outcome}:{resolution.target_node_id or resolution.created_node_id or resolution.provisional_node_id}"
        )

        if resolution.outcome in _NON_MUTATING_OUTCOMES:
            unresolved.append(
                ContributionIdentityMention(
                    mention_id=extract_id,
                    label=label,
                    object_kind=object_kind,
                    aliases=[label],
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
                        source_artifact_id=artifact_id,
                        source_revision_id=revision_id,
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
                    aliases=[label],
                    evidence_ref_ids=evidence_refs,
                    identity_resolution_outcome=resolution.outcome or "unresolved",
                    diagnostics=[*resolution.diagnostics, "no_durable_node_id"],
                    candidate_node_ids=[],
                )
            )
            continue

        node_id_map[extract_id] = durable_id
        accepted_proposals.append(
            map_candidate_node_to_assertion(
                node,
                source_artifact_id=artifact_id,
                source_revision_id=revision_id,
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
        for edge in list(candidate_graph.get("edges") or []):
            if not isinstance(edge, dict):
                continue
            from_id = str(edge.get("from_node_id") or "")
            to_id = str(edge.get("to_node_id") or "")
            if from_id not in mapped or to_id not in mapped:
                continue
            accepted_proposals.append(
                map_candidate_edge_to_assertion(
                    edge,
                    source_artifact_id=artifact_id,
                    source_revision_id=revision_id,
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
        source_kind="source_extraction",
        source_artifact_id=artifact_id,
        source_revision_id=revision_id,
        extraction_profile=extraction_profile,
        campaign_scope=scope,
        authored_by=authored_by,
        candidate_assertions=list(candidate_contribution.candidate_assertions),
        accepted_assertions=[],  # operator confirm promotes accepted_proposals
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
        diagnostics=diagnostics,
    )


def build_accepted_contribution_from_proposals(
    gate: IdentityGateResult,
    *,
    accepted_assertion_ids: Sequence[str] | None = None,
    authored_by: str | None = None,
) -> GraphContribution:
    """Build a merge-ready contribution from selected accepted proposals."""
    allow = set(accepted_assertion_ids) if accepted_assertion_ids is not None else None
    selected = [
        assertion
        for assertion in gate.accepted_proposals
        if allow is None or assertion.assertion_id in allow
    ]
    if not selected:
        raise CandidateGraphMappingError("no accepted proposals selected for merge")

    # Edges require both endpoints present in accepted node set or already on head.
    node_subjects = {
        a.subject_node_id
        for a in selected
        if a.assertion_kind == "node" and a.subject_node_id
    }
    filtered: list[GraphContributionAssertion] = []
    for assertion in selected:
        if assertion.assertion_kind == "edge":
            if (
                assertion.subject_node_id not in node_subjects
                and assertion.subject_node_id not in gate.node_id_map.values()
            ):
                # Endpoint may already exist on head via resolved_existing map values.
                pass
            if assertion.subject_node_id is None or assertion.target_node_id is None:
                continue
        filtered.append(assertion)

    base = gate.contribution
    return create_graph_contribution(
        world_id=gate.world_id,
        source_kind="source_extraction",
        source_artifact_id=base.source_artifact_id,
        source_revision_id=base.source_revision_id,
        extraction_profile=base.extraction_profile,
        campaign_scope=base.campaign_scope,
        authored_by=authored_by or base.authored_by,
        accepted_assertions=filtered,
        rejected_assertions=list(gate.rejected_assertions),
        unresolved_mentions=list(gate.unresolved_mentions),
        diagnostics=[
            *gate.diagnostics,
            f"accepted_for_merge:{len(filtered)}",
            f"parent_revision_id:{gate.parent_revision_id}",
        ],
    )
