from __future__ import annotations

import hashlib
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from graph_memory.union_supergraph.load import (
    load_union_supergraph_store,
    write_union_supergraph_store,
)
from graph_memory.union_supergraph.merge_reconciliation import (
    EdgeRewirePlan,
    MergeAssertionPlan,
    ReconciliationDiagnostic,
    UnionSupergraphMergePlan,
)
from graph_memory.union_supergraph.model import (
    UnionIdentityRedirect,
    UnionSupergraphAdjacencyItem,
    UnionSupergraphEdge,
    UnionSupergraphMergeRecord,
    UnionSupergraphNode,
    UnionSupergraphStore,
)
from graph_memory.union_supergraph.redirects import active_identity_redirect_map


@dataclass(frozen=True)
class UnionSupergraphApplyResult:
    campaign_id: str
    materialization_pass_id: str
    applied_assertion_ids: tuple[str, ...]
    skipped_assertion_ids: tuple[str, ...]
    redirects_added: int
    merge_records_added: int
    survivor_nodes_created: int
    survivor_nodes_updated: int
    merged_away_nodes_marked: int
    edges_rewired: int
    edges_deduped: int
    diagnostics: tuple[ReconciliationDiagnostic, ...]
    backup_path: str | None = None
    store_path: str | None = None


def make_merge_record_id(assertion_id: str, materialization_pass_id: str) -> str:
    digest = hashlib.sha256(
        f"{assertion_id}:{materialization_pass_id}".encode("utf-8")
    ).hexdigest()[:16]
    return f"merge_record:{digest}"


def _append_diagnostic(
    diagnostics: list[ReconciliationDiagnostic],
    *,
    severity: str,
    code: str,
    message: str,
    assertion_id: str | None = None,
    node_id: str | None = None,
) -> None:
    diagnostics.append(
        ReconciliationDiagnostic(
            severity=severity,  # type: ignore[arg-type]
            code=code,
            message=message,
            assertion_id=assertion_id,
            node_id=node_id,
        )
    )


def _dedupe_extend(existing: list[str], additions: Iterable[str]) -> list[str]:
    seen = set(existing)
    merged = list(existing)
    for item in additions:
        if item in seen:
            continue
        seen.add(item)
        merged.append(item)
    return merged


def _derive_survivor_label(survivor_node_id: str, aliases: Sequence[str]) -> str:
    for alias in aliases:
        trimmed = alias.strip()
        if trimmed:
            return trimmed
    slug = survivor_node_id.split(":", 1)[-1]
    return slug.replace("_", " ").strip() or survivor_node_id


def _best_kind_role(
    source_node_ids: Sequence[str],
    nodes: dict[str, UnionSupergraphNode],
) -> tuple[str, str]:
    for node_id in source_node_ids:
        node = nodes.get(node_id)
        if node is None:
            continue
        kind = node.kind.strip() if node.kind else ""
        role = node.role.strip() if node.role else ""
        if kind and role:
            return kind, role
        if kind:
            return kind, role or kind
    return "unknown", "unknown"


def _is_projectable_edge(edge: UnionSupergraphEdge) -> bool:
    return edge.state.get("memory_state") != "rewired_from_merged_away"


def _find_equivalent_edge(
    edges: dict[str, UnionSupergraphEdge],
    *,
    source_node_id: str,
    target_node_id: str,
    predicate: str,
    direction: str,
) -> UnionSupergraphEdge | None:
    for edge in edges.values():
        if not _is_projectable_edge(edge):
            continue
        if (
            edge.source_node_id == source_node_id
            and edge.target_node_id == target_node_id
            and edge.predicate == predicate
            and edge.direction == direction
        ):
            return edge
    return None


def _make_rewired_edge_id(rewire: EdgeRewirePlan) -> str:
    return (
        f"edge:{rewire.planned_source_node_id}:{rewire.predicate}:"
        f"{rewire.planned_target_node_id}:merged_from:{rewire.edge_id}"
    )


def _rebuild_adjacency(store: UnionSupergraphStore) -> dict[str, list[UnionSupergraphAdjacencyItem]]:
    adjacency: dict[str, list[UnionSupergraphAdjacencyItem]] = {}
    focus_session_id = store.focus_session_id

    for edge in store.edges.values():
        if not _is_projectable_edge(edge):
            continue
        anchored = focus_session_id in set(edge.session_ids)
        adjacency.setdefault(edge.source_node_id, []).append(
            UnionSupergraphAdjacencyItem(
                edge_id=edge.edge_id,
                node_id=edge.target_node_id,
                label=edge.label,
                direction="outbound",
                anchored_to_focus_session=anchored,
            )
        )
        adjacency.setdefault(edge.target_node_id, []).append(
            UnionSupergraphAdjacencyItem(
                edge_id=edge.edge_id,
                node_id=edge.source_node_id,
                label=edge.label,
                direction="inbound",
                anchored_to_focus_session=anchored,
            )
        )

    return adjacency


def _applied_assertion_ids(store: UnionSupergraphStore) -> set[str]:
    return {
        record.assertion_id
        for record in store.identity_merge_records
        if record.status == "applied"
    }


def _resolve_redirects_for_assertion(
    assertion_plan: MergeAssertionPlan,
    active_redirects: dict[str, UnionIdentityRedirect],
    diagnostics: list[ReconciliationDiagnostic],
) -> list[UnionIdentityRedirect] | None:
    """Pre-validate all redirects for an assertion before any store mutation."""
    redirects_to_add: list[UnionIdentityRedirect] = []
    for redirect in assertion_plan.redirects:
        existing = active_redirects.get(redirect.from_node_id)
        if existing is not None:
            if existing.to_node_id == redirect.to_node_id:
                _append_diagnostic(
                    diagnostics,
                    severity="info",
                    code="merge_apply_redirect_already_exists",
                    message=(
                        f"Active redirect already maps {redirect.from_node_id} to "
                        f"{redirect.to_node_id}; skipping duplicate redirect append"
                    ),
                    assertion_id=assertion_plan.assertion_id,
                    node_id=redirect.from_node_id,
                )
                continue
            _append_diagnostic(
                diagnostics,
                severity="error",
                code="merge_apply_redirect_conflict",
                message=(
                    f"Skipping assertion {assertion_plan.assertion_id}: active redirect "
                    f"maps {redirect.from_node_id} to {existing.to_node_id}, not "
                    f"{redirect.to_node_id}"
                ),
                assertion_id=assertion_plan.assertion_id,
                node_id=redirect.from_node_id,
            )
            return None
        redirects_to_add.append(redirect)
    return redirects_to_add


def _apply_assertion_plan(
    store: UnionSupergraphStore,
    assertion_plan: MergeAssertionPlan,
    *,
    applied_at: str,
    materialization_pass_id: str,
    diagnostics: list[ReconciliationDiagnostic],
) -> dict[str, int] | None:
    counts = {
        "redirects_added": 0,
        "survivor_nodes_created": 0,
        "survivor_nodes_updated": 0,
        "merged_away_nodes_marked": 0,
        "edges_rewired": 0,
        "edges_deduped": 0,
    }

    if assertion_plan.assertion_id in _applied_assertion_ids(store):
        _append_diagnostic(
            diagnostics,
            severity="info",
            code="merge_assertion_already_applied",
            message=(
                f"Skipping assertion {assertion_plan.assertion_id}: merge record already applied"
            ),
            assertion_id=assertion_plan.assertion_id,
        )
        return None

    active_redirects = active_identity_redirect_map(store.identity_redirects)
    redirects_to_add = _resolve_redirects_for_assertion(
        assertion_plan,
        active_redirects,
        diagnostics,
    )
    if redirects_to_add is None:
        return None

    store.identity_redirects.extend(redirects_to_add)
    counts["redirects_added"] = len(redirects_to_add)
    for redirect in redirects_to_add:
        active_redirects[redirect.from_node_id] = redirect

    hydration = assertion_plan.survivor_hydration
    survivor_node_id = assertion_plan.survivor_node_id
    aliases_to_add = list(assertion_plan.aliases_to_union)
    evidence_to_add = list(assertion_plan.evidence_ref_ids_to_union)
    domains_to_add = list(hydration.source_domains_to_add if hydration else ())

    existing_survivor = store.nodes.get(survivor_node_id)
    if existing_survivor is None:
        kind, role = _best_kind_role(
            hydration.source_node_ids if hydration else (),
            store.nodes,
        )
        store.nodes[survivor_node_id] = UnionSupergraphNode(
            node_id=survivor_node_id,
            label=_derive_survivor_label(survivor_node_id, aliases_to_add),
            kind=kind,
            role=role,
            aliases=aliases_to_add,
            source_domains=domains_to_add or ["recap"],
            evidence_ref_ids=evidence_to_add,
            state={
                "memory_state": "graph_read_model",
                "identity_state": "survivor",
                "created_by_reconciliation": True,
                "merge_assertion_id": assertion_plan.assertion_id,
                "materialization_pass_id": materialization_pass_id,
            },
        )
        counts["survivor_nodes_created"] = 1
        _append_diagnostic(
            diagnostics,
            severity="info",
            code="merge_apply_survivor_created",
            message=f"Created survivor node {survivor_node_id}",
            assertion_id=assertion_plan.assertion_id,
            node_id=survivor_node_id,
        )
    else:
        updated_state = dict(existing_survivor.state)
        updated_state.setdefault("memory_state", "graph_read_model")
        updated_state["identity_state"] = "survivor"
        updated_state["merge_assertion_id"] = assertion_plan.assertion_id
        updated_state["materialization_pass_id"] = materialization_pass_id
        label = existing_survivor.label.strip() or _derive_survivor_label(
            survivor_node_id,
            aliases_to_add,
        )
        store.nodes[survivor_node_id] = existing_survivor.model_copy(
            update={
                "label": label,
                "aliases": _dedupe_extend(existing_survivor.aliases, aliases_to_add),
                "evidence_ref_ids": _dedupe_extend(
                    existing_survivor.evidence_ref_ids,
                    evidence_to_add,
                ),
                "source_domains": _dedupe_extend(
                    existing_survivor.source_domains,
                    domains_to_add,
                ),
                "state": updated_state,
            }
        )
        counts["survivor_nodes_updated"] = 1
        _append_diagnostic(
            diagnostics,
            severity="info",
            code="merge_apply_survivor_updated",
            message=f"Updated survivor node {survivor_node_id}",
            assertion_id=assertion_plan.assertion_id,
            node_id=survivor_node_id,
        )

    for merged_away_id in assertion_plan.merged_away_node_ids:
        merged_node = store.nodes.get(merged_away_id)
        if merged_node is None:
            continue
        updated_state = dict(merged_node.state)
        updated_state["memory_state"] = "merged_away"
        updated_state["merged_into"] = survivor_node_id
        updated_state["merge_assertion_id"] = assertion_plan.assertion_id
        updated_state["materialization_pass_id"] = materialization_pass_id
        store.nodes[merged_away_id] = merged_node.model_copy(update={"state": updated_state})
        counts["merged_away_nodes_marked"] += 1
        _append_diagnostic(
            diagnostics,
            severity="info",
            code="merge_apply_merged_node_marked",
            message=f"Marked merged-away node {merged_away_id}",
            assertion_id=assertion_plan.assertion_id,
            node_id=merged_away_id,
        )

    for rewire in assertion_plan.edges_to_rewire:
        original_edge = store.edges.get(rewire.edge_id)
        if original_edge is None:
            continue

        equivalent = _find_equivalent_edge(
            store.edges,
            source_node_id=rewire.planned_source_node_id,
            target_node_id=rewire.planned_target_node_id,
            predicate=rewire.predicate,
            direction=original_edge.direction,
        )
        if equivalent is not None and equivalent.edge_id != rewire.edge_id:
            rewired_from_edge_ids = list(equivalent.state.get("rewired_from_edge_ids") or [])
            rewired_from_node_ids = list(equivalent.state.get("rewired_from_node_ids") or [])
            if rewire.edge_id not in rewired_from_edge_ids:
                rewired_from_edge_ids.append(rewire.edge_id)
            for node_id in assertion_plan.merged_away_node_ids:
                if node_id not in rewired_from_node_ids:
                    rewired_from_node_ids.append(node_id)

            updated_state = dict(equivalent.state)
            updated_state["rewired_from_edge_ids"] = rewired_from_edge_ids
            updated_state["rewired_from_node_ids"] = rewired_from_node_ids
            updated_state["merge_assertion_id"] = assertion_plan.assertion_id
            store.edges[equivalent.edge_id] = equivalent.model_copy(
                update={
                    "evidence_ref_ids": _dedupe_extend(
                        equivalent.evidence_ref_ids,
                        rewire.evidence_ref_ids,
                    ),
                    "source_domains": _dedupe_extend(
                        equivalent.source_domains,
                        original_edge.source_domains,
                    ),
                    "session_ids": _dedupe_extend(
                        equivalent.session_ids,
                        original_edge.session_ids,
                    ),
                    "state": updated_state,
                }
            )
            counts["edges_deduped"] += 1
            _append_diagnostic(
                diagnostics,
                severity="info",
                code="merge_apply_edge_deduped",
                message=(
                    f"Deduped edge {rewire.edge_id} onto existing edge {equivalent.edge_id}"
                ),
                assertion_id=assertion_plan.assertion_id,
            )
            target_edge_id = equivalent.edge_id
        else:
            new_edge_id = _make_rewired_edge_id(rewire)
            store.edges[new_edge_id] = UnionSupergraphEdge(
                edge_id=new_edge_id,
                source_node_id=rewire.planned_source_node_id,
                target_node_id=rewire.planned_target_node_id,
                predicate=rewire.predicate,
                label=original_edge.label,
                direction=original_edge.direction,
                source_domains=list(original_edge.source_domains),
                session_ids=list(original_edge.session_ids),
                evidence_ref_ids=list(rewire.evidence_ref_ids),
                state={
                    "memory_state": "graph_read_model",
                    "rewired_from_edge_id": rewire.edge_id,
                    "rewired_from_node_ids": list(assertion_plan.merged_away_node_ids),
                    "merge_assertion_id": assertion_plan.assertion_id,
                    "materialization_pass_id": materialization_pass_id,
                },
            )
            counts["edges_rewired"] += 1
            _append_diagnostic(
                diagnostics,
                severity="info",
                code="merge_apply_edge_rewired",
                message=f"Rewired edge {rewire.edge_id} to {new_edge_id}",
                assertion_id=assertion_plan.assertion_id,
            )
            target_edge_id = new_edge_id

        original_state = dict(original_edge.state)
        original_state["memory_state"] = "rewired_from_merged_away"
        original_state["rewired_to_edge_id"] = target_edge_id
        original_state["merge_assertion_id"] = assertion_plan.assertion_id
        original_state["materialization_pass_id"] = materialization_pass_id
        store.edges[rewire.edge_id] = original_edge.model_copy(update={"state": original_state})

    redirect_ids = [
        active_redirects[redirect.from_node_id].redirect_id
        for redirect in assertion_plan.redirects
        if redirect.from_node_id in active_redirects
    ]

    store.identity_merge_records.append(
        UnionSupergraphMergeRecord(
            merge_record_id=make_merge_record_id(
                assertion_plan.assertion_id,
                materialization_pass_id,
            ),
            assertion_id=assertion_plan.assertion_id,
            survivor_node_id=survivor_node_id,
            merged_away_node_ids=list(assertion_plan.merged_away_node_ids),
            merged_away_original_refs=list(assertion_plan.merged_away_original_refs),
            redirect_ids=redirect_ids,
            evidence_ref_ids_unioned=list(assertion_plan.evidence_ref_ids_to_union),
            edges_rewired_count=counts["edges_rewired"],
            edges_deduped_count=counts["edges_deduped"],
            aliases_unioned=list(assertion_plan.aliases_to_union),
            applied_at=applied_at,
            status="applied",
            materialization_pass_id=materialization_pass_id,
        )
    )

    _append_diagnostic(
        diagnostics,
        severity="info",
        code="merge_assertion_applied",
        message=f"Applied merge reconciliation for assertion {assertion_plan.assertion_id}",
        assertion_id=assertion_plan.assertion_id,
    )
    return counts


def apply_union_supergraph_merge_plan(
    *,
    union_store: UnionSupergraphStore,
    plan: UnionSupergraphMergePlan,
    applied_at: str,
) -> tuple[UnionSupergraphStore, UnionSupergraphApplyResult]:
    """Return a new store with merge reconciliation plan applied."""
    if plan.campaign_id != union_store.campaign_id:
        raise ValueError(
            f"plan campaign_id {plan.campaign_id!r} does not match store "
            f"{union_store.campaign_id!r}"
        )

    updated_store = union_store.model_copy(deep=True)
    diagnostics: list[ReconciliationDiagnostic] = []
    applied_assertion_ids: list[str] = []
    skipped_assertion_ids: list[str] = []

    totals = {
        "redirects_added": 0,
        "merge_records_added": 0,
        "survivor_nodes_created": 0,
        "survivor_nodes_updated": 0,
        "merged_away_nodes_marked": 0,
        "edges_rewired": 0,
        "edges_deduped": 0,
    }

    for assertion_plan in plan.plans:
        counts = _apply_assertion_plan(
            updated_store,
            assertion_plan,
            applied_at=applied_at,
            materialization_pass_id=plan.materialization_pass_id,
            diagnostics=diagnostics,
        )
        if counts is None:
            skipped_assertion_ids.append(assertion_plan.assertion_id)
            continue

        applied_assertion_ids.append(assertion_plan.assertion_id)
        totals["merge_records_added"] += 1
        for key, value in counts.items():
            totals[key] += value

    if applied_assertion_ids:
        updated_store.adjacency = _rebuild_adjacency(updated_store)

    result = UnionSupergraphApplyResult(
        campaign_id=plan.campaign_id,
        materialization_pass_id=plan.materialization_pass_id,
        applied_assertion_ids=tuple(applied_assertion_ids),
        skipped_assertion_ids=tuple(skipped_assertion_ids),
        redirects_added=totals["redirects_added"],
        merge_records_added=totals["merge_records_added"],
        survivor_nodes_created=totals["survivor_nodes_created"],
        survivor_nodes_updated=totals["survivor_nodes_updated"],
        merged_away_nodes_marked=totals["merged_away_nodes_marked"],
        edges_rewired=totals["edges_rewired"],
        edges_deduped=totals["edges_deduped"],
        diagnostics=tuple(diagnostics),
    )
    return updated_store, result


def _backup_store_path(
    union_store_path: Path,
    *,
    applied_at: str,
    backup_dir: Path | None,
) -> Path:
    stamp = applied_at.replace(":", "").replace("-", "")
    backup_name = f"{union_store_path.name}.backup.{stamp}.json"
    directory = backup_dir or union_store_path.parent
    directory.mkdir(parents=True, exist_ok=True)
    return directory / backup_name


def apply_union_supergraph_merge_plan_to_file(
    *,
    union_store_path: Path,
    plan: UnionSupergraphMergePlan,
    applied_at: str,
    backup_dir: Path | None = None,
) -> UnionSupergraphApplyResult:
    """Load store, backup original, apply plan, and write updated store."""
    diagnostics: list[ReconciliationDiagnostic] = []
    union_store = load_union_supergraph_store(union_store_path)

    backup_path = _backup_store_path(
        union_store_path,
        applied_at=applied_at,
        backup_dir=backup_dir,
    )
    shutil.copyfile(union_store_path, backup_path)
    _append_diagnostic(
        diagnostics,
        severity="info",
        code="merge_apply_backup_created",
        message=f"Created union store backup at {backup_path}",
    )

    updated_store, result = apply_union_supergraph_merge_plan(
        union_store=union_store,
        plan=plan,
        applied_at=applied_at,
    )

    write_union_supergraph_store(union_store_path, updated_store)
    _append_diagnostic(
        diagnostics,
        severity="info",
        code="merge_apply_store_written",
        message=f"Wrote updated union store to {union_store_path}",
    )

    return UnionSupergraphApplyResult(
        campaign_id=result.campaign_id,
        materialization_pass_id=result.materialization_pass_id,
        applied_assertion_ids=result.applied_assertion_ids,
        skipped_assertion_ids=result.skipped_assertion_ids,
        redirects_added=result.redirects_added,
        merge_records_added=result.merge_records_added,
        survivor_nodes_created=result.survivor_nodes_created,
        survivor_nodes_updated=result.survivor_nodes_updated,
        merged_away_nodes_marked=result.merged_away_nodes_marked,
        edges_rewired=result.edges_rewired,
        edges_deduped=result.edges_deduped,
        diagnostics=result.diagnostics + tuple(diagnostics),
        backup_path=str(backup_path),
        store_path=str(union_store_path),
    )
