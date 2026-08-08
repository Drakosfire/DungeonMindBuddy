#!/usr/bin/env python3
"""E1: world-fed known-entity registry experiment.

Feeds world head-revision nodes into the deterministic known-entity registry
via ``CategoryGraphExtractionOptions.extra_known_entities`` and measures three
arm configurations against the party-only control (A0, re-scored from stored
runs — no new LLM calls):

- A1: concrete kinds (npc/location/group/faction/item/creature), same campaign
- A2: concrete kinds, all campaigns
- A3: all kinds (incl. threads/mysteries/events), all campaigns

Test beds:
- s23: Session 23 stored run, gold-scored via ``compare_parts`` (recall delta,
  extras suppression, E4 alias audit).
- s25: Session 25 stored run, deterministic metrics only (suppression drops,
  canonical reuse, novelty preservation, cost) — no gold exists.

Usage:

    uv run python -m evals.graph_memory_layer.run_world_fed_registry_experiment \
        --beds s23,s25 --arms a1,a2,a3 --trials 3

    # Control re-score only (no LLM calls):
    uv run python -m evals.graph_memory_layer.run_world_fed_registry_experiment \
        --beds s23,s25 --arms a1 --trials 1 --control-only
"""
from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from evals.graph_memory_layer.live_vs_gold_compare import (
    compare_parts,
    parts_from_raw_graph,
)
from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import (
    load_gold_candidate_graph_dict,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    CategoryGraphExtractionResult,
    OpenAICategoryGraphPassClient,
    run_category_pipeline,
)
from src.graph_memory.extraction.known_entity_registry import (
    WORLD_ENTITY_DEFAULT_KINDS,
    KnownEntity,
    build_known_entity_registry,
    extend_known_entity_registry,
    known_entities_from_world_graph,
    normalize_match_surface,
)

WORLD_HEAD_PATH = Path("out/graph_memory/worlds/eldyrwild/head.json")


@dataclass(frozen=True)
class Bed:
    key: str
    campaign_id: str
    session_id: str
    session_number: int
    stored_run_dir: Path
    has_gold: bool


BEDS: dict[str, Bed] = {
    "s23": Bed(
        key="s23",
        campaign_id="longmont-c2",
        session_id="session-23",
        session_number=23,
        stored_run_dir=Path("out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z"),
        has_gold=True,
    ),
    "s25": Bed(
        key="s25",
        campaign_id="longmont-c2",
        session_id="session-25",
        session_number=25,
        stored_run_dir=Path("out/graph_memory/runs/longmont-c2/session-25/20260808T010341Z"),
        has_gold=False,
    ),
}

ARM_SPECS: dict[str, dict[str, Any]] = {
    "a1": {
        "description": "concrete kinds, same campaign",
        "include_kinds": WORLD_ENTITY_DEFAULT_KINDS,
        "scope_to_campaign": True,
    },
    "a2": {
        "description": "concrete kinds, all campaigns",
        "include_kinds": WORLD_ENTITY_DEFAULT_KINDS,
        "scope_to_campaign": False,
    },
    "a3": {
        "description": "all kinds (incl. threads/mysteries/events), all campaigns",
        "include_kinds": None,
        "scope_to_campaign": False,
    },
}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_world_graph(head_path: Path = WORLD_HEAD_PATH) -> dict[str, Any]:
    """Resolve the world head pointer to the head revision's graph payload."""
    pointer = json.loads(head_path.read_text(encoding="utf-8"))
    revision_id = pointer["head_revision_id"]
    graph_path = head_path.parent / "revisions" / revision_id / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["_resolved_revision_id"] = revision_id
    return graph


def build_arm_extras(
    arm: str,
    world_graph: Mapping[str, Any],
    campaign_id: str,
) -> list[KnownEntity]:
    spec = ARM_SPECS[arm]
    scopes = frozenset({campaign_id}) if spec["scope_to_campaign"] else None
    return known_entities_from_world_graph(
        world_graph,
        include_kinds=spec["include_kinds"],
        campaign_scopes=scopes,
    )


def _registry_size(bed: Bed, extras: Sequence[KnownEntity]) -> dict[str, int]:
    base = build_known_entity_registry(bed.campaign_id, bed.session_number)
    merged = extend_known_entity_registry(base, extras)
    return {
        "base_entities": len(base.entities),
        "extra_offered": len(extras),
        "extra_added": int(merged.diagnostics.get("extra_entities_added") or 0),
        "registry_total": len(merged.entities),
    }


def _world_surface_norms(world_graph: Mapping[str, Any]) -> set[str]:
    surfaces: set[str] = set()
    raw_nodes = world_graph.get("nodes")
    rows = raw_nodes.values() if isinstance(raw_nodes, Mapping) else (raw_nodes or [])
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        label = str(row.get("label") or "")
        if label:
            surfaces.add(normalize_match_surface(label))
        for alias in row.get("aliases") or []:
            if isinstance(alias, str) and alias.strip():
                surfaces.add(normalize_match_surface(alias))
    for surface in (world_graph.get("aliases") or {}):
        if isinstance(surface, str) and surface.strip():
            surfaces.add(normalize_match_surface(surface))
    return {s for s in surfaces if s}


def _token_totals(pass_telemetry: Mapping[str, Any]) -> dict[str, int]:
    totals = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    for entry in pass_telemetry.values():
        usage = (entry or {}).get("usage") or {}
        for key in totals:
            val = usage.get(key)
            if isinstance(val, (int, float)):
                totals[key] += int(val)
    return totals


def _deterministic_metrics(
    *,
    candidate_graph: Mapping[str, Any],
    known_entity_mentions: Mapping[str, Any],
    consolidation_diagnostics: Mapping[str, Any] | None,
    world_graph: Mapping[str, Any],
) -> dict[str, Any]:
    nodes = [n for n in (candidate_graph.get("nodes") or []) if isinstance(n, Mapping)]
    edges = [e for e in (candidate_graph.get("edges") or []) if isinstance(e, Mapping)]
    mentions = [
        m for m in (known_entity_mentions.get("mentions") or []) if isinstance(m, Mapping)
    ]
    mention_ids = {str(m.get("canonical_entity_id")) for m in mentions}
    world_ids = set()
    raw_nodes = world_graph.get("nodes")
    rows = raw_nodes.values() if isinstance(raw_nodes, Mapping) else (raw_nodes or [])
    for row in rows:
        if isinstance(row, Mapping) and row.get("node_id"):
            world_ids.add(str(row["node_id"]))

    world_norms = _world_surface_norms(world_graph)
    novel_labels = sorted(
        {
            str(n.get("label"))
            for n in nodes
            if str(n.get("label") or "").strip()
            and normalize_match_surface(str(n.get("label"))) not in world_norms
        }
    )

    ke_diag = (consolidation_diagnostics or {}).get("known_entity_mentions") or {}
    dropped = ke_diag.get("dropped_duplicate_node_ids") or []
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "mention_count": len(mentions),
        "mention_distinct_ids": len(mention_ids),
        "world_canonical_reuse": len(mention_ids & world_ids),
        "novel_node_count": len(novel_labels),
        "novel_node_labels": novel_labels,
        "suppressed_duplicate_nodes": len(dropped),
        "suppressed_duplicate_node_ids": sorted(str(d) for d in dropped),
        "mention_evidence_attachments": int(
            ke_diag.get("mention_evidence_attachments") or 0
        ),
    }


def _gold_metrics(
    candidate_graph: Mapping[str, Any],
    gold_parts: Mapping[str, Any],
) -> dict[str, Any]:
    report = compare_parts(parts_from_raw_graph(candidate_graph), gold_parts)
    coverage = report.get("coverage") or {}
    scores = report.get("scores") or {}
    matched_nodes = set(coverage.get("matched_nodes") or [])
    extra_nodes = coverage.get("extra_candidate_nodes") or []
    alias_diag = (report.get("diagnostics") or {}).get("label_alias") or {}
    return {
        "node_recall": scores.get("node_recall"),
        "edge_recall": scores.get("edge_recall"),
        "matched_nodes": len(matched_nodes),
        "matched_edges": len(coverage.get("matched_edges") or []),
        "candidate_nodes_total": coverage.get("candidate_nodes_total"),
        "extra_nodes_vs_gold": len(extra_nodes),
        "alias_assisted_node_matches": len(
            alias_diag.get("alias_assisted_node_matches") or []
        ),
    }


def control_metrics(bed: Bed, world_graph: Mapping[str, Any]) -> dict[str, Any]:
    """A0: re-score the stored party-only run without new LLM calls."""
    run_dir = bed.stored_run_dir
    candidate = json.loads((run_dir / "candidate_graph.json").read_text(encoding="utf-8"))
    mentions_path = run_dir / "known_entity_mentions.json"
    mentions = (
        json.loads(mentions_path.read_text(encoding="utf-8"))
        if mentions_path.exists()
        else {"mentions": []}
    )
    metrics = _deterministic_metrics(
        candidate_graph=candidate,
        known_entity_mentions=mentions,
        consolidation_diagnostics=None,
        world_graph=world_graph,
    )
    manifest_path = run_dir / "graph_ingest_run_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cost = (manifest.get("extraction") or {}).get("total_cost_usd") or manifest.get(
            "total_cost_usd"
        )
        metrics["total_cost_usd"] = cost
    if bed.has_gold:
        metrics["gold"] = _gold_metrics(candidate, parts_from_raw_graph(load_gold_candidate_graph_dict()))
    return metrics


def run_arm_trial(
    *,
    bed: Bed,
    arm: str,
    trial_index: int,
    out_dir: Path,
    model_id: str,
    reasoning_effort: str | None,
    world_graph: Mapping[str, Any],
) -> dict[str, Any]:
    span_index = json.loads(
        (bed.stored_run_dir / "source_span_index.json").read_text(encoding="utf-8")
    )
    # v1 span indexes carry line ranges only; slice text from the same
    # normalized recap the index was packaged with.
    source_text = (bed.stored_run_dir / "normalized_recap_source.md").read_text(
        encoding="utf-8"
    )
    extras = build_arm_extras(arm, world_graph, bed.campaign_id)
    registry_stats = _registry_size(bed, extras)

    options = CategoryGraphExtractionOptions(
        campaign_id=bed.campaign_id,
        session_id=bed.session_id,
        session_number=bed.session_number,
        source_span_index=span_index,
        source_text=source_text,
        model_id=model_id,
        extra_known_entities=tuple(extras),
    )
    client = OpenAICategoryGraphPassClient(reasoning_effort=reasoning_effort)
    result: CategoryGraphExtractionResult = run_category_pipeline(client, options)

    trial_dir = out_dir / bed.key / arm / f"trial_{trial_index:02d}"
    trial_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "candidate_graph.json").write_text(
        json.dumps(result.candidate_graph, indent=2), encoding="utf-8"
    )
    (trial_dir / "known_entity_mentions.json").write_text(
        json.dumps(result.known_entity_mentions, indent=2), encoding="utf-8"
    )
    (trial_dir / "consolidation_diagnostics.json").write_text(
        json.dumps(result.consolidation_diagnostics, indent=2, default=str),
        encoding="utf-8",
    )

    metrics = _deterministic_metrics(
        candidate_graph=result.candidate_graph,
        known_entity_mentions=result.known_entity_mentions,
        consolidation_diagnostics=result.consolidation_diagnostics,
        world_graph=world_graph,
    )
    metrics.update(
        {
            "arm": arm,
            "bed": bed.key,
            "trial": trial_index,
            "model_id": result.model_id,
            "total_cost_usd": result.total_cost_usd,
            "tokens": _token_totals(result.pass_telemetry),
            **registry_stats,
        }
    )
    if bed.has_gold:
        metrics["gold"] = _gold_metrics(
            result.candidate_graph,
            parts_from_raw_graph(load_gold_candidate_graph_dict()),
        )
    (trial_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, default=str), encoding="utf-8"
    )
    return metrics


def _aggregate(rows: list[dict[str, Any]], key: str) -> dict[str, float] | None:
    vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    if not vals:
        return None
    return {"mean": statistics.mean(vals), "min": min(vals), "max": max(vals)}


def _aggregate_gold(rows: list[dict[str, Any]], key: str) -> dict[str, float] | None:
    vals = [
        r["gold"][key]
        for r in rows
        if isinstance(r.get("gold"), dict) and isinstance(r["gold"].get(key), (int, float))
    ]
    if not vals:
        return None
    return {"mean": statistics.mean(vals), "min": min(vals), "max": max(vals)}


def write_rollup(
    out_root: Path,
    *,
    stamp: str,
    model_id: str,
    trials: int,
    arm_rows: dict[str, dict[str, list[dict[str, Any]]]],
    controls: dict[str, dict[str, Any]],
    world_revision: str,
) -> None:
    lines = [
        "# E1 world-fed known-entity registry rollup",
        "",
        f"- stamp: `{stamp}`",
        f"- model: `{model_id}`",
        f"- trials per arm: {trials}",
        f"- world head revision: `{world_revision}`",
        "",
    ]
    summary: dict[str, Any] = {
        "schema": "dmb_world_fed_registry_rollup_v1",
        "stamp": stamp,
        "model_id": model_id,
        "trials": trials,
        "world_head_revision": world_revision,
        "beds": {},
    }
    for bed_key in sorted(controls.keys() | arm_rows.keys()):
        control = controls.get(bed_key)
        lines.append(f"## Bed `{bed_key}`")
        lines.append("")
        if control:
            gold = control.get("gold") or {}
            lines.append(
                f"- **A0 control (stored party-only run):** nodes={control['node_count']} "
                f"mentions={control['mention_count']} "
                f"world_reuse={control['world_canonical_reuse']} "
                f"novel={control['novel_node_count']}"
                + (
                    f" node_recall={gold.get('node_recall')} edge_recall={gold.get('edge_recall')}"
                    if gold
                    else ""
                )
            )
            lines.append("")
        bed_has_rows = any(arm_rows.get(bed_key, {}).values())
        header = (
            "| arm | registry | nodes | mentions | world reuse | novel | "
            "suppressed dups | cost (mean) |"
        )
        gold_header = " node recall | edge recall | extras vs gold | alias-assisted |"
        has_gold = bed_has_rows and any(
            "gold" in r for rows in arm_rows[bed_key].values() for r in rows
        )
        bed_summary: dict[str, Any] = {"control": control, "arms": {}}
        if bed_has_rows:
            lines.append(header + (gold_header if has_gold else ""))
            lines.append("|---|---|---|---|---|---|---|---" + ("|---|---|---|---|" if has_gold else ""))
        for arm in sorted(arm_rows.get(bed_key, {})):
            rows = arm_rows[bed_key][arm]
            if not rows:
                continue
            reg = rows[0].get("registry_total")
            cost = _aggregate(rows, "total_cost_usd")
            cells = [
                f"`{arm}`",
                str(reg),
                f"{_agg_s(_aggregate(rows, 'node_count'))}",
                f"{_agg_s(_aggregate(rows, 'mention_count'))}",
                f"{_agg_s(_aggregate(rows, 'world_canonical_reuse'))}",
                f"{_agg_s(_aggregate(rows, 'novel_node_count'))}",
                f"{_agg_s(_aggregate(rows, 'suppressed_duplicate_nodes'))}",
                f"${cost['mean']:.4f}" if cost else "n/a",
            ]
            if has_gold:
                cells += [
                    _agg_s(_aggregate_gold(rows, "node_recall")),
                    _agg_s(_aggregate_gold(rows, "edge_recall")),
                    _agg_s(_aggregate_gold(rows, "extra_nodes_vs_gold")),
                    _agg_s(_aggregate_gold(rows, "alias_assisted_node_matches")),
                ]
            lines.append("| " + " | ".join(cells) + " |")
            bed_summary["arms"][arm] = {
                "registry_total": reg,
                "runs": rows,
            }
        lines.append("")
        summary["beds"][bed_key] = bed_summary

    (out_root / f"ROLLUP_{stamp}.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    (out_root / f"ROLLUP_{stamp}.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def _agg_s(agg: dict[str, float] | None) -> str:
    if agg is None:
        return "n/a"
    mean = agg["mean"]
    if agg["min"] == agg["max"]:
        return f"{mean:.2f}"
    return f"{mean:.2f} [{agg['min']:.2f}–{agg['max']:.2f}]"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--beds", default="s23,s25")
    parser.add_argument("--arms", default="a1,a2,a3")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--model-id", default="gpt-5.6-luna")
    parser.add_argument(
        "--reasoning-effort",
        default="medium",
        help="Responses API reasoning effort (default medium for luna).",
    )
    parser.add_argument("--out-root", default="out/graph_memory/experiments/world_fed_registry")
    parser.add_argument("--world-head", default=str(WORLD_HEAD_PATH))
    parser.add_argument(
        "--control-only",
        action="store_true",
        help="Re-score stored A0 baselines only; no LLM calls.",
    )
    args = parser.parse_args()

    bed_keys = [b.strip() for b in args.beds.split(",") if b.strip()]
    arm_keys = [a.strip() for a in args.arms.split(",") if a.strip()]
    world_graph = load_world_graph(Path(args.world_head))
    world_revision = str(world_graph.get("_resolved_revision_id") or "")

    stamp = _utc_stamp()
    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    controls = {key: control_metrics(BEDS[key], world_graph) for key in bed_keys}

    arm_rows: dict[str, dict[str, list[dict[str, Any]]]] = {
        key: {arm: [] for arm in arm_keys} for key in bed_keys
    }
    if not args.control_only:
        for bed_key in bed_keys:
            bed = BEDS[bed_key]
            for arm in arm_keys:
                for trial in range(1, args.trials + 1):
                    print(
                        f"[world-fed] bed={bed_key} arm={arm} trial={trial} "
                        f"model={args.model_id}",
                        flush=True,
                    )
                    metrics = run_arm_trial(
                        bed=bed,
                        arm=arm,
                        trial_index=trial,
                        out_dir=out_root / stamp,
                        model_id=args.model_id,
                        reasoning_effort=args.reasoning_effort,
                        world_graph=world_graph,
                    )
                    arm_rows[bed_key][arm].append(metrics)

    write_rollup(
        out_root,
        stamp=stamp,
        model_id=args.model_id,
        trials=args.trials,
        arm_rows=arm_rows,
        controls=controls,
        world_revision=world_revision,
    )


if __name__ == "__main__":
    main()
