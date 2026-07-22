#!/usr/bin/env python3
"""Benchmark World Graph projection / catalog load stages for storage decisions.

Writes a JSON report under evals/graph_memory_layer/artifacts/projection_load_benchmark/
and prints a go/no-go summary for PostgreSQL migration.

Never prints corpus prose.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))


@dataclass
class TrialResult:
    name: str
    elapsed_ms: float
    stages: list[dict[str, Any]]
    counts: dict[str, int]
    contribution_cache_hits: int
    contribution_cache_misses: int
    contribution_load_ms: float
    payload_bytes: int | None = None
    projection_cache_hits: int | None = None
    projection_cache_misses: int | None = None
    meta: dict[str, Any] | None = None


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"n": 0, "p50_ms": 0.0, "p95_ms": 0.0, "mean_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0}
    return {
        "n": len(values),
        "p50_ms": round(_percentile(values, 0.50), 3),
        "p95_ms": round(_percentile(values, 0.95), 3),
        "mean_ms": round(statistics.fmean(values), 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def _capture_trace(pipeline: str, fn) -> tuple[Any, dict[str, Any]]:
    from graph_memory.projection_load_telemetry import (
        emit_projection_load_trace,
        projection_load_trace,
    )

    with projection_load_trace(pipeline, emit=False) as trace:
        result = fn()
        payload = emit_projection_load_trace(trace, outcome="ok")
    return result, payload


def _stage_share(payload: dict[str, Any]) -> dict[str, float]:
    total = float(payload.get("elapsed_ms") or 0.0)
    if total <= 0:
        return {}
    shares: dict[str, float] = {}
    for stage in payload.get("stages") or []:
        name = str(stage.get("stage") or "")
        if not name:
            continue
        shares[name] = round(float(stage.get("elapsed_ms") or 0.0) / total, 4)
    return shares


def run_benchmark(
    *,
    world_root: Path,
    world_id: str,
    campaign_id: str,
    session_id: str,
    trials: int,
) -> dict[str, Any]:
    from apps.live_control_server.services.graph_ingest_run_registry import (
        discover_graph_ingest_runs,
    )
    from apps.live_control_server.services.world_graph_recap_projection import (
        build_world_graph_recap_projection_payload,
    )
    from graph_memory.kernel.world_projection import project_world_graph
    from graph_memory.kernel.world_retrieval import search_campaign_graph
    from graph_memory.projection.world_projection import (
        WorldGraphProjectionFocus,
        WorldGraphProjectionRequest,
    )
    from graph_memory.retrieval.models import (
        RETRIEVAL_SEARCH_REQUEST_SCHEMA,
        WorldGraphSearchRequest,
    )
    from graph_memory.world_projection_cache import (
        clear_projection_cache,
        projection_cache_stats,
    )
    from graph_memory.world_supergraph.storage import load_current_world_graph

    clear_projection_cache()

    # Cardinality snapshot (no prose).
    _head, revision, store = load_current_world_graph(world_root, world_id)
    graph_json = (
        world_root
        / "graph_memory"
        / "worlds"
        / world_id
        / "revisions"
        / revision.revision_id
        / "graph.json"
    )
    contribution_dir = (
        world_root / "graph_memory" / "worlds" / world_id / "contributions"
    )
    cardinality = {
        "revision_id": revision.revision_id,
        "node_count": len(store.nodes),
        "edge_count": len(store.edges),
        "assertion_support_count": len(getattr(store, "assertion_support", {}) or {}),
        "graph_json_bytes": graph_json.stat().st_size if graph_json.is_file() else None,
        "contribution_file_count": (
            len(list(contribution_dir.glob("*.json"))) if contribution_dir.is_dir() else 0
        ),
    }

    request = WorldGraphProjectionRequest(
        schema="dmb_world_graph_projection_request_v1",
        world_id=world_id,
        campaign_id=campaign_id,
        focus=WorldGraphProjectionFocus(kind="session", session_id=session_id),
        admissibility="gm",
        scope_mode="campaign",
    )

    cold_projection: list[TrialResult] = []
    warm_projection: list[TrialResult] = []
    recap_trials: list[TrialResult] = []
    catalog_trials: list[TrialResult] = []
    search_trials: list[TrialResult] = []

    # Cold projection trials (clear process cache each time).
    for _ in range(trials):
        clear_projection_cache()
        started = time.perf_counter()

        def _project():
            return project_world_graph(world_root, request)

        projection, payload = _capture_trace("benchmark_world_projection", _project)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        serialized = projection.model_dump_json().encode("utf-8")
        stats = projection_cache_stats()
        cold_projection.append(
            TrialResult(
                name="projection_cold",
                elapsed_ms=elapsed_ms,
                stages=list(payload.get("stages") or []),
                counts=dict(payload.get("counts") or {}),
                contribution_cache_hits=int(payload.get("contribution_cache_hits") or 0),
                contribution_cache_misses=int(payload.get("contribution_cache_misses") or 0),
                contribution_load_ms=float(payload.get("contribution_load_ms") or 0.0),
                payload_bytes=len(serialized),
                projection_cache_hits=stats["hits"],
                projection_cache_misses=stats["misses"],
                meta={"stage_share": _stage_share(payload)},
            )
        )

    # Warm projection via service-layer cache (ledger-fingerprinted).
    clear_projection_cache()
    from apps.live_control_server.services.world_graph_projection import (
        project_world_graph as service_project_world_graph,
    )

    os.environ["DMB_WORLD_GRAPH_PROJECTION_CACHE"] = "1"
    service_project_world_graph(request, root=world_root)  # seed
    for _ in range(trials):
        started = time.perf_counter()

        def _project_warm():
            return service_project_world_graph(request, root=world_root)

        projection, payload = _capture_trace("benchmark_world_projection_warm", _project_warm)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        stats = projection_cache_stats()
        warm_projection.append(
            TrialResult(
                name="projection_warm",
                elapsed_ms=elapsed_ms,
                stages=list(payload.get("stages") or []),
                counts=dict(payload.get("counts") or {}),
                contribution_cache_hits=int(payload.get("contribution_cache_hits") or 0),
                contribution_cache_misses=int(payload.get("contribution_cache_misses") or 0),
                contribution_load_ms=float(payload.get("contribution_load_ms") or 0.0),
                payload_bytes=len(projection.model_dump_json().encode("utf-8")),
                projection_cache_hits=stats["hits"],
                projection_cache_misses=stats["misses"],
                meta={"stage_share": _stage_share(payload)},
            )
        )

    # Recap projection.
    for _ in range(max(1, trials // 2)):
        clear_projection_cache()
        started = time.perf_counter()

        def _recap():
            return build_world_graph_recap_projection_payload(request, root=world_root)

        payload_obj, payload = _capture_trace("benchmark_recap_projection", _recap)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        recap_trials.append(
            TrialResult(
                name="recap_projection",
                elapsed_ms=elapsed_ms,
                stages=list(payload.get("stages") or []),
                counts=dict(payload.get("counts") or {}),
                contribution_cache_hits=int(payload.get("contribution_cache_hits") or 0),
                contribution_cache_misses=int(payload.get("contribution_cache_misses") or 0),
                contribution_load_ms=float(payload.get("contribution_load_ms") or 0.0),
                payload_bytes=len(json.dumps(payload_obj).encode("utf-8")),
                meta={"stage_share": _stage_share(payload)},
            )
        )

    # Catalog discovery.
    for _ in range(max(1, trials // 2)):
        started = time.perf_counter()

        def _catalog():
            return discover_graph_ingest_runs(
                REPO_ROOT,
                require_preview_union_store=True,
                include_eval_roots=False,
            )

        runs, payload = _capture_trace("benchmark_catalog", _catalog)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        catalog_trials.append(
            TrialResult(
                name="catalog_discovery",
                elapsed_ms=elapsed_ms,
                stages=list(payload.get("stages") or []),
                counts=dict(payload.get("counts") or {}),
                contribution_cache_hits=0,
                contribution_cache_misses=0,
                contribution_load_ms=0.0,
                payload_bytes=None,
                meta={
                    "run_count": len(runs),
                    "stage_share": _stage_share(payload),
                },
            )
        )

    # Search (full projection then rank).
    for _ in range(max(1, trials // 2)):
        clear_projection_cache()
        started = time.perf_counter()
        search_req = WorldGraphSearchRequest.model_validate(
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": campaign_id,
                "focus": {"kind": "session", "sessionId": session_id},
                "admissibility": "gm",
                "queryText": "stafl",
                "scopeMode": "campaign",
            }
        )

        def _search():
            return search_campaign_graph(world_root, search_req)

        result, payload = _capture_trace("benchmark_search_campaign_graph", _search)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        search_trials.append(
            TrialResult(
                name="search_campaign_graph",
                elapsed_ms=elapsed_ms,
                stages=list(payload.get("stages") or []),
                counts={
                    "matched_nodes": len(getattr(result, "nodes", []) or []),
                    **dict(payload.get("counts") or {}),
                },
                contribution_cache_hits=int(payload.get("contribution_cache_hits") or 0),
                contribution_cache_misses=int(payload.get("contribution_cache_misses") or 0),
                contribution_load_ms=float(payload.get("contribution_load_ms") or 0.0),
                meta={"stage_share": _stage_share(payload)},
            )
        )

    def _aggregate(trials_list: list[TrialResult]) -> dict[str, Any]:
        if not trials_list:
            return {}
        first = trials_list[0]
        contrib_misses = [t.contribution_cache_misses for t in trials_list]
        contrib_hits = [t.contribution_cache_hits for t in trials_list]
        stage_totals: dict[str, list[float]] = {}
        for trial in trials_list:
            for stage in trial.stages:
                name = str(stage.get("stage") or "")
                if not name:
                    continue
                stage_totals.setdefault(name, []).append(float(stage.get("elapsed_ms") or 0.0))
        return {
            "latency": _summarize([t.elapsed_ms for t in trials_list]),
            "payload_bytes_p50": (
                int(statistics.median([t.payload_bytes for t in trials_list if t.payload_bytes]))
                if any(t.payload_bytes for t in trials_list)
                else None
            ),
            "contribution_cache_misses_mean": round(statistics.fmean(contrib_misses), 3),
            "contribution_cache_hits_mean": round(statistics.fmean(contrib_hits), 3),
            "contribution_load_ms_mean": round(
                statistics.fmean([t.contribution_load_ms for t in trials_list]), 3
            ),
            "stage_ms_mean": {
                name: round(statistics.fmean(vals), 3) for name, vals in sorted(stage_totals.items())
            },
            "sample_counts": first.counts,
            "sample_stage_share": (first.meta or {}).get("stage_share"),
        }

    cold_agg = _aggregate(cold_projection)
    warm_agg = _aggregate(warm_projection)
    recap_agg = _aggregate(recap_trials)
    catalog_agg = _aggregate(catalog_trials)
    search_agg = _aggregate(search_trials)

    cold_p95 = float((cold_agg.get("latency") or {}).get("p95_ms") or 0.0)
    stage_mean = cold_agg.get("stage_ms_mean") or {}
    load_ms = float(stage_mean.get("load_revision_context") or 0.0)
    build_ms = float(stage_mean.get("build_projection_payload") or 0.0)
    contrib_load_ms = float(cold_agg.get("contribution_load_ms_mean") or 0.0)
    storage_like_ms = load_ms + contrib_load_ms
    storage_share = (storage_like_ms / cold_p95) if cold_p95 > 0 else 0.0
    build_share = (build_ms / cold_p95) if cold_p95 > 0 else 0.0

    # Decision gate from the plan.
    postgres_candidate = (
        cold_p95 > 500.0
        and storage_share >= 0.80
        and int(cardinality.get("node_count") or 0) >= 2000
    )
    optimize_code_first = not postgres_candidate
    decision = {
        "postgres_spike_justified": postgres_candidate,
        "recommended_path": (
            "prototype_postgresql_compatibility_spike"
            if postgres_candidate
            else "optimize_file_backed_projection_path"
        ),
        "reasons": [
            f"cold_projection_p95_ms={cold_p95:.1f} (gate >500)",
            f"storage_like_share={storage_share:.3f} (load_revision+contribution_loads; gate >=0.80)",
            f"build_projection_share={build_share:.3f}",
            f"node_count={cardinality.get('node_count')} (gate >=2000 for postgres)",
            f"warm_projection_p50_ms={(warm_agg.get('latency') or {}).get('p50_ms')}",
            f"recap_p50_ms={(recap_agg.get('latency') or {}).get('p50_ms')}",
            f"catalog_p50_ms={(catalog_agg.get('latency') or {}).get('p50_ms')}",
        ],
        "optimize_code_first": optimize_code_first,
    }

    return {
        "schema": "dmb_projection_load_benchmark_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "world_root": str(world_root),
        "world_id": world_id,
        "campaign_id": campaign_id,
        "session_id": session_id,
        "trials": trials,
        "cardinality": cardinality,
        "aggregates": {
            "projection_cold": cold_agg,
            "projection_warm": warm_agg,
            "recap_projection": recap_agg,
            "catalog_discovery": catalog_agg,
            "search_campaign_graph": search_agg,
        },
        "trials_raw": {
            "projection_cold": [asdict(t) for t in cold_projection],
            "projection_warm": [asdict(t) for t in warm_projection],
            "recap_projection": [asdict(t) for t in recap_trials],
            "catalog_discovery": [asdict(t) for t in catalog_trials],
            "search_campaign_graph": [asdict(t) for t in search_trials],
        },
        "decision": decision,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--world-root",
        type=Path,
        default=REPO_ROOT / "out",
        help="World graph root (contains graph_memory/worlds/...)",
    )
    parser.add_argument("--world-id", default="eldyrwild")
    parser.add_argument("--campaign-id", default="longmont-c1")
    parser.add_argument("--session-id", default="session-6")
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT
        / "evals"
        / "graph_memory_layer"
        / "artifacts"
        / "projection_load_benchmark",
    )
    args = parser.parse_args(argv)

    report = run_benchmark(
        world_root=args.world_root.resolve(),
        world_id=args.world_id,
        campaign_id=args.campaign_id,
        session_id=args.session_id,
        trials=max(1, args.trials),
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_json = args.out_dir / f"projection_load_benchmark--{stamp}.json"
    latest = args.out_dir / "latest.json"
    decision_md = args.out_dir / "POSTGRES-GO-NO-GO.md"
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    decision = report["decision"]
    card = report["cardinality"]
    cold = report["aggregates"]["projection_cold"]["latency"]
    warm = report["aggregates"]["projection_warm"]["latency"]
    lines = [
        "# PostgreSQL go / no-go — graph load benchmark",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Cardinality",
        "",
        f"- revision: `{card.get('revision_id')}`",
        f"- nodes: `{card.get('node_count')}`",
        f"- edges: `{card.get('edge_count')}`",
        f"- assertion_support: `{card.get('assertion_support_count')}`",
        f"- graph.json bytes: `{card.get('graph_json_bytes')}`",
        f"- contribution files: `{card.get('contribution_file_count')}`",
        "",
        "## Latency",
        "",
        f"- cold projection p50/p95: `{cold.get('p50_ms')}` / `{cold.get('p95_ms')}` ms",
        f"- warm projection p50/p95: `{warm.get('p50_ms')}` / `{warm.get('p95_ms')}` ms",
        f"- recap p50: `{(report['aggregates']['recap_projection'].get('latency') or {}).get('p50_ms')}` ms",
        f"- catalog p50: `{(report['aggregates']['catalog_discovery'].get('latency') or {}).get('p50_ms')}` ms",
        f"- search p50: `{(report['aggregates']['search_campaign_graph'].get('latency') or {}).get('p50_ms')}` ms",
        "",
        "## Decision",
        "",
        f"- **recommended_path:** `{decision['recommended_path']}`",
        f"- **postgres_spike_justified:** `{decision['postgres_spike_justified']}`",
        "",
        "Reasons:",
        "",
    ]
    for reason in decision["reasons"]:
        lines.append(f"- {reason}")
    lines.extend(
        [
            "",
            "## Gate (from plan)",
            "",
            "Proceed to PostgreSQL design only if measured p95 projection is >500ms,",
            "≥80% of that time is store load + contribution file fan-out, and projected",
            "cardinality is heading past ~2000 nodes (or contribution fan-out dominates).",
            "Otherwise keep optimizing the file-backed projection path.",
            "",
            f"Full JSON: `{out_json.relative_to(REPO_ROOT)}`",
            "",
        ]
    )
    decision_md.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"out_json": str(out_json), "decision": decision}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
