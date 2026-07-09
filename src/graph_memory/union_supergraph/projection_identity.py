"""Durable union identity reconciliation helpers for graph projection."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.union_supergraph.model import (
    UnionIdentityRedirect,
    UnionSupergraphEdge,
    UnionSupergraphMergeRecord,
    UnionSupergraphNode,
    UnionSupergraphStore,
)
from graph_memory.union_supergraph.redirects import (
    active_identity_redirect_map,
    redirect_chain,
    resolve_union_node_id,
)

_DMB_NODE_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(dmb-node:([^)]+)\)")
_MERGED_AWAY_MEMORY_STATE = "merged_away"
_REWIRED_FROM_MEMORY_STATE = "rewired_from_merged_away"


class UnionProjectionIdentityDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    count: int | None = None
    severity: Literal["info", "warning", "error"] = "info"


@dataclass(frozen=True)
class UnionProjectionIdentityContext:
    redirects_by_from: Mapping[str, UnionIdentityRedirect]
    merge_records_by_survivor: Mapping[str, tuple[UnionSupergraphMergeRecord, ...]]
    merged_away_to_survivor: Mapping[str, str]
    applied_assertion_ids: frozenset[str]
    diagnostics: tuple[UnionProjectionIdentityDiagnostic, ...] = field(default_factory=tuple)


def build_union_projection_identity_context(
    store: UnionSupergraphStore,
) -> UnionProjectionIdentityContext:
    """Build projection identity context from durable union store reconciliation state."""
    redirects_by_from = active_identity_redirect_map(store.identity_redirects)
    merge_records_by_survivor: dict[str, list[UnionSupergraphMergeRecord]] = defaultdict(list)
    applied_assertion_ids: set[str] = set()
    merged_away_to_survivor: dict[str, str] = {}

    for record in store.identity_merge_records:
        if record.status != "applied":
            continue
        applied_assertion_ids.add(record.assertion_id)
        merge_records_by_survivor[record.survivor_node_id].append(record)

    for record in store.identity_merge_records:
        if record.status != "applied":
            continue
        survivor_id = record.survivor_node_id
        merged_away_to_survivor.pop(survivor_id, None)
        for merged_away_id in record.merged_away_node_ids:
            if merged_away_id == survivor_id:
                continue
            merged_away_to_survivor[merged_away_id] = survivor_id
        for original_ref_id in record.merged_away_original_refs:
            if original_ref_id == survivor_id:
                continue
            merged_away_to_survivor.setdefault(original_ref_id, survivor_id)

    for from_node_id, redirect in redirects_by_from.items():
        merged_away_to_survivor.setdefault(from_node_id, redirect.to_node_id)

    diagnostics: list[UnionProjectionIdentityDiagnostic] = []
    if redirects_by_from:
        diagnostics.append(
            UnionProjectionIdentityDiagnostic(
                code="union_identity_redirect_applied",
                message=(
                    f"Resolved union node ids through {len(redirects_by_from)} "
                    "active identity redirect(s)"
                ),
                count=len(redirects_by_from),
            )
        )

    for from_node_id in redirects_by_from:
        chain = redirect_chain(from_node_id, redirects_by_from)
        if len(chain) >= 2 and chain[-1] in chain[:-1]:
            diagnostics.append(
                UnionProjectionIdentityDiagnostic(
                    code="union_identity_redirect_cycle_detected",
                    message=f"Active identity redirect cycle detected: {' -> '.join(chain)}",
                    severity="warning",
                )
            )
            break

    for redirect in redirects_by_from.values():
        if redirect.to_node_id not in store.nodes:
            diagnostics.append(
                UnionProjectionIdentityDiagnostic(
                    code="union_identity_redirect_missing_survivor",
                    message=(
                        f"Active redirect {redirect.redirect_id} targets missing survivor "
                        f"{redirect.to_node_id}"
                    ),
                    severity="warning",
                )
            )

    return UnionProjectionIdentityContext(
        redirects_by_from=redirects_by_from,
        merge_records_by_survivor={
            survivor_id: tuple(records)
            for survivor_id, records in merge_records_by_survivor.items()
        },
        merged_away_to_survivor=merged_away_to_survivor,
        applied_assertion_ids=frozenset(applied_assertion_ids),
        diagnostics=tuple(diagnostics),
    )


def resolve_projected_node_id(
    node_id: str,
    context: UnionProjectionIdentityContext,
) -> str:
    """Resolve a union node id to its canonical survivor id for projection."""
    return resolve_union_node_id(node_id, context.redirects_by_from)


def _node_memory_state(node: UnionSupergraphNode) -> str | None:
    memory_state = node.state.get("memory_state")
    return memory_state if isinstance(memory_state, str) else None


def _edge_memory_state(edge: UnionSupergraphEdge) -> str | None:
    memory_state = edge.state.get("memory_state")
    return memory_state if isinstance(memory_state, str) else None


def is_projectable_union_node(
    node: UnionSupergraphNode,
    context: UnionProjectionIdentityContext,
) -> bool:
    """Return whether a union node should appear as a normal active projection node."""
    if _node_memory_state(node) == _MERGED_AWAY_MEMORY_STATE:
        return False
    if node.node_id in context.merged_away_to_survivor:
        survivor_id = context.merged_away_to_survivor[node.node_id]
        if survivor_id != node.node_id:
            return False
    return True


def is_projectable_union_edge(
    edge: UnionSupergraphEdge,
    context: UnionProjectionIdentityContext,
) -> bool:
    """Return whether a union edge should appear as a normal active projection edge."""
    _ = context
    return _edge_memory_state(edge) != _REWIRED_FROM_MEMORY_STATE


def projectable_node_ids(
    store: UnionSupergraphStore,
    context: UnionProjectionIdentityContext,
) -> list[str]:
    return sorted(
        node_id
        for node_id, node in store.nodes.items()
        if is_projectable_union_node(node, context)
    )


def survivor_identity_provenance(
    node_id: str,
    context: UnionProjectionIdentityContext,
) -> dict[str, Any]:
    """Collect durable merge provenance fields for a survivor node view."""
    records = context.merge_records_by_survivor.get(node_id, ())
    if not records:
        return {}

    merged_away_ids: list[str] = []
    merge_assertion_ids: list[str] = []
    redirect_ids: list[str] = []
    merge_record_ids: list[str] = []

    for record in records:
        merge_record_ids.append(record.merge_record_id)
        merge_assertion_ids.append(record.assertion_id)
        redirect_ids.extend(record.redirect_ids)
        for merged_away_id in record.merged_away_node_ids:
            if merged_away_id not in merged_away_ids:
                merged_away_ids.append(merged_away_id)
        for original_ref_id in record.merged_away_original_refs:
            if original_ref_id not in merged_away_ids:
                merged_away_ids.append(original_ref_id)

    return {
        "identity_merge_record_ids": merge_record_ids,
        "merge_assertion_ids": merge_assertion_ids,
        "identity_redirect_ids": redirect_ids,
        "merged_away_ids": merged_away_ids,
    }


def resolve_projection_markdown_dmb_node_links(
    markdown: str,
    context: UnionProjectionIdentityContext,
) -> tuple[str, int]:
    """Rewrite dmb-node link targets in projection markdown through durable redirects."""
    if not markdown or not context.redirects_by_from:
        return markdown, 0

    resolved_count = 0

    def replace_node_id(match: re.Match[str]) -> str:
        nonlocal resolved_count
        label = match.group(1)
        node_id = match.group(2)
        redirected = resolve_projected_node_id(node_id, context)
        if redirected == node_id:
            return match.group(0)
        resolved_count += 1
        return f"[{label}](dmb-node:{redirected})"

    return _DMB_NODE_LINK_PATTERN.sub(replace_node_id, markdown), resolved_count


def append_identity_projection_diagnostics(
    diagnostics: list[UnionProjectionIdentityDiagnostic],
    *,
    merged_away_nodes_filtered: int = 0,
    rewired_edges_filtered: int = 0,
    edge_endpoints_resolved: int = 0,
    mention_targets_resolved: int = 0,
) -> None:
    if merged_away_nodes_filtered:
        diagnostics.append(
            UnionProjectionIdentityDiagnostic(
                code="union_identity_merged_away_node_filtered",
                message=(
                    f"Filtered {merged_away_nodes_filtered} merged-away node(s) from "
                    "normal active projection output"
                ),
                count=merged_away_nodes_filtered,
            )
        )
    if rewired_edges_filtered:
        diagnostics.append(
            UnionProjectionIdentityDiagnostic(
                code="union_identity_rewired_edge_filtered",
                message=(
                    f"Filtered {rewired_edges_filtered} rewired-from edge(s) from "
                    "normal active projection output"
                ),
                count=rewired_edges_filtered,
            )
        )
    if edge_endpoints_resolved:
        diagnostics.append(
            UnionProjectionIdentityDiagnostic(
                code="union_identity_edge_endpoint_resolved",
                message=(
                    f"Resolved {edge_endpoints_resolved} projected edge endpoint(s) "
                    "through active identity redirects"
                ),
                count=edge_endpoints_resolved,
            )
        )
    if mention_targets_resolved:
        diagnostics.append(
            UnionProjectionIdentityDiagnostic(
                code="union_identity_mention_target_resolved",
                message=(
                    f"Resolved {mention_targets_resolved} mention target(s) through "
                    "active identity redirects"
                ),
                count=mention_targets_resolved,
            )
        )
