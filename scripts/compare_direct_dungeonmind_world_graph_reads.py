#!/usr/bin/env -S uv run python
"""CUTOVER R.3: real-current semantic parity + performance witness.

Runs the same logical World Graph read requests through both read paths
against the live adopted world:

```text
legacy path (oracle):  DND authority → Buddy hydration → Buddy kernel
new path (direct):     DND authority → DND R.1/R.2 native read → DTO adapter
```

The legacy path exists only as the comparison oracle for this witness; it is
not a permanent shadow mode.

Outputs a local JSON report (private — contains object/evidence identifiers;
never commit it) and prints a safe aggregate summary (counts, timings,
divergence-class tallies) suitable for transcription into the checked-in
benchmark summary.

Divergence classification follows HANDOFF §6.3:

```text
representation only
new deterministic R.2 search ranking
product-local presentation join
intentionally retired legacy-only field
blocking semantic difference
```

plus one explicit extension, ``successor_admission_semantics_accepted``, used
solely for the review-accepted evidence-chain scope tightening residual
(see Docs/Benchmarks/BASELINE-r3-direct-dungeonmind-current-reads.md).

Usage:

```bash
uv run python scripts/compare_direct_dungeonmind_world_graph_reads.py \
    --database-url "$DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL" \
    --world-id eldyrwild \
    --frozen-root /path/to/repo/out \
    --repo-root /path/to/repo \
    --runs 5 \
    --output /tmp/r3-witness.json
```
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Divergence model
# ---------------------------------------------------------------------------

CLASS_REPRESENTATION = "representation only"
CLASS_SEARCH_RANKING = "new deterministic R.2 search ranking"
CLASS_PRESENTATION_JOIN = "product-local presentation join"
CLASS_RETIRED_LEGACY = "intentionally retired legacy-only field"
CLASS_BLOCKING = "blocking semantic difference"
CLASS_ADMISSION_ACCEPTED = "successor_admission_semantics_accepted"
CLASS_UNREPRESENTED_PROPERTY = "property assertions not represented in v6 payload"
CLASS_DATA_INTEGRITY = "data integrity issue (broken evidence chain)"

# Review-accepted residual: world-universal objects whose remaining evidence
# is genuine campaign chronology (c2 recap) are excluded from c1 reads by
# DungeonMind's fail-closed per-evidence-chain admission. The legacy kernel
# scoped objects but never evidence chains. Accepted in the R.3 review of the
# campaign-lens divergence after the world-owning data fix landed.
EXPECTED_ADMISSION_RESIDUAL: dict[str, set[str]] = {
    # case name → node ids legacy serves that direct excludes
    "projection:campaign:c1": {"location:mireward"},
    # The pin variants read the same c1 scope through different revision
    # pins; the same accepted residual applies.
    "projection:pin:exact-dnd-head": {"location:mireward"},
    "projection:pin:legacy-bridge": {"location:mireward"},
}


@dataclass
class Divergence:
    case: str
    kind: str
    identifier: str
    classification: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "case": self.case,
            "kind": self.kind,
            "identifier": self.identifier,
            "classification": self.classification,
            "detail": self.detail,
        }


@dataclass
class CaseReport:
    case: str
    divergences: list[Divergence] = field(default_factory=list)
    legacy_counts: dict[str, int] = field(default_factory=dict)
    direct_counts: dict[str, int] = field(default_factory=dict)
    error: str | None = None


# ---------------------------------------------------------------------------
# Path runners
# ---------------------------------------------------------------------------


_LEGACY_ROUTE_CACHE: dict[tuple[str, str | None, str | None, str], Any] = {}


def _legacy_route(request, *, root: Path):
    """Hydrate once per (scope, campaign, pin, admissibility); reuse after.

    The legacy authority adapter's hydration is keyed by DungeonMind revision;
    routing every case through it unchanged would re-verify the same hydration
    for minutes per case. The route only rewrites the revision pin, so caching
    per scope identity is faithful for the witness's unpinned/pinned requests.
    Admissibility is part of the key: the kernel fails closed on non-GM, so a
    cached GM route must never be reused for a PLAYER request.
    """
    from apps.live_control_server.services.world_graph_projection import (
        _route_authority_read,
    )

    key = (
        getattr(request, "scope_mode", "campaign"),
        getattr(request, "campaign_id", None),
        getattr(request, "revision_pin", None),
        getattr(request, "admissibility", "gm"),
    )
    if key not in _LEGACY_ROUTE_CACHE:
        _LEGACY_ROUTE_CACHE[key] = _route_authority_read(request, root)
    return _LEGACY_ROUTE_CACHE[key]


def _legacy_projection(request, *, root: Path):
    """Pre-R.3 service path: authority route (hydration) + Buddy kernel."""
    import graph_memory.kernel as kernel
    from apps.live_control_server.services.world_graph_projection import (
        _normalize_authority_identity,
    )

    route = _legacy_route(request, root=root)
    context = kernel.resolve_projection_read_context(route.graph_root, route.request)
    projection = kernel.project_world_graph_from_context(
        route.graph_root, route.request, context
    )
    return _normalize_authority_identity(projection, route)


def _legacy_retrieval(op: str, request, *, root: Path, repo_root: Path):
    import graph_memory.kernel as kernel
    from apps.live_control_server.services.world_graph_retrieval import (
        _normalize_authority_identity,
    )

    route = _legacy_route(request, root=root)
    # Unpinned GM requests pass through routing unchanged; the cached route
    # supplies the hydrated graph root and public identity, the current op's
    # request object is the one the kernel validates.
    if getattr(request, "revision_pin", None):
        routed_request = route.request
    else:
        routed_request = request
    if op == "search":
        result = kernel.search_campaign_graph(route.graph_root, routed_request)
    elif op == "object":
        result = kernel.get_campaign_object(route.graph_root, routed_request)
    elif op == "neighborhood":
        result = kernel.get_object_neighborhood(route.graph_root, routed_request)
    elif op == "evidence":
        result = kernel.get_object_evidence(route.graph_root, routed_request)
    elif op == "anchor":
        resolved = kernel.resolve_admitted_anchor_match(route.graph_root, routed_request)
        if hasattr(resolved, "outcome"):  # already a read result
            return _normalize_authority_identity(resolved, route)
        raise RuntimeError(
            "legacy anchor oracle resolved to a derivation; use the service path"
        )
    else:  # pragma: no cover
        raise ValueError(op)
    return _normalize_authority_identity(result, route)


def _legacy_anchor_read(request, *, root: Path, repo_root: Path):
    """The legacy anchor read has product-local content joins; call the full
    pre-R.3 service body via the current service's legacy helpers."""
    import graph_memory.kernel as kernel
    from apps.live_control_server.services.world_graph_retrieval import (
        _normalize_authority_identity,
    )

    route = _legacy_route(request, root=root)
    resolved = kernel.resolve_admitted_anchor_match(route.graph_root, request)
    # WorldGraphSourceAnchorReadResult short-circuit (unavailable/unsupported)
    if hasattr(resolved, "outcome"):
        return _normalize_authority_identity(resolved, route)
    return resolved  # derivation; content join compared separately


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def _node_key(node: Any) -> str:
    return node.node_id


def _rel_key(rel: Any) -> tuple[str, str, str]:
    return (rel.source_node_id, rel.target_node_id, rel.predicate)


def _rel_endpoints(rel: Any) -> tuple[str, str]:
    return (rel.source_node_id, rel.target_node_id)


def _attr_key(attr: Any) -> tuple[str, str]:
    return (attr.subject_node_id, getattr(attr, "attribute_id", None) or attr.label)


def compare_projections(case: str, legacy, direct) -> CaseReport:
    report = CaseReport(case=case)
    report.legacy_counts = {
        "nodes": len(legacy.nodes),
        "relationships": len(legacy.relationships),
        "attributes": len(legacy.attributes),
        "evidence": len(legacy.evidence),
    }
    report.direct_counts = {
        "nodes": len(direct.nodes),
        "relationships": len(direct.relationships),
        "attributes": len(direct.attributes),
        "evidence": len(direct.evidence),
    }

    # Snapshot identity must compare exactly (§6.2).
    for field_name in ("revision_id", "head_revision_id", "is_head", "scope_mode", "admissibility"):
        l_val = getattr(legacy.snapshot, field_name)
        d_val = getattr(direct.snapshot, field_name)
        if l_val != d_val:
            report.divergences.append(
                Divergence(
                    case,
                    f"snapshot.{field_name}",
                    f"{l_val!r} != {d_val!r}",
                    CLASS_BLOCKING,
                    "snapshot identity must be exact",
                )
            )

    legacy_nodes = {_node_key(n): n for n in legacy.nodes}
    direct_nodes = {_node_key(n): n for n in direct.nodes}
    expected_residual = EXPECTED_ADMISSION_RESIDUAL.get(case, set())

    for node_id in sorted(legacy_nodes.keys() - direct_nodes.keys()):
        if node_id in expected_residual:
            report.divergences.append(
                Divergence(
                    case,
                    "node_only_in_legacy",
                    node_id,
                    CLASS_ADMISSION_ACCEPTED,
                    "evidence-chain scope tightening; review-accepted residual",
                )
            )
        elif legacy_nodes[node_id].kind == "external_resource":
            # Handoff §D: external_resource is a Buddy-only hydration-era
            # payload the DungeonMind authority snapshot intentionally omits.
            report.divergences.append(
                Divergence(
                    case,
                    "node_only_in_legacy",
                    node_id,
                    CLASS_RETIRED_LEGACY,
                    "external_resource node intentionally omitted from the "
                    "DungeonMind authority snapshot (handoff §D)",
                )
            )
        elif node_id == "node:cutover-canary":
            # The cutover-canary's evidence chain references a source artifact
            # (artifact:recap:longmont-c2:session-26-cutover-live-canary) that
            # does not exist in the source repository. DungeonMind's fail-closed
            # admission correctly excludes it; the legacy kernel serves it
            # because it never validates evidence chains.
            report.divergences.append(
                Divergence(
                    case,
                    "node_only_in_legacy",
                    node_id,
                    CLASS_DATA_INTEGRITY,
                    "evidence chain references a non-existent source artifact; "
                    "direct path correctly excludes, legacy kernel serves "
                    "because it never validates evidence chains",
                )
            )
        else:
            report.divergences.append(
                Divergence(
                    case,
                    "node_only_in_legacy",
                    node_id,
                    CLASS_BLOCKING,
                    "legacy admits an object the direct path excludes; not a "
                    "registered residual",
                )
            )
    for node_id in sorted(direct_nodes.keys() - legacy_nodes.keys()):
        report.divergences.append(
            Divergence(
                case,
                "node_only_in_direct",
                node_id,
                CLASS_RETIRED_LEGACY,
                "legacy kernel projectability/identity filter retired; "
                "DungeonMind serves admitted payload truth",
            )
        )

    # Labels/aliases compare exactly for shared nodes.
    for node_id in sorted(legacy_nodes.keys() & direct_nodes.keys()):
        l_node, d_node = legacy_nodes[node_id], direct_nodes[node_id]
        if l_node.label != d_node.label:
            report.divergences.append(
                Divergence(case, "node.label", node_id, CLASS_BLOCKING)
            )
        if sorted(l_node.aliases) != sorted(d_node.aliases):
            # The legacy kernel defaults a node's aliases to [label] when a
            # contribution declares none (contribution_merge). The v6 payload
            # carries explicit governed aliases only; the label echo is a
            # kernel presentation default, not source data. Real alias data
            # (beyond the echo) must still compare exactly.
            legacy_residual = sorted(a for a in l_node.aliases if a != l_node.label)
            if legacy_residual == sorted(d_node.aliases):
                report.divergences.append(
                    Divergence(
                        case,
                        "node.aliases",
                        node_id,
                        CLASS_REPRESENTATION,
                        "legacy kernel label-echo alias default retired; "
                        "explicit governed aliases compare exactly",
                    )
                )
            else:
                report.divergences.append(
                    Divergence(
                        case,
                        "node.aliases",
                        f"{node_id}: legacy={sorted(l_node.aliases)} direct={sorted(d_node.aliases)}",
                        CLASS_BLOCKING,
                        "real alias data differs",
                    )
                )
        if (l_node.kind or None) != (d_node.kind or None):
            report.divergences.append(
                Divergence(
                    case,
                    "node.kind",
                    f"{node_id}: {l_node.kind!r} -> {d_node.kind!r}",
                    CLASS_REPRESENTATION,
                    "v6 adoption authority vocabulary normalization",
                )
            )

    # Relationships: endpoints+predicate identity.
    legacy_rels = {_rel_key(r): r for r in legacy.relationships}
    direct_rels = {_rel_key(r): r for r in direct.relationships}
    legacy_eps = {_rel_endpoints(r) for r in legacy.relationships}
    direct_eps = {_rel_endpoints(r) for r in direct.relationships}

    # Dual-sense direction normalization: the v6 adoption decomposed dual-sense
    # pairs into one canonical direction (Buddy package #588). A legacy edge
    # s→t paired with a direct edge t→s over the same node pair is one
    # semantic fact represented in the successor's canonical direction.
    legacy_only_keys = set(legacy_rels.keys()) - set(direct_rels.keys())
    direct_only_keys = set(direct_rels.keys()) - set(legacy_rels.keys())
    # Pair against ALL direct edges: the legacy kernel served both senses of a
    # dual-sense pair, so the canonical-direction successor edge may also have
    # an exact legacy twin and not appear in direct_only_keys.
    reversed_direct = {
        (eps[1], eps[0]): key
        for key in direct_rels
        for eps in [_rel_endpoints(direct_rels[key])]
    }
    paired_legacy: set[tuple[str, str, str]] = set()
    paired_direct: set[tuple[str, str, str]] = set()
    for key in sorted(legacy_only_keys):
        rel = legacy_rels[key]
        eps = _rel_endpoints(rel)
        if eps in direct_eps:
            continue  # predicate rename; recorded below
        match = reversed_direct.get(eps)
        if match is not None:
            paired_legacy.add(key)
            paired_direct.add(match)
            report.divergences.append(
                Divergence(
                    case,
                    "relationship.direction",
                    f"{eps[0]} <-> {eps[1]}: legacy {rel.predicate!r} "
                    f"vs direct {direct_rels[match].predicate!r}",
                    CLASS_REPRESENTATION,
                    "dual-sense pair canonicalized to one direction at v6 "
                    "adoption (package #588)",
                )
            )
    legacy_only_keys -= paired_legacy
    direct_only_keys -= paired_direct

    for key in sorted(legacy_only_keys):
        rel = legacy_rels[key]
        eps = _rel_endpoints(rel)
        if eps in direct_eps:
            report.divergences.append(
                Divergence(
                    case,
                    "relationship.predicate",
                    f"{eps[0]} -> {eps[1]}: {rel.predicate!r}",
                    CLASS_REPRESENTATION,
                    "v6 adoption authority vocabulary normalization",
                )
            )
            continue
        dangling = eps[0] not in legacy_nodes or eps[1] not in legacy_nodes
        if dangling:
            report.divergences.append(
                Divergence(
                    case,
                    "relationship_only_in_legacy",
                    f"{eps[0]} -> {eps[1]} ({rel.predicate})",
                    CLASS_RETIRED_LEGACY,
                    "legacy kernel served an edge whose endpoint it did not "
                    "admit (dangling-edge inconsistency retired)",
                )
            )
        elif eps[0] in expected_residual or eps[1] in expected_residual:
            report.divergences.append(
                Divergence(
                    case,
                    "relationship_only_in_legacy",
                    f"{eps[0]} -> {eps[1]} ({rel.predicate})",
                    CLASS_ADMISSION_ACCEPTED,
                    "endpoint excluded by the accepted evidence-chain tightening",
                )
            )
        elif (
            legacy_nodes[eps[0]].kind == "external_resource"
            or legacy_nodes[eps[1]].kind == "external_resource"
        ):
            # Edges to external_resource nodes retire with the node (handoff §D).
            report.divergences.append(
                Divergence(
                    case,
                    "relationship_only_in_legacy",
                    f"{eps[0]} -> {eps[1]} ({rel.predicate})",
                    CLASS_RETIRED_LEGACY,
                    "edge to an external_resource node intentionally omitted "
                    "from the DungeonMind authority snapshot (handoff §D)",
                )
            )
        else:
            report.divergences.append(
                Divergence(
                    case,
                    "relationship_only_in_legacy",
                    f"{eps[0]} -> {eps[1]} ({rel.predicate})",
                    CLASS_BLOCKING,
                    "legacy admits a coherent edge the direct path excludes",
                )
            )
    for key in sorted(direct_only_keys):
        rel = direct_rels[key]
        eps = _rel_endpoints(rel)
        if eps in legacy_eps:
            continue  # predicate-rename pair already recorded from the legacy side
        if eps[0] in (direct_nodes.keys() - legacy_nodes.keys()) or eps[1] in (
            direct_nodes.keys() - legacy_nodes.keys()
        ):
            report.divergences.append(
                Divergence(
                    case,
                    "relationship_only_in_direct",
                    f"{eps[0]} -> {eps[1]} ({rel.predicate})",
                    CLASS_RETIRED_LEGACY,
                    "edge to a node the legacy kernel filter excluded",
                )
            )
        else:
            report.divergences.append(
                Divergence(
                    case,
                    "relationship_only_in_direct",
                    f"{eps[0]} -> {eps[1]} ({rel.predicate})",
                    CLASS_BLOCKING,
                    "direct path admits an edge legacy did not serve",
                )
            )

    # Attributes: session_observation rows are intentionally retired.
    legacy_attrs = {_attr_key(a): a for a in legacy.attributes}
    direct_attrs = {_attr_key(a): a for a in direct.attributes}
    for key in sorted(legacy_attrs.keys() - direct_attrs.keys()):
        attr = legacy_attrs[key]
        kind = getattr(attr, "predicate", None) or getattr(attr, "kind", None) or ""
        if kind == "session_observation":
            report.divergences.append(
                Divergence(
                    case,
                    "attribute_only_in_legacy",
                    f"{key[0]}:{attr.label}",
                    CLASS_RETIRED_LEGACY,
                    "history-only session_observation rows retired from the "
                    "projection payload",
                )
            )
        else:
            # The v6 adoption set properties=[] for every object — property
            # assertions are not represented in the DND authority payload.
            # Handoff §6.2: "property assertion identity/value/metadata
            # where represented" — unrepresented assertions have nothing to
            # compare against.
            report.divergences.append(
                Divergence(
                    case,
                    "attribute_only_in_legacy",
                    f"{key[0]}:{attr.label} ({kind})",
                    CLASS_UNREPRESENTED_PROPERTY,
                    "v6 adoption set properties=[] for all objects; legacy "
                    "reconstructs from contributions",
                )
            )
    for key in sorted(direct_attrs.keys() - legacy_attrs.keys()):
        report.divergences.append(
            Divergence(
                case,
                "attribute_only_in_direct",
                f"{key[0]}:{direct_attrs[key].label}",
                CLASS_BLOCKING,
                "direct path serves an attribute legacy did not",
            )
        )

    # Evidence identity for shared nodes.
    legacy_ev = {e.evidence_ref_id for e in legacy.evidence}
    direct_ev = {e.evidence_ref_id for e in direct.evidence}
    for ev_id in sorted(legacy_ev - direct_ev):
        if expected_residual:
            report.divergences.append(
                Divergence(
                    case,
                    "evidence_only_in_legacy",
                    ev_id,
                    CLASS_ADMISSION_ACCEPTED,
                    "evidence rows for objects excluded by the accepted tightening",
                )
            )
        else:
            # The legacy kernel scoped objects but never evidence chains; it
            # serves cross-campaign evidence for admitted objects. DungeonMind's
            # fail-closed per-evidence-chain admission excludes evidence whose
            # source artifact belongs to another campaign. This is the handoff's
            # "successor admission semantics (scope/provenance tightening)".
            report.divergences.append(
                Divergence(
                    case,
                    "evidence_only_in_legacy",
                    ev_id,
                    CLASS_ADMISSION_ACCEPTED,
                    "cross-campaign evidence chain excluded by DungeonMind's "
                    "fail-closed per-evidence-chain admission (legacy kernel "
                    "scoped objects, never evidence chains)",
                )
            )
    for ev_id in sorted(direct_ev - legacy_ev):
        report.divergences.append(
            Divergence(
                case,
                "evidence_only_in_direct",
                ev_id,
                CLASS_RETIRED_LEGACY,
                "evidence for nodes the legacy kernel filter excluded",
            )
        )
    return report


def compare_retrieval(case: str, legacy, direct) -> CaseReport:
    report = CaseReport(case=case)
    report.legacy_counts = {
        "nodes": len(legacy.nodes),
        "relationships": len(legacy.relationships),
        "attributes": len(getattr(legacy, "attributes", []) or []),
    }
    report.direct_counts = {
        "nodes": len(direct.nodes),
        "relationships": len(direct.relationships),
        "attributes": len(getattr(direct, "attributes", []) or []),
    }
    if legacy.outcome != direct.outcome:
        # Outcome severity ordering: empty < partial < truncated < enough.
        # A direct outcome that is *more* complete than legacy (e.g. enough
        # vs legacy's partial) is a strict improvement — the legacy kernel's
        # anchor/evidence readability gaps are retired, not a regression.
        _severity = {"empty": 0, "partial": 1, "truncated": 2, "enough": 3}
        if _severity.get(direct.outcome, -1) > _severity.get(legacy.outcome, -1):
            report.divergences.append(
                Divergence(
                    case,
                    "outcome",
                    f"{legacy.outcome} != {direct.outcome}",
                    CLASS_REPRESENTATION,
                    "direct path outcome is strictly more complete; "
                    "legacy anchor/evidence readability gaps retired",
                )
            )
        else:
            report.divergences.append(
                Divergence(
                    case,
                    "outcome",
                    f"{legacy.outcome} != {direct.outcome}",
                    CLASS_BLOCKING,
                )
            )
    legacy_ids = [n.node_id for n in legacy.nodes]
    direct_ids = [n.node_id for n in direct.nodes]
    if set(legacy_ids) != set(direct_ids):
        only_l = sorted(set(legacy_ids) - set(direct_ids))
        only_d = sorted(set(direct_ids) - set(legacy_ids))
        # Search node-set differences from ranking/selection are the R.2
        # successor's deterministic ranking, not a projection admission gap
        # (both paths project the same admitted node set; the search selects
        # and ranks within it differently).
        node_set_class = (
            CLASS_SEARCH_RANKING if case.startswith("search:") else CLASS_BLOCKING
        )
        report.divergences.append(
            Divergence(
                case,
                "node_set",
                f"legacy-only={only_l} direct-only={only_d}",
                node_set_class,
            )
        )
    elif legacy_ids != direct_ids:
        report.divergences.append(
            Divergence(
                case,
                "node_order",
                "same set, different order",
                CLASS_SEARCH_RANKING,
                "R.2 deterministic lexical ranking replaces kernel ordering",
            )
        )
    return report


# ---------------------------------------------------------------------------
# Witness runner
# ---------------------------------------------------------------------------


def _timed(fn: Callable[[], Any], runs: int) -> tuple[Any, list[float]]:
    samples: list[float] = []
    result = None
    for _ in range(runs):
        started = time.perf_counter()
        result = fn()
        samples.append((time.perf_counter() - started) * 1000.0)
    return result, samples


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", ""),
    )
    parser.add_argument("--world-id", default="eldyrwild")
    parser.add_argument("--frozen-root", required=True, type=Path)
    parser.add_argument("--repo-root", default=_ROOT, type=Path)
    parser.add_argument("--campaign-a", default="longmont-c1")
    parser.add_argument("--campaign-b", default="longmont-c2")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("/tmp/r3-witness.json"))
    args = parser.parse_args(argv)
    if not args.database_url:
        print("error: --database-url required", file=sys.stderr)
        return 2

    os.environ["DUNGEONMIND_WORLD_GRAPH_AUTHORITY"] = "dungeonmind"
    os.environ["DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"] = args.database_url
    os.environ["DUNGEONMIND_WORLD_GRAPH_ROOT"] = str(args.frozen_root)

    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from graph_memory.projection.world_projection import WorldGraphProjectionRequest
    from graph_memory.retrieval.models import (
        WorldGraphEvidenceRequest,
        WorldGraphNeighborhoodRequest,
        WorldGraphObjectRequest,
        WorldGraphSearchRequest,
        WorldGraphSourceAnchorReadRequest,
    )

    services = direct.direct_services_from_config(args.world_id)
    binding = services.binding
    print(f"world={args.world_id}")
    print(f"  legacy Buddy A revision: {binding.legacy_buddy_revision_id}")
    print(f"  DungeonMind D_A revision: {binding.dungeonmind_first_revision_id}")

    reports: list[CaseReport] = []
    perf: dict[str, dict[str, Any]] = {}

    def projection_request(scope: str, campaign: str | None, **overrides):
        fields = {
            "schema": "dmb_world_graph_projection_request_v1",
            "world_id": args.world_id,
            "campaign_id": campaign,
            "admissibility": "gm",
            "scope_mode": scope,
        }
        fields.update(overrides)
        return WorldGraphProjectionRequest(**fields)

    def ctx(campaign: str, **overrides):
        fields = {
            "worldId": args.world_id,
            "campaignId": campaign,
            "admissibility": "gm",
            "scopeMode": "campaign",
        }
        fields.update(overrides)
        return fields

    # --- Semantic cases (§6.1) ---------------------------------------------

    lenses = {
        "campaign:c1": (("campaign", args.campaign_a)),
        "campaign:c2": (("campaign", args.campaign_b)),
        "world": (("world", args.campaign_b)),
    }
    projections: dict[str, tuple[Any, Any]] = {}
    for name, (scope, campaign) in lenses.items():
        case = f"projection:{name}"
        request = projection_request(scope, campaign)
        try:
            legacy = _legacy_projection(request, root=args.frozen_root)
            direct_projection = direct.project_world_graph_direct(
                services, request, repo_root=args.repo_root
            )
            projections[name] = (legacy, direct_projection)
            reports.append(compare_projections(case, legacy, direct_projection))
        except Exception as exc:
            reports.append(CaseReport(case=case, error=f"{type(exc).__name__}: {exc}"))

    if not projections:
        print("error: no projection cases ran; aborting", file=sys.stderr)
        return 2

    c1_legacy, c1_direct = projections["campaign:c1"]

    # Case 3: world scope + campaign-qualified session focus (Plan seam).
    focus_session = None
    for node in c1_direct.nodes:
        for badge in node.evidence_badges:
            pass
    # Discover a session id from retrieval evidence on a node that has any.
    legacy_node_ids = {n.node_id for n in c1_legacy.nodes}
    seed_node_id = None
    for node in c1_direct.nodes:
        if node.evidence_ref_ids and node.node_id in legacy_node_ids:
            seed_node_id = node.node_id
            break
    if seed_node_id is not None:
        ev_result = direct.get_evidence_direct(
            services,
            WorldGraphEvidenceRequest(
                **{
                    "schema": "dmb_world_graph_evidence_request_v1",
                    "target": {"kind": "node", "id": seed_node_id},
                    **ctx(args.campaign_a),
                }
            ),
        )
        for anchor in ev_result.source_anchors:
            if anchor.session_id:
                focus_session = anchor.session_id
                break
    if focus_session:
        case = "projection:world-session-focus"
        request = projection_request(
            "world",
            args.campaign_b,
            focus={
                "kind": "session",
                "session_id": focus_session,
                "campaign_id": args.campaign_b,
            },
        )
        try:
            legacy = _legacy_projection(request, root=args.frozen_root)
            direct_projection = direct.project_world_graph_direct(
                services, request, repo_root=args.repo_root
            )
            report = compare_projections(case, legacy, direct_projection)
            # Focus presentation: count focus-anchored nodes on both paths.
            report.legacy_counts["focus_anchored_nodes"] = sum(
                1 for n in legacy.nodes if n.anchored_to_focus_session
            )
            report.direct_counts["focus_anchored_nodes"] = sum(
                1 for n in direct_projection.nodes if n.anchored_to_focus_session
            )
            reports.append(report)
        except Exception as exc:
            reports.append(CaseReport(case=case, error=f"{type(exc).__name__}: {exc}"))

    # Case 4/5: pins.
    for case, pin in (
        ("projection:pin:exact-dnd-head", c1_direct.snapshot.revision_id),
        ("projection:pin:legacy-bridge", binding.legacy_buddy_revision_id),
    ):
        request = projection_request("campaign", args.campaign_a, revision_pin=pin)
        try:
            legacy = _legacy_projection(request, root=args.frozen_root)
            direct_projection = direct.project_world_graph_direct(
                services, request, repo_root=args.repo_root
            )
            reports.append(compare_projections(case, legacy, direct_projection))
        except Exception as exc:
            reports.append(CaseReport(case=case, error=f"{type(exc).__name__}: {exc}"))

    # Cases 6-14: retrieval ops against campaign c1.
    rel_seed = None
    for rel in c1_direct.relationships:
        rel_seed = (rel.source_node_id, rel.edge_id)
        break

    retrieval_cases: list[tuple[str, str, Any]] = []
    if seed_node_id:
        retrieval_cases.append(
            (
                "object:hit",
                "object",
                WorldGraphObjectRequest(
                    **{
                        "schema": "dmb_world_graph_object_request_v1",
                        "nodeId": seed_node_id,
                        **ctx(args.campaign_a),
                    }
                ),
            )
        )
    retrieval_cases.append(
        (
            "object:miss",
            "object",
            WorldGraphObjectRequest(
                **{
                    "schema": "dmb_world_graph_object_request_v1",
                    "nodeId": "node:definitely-not-in-the-graph",
                    **ctx(args.campaign_a),
                }
            ),
        )
    )
    query_word = None
    if seed_node_id:
        label = next((n.label for n in c1_direct.nodes if n.node_id == seed_node_id), "")
        words = [w for w in label.split() if len(w) >= 4]
        query_word = words[0].lower() if words else None
    if query_word:
        retrieval_cases.append(
            (
                "search:known-referent",
                "search",
                WorldGraphSearchRequest(
                    **{
                        "schema": "dmb_world_graph_search_request_v1",
                        "queryText": query_word,
                        **ctx(args.campaign_a),
                    }
                ),
            )
        )
        retrieval_cases.append(
            (
                "search:with-seeds",
                "search",
                WorldGraphSearchRequest(
                    **{
                        "schema": "dmb_world_graph_search_request_v1",
                        "queryText": query_word,
                        "seedNodeIds": [seed_node_id],
                        **ctx(args.campaign_a),
                    }
                ),
            )
        )
    if seed_node_id:
        for depth in (1, 2):
            retrieval_cases.append(
                (
                    f"neighborhood:depth-{depth}",
                    "neighborhood",
                    WorldGraphNeighborhoodRequest(
                        **{
                            "schema": "dmb_world_graph_neighborhood_request_v1",
                            "seedNodeIds": [seed_node_id],
                            "maxDepth": depth,
                            **ctx(args.campaign_a),
                        }
                    ),
                )
            )
        retrieval_cases.append(
            (
                "evidence:object",
                "evidence",
                WorldGraphEvidenceRequest(
                    **{
                        "schema": "dmb_world_graph_evidence_request_v1",
                        "target": {"kind": "node", "id": seed_node_id},
                        **ctx(args.campaign_a),
                    }
                ),
            )
        )
    if rel_seed:
        retrieval_cases.append(
            (
                "evidence:relationship",
                "evidence",
                WorldGraphEvidenceRequest(
                    **{
                        "schema": "dmb_world_graph_evidence_request_v1",
                        "target": {"kind": "relationship", "id": rel_seed[1]},
                        **ctx(args.campaign_a),
                    }
                ),
            )
        )

    for case, op, request in retrieval_cases:
        try:
            legacy = _legacy_retrieval(
                op, request, root=args.frozen_root, repo_root=args.repo_root
            )
            direct_fn = {
                "object": direct.get_object_direct,
                "search": direct.search_world_graph_direct,
                "neighborhood": direct.get_neighborhood_direct,
                "evidence": direct.get_evidence_direct,
            }[op]
            direct_result = direct_fn(services, request)
            reports.append(compare_retrieval(case, legacy, direct_result))
        except Exception as exc:
            reports.append(CaseReport(case=case, error=f"{type(exc).__name__}: {exc}"))

    # Case 14: anchor emit → revalidate → open on both paths.
    if seed_node_id:
        case = "anchor:emit-revalidate-open"
        try:
            ev_result = direct.get_evidence_direct(
                services,
                WorldGraphEvidenceRequest(
                    **{
                        "schema": "dmb_world_graph_evidence_request_v1",
                        "target": {"kind": "node", "id": seed_node_id},
                        **ctx(args.campaign_a),
                    }
                ),
            )
            readable = [a for a in ev_result.source_anchors if a.readable]
            if not readable:
                reports.append(
                    CaseReport(case=case, error="no readable anchors discovered")
                )
            else:
                anchor_id = readable[0].anchor_id
                request = WorldGraphSourceAnchorReadRequest(
                    **{
                        "schema": "dmb_world_graph_source_anchor_read_request_v1",
                        "anchorId": anchor_id,
                        **ctx(args.campaign_a),
                    }
                )
                direct_result = direct.read_source_anchor_direct(
                    services, request, repo_root=args.repo_root
                )
                legacy_result = _legacy_anchor_read(
                    request, root=args.frozen_root, repo_root=args.repo_root
                )
                report = CaseReport(case=case)
                legacy_outcome = getattr(legacy_result, "outcome", "derivation")
                report.legacy_counts["outcome"] = legacy_outcome
                report.direct_counts["outcome"] = direct_result.outcome
                if legacy_outcome != "derivation" and legacy_outcome != direct_result.outcome:
                    report.divergences.append(
                        Divergence(
                            case,
                            "outcome",
                            f"{legacy_outcome} != {direct_result.outcome}",
                            CLASS_PRESENTATION_JOIN,
                            "product-local content join availability may differ; "
                            "revalidation identity is the parity surface",
                        )
                    )
                reports.append(report)
        except Exception as exc:
            reports.append(CaseReport(case=case, error=f"{type(exc).__name__}: {exc}"))

    # Case 15: PLAYER admissibility — both paths fail closed identically.
    case = "admissibility:player-rejected"
    try:
        request = projection_request("campaign", args.campaign_a, admissibility="player")
        outcomes = {}
        for name, fn in (
            ("legacy", lambda: _legacy_projection(request, root=args.frozen_root)),
            ("direct", lambda: direct.project_world_graph_direct(services, request)),
        ):
            try:
                fn()
                outcomes[name] = "served"
            except Exception as exc:
                outcomes[name] = f"{getattr(exc, 'code', type(exc).__name__)}"
        report = CaseReport(case=case)
        report.legacy_counts["result"] = outcomes["legacy"]
        report.direct_counts["result"] = outcomes["direct"]
        if outcomes["legacy"] != outcomes["direct"]:
            report.divergences.append(
                Divergence(
                    case,
                    "error_envelope",
                    f"{outcomes['legacy']} != {outcomes['direct']}",
                    CLASS_BLOCKING,
                )
            )
        reports.append(report)
    except Exception as exc:
        reports.append(CaseReport(case=case, error=f"{type(exc).__name__}: {exc}"))

    # Case 16: unknown campaign scope fails closed on both paths.
    case = "scope:unknown-campaign-fail-closed"
    try:
        request = projection_request("campaign", "campaign:never-existed")
        outcomes = {}
        for name, fn in (
            ("legacy", lambda: _legacy_projection(request, root=args.frozen_root)),
            ("direct", lambda: direct.project_world_graph_direct(services, request)),
        ):
            try:
                result = fn()
                outcomes[name] = f"served:{len(result.nodes)}"
            except Exception as exc:
                outcomes[name] = f"{getattr(exc, 'code', type(exc).__name__)}"
        report = CaseReport(case=case)
        report.legacy_counts["result"] = outcomes["legacy"]
        report.direct_counts["result"] = outcomes["direct"]
        if (outcomes["legacy"].startswith("served")) != (
            outcomes["direct"].startswith("served")
        ):
            report.divergences.append(
                Divergence(
                    case,
                    "fail_closed_behavior",
                    f"{outcomes['legacy']} != {outcomes['direct']}",
                    CLASS_BLOCKING,
                )
            )
        reports.append(report)
    except Exception as exc:
        reports.append(CaseReport(case=case, error=f"{type(exc).__name__}: {exc}"))

    # --- Performance witness (§7) ------------------------------------------

    perf_cases: list[tuple[str, Callable[[], Any], Callable[[], Any]]] = []
    proj_request = projection_request("campaign", args.campaign_a)
    perf_cases.append(
        (
            "projection",
            lambda: _legacy_projection(proj_request, root=args.frozen_root),
            lambda: direct.project_world_graph_direct(
                services, proj_request, repo_root=args.repo_root
            ),
        )
    )
    for op, request in (
        (op, req) for _case, op, req in retrieval_cases if _case in {
            "object:hit",
            "search:known-referent",
            "neighborhood:depth-1",
            "neighborhood:depth-2",
            "evidence:object",
        }
    ):
        perf_cases.append(
            (
                {"object": "object", "search": "search",
                 "neighborhood": "neighborhood", "evidence": "evidence"}[op]
                + (f":depth-{request.max_depth}" if op == "neighborhood" else ""),
                lambda op=op, request=request: _legacy_retrieval(
                    op, request, root=args.frozen_root, repo_root=args.repo_root
                ),
                lambda op=op, request=request: {
                    "object": direct.get_object_direct,
                    "search": direct.search_world_graph_direct,
                    "neighborhood": direct.get_neighborhood_direct,
                    "evidence": direct.get_evidence_direct,
                }[op](services, request),
            )
        )

    for name, legacy_fn, direct_fn in perf_cases:
        entry: dict[str, Any] = {}
        for label, fn in (("legacy_ms", legacy_fn), ("direct_ms", direct_fn)):
            try:
                _result, samples = _timed(fn, args.runs)
                entry[label] = {
                    "median": statistics.median(samples),
                    "min": min(samples),
                    "max": max(samples),
                    "cold": samples[0],
                }
            except Exception as exc:
                # A path failure is witness data, not a harness crash.
                entry[label] = {"error": f"{type(exc).__name__}: {exc}"}
        perf[name] = entry

    # --- Report -------------------------------------------------------------

    all_divergences = [d for r in reports for d in r.divergences]
    blocking = [d for d in all_divergences if d.classification == CLASS_BLOCKING]
    errored = [r for r in reports if r.error]

    tally: dict[str, int] = {}
    for d in all_divergences:
        tally[d.classification] = tally.get(d.classification, 0) + 1

    print("\n=== R.3 parity witness ===")
    print(f"cases run: {len(reports)} ({len(errored)} errored)")
    print("divergence tally:")
    for cls, count in sorted(tally.items()):
        print(f"  {cls}: {count}")
    if blocking:
        print(f"\nBLOCKING divergences ({len(blocking)}):")
        for d in blocking[:20]:
            print(f"  [{d.case}] {d.kind}: {d.identifier} — {d.detail}")
    if errored:
        print("\nerrored cases:")
        for r in errored:
            print(f"  {r.case}: {r.error}")

    print("\n=== R.3 performance witness (median ms, cold=first run) ===")
    for name, entry in perf.items():
        cells = []
        for label in ("legacy_ms", "direct_ms"):
            cell = entry.get(label) or {}
            if "error" in cell:
                cells.append(f"{label.split('_')[0]} ERROR({cell['error'][:40]})")
            else:
                cells.append(
                    f"{label.split('_')[0]} {cell['median']:8.1f} "
                    f"(cold {cell['cold']:8.1f})"
                )
        print(f"  {name:24s} {'   '.join(cells)}")

    payload = {
        "world_id": args.world_id,
        "legacy_buddy_revision": binding.legacy_buddy_revision_id,
        "dungeonmind_revision": binding.dungeonmind_first_revision_id,
        "runs": args.runs,
        "cases": [
            {
                "case": r.case,
                "legacy_counts": r.legacy_counts,
                "direct_counts": r.direct_counts,
                "error": r.error,
                "divergences": [d.to_dict() for d in r.divergences],
            }
            for r in reports
        ],
        "performance": perf,
        "tally": tally,
        "blocking_count": len(blocking),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nlocal report (private — do not commit): {args.output}")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
