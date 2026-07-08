from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphMergeObjectsAssertion,
    AuthoredGraphObjectRef,
    AuthoredGraphOverlay,
)
from graph_memory.union_supergraph.model import (
    UnionIdentityRedirect,
    UnionSupergraphStore,
)
from graph_memory.union_supergraph.redirects import (
    active_identity_redirect_map,
    resolve_union_node_id,
)

DiagnosticSeverity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class ReconciliationDiagnostic:
    severity: DiagnosticSeverity
    code: str
    message: str
    assertion_id: str | None = None
    node_id: str | None = None


@dataclass(frozen=True)
class EdgeRewirePlan:
    edge_id: str
    original_source_node_id: str
    original_target_node_id: str
    planned_source_node_id: str
    planned_target_node_id: str
    predicate: str
    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class SurvivorHydrationPlan:
    survivor_node_id: str
    create_survivor_if_missing: bool
    source_node_ids: tuple[str, ...]
    aliases_to_add: tuple[str, ...]
    evidence_ref_ids_to_add: tuple[str, ...]
    source_domains_to_add: tuple[str, ...]
    summary_source_node_id: str | None = None


@dataclass(frozen=True)
class MergeAssertionPlan:
    assertion_id: str
    survivor_node_id: str
    merged_away_original_refs: tuple[str, ...]
    merged_away_node_ids: tuple[str, ...]
    redirects: tuple[UnionIdentityRedirect, ...]
    aliases_to_union: tuple[str, ...]
    evidence_ref_ids_to_union: tuple[str, ...]
    edges_to_rewire: tuple[EdgeRewirePlan, ...]
    survivor_hydration: SurvivorHydrationPlan | None


@dataclass(frozen=True)
class UnionSupergraphMergePlan:
    campaign_id: str
    materialization_pass_id: str
    plans: tuple[MergeAssertionPlan, ...]
    diagnostics: tuple[ReconciliationDiagnostic, ...]


def make_identity_redirect_id(assertion_id: str, from_node_id: str) -> str:
    digest = hashlib.sha256(f"{assertion_id}:{from_node_id}".encode("utf-8")).hexdigest()[
        :16
    ]
    return f"redirect:{digest}"


def node_id_from_object_ref(ref: AuthoredGraphObjectRef) -> str | None:
    if ref.ref_kind == "existing_graph_node":
        return ref.node_id
    if ref.ref_kind == "local_proposal":
        return ref.local_proposal_id
    if ref.ref_kind == "authored_node":
        return ref.authored_node_id
    return None


def _dedupe_preserve_order(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _normalize_label(value: str) -> str:
    return " ".join(value.split()).casefold()


def _label_match_node_ids(
    ref_label: str,
    union_store: UnionSupergraphStore,
    *,
    exclude_node_id: str | None = None,
) -> tuple[str, ...]:
    normalized_ref_label = _normalize_label(ref_label)
    matches: list[str] = []
    for node_id, node in union_store.nodes.items():
        if exclude_node_id is not None and node_id == exclude_node_id:
            continue
        node_labels = {
            _normalize_label(node.label),
            *(_normalize_label(alias) for alias in node.aliases),
        }
        if normalized_ref_label in node_labels:
            matches.append(node_id)
    return _dedupe_preserve_order(matches)


def _resolve_merged_away_node_ids(
    ref: AuthoredGraphObjectRef,
    union_store: UnionSupergraphStore,
    *,
    assertion_id: str,
) -> tuple[tuple[str, ...], list[ReconciliationDiagnostic]]:
    original_ref_id = node_id_from_object_ref(ref)
    if not original_ref_id:
        return (), []

    if original_ref_id in union_store.nodes:
        return (original_ref_id,), []

    label_matches = _label_match_node_ids(
        ref.label,
        union_store,
        exclude_node_id=original_ref_id,
    )
    if len(label_matches) == 1:
        matched_node_id = label_matches[0]
        return (
            (original_ref_id, matched_node_id),
            [
                ReconciliationDiagnostic(
                    severity="warning",
                    code="merge_merged_ref_resolved_by_label",
                    message=(
                        f"Merged-away ref {original_ref_id} is missing from union store; "
                        f"resolved by exact label match to {matched_node_id}"
                    ),
                    assertion_id=assertion_id,
                    node_id=original_ref_id,
                )
            ],
        )

    diagnostics: list[ReconciliationDiagnostic] = []
    if len(label_matches) > 1:
        matched_ids = ", ".join(label_matches)
        diagnostics.append(
            ReconciliationDiagnostic(
                severity="warning",
                code="merge_merged_ref_ambiguous",
                message=(
                    f"Merged-away ref {original_ref_id} is missing from union store and "
                    f"label {ref.label!r} matches multiple nodes ({matched_ids}); "
                    "planning original ref only"
                ),
                assertion_id=assertion_id,
                node_id=original_ref_id,
            )
        )

    return (original_ref_id,), diagnostics


def _collect_node_material(
    node_ids: Sequence[str],
    union_store: UnionSupergraphStore,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    aliases: list[str] = []
    evidence_ref_ids: list[str] = []
    source_domains: list[str] = []
    present_node_ids: list[str] = []

    for node_id in node_ids:
        node = union_store.nodes.get(node_id)
        if node is None:
            continue
        present_node_ids.append(node_id)
        aliases.append(node.label)
        aliases.extend(node.aliases)
        evidence_ref_ids.extend(node.evidence_ref_ids)
        source_domains.extend(node.source_domains)

    return (
        _dedupe_preserve_order(present_node_ids),
        _dedupe_preserve_order(aliases),
        _dedupe_preserve_order(evidence_ref_ids),
        _dedupe_preserve_order(source_domains),
    )


def _choose_summary_source_node_id(
    present_node_ids: Sequence[str],
    union_store: UnionSupergraphStore,
) -> str | None:
    if not present_node_ids:
        return None

    def evidence_count(node_id: str) -> int:
        node = union_store.nodes.get(node_id)
        return len(node.evidence_ref_ids) if node is not None else 0

    return max(present_node_ids, key=lambda node_id: (evidence_count(node_id), node_id))


def _plan_edge_rewires(
    *,
    survivor_node_id: str,
    merged_away_node_ids: Sequence[str],
    union_store: UnionSupergraphStore,
) -> tuple[EdgeRewirePlan, ...]:
    merged_away_set = set(merged_away_node_ids)
    rewires: list[EdgeRewirePlan] = []

    for edge in union_store.edges.values():
        touches_merged_away = (
            edge.source_node_id in merged_away_set or edge.target_node_id in merged_away_set
        )
        if not touches_merged_away:
            continue

        planned_source = (
            survivor_node_id
            if edge.source_node_id in merged_away_set
            else edge.source_node_id
        )
        planned_target = (
            survivor_node_id
            if edge.target_node_id in merged_away_set
            else edge.target_node_id
        )
        if (
            planned_source == edge.source_node_id
            and planned_target == edge.target_node_id
        ):
            continue

        rewires.append(
            EdgeRewirePlan(
                edge_id=edge.edge_id,
                original_source_node_id=edge.source_node_id,
                original_target_node_id=edge.target_node_id,
                planned_source_node_id=planned_source,
                planned_target_node_id=planned_target,
                predicate=edge.predicate,
                evidence_ref_ids=tuple(edge.evidence_ref_ids),
            )
        )

    return tuple(rewires)


def _append_diagnostic(
    diagnostics: list[ReconciliationDiagnostic],
    *,
    severity: DiagnosticSeverity,
    code: str,
    message: str,
    assertion_id: str | None = None,
    node_id: str | None = None,
) -> None:
    diagnostics.append(
        ReconciliationDiagnostic(
            severity=severity,
            code=code,
            message=message,
            assertion_id=assertion_id,
            node_id=node_id,
        )
    )


def _plan_merge_assertion(
    assertion: AuthoredGraphMergeObjectsAssertion,
    *,
    campaign_id: str,
    union_store: UnionSupergraphStore,
    materialization_pass_id: str,
    active_redirects: dict[str, UnionIdentityRedirect],
) -> tuple[MergeAssertionPlan | None, list[ReconciliationDiagnostic]]:
    diagnostics: list[ReconciliationDiagnostic] = []

    if assertion.campaign_id != campaign_id:
        _append_diagnostic(
            diagnostics,
            severity="error",
            code="merge_assertion_wrong_campaign",
            message=(
                f"Skipping merge assertion {assertion.assertion_id}: campaign "
                f"{assertion.campaign_id!r} does not match planner campaign {campaign_id!r}"
            ),
            assertion_id=assertion.assertion_id,
        )
        return None, diagnostics

    if assertion.status != "authored":
        _append_diagnostic(
            diagnostics,
            severity="info",
            code="merge_assertion_inactive",
            message=(
                f"Skipping merge assertion {assertion.assertion_id}: status is "
                f"{assertion.status!r}"
            ),
            assertion_id=assertion.assertion_id,
        )
        return None, diagnostics

    survivor_node_id = node_id_from_object_ref(assertion.survivor_object_ref)
    if not survivor_node_id:
        _append_diagnostic(
            diagnostics,
            severity="error",
            code="merge_assertion_missing_survivor",
            message=(
                f"Skipping merge assertion {assertion.assertion_id}: survivor ref has no node id"
            ),
            assertion_id=assertion.assertion_id,
        )
        return None, diagnostics

    if not assertion.merged_object_refs:
        _append_diagnostic(
            diagnostics,
            severity="error",
            code="merge_assertion_empty_merged_refs",
            message=(
                f"Skipping merge assertion {assertion.assertion_id}: no merged_object_refs"
            ),
            assertion_id=assertion.assertion_id,
        )
        return None, diagnostics

    merged_away_original_refs = _dedupe_preserve_order(
        node_id
        for ref in assertion.merged_object_refs
        if (node_id := node_id_from_object_ref(ref)) is not None
    )
    if not merged_away_original_refs:
        _append_diagnostic(
            diagnostics,
            severity="error",
            code="merge_assertion_empty_merged_refs",
            message=(
                f"Skipping merge assertion {assertion.assertion_id}: merged refs lack node ids"
            ),
            assertion_id=assertion.assertion_id,
        )
        return None, diagnostics

    merged_away_node_id_parts: list[str] = []
    for ref in assertion.merged_object_refs:
        resolved_ids, resolution_diagnostics = _resolve_merged_away_node_ids(
            ref,
            union_store,
            assertion_id=assertion.assertion_id,
        )
        diagnostics.extend(resolution_diagnostics)
        merged_away_node_id_parts.extend(resolved_ids)
    merged_away_node_ids = _dedupe_preserve_order(merged_away_node_id_parts)
    if survivor_node_id in merged_away_node_ids:
        _append_diagnostic(
            diagnostics,
            severity="error",
            code="merge_assertion_self_merge",
            message=(
                f"Skipping merge assertion {assertion.assertion_id}: survivor "
                f"{survivor_node_id} is also listed as merged-away"
            ),
            assertion_id=assertion.assertion_id,
            node_id=survivor_node_id,
        )
        return None, diagnostics

    resolved_survivor_id = resolve_union_node_id(
        survivor_node_id,
        active_redirects,
    )
    if resolved_survivor_id != survivor_node_id:
        _append_diagnostic(
            diagnostics,
            severity="warning",
            code="merge_transitive_survivor_redirect",
            message=(
                f"Survivor {survivor_node_id} already redirects to "
                f"{resolved_survivor_id}; planning uses GM-chosen survivor id"
            ),
            assertion_id=assertion.assertion_id,
            node_id=survivor_node_id,
        )

    redirects: list[UnionIdentityRedirect] = []
    for merged_away_id in merged_away_node_ids:
        existing = active_redirects.get(merged_away_id)
        if existing is not None:
            if existing.to_node_id == survivor_node_id:
                _append_diagnostic(
                    diagnostics,
                    severity="info",
                    code="merge_redirect_already_materialized",
                    message=(
                        f"Active redirect already maps {merged_away_id} to survivor "
                        f"{survivor_node_id}; skipping duplicate redirect proposal"
                    ),
                    assertion_id=assertion.assertion_id,
                    node_id=merged_away_id,
                )
                continue
            _append_diagnostic(
                diagnostics,
                severity="error",
                code="merge_redirect_conflict",
                message=(
                    f"Skipping merge assertion {assertion.assertion_id}: active redirect "
                    f"maps {merged_away_id} to {existing.to_node_id}, not survivor "
                    f"{survivor_node_id}"
                ),
                assertion_id=assertion.assertion_id,
                node_id=merged_away_id,
            )
            return None, diagnostics

        redirects.append(
            UnionIdentityRedirect(
                redirect_id=make_identity_redirect_id(assertion.assertion_id, merged_away_id),
                campaign_id=assertion.campaign_id,
                from_node_id=merged_away_id,
                to_node_id=survivor_node_id,
                assertion_id=assertion.assertion_id,
                event_id=None,
                merge_reason=assertion.merge_reason,
                created_at=assertion.provenance.created_at,
                status="active",
                materialization_pass_id=materialization_pass_id,
            )
        )

    for original_ref_id in merged_away_original_refs:
        if original_ref_id not in union_store.nodes:
            _append_diagnostic(
                diagnostics,
                severity="warning",
                code="merge_merged_node_missing",
                message=(
                    f"Merged-away node {original_ref_id} is not present in union store; "
                    "redirect will still be planned"
                ),
                assertion_id=assertion.assertion_id,
                node_id=original_ref_id,
            )

    survivor_missing = survivor_node_id not in union_store.nodes
    if survivor_missing:
        _append_diagnostic(
            diagnostics,
            severity="warning",
            code="merge_survivor_node_missing",
            message=(
                f"Survivor node {survivor_node_id} is not present in union store; "
                "hydration will create or enrich it during apply"
            ),
            assertion_id=assertion.assertion_id,
            node_id=survivor_node_id,
        )

    present_source_ids, aliases_to_union, evidence_to_union, source_domains = _collect_node_material(
        merged_away_node_ids,
        union_store,
    )
    edges_to_rewire = _plan_edge_rewires(
        survivor_node_id=survivor_node_id,
        merged_away_node_ids=merged_away_node_ids,
        union_store=union_store,
    )

    survivor_hydration = SurvivorHydrationPlan(
        survivor_node_id=survivor_node_id,
        create_survivor_if_missing=survivor_missing,
        source_node_ids=present_source_ids,
        aliases_to_add=aliases_to_union,
        evidence_ref_ids_to_add=evidence_to_union,
        source_domains_to_add=source_domains,
        summary_source_node_id=_choose_summary_source_node_id(
            present_source_ids,
            union_store,
        ),
    )

    _append_diagnostic(
        diagnostics,
        severity="info",
        code="merge_plan_created",
        message=(
            f"Planned merge reconciliation for assertion {assertion.assertion_id}: "
            f"{len(redirects)} redirect(s), {len(edges_to_rewire)} edge rewire(s)"
        ),
        assertion_id=assertion.assertion_id,
    )

    return (
        MergeAssertionPlan(
            assertion_id=assertion.assertion_id,
            survivor_node_id=survivor_node_id,
            merged_away_original_refs=merged_away_original_refs,
            merged_away_node_ids=merged_away_node_ids,
            redirects=tuple(redirects),
            aliases_to_union=aliases_to_union,
            evidence_ref_ids_to_union=evidence_to_union,
            edges_to_rewire=edges_to_rewire,
            survivor_hydration=survivor_hydration,
        ),
        diagnostics,
    )


def plan_authored_merge_reconciliation(
    *,
    campaign_id: str,
    overlay: AuthoredGraphOverlay,
    union_store: UnionSupergraphStore,
    materialization_pass_id: str,
) -> UnionSupergraphMergePlan:
    """Plan union-supergraph merge reconciliation without mutating the store."""
    diagnostics: list[ReconciliationDiagnostic] = []
    plans: list[MergeAssertionPlan] = []
    active_redirects = active_identity_redirect_map(union_store.identity_redirects)

    for assertion in overlay.assertions:
        if not isinstance(assertion, AuthoredGraphMergeObjectsAssertion):
            continue

        plan, assertion_diagnostics = _plan_merge_assertion(
            assertion,
            campaign_id=campaign_id,
            union_store=union_store,
            materialization_pass_id=materialization_pass_id,
            active_redirects=active_redirects,
        )
        diagnostics.extend(assertion_diagnostics)
        if plan is not None:
            plans.append(plan)

    return UnionSupergraphMergePlan(
        campaign_id=campaign_id,
        materialization_pass_id=materialization_pass_id,
        plans=tuple(plans),
        diagnostics=tuple(diagnostics),
    )
