"""Rebuild world graph payloads from contribution ledger + identity decisions (PR005)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from graph_memory.kernel.contribution_models import ContributionMergeResult
from graph_memory.kernel.contributions import (
    _canonicalize_graph_contribution_assertions,
    compute_contribution_source_payload_sha256,
)
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
from graph_memory.world_supergraph.identity_decision_store import (
    list_identity_decision_records,
    load_identity_decision_record,
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
        "contribution_source_payload_sha256": payload.get(
            "contribution_source_payload_sha256", {}
        ),
        "initialization_contribution_ids": payload.get(
            "initialization_contribution_ids", []
        ),
        "initialization_plan_digest": payload.get("initialization_plan_digest"),
        "initialization_attestation_digest": payload.get(
            "initialization_attestation_digest"
        ),
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
    """Load identity decisions from the durable ledger (not the current head).

    Rebuild must not depend on the head as an input while also comparing against
    it. Decision payloads are synced to the ledger on every successful publish.
    """
    decisions: list[IdentityDecisionRecord] = []
    seen: set[str] = set()

    for record in list_identity_decision_records(root, world_id):
        if explicit_decision_ids is not None and record.decision_id not in set(
            explicit_decision_ids
        ):
            continue
        if record.decision_id in seen:
            continue
        seen.add(record.decision_id)
        decisions.append(record)

    if explicit_decision_ids is not None:
        return decisions

    # Resolve contribution-referenced decision ids from the durable ledger.
    for cid in contribution_ids:
        contrib = load_contribution_record(root, world_id, cid)
        for decision_id in contrib.identity_decision_ids:
            if decision_id in seen:
                continue
            try:
                record = load_identity_decision_record(root, world_id, decision_id)
            except FileNotFoundError:
                continue
            seen.add(decision_id)
            decisions.append(record)

    return decisions


def rebuild_from_contributions(
    root: Path,
    *,
    world_id: str,
    contribution_ids: list[str] | None = None,
    identity_decision_ids: list[str] | None = None,
    publish: bool = False,
    compare_revision_id: str | None = None,
) -> ContributionMergeResult:
    """Replay active contributions (+ identity decisions) onto the baseline revision.

    Identity decisions are loaded from the durable identity-decision ledger, not
    from the current head. The rebuilt payload is compared for equivalence:

    - Always against the current head (``equivalent_to_head`` /
      ``rebuild_equivalent_to_head``).
    - Additionally against ``compare_revision_id`` when set
      (``equivalent_to_pinned_revision`` /
      ``rebuild_equivalent_to_pinned_revision``).

    When ``compare_revision_id`` is set, ``publish`` must be False. The pin is
    the audit target; head equivalence is reported separately so a concurrent
    head advance cannot be mislabeled as pinned-audit success.
    """
    if compare_revision_id is not None and publish:
        raise ValueError(
            "compare_revision_id cannot be used with publish=True; "
            "pin comparison only applies to audit rebuilds"
        )
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
    assertion_identity_rekeys: list[dict[str, str]] = []
    payload_digests = dict(baseline.contribution_source_payload_sha256)
    for cid in replay_ids:
        contrib = load_contribution_record(root, world_id, cid)
        if contrib.status == "failed":
            diagnostics.append(f"skip_failed:{cid}")
            continue
        # Digest the on-disk ledger record before in-memory identity rekeying so
        # migration leave ledger bytes authoritative for graph-data source reads.
        payload_digests[contrib.contribution_id] = (
            compute_contribution_source_payload_sha256(contrib)
        )
        contrib, rekeys = _canonicalize_graph_contribution_assertions(contrib)
        for old_assertion_id, new_assertion_id in rekeys:
            assertion_identity_rekeys.append(
                {
                    "contribution_id": contrib.contribution_id,
                    "old_assertion_id": old_assertion_id,
                    "new_assertion_id": new_assertion_id,
                }
            )
            diagnostics.append(
                "assertion_identity_rekeyed:"
                f"{contrib.contribution_id}:{old_assertion_id}->{new_assertion_id}"
            )
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

    baseline_decision_ids = {
        item.get("decision_id")
        for item in (working.identity_decisions or [])
        if isinstance(item, dict) and item.get("decision_id")
    }
    identity_decisions = _collect_identity_decisions(
        root, world_id, replay_ids, identity_decision_ids
    )
    for decision in identity_decisions:
        if decision.status != "active":
            continue
        # Decisions already present on the baseline revision are already reflected
        # in baseline graph state — skip re-application to avoid duplicates.
        if decision.decision_id in baseline_decision_ids:
            continue
        working = _apply_identity_decision(working, decision)

    working = working.model_copy(
        update={
            "adjacency": rebuild_adjacency(working),
            "contribution_source_payload_sha256": payload_digests,
        }
    )

    head, head_revision, head_store = load_current_world_graph(root, world_id)
    if compare_revision_id is not None:
        pin = str(compare_revision_id).strip()
        if not pin:
            raise ValueError("compare_revision_id must be non-empty when provided")
        compared_store = load_world_graph_revision(root, world_id, pin)
        compared_revision_id = pin
        if head.head_revision_id != pin:
            diagnostics.append(
                f"head_advanced_past_compare_revision:{head.head_revision_id}"
            )
        diagnostics.append(f"rebuild_compare_revision:{pin}")
    else:
        compared_store = head_store
        compared_revision_id = head.head_revision_id

    init_plan = compared_store.initialization_plan_digest
    init_attest = compared_store.initialization_attestation_digest
    init_contribs = list(compared_store.initialization_contribution_ids)
    if init_plan is None or init_attest is None or not init_contribs:
        # Lazy import avoids kernel circular import via world_initialization.
        from graph_memory.kernel.world_initialization import (
            compute_initialization_attestation_digest,
            read_initialization_receipt,
        )

        receipt = read_initialization_receipt(root, world_id)
        if receipt is not None:
            init_plan = init_plan or receipt.plan_digest
            init_attest = init_attest or compute_initialization_attestation_digest(
                receipt.approval_attestation
            )
            if not init_contribs:
                init_contribs = [
                    item.contribution_id for item in receipt.ordered_contributions
                ]
            diagnostics.append("rebuild_restored_initialization_digests_from_receipt")
    if init_plan is not None:
        working = working.model_copy(
            update={
                "initialization_contribution_ids": init_contribs,
                "initialization_plan_digest": init_plan,
                "initialization_attestation_digest": init_attest,
            }
        )
    equivalent_to_compared = (
        _canonical_graph_fingerprint(working)
        == _canonical_graph_fingerprint(compared_store)
    )
    equivalent_to_head_store = (
        _canonical_graph_fingerprint(working)
        == _canonical_graph_fingerprint(head_store)
    )
    if equivalent_to_compared:
        diagnostics.append("rebuild_equivalent_to_pre_publish_head")
        if compare_revision_id is not None:
            diagnostics.append("rebuild_equivalent_to_pinned_revision")
    else:
        diagnostics.append("rebuild_differs_from_pre_publish_head")
        diagnostics.append(
            f"node_count_rebuild={len(working.nodes)} compared={len(compared_store.nodes)}"
        )
        diagnostics.append(
            f"edge_count_rebuild={len(working.edges)} compared={len(compared_store.edges)}"
        )
        if compare_revision_id is not None:
            diagnostics.append("rebuild_differs_from_pinned_revision")

    revision_id: str | None = None
    published = False
    published_revision_id: str | None = None
    equivalent_to_published_head: bool | None = None
    if publish:
        result = publish_world_graph_revision(
            root,
            world_id,
            working,
            operation_ids=["rebuild:from_contributions", *replay_ids],
            expected_parent_revision_id=head.head_revision_id,
        )
        published_revision_id = result.revision.revision_id
        revision_id = published_revision_id
        published = True
        published_store = load_world_graph_revision(
            root, world_id, published_revision_id
        )
        equivalent_to_published_head = (
            _canonical_graph_fingerprint(working)
            == _canonical_graph_fingerprint(published_store)
        )
        diagnostics.append("rebuild_published_new_head")
        if equivalent_to_published_head:
            diagnostics.append("rebuild_equivalent_to_published_head")
            diagnostics.append("rebuild_equivalent_to_head")
        else:
            diagnostics.append("rebuild_differs_from_published_head")
            diagnostics.append("rebuild_differs_from_head")
    else:
        revision_id = (
            compared_revision_id
            if compare_revision_id is not None
            else head_revision.revision_id
        )
        # Head equivalence is always against the actual current head store —
        # never aliased from a pinned compare revision.
        if equivalent_to_head_store:
            diagnostics.append("rebuild_equivalent_to_head")
        else:
            diagnostics.append("rebuild_differs_from_head")

    report: dict[str, Any] = {
        "world_id": world_id,
        "baseline_revision_id": index.baseline_revision_id,
        "compared_head_revision_id": compared_revision_id,
        "current_head_revision_id": head.head_revision_id,
        "published_revision_id": published_revision_id,
        "published": published,
        "head_revision_id": published_revision_id or head.head_revision_id,
        "contribution_ids": replay_ids,
        "identity_decision_ids": [d.decision_id for d in identity_decisions],
        "assertion_identity_rekeys": assertion_identity_rekeys,
        "equivalent_to_pre_publish_head": equivalent_to_compared,
        "equivalent_to_pinned_revision": (
            equivalent_to_compared if compare_revision_id is not None else None
        ),
        "equivalent_to_published_head": equivalent_to_published_head,
        "equivalent_to_head": (
            equivalent_to_published_head
            if published
            else equivalent_to_head_store
        ),
        "diagnostics": diagnostics,
    }
    write_rebuild_report(root, world_id, report)

    return ContributionMergeResult(
        world_id=world_id,
        parent_revision_id=compared_revision_id,
        revision_id=revision_id,
        contribution_ids=replay_ids,
        accepted_assertion_ids=accepted_ids,
        diagnostics=diagnostics,
        published=published,
    )
