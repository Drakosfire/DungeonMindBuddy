"""Durable identity decision records and reversible merge/split/unmerge (PR004).

Assertion-level evidence reassignment after split is deferred to PR005. This
module owns identity/alias/redirect state and replayable decision records.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from graph_memory.kernel.identity_models import (
    IdentityDecisionKind,
    IdentityDecisionRecord,
)
from graph_memory.union_supergraph.model import (
    UnionIdentityRedirect,
    UnionSupergraphNode,
    UnionSupergraphStore,
)
from graph_memory.union_supergraph.redirects import active_identity_redirect_map

_IDENTITY_DECISION_SCHEMA = "dmb_identity_decision_v0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compute_identity_decision_id(
    *,
    world_id: str,
    decision_kind: IdentityDecisionKind,
    subject_node_id: str | None,
    target_node_id: str | None,
    alias: str | None,
    source_candidate_id: str | None,
    reason: str,
) -> str:
    payload = {
        "world_id": world_id,
        "decision_kind": decision_kind,
        "subject_node_id": subject_node_id,
        "target_node_id": target_node_id,
        "alias": alias,
        "source_candidate_id": source_candidate_id,
        "reason": reason,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"identity-decision:{digest}"


def build_identity_decision_record(
    *,
    world_id: str,
    decision_kind: IdentityDecisionKind,
    actor: str,
    reason: str,
    source_candidate_id: str | None = None,
    subject_node_id: str | None = None,
    target_node_id: str | None = None,
    affected_node_ids: list[str] | None = None,
    alias: str | None = None,
    reversible: bool = True,
    supersedes_decision_ids: list[str] | None = None,
    created_at: str | None = None,
) -> IdentityDecisionRecord:
    if not actor.strip():
        raise ValueError("actor must be non-empty")
    if not reason.strip():
        raise ValueError("reason must be non-empty")
    decision_id = compute_identity_decision_id(
        world_id=world_id,
        decision_kind=decision_kind,
        subject_node_id=subject_node_id,
        target_node_id=target_node_id,
        alias=alias,
        source_candidate_id=source_candidate_id,
        reason=reason,
    )
    return IdentityDecisionRecord(
        decision_id=decision_id,
        world_id=world_id,
        decision_kind=decision_kind,
        created_at=created_at or _utc_now_iso(),
        actor=actor.strip(),
        reason=reason.strip(),
        source_candidate_id=source_candidate_id,
        subject_node_id=subject_node_id,
        target_node_id=target_node_id,
        affected_node_ids=list(affected_node_ids or []),
        alias=alias,
        reversible=reversible,
        supersedes_decision_ids=list(supersedes_decision_ids or []),
        status="active",
    )


def _decision_dicts(store: UnionSupergraphStore) -> list[dict[str, Any]]:
    return [dict(item) for item in store.identity_decisions]


def _append_decision(
    store: UnionSupergraphStore,
    decision: IdentityDecisionRecord,
) -> UnionSupergraphStore:
    decisions = _decision_dicts(store)
    decisions.append(decision.model_dump(mode="json"))
    return store.model_copy(update={"identity_decisions": decisions})


def _replace_decisions(
    store: UnionSupergraphStore,
    decisions: list[IdentityDecisionRecord],
) -> UnionSupergraphStore:
    return store.model_copy(
        update={"identity_decisions": [d.model_dump(mode="json") for d in decisions]}
    )


def _load_decisions(store: UnionSupergraphStore) -> list[IdentityDecisionRecord]:
    return [IdentityDecisionRecord.model_validate(raw) for raw in store.identity_decisions]


def _dedupe_extend(existing: list[str], extra: list[str]) -> list[str]:
    seen = {item.casefold(): item for item in existing}
    result = list(existing)
    for item in extra:
        key = item.casefold()
        if key not in seen:
            seen[key] = item
            result.append(item)
    return result


def _mark_node_state(
    node: UnionSupergraphNode,
    **state_updates: Any,
) -> UnionSupergraphNode:
    updated = dict(node.state)
    updated.update(state_updates)
    return node.model_copy(update={"state": updated})


def record_identity_decision(
    store: UnionSupergraphStore,
    decision: IdentityDecisionRecord,
) -> UnionSupergraphStore:
    """Append a durable identity decision record without applying merge/split side effects.

    Use ``merge_identity`` / ``split_identity`` / ``unmerge_identity`` for mutating
    redirect/alias state. This function is the low-level append path for human
    override, reject, and ambiguity markers.
    """
    if not decision.actor.strip():
        raise ValueError("actor must be non-empty")
    if not decision.reason.strip():
        raise ValueError("reason must be non-empty")
    return _append_decision(store, decision)


def merge_identity(
    store: UnionSupergraphStore,
    *,
    world_id: str,
    source_node_id: str,
    target_node_id: str,
    actor: str,
    reason: str,
) -> tuple[UnionSupergraphStore, IdentityDecisionRecord]:
    if source_node_id == target_node_id:
        raise ValueError("source_node_id and target_node_id must differ")
    if source_node_id not in store.nodes:
        raise KeyError(f"unknown source_node_id: {source_node_id}")
    if target_node_id not in store.nodes:
        raise KeyError(f"unknown target_node_id: {target_node_id}")

    decision = build_identity_decision_record(
        world_id=world_id,
        decision_kind="merge",
        actor=actor,
        reason=reason,
        subject_node_id=source_node_id,
        target_node_id=target_node_id,
        affected_node_ids=[source_node_id, target_node_id],
    )

    source = store.nodes[source_node_id]
    target = store.nodes[target_node_id]

    aliases_to_union = _dedupe_extend(
        list(target.aliases),
        [source.label, *source.aliases],
    )
    evidence_to_union = _dedupe_extend(list(target.evidence_ref_ids), list(source.evidence_ref_ids))
    domains_to_union = _dedupe_extend(list(target.source_domains), list(source.source_domains))

    updated_target = target.model_copy(
        update={
            "aliases": aliases_to_union,
            "evidence_ref_ids": evidence_to_union,
            "source_domains": domains_to_union,
            "state": {
                **dict(target.state),
                "identity_state": "survivor",
                "identity_canon_state": "canonical",
                "last_identity_decision_id": decision.decision_id,
            },
        }
    )
    updated_source = _mark_node_state(
        source,
        memory_state="merged_away",
        identity_canon_state="merged_away",
        merged_into=target_node_id,
        last_identity_decision_id=decision.decision_id,
    )

    alias_map = dict(store.aliases)
    for alias in aliases_to_union:
        alias_map[alias.casefold()] = target_node_id
    alias_map[source.label.casefold()] = target_node_id

    redirect = UnionIdentityRedirect(
        redirect_id=f"redirect:{decision.decision_id}",
        campaign_id=store.campaign_id,
        from_node_id=source_node_id,
        to_node_id=target_node_id,
        assertion_id=f"assertion:{decision.decision_id}",
        merge_reason=reason,
        created_at=decision.created_at,
        status="active",
        materialization_pass_id=f"pass:kernel-identity:{decision.decision_id}",
    )

    # Retract any prior active redirect from the same source.
    redirects = []
    for existing in store.identity_redirects:
        if existing.from_node_id == source_node_id and existing.status == "active":
            redirects.append(existing.model_copy(update={"status": "retracted"}))
        else:
            redirects.append(existing)
    redirects.append(redirect)

    nodes = dict(store.nodes)
    nodes[source_node_id] = updated_source
    nodes[target_node_id] = updated_target

    updated = store.model_copy(
        update={
            "nodes": nodes,
            "aliases": alias_map,
            "identity_redirects": redirects,
        }
    )
    return _append_decision(updated, decision), decision


def split_identity(
    store: UnionSupergraphStore,
    *,
    world_id: str,
    merged_node_id: str,
    new_node_id: str,
    actor: str,
    reason: str,
) -> tuple[UnionSupergraphStore, IdentityDecisionRecord]:
    if merged_node_id == new_node_id:
        raise ValueError("merged_node_id and new_node_id must differ")
    if merged_node_id not in store.nodes:
        raise KeyError(f"unknown merged_node_id: {merged_node_id}")
    if new_node_id in store.nodes:
        raise ValueError(f"new_node_id already exists: {new_node_id}")

    decision = build_identity_decision_record(
        world_id=world_id,
        decision_kind="split",
        actor=actor,
        reason=reason,
        subject_node_id=merged_node_id,
        target_node_id=new_node_id,
        affected_node_ids=[merged_node_id, new_node_id],
    )

    source = store.nodes[merged_node_id]
    new_node = UnionSupergraphNode(
        node_id=new_node_id,
        label=source.label,
        kind=source.kind,
        role=source.role,
        aliases=[],
        source_domains=list(source.source_domains),
        evidence_ref_ids=[],
        state={
            "memory_state": "graph_read_model",
            "identity_canon_state": "canonical",
            "identity_state": "split_from",
            "split_from_node_id": merged_node_id,
            "last_identity_decision_id": decision.decision_id,
            "created_by_identity_split": True,
        },
    )
    updated_source = _mark_node_state(
        source,
        identity_state="split_source",
        last_identity_decision_id=decision.decision_id,
        split_produced_node_id=new_node_id,
    )

    nodes = dict(store.nodes)
    nodes[merged_node_id] = updated_source
    nodes[new_node_id] = new_node

    updated = store.model_copy(update={"nodes": nodes})
    return _append_decision(updated, decision), decision


def unmerge_identity(
    store: UnionSupergraphStore,
    *,
    world_id: str,
    decision_id: str,
    actor: str,
    reason: str,
) -> tuple[UnionSupergraphStore, IdentityDecisionRecord]:
    decisions = _load_decisions(store)
    original = next((d for d in decisions if d.decision_id == decision_id), None)
    if original is None:
        raise KeyError(f"unknown identity decision_id: {decision_id}")
    if original.decision_kind != "merge":
        raise ValueError(f"decision {decision_id} is not a merge decision")
    if original.subject_node_id is None or original.target_node_id is None:
        raise ValueError(f"merge decision {decision_id} missing subject/target node ids")

    unmerge = build_identity_decision_record(
        world_id=world_id,
        decision_kind="unmerge",
        actor=actor,
        reason=reason,
        subject_node_id=original.subject_node_id,
        target_node_id=original.target_node_id,
        affected_node_ids=list(original.affected_node_ids),
        supersedes_decision_ids=[original.decision_id],
    )

    # Mark original merge as superseded (remains inspectable).
    updated_decisions: list[IdentityDecisionRecord] = []
    for decision in decisions:
        if decision.decision_id == original.decision_id:
            updated_decisions.append(decision.model_copy(update={"status": "superseded"}))
        else:
            updated_decisions.append(decision)
    updated_decisions.append(unmerge)

    # Retract active redirect created by the merge.
    redirects: list[UnionIdentityRedirect] = []
    for redirect in store.identity_redirects:
        if (
            redirect.from_node_id == original.subject_node_id
            and redirect.to_node_id == original.target_node_id
            and redirect.status == "active"
        ):
            redirects.append(redirect.model_copy(update={"status": "retracted"}))
        else:
            redirects.append(redirect)

    nodes = dict(store.nodes)
    source = nodes.get(original.subject_node_id)
    if source is not None:
        restored_state = dict(source.state)
        restored_state["memory_state"] = "graph_read_model"
        restored_state["identity_canon_state"] = "canonical"
        restored_state.pop("merged_into", None)
        restored_state["last_identity_decision_id"] = unmerge.decision_id
        restored_state["unmerged_by_decision_id"] = unmerge.decision_id
        nodes[original.subject_node_id] = source.model_copy(update={"state": restored_state})

    updated = store.model_copy(
        update={
            "nodes": nodes,
            "identity_redirects": redirects,
        }
    )
    updated = _replace_decisions(updated, updated_decisions)

    # Sanity: source should no longer be in the active redirect map.
    active = active_identity_redirect_map(updated.identity_redirects)
    if original.subject_node_id in active:
        raise RuntimeError(
            f"unmerge failed to clear active redirect for {original.subject_node_id}"
        )
    return updated, unmerge


# Document schema marker for future serializers / rebuild tooling.
IDENTITY_DECISION_SCHEMA = _IDENTITY_DECISION_SCHEMA
