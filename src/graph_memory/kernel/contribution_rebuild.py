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
from graph_memory.union_supergraph.model import (
    ContributionReplayManifestEntry,
    UnionSupergraphStore,
)
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
        "contribution_replay_manifest": payload.get("contribution_replay_manifest", []),
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


def _pinned_replay_manifest(
    pinned_store: UnionSupergraphStore,
) -> list[ContributionReplayManifestEntry]:
    """Load the revision-bound contribution replay plan, failing closed if absent."""
    raw = list(pinned_store.contribution_replay_manifest or [])
    if not raw:
        if pinned_store.contribution_source_payload_sha256:
            raise ValueError(
                "pinned revision lacks contribution_replay_manifest; "
                "cannot audit lifecycle-accurate replay from digests alone"
            )
        return []
    return [
        entry
        if isinstance(entry, ContributionReplayManifestEntry)
        else ContributionReplayManifestEntry.model_validate(entry)
        for entry in raw
    ]


def _identity_decisions_from_store_snapshot(
    store: UnionSupergraphStore,
    *,
    explicit_decision_ids: list[str] | None = None,
) -> list[IdentityDecisionRecord]:
    """Replay identity decisions from a revision snapshot, not the live ledger."""
    allowed = None if explicit_decision_ids is None else set(explicit_decision_ids)
    decisions: list[IdentityDecisionRecord] = []
    seen: set[str] = set()
    for raw in store.identity_decisions or []:
        decision = IdentityDecisionRecord.model_validate(raw)
        if allowed is not None and decision.decision_id not in allowed:
            continue
        if decision.decision_id in seen:
            continue
        seen.add(decision.decision_id)
        decisions.append(decision)
    if allowed is not None:
        missing = sorted(allowed - seen)
        if missing:
            raise ValueError(
                "pinned identity decision ids missing from revision snapshot: "
                + ",".join(missing)
            )
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
    """Replay contributions (+ identity decisions) onto the baseline revision.

    Unpinned rebuilds load contribution lifecycle and identity decisions from the
    durable ledgers and compare against the current head.

    When ``compare_revision_id`` is set, ``publish`` must be False. The pin is the
    audit target for the comparison graph, the contribution replay plan (ordered
    membership + lifecycle status + digests), and the identity-decision snapshot
    bound into that revision. Head equivalence is reported separately.
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

    pinned_store: UnionSupergraphStore | None = None
    pinned_revision_id: str | None = None
    pinned_manifest: list[ContributionReplayManifestEntry] | None = None
    if compare_revision_id is not None:
        pinned_revision_id = str(compare_revision_id).strip()
        if not pinned_revision_id:
            raise ValueError("compare_revision_id must be non-empty when provided")
        pinned_store = load_world_graph_revision(root, world_id, pinned_revision_id)
        diagnostics.append(f"rebuild_compare_revision:{pinned_revision_id}")
        pinned_manifest = _pinned_replay_manifest(pinned_store)

    replay_status_by_id: dict[str, str] = {}
    replay_digest_by_id: dict[str, str] = {}
    if contribution_ids is None:
        if pinned_manifest is not None:
            replay_ids = [entry.contribution_id for entry in pinned_manifest]
            replay_status_by_id = {
                entry.contribution_id: entry.status for entry in pinned_manifest
            }
            replay_digest_by_id = {
                entry.contribution_id: entry.source_payload_sha256
                for entry in pinned_manifest
            }
            diagnostics.append(
                f"rebuild_replay_pinned_to_revision:{pinned_revision_id}"
            )
        else:
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
        if pinned_manifest is not None:
            manifest_by_id = {
                entry.contribution_id: entry for entry in pinned_manifest
            }
            missing = [cid for cid in replay_ids if cid not in manifest_by_id]
            if missing:
                raise ValueError(
                    "explicit contribution_ids missing from pinned replay "
                    "manifest: " + ",".join(missing)
                )
            replay_status_by_id = {
                cid: manifest_by_id[cid].status for cid in replay_ids
            }
            replay_digest_by_id = {
                cid: manifest_by_id[cid].source_payload_sha256 for cid in replay_ids
            }

    accepted_ids: list[str] = []
    assertion_identity_rekeys: list[dict[str, str]] = []
    payload_digests = dict(baseline.contribution_source_payload_sha256)
    rebuilt_manifest: list[ContributionReplayManifestEntry] = []
    for cid in replay_ids:
        contrib = load_contribution_record(root, world_id, cid)
        # Digest the on-disk ledger record before in-memory identity rekeying so
        # migration leave ledger bytes authoritative for graph-data source reads.
        actual_digest = compute_contribution_source_payload_sha256(contrib)
        expected_digest = replay_digest_by_id.get(cid)
        if expected_digest is not None and actual_digest != expected_digest:
            raise ValueError(
                "pinned contribution source digest mismatch for "
                f"{cid}: ledger no longer matches revision-bound digest"
            )
        if pinned_store is not None:
            # Lifecycle comes from the pinned revision, never the live ledger.
            effective_status = replay_status_by_id.get(cid)
            if effective_status is None:
                raise ValueError(
                    f"pinned contribution {cid} lacks replay-manifest status"
                )
        else:
            effective_status = contrib.status
            if effective_status == "failed":
                diagnostics.append(f"skip_failed:{cid}")
                continue

        payload_digests[contrib.contribution_id] = actual_digest
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
        if effective_status in {"superseded", "retracted"}:
            support = _support_map(working)
            unsupported = _remove_contribution_support(
                support,
                cid,
                as_superseded=(effective_status == "superseded"),
            )
            working = _with_support_map(working, support)
            working = _mark_graph_objects_unsupported(working, support, unsupported)
            diagnostics.append(f"replayed_{effective_status}_support_removal:{cid}")
        if effective_status in {"active", "superseded", "retracted"}:
            rebuilt_manifest.append(
                ContributionReplayManifestEntry(
                    contribution_id=cid,
                    status=effective_status,  # type: ignore[arg-type]
                    source_payload_sha256=actual_digest,
                )
            )

    baseline_decision_ids = {
        item.get("decision_id")
        for item in (working.identity_decisions or [])
        if isinstance(item, dict) and item.get("decision_id")
    }
    if pinned_store is not None:
        identity_decisions = _identity_decisions_from_store_snapshot(
            pinned_store,
            explicit_decision_ids=identity_decision_ids,
        )
        diagnostics.append(
            f"rebuild_identity_decisions_pinned_to_revision:{pinned_revision_id}"
        )
    else:
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
            "contribution_replay_manifest": rebuilt_manifest,
        }
    )

    head, head_revision, head_store = load_current_world_graph(root, world_id)
    if pinned_store is not None:
        compared_store = pinned_store
        compared_revision_id = pinned_revision_id
        assert compared_revision_id is not None
        if head.head_revision_id != compared_revision_id:
            diagnostics.append(
                f"head_advanced_past_compare_revision:{head.head_revision_id}"
            )
    else:
        compared_store = head_store
        compared_revision_id = head.head_revision_id
        # Legacy heads published before the replay manifest must compare without
        # inventing one on the rebuild side.
        if not list(compared_store.contribution_replay_manifest or []) and not publish:
            working = working.model_copy(update={"contribution_replay_manifest": []})
            diagnostics.append("rebuild_omitted_replay_manifest_for_legacy_compare")

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
        diagnostics.append("rebuild_equivalent_to_compared_revision")
        if compare_revision_id is not None:
            diagnostics.append("rebuild_equivalent_to_pinned_revision")
    else:
        diagnostics.append("rebuild_differs_from_compared_revision")
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
        "compared_revision_id": compared_revision_id,
        "current_head_revision_id": head.head_revision_id,
        "published_revision_id": published_revision_id,
        "published": published,
        "head_revision_id": published_revision_id or head.head_revision_id,
        "contribution_ids": replay_ids,
        "identity_decision_ids": [d.decision_id for d in identity_decisions],
        "assertion_identity_rekeys": assertion_identity_rekeys,
        "equivalent_to_compared_revision": equivalent_to_compared,
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
