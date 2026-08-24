"""Storage-neutral World Graph facts for governed mutation (CUTOVER D.1).

This is Buddy-owned adaptation logic, not an authority store, cache, agent
context, or graph engine. It carries only the object identity facts the
current exact-run prepare → confirm workflow needs: revision identity,
object ids, labels, kinds, aliases, plus the identity-decision / redirect /
canon-state fields the current classifier demonstrably reads.

Producers:

- ``mutation_context_from_store`` — retained ``buddy_files`` / fixture path
- DungeonMind native producer lives in
  ``apps.live_control_server.integrations.dungeonmind.world_graph_writes``
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from graph_memory.kernel.identity_models import (
    IdentityCandidate,
    IdentityDecisionRecord,
    IdentityResolution,
)
from graph_memory.kernel.identity_policy import (
    DEFAULT_IDENTITY_RESOLUTION_POLICY,
    IdentityResolutionPolicy,
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_DND_VOCAB_PREFIX = "dnd5e:"


def wire_kind(value: str | None) -> str:
    """Strip the DungeonMind vocabulary prefix so identity matches Buddy kinds."""
    if not value:
        return ""
    return (
        value[len(_DND_VOCAB_PREFIX) :]
        if value.startswith(_DND_VOCAB_PREFIX)
        else value
    )


@dataclass(frozen=True)
class MutationObject:
    """One object identity fact visible to governed mutation."""

    object_id: str
    label: str
    kind: str
    aliases: tuple[str, ...] = ()
    canon_state: str = ""
    memory_state: str = ""


@dataclass(frozen=True)
class WorldGraphMutationContext:
    """Exact-revision identity facts for prepare / confirm.

    ``revision_id`` is the sealed parent. ``head_revision_id`` is the current
    published head at the moment the context was built (may equal revision_id).
    """

    world_id: str
    revision_id: str
    head_revision_id: str
    objects: Mapping[str, MutationObject]
    alias_owners: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    identity_redirects: Mapping[str, str] = field(default_factory=dict)
    identity_decisions: tuple[IdentityDecisionRecord, ...] = ()
    identity_ledger_records: tuple[Mapping[str, Any], ...] = ()

    def object_ids(self) -> frozenset[str]:
        return frozenset(self.objects)

    def alias_owner_map(self) -> dict[str, str]:
        """First-owner map for connect-existing alias skip diagnostics."""
        return {
            alias: owners[0]
            for alias, owners in self.alias_owners.items()
            if owners
        }


def mutation_context_from_store(
    store: Any,
    *,
    world_id: str,
    revision_id: str,
    head_revision_id: str,
) -> WorldGraphMutationContext:
    """Adapt a file-backed ``UnionSupergraphStore`` into the mutation context."""
    objects: dict[str, MutationObject] = {}
    for node_id, node in dict(getattr(store, "nodes", {}) or {}).items():
        state = dict(getattr(node, "state", None) or {})
        objects[str(node_id)] = MutationObject(
            object_id=str(node_id),
            label=str(getattr(node, "label", "") or ""),
            kind=str(getattr(node, "kind", "") or ""),
            aliases=tuple(
                str(alias)
                for alias in list(getattr(node, "aliases", None) or [])
                if str(alias).strip()
            ),
            canon_state=str(
                state.get("identity_canon_state") or state.get("canon_state") or ""
            ),
            memory_state=str(state.get("memory_state") or ""),
        )

    alias_owners: dict[str, tuple[str, ...]] = {}
    for alias, owner in dict(getattr(store, "aliases", {}) or {}).items():
        key = str(alias)
        owner_id = str(owner)
        if not key or not owner_id:
            continue
        prior = alias_owners.get(key, ())
        if owner_id not in prior:
            alias_owners[key] = (*prior, owner_id)

    redirects: dict[str, str] = {}
    for raw in list(getattr(store, "identity_redirects", None) or []):
        status = str(getattr(raw, "status", "") or "")
        if status != "active":
            continue
        source = str(getattr(raw, "from_node_id", "") or "")
        target = str(getattr(raw, "to_node_id", "") or "")
        if source and target and source != target:
            redirects[source] = target

    decisions: list[IdentityDecisionRecord] = []
    for raw in list(getattr(store, "identity_decisions", None) or []):
        try:
            decisions.append(IdentityDecisionRecord.model_validate(raw))
        except Exception:
            continue

    return WorldGraphMutationContext(
        world_id=world_id,
        revision_id=revision_id,
        head_revision_id=head_revision_id,
        objects=objects,
        alias_owners=alias_owners,
        identity_redirects=redirects,
        identity_decisions=tuple(decisions),
    )


_CANDIDATE_DECISION_KINDS = frozenset(
    {"reject_candidate", "human_override", "mark_ambiguous"}
)


def _iso_timestamp(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def identity_facts_from_dungeonmind_decisions(
    decisions: Sequence[Any],
) -> tuple[dict[str, str], dict[str, tuple[str, ...]], tuple[IdentityDecisionRecord, ...]]:
    """Adapt durable DungeonMind identity decisions into classifier facts.

    DungeonMind has no ``source_candidate_id`` field. For reject / override /
    ambiguous marks, the native equivalent is ``subject_object_ids[0]`` (the
    candidate id the decision was recorded against). Active merges become
    identity redirects: every non-target subject maps to the merge target.
    Merge side-effect alias rewrites are folded into ``alias_owners`` so a
    merged-away label still resolves to the surviving object.
    """
    redirects: dict[str, str] = {}
    extra_alias_owners: dict[str, tuple[str, ...]] = {}
    mapped: list[IdentityDecisionRecord] = []
    for raw in decisions:
        kind = str(getattr(raw, "decision_kind", "") or "")
        status = str(getattr(raw, "status", "") or "active")
        subjects = [
            str(item)
            for item in list(getattr(raw, "subject_object_ids", None) or [])
            if str(item).strip()
        ]
        targets = [
            str(item)
            for item in list(getattr(raw, "target_object_ids", None) or [])
            if str(item).strip()
        ]
        source_candidate_id = getattr(raw, "source_candidate_id", None)
        if not source_candidate_id and kind in _CANDIDATE_DECISION_KINDS and subjects:
            source_candidate_id = subjects[0]
        record = IdentityDecisionRecord.model_validate(
            {
                "decision_id": str(getattr(raw, "decision_id", "") or ""),
                "world_id": str(getattr(raw, "world_id", "") or ""),
                "decision_kind": kind,
                "created_at": _iso_timestamp(getattr(raw, "created_at", None)),
                "actor": str(getattr(raw, "actor", None) or "system"),
                "reason": str(
                    getattr(raw, "reason", None) or "dungeonmind identity decision"
                ),
                "source_candidate_id": (
                    str(source_candidate_id) if source_candidate_id else None
                ),
                "subject_node_id": subjects[0] if subjects else None,
                "target_node_id": targets[0] if targets else None,
                "affected_node_ids": subjects,
                "alias": getattr(raw, "alias", None),
                "reversible": bool(getattr(raw, "reversible", True)),
                "supersedes_decision_ids": list(
                    getattr(raw, "supersedes_decision_ids", None) or []
                ),
                "status": status,
                "merge_side_effects": None,
            }
        )
        mapped.append(record)
        if status != "active" or kind != "merge" or not targets:
            continue
        target = targets[0]
        for subject in subjects:
            if subject != target:
                redirects[subject] = target
        side_effects = getattr(raw, "merge_side_effects", None)
        if side_effects is None:
            continue
        for rewrite in list(getattr(side_effects, "alias_map_rewrites", None) or []):
            if isinstance(rewrite, dict):
                key = str(rewrite.get("alias_key") or "").strip()
                new_owner = str(rewrite.get("new_owner_node_id") or "").strip()
            else:
                key = str(getattr(rewrite, "alias_key", "") or "").strip()
                new_owner = str(getattr(rewrite, "new_owner_node_id", "") or "").strip()
            if key and new_owner:
                prior = extra_alias_owners.get(key, ())
                if new_owner not in prior:
                    extra_alias_owners[key] = (*prior, new_owner)
        for alias in list(getattr(side_effects, "aliases_added_to_target", None) or []):
            key = str(alias).strip()
            if not key:
                continue
            prior = extra_alias_owners.get(key, ())
            if target not in prior:
                extra_alias_owners[key] = (*prior, target)
    return redirects, extra_alias_owners, tuple(mapped)


def apply_identity_redirects_to_objects(
    objects: Mapping[str, MutationObject],
    redirects: Mapping[str, str],
) -> dict[str, MutationObject]:
    """Materialize merge redirects onto object identity state.

    DungeonMind graph payloads may still list merge-source objects as
    canonical. Classifier matching must treat those sources as merged-away
    and follow redirects to the surviving identity.
    """
    updated = dict(objects)
    for source in redirects:
        obj = updated.get(source)
        if obj is None or _is_merged_away_identity(obj):
            continue
        updated[source] = MutationObject(
            object_id=obj.object_id,
            label=obj.label,
            kind=obj.kind,
            aliases=obj.aliases,
            canon_state="merged_away",
            memory_state="merged_away",
        )
    return updated


def mutation_context_from_world_root(
    root: Path,
    world_id: str,
    *,
    revision_id: str | None = None,
) -> WorldGraphMutationContext:
    """File-mode producer: open a Buddy world root and adapt the pinned revision."""
    from graph_memory.kernel import open_current_world_graph
    from graph_memory.kernel.world_graph import load_world_graph_revision

    head, current_revision, current_store = open_current_world_graph(root, world_id)
    head_id = head.head_revision_id
    pinned = (revision_id or "").strip() or head_id
    store = (
        current_store
        if pinned == current_revision.revision_id or pinned == head_id
        else load_world_graph_revision(root, world_id, pinned)
    )
    return mutation_context_from_store(
        store,
        world_id=world_id,
        revision_id=pinned,
        head_revision_id=head_id,
    )


def mutation_objects_as_match_dicts(
    context: WorldGraphMutationContext,
) -> list[dict[str, Any]]:
    """Head-node dicts for the diagnostic fixed-candidate scorer."""
    return [
        {
            "node_id": obj.object_id,
            "label": obj.label,
            "node_type": obj.kind,
            "aliases": list(obj.aliases),
        }
        for obj in context.objects.values()
    ]


def endpoint_available(
    node_id: str,
    *,
    selected_node_subjects: set[str],
    context: WorldGraphMutationContext,
) -> bool:
    if node_id in selected_node_subjects:
        return True
    return node_id in context.objects


# ---------------------------------------------------------------------------
# Identity classifier over mutation-context facts (one algorithm)
# ---------------------------------------------------------------------------


def _norm(value: str) -> str:
    return value.strip().lower()


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


def _object_surface_terms(obj: MutationObject) -> set[str]:
    terms = {_norm(obj.label)}
    for alias in obj.aliases:
        if alias.strip():
            terms.add(_norm(alias))
    return {term for term in terms if term}


def _resolve_redirect(object_id: str, redirects: Mapping[str, str]) -> str:
    visited: set[str] = set()
    current = object_id
    while current in redirects:
        if current in visited:
            return object_id
        visited.add(current)
        current = redirects[current]
    return current


def _is_noncanonical_provisional(obj: MutationObject) -> bool:
    return obj.canon_state in {"noncanonical_provisional", "provisional"}


def _is_rejected_identity(obj: MutationObject) -> bool:
    return obj.canon_state in {"rejected", "retracted"}


def _is_merged_away_identity(obj: MutationObject) -> bool:
    return obj.memory_state == "merged_away" or obj.canon_state == "merged_away"


def _active_canonical_objects(
    context: WorldGraphMutationContext,
) -> dict[str, MutationObject]:
    result: dict[str, MutationObject] = {}
    for object_id, obj in context.objects.items():
        if object_id in context.identity_redirects:
            continue
        if _is_merged_away_identity(obj) or _is_rejected_identity(obj):
            continue
        if _is_noncanonical_provisional(obj):
            continue
        if _resolve_redirect(object_id, context.identity_redirects) != object_id:
            continue
        result[object_id] = obj
    return result


def _active_provisional_objects(
    context: WorldGraphMutationContext,
) -> dict[str, MutationObject]:
    result: dict[str, MutationObject] = {}
    for object_id, obj in context.objects.items():
        if object_id in context.identity_redirects:
            continue
        if _is_merged_away_identity(obj) or _is_rejected_identity(obj):
            continue
        if not _is_noncanonical_provisional(obj):
            continue
        if _resolve_redirect(object_id, context.identity_redirects) != object_id:
            continue
        result[object_id] = obj
    return result


def _alias_map_matches(
    context: WorldGraphMutationContext,
    terms: set[str],
) -> list[str]:
    matches: list[str] = []
    for alias, owners in context.alias_owners.items():
        if _norm(alias) not in terms:
            continue
        matches.extend(owners)
    return matches


def _decision_for_candidate(
    context: WorldGraphMutationContext,
    candidate: IdentityCandidate,
) -> IdentityDecisionRecord | None:
    active = []
    for record in context.identity_decisions:
        if record.status != "active":
            continue
        if record.decision_kind not in _CANDIDATE_DECISION_KINDS:
            continue
        if record.source_candidate_id == candidate.candidate_id:
            active.append(record)
            continue
        if (
            not record.source_candidate_id
            and record.subject_node_id == candidate.candidate_id
        ):
            active.append(record)
    if not active:
        return None
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
    context: WorldGraphMutationContext,
    candidate: IdentityCandidate,
    *,
    policy: IdentityResolutionPolicy,
) -> tuple[list[MutationObject], list[MutationObject], list[MutationObject]]:
    terms = _candidate_surface_terms(candidate)
    if not terms:
        return [], [], []

    candidate_kind = _norm(candidate.object_kind)
    same_kind: dict[str, MutationObject] = {}
    cross_kind: dict[str, MutationObject] = {}
    provisional_same_kind: dict[str, MutationObject] = {}

    canonical = _active_canonical_objects(context)
    provisional = _active_provisional_objects(context)

    if policy.alias_match_kinds:
        for node_id in _alias_map_matches(context, terms):
            resolved_id = _resolve_redirect(node_id, context.identity_redirects)
            if resolved_id in canonical:
                obj = canonical[resolved_id]
                if _norm(obj.kind) == candidate_kind:
                    same_kind[resolved_id] = obj
                elif policy.block_cross_kind_alias_collision:
                    cross_kind[resolved_id] = obj
                continue
            if resolved_id in provisional:
                obj = provisional[resolved_id]
                if _norm(obj.kind) == candidate_kind:
                    provisional_same_kind[resolved_id] = obj
                elif policy.block_cross_kind_alias_collision:
                    cross_kind[resolved_id] = obj
                continue
            obj = context.objects.get(resolved_id)
            if obj is None or _is_merged_away_identity(obj) or _is_rejected_identity(obj):
                continue
            if policy.block_cross_kind_alias_collision and _norm(obj.kind) != candidate_kind:
                cross_kind[resolved_id] = obj

    for object_id, obj in canonical.items():
        if not (terms & _object_surface_terms(obj)):
            continue
        if policy.exact_label_match_kinds and _norm(obj.kind) == candidate_kind:
            same_kind[object_id] = obj
        elif policy.block_cross_kind_alias_collision and _norm(obj.kind) != candidate_kind:
            cross_kind[object_id] = obj

    for object_id, obj in provisional.items():
        if not (terms & _object_surface_terms(obj)):
            continue
        if _norm(obj.kind) == candidate_kind:
            provisional_same_kind[object_id] = obj
        elif policy.block_cross_kind_alias_collision:
            cross_kind[object_id] = obj

    return (
        list(same_kind.values()),
        list(cross_kind.values()),
        list(provisional_same_kind.values()),
    )


def resolve_identity_against_context(
    context: WorldGraphMutationContext,
    candidate: IdentityCandidate,
    *,
    policy: IdentityResolutionPolicy | None = None,
) -> IdentityResolution:
    """Classify identity against mutation-context facts. Does not mutate."""
    active_policy = policy or DEFAULT_IDENTITY_RESOLUTION_POLICY

    prior = _decision_for_candidate(context, candidate)
    if prior is not None:
        return _resolution_from_decision(candidate, prior)

    same_kind, cross_kind, provisional_same_kind = _find_plausible_matches(
        context, candidate, policy=active_policy
    )

    if cross_kind and active_policy.block_cross_kind_alias_collision:
        blocked_ids = [obj.object_id for obj in cross_kind]
        diagnostics = [
            (
                f"Cross-kind collision: candidate kind={candidate.object_kind!r} "
                f"conflicts with existing "
                f"{obj.kind!r} node {obj.object_id} ({obj.label!r})"
            )
            for obj in cross_kind
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
        match_ids = [obj.object_id for obj in same_kind]
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="ambiguous",
            diagnostics=[
                "Multiple plausible same-kind matches: " + ", ".join(match_ids),
                *[f"match:{obj.object_id}:{obj.label}" for obj in same_kind],
            ],
            requires_human_review=True,
        )

    if len(same_kind) == 1:
        target = same_kind[0]
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="resolved_existing",
            target_node_id=target.object_id,
            diagnostics=[f"Exact same-kind match to existing node {target.object_id}"],
            requires_human_review=False,
            canon_state="canonical",
        )

    if len(provisional_same_kind) > 1:
        match_ids = [obj.object_id for obj in provisional_same_kind]
        return IdentityResolution(
            world_id=candidate.world_id,
            candidate_id=candidate.candidate_id,
            outcome="ambiguous",
            diagnostics=[
                "Multiple provisional same-kind matches (not canonical): "
                + ", ".join(match_ids),
                *[
                    f"provisional_match:{obj.object_id}:{obj.label}"
                    for obj in provisional_same_kind
                ],
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
            provisional_node_id=provisional.object_id,
            diagnostics=[
                f"Matched existing noncanonical provisional identity {provisional.object_id}; "
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


__all__ = [
    "MutationObject",
    "WorldGraphMutationContext",
    "apply_identity_redirects_to_objects",
    "endpoint_available",
    "identity_facts_from_dungeonmind_decisions",
    "mutation_context_from_store",
    "mutation_context_from_world_root",
    "mutation_objects_as_match_dicts",
    "resolve_identity_against_context",
    "wire_kind",
]
