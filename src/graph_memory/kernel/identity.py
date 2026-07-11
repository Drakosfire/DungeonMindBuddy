"""Graph Kernel identity classification (PR004).

``resolve_identity`` / ``classify_identity_outcome`` are pure classifiers: they
return an explicit outcome and do **not** mutate the durable graph. Mutations
happen only through decision-record APIs in ``identity_decisions``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from graph_memory.kernel.identity_models import (
    IdentityCandidate,
    IdentityDecisionRecord,
    IdentityResolution,
)
from graph_memory.kernel.identity_policy import (
    DEFAULT_IDENTITY_RESOLUTION_POLICY,
    IdentityResolutionPolicy,
)
from graph_memory.union_supergraph.model import UnionSupergraphNode, UnionSupergraphStore
from graph_memory.union_supergraph.redirects import (
    active_identity_redirect_map,
    resolve_union_node_id,
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _norm(value: str) -> str:
    return value.strip().lower()


def _norm_kind(value: str) -> str:
    return _norm(value)


def _slug(label: str) -> str:
    slug = _SLUG_RE.sub("_", _norm(label)).strip("_")
    return slug or "unnamed"


def _proposed_created_node_id(candidate: IdentityCandidate) -> str:
    if candidate.proposed_node_id and candidate.proposed_node_id.strip():
        return candidate.proposed_node_id.strip()
    return f"node:{_slug(candidate.label)}"


def _proposed_provisional_node_id(candidate: IdentityCandidate) -> str:
    return f"provisional:{candidate.candidate_id}"


def _candidate_surface_terms(candidate: IdentityCandidate) -> set[str]:
    terms = {_norm(candidate.label)}
    for alias in candidate.aliases:
        if alias.strip():
            terms.add(_norm(alias))
    return {term for term in terms if term}


def _node_surface_terms(node: UnionSupergraphNode) -> set[str]:
    terms = {_norm(node.label)}
    for alias in node.aliases:
        if alias.strip():
            terms.add(_norm(alias))
    return {term for term in terms if term}


def _node_identity_canon_state(node: UnionSupergraphNode) -> str:
    return str(node.state.get("identity_canon_state") or node.state.get("canon_state") or "")


def _is_noncanonical_provisional(node: UnionSupergraphNode) -> bool:
    return _node_identity_canon_state(node) == "noncanonical_provisional"


def _is_rejected_identity(node: UnionSupergraphNode) -> bool:
    return _node_identity_canon_state(node) == "rejected"


def _is_merged_away_identity(node: UnionSupergraphNode) -> bool:
    memory_state = str(node.state.get("memory_state") or "")
    return memory_state == "merged_away" or _node_identity_canon_state(node) == "merged_away"


def _active_canonical_nodes(store: UnionSupergraphStore) -> dict[str, UnionSupergraphNode]:
    """Canonical durable identities only — never provisional, rejected, or merged-away."""
    redirects = active_identity_redirect_map(store.identity_redirects)
    result: dict[str, UnionSupergraphNode] = {}
    for node_id, node in store.nodes.items():
        if node_id in redirects:
            continue
        if _is_merged_away_identity(node):
            continue
        if _is_rejected_identity(node):
            continue
        if _is_noncanonical_provisional(node):
            continue
        # Resolve through redirects so survivors are keyed by canonical id.
        canonical_id = resolve_union_node_id(node_id, redirects)
        if canonical_id != node_id:
            continue
        result[node_id] = node
    return result


def _active_provisional_nodes(store: UnionSupergraphStore) -> dict[str, UnionSupergraphNode]:
    redirects = active_identity_redirect_map(store.identity_redirects)
    result: dict[str, UnionSupergraphNode] = {}
    for node_id, node in store.nodes.items():
        if node_id in redirects or _is_merged_away_identity(node) or _is_rejected_identity(node):
            continue
        if not _is_noncanonical_provisional(node):
            continue
        canonical_id = resolve_union_node_id(node_id, redirects)
        if canonical_id != node_id:
            continue
        result[node_id] = node
    return result


def _alias_map_matches(
    store: UnionSupergraphStore,
    terms: set[str],
) -> list[str]:
    matches: list[str] = []
    for alias, node_id in store.aliases.items():
        if _norm(alias) in terms:
            matches.append(node_id)
    return matches


def _load_decision_records(store: UnionSupergraphStore) -> list[IdentityDecisionRecord]:
    records: list[IdentityDecisionRecord] = []
    for raw in store.identity_decisions:
        try:
            records.append(IdentityDecisionRecord.model_validate(raw))
        except Exception:
            continue
    return records


def _decision_for_candidate(
    store: UnionSupergraphStore,
    candidate: IdentityCandidate,
) -> IdentityDecisionRecord | None:
    active = [
        record
        for record in _load_decision_records(store)
        if record.status == "active" and record.source_candidate_id == candidate.candidate_id
    ]
    if not active:
        return None
    # Prefer the latest by created_at then decision_id for stability.
    active.sort(key=lambda r: (r.created_at, r.decision_id))
    return active[-1]


def _resolution_from_decision(
    candidate: IdentityCandidate,
    decision: IdentityDecisionRecord,
) -> IdentityResolution:
    if decision.decision_kind == "reject_candidate":
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="rejected",
            diagnostics=[f"Rejected by decision {decision.decision_id}: {decision.reason}"],
            requires_human_review=False,
            canon_state="rejected",
            decision_id=decision.decision_id,
        )
    if decision.decision_kind == "mark_ambiguous":
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="ambiguous",
            diagnostics=[f"Marked ambiguous by decision {decision.decision_id}"],
            requires_human_review=True,
            decision_id=decision.decision_id,
        )
    return IdentityResolution(
        world_id=candidate.world_id,
        candidate_id=candidate.candidate_id,
        outcome="human_override",
        target_node_id=decision.target_node_id,
        diagnostics=[
            f"Human override decision {decision.decision_id} by {decision.actor}: {decision.reason}"
        ],
        requires_human_review=False,
        decision_id=decision.decision_id,
        canon_state="canonical" if decision.target_node_id else None,
    )


def _find_plausible_matches(
    store: UnionSupergraphStore,
    candidate: IdentityCandidate,
    *,
    policy: IdentityResolutionPolicy,
) -> tuple[list[UnionSupergraphNode], list[UnionSupergraphNode], list[UnionSupergraphNode]]:
    """Return (canonical_same_kind, cross_kind_collisions, provisional_same_kind)."""
    terms = _candidate_surface_terms(candidate)
    if not terms:
        return [], [], []

    candidate_kind = _norm_kind(candidate.object_kind)
    same_kind: dict[str, UnionSupergraphNode] = {}
    cross_kind: dict[str, UnionSupergraphNode] = {}
    provisional_same_kind: dict[str, UnionSupergraphNode] = {}

    canonical_nodes = _active_canonical_nodes(store)
    provisional_nodes = _active_provisional_nodes(store)

    # Alias map hits — only canonical nodes may become resolved_existing.
    if policy.alias_match_kinds:
        for node_id in _alias_map_matches(store, terms):
            resolved_id = resolve_union_node_id(node_id, store.identity_redirects)
            if resolved_id in canonical_nodes:
                node = canonical_nodes[resolved_id]
                if _norm_kind(node.kind) == candidate_kind:
                    same_kind[resolved_id] = node
                elif policy.block_cross_kind_alias_collision:
                    cross_kind[resolved_id] = node
                continue
            if resolved_id in provisional_nodes:
                node = provisional_nodes[resolved_id]
                if _norm_kind(node.kind) == candidate_kind:
                    provisional_same_kind[resolved_id] = node
                elif policy.block_cross_kind_alias_collision:
                    cross_kind[resolved_id] = node
                continue
            node = store.nodes.get(resolved_id)
            if node is None or _is_merged_away_identity(node) or _is_rejected_identity(node):
                continue
            if policy.block_cross_kind_alias_collision and _norm_kind(node.kind) != candidate_kind:
                cross_kind[resolved_id] = node

    for node_id, node in canonical_nodes.items():
        node_terms = _node_surface_terms(node)
        if not (terms & node_terms):
            continue
        if policy.exact_label_match_kinds and _norm_kind(node.kind) == candidate_kind:
            same_kind[node_id] = node
        elif policy.block_cross_kind_alias_collision and _norm_kind(node.kind) != candidate_kind:
            cross_kind[node_id] = node

    for node_id, node in provisional_nodes.items():
        node_terms = _node_surface_terms(node)
        if not (terms & node_terms):
            continue
        if _norm_kind(node.kind) == candidate_kind:
            provisional_same_kind[node_id] = node
        elif policy.block_cross_kind_alias_collision:
            cross_kind[node_id] = node

    return (
        list(same_kind.values()),
        list(cross_kind.values()),
        list(provisional_same_kind.values()),
    )


def classify_identity_outcome(
    store: UnionSupergraphStore,
    candidate: IdentityCandidate,
    *,
    policy: IdentityResolutionPolicy | None = None,
) -> IdentityResolution:
    """Classify a candidate into an explicit identity outcome without mutating ``store``."""
    active_policy = policy or DEFAULT_IDENTITY_RESOLUTION_POLICY

    prior = _decision_for_candidate(store, candidate)
    if prior is not None:
        return _resolution_from_decision(candidate, prior)

    same_kind, cross_kind, provisional_same_kind = _find_plausible_matches(
        store, candidate, policy=active_policy
    )

    # Confidence never overrides collision policy.
    if cross_kind and active_policy.block_cross_kind_alias_collision:
        blocked_ids = [node.node_id for node in cross_kind]
        diagnostics = [
            (
                f"Cross-kind collision: candidate kind={candidate.object_kind!r} "
                f"conflicts with existing "
                f"{node.kind!r} node {node.node_id} ({node.label!r})"
            )
            for node in cross_kind
        ]
        if candidate.confidence is not None:
            diagnostics.append(
                f"Candidate confidence={candidate.confidence} is not authority and does not "
                "override collision policy"
            )
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="blocked_collision",
            blocked_by=blocked_ids,
            diagnostics=diagnostics,
            requires_human_review=True,
        )

    if len(same_kind) > 1:
        match_ids = [node.node_id for node in same_kind]
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="ambiguous",
            diagnostics=[
                "Multiple plausible same-kind matches: " + ", ".join(match_ids),
                *[f"match:{node.node_id}:{node.label}" for node in same_kind],
            ],
            requires_human_review=True,
        )

    if len(same_kind) == 1:
        target = same_kind[0]
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="resolved_existing",
            target_node_id=target.node_id,
            diagnostics=[f"Exact same-kind match to existing node {target.node_id}"],
            requires_human_review=False,
            canon_state="canonical",
        )

    # Existing provisional matches must not silently promote to resolved_existing.
    if len(provisional_same_kind) > 1:
        match_ids = [node.node_id for node in provisional_same_kind]
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="ambiguous",
            diagnostics=[
                "Multiple provisional same-kind matches (not canonical): " + ", ".join(match_ids),
                *[f"provisional_match:{node.node_id}:{node.label}" for node in provisional_same_kind],
            ],
            requires_human_review=True,
            canon_state="noncanonical_provisional",
        )

    if len(provisional_same_kind) == 1:
        provisional = provisional_same_kind[0]
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="provisional_new",
            provisional_node_id=provisional.node_id,
            diagnostics=[
                f"Matched existing noncanonical provisional identity {provisional.node_id}; "
                "not promoted to canonical resolved_existing",
            ],
            requires_human_review=True,
            canon_state="noncanonical_provisional",
        )

    has_evidence = bool(candidate.evidence_ref_ids)
    if active_policy.require_evidence_for_created_new and not has_evidence:
        if active_policy.allow_provisional_new:
            provisional_id = _proposed_provisional_node_id(candidate)
            return IdentityResolution(
                world_id=candidate.world_id,
                candidate_id=candidate.candidate_id,
                outcome="provisional_new",
                provisional_node_id=provisional_id,
                diagnostics=[
                    "No existing match and insufficient evidence for canonical creation; "
                    "proposing noncanonical provisional identity",
                    f"provisional_node_id={provisional_id}",
                ],
                requires_human_review=True,
                canon_state="noncanonical_provisional",
            )
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="rejected",
            diagnostics=["No match and provisional creation disabled by policy"],
            requires_human_review=False,
            canon_state="rejected",
        )

    created_id = _proposed_created_node_id(candidate)
    return IdentityResolution(
        world_id=candidate.world_id,
        candidate_id=candidate.candidate_id,
        outcome="created_new",
        created_node_id=created_id,
        diagnostics=[
            "No collision; evidence present — instructs canonical creation "
            "(store not mutated by classify/resolve)",
            f"created_node_id={created_id}",
        ],
        requires_human_review=False,
        canon_state="canonical",
    )


def resolve_identity(
    store: UnionSupergraphStore,
    candidate: IdentityCandidate,
    *,
    policy: IdentityResolutionPolicy | None = None,
) -> IdentityResolution:
    """Resolve identity outcome. Does not mutate ``store``."""
    return classify_identity_outcome(store, candidate, policy=policy)


def iter_active_identity_decisions(
    store: UnionSupergraphStore,
) -> Iterable[IdentityDecisionRecord]:
    for record in _load_decision_records(store):
        if record.status == "active":
            yield record
