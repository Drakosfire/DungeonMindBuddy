"""Eldyrwild relationship adjudication continuity across descendant revisions.

Carries the merged PR #526 source-grounded findings forward only when a
requested revision is the adjudication anchor or a proven descendant, and the
durable edge shape plus sealed source grounding remain unchanged.

Does not mutate the World Graph. Does not invent new semantic judgments.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

import graph_memory.kernel as kernel
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_CAMPAIGN_ID,
    ELDYRWILD_PAYLOAD_SHA256,
    ELDYRWILD_RESIDUAL_FINDINGS,
    ELDYRWILD_REVISION_ID,
    ELDYRWILD_WORLD_ID,
    AdjudicationFinding,
    load_residual_source_seals,
    resolve_evidence_excerpt,
    verify_excerpt_against_seal,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _load_exact_buddy_revision,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1 = (
    "dmb_dungeonmind_relationship_adjudication_continuity_v1"
)

ContinuityState = Literal[
    "ANCHOR",
    "CARRIED_FORWARD",
    "INVALIDATED_BY_EDGE_CHANGE",
    "INVALIDATED_BY_SOURCE_CHANGE",
    "EDGE_REMOVED",
    "NOT_DESCENDANT",
    "REQUIRES_READJUDICATION",
]

ContinuityDiagnostic = Literal[
    "ANCESTRY_UNPROVEN",
    "EDGE_SHAPE_DRIFT",
    "SOURCE_GROUNDING_DRIFT",
    "SUPPORT_LINEAGE_DRIFT",
    "MISSING_EDGE",
    "MISSING_SOURCE_PROOF",
    "DURABLE_REVISION_LINEAGE_READ_SEAM_MISSING",
    "WORLD_MISMATCH",
]


class RelationshipAdjudicationContinuityError(RuntimeError):
    """Raised when continuity analysis fails closed."""


class RelationshipAdjudicationContinuityRowV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    anchor_revision_id: str
    requested_revision_id: str
    continuity_state: ContinuityState
    original_disposition: str
    original_responsible_repo: str
    original_next_action: str
    expected_buddy_predicate: str
    expected_source_node_id: str
    expected_source_buddy_kind: str
    expected_target_node_id: str
    expected_target_buddy_kind: str
    source_grounding_verified: bool
    durable_shape_verified: bool
    diagnostic: ContinuityDiagnostic | None = None
    diagnostic_detail: str | None = None


class RelationshipAdjudicationContinuityReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1
    world_id: str
    campaign_id: str
    anchor_revision_id: str
    anchor_graph_payload_sha256: str
    requested_revision_id: str
    requested_graph_payload_sha256: str | None = None
    anchor_is_ancestor: bool
    anchor_finding_count: int
    carried_forward_count: int
    invalidated_edge_change_count: int
    invalidated_source_change_count: int
    removed_edge_count: int
    requires_readjudication_count: int
    not_descendant_count: int
    anchor_count: int
    rows: list[RelationshipAdjudicationContinuityRowV1] = Field(default_factory=list)
    continuity_state_inventory: list[dict[str, Any]] = Field(default_factory=list)


@dataclass(frozen=True)
class _ExpectedEdgeShape:
    edge_id: str
    buddy_predicate: str
    source_node_id: str
    source_buddy_kind: str
    target_node_id: str
    target_buddy_kind: str
    primary_evidence_ref_id: str | None
    supporting_assertion_ids: tuple[str, ...]
    edge_evidence_ref_ids: tuple[str, ...]


def _counter_rows(counter: Counter[str]) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in sorted(counter.items())]


def prove_revision_is_anchor_or_descendant_v1(
    *,
    root: Path,
    world_id: str,
    requested_revision_id: str,
    anchor_revision_id: str = ELDYRWILD_REVISION_ID,
    anchor_world_id: str = ELDYRWILD_WORLD_ID,
) -> tuple[bool, ContinuityDiagnostic | None, str | None]:
    """Prove ancestry via the public Kernel revision-manifest parent chain.

    Walks ``parent_revision_id`` using ``load_world_graph_revision_manifest``.
    Does not parse storage paths or infer from timestamps/operation IDs.

    World ownership is part of the proof: matching revision IDs alone never
    grant ancestry across worlds.
    """
    if world_id != anchor_world_id:
        return (
            False,
            "WORLD_MISMATCH",
            f"world_id {world_id!r} is not adjudication world {anchor_world_id!r}",
        )

    if not hasattr(kernel, "load_world_graph_revision_manifest"):
        return (
            False,
            "DURABLE_REVISION_LINEAGE_READ_SEAM_MISSING",
            "graph_memory.kernel.load_world_graph_revision_manifest is unavailable",
        )

    try:
        requested_manifest = kernel.load_world_graph_revision_manifest(
            root, world_id, requested_revision_id
        )
    except WorldGraphNotFoundError as exc:
        return (
            False,
            "ANCESTRY_UNPROVEN",
            f"requested revision missing: {requested_revision_id!r} ({exc})",
        )
    except Exception as exc:  # noqa: BLE001
        return (
            False,
            "ANCESTRY_UNPROVEN",
            f"unreadable requested revision {requested_revision_id!r}: {exc}",
        )
    if getattr(requested_manifest, "world_id", None) != world_id:
        return (
            False,
            "ANCESTRY_UNPROVEN",
            f"manifest world_id mismatch at {requested_revision_id!r}",
        )

    if requested_revision_id == anchor_revision_id:
        return True, None, None

    seen: set[str] = set()
    current: str | None = requested_revision_id
    while current is not None:
        if current in seen:
            return (
                False,
                "ANCESTRY_UNPROVEN",
                f"revision lineage cycle detected at {current!r}",
            )
        seen.add(current)
        if current == anchor_revision_id:
            return True, None, None
        try:
            manifest = kernel.load_world_graph_revision_manifest(
                root, world_id, current
            )
        except WorldGraphNotFoundError as exc:
            return (
                False,
                "ANCESTRY_UNPROVEN",
                f"missing revision while walking lineage: {current!r} ({exc})",
            )
        except Exception as exc:  # noqa: BLE001
            return (
                False,
                "ANCESTRY_UNPROVEN",
                f"unreadable revision lineage at {current!r}: {exc}",
            )
        if getattr(manifest, "world_id", None) != world_id:
            return (
                False,
                "ANCESTRY_UNPROVEN",
                f"manifest world_id mismatch at {current!r}",
            )
        parent = getattr(manifest, "parent_revision_id", None)
        current = parent if isinstance(parent, str) and parent else None
    return (
        False,
        "ANCESTRY_UNPROVEN",
        f"anchor {anchor_revision_id!r} not found in parent chain of "
        f"{requested_revision_id!r}",
    )


def _supports_for_edge(store: UnionSupergraphStore, edge_id: str) -> list[dict[str, Any]]:
    supports: list[dict[str, Any]] = []
    for support in store.assertion_support.values():
        if isinstance(support, dict) and support.get("graph_object_id") == edge_id:
            supports.append(support)
        elif hasattr(support, "get") and support.get("graph_object_id") == edge_id:
            supports.append(dict(support))
    return supports


def _assertion_ids_for_edge(store: UnionSupergraphStore, edge_id: str) -> tuple[str, ...]:
    ids: list[str] = []
    for support in _supports_for_edge(store, edge_id):
        sid = support.get("assertion_id")
        if isinstance(sid, str) and sid:
            ids.append(sid)
    return tuple(dict.fromkeys(ids))


def _evidence_ids_for_edge(store: UnionSupergraphStore, edge_id: str) -> tuple[str, ...]:
    edge = store.edges.get(edge_id)
    ids: list[str] = []
    if edge is not None:
        ids.extend(list(edge.evidence_ref_ids or []))
    for support in _supports_for_edge(store, edge_id):
        ids.extend(support.get("evidence_ref_ids") or [])
        for refs in (support.get("per_contribution_evidence_ref_ids") or {}).values():
            ids.extend(refs or [])
    return tuple(dict.fromkeys(ids))


def _node_kind(store: UnionSupergraphStore, node_id: str) -> str | None:
    node = store.nodes.get(node_id)
    if node is None:
        return None
    kind = getattr(node, "kind", None)
    return kind if isinstance(kind, str) and kind.strip() else None


def _expected_shape_from_anchor_edge(
    *,
    edge_id: str,
    store: UnionSupergraphStore,
    seal: Mapping[str, Any] | None,
) -> _ExpectedEdgeShape:
    edge = store.edges.get(edge_id)
    if edge is None:
        raise RelationshipAdjudicationContinuityError(
            f"anchor finding edge missing from anchor revision: {edge_id}"
        )
    source_kind = _node_kind(store, edge.source_node_id)
    target_kind = _node_kind(store, edge.target_node_id)
    if source_kind is None or target_kind is None:
        raise RelationshipAdjudicationContinuityError(
            f"anchor finding endpoints missing kinds for {edge_id}"
        )
    primary = None
    if seal is not None:
        primary_raw = seal.get("primary_evidence_ref_id")
        if isinstance(primary_raw, str) and primary_raw:
            primary = primary_raw
    return _ExpectedEdgeShape(
        edge_id=edge_id,
        buddy_predicate=edge.predicate,
        source_node_id=edge.source_node_id,
        source_buddy_kind=source_kind,
        target_node_id=edge.target_node_id,
        target_buddy_kind=target_kind,
        primary_evidence_ref_id=primary,
        supporting_assertion_ids=_assertion_ids_for_edge(store, edge_id),
        edge_evidence_ref_ids=_evidence_ids_for_edge(store, edge_id),
    )


def _shape_matches(
    expected: _ExpectedEdgeShape,
    *,
    store: UnionSupergraphStore,
    edge_id: str,
) -> tuple[bool, str | None]:
    edge = store.edges.get(edge_id)
    if edge is None:
        return False, "edge missing"
    mismatches: list[str] = []
    if edge.predicate != expected.buddy_predicate:
        mismatches.append(
            f"predicate {edge.predicate!r} != {expected.buddy_predicate!r}"
        )
    if edge.source_node_id != expected.source_node_id:
        mismatches.append(
            f"source_node_id {edge.source_node_id!r} != {expected.source_node_id!r}"
        )
    if edge.target_node_id != expected.target_node_id:
        mismatches.append(
            f"target_node_id {edge.target_node_id!r} != {expected.target_node_id!r}"
        )
    source_kind = _node_kind(store, edge.source_node_id)
    target_kind = _node_kind(store, edge.target_node_id)
    if source_kind != expected.source_buddy_kind:
        mismatches.append(
            f"source_buddy_kind {source_kind!r} != {expected.source_buddy_kind!r}"
        )
    if target_kind != expected.target_buddy_kind:
        mismatches.append(
            f"target_buddy_kind {target_kind!r} != {expected.target_buddy_kind!r}"
        )
    if mismatches:
        return False, "; ".join(mismatches)
    return True, None


def _verify_source_grounding(
    *,
    store: UnionSupergraphStore,
    edge_id: str,
    seal: Mapping[str, Any] | None,
    world_graph_root: Path | None,
    verify_excerpt: bool,
) -> tuple[bool, ContinuityDiagnostic | None, str | None]:
    if seal is None:
        return False, "MISSING_SOURCE_PROOF", "missing source seal for edge"
    primary = seal.get("primary_evidence_ref_id")
    if not isinstance(primary, str) or not primary:
        return False, "MISSING_SOURCE_PROOF", "seal missing primary_evidence_ref_id"

    evidence_ids = set(_evidence_ids_for_edge(store, edge_id))
    if primary not in evidence_ids:
        return (
            False,
            "SOURCE_GROUNDING_DRIFT",
            f"primary evidence {primary} not linked on descendant edge/support",
        )

    evidence = store.evidence.get(primary)
    if evidence is None:
        return (
            False,
            "SOURCE_GROUNDING_DRIFT",
            f"primary evidence record missing: {primary}",
        )

    artifact_id = getattr(evidence, "source_artifact_id", None)
    span_ref = getattr(evidence, "source_span_ref_id", None)
    if artifact_id != seal.get("source_artifact_id"):
        return (
            False,
            "SOURCE_GROUNDING_DRIFT",
            f"source_artifact_id drifted: {artifact_id!r} != "
            f"{seal.get('source_artifact_id')!r}",
        )
    if span_ref != seal.get("source_span_ref_id"):
        return (
            False,
            "SOURCE_GROUNDING_DRIFT",
            f"source_span_ref_id drifted: {span_ref!r} != "
            f"{seal.get('source_span_ref_id')!r}",
        )

    artifact = store.source_artifacts.get(artifact_id) if artifact_id else None
    if artifact is None:
        return (
            False,
            "SOURCE_GROUNDING_DRIFT",
            f"source artifact missing: {artifact_id}",
        )
    content_sha = getattr(artifact, "content_sha256", None)
    if content_sha != seal.get("artifact_content_sha256"):
        return (
            False,
            "SOURCE_GROUNDING_DRIFT",
            f"artifact_content_sha256 drifted: {content_sha!r} != "
            f"{seal.get('artifact_content_sha256')!r}",
        )

    if verify_excerpt and world_graph_root is not None:
        try:
            live = resolve_evidence_excerpt(
                store,
                edge_id=edge_id,
                evidence_ref_id=primary,
                world_graph_root=world_graph_root,
            )
            verify_excerpt_against_seal(live, seal, edge_id=edge_id)
        except Exception as exc:  # noqa: BLE001
            return False, "SOURCE_GROUNDING_DRIFT", f"excerpt verification failed: {exc}"

    return True, None, None


def _verify_support_lineage(
    *,
    expected: _ExpectedEdgeShape,
    store: UnionSupergraphStore,
) -> tuple[bool, ContinuityDiagnostic | None, str | None]:
    """Require that original support was not silently replaced away.

    New contributions may appear. The original assertion IDs (when any existed)
    must still be present, or the sealed primary evidence must still be linked.
    """
    live_assertions = set(_assertion_ids_for_edge(store, expected.edge_id))
    live_evidence = set(_evidence_ids_for_edge(store, expected.edge_id))

    if expected.supporting_assertion_ids:
        retained = set(expected.supporting_assertion_ids) & live_assertions
        if not retained:
            # Support ledger replaced — still allow if primary evidence remains linked.
            if (
                expected.primary_evidence_ref_id
                and expected.primary_evidence_ref_id in live_evidence
            ):
                return True, None, None
            return (
                False,
                "SUPPORT_LINEAGE_DRIFT",
                "original supporting assertions absent and primary evidence unlinked",
            )

    if expected.primary_evidence_ref_id:
        if expected.primary_evidence_ref_id not in live_evidence:
            return (
                False,
                "SUPPORT_LINEAGE_DRIFT",
                "primary evidence linkage disappeared from support/edge",
            )

    return True, None, None


def _row_for_finding(
    *,
    edge_id: str,
    finding: AdjudicationFinding,
    expected: _ExpectedEdgeShape,
    seal: Mapping[str, Any] | None,
    requested_revision_id: str,
    anchor_revision_id: str,
    requested_store: UnionSupergraphStore | None,
    world_graph_root: Path | None,
    verify_excerpt: bool,
    ancestry_ok: bool,
    ancestry_diagnostic: ContinuityDiagnostic | None,
    ancestry_detail: str | None,
) -> RelationshipAdjudicationContinuityRowV1:
    base_kwargs = {
        "edge_id": edge_id,
        "anchor_revision_id": anchor_revision_id,
        "requested_revision_id": requested_revision_id,
        "original_disposition": finding.disposition.value,
        "original_responsible_repo": finding.responsible_repo.value,
        "original_next_action": finding.next_action.value,
        "expected_buddy_predicate": expected.buddy_predicate,
        "expected_source_node_id": expected.source_node_id,
        "expected_source_buddy_kind": expected.source_buddy_kind,
        "expected_target_node_id": expected.target_node_id,
        "expected_target_buddy_kind": expected.target_buddy_kind,
    }

    if not ancestry_ok:
        return RelationshipAdjudicationContinuityRowV1(
            **base_kwargs,
            continuity_state="NOT_DESCENDANT",
            source_grounding_verified=False,
            durable_shape_verified=False,
            diagnostic=ancestry_diagnostic or "ANCESTRY_UNPROVEN",
            diagnostic_detail=ancestry_detail,
        )

    if requested_store is None:
        return RelationshipAdjudicationContinuityRowV1(
            **base_kwargs,
            continuity_state="REQUIRES_READJUDICATION",
            source_grounding_verified=False,
            durable_shape_verified=False,
            diagnostic="ANCESTRY_UNPROVEN",
            diagnostic_detail="requested revision store unavailable",
        )

    edge = requested_store.edges.get(edge_id)
    if edge is None:
        return RelationshipAdjudicationContinuityRowV1(
            **base_kwargs,
            continuity_state="EDGE_REMOVED",
            source_grounding_verified=False,
            durable_shape_verified=False,
            diagnostic="MISSING_EDGE",
            diagnostic_detail="adjudicated edge absent from requested revision",
        )

    shape_ok, shape_detail = _shape_matches(
        expected, store=requested_store, edge_id=edge_id
    )
    if not shape_ok:
        return RelationshipAdjudicationContinuityRowV1(
            **base_kwargs,
            continuity_state="INVALIDATED_BY_EDGE_CHANGE",
            source_grounding_verified=False,
            durable_shape_verified=False,
            diagnostic="EDGE_SHAPE_DRIFT",
            diagnostic_detail=shape_detail,
        )

    support_ok, support_diag, support_detail = _verify_support_lineage(
        expected=expected, store=requested_store
    )
    if not support_ok:
        return RelationshipAdjudicationContinuityRowV1(
            **base_kwargs,
            continuity_state="REQUIRES_READJUDICATION",
            source_grounding_verified=False,
            durable_shape_verified=True,
            diagnostic=support_diag,
            diagnostic_detail=support_detail,
        )

    grounding_ok, grounding_diag, grounding_detail = _verify_source_grounding(
        store=requested_store,
        edge_id=edge_id,
        seal=seal,
        world_graph_root=world_graph_root,
        verify_excerpt=verify_excerpt,
    )
    if not grounding_ok:
        return RelationshipAdjudicationContinuityRowV1(
            **base_kwargs,
            continuity_state="INVALIDATED_BY_SOURCE_CHANGE",
            source_grounding_verified=False,
            durable_shape_verified=True,
            diagnostic=grounding_diag,
            diagnostic_detail=grounding_detail,
        )

    state: ContinuityState = (
        "ANCHOR" if requested_revision_id == anchor_revision_id else "CARRIED_FORWARD"
    )
    return RelationshipAdjudicationContinuityRowV1(
        **base_kwargs,
        continuity_state=state,
        source_grounding_verified=True,
        durable_shape_verified=True,
        diagnostic=None,
        diagnostic_detail=None,
    )


def _analyze_relationship_adjudication_continuity_with_authorities(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    findings: Mapping[str, AdjudicationFinding],
    seals_by_edge: Mapping[str, Mapping[str, Any]],
    anchor_world_id: str = ELDYRWILD_WORLD_ID,
    anchor_revision_id: str = ELDYRWILD_REVISION_ID,
    anchor_payload_sha256: str = ELDYRWILD_PAYLOAD_SHA256,
    campaign_id: str = ELDYRWILD_CAMPAIGN_ID,
    anchor_store: UnionSupergraphStore | None = None,
    requested_store: UnionSupergraphStore | None = None,
    requested_payload_sha256: str | None = None,
    world_graph_root: Path | None = None,
    verify_excerpt: bool = True,
) -> RelationshipAdjudicationContinuityReportV1:
    """Private continuity path with injectable authorities (tests only)."""
    if len(findings) != 59 and findings is ELDYRWILD_RESIDUAL_FINDINGS:
        raise RelationshipAdjudicationContinuityError(
            f"built-in adjudication findings must be exactly 59; got {len(findings)}"
        )

    if world_id != anchor_world_id:
        # Cross-world: no carry-forward authority.
        rows = [
            RelationshipAdjudicationContinuityRowV1(
                edge_id=edge_id,
                anchor_revision_id=anchor_revision_id,
                requested_revision_id=revision_id,
                continuity_state="NOT_DESCENDANT",
                original_disposition=finding.disposition.value,
                original_responsible_repo=finding.responsible_repo.value,
                original_next_action=finding.next_action.value,
                expected_buddy_predicate="",
                expected_source_node_id="",
                expected_source_buddy_kind="",
                expected_target_node_id="",
                expected_target_buddy_kind="",
                source_grounding_verified=False,
                durable_shape_verified=False,
                diagnostic="WORLD_MISMATCH",
                diagnostic_detail=(
                    f"world_id {world_id!r} is not adjudication world "
                    f"{anchor_world_id!r}"
                ),
            )
            for edge_id, finding in sorted(findings.items())
        ]
        return _finalize_report(
            world_id=world_id,
            campaign_id=campaign_id,
            anchor_revision_id=anchor_revision_id,
            anchor_graph_payload_sha256=anchor_payload_sha256,
            requested_revision_id=revision_id,
            requested_graph_payload_sha256=requested_payload_sha256,
            anchor_is_ancestor=False,
            rows=rows,
        )

    # Load expected shapes from the immutable anchor revision.
    if anchor_store is None:
        anchor_manifest, anchor_store = _load_exact_buddy_revision(
            root=root,
            world_id=anchor_world_id,
            revision_id=anchor_revision_id,
        )
        if anchor_manifest.graph_payload_sha256 != anchor_payload_sha256:
            raise RelationshipAdjudicationContinuityError(
                "anchor graph_payload_sha256 mismatch: "
                f"{anchor_manifest.graph_payload_sha256} != {anchor_payload_sha256}"
            )
    elif not isinstance(anchor_store, UnionSupergraphStore):
        raise RelationshipAdjudicationContinuityError(
            "anchor_store must be a UnionSupergraphStore"
        )

    expected_shapes: dict[str, _ExpectedEdgeShape] = {}
    for edge_id in findings:
        expected_shapes[edge_id] = _expected_shape_from_anchor_edge(
            edge_id=edge_id,
            store=anchor_store,
            seal=seals_by_edge.get(edge_id),
        )

    ancestry_ok, ancestry_diag, ancestry_detail = prove_revision_is_anchor_or_descendant_v1(
        root=root,
        world_id=world_id,
        requested_revision_id=revision_id,
        anchor_revision_id=anchor_revision_id,
        anchor_world_id=anchor_world_id,
    )

    live_requested_store = requested_store
    live_payload = requested_payload_sha256
    if ancestry_ok and live_requested_store is None:
        requested_manifest, live_requested_store = _load_exact_buddy_revision(
            root=root,
            world_id=world_id,
            revision_id=revision_id,
        )
        live_payload = requested_manifest.graph_payload_sha256

    excerpt_root = world_graph_root if world_graph_root is not None else root
    rows: list[RelationshipAdjudicationContinuityRowV1] = []
    for edge_id, finding in sorted(findings.items()):
        rows.append(
            _row_for_finding(
                edge_id=edge_id,
                finding=finding,
                expected=expected_shapes[edge_id],
                seal=seals_by_edge.get(edge_id),
                requested_revision_id=revision_id,
                anchor_revision_id=anchor_revision_id,
                requested_store=live_requested_store,
                world_graph_root=excerpt_root,
                verify_excerpt=verify_excerpt,
                ancestry_ok=ancestry_ok,
                ancestry_diagnostic=ancestry_diag,
                ancestry_detail=ancestry_detail,
            )
        )

    return _finalize_report(
        world_id=world_id,
        campaign_id=campaign_id,
        anchor_revision_id=anchor_revision_id,
        anchor_graph_payload_sha256=anchor_payload_sha256,
        requested_revision_id=revision_id,
        requested_graph_payload_sha256=live_payload,
        anchor_is_ancestor=ancestry_ok,
        rows=rows,
    )


def _finalize_report(
    *,
    world_id: str,
    campaign_id: str,
    anchor_revision_id: str,
    anchor_graph_payload_sha256: str,
    requested_revision_id: str,
    requested_graph_payload_sha256: str | None,
    anchor_is_ancestor: bool,
    rows: list[RelationshipAdjudicationContinuityRowV1],
) -> RelationshipAdjudicationContinuityReportV1:
    state_counter: Counter[str] = Counter(row.continuity_state for row in rows)
    return RelationshipAdjudicationContinuityReportV1(
        schema_version=RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1,
        world_id=world_id,
        campaign_id=campaign_id,
        anchor_revision_id=anchor_revision_id,
        anchor_graph_payload_sha256=anchor_graph_payload_sha256,
        requested_revision_id=requested_revision_id,
        requested_graph_payload_sha256=requested_graph_payload_sha256,
        anchor_is_ancestor=anchor_is_ancestor,
        anchor_finding_count=len(rows),
        carried_forward_count=state_counter.get("CARRIED_FORWARD", 0),
        invalidated_edge_change_count=state_counter.get("INVALIDATED_BY_EDGE_CHANGE", 0),
        invalidated_source_change_count=state_counter.get(
            "INVALIDATED_BY_SOURCE_CHANGE", 0
        ),
        removed_edge_count=state_counter.get("EDGE_REMOVED", 0),
        requires_readjudication_count=state_counter.get("REQUIRES_READJUDICATION", 0),
        not_descendant_count=state_counter.get("NOT_DESCENDANT", 0),
        anchor_count=state_counter.get("ANCHOR", 0),
        rows=rows,
        continuity_state_inventory=_counter_rows(state_counter),
    )


def analyze_relationship_adjudication_continuity_v1(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
) -> RelationshipAdjudicationContinuityReportV1:
    """Analyze continuity of the built-in Eldyrwild adjudication for one revision.

    Always binds the immutable built-in findings and source seals. Caller-supplied
    catalogs/seals/stores are intentionally not accepted.
    """
    return _analyze_relationship_adjudication_continuity_with_authorities(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
        findings=ELDYRWILD_RESIDUAL_FINDINGS,
        seals_by_edge=load_residual_source_seals(),
        verify_excerpt=True,
    )


def compact_relationship_adjudication_continuity_report_v1(
    report: RelationshipAdjudicationContinuityReportV1,
) -> dict[str, Any]:
    return report.model_dump(mode="json")


def continuity_active_edge_ids_v1(
    report: RelationshipAdjudicationContinuityReportV1,
) -> list[str]:
    """Edge IDs whose prior adjudication remains applicable."""
    return sorted(
        row.edge_id
        for row in report.rows
        if row.continuity_state in {"ANCHOR", "CARRIED_FORWARD"}
    )


def continuity_invalidated_edge_ids_v1(
    report: RelationshipAdjudicationContinuityReportV1,
) -> list[str]:
    """Edge IDs that had prior adjudication which no longer applies."""
    return sorted(
        row.edge_id
        for row in report.rows
        if row.continuity_state
        in {
            "INVALIDATED_BY_EDGE_CHANGE",
            "INVALIDATED_BY_SOURCE_CHANGE",
            "EDGE_REMOVED",
            "REQUIRES_READJUDICATION",
            "NOT_DESCENDANT",
        }
    )
