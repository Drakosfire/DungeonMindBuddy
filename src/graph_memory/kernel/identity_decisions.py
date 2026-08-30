"""Durable identity decision records and reversible merge/split/unmerge (PR004).

Assertion-level evidence reassignment after split is deferred to PR005. This
module owns identity/alias/redirect state and replayable decision records.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from graph_memory.evidence.assertion_support import DurableAssertionSupport
from apps.live_control_server.models.world_graph_contributions import semantic_assertion_value
from graph_memory.kernel.identity_models import (
    IdentityAliasMapRewrite,
    IdentityDecisionKind,
    IdentityDecisionRecord,
    IdentityMergeSideEffects,
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
    merge_side_effects: IdentityMergeSideEffects | None = None,
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
        merge_side_effects=merge_side_effects,
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


def _items_added(existing: list[str], candidates: list[str]) -> list[str]:
    existing_keys = {item.casefold() for item in existing}
    added: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.casefold()
        if key in existing_keys or key in seen:
            continue
        seen.add(key)
        added.append(item)
    return added


def _remove_items(existing: list[str], to_remove: list[str]) -> list[str]:
    remove_keys = {item.casefold() for item in to_remove}
    return [item for item in existing if item.casefold() not in remove_keys]


def _node_identity_canon_state(node: UnionSupergraphNode) -> str:
    return str(node.state.get("identity_canon_state") or node.state.get("canon_state") or "")


def _assert_merge_target_eligible(target: UnionSupergraphNode) -> None:
    memory_state = str(target.state.get("memory_state") or "")
    canon = _node_identity_canon_state(target)
    if memory_state == "merged_away" or canon == "merged_away":
        raise ValueError(
            f"cannot merge into merged_away target {target.node_id}; "
            "use a deliberate human override path if that is intended"
        )
    if canon == "rejected":
        raise ValueError(
            f"cannot merge into rejected target {target.node_id}; "
            "use a deliberate human override path if that is intended"
        )
    if canon == "noncanonical_provisional":
        raise ValueError(
            f"cannot merge into noncanonical_provisional target {target.node_id}; "
            "promote or override explicitly before merge"
        )


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

    Use ``merge_identity`` / ``split_identity`` / ``unmerge_identity`` /
    ``remove_identity_alias`` for mutating redirect/alias state. This function
    is the low-level append path for human override, reject, and ambiguity
    markers.
    """
    if not decision.actor.strip():
        raise ValueError("actor must be non-empty")
    if not decision.reason.strip():
        raise ValueError("reason must be non-empty")
    if decision.decision_kind in {"alias_remove", "alias_add"}:
        raise ValueError(
            f"record_identity_decision cannot apply {decision.decision_kind}; "
            "use remove_identity_alias for alias_remove"
        )
    return _append_decision(store, decision)


def _alias_currently_present(node: UnionSupergraphNode, alias: str) -> bool:
    needle = alias.casefold()
    return any(item.casefold() == needle for item in node.aliases if item)


def _surface_produces_alias_key(node: UnionSupergraphNode, key: str) -> bool:
    if node.label.strip() and node.label.casefold() == key:
        return True
    return any(item.strip() and item.casefold() == key for item in node.aliases)


def _assert_alias_remove_subject_eligible(subject: UnionSupergraphNode) -> None:
    memory_state = str(subject.state.get("memory_state") or "")
    canon = _node_identity_canon_state(subject)
    if memory_state == "merged_away" or canon == "merged_away":
        raise ValueError(
            f"cannot remove alias from merged_away subject {subject.node_id}; "
            "subject is not a current canonical identity"
        )
    if canon == "rejected":
        raise ValueError(
            f"cannot remove alias from rejected subject {subject.node_id}; "
            "subject is not a current canonical identity"
        )
    if canon == "noncanonical_provisional":
        raise ValueError(
            f"cannot remove alias from noncanonical_provisional subject {subject.node_id}; "
            "subject is not a current canonical identity"
        )


def _iter_typed_supports(store: UnionSupergraphStore) -> list[DurableAssertionSupport]:
    supports: list[DurableAssertionSupport] = []
    for value in (store.assertion_support or {}).values():
        if isinstance(value, DurableAssertionSupport):
            supports.append(value)
        elif isinstance(value, dict):
            supports.append(DurableAssertionSupport.model_validate(value))
    return supports


def _candidate_supports_for_subject(
    store: UnionSupergraphStore,
    subject_node_id: str,
) -> list[DurableAssertionSupport]:
    candidates: list[DurableAssertionSupport] = []
    for support in _iter_typed_supports(store):
        if support.support_state != "supported" or not support.active_contribution_ids:
            continue
        kind = support.assertion_kind
        if kind not in {None, "alias", "node"}:
            continue
        if support.graph_object_id not in {None, subject_node_id}:
            continue
        candidates.append(support)
    return candidates


def _assertion_semantic_fingerprint(assertion: Any) -> tuple[Any, ...]:
    return (
        assertion.assertion_kind,
        assertion.subject_node_id,
        assertion.target_node_id,
        assertion.predicate,
        assertion.label,
        json.dumps(
            semantic_assertion_value(assertion.value),
            sort_keys=True,
            separators=(",", ":"),
        ),
        assertion.epistemic_kind,
        assertion.visibility,
        assertion.campaign_scope,
        json.dumps(assertion.temporal_scope, sort_keys=True, separators=(",", ":"))
        if assertion.temporal_scope is not None
        else None,
    )


def _assertion_graph_object_id(assertion: Any) -> str:
    return str(assertion.subject_node_id or assertion.target_node_id or "")


def _load_assertions_from_support(
    root: Path,
    world_id: str,
    support: DurableAssertionSupport,
) -> list[Any]:
    from graph_memory.world_supergraph.contribution_store import load_contribution_record

    resolved: list[Any] = []
    for contribution_id in support.active_contribution_ids:
        try:
            contribution = load_contribution_record(root, world_id, contribution_id)
        except FileNotFoundError as exc:
            raise ValueError(
                f"cannot resolve assertion support {support.assertion_id!r}: "
                f"missing contribution {contribution_id!r}"
            ) from exc
        matched = next(
            (
                candidate
                for candidate in contribution.accepted_assertions
                if candidate.assertion_id == support.assertion_id
            ),
            None,
        )
        if matched is None:
            raise ValueError(
                f"cannot resolve assertion support {support.assertion_id!r}: "
                f"active contribution {contribution_id!r} does not contain the assertion"
            )
        if getattr(matched, "contribution_id", contribution_id) != contribution_id:
            raise ValueError(
                f"cannot resolve assertion support {support.assertion_id!r}: "
                f"assertion contribution_id {matched.contribution_id!r} does not "
                f"match active contribution {contribution_id!r}"
            )
        resolved.append(matched)

    if not resolved:
        raise ValueError(
            f"cannot resolve assertion support {support.assertion_id!r} from "
            f"active contributions {list(support.active_contribution_ids)}"
        )
    return resolved


def _assert_support_copies_consistent(
    support: DurableAssertionSupport,
    assertions: list[Any],
) -> None:
    fingerprints = {_assertion_semantic_fingerprint(item) for item in assertions}
    if len(fingerprints) > 1:
        raise ValueError(
            f"cannot resolve assertion support {support.assertion_id!r}: "
            "semantically divergent active copies"
        )
    expected_object_id = support.graph_object_id
    if expected_object_id is None:
        return
    for assertion in assertions:
        actual = _assertion_graph_object_id(assertion)
        if actual != expected_object_id:
            raise ValueError(
                f"cannot resolve assertion support {support.assertion_id!r}: "
                f"graph_object_id {expected_object_id!r} does not match "
                f"assertion object {actual!r}"
            )


def _assertion_lists_alias(assertion: Any, alias: str) -> bool:
    needle = alias.casefold()
    if assertion.assertion_kind == "alias":
        value = dict(assertion.value or {})
        claimed = str(assertion.label or value.get("alias") or "")
        return bool(claimed.strip()) and claimed.casefold() == needle
    if assertion.assertion_kind == "node":
        value = dict(assertion.value or {})
        return any(
            str(item).strip() and str(item).casefold() == needle
            for item in list(value.get("aliases") or [])
        )
    return False


def _assert_no_independent_semantic_support(
    store: UnionSupergraphStore,
    *,
    world_id: str,
    subject_node_id: str,
    alias: str,
    root: Path | None,
) -> None:
    candidates = _candidate_supports_for_subject(store, subject_node_id)
    if not candidates:
        return
    if root is None:
        raise ValueError(
            f"cannot resolve assertion support for {subject_node_id!r} "
            "without contribution root"
        )
    for support in candidates:
        assertions = _load_assertions_from_support(root, world_id, support)
        if any(
            (
                item.subject_node_id == subject_node_id
                or support.graph_object_id == subject_node_id
            )
            and _assertion_lists_alias(item, alias)
            for item in assertions
        ):
            raise ValueError(
                f"cannot remove alias {alias!r} from {subject_node_id}: "
                "independent semantic support exists"
            )
        _assert_support_copies_consistent(support, assertions)
        subjects = {item.subject_node_id for item in assertions}
        if subjects != {subject_node_id}:
            if support.graph_object_id == subject_node_id:
                raise ValueError(
                    f"cannot resolve assertion support {support.assertion_id!r}: "
                    f"subject {sorted(subjects)!r} does not match {subject_node_id!r}"
                )


def _assert_unmerge_not_blocked_by_alias_remove(
    decisions: list[IdentityDecisionRecord],
    merge: IdentityDecisionRecord,
) -> None:
    if merge.merge_side_effects is None:
        return
    added = {
        item.casefold()
        for item in merge.merge_side_effects.aliases_added_to_target
        if item.strip()
    }
    if not added:
        return
    merge_index = next(
        (
            index
            for index, item in enumerate(decisions)
            if item.decision_id == merge.decision_id
        ),
        None,
    )
    if merge_index is None:
        return
    for decision in decisions[merge_index + 1 :]:
        if decision.status != "active" or decision.decision_kind != "alias_remove":
            continue
        if decision.subject_node_id != merge.target_node_id:
            continue
        if decision.alias and decision.alias.casefold() in added:
            raise ValueError(
                f"cannot unmerge {merge.decision_id} while later alias_remove "
                f"{decision.decision_id} retired {decision.alias!r} from "
                f"{merge.target_node_id}"
            )


def remove_identity_alias(
    store: UnionSupergraphStore,
    *,
    world_id: str,
    subject_node_id: str,
    alias: str,
    actor: str,
    reason: str,
    root: Path | None = None,
) -> tuple[UnionSupergraphStore, IdentityDecisionRecord]:
    """Retire one currently materialized alias from a canonical survivor node."""
    if not str(alias).strip():
        raise ValueError("alias must be non-empty")
    requested_alias = str(alias)
    if subject_node_id not in store.nodes:
        raise KeyError(f"unknown subject_node_id: {subject_node_id}")

    subject = store.nodes[subject_node_id]
    _assert_alias_remove_subject_eligible(subject)
    if requested_alias.casefold() == subject.label.casefold():
        raise ValueError(
            f"cannot remove canonical label {subject.label!r} from {subject_node_id}"
        )

    decision_id = compute_identity_decision_id(
        world_id=world_id,
        decision_kind="alias_remove",
        subject_node_id=subject_node_id,
        target_node_id=None,
        alias=requested_alias,
        source_candidate_id=None,
        reason=reason,
    )
    decisions = _load_decisions(store)
    existing = next(
        (
            item
            for item in decisions
            if item.decision_id == decision_id
            and item.status == "active"
            and item.decision_kind == "alias_remove"
        ),
        None,
    )
    present = _alias_currently_present(subject, requested_alias)
    if existing is None and not present:
        raise ValueError(
            f"alias {requested_alias!r} is not currently materialized on {subject_node_id}"
        )
    if existing is not None and not present:
        return store, existing
    if existing is not None and present:
        raise ValueError(
            f"alias_remove {decision_id} already retired {requested_alias!r} from "
            f"{subject_node_id}; same-reason reintroduction collision"
        )

    _assert_no_independent_semantic_support(
        store,
        world_id=world_id,
        subject_node_id=subject_node_id,
        alias=requested_alias,
        root=root,
    )

    decision = build_identity_decision_record(
        world_id=world_id,
        decision_kind="alias_remove",
        actor=actor,
        reason=reason,
        subject_node_id=subject_node_id,
        target_node_id=None,
        affected_node_ids=[subject_node_id],
        alias=requested_alias,
        merge_side_effects=None,
    )

    updated_aliases = _remove_items(list(subject.aliases), [requested_alias])
    updated_subject = subject.model_copy(
        update={
            "aliases": updated_aliases,
            "state": {
                **dict(subject.state),
                "last_identity_decision_id": decision.decision_id,
            },
        }
    )
    nodes = dict(store.nodes)
    nodes[subject_node_id] = updated_subject

    alias_map = dict(store.aliases)
    key = requested_alias.casefold()
    if alias_map.get(key) == subject_node_id and not _surface_produces_alias_key(
        updated_subject, key
    ):
        alias_map.pop(key, None)

    updated = store.model_copy(update={"nodes": nodes, "aliases": alias_map})
    return _append_decision(updated, decision), decision


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

    source = store.nodes[source_node_id]
    target = store.nodes[target_node_id]
    _assert_merge_target_eligible(target)

    source_surface = [source.label, *source.aliases]
    aliases_added = _items_added(list(target.aliases), source_surface)
    evidence_added = _items_added(list(target.evidence_ref_ids), list(source.evidence_ref_ids))
    domains_added = _items_added(list(target.source_domains), list(source.source_domains))

    aliases_to_union = _dedupe_extend(list(target.aliases), source_surface)
    evidence_to_union = _dedupe_extend(list(target.evidence_ref_ids), list(source.evidence_ref_ids))
    domains_to_union = _dedupe_extend(list(target.source_domains), list(source.source_domains))

    alias_map = dict(store.aliases)
    alias_map_rewrites: list[IdentityAliasMapRewrite] = []
    keys_to_point_at_target = {term.casefold() for term in source_surface if term.strip()}
    for key in sorted(keys_to_point_at_target):
        prior_owner = alias_map.get(key)
        if prior_owner != target_node_id:
            alias_map_rewrites.append(
                IdentityAliasMapRewrite(
                    alias_key=key,
                    prior_owner_node_id=prior_owner,
                    new_owner_node_id=target_node_id,
                )
            )
        alias_map[key] = target_node_id

    side_effects = IdentityMergeSideEffects(
        aliases_added_to_target=aliases_added,
        evidence_ref_ids_added_to_target=evidence_added,
        source_domains_added_to_target=domains_added,
        alias_map_rewrites=alias_map_rewrites,
    )

    decision = build_identity_decision_record(
        world_id=world_id,
        decision_kind="merge",
        actor=actor,
        reason=reason,
        subject_node_id=source_node_id,
        target_node_id=target_node_id,
        affected_node_ids=[source_node_id, target_node_id],
        merge_side_effects=side_effects,
    )

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
    if original.merge_side_effects is None:
        raise ValueError(
            f"merge decision {decision_id} is missing merge_side_effects; "
            "cannot safely reverse alias/evidence/domain state"
        )
    _assert_unmerge_not_blocked_by_alias_remove(decisions, original)

    side_effects = original.merge_side_effects
    source_node_id = original.subject_node_id
    target_node_id = original.target_node_id

    unmerge = build_identity_decision_record(
        world_id=world_id,
        decision_kind="unmerge",
        actor=actor,
        reason=reason,
        subject_node_id=source_node_id,
        target_node_id=target_node_id,
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
            redirect.from_node_id == source_node_id
            and redirect.to_node_id == target_node_id
            and redirect.status == "active"
        ):
            redirects.append(redirect.model_copy(update={"status": "retracted"}))
        else:
            redirects.append(redirect)

    nodes = dict(store.nodes)
    source = nodes.get(source_node_id)
    if source is not None:
        restored_state = dict(source.state)
        restored_state["memory_state"] = "graph_read_model"
        restored_state["identity_canon_state"] = "canonical"
        restored_state.pop("merged_into", None)
        restored_state["last_identity_decision_id"] = unmerge.decision_id
        restored_state["unmerged_by_decision_id"] = unmerge.decision_id
        nodes[source_node_id] = source.model_copy(update={"state": restored_state})

    target = nodes.get(target_node_id)
    if target is not None:
        nodes[target_node_id] = target.model_copy(
            update={
                "aliases": _remove_items(
                    list(target.aliases), side_effects.aliases_added_to_target
                ),
                "evidence_ref_ids": _remove_items(
                    list(target.evidence_ref_ids),
                    side_effects.evidence_ref_ids_added_to_target,
                ),
                "source_domains": _remove_items(
                    list(target.source_domains),
                    side_effects.source_domains_added_to_target,
                ),
                "state": {
                    **dict(target.state),
                    "last_identity_decision_id": unmerge.decision_id,
                },
            }
        )

    alias_map = dict(store.aliases)
    for rewrite in side_effects.alias_map_rewrites:
        if rewrite.prior_owner_node_id is None:
            # Created by merge — restore to the unmerged source identity.
            alias_map[rewrite.alias_key] = source_node_id
        else:
            alias_map[rewrite.alias_key] = rewrite.prior_owner_node_id

    # Ensure restored source surface terms resolve to the source again.
    if source is not None:
        for term in [source.label, *source.aliases]:
            if term.strip():
                alias_map[term.casefold()] = source_node_id

    updated = store.model_copy(
        update={
            "nodes": nodes,
            "aliases": alias_map,
            "identity_redirects": redirects,
        }
    )
    updated = _replace_decisions(updated, updated_decisions)

    # Sanity: source should no longer be in the active redirect map.
    active = active_identity_redirect_map(updated.identity_redirects)
    if source_node_id in active:
        raise RuntimeError(
            f"unmerge failed to clear active redirect for {source_node_id}"
        )
    return updated, unmerge


# Document schema marker for future serializers / rebuild tooling.
IDENTITY_DECISION_SCHEMA = _IDENTITY_DECISION_SCHEMA
