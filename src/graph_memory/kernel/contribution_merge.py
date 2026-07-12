"""Merge GraphContributions into proposed world graph revisions (PR005)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contribution_models import (
    ContributionMergeResult,
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.kernel.contributions import (
    _canonicalize_graph_contribution_assertions,
    create_graph_contribution,
)
from graph_memory.kernel.world_graph import (
    WorldGraphNotFoundError,
    WorldGraphValidationError,
    load_current_world_graph,
    open_world_graph_head,
    publish_world_graph_revision,
)
from graph_memory.union_supergraph.model import (
    UnionSupergraphAdjacencyItem,
    UnionSupergraphEdge,
    UnionSupergraphEvidence,
    UnionSupergraphNode,
    UnionSupergraphSourceArtifact,
    UnionSupergraphStore,
)
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
    save_contribution_index,
    upsert_contribution_in_index,
    write_contribution_record,
)


def _support_map(store: UnionSupergraphStore) -> dict[str, DurableAssertionSupport]:
    raw = store.assertion_support or {}
    result: dict[str, DurableAssertionSupport] = {}
    for key, value in raw.items():
        if isinstance(value, DurableAssertionSupport):
            result[key] = value
        elif isinstance(value, dict):
            result[key] = DurableAssertionSupport.model_validate(value)
    return result


def _with_support_map(
    store: UnionSupergraphStore,
    support: dict[str, DurableAssertionSupport],
) -> UnionSupergraphStore:
    return store.model_copy(
        update={
            "assertion_support": {
                key: value.model_dump(mode="json") for key, value in support.items()
            }
        }
    )


def rebuild_adjacency(
    store: UnionSupergraphStore,
) -> dict[str, list[UnionSupergraphAdjacencyItem]]:
    """Rebuild adjacency lists from the current edge map."""
    adjacency: dict[str, list[UnionSupergraphAdjacencyItem]] = {
        node_id: [] for node_id in store.nodes
    }
    focus = store.focus_session_id
    for edge in store.edges.values():
        anchored = focus in (edge.session_ids or [])
        if edge.source_node_id in adjacency:
            adjacency[edge.source_node_id].append(
                UnionSupergraphAdjacencyItem(
                    edge_id=edge.edge_id,
                    node_id=edge.target_node_id,
                    direction="outbound",
                    label=edge.label,
                    anchored_to_focus_session=anchored,
                )
            )
        if edge.target_node_id in adjacency:
            adjacency[edge.target_node_id].append(
                UnionSupergraphAdjacencyItem(
                    edge_id=edge.edge_id,
                    node_id=edge.source_node_id,
                    direction="inbound",
                    label=edge.label,
                    anchored_to_focus_session=anchored,
                )
            )
    return adjacency


def _rebuild_adjacency(
    store: UnionSupergraphStore,
) -> dict[str, list[UnionSupergraphAdjacencyItem]]:
    return rebuild_adjacency(store)


def _ensure_artifact(
    artifacts: dict[str, UnionSupergraphSourceArtifact],
    *,
    artifact_id: str,
    source_domain: str,
    campaign_id: str,
    uri: str | None = None,
    session_id: str | None = None,
) -> None:
    if artifact_id in artifacts:
        return
    payload: dict[str, Any] = {
        "source_artifact_id": artifact_id,
        "source_domain": source_domain,
        "campaign_id": campaign_id,
        "uri": uri or f"contribution://{artifact_id}",
    }
    if session_id:
        payload["session_id"] = session_id
    artifacts[artifact_id] = UnionSupergraphSourceArtifact.model_validate(payload)


def _ensure_evidence(
    evidence: dict[str, UnionSupergraphEvidence],
    artifacts: dict[str, UnionSupergraphSourceArtifact],
    *,
    evidence_ref_id: str,
    source_artifact_id: str,
    source_domain: str,
    campaign_id: str,
    session_id: str | None = None,
    locator: str | None = None,
    source_span_ref_id: str | None = None,
) -> None:
    if evidence_ref_id in evidence:
        return
    _ensure_artifact(
        artifacts,
        artifact_id=source_artifact_id,
        source_domain=source_domain,
        campaign_id=campaign_id,
        session_id=session_id,
    )
    payload: dict[str, Any] = {
        "evidence_ref_id": evidence_ref_id,
        "source_artifact_id": source_artifact_id,
        "source_domain": source_domain,
        "evidence_role": "contribution_support",
        "can_open_source": True,
        "can_highlight_span": bool(source_span_ref_id),
    }
    if session_id:
        payload["session_id"] = session_id
        payload["source_span_ref_id"] = source_span_ref_id or f"span:{evidence_ref_id}"
    else:
        payload["locator"] = locator or f"contribution/{evidence_ref_id}"
    evidence[evidence_ref_id] = UnionSupergraphEvidence.model_validate(payload)


def _add_support(
    support: dict[str, DurableAssertionSupport],
    assertion: GraphContributionAssertion,
    contribution_id: str,
    *,
    graph_object_id: str | None,
) -> None:
    existing = support.get(assertion.assertion_id)
    artifact_ids = [aid for aid in [assertion.source_artifact_id] if aid]
    if existing is None:
        support[assertion.assertion_id] = DurableAssertionSupport(
            assertion_id=assertion.assertion_id,
            active_contribution_ids=[contribution_id],
            evidence_ref_ids=list(assertion.evidence_ref_ids),
            source_artifact_ids=artifact_ids,
            support_state="supported",
            introduced_by_contribution_id=contribution_id,
            assertion_kind=assertion.assertion_kind,
            graph_object_id=graph_object_id,
        )
        return

    active = list(existing.active_contribution_ids)
    if contribution_id not in active:
        active.append(contribution_id)
    evidence = list(existing.evidence_ref_ids)
    for ref in assertion.evidence_ref_ids:
        if ref not in evidence:
            evidence.append(ref)
    sources = list(existing.source_artifact_ids)
    for aid in artifact_ids:
        if aid not in sources:
            sources.append(aid)
    support[assertion.assertion_id] = existing.model_copy(
        update={
            "active_contribution_ids": active,
            "evidence_ref_ids": evidence,
            "source_artifact_ids": sources,
            "support_state": "supported",
            "graph_object_id": existing.graph_object_id or graph_object_id,
        }
    )


def _remove_contribution_support(
    support: dict[str, DurableAssertionSupport],
    contribution_id: str,
    *,
    as_superseded: bool,
) -> list[str]:
    """Remove contribution support; return assertion ids that became unsupported."""
    unsupported: list[str] = []
    for assertion_id, record in list(support.items()):
        if contribution_id not in record.active_contribution_ids:
            continue
        active = [
            cid for cid in record.active_contribution_ids if cid != contribution_id
        ]
        superseded = list(record.superseded_contribution_ids)
        retracted = list(record.retracted_contribution_ids)
        if as_superseded:
            if contribution_id not in superseded:
                superseded.append(contribution_id)
        else:
            if contribution_id not in retracted:
                retracted.append(contribution_id)
        state = (
            "supported" if active else ("unsupported" if as_superseded else "retracted")
        )
        support[assertion_id] = record.model_copy(
            update={
                "active_contribution_ids": active,
                "superseded_contribution_ids": superseded,
                "retracted_contribution_ids": retracted,
                "support_state": state,
            }
        )
        if not active:
            unsupported.append(assertion_id)
    return unsupported


def _mark_graph_objects_unsupported(
    store: UnionSupergraphStore,
    support: dict[str, DurableAssertionSupport],
    unsupported_assertion_ids: list[str],
) -> UnionSupergraphStore:
    nodes = dict(store.nodes)
    edges = dict(store.edges)
    for assertion_id in unsupported_assertion_ids:
        record = support.get(assertion_id)
        if record is None or not record.graph_object_id:
            continue
        object_id = record.graph_object_id
        if object_id in nodes:
            node = nodes[object_id]
            nodes[object_id] = node.model_copy(
                update={
                    "state": {
                        **dict(node.state),
                        "support_state": record.support_state,
                        "memory_state": "unsupported_assertion",
                    }
                }
            )
        if object_id in edges:
            edge = edges[object_id]
            edges[object_id] = edge.model_copy(
                update={
                    "state": {
                        **dict(edge.state),
                        "support_state": record.support_state,
                        "memory_state": "unsupported_assertion",
                    }
                }
            )
    return store.model_copy(update={"nodes": nodes, "edges": edges})


def _apply_node_assertion(
    store: UnionSupergraphStore,
    assertion: GraphContributionAssertion,
    contribution: GraphContribution,
) -> tuple[UnionSupergraphStore, str]:
    value = dict(assertion.value)
    node_id = assertion.subject_node_id or str(value.get("node_id") or "")
    if not node_id:
        raise ValueError(
            f"node assertion {assertion.assertion_id} missing subject_node_id"
        )

    nodes = dict(store.nodes)
    evidence = dict(store.evidence)
    artifacts = dict(store.source_artifacts)
    aliases = dict(store.aliases)

    evidence_ids = list(assertion.evidence_ref_ids)
    for ref_payload in value.get("evidence") or []:
        if not isinstance(ref_payload, dict):
            continue
        ref_id = str(ref_payload.get("evidence_ref_id") or "")
        if not ref_id:
            continue
        _ensure_evidence(
            evidence,
            artifacts,
            evidence_ref_id=ref_id,
            source_artifact_id=str(
                ref_payload.get("source_artifact_id")
                or assertion.source_artifact_id
                or f"artifact:{contribution.contribution_id}"
            ),
            source_domain=str(ref_payload.get("source_domain") or "manual_seed"),
            campaign_id=store.campaign_id,
            session_id=ref_payload.get("session_id"),
            locator=ref_payload.get("locator"),
            source_span_ref_id=ref_payload.get("source_span_ref_id"),
        )
        if ref_id not in evidence_ids:
            evidence_ids.append(ref_id)

    for artifact_payload in value.get("source_artifacts") or []:
        if isinstance(artifact_payload, dict) and artifact_payload.get(
            "source_artifact_id"
        ):
            artifacts[str(artifact_payload["source_artifact_id"])] = (
                UnionSupergraphSourceArtifact.model_validate(artifact_payload)
            )

    if not evidence_ids:
        # Fall back to creating contribution-scoped evidence so validation can pass.
        ref_id = f"evidence:{contribution.contribution_id}:{node_id}"
        artifact_id = (
            assertion.source_artifact_id
            or contribution.source_artifact_id
            or f"artifact:{contribution.contribution_id}"
        )
        _ensure_evidence(
            evidence,
            artifacts,
            evidence_ref_id=ref_id,
            source_artifact_id=artifact_id,
            source_domain=str(value.get("source_domain") or "manual_seed"),
            campaign_id=store.campaign_id,
            locator=f"contribution/{contribution.contribution_id}/{node_id}",
        )
        evidence_ids = [ref_id]

    source_domains = list(value.get("source_domains") or ["manual_seed"])
    label = assertion.label or str(value.get("label") or node_id)
    kind = str(value.get("kind") or "npc")
    role = str(value.get("role") or kind)
    node_aliases = list(value.get("aliases") or ([label] if label else []))

    existing = nodes.get(node_id)
    if existing is None:
        nodes[node_id] = UnionSupergraphNode(
            node_id=node_id,
            label=label,
            kind=kind,
            role=role,
            aliases=node_aliases,
            source_domains=source_domains,
            evidence_ref_ids=evidence_ids,
            state={
                "memory_state": "contribution_accepted",
                "canon_state": value.get("canon_state") or "canonical",
                "approval_state": value.get("approval_state") or "accepted",
                "identity_canon_state": value.get("identity_canon_state")
                or "canonical",
                "epistemic_kind": assertion.epistemic_kind,
                "visibility": assertion.visibility,
                "campaign_scope": assertion.campaign_scope,
                "introduced_by_contribution_id": contribution.contribution_id,
            },
        )
    else:
        merged_aliases = list(existing.aliases)
        for alias in node_aliases:
            if alias not in merged_aliases:
                merged_aliases.append(alias)
        merged_evidence = list(existing.evidence_ref_ids)
        for ref in evidence_ids:
            if ref not in merged_evidence:
                merged_evidence.append(ref)
        merged_domains = list(existing.source_domains)
        for domain in source_domains:
            if domain not in merged_domains:
                merged_domains.append(domain)
        nodes[node_id] = existing.model_copy(
            update={
                "aliases": merged_aliases,
                "evidence_ref_ids": merged_evidence,
                "source_domains": merged_domains,
                "state": {
                    **dict(existing.state),
                    "support_state": "supported",
                    "memory_state": "contribution_accepted",
                },
            }
        )

    for term in [label, *node_aliases]:
        if term and term.strip():
            aliases[term.casefold()] = node_id

    updated = store.model_copy(
        update={
            "nodes": nodes,
            "evidence": evidence,
            "source_artifacts": artifacts,
            "aliases": aliases,
        }
    )
    return updated, node_id


def _apply_edge_assertion(
    store: UnionSupergraphStore,
    assertion: GraphContributionAssertion,
    contribution: GraphContribution,
) -> tuple[UnionSupergraphStore, str]:
    value = dict(assertion.value)
    source_id = assertion.subject_node_id or str(value.get("source_node_id") or "")
    target_id = assertion.target_node_id or str(value.get("target_node_id") or "")
    predicate = assertion.predicate or str(value.get("predicate") or "related_to")
    if not source_id or not target_id:
        raise ValueError(f"edge assertion {assertion.assertion_id} missing endpoints")
    if source_id not in store.nodes or target_id not in store.nodes:
        raise ValueError(
            f"edge assertion {assertion.assertion_id} endpoints must exist before merge"
        )

    edge_id = str(value.get("edge_id") or f"edge:{source_id}:{predicate}:{target_id}")
    evidence = dict(store.evidence)
    artifacts = dict(store.source_artifacts)
    edges = dict(store.edges)

    evidence_ids = list(assertion.evidence_ref_ids)
    for ref_payload in value.get("evidence") or []:
        if not isinstance(ref_payload, dict):
            continue
        ref_id = str(ref_payload.get("evidence_ref_id") or "")
        if not ref_id:
            continue
        _ensure_evidence(
            evidence,
            artifacts,
            evidence_ref_id=ref_id,
            source_artifact_id=str(
                ref_payload.get("source_artifact_id")
                or assertion.source_artifact_id
                or f"artifact:{contribution.contribution_id}"
            ),
            source_domain=str(ref_payload.get("source_domain") or "manual_seed"),
            campaign_id=store.campaign_id,
            session_id=ref_payload.get("session_id"),
            locator=ref_payload.get("locator"),
            source_span_ref_id=ref_payload.get("source_span_ref_id"),
        )
        if ref_id not in evidence_ids:
            evidence_ids.append(ref_id)

    for artifact_payload in value.get("source_artifacts") or []:
        if isinstance(artifact_payload, dict) and artifact_payload.get(
            "source_artifact_id"
        ):
            artifacts[str(artifact_payload["source_artifact_id"])] = (
                UnionSupergraphSourceArtifact.model_validate(artifact_payload)
            )

    if not evidence_ids:
        ref_id = f"evidence:{contribution.contribution_id}:{edge_id}"
        artifact_id = (
            assertion.source_artifact_id
            or contribution.source_artifact_id
            or f"artifact:{contribution.contribution_id}"
        )
        _ensure_evidence(
            evidence,
            artifacts,
            evidence_ref_id=ref_id,
            source_artifact_id=artifact_id,
            source_domain=str(value.get("source_domain") or "manual_seed"),
            campaign_id=store.campaign_id,
            locator=f"contribution/{contribution.contribution_id}/{edge_id}",
        )
        evidence_ids = [ref_id]

    source_domains = list(value.get("source_domains") or ["manual_seed"])
    label = assertion.label or str(value.get("label") or predicate.replace("_", " "))
    session_ids = list(value.get("session_ids") or [])

    existing = edges.get(edge_id)
    if existing is None:
        edges[edge_id] = UnionSupergraphEdge(
            edge_id=edge_id,
            source_node_id=source_id,
            target_node_id=target_id,
            predicate=predicate,
            label=label,
            direction=str(value.get("direction") or "outbound"),
            source_domains=source_domains,
            session_ids=session_ids,
            evidence_ref_ids=evidence_ids,
            state={
                "memory_state": "contribution_accepted",
                "canon_state": value.get("canon_state") or "canonical",
                "approval_state": value.get("approval_state") or "accepted",
                "epistemic_kind": assertion.epistemic_kind,
                "visibility": assertion.visibility,
                "campaign_scope": assertion.campaign_scope,
                "introduced_by_contribution_id": contribution.contribution_id,
            },
        )
    else:
        merged_evidence = list(existing.evidence_ref_ids)
        for ref in evidence_ids:
            if ref not in merged_evidence:
                merged_evidence.append(ref)
        merged_domains = list(existing.source_domains)
        for domain in source_domains:
            if domain not in merged_domains:
                merged_domains.append(domain)
        edges[edge_id] = existing.model_copy(
            update={
                "evidence_ref_ids": merged_evidence,
                "source_domains": merged_domains,
                "state": {
                    **dict(existing.state),
                    "support_state": "supported",
                    "memory_state": "contribution_accepted",
                },
            }
        )

    updated = store.model_copy(
        update={"edges": edges, "evidence": evidence, "source_artifacts": artifacts}
    )
    updated = updated.model_copy(update={"adjacency": _rebuild_adjacency(updated)})
    return updated, edge_id


def _apply_alias_assertion(
    store: UnionSupergraphStore,
    assertion: GraphContributionAssertion,
) -> tuple[UnionSupergraphStore, str]:
    node_id = assertion.subject_node_id
    alias = assertion.label or str(assertion.value.get("alias") or "")
    if not node_id or not alias:
        raise ValueError(f"alias assertion {assertion.assertion_id} missing node/alias")
    if node_id not in store.nodes:
        raise ValueError(
            f"alias assertion {assertion.assertion_id} node does not exist"
        )

    nodes = dict(store.nodes)
    node = nodes[node_id]
    aliases_list = list(node.aliases)
    if alias not in aliases_list:
        aliases_list.append(alias)
    nodes[node_id] = node.model_copy(update={"aliases": aliases_list})
    alias_map = dict(store.aliases)
    alias_map[alias.casefold()] = node_id
    return store.model_copy(update={"nodes": nodes, "aliases": alias_map}), node_id


# Identity outcomes that never create durable support / graph mutations on merge.
_NON_MUTATING_IDENTITY_OUTCOMES = frozenset(
    {
        "ambiguous",
        "blocked_collision",
        "rejected",
        "provisional_new",
    }
)


def _is_graph_mutating_accepted_assertion(
    assertion: GraphContributionAssertion,
) -> bool:
    """True when apply_accepted_assertions would create support for this assertion."""
    if assertion.acceptance_state != "accepted":
        return False
    return assertion.identity_resolution_outcome not in _NON_MUTATING_IDENTITY_OUTCOMES


def _apply_attribute_assertion(
    store: UnionSupergraphStore,
    assertion: GraphContributionAssertion,
    contribution: GraphContribution,
) -> tuple[UnionSupergraphStore, str | None]:
    """Materialize embedded attribute evidence/artifacts; return subject id."""
    subject_id = assertion.subject_node_id
    value = dict(assertion.value)
    evidence = dict(store.evidence)
    artifacts = dict(store.source_artifacts)

    for artifact_payload in value.get("source_artifacts") or []:
        if not isinstance(artifact_payload, dict):
            raise ValueError(
                f"attribute assertion {assertion.assertion_id} has invalid "
                "embedded source artifact"
            )
        artifact_id = str(artifact_payload.get("source_artifact_id") or "")
        if not artifact_id:
            raise ValueError(
                f"attribute assertion {assertion.assertion_id} embedded source "
                "artifact is missing source_artifact_id"
            )
        artifact = UnionSupergraphSourceArtifact.model_validate(artifact_payload)
        existing_artifact = artifacts.get(artifact_id)
        if (
            existing_artifact is not None
            and existing_artifact.model_dump(mode="json")
            != artifact.model_dump(mode="json")
        ):
            raise ValueError(
                f"attribute assertion {assertion.assertion_id} source artifact "
                f"{artifact_id!r} disagrees with existing artifact"
            )
        artifacts[artifact_id] = artifact

    for ref_payload in value.get("evidence") or []:
        if not isinstance(ref_payload, dict):
            raise ValueError(
                f"attribute assertion {assertion.assertion_id} has invalid "
                "embedded evidence"
            )
        payload = dict(ref_payload)
        payload.setdefault("evidence_role", "contribution_support")
        payload.setdefault("can_open_source", True)
        payload.setdefault(
            "can_highlight_span", bool(payload.get("source_span_ref_id"))
        )
        try:
            embedded = UnionSupergraphEvidence.model_validate(payload)
        except ValueError as exc:
            raise ValueError(
                f"attribute assertion {assertion.assertion_id} has invalid "
                f"embedded evidence: {exc}"
            ) from exc
        artifact = artifacts.get(embedded.source_artifact_id)
        if artifact is None:
            raise ValueError(
                f"attribute assertion {assertion.assertion_id} evidence "
                f"{embedded.evidence_ref_id!r} is missing source artifact "
                f"{embedded.source_artifact_id!r}"
            )
        if embedded.source_domain != artifact.source_domain:
            raise ValueError(
                f"attribute assertion {assertion.assertion_id} evidence "
                f"{embedded.evidence_ref_id!r} source domain disagrees with "
                f"artifact {embedded.source_artifact_id!r}"
            )
        existing_evidence = evidence.get(embedded.evidence_ref_id)
        if (
            existing_evidence is not None
            and existing_evidence.model_dump(mode="json")
            != embedded.model_dump(mode="json")
        ):
            raise ValueError(
                f"attribute assertion {assertion.assertion_id} evidence "
                f"{embedded.evidence_ref_id!r} disagrees with existing evidence"
            )
        evidence[embedded.evidence_ref_id] = embedded

    missing_evidence = [
        ref_id for ref_id in assertion.evidence_ref_ids if ref_id not in evidence
    ]
    if missing_evidence:
        raise ValueError(
            f"attribute assertion {assertion.assertion_id} has unresolved "
            f"evidence references: {missing_evidence}"
        )

    return (
        store.model_copy(update={"evidence": evidence, "source_artifacts": artifacts}),
        subject_id,
    )


def apply_accepted_assertions(
    store: UnionSupergraphStore,
    contribution: GraphContribution,
) -> tuple[UnionSupergraphStore, dict[str, DurableAssertionSupport], list[str]]:
    """Apply accepted assertions; return updated store, support map, accepted ids."""
    support = _support_map(store)
    accepted_ids: list[str] = []
    working = store

    for assertion in contribution.accepted_assertions:
        if not _is_graph_mutating_accepted_assertion(assertion):
            continue

        graph_object_id: str | None = None
        if assertion.assertion_kind == "node":
            working, graph_object_id = _apply_node_assertion(
                working, assertion, contribution
            )
        elif assertion.assertion_kind == "edge":
            working, graph_object_id = _apply_edge_assertion(
                working, assertion, contribution
            )
        elif assertion.assertion_kind == "alias":
            working, graph_object_id = _apply_alias_assertion(working, assertion)
        elif assertion.assertion_kind in {"attribute", "evidence_ref"}:
            working, graph_object_id = _apply_attribute_assertion(
                working, assertion, contribution
            )
        else:
            raise ValueError(f"unsupported assertion_kind {assertion.assertion_kind}")

        _add_support(
            support,
            assertion,
            contribution.contribution_id,
            graph_object_id=graph_object_id,
        )
        accepted_ids.append(assertion.assertion_id)

    working = _with_support_map(working, support)
    return working, support, accepted_ids


def _contribution_already_applied(
    store: UnionSupergraphStore,
    contribution: GraphContribution,
) -> bool:
    """Return True when re-merge would be a no-op (mirrors apply_accepted_assertions skips)."""
    support = _support_map(store)
    mutating = [
        a
        for a in contribution.accepted_assertions
        if _is_graph_mutating_accepted_assertion(a)
    ]
    if not mutating:
        # Diagnostic-only / blocked-only / provisional-only: no support records expected.
        return True
    for assertion in mutating:
        record = support.get(assertion.assertion_id)
        if record is None:
            return False
        if contribution.contribution_id not in record.active_contribution_ids:
            return False
    return True


def _canonical_mutating_assertion_ids(
    contribution: GraphContribution,
) -> set[str]:
    canonical, _rekeys = _canonicalize_graph_contribution_assertions(contribution)
    return {
        assertion.assertion_id
        for assertion in canonical.accepted_assertions
        if _is_graph_mutating_accepted_assertion(assertion)
    }


def _contribution_referenced_under_legacy_assertion_ids(
    store: UnionSupergraphStore,
    *,
    contribution_id: str,
    canonical_assertion_ids: set[str],
) -> bool:
    """True when contribution appears on a non-canonical support record.

    Membership in active, superseded, or retracted support history all count.
    Retracted legacy support must still force migration; otherwise a later
    equivalent merge can publish a second semantic assertion identity.
    """
    for assertion_id, record in _support_map(store).items():
        if assertion_id in canonical_assertion_ids:
            continue
        membership = {
            *record.active_contribution_ids,
            *record.superseded_contribution_ids,
            *record.retracted_contribution_ids,
        }
        if contribution_id in membership:
            return True
    return False


def _head_requires_assertion_identity_migration(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
) -> bool:
    """True when non-failed ledger contributions still reference legacy assertion IDs."""
    index = load_contribution_index(root, world_id)
    failed = set(index.failed_contribution_ids)
    for contribution_id in index.all_contribution_ids:
        if contribution_id in failed:
            continue
        try:
            contrib = load_contribution_record(root, world_id, contribution_id)
        except FileNotFoundError:
            continue
        if contrib.status == "failed":
            continue
        canonical_ids = _canonical_mutating_assertion_ids(contrib)
        if _contribution_referenced_under_legacy_assertion_ids(
            store,
            contribution_id=contribution_id,
            canonical_assertion_ids=canonical_ids,
        ):
            return True
    return False


def _migration_required_result(
    *,
    world_id: str,
    parent_revision_id: str | None,
    contribution_ids: list[str],
    diagnostics: list[str],
    superseded_contribution_ids: list[str] | None = None,
) -> ContributionMergeResult:
    migration_diagnostics = [
        *diagnostics,
        "assertion_identity_migration_required",
        "rebuild_from_contributions(publish=True) required before merge or supersession",
    ]
    return ContributionMergeResult(
        world_id=world_id,
        parent_revision_id=parent_revision_id,
        revision_id=None,
        contribution_ids=contribution_ids,
        accepted_assertion_ids=[],
        rejected_assertion_ids=[],
        retracted_assertion_ids=[],
        superseded_contribution_ids=list(superseded_contribution_ids or []),
        diagnostics=migration_diagnostics,
        published=False,
    )


def _load_or_none(
    root: Path, world_id: str
) -> tuple[str | None, UnionSupergraphStore | None]:
    try:
        head, _revision, store = load_current_world_graph(root, world_id)
        return head.head_revision_id, store
    except WorldGraphNotFoundError:
        return None, None


def merge_contribution_to_revision(
    root: Path,
    *,
    world_id: str,
    contribution: GraphContribution,
    expected_parent_revision_id: str | None = None,
) -> ContributionMergeResult:
    """Persist contribution, merge accepted assertions, publish immutable revision."""
    contribution, assertion_rekeys = _canonicalize_graph_contribution_assertions(
        contribution
    )
    diagnostics: list[str] = list(contribution.diagnostics)
    diagnostics.extend(
        f"assertion_identity_rekeyed:{old_id}->{new_id}"
        for old_id, new_id in assertion_rekeys
    )
    rejected_ids = [a.assertion_id for a in contribution.rejected_assertions]

    for mention in contribution.unresolved_mentions:
        diagnostics.append(
            f"unresolved_mention:{mention.mention_id}:{mention.identity_resolution_outcome}"
        )
        if mention.identity_resolution_outcome in {"ambiguous", "blocked_collision"}:
            diagnostics.append(
                f"identity_{mention.identity_resolution_outcome}_kept_contribution_level"
            )

    parent_revision_id, current_store = _load_or_none(root, world_id)
    if current_store is None:
        raise WorldGraphNotFoundError(
            f"world {world_id!r} has no graph head; publish a baseline revision before "
            "merging contributions"
        )

    if expected_parent_revision_id is not None:
        head = open_world_graph_head(root, world_id)
        if head.head_revision_id != expected_parent_revision_id:
            raise ValueError(
                f"stale parent: expected {expected_parent_revision_id!r}, "
                f"head is {head.head_revision_id!r}"
            )

    index = load_contribution_index(root, world_id)
    if index.baseline_revision_id is None:
        index = index.model_copy(update={"baseline_revision_id": parent_revision_id})

    # Idempotent reprocessing: same contribution already active and applied.
    if contribution.contribution_id in index.active_contribution_ids:
        try:
            existing = load_contribution_record(
                root, world_id, contribution.contribution_id
            )
        except FileNotFoundError:
            existing = None
        if existing is not None and existing.status == "active":
            if _contribution_already_applied(current_store, contribution):
                diagnostics.append("idempotent_noop:contribution_already_applied")
                return ContributionMergeResult(
                    world_id=world_id,
                    parent_revision_id=parent_revision_id,
                    revision_id=parent_revision_id,
                    contribution_ids=[contribution.contribution_id],
                    accepted_assertion_ids=[
                        a.assertion_id for a in contribution.accepted_assertions
                    ],
                    rejected_assertion_ids=rejected_ids,
                    diagnostics=diagnostics,
                    published=False,
                )

    # Pre-repair heads keep legacy assertion IDs. Re-merge/supersede under the
    # current semantic rule would overwrite ledger records and create mixed
    # identity support. Require explicit rebuild migration first.
    if _head_requires_assertion_identity_migration(root, world_id, current_store):
        return _migration_required_result(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            contribution_ids=[contribution.contribution_id],
            diagnostics=diagnostics,
        )

    # Persist contribution record before attempting graph mutation.
    to_store = contribution.model_copy(
        update={"status": "active", "diagnostics": diagnostics}
    )
    write_contribution_record(root, world_id, to_store)

    try:
        proposed, _support, accepted_ids = apply_accepted_assertions(
            current_store, to_store
        )
        # Ensure adjacency covers all nodes even when only nodes were added.
        proposed = proposed.model_copy(
            update={"adjacency": _rebuild_adjacency(proposed)}
        )

        publish_result = publish_world_graph_revision(
            root,
            world_id,
            proposed,
            operation_ids=[to_store.contribution_id],
            expected_parent_revision_id=parent_revision_id,
        )
    except (WorldGraphValidationError, ValueError, Exception) as exc:
        failed = to_store.model_copy(
            update={
                "status": "failed",
                "diagnostics": [*diagnostics, f"merge_failed:{exc}"],
            }
        )
        write_contribution_record(root, world_id, failed)
        index = upsert_contribution_in_index(index, failed)
        save_contribution_index(root, world_id, index)
        diagnostics.append(f"merge_failed:{exc}")
        return ContributionMergeResult(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            revision_id=None,
            contribution_ids=[to_store.contribution_id],
            accepted_assertion_ids=[],
            rejected_assertion_ids=rejected_ids,
            diagnostics=diagnostics,
            published=False,
        )

    index = upsert_contribution_in_index(index, to_store)
    save_contribution_index(root, world_id, index)

    return ContributionMergeResult(
        world_id=world_id,
        parent_revision_id=parent_revision_id,
        revision_id=publish_result.revision.revision_id,
        contribution_ids=[to_store.contribution_id],
        accepted_assertion_ids=accepted_ids,
        rejected_assertion_ids=rejected_ids,
        diagnostics=diagnostics,
        published=True,
    )


def supersede_graph_contribution(
    root: Path,
    *,
    world_id: str,
    new_contribution: GraphContribution,
    superseded_contribution_id: str,
    expected_parent_revision_id: str | None = None,
) -> ContributionMergeResult:
    new_contribution, assertion_rekeys = _canonicalize_graph_contribution_assertions(
        new_contribution
    )
    if assertion_rekeys:
        new_contribution = new_contribution.model_copy(
            update={
                "diagnostics": [
                    *new_contribution.diagnostics,
                    *[
                        f"assertion_identity_rekeyed:{old_id}->{new_id}"
                        for old_id, new_id in assertion_rekeys
                    ],
                ]
            }
        )
    parent_revision_id, current_store = _load_or_none(root, world_id)
    if current_store is None:
        raise WorldGraphNotFoundError(f"world {world_id!r} has no graph head")

    if expected_parent_revision_id is not None:
        head = open_world_graph_head(root, world_id)
        if head.head_revision_id != expected_parent_revision_id:
            raise ValueError(
                f"stale parent: expected {expected_parent_revision_id!r}, "
                f"head is {head.head_revision_id!r}"
            )

    old = load_contribution_record(root, world_id, superseded_contribution_id)
    if _head_requires_assertion_identity_migration(root, world_id, current_store):
        return _migration_required_result(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            contribution_ids=[new_contribution.contribution_id],
            diagnostics=list(new_contribution.diagnostics),
            superseded_contribution_ids=[],
        )
    support = _support_map(current_store)
    unsupported = _remove_contribution_support(
        support, superseded_contribution_id, as_superseded=True
    )
    working = _with_support_map(current_store, support)
    working = _mark_graph_objects_unsupported(working, support, unsupported)

    # Ensure new contribution records supersession lineage.
    if new_contribution.supersedes_contribution_id != superseded_contribution_id:
        new_contribution = create_graph_contribution(
            world_id=new_contribution.world_id,
            source_kind=new_contribution.source_kind,
            source_artifact_id=new_contribution.source_artifact_id,
            source_revision_id=new_contribution.source_revision_id,
            extraction_profile=new_contribution.extraction_profile,
            campaign_scope=new_contribution.campaign_scope,
            candidate_assertions=new_contribution.candidate_assertions,
            accepted_assertions=new_contribution.accepted_assertions,
            rejected_assertions=new_contribution.rejected_assertions,
            unresolved_mentions=new_contribution.unresolved_mentions,
            identity_decision_ids=new_contribution.identity_decision_ids,
            authored_by=new_contribution.authored_by,
            supersedes_contribution_id=superseded_contribution_id,
            produced_at=new_contribution.produced_at,
            diagnostics=new_contribution.diagnostics,
        )

    # Persist the new contribution attempt, but do NOT mark the old contribution
    # superseded (or update the index) until publish succeeds. Otherwise a failed
    # publish leaves the ledger disagreeing with the still-active graph head.
    index = load_contribution_index(root, world_id)
    pending_new = new_contribution.model_copy(update={"status": "active"})
    write_contribution_record(root, world_id, pending_new)

    try:
        proposed, _support2, accepted_ids = apply_accepted_assertions(
            working, new_contribution
        )
        proposed = proposed.model_copy(
            update={"adjacency": _rebuild_adjacency(proposed)}
        )
        publish_result = publish_world_graph_revision(
            root,
            world_id,
            proposed,
            operation_ids=[
                f"supersede:{superseded_contribution_id}",
                new_contribution.contribution_id,
            ],
            expected_parent_revision_id=parent_revision_id,
        )
    except (WorldGraphValidationError, ValueError, Exception) as exc:
        failed = new_contribution.model_copy(
            update={"status": "failed", "diagnostics": [f"supersede_failed:{exc}"]}
        )
        write_contribution_record(root, world_id, failed)
        index = upsert_contribution_in_index(index, failed)
        save_contribution_index(root, world_id, index)
        return ContributionMergeResult(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            revision_id=None,
            contribution_ids=[new_contribution.contribution_id],
            superseded_contribution_ids=[],
            retracted_assertion_ids=[],
            diagnostics=[f"supersede_failed:{exc}"],
            published=False,
        )

    superseded = old.model_copy(update={"status": "superseded"})
    write_contribution_record(root, world_id, superseded)
    active_new = new_contribution.model_copy(update={"status": "active"})
    write_contribution_record(root, world_id, active_new)
    index = upsert_contribution_in_index(index, superseded)
    index = upsert_contribution_in_index(index, active_new)
    save_contribution_index(root, world_id, index)

    return ContributionMergeResult(
        world_id=world_id,
        parent_revision_id=parent_revision_id,
        revision_id=publish_result.revision.revision_id,
        contribution_ids=[new_contribution.contribution_id],
        accepted_assertion_ids=accepted_ids,
        retracted_assertion_ids=unsupported,
        superseded_contribution_ids=[superseded_contribution_id],
        diagnostics=[],
        published=True,
    )


def retract_graph_contribution(
    root: Path,
    *,
    world_id: str,
    contribution_id: str,
    reason: str,
    expected_parent_revision_id: str | None = None,
) -> ContributionMergeResult:
    if not reason.strip():
        raise ValueError("reason must be non-empty")

    parent_revision_id, current_store = _load_or_none(root, world_id)
    if current_store is None:
        raise WorldGraphNotFoundError(f"world {world_id!r} has no graph head")

    if expected_parent_revision_id is not None:
        head = open_world_graph_head(root, world_id)
        if head.head_revision_id != expected_parent_revision_id:
            raise ValueError(
                f"stale parent: expected {expected_parent_revision_id!r}, "
                f"head is {head.head_revision_id!r}"
            )

    existing = load_contribution_record(root, world_id, contribution_id)
    support = _support_map(current_store)
    unsupported = _remove_contribution_support(
        support, contribution_id, as_superseded=False
    )
    working = _with_support_map(current_store, support)
    working = _mark_graph_objects_unsupported(working, support, unsupported)
    working = working.model_copy(update={"adjacency": _rebuild_adjacency(working)})

    # Do not mutate the contribution ledger until publish succeeds. A failed
    # publish must leave the record active so ledger and graph head agree.
    try:
        publish_result = publish_world_graph_revision(
            root,
            world_id,
            working,
            operation_ids=[f"retract:{contribution_id}"],
            expected_parent_revision_id=parent_revision_id,
        )
    except (WorldGraphValidationError, Exception) as exc:
        return ContributionMergeResult(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            revision_id=None,
            contribution_ids=[contribution_id],
            retracted_assertion_ids=[],
            diagnostics=[f"retract_publish_failed:{exc}"],
            published=False,
        )

    retracted = existing.model_copy(
        update={
            "status": "retracted",
            "diagnostics": [*existing.diagnostics, f"retracted:{reason}"],
        }
    )
    write_contribution_record(root, world_id, retracted)
    index = load_contribution_index(root, world_id)
    index = upsert_contribution_in_index(index, retracted)
    save_contribution_index(root, world_id, index)

    return ContributionMergeResult(
        world_id=world_id,
        parent_revision_id=parent_revision_id,
        revision_id=publish_result.revision.revision_id,
        contribution_ids=[contribution_id],
        retracted_assertion_ids=unsupported,
        diagnostics=[f"retracted:{reason}"],
        published=True,
    )
