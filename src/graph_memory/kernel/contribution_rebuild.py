"""Rebuild world graph payloads from contribution ledger + identity decisions (PR005)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from graph_memory.kernel.contribution_models import ContributionMergeResult
from graph_memory.kernel.identity_decisions import (
    merge_identity,
    record_identity_decision,
    split_identity,
    unmerge_identity,
)
from graph_memory.kernel.identity_models import IdentityDecisionRecord
from graph_memory.kernel.world_graph import (
    WorldGraphNotFoundError,
    load_current_world_graph,
    load_world_graph_revision,
    publish_world_graph_revision,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
    write_rebuild_report,
)


def _canonical_graph_fingerprint(store: UnionSupergraphStore) -> str:
    """Stable comparison payload for rebuild equivalence."""
    payload = store.model_dump(mode="json", by_alias=True)
    focused = {
        "nodes": payload.get("nodes", {}),
        "edges": payload.get("edges", {}),
        "aliases": payload.get("aliases", {}),
        "assertion_support": payload.get("assertion_support", {}),
        "evidence": payload.get("evidence", {}),
        "source_artifacts": payload.get("source_artifacts", {}),
    }
    return json.dumps(focused, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _apply_identity_decision(
    store: UnionSupergraphStore, decision: IdentityDecisionRecord
) -> UnionSupergraphStore:
    kind = decision.decision_kind
    if kind == "merge":
        if not decision.subject_node_id or not decision.target_node_id:
            return store
        updated, _ = merge_identity(
            store,
            world_id=decision.world_id,
            source_node_id=decision.subject_node_id,
            target_node_id=decision.target_node_id,
            actor=decision.actor,
            reason=decision.reason,
        )
        return updated
    if kind == "split":
        if not decision.subject_node_id or not decision.target_node_id:
            return store
        updated, _ = split_identity(
            store,
            world_id=decision.world_id,
            merged_node_id=decision.subject_node_id,
            new_node_id=decision.target_node_id,
            actor=decision.actor,
            reason=decision.reason,
        )
        return updated
    if kind == "unmerge":
        # Unmerge requires the original merge decision id in supersedes list.
        if not decision.supersedes_decision_ids:
            return record_identity_decision(store, decision)
        updated, _ = unmerge_identity(
            store,
            world_id=decision.world_id,
            decision_id=decision.supersedes_decision_ids[0],
            actor=decision.actor,
            reason=decision.reason,
        )
        return updated
    return record_identity_decision(store, decision)


def _collect_identity_decisions(
    root: Path,
    world_id: str,
    contribution_ids: list[str],
    explicit_decision_ids: list[str] | None,
) -> list[IdentityDecisionRecord]:
    decisions: list[IdentityDecisionRecord] = []
    seen: set[str] = set()

    # Prefer decisions already present on the current head (authoritative replay order).
    try:
        _head, _rev, current = load_current_world_graph(root, world_id)
        for raw in current.identity_decisions:
            record = IdentityDecisionRecord.model_validate(raw)
            if explicit_decision_ids is not None and record.decision_id not in explicit_decision_ids:
                continue
            if record.decision_id in seen:
                continue
            seen.add(record.decision_id)
            decisions.append(record)
    except WorldGraphNotFoundError:
        pass

    if explicit_decision_ids is not None:
        return [d for d in decisions if d.decision_id in set(explicit_decision_ids)]

    # Also gather ids referenced by contributions (may already be in head).
    for cid in contribution_ids:
        contrib = load_contribution_record(root, world_id, cid)
        for decision_id in contrib.identity_decision_ids:
            if decision_id in seen:
                continue
            # If not on head, we cannot reconstruct opaque decision payloads from id alone.
            # Rebuild relies on decisions persisted in the graph payload.
            continue

    return decisions


def rebuild_from_contributions(
    root: Path,
    *,
    world_id: str,
    contribution_ids: list[str] | None = None,
    identity_decision_ids: list[str] | None = None,
    publish: bool = False,
) -> ContributionMergeResult:
    """Replay active contributions (+ identity decisions) onto the baseline revision.

    Compares the rebuilt payload to the current head. Optionally publishes a rebuild
    revision when ``publish=True`` and equivalence holds or when forced by caller.
    """
    index = load_contribution_index(root, world_id)
    diagnostics: list[str] = []
    if index.baseline_revision_id is None:
        raise WorldGraphNotFoundError(
            f"world {world_id!r} has no contribution baseline_revision_id; "
            "merge at least one contribution after a baseline publish"
        )

    baseline = load_world_graph_revision(root, world_id, index.baseline_revision_id)
    working = baseline.model_copy(deep=True)

    # Clear contribution-derived support before replay.
    working = working.model_copy(update={"assertion_support": {}})

    from graph_memory.kernel.contribution_merge import (
        _mark_graph_objects_unsupported,
        _remove_contribution_support,
        _support_map,
        _with_support_map,
        apply_accepted_assertions,
        rebuild_adjacency,
    )

    if contribution_ids is None:
        # Full historical replay: apply each non-failed contribution, then
        # remove support for superseded/retracted ones so unsupported objects
        # remain inspectable (matching head semantics).
        replay_ids = [
            cid
            for cid in index.all_contribution_ids
            if cid not in set(index.failed_contribution_ids)
        ]
    else:
        replay_ids = list(contribution_ids)

    accepted_ids: list[str] = []
    for cid in replay_ids:
        contrib = load_contribution_record(root, world_id, cid)
        if contrib.status == "failed":
            diagnostics.append(f"skip_failed:{cid}")
            continue
        working, _support, applied = apply_accepted_assertions(working, contrib)
        accepted_ids.extend(applied)
        if contrib.status in {"superseded", "retracted"}:
            support = _support_map(working)
            unsupported = _remove_contribution_support(
                support,
                cid,
                as_superseded=(contrib.status == "superseded"),
            )
            working = _with_support_map(working, support)
            working = _mark_graph_objects_unsupported(working, support, unsupported)
            diagnostics.append(f"replayed_{contrib.status}_support_removal:{cid}")

    identity_decisions = _collect_identity_decisions(
        root, world_id, replay_ids, identity_decision_ids
    )
    for decision in identity_decisions:
        if decision.status != "active":
            continue
        working = _apply_identity_decision(working, decision)

    working = working.model_copy(update={"adjacency": rebuild_adjacency(working)})

    head, head_revision, current = load_current_world_graph(root, world_id)
    equivalent = _canonical_graph_fingerprint(working) == _canonical_graph_fingerprint(
        current
    )
    if equivalent:
        diagnostics.append("rebuild_equivalent_to_head")
    else:
        diagnostics.append("rebuild_differs_from_head")
        diagnostics.append(
            f"node_count_rebuild={len(working.nodes)} head={len(current.nodes)}"
        )
        diagnostics.append(
            f"edge_count_rebuild={len(working.edges)} head={len(current.edges)}"
        )

    report: dict[str, Any] = {
        "world_id": world_id,
        "baseline_revision_id": index.baseline_revision_id,
        "head_revision_id": head.head_revision_id,
        "contribution_ids": replay_ids,
        "identity_decision_ids": [d.decision_id for d in identity_decisions],
        "equivalent_to_head": equivalent,
        "diagnostics": diagnostics,
    }
    write_rebuild_report(root, world_id, report)

    revision_id: str | None = None
    published = False
    if publish:
        result = publish_world_graph_revision(
            root,
            world_id,
            working,
            operation_ids=["rebuild:from_contributions", *replay_ids],
            expected_parent_revision_id=head.head_revision_id,
        )
        revision_id = result.revision.revision_id
        published = True
    else:
        revision_id = head_revision.revision_id

    return ContributionMergeResult(
        world_id=world_id,
        parent_revision_id=head.head_revision_id,
        revision_id=revision_id,
        contribution_ids=replay_ids,
        accepted_assertion_ids=accepted_ids,
        diagnostics=diagnostics,
        published=published,
    )
