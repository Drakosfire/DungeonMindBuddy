"""Merge GraphContributions into proposed world graph revisions (PR005)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Mapping

from graph_memory.source_artifact_domains import CAMPAIGN_STABLE_SOURCE_DOMAINS
from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contribution_models import (
    ContributionMergeResult,
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.kernel.contributions import (
    _canonicalize_graph_contribution_assertions,
    compute_contribution_source_payload_sha256,
    create_graph_contribution,
    explicit_assertion_evidence_ref_ids,
    explicit_assertion_source_artifact_ids,
    normalize_assertion_provenance,
    semantic_assertion_value,
)
from graph_memory.kernel.world_graph import (
    WorldGraphNotFoundError,
    WorldGraphStaleParentError,
    WorldGraphValidationError,
    load_current_world_graph,
    open_world_graph_head,
    publish_world_graph_revision,
)
from graph_memory.union_supergraph.model import (
    ContributionReplayManifestEntry,
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
    upsert_and_save_contribution_index,
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


def _canonicalize_json_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _node_core_semantic_fingerprint(
    assertion: GraphContributionAssertion,
) -> tuple[Any, ...]:
    """Match world_projection correction-sensitive fingerprint (aliases excluded)."""
    value = dict(semantic_assertion_value(assertion.value))
    value.pop("aliases", None)
    return (
        assertion.assertion_kind,
        assertion.subject_node_id,
        assertion.target_node_id,
        assertion.predicate,
        assertion.label,
        _canonicalize_json_value(value),
        assertion.epistemic_kind,
        assertion.visibility,
        assertion.campaign_scope,
        _canonicalize_json_value(assertion.temporal_scope),
    )


def _load_assertion_from_support(
    root: Path,
    world_id: str,
    support: DurableAssertionSupport,
) -> GraphContributionAssertion:
    for contribution_id in support.active_contribution_ids:
        contribution = load_contribution_record(root, world_id, contribution_id)
        for candidate in contribution.accepted_assertions:
            if candidate.assertion_id == support.assertion_id:
                return candidate
    raise ValueError(
        f"assertion {support.assertion_id!r} not found in active contributions "
        f"{list(support.active_contribution_ids)}"
    )


def _refuse_disagreeing_active_node_assertion(
    *,
    root: Path,
    world_id: str,
    support: dict[str, DurableAssertionSupport],
    assertion: GraphContributionAssertion,
) -> None:
    """Fail closed before adding a second disagreeing active node support."""
    if assertion.assertion_kind != "node":
        return
    node_id = (assertion.subject_node_id or "").strip()
    if not node_id:
        return
    new_fp = _node_core_semantic_fingerprint(assertion)
    for existing in support.values():
        if existing.assertion_kind != "node":
            continue
        if existing.support_state != "supported" or not existing.active_contribution_ids:
            continue
        if existing.graph_object_id != node_id:
            continue
        if existing.assertion_id == assertion.assertion_id:
            continue
        prior = _load_assertion_from_support(root, world_id, existing)
        prior_fp = _node_core_semantic_fingerprint(prior)
        if prior_fp != new_fp:
            raise ValueError(
                "refusing node assertion that disagrees with an already-active "
                f"correction-sensitive fingerprint for {node_id!r}: "
                f"existing={existing.assertion_id!r} new={assertion.assertion_id!r}"
            )


def _synthesize_replay_manifest_from_digests(
    store: UnionSupergraphStore,
) -> list[ContributionReplayManifestEntry]:
    """Best-effort migration for revisions published before the replay manifest.

    Digests alone do not record supersession/retraction. Synthesized entries are
    treated as active so the next publish can carry a complete ordered plan.
    """
    return [
        ContributionReplayManifestEntry(
            contribution_id=contribution_id,
            status="active",
            source_payload_sha256=digest,
        )
        for contribution_id, digest in (store.contribution_source_payload_sha256 or {}).items()
    ]


def _copy_replay_manifest(
    store: UnionSupergraphStore,
) -> list[ContributionReplayManifestEntry]:
    existing = list(store.contribution_replay_manifest or [])
    if existing:
        return [
            entry
            if isinstance(entry, ContributionReplayManifestEntry)
            else ContributionReplayManifestEntry.model_validate(entry)
            for entry in existing
        ]
    return _synthesize_replay_manifest_from_digests(store)


def upsert_contribution_replay_entry(
    store: UnionSupergraphStore,
    *,
    contribution_id: str,
    status: Literal["active", "superseded", "retracted"],
    source_payload_sha256: str,
) -> UnionSupergraphStore:
    """Insert or replace one revision-bound contribution replay entry."""
    manifest = _copy_replay_manifest(store)
    updated = False
    for index, entry in enumerate(manifest):
        if entry.contribution_id != contribution_id:
            continue
        if (
            entry.source_payload_sha256 != source_payload_sha256
            and entry.source_payload_sha256
        ):
            raise ValueError(
                "contribution replay digest already bound with a different value: "
                f"{contribution_id}"
            )
        manifest[index] = ContributionReplayManifestEntry(
            contribution_id=contribution_id,
            status=status,
            source_payload_sha256=source_payload_sha256,
        )
        updated = True
        break
    if not updated:
        manifest.append(
            ContributionReplayManifestEntry(
                contribution_id=contribution_id,
                status=status,
                source_payload_sha256=source_payload_sha256,
            )
        )
    return store.model_copy(update={"contribution_replay_manifest": manifest})


def mark_contribution_replay_status(
    store: UnionSupergraphStore,
    *,
    contribution_id: str,
    status: Literal["active", "superseded", "retracted"],
) -> UnionSupergraphStore:
    """Update lifecycle status for an existing replay-manifest contribution."""
    manifest = _copy_replay_manifest(store)
    for index, entry in enumerate(manifest):
        if entry.contribution_id != contribution_id:
            continue
        manifest[index] = ContributionReplayManifestEntry(
            contribution_id=entry.contribution_id,
            status=status,
            source_payload_sha256=entry.source_payload_sha256,
        )
        return store.model_copy(update={"contribution_replay_manifest": manifest})
    digest = (store.contribution_source_payload_sha256 or {}).get(contribution_id)
    if not digest:
        raise ValueError(
            "cannot mark contribution replay status; contribution is not bound "
            f"into revision digests: {contribution_id}"
        )
    return upsert_contribution_replay_entry(
        store,
        contribution_id=contribution_id,
        status=status,
        source_payload_sha256=digest,
    )


def stamp_contribution_source_digest(
    store: UnionSupergraphStore,
    contribution: GraphContribution,
    *,
    status: Literal["active", "superseded", "retracted"] = "active",
) -> UnionSupergraphStore:
    """Bind a lifecycle-neutral contribution source digest into revision state.

    Digests are write-once per contribution ID. A later ledger lifecycle change
    (status/diagnostics) must not alter an already stamped digest. Also upserts
    the revision-bound contribution replay manifest entry used by pinned audits.
    """
    digest = compute_contribution_source_payload_sha256(contribution)
    payloads = dict(store.contribution_source_payload_sha256)
    existing = payloads.get(contribution.contribution_id)
    if existing is not None and existing != digest:
        raise ValueError(
            "contribution source digest already bound with a different value: "
            f"{contribution.contribution_id}"
        )
    payloads[contribution.contribution_id] = digest
    updated = store.model_copy(update={"contribution_source_payload_sha256": payloads})
    return upsert_contribution_replay_entry(
        updated,
        contribution_id=contribution.contribution_id,
        status=status,
        source_payload_sha256=digest,
    )


def stamp_initialization_authority(
    store: UnionSupergraphStore,
    *,
    initialization_contribution_ids: list[str],
    initialization_plan_digest: str,
    initialization_attestation_digest: str,
) -> UnionSupergraphStore:
    """Write-once initialization authority stamp for a World Graph store.

    Internal to the initialization workflow only — not a public Kernel mutator.
    Callers must already have validated plan/contribution coherence.
    """
    if not initialization_plan_digest.strip():
        raise ValueError("initialization_plan_digest must be non-empty")
    if not initialization_attestation_digest.strip():
        raise ValueError("initialization_attestation_digest must be non-empty")
    ids = list(initialization_contribution_ids)
    if store.initialization_plan_digest is not None:
        if (
            store.initialization_plan_digest != initialization_plan_digest
            or store.initialization_attestation_digest
            != initialization_attestation_digest
            or list(store.initialization_contribution_ids) != ids
        ):
            raise ValueError(
                "initialization authority already established with different values"
            )
        return store
    return store.model_copy(
        update={
            "initialization_contribution_ids": ids,
            "initialization_plan_digest": initialization_plan_digest,
            "initialization_attestation_digest": initialization_attestation_digest,
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


def _source_artifact_compatible(
    existing: Mapping[str, Any],
    incoming: Mapping[str, Any],
) -> bool:
    """True when artifacts match for merge, allowing session_id-only drift.

    Campaign-stable registries (``CAMPAIGN_STABLE_SOURCE_DOMAINS``, e.g.
    ``party_registry``) may reappear on later session promotes with a
    different session stamp but identical content digest. Session-scoped
    domains must still require exact equality — a session_id mismatch there
    is a real provenance disagreement, not stable-registry drift.
    """
    if existing == incoming:
        return True
    if existing.get("content_sha256") != incoming.get("content_sha256"):
        return False
    if not existing.get("content_sha256"):
        return False
    existing_domain = existing.get("source_domain")
    incoming_domain = incoming.get("source_domain")
    if (
        existing_domain not in CAMPAIGN_STABLE_SOURCE_DOMAINS
        or incoming_domain not in CAMPAIGN_STABLE_SOURCE_DOMAINS
    ):
        return False
    existing_core = {k: v for k, v in existing.items() if k != "session_id"}
    incoming_core = {k: v for k, v in incoming.items() if k != "session_id"}
    return existing_core == incoming_core


def _materialize_assertion_provenance(
    store: UnionSupergraphStore,
    assertion: GraphContributionAssertion,
    contribution: GraphContribution,
    *,
    context: str,
    strict_embedded_evidence: bool = False,
) -> tuple[
    dict[str, UnionSupergraphEvidence],
    dict[str, UnionSupergraphSourceArtifact],
    list[str],
]:
    """Materialize every provenance form accepted by the shared normalizer.

    Reference-only evidence ids must already resolve in the store; embedded
    evidence and source-artifact payloads create their records here. This
    makes it impossible for a merge to publish provenance the projection
    reader cannot close over later.
    """
    value = dict(assertion.value)
    provenance = normalize_assertion_provenance(assertion)
    evidence = dict(store.evidence)
    artifacts = dict(store.source_artifacts)
    default_artifact_id = (
        assertion.source_artifact_id
        or contribution.source_artifact_id
        or f"artifact:{contribution.contribution_id}"
    )
    default_domain = str(value.get("source_domain") or "manual_seed")

    for artifact_payload in value.get("source_artifacts") or []:
        if not isinstance(artifact_payload, dict):
            raise ValueError(
                f"{context} assertion {assertion.assertion_id} has invalid "
                "embedded source artifact"
            )
        artifact_id = str(artifact_payload.get("source_artifact_id") or "")
        if not artifact_id:
            raise ValueError(
                f"{context} assertion {assertion.assertion_id} embedded source "
                "artifact is missing source_artifact_id"
            )
        artifact = UnionSupergraphSourceArtifact.model_validate(artifact_payload)
        existing = artifacts.get(artifact_id)
        if existing is not None:
            existing_dump = existing.model_dump(mode="json")
            incoming_dump = artifact.model_dump(mode="json")
            if existing_dump != incoming_dump:
                # Campaign-stable registries often re-promote with a new
                # session_id stamp while content_sha256 is unchanged. Keep the
                # existing record when that is the only disagreement.
                if not _source_artifact_compatible(existing_dump, incoming_dump):
                    raise ValueError(
                        f"{context} assertion {assertion.assertion_id} source artifact "
                        f"{artifact_id!r} disagrees with existing artifact"
                    )
                artifact = existing
        artifacts[artifact_id] = artifact

    for evidence_payload in value.get("evidence") or []:
        if not isinstance(evidence_payload, dict):
            raise ValueError(
                f"{context} assertion {assertion.assertion_id} has invalid "
                "embedded evidence"
            )
        evidence_ref_id = str(evidence_payload.get("evidence_ref_id") or "")
        if not evidence_ref_id:
            raise ValueError(
                f"{context} assertion {assertion.assertion_id} embedded evidence "
                "is missing evidence_ref_id"
            )
        evidence_artifact_id = str(
            evidence_payload.get("source_artifact_id") or default_artifact_id
        )
        if strict_embedded_evidence:
            artifact = artifacts.get(evidence_artifact_id)
            if artifact is None:
                raise ValueError(
                    f"{context} assertion {assertion.assertion_id} evidence "
                    f"{evidence_ref_id!r} is missing source artifact "
                    f"{evidence_artifact_id!r}"
                )
            evidence_domain = str(
                evidence_payload.get("source_domain") or default_domain
            )
            if artifact.source_domain != evidence_domain:
                raise ValueError(
                    f"{context} assertion {assertion.assertion_id} evidence "
                    f"{evidence_ref_id!r} source domain disagrees with "
                    f"artifact {evidence_artifact_id!r}"
                )
        _ensure_evidence(
            evidence,
            artifacts,
            evidence_ref_id=evidence_ref_id,
            source_artifact_id=evidence_artifact_id,
            source_domain=str(evidence_payload.get("source_domain") or default_domain),
            campaign_id=store.campaign_id,
            session_id=evidence_payload.get("session_id"),
            locator=evidence_payload.get("locator"),
            source_span_ref_id=evidence_payload.get("source_span_ref_id"),
        )

    for artifact_id in provenance.source_artifact_ids:
        if artifact_id not in artifacts:
            _ensure_artifact(
                artifacts,
                artifact_id=artifact_id,
                source_domain=default_domain,
                campaign_id=store.campaign_id,
            )

    missing_evidence = [
        evidence_ref_id
        for evidence_ref_id in provenance.evidence_ref_ids
        if evidence_ref_id not in evidence
    ]
    if missing_evidence:
        raise ValueError(
            f"{context} assertion {assertion.assertion_id} has unresolved "
            f"evidence references: {missing_evidence}"
        )
    missing_artifacts = [
        artifact_id
        for artifact_id in provenance.source_artifact_ids
        if artifact_id not in artifacts
    ]
    if missing_artifacts:
        raise ValueError(
            f"{context} assertion {assertion.assertion_id} has unresolved "
            f"source artifacts: {missing_artifacts}"
        )
    return evidence, artifacts, provenance.evidence_ref_ids


def _add_support(
    support: dict[str, DurableAssertionSupport],
    assertion: GraphContributionAssertion,
    contribution_id: str,
    *,
    graph_object_id: str | None,
) -> None:
    existing = support.get(assertion.assertion_id)
    contribution_evidence_ref_ids = explicit_assertion_evidence_ref_ids(assertion)
    contribution_source_artifact_ids = explicit_assertion_source_artifact_ids(assertion)
    if existing is None:
        support[assertion.assertion_id] = DurableAssertionSupport(
            assertion_id=assertion.assertion_id,
            active_contribution_ids=[contribution_id],
            evidence_ref_ids=contribution_evidence_ref_ids,
            source_artifact_ids=contribution_source_artifact_ids,
            support_state="supported",
            introduced_by_contribution_id=contribution_id,
            assertion_kind=assertion.assertion_kind,
            graph_object_id=graph_object_id,
            provenance_lineage_version=1,
            per_contribution_evidence_ref_ids={contribution_id: contribution_evidence_ref_ids},
            per_contribution_source_artifact_ids={contribution_id: contribution_source_artifact_ids},
        )
        return

    active = list(existing.active_contribution_ids)
    if contribution_id not in active:
        active.append(contribution_id)
    evidence = list(existing.evidence_ref_ids)
    for ref in contribution_evidence_ref_ids:
        if ref not in evidence:
            evidence.append(ref)
    sources = list(existing.source_artifact_ids)
    for aid in contribution_source_artifact_ids:
        if aid not in sources:
            sources.append(aid)
    per_contribution_evidence = dict(existing.per_contribution_evidence_ref_ids)
    per_contribution_evidence[contribution_id] = contribution_evidence_ref_ids
    per_contribution_sources = dict(existing.per_contribution_source_artifact_ids)
    per_contribution_sources[contribution_id] = contribution_source_artifact_ids
    support[assertion.assertion_id] = existing.model_copy(
        update={
            "active_contribution_ids": active,
            "evidence_ref_ids": evidence,
            "source_artifact_ids": sources,
            "support_state": "supported",
            "graph_object_id": existing.graph_object_id or graph_object_id,
            "provenance_lineage_version": 1,
            "per_contribution_evidence_ref_ids": per_contribution_evidence,
            "per_contribution_source_artifact_ids": per_contribution_sources,
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
        per_contribution_evidence = dict(record.per_contribution_evidence_ref_ids)
        per_contribution_evidence.pop(contribution_id, None)
        per_contribution_sources = dict(record.per_contribution_source_artifact_ids)
        per_contribution_sources.pop(contribution_id, None)
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
                "per_contribution_evidence_ref_ids": per_contribution_evidence,
                "per_contribution_source_artifact_ids": per_contribution_sources,
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
    """Flip a node/edge's own memory_state when it loses its defining support.

    Attribute and alias assertions share ``graph_object_id`` with the node or
    edge they describe, but they are not what makes that node/edge exist --
    losing an alias must not evict the whole node from the graph. Only a
    ``node``/``edge`` kind assertion losing support means the graph object
    itself is unsupported.
    """
    nodes = dict(store.nodes)
    edges = dict(store.edges)
    for assertion_id in unsupported_assertion_ids:
        record = support.get(assertion_id)
        if record is None or not record.graph_object_id:
            continue
        object_id = record.graph_object_id
        has_other_active_support = any(
            candidate.assertion_id != assertion_id
            and candidate.graph_object_id == object_id
            and candidate.assertion_kind == record.assertion_kind
            and candidate.support_state == "supported"
            and candidate.active_contribution_ids
            for candidate in support.values()
        )
        if (
            object_id in nodes
            and record.assertion_kind == "node"
            and not has_other_active_support
        ):
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
        if (
            object_id in edges
            and record.assertion_kind == "edge"
            and not has_other_active_support
        ):
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
    aliases = dict(store.aliases)
    evidence, artifacts, evidence_ids = _materialize_assertion_provenance(
        store, assertion, contribution, context="node"
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
    edges = dict(store.edges)
    evidence, artifacts, evidence_ids = _materialize_assertion_provenance(
        store, assertion, contribution, context="edge"
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
        # session_ids are additive observation provenance (same edge re-attested
        # across sessions). Merge like evidence/domains; do not replace.
        merged_sessions = list(existing.session_ids)
        for session_id in session_ids:
            if session_id not in merged_sessions:
                merged_sessions.append(session_id)
        edges[edge_id] = existing.model_copy(
            update={
                "evidence_ref_ids": merged_evidence,
                "source_domains": merged_domains,
                "session_ids": merged_sessions,
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
    contribution: GraphContribution,
) -> tuple[UnionSupergraphStore, str]:
    node_id = assertion.subject_node_id
    alias = assertion.label or str(assertion.value.get("alias") or "")
    if not node_id or not alias:
        raise ValueError(f"alias assertion {assertion.assertion_id} missing node/alias")
    if node_id not in store.nodes:
        raise ValueError(
            f"alias assertion {assertion.assertion_id} node does not exist"
        )

    evidence, artifacts, evidence_ref_ids = _materialize_assertion_provenance(
        store, assertion, contribution, context="alias"
    )
    nodes = dict(store.nodes)
    node = nodes[node_id]
    aliases_list = list(node.aliases)
    if alias not in aliases_list:
        aliases_list.append(alias)
    node_evidence_ref_ids = list(node.evidence_ref_ids)
    for evidence_ref_id in evidence_ref_ids:
        if evidence_ref_id not in node_evidence_ref_ids:
            node_evidence_ref_ids.append(evidence_ref_id)
    nodes[node_id] = node.model_copy(
        update={"aliases": aliases_list, "evidence_ref_ids": node_evidence_ref_ids}
    )
    alias_map = dict(store.aliases)
    existing_owner = alias_map.get(alias.casefold())
    if existing_owner is not None and existing_owner != node_id:
        raise ValueError(
            f"alias assertion {assertion.assertion_id} would hijack alias "
            f"{alias!r} owned by {existing_owner!r}"
        )
    alias_map[alias.casefold()] = node_id
    return (
        store.model_copy(
            update={
                "nodes": nodes,
                "aliases": alias_map,
                "evidence": evidence,
                "source_artifacts": artifacts,
            }
        ),
        node_id,
    )


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
    """Materialize normalized attribute provenance; return subject id."""
    subject_id = assertion.subject_node_id
    evidence, artifacts, _evidence_ref_ids = _materialize_assertion_provenance(
        store,
        assertion,
        contribution,
        context="attribute",
        strict_embedded_evidence=True,
    )
    return (
        store.model_copy(update={"evidence": evidence, "source_artifacts": artifacts}),
        subject_id,
    )


def apply_accepted_assertions(
    store: UnionSupergraphStore,
    contribution: GraphContribution,
    *,
    root: Path | None = None,
    world_id: str | None = None,
) -> tuple[UnionSupergraphStore, dict[str, DurableAssertionSupport], list[str]]:
    """Apply accepted assertions; return updated store, support map, accepted ids.

    When ``root`` and ``world_id`` are supplied, refuse node assertions whose
    correction-sensitive fingerprint disagrees with an already-active support
    for the same subject (projection integrity contract).
    """
    support = _support_map(store)
    accepted_ids: list[str] = []
    working = store

    for assertion in contribution.accepted_assertions:
        if not _is_graph_mutating_accepted_assertion(assertion):
            continue

        if (
            root is not None
            and world_id is not None
            and assertion.assertion_kind == "node"
        ):
            _refuse_disagreeing_active_node_assertion(
                root=root,
                world_id=world_id,
                support=support,
                assertion=assertion,
            )

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
            working, graph_object_id = _apply_alias_assertion(
                working, assertion, contribution
            )
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


def _contribution_active_and_applied_on_head(
    root: Path,
    world_id: str,
    contribution: GraphContribution,
) -> bool:
    """True when this contribution is active in the ledger and applied on the head.

    Used so a CAS loser cannot demote a peer-published identical contribution.
    """
    try:
        existing = load_contribution_record(
            root, world_id, contribution.contribution_id
        )
    except FileNotFoundError:
        return False
    if existing is None or existing.status != "active":
        return False
    try:
        _head, _revision, store = load_current_world_graph(root, world_id)
    except WorldGraphNotFoundError:
        return False
    return _contribution_already_applied(store, contribution)


def _mark_merge_contribution_failed(
    *,
    root: Path,
    world_id: str,
    to_store: GraphContribution,
    diagnostics: list[str],
    reason: str,
) -> list[str]:
    failed = to_store.model_copy(
        update={
            "status": "failed",
            "diagnostics": [*diagnostics, reason],
        }
    )
    write_contribution_record(root, world_id, failed)
    upsert_and_save_contribution_index(root, world_id, failed)
    return [*diagnostics, reason]


def _stale_parent_value_error(
    *,
    expected_parent_revision_id: str | None,
    exc: BaseException,
) -> ValueError:
    return ValueError(
        f"stale parent: expected {expected_parent_revision_id!r}, "
        f"head advanced during publish ({exc})"
    )


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


def _head_lacks_contribution_source_authority(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
) -> bool:
    """True when non-failed ledger contributions lack coherent source digests.

    Forward-only: incomplete heads are refused. Operators must reinitialize (or
    rebuild to recompute from the ledger), not rely on a legacy-migration path.
    """
    index = load_contribution_index(root, world_id)
    failed = set(index.failed_contribution_ids)
    digests = store.contribution_source_payload_sha256 or {}
    for contribution_id in index.all_contribution_ids:
        if contribution_id in failed:
            continue
        try:
            contrib = load_contribution_record(root, world_id, contribution_id)
        except FileNotFoundError:
            # Indexed, non-failed contributions must have a ledger record. A
            # missing file means graph-data source authority cannot be verified.
            return True
        if contrib.status == "failed":
            continue
        expected = digests.get(contribution_id)
        if expected is None:
            return True
        actual = compute_contribution_source_payload_sha256(contrib)
        if actual != expected:
            return True
    return False


def _migration_required_result(
    *,
    world_id: str,
    parent_revision_id: str | None,
    contribution_ids: list[str],
    diagnostics: list[str],
    superseded_contribution_ids: list[str] | None = None,
    reason: str = "assertion_identity_migration_required",
) -> ContributionMergeResult:
    if reason == "contribution_source_authority_incomplete":
        guidance = (
            "reinitialize the world graph (or rebuild_from_contributions with "
            "publish=True to recompute digests) before merge, supersession, or retraction"
        )
    else:
        guidance = (
            "rebuild_from_contributions(publish=True) required before merge or supersession"
        )
    migration_diagnostics = [
        *diagnostics,
        reason,
        guidance,
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

    # Forward-only: refuse incomplete source authority before any idempotent no-op.
    if _head_lacks_contribution_source_authority(root, world_id, current_store):
        return _migration_required_result(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            contribution_ids=[contribution.contribution_id],
            diagnostics=diagnostics,
            reason="contribution_source_authority_incomplete",
        )

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
    # identity support. Require explicit rebuild first.
    if _head_requires_assertion_identity_migration(root, world_id, current_store):
        return _migration_required_result(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            contribution_ids=[contribution.contribution_id],
            diagnostics=diagnostics,
            reason="assertion_identity_migration_required",
        )

    # Persist contribution record before attempting graph mutation.
    to_store = contribution.model_copy(
        update={"status": "active", "diagnostics": diagnostics}
    )
    write_contribution_record(root, world_id, to_store)

    try:
        proposed, _support, accepted_ids = apply_accepted_assertions(
            current_store, to_store, root=root, world_id=world_id
        )
        # Ensure adjacency covers all nodes even when only nodes were added.
        proposed = proposed.model_copy(
            update={"adjacency": _rebuild_adjacency(proposed)}
        )
        proposed = stamp_contribution_source_digest(proposed, to_store)

        publish_result = publish_world_graph_revision(
            root,
            world_id,
            proposed,
            operation_ids=[to_store.contribution_id],
            expected_parent_revision_id=parent_revision_id,
        )
    except WorldGraphStaleParentError as exc:
        # CAS loser: never demote a contribution that already published on head.
        if not _contribution_active_and_applied_on_head(root, world_id, to_store):
            _mark_merge_contribution_failed(
                root=root,
                world_id=world_id,
                to_store=to_store,
                diagnostics=diagnostics,
                reason=f"merge_failed:{exc}",
            )
        raise _stale_parent_value_error(
            expected_parent_revision_id=parent_revision_id,
            exc=exc,
        ) from exc
    except (WorldGraphValidationError, ValueError, Exception) as exc:
        if isinstance(exc, ValueError) and "stale parent" in str(exc).lower():
            if not _contribution_active_and_applied_on_head(root, world_id, to_store):
                _mark_merge_contribution_failed(
                    root=root,
                    world_id=world_id,
                    to_store=to_store,
                    diagnostics=diagnostics,
                    reason=f"merge_failed:{exc}",
                )
            raise
        # If a peer already published this exact contribution, do not overwrite
        # the winning active ledger record as failed.
        if _contribution_active_and_applied_on_head(root, world_id, to_store):
            raise
        diagnostics = _mark_merge_contribution_failed(
            root=root,
            world_id=world_id,
            to_store=to_store,
            diagnostics=diagnostics,
            reason=f"merge_failed:{exc}",
        )
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

    upsert_and_save_contribution_index(
        root,
        world_id,
        to_store,
        baseline_revision_id=parent_revision_id,
    )

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

    if _head_lacks_contribution_source_authority(root, world_id, current_store):
        return _migration_required_result(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            contribution_ids=[new_contribution.contribution_id],
            diagnostics=list(new_contribution.diagnostics),
            superseded_contribution_ids=[],
            reason="contribution_source_authority_incomplete",
        )
    old = load_contribution_record(root, world_id, superseded_contribution_id)
    if _head_requires_assertion_identity_migration(root, world_id, current_store):
        return _migration_required_result(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            contribution_ids=[new_contribution.contribution_id],
            diagnostics=list(new_contribution.diagnostics),
            superseded_contribution_ids=[],
            reason="assertion_identity_migration_required",
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
    pending_new = new_contribution.model_copy(update={"status": "active"})
    write_contribution_record(root, world_id, pending_new)

    try:
        proposed, _support2, accepted_ids = apply_accepted_assertions(
            working, new_contribution, root=root, world_id=world_id
        )
        proposed = proposed.model_copy(
            update={"adjacency": _rebuild_adjacency(proposed)}
        )
        proposed = stamp_contribution_source_digest(proposed, new_contribution)
        proposed = mark_contribution_replay_status(
            proposed,
            contribution_id=superseded_contribution_id,
            status="superseded",
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
        upsert_and_save_contribution_index(root, world_id, failed)
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
    upsert_and_save_contribution_index(root, world_id, superseded, active_new)

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

    if _head_lacks_contribution_source_authority(root, world_id, current_store):
        return _migration_required_result(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            contribution_ids=[contribution_id],
            diagnostics=[],
            reason="contribution_source_authority_incomplete",
        )

    existing = load_contribution_record(root, world_id, contribution_id)
    support = _support_map(current_store)
    unsupported = _remove_contribution_support(
        support, contribution_id, as_superseded=False
    )
    working = _with_support_map(current_store, support)
    working = _mark_graph_objects_unsupported(working, support, unsupported)
    working = working.model_copy(update={"adjacency": _rebuild_adjacency(working)})
    working = mark_contribution_replay_status(
        working,
        contribution_id=contribution_id,
        status="retracted",
    )

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
    upsert_and_save_contribution_index(root, world_id, retracted)

    return ContributionMergeResult(
        world_id=world_id,
        parent_revision_id=parent_revision_id,
        revision_id=publish_result.revision.revision_id,
        contribution_ids=[contribution_id],
        retracted_assertion_ids=unsupported,
        diagnostics=[f"retracted:{reason}"],
        published=True,
    )
