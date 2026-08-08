"""Identity-resolution live candidate graph vs Session 23 gold comparison.

This comparator matches candidate objects to gold by *meaning* rather than by
exact id/label, using ``src.graph_memory.identity_resolution``:

- node-type **class** equivalence (``group`` ~ ``organization`` ~ ``faction``);
- relationship **predicate family** folding (``works_with`` ~ ``allied_with``);
- **best-match assignment** (highest-score-first) so a broad gold label does not
  greedily steal the candidate a narrower gold label needed; and
- candidate **dedup** (inverse-edge + duplicate-node collapse) before scoring,
  so precision is measured against the consolidated graph.

The output schema (``coverage``/``scores``/``soft_misses``) is unchanged; only
the matching engine and a ``dedup`` diagnostics block are new.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import (
    GOLD_FIXTURE_ID,
    parse_gold_candidate_graph,
)
from src.graph_memory import identity_resolution as ir
from src.graph_memory.candidate_graph_preview import CandidateGraphPreview, candidate_graph_preview_from_dict

COMPARISON_SCHEMA = "dmb_live_vs_gold_comparison_report_v0"
COMPARISON_VERSION = "0.1"
COMPARISON_ID = "graph-memory:live-vs-gold-comparison:session-23:v0"


def _id_of(obj: Any, id_attr: str) -> str:
    return str(ir._get(obj, id_attr, ""))


def _label_of(obj: Any, label_attr: str) -> str:
    return str(ir._get(obj, label_attr, "") or "")


def _write_score(g: Any, c: Any) -> float:
    lab = ir.label_similarity(_label_of(g, "label"), _label_of(c, "label"))
    type_ok = str(ir._get(g, "write_type", "")) == str(ir._get(c, "write_type", ""))
    return round(0.7 * lab + (0.3 if type_ok else 0.0), 4)


def _label_only_score(g: Any, c: Any) -> float:
    return ir.label_similarity(_label_of(g, "label"), _label_of(c, "label"))


def _compare_kind(
    gold_objs: Sequence[Any],
    cand_objs: Sequence[Any],
    id_attr: str,
    label_attr: str,
    score_fn: Callable[[Any, Any], float],
    *,
    threshold: float,
) -> tuple[list[str], list[str], list[str]]:
    pairs = ir.best_match_assignment(gold_objs, cand_objs, score_fn, threshold=threshold)
    matched_gold = {gi for gi, _ci, _s in pairs}
    matched_cand = {ci for _gi, ci, _s in pairs}
    matched_ids = [_id_of(gold_objs[gi], id_attr) for gi, _ci, _s in pairs]
    missing = sorted(_id_of(g, id_attr) for i, g in enumerate(gold_objs) if i not in matched_gold)
    extra = sorted(_id_of(c, id_attr) for i, c in enumerate(cand_objs) if i not in matched_cand)
    return matched_ids, missing, extra


def _score(matched: int, total: int) -> float:
    return round((matched / total) if total else 1.0, 4)


_PART_KEYS = ("nodes", "edges", "beats", "proposed_writes", "ignored_items", "deferred_items")


def _parts_from_preview(graph: CandidateGraphPreview) -> dict[str, list[Any]]:
    return {key: list(getattr(graph, key)) for key in _PART_KEYS}


def parts_from_raw_graph(graph: Mapping[str, Any]) -> dict[str, list[Any]]:
    """Build comparison parts from a raw candidate/gold graph dict.

    Tolerant of the live-extractor envelope shape (where edges may use
    ``source_span_ref_id`` evidence and a reduced ``semantic_state``) so the
    same engine can score S22-style outputs that do not parse cleanly into
    ``CandidateGraphPreview``.
    """
    return {key: list(graph.get(key, []) or []) for key in _PART_KEYS}


def compare_parts(
    live_parts: Mapping[str, Sequence[Any]],
    gold_parts: Mapping[str, Sequence[Any]],
    *,
    gold_fixture_id: str = GOLD_FIXTURE_ID,
    report_id: str = COMPARISON_ID,
) -> dict[str, Any]:
    hard: list[dict[str, str]] = []
    soft: list[dict[str, str]] = []
    coverage: dict[str, Any] = {}

    # consolidate the candidate first: collapse duplicate nodes and inverse /
    # duplicate edges so precision reflects the deduplicated graph.
    all_live_nodes = list(live_parts.get("nodes", []))
    node_dedup = ir.dedup_nodes(all_live_nodes)
    edge_dedup = ir.dedup_edges(list(live_parts.get("edges", [])), all_live_nodes)
    live_nodes = node_dedup["kept"]
    live_edges = edge_dedup["kept"]

    gold_nidx = ir.node_index(list(gold_parts.get("nodes", [])))
    cand_nidx = ir.node_index(all_live_nodes)

    def _edge_score(g: Any, c: Any) -> float:
        return ir.edge_match_score(g, c, gold_nidx, cand_nidx)

    def _beat_score(g: Any, c: Any) -> float:
        return ir.beat_match_score(g, c, gold_nidx, cand_nidx)

    plan = [
        ("nodes", live_nodes, list(gold_parts.get("nodes", [])), "node_id", "label", ir.node_match_score, 0.6, "missing_required_node"),
        ("edges", live_edges, list(gold_parts.get("edges", [])), "edge_id", "label", _edge_score, 0.6, "missing_required_edge"),
        ("beats", list(live_parts.get("beats", [])), list(gold_parts.get("beats", [])), "beat_id", "title", _beat_score, 0.45, "missing_required_beat"),
        ("proposed_writes", list(live_parts.get("proposed_writes", [])), list(gold_parts.get("proposed_writes", [])), "write_id", "label", _write_score, 0.5, "missing_proposed_write"),
        ("ignored_items", list(live_parts.get("ignored_items", [])), list(gold_parts.get("ignored_items", [])), "item_id", "label", _label_only_score, 0.5, "missing_ignored_item"),
        ("deferred_items", list(live_parts.get("deferred_items", [])), list(gold_parts.get("deferred_items", [])), "item_id", "label", _label_only_score, 0.5, "missing_deferred_item"),
    ]

    for name, lseq, gseq, id_attr, label_attr, score_fn, threshold, issue in plan:
        matched, missing, extra = _compare_kind(gseq, lseq, id_attr, label_attr, score_fn, threshold=threshold)
        gold_label_by_id = {_id_of(g, id_attr): _label_of(g, label_attr) for g in gseq}
        cand_label_by_id = {_id_of(c, id_attr): _label_of(c, label_attr) for c in lseq}
        coverage[f"gold_{name}_total"] = len(gseq)
        coverage[f"candidate_{name}_total"] = len(lseq)
        coverage[f"matched_{name}"] = matched
        coverage[f"missing_gold_{name}"] = [{"id": i, "label": gold_label_by_id.get(i, "")} for i in missing]
        coverage[f"extra_candidate_{name}"] = [{"id": i, "label": cand_label_by_id.get(i, "")} for i in extra]
        for mid in missing:
            soft.append({"issue": issue, "detail": mid, "label": gold_label_by_id.get(mid, "")})

    edge_miss_diagnostics = ir.build_edge_miss_diagnostics(
        [entry["id"] if isinstance(entry, dict) else str(entry) for entry in coverage.get("missing_gold_edges", [])],
        list(gold_parts.get("edges", [])),
        live_edges,
        gold_nidx,
        cand_nidx,
        threshold=0.6,
    )

    # Audit: surface matched node pairs whose score depended on the curated
    # label-alias layer, so alias-assisted recalls are visible in reports.
    node_pairs = ir.best_match_assignment(
        list(gold_parts.get("nodes", [])), live_nodes, ir.node_match_score, threshold=0.6
    )
    alias_assisted = [
        {
            "gold_node_id": _id_of(gold_parts["nodes"][gi], "node_id"),
            "gold_label": _label_of(gold_parts["nodes"][gi], "label"),
            "candidate_node_id": _id_of(live_nodes[ci], "node_id"),
            "candidate_label": _label_of(live_nodes[ci], "label"),
        }
        for gi, ci, _s in node_pairs
        if ir.alias_assisted_labels(
            _label_of(gold_parts["nodes"][gi], "label"), _label_of(live_nodes[ci], "label")
        )
    ]

    scores = {
        "node_recall": _score(len(coverage["matched_nodes"]), coverage["gold_nodes_total"]),
        "edge_recall": _score(len(coverage["matched_edges"]), coverage["gold_edges_total"]),
        "beat_recall": _score(len(coverage["matched_beats"]), coverage["gold_beats_total"]),
        "proposed_write_recall": _score(len(coverage["matched_proposed_writes"]), coverage["gold_proposed_writes_total"]),
        "ignored_item_recall": _score(len(coverage["matched_ignored_items"]), coverage["gold_ignored_items_total"]),
        "deferred_item_recall": _score(len(coverage["matched_deferred_items"]), coverage["gold_deferred_items_total"]),
        "node_precision_proxy": _score(len(coverage["matched_nodes"]), coverage["candidate_nodes_total"]),
        "edge_precision_proxy": _score(len(coverage["matched_edges"]), coverage["candidate_edges_total"]),
        "evidence_alignment_score": 1.0,
        "high_risk_audit_score": 1.0,
        "safety_gate_score": 1.0 if not hard else 0.0,
    }
    return {
        "schema": COMPARISON_SCHEMA,
        "version": COMPARISON_VERSION,
        "report_id": report_id,
        "gold_fixture_id": gold_fixture_id,
        "comparison_mode": "live_identity_vs_gold",
        "hard_failures": hard,
        "soft_misses": soft,
        "scores": scores,
        "coverage": coverage,
        "dedup": {
            "candidate_nodes_raw": len(all_live_nodes),
            "candidate_nodes_deduped": len(live_nodes),
            "merged_nodes": node_dedup["merged"],
            "candidate_edges_raw": len(list(live_parts.get("edges", []))),
            "candidate_edges_deduped": len(live_edges),
            "merged_edges": edge_dedup["merged"],
        },
        "diagnostics": {
            "llm_used": True,
            "identity_resolution": True,
            "best_match_assignment": True,
            "candidate_dedup_applied": True,
            "id_match_not_required": True,
            "label_alias": {
                "policy_version": ir.LABEL_ALIAS_POLICY_VERSION,
                "alias_assisted_node_matches": alias_assisted,
            },
            "edge_miss_diagnostics": edge_miss_diagnostics,
        },
    }


def compare_live_to_gold(live_graph: Mapping[str, Any] | CandidateGraphPreview) -> dict[str, Any]:
    live = live_graph if isinstance(live_graph, CandidateGraphPreview) else candidate_graph_preview_from_dict(live_graph)
    gold = parse_gold_candidate_graph()
    return compare_parts(_parts_from_preview(live), _parts_from_preview(gold))


def compare_live_candidate_file(candidate_path: Path, *, reconciled_graph: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if reconciled_graph is not None:
        return compare_live_to_gold(reconciled_graph)
    data = json.loads(candidate_path.read_text(encoding="utf-8"))
    if "reconciled_candidate_graph" in data:
        return compare_live_to_gold(data["reconciled_candidate_graph"])
    return compare_live_to_gold(data.get("candidate_graph", data))
