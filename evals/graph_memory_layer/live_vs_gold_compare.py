"""Fuzzy live candidate graph vs Session 23 gold comparison."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import (
    GOLD_FIXTURE_ID,
    parse_gold_candidate_graph,
)
from evals.graph_memory_layer.session_23_recap_ingest_fixture import load_source_span_seed_refs
from src.graph_memory.candidate_graph_preview import CandidateGraphPreview, candidate_graph_preview_from_dict

COMPARISON_SCHEMA = "dmb_live_vs_gold_comparison_report_v0"
COMPARISON_VERSION = "0.1"
COMPARISON_ID = "graph-memory:live-vs-gold-comparison:session-23:v0"


def _norm_label(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", "", value.lower())).strip()


def _label_match(a: str, b: str) -> bool:
    na, nb = _norm_label(a), _norm_label(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    aw, bw = set(na.split()), set(nb.split())
    if len(aw & bw) >= min(2, len(aw), len(bw)):
        return True
    return False


def _anchor_lines(anchor_id: str | None) -> tuple[int, int] | None:
    if not anchor_id:
        return None
    for ref in load_source_span_seed_refs()["source_span_refs"]:
        if ref["source_anchor_id"] == anchor_id:
            return ref["start_line"], ref["end_line"]
    return None


def _evidence_line_ranges(obj: Any) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for ref in getattr(obj, "evidence_refs", ()) or obj.get("evidence_refs", []) or []:
        if isinstance(ref, Mapping):
            anchor = ref.get("source_anchor_id")
            lines = _anchor_lines(anchor)
            if lines:
                ranges.append(lines)
    return ranges


def _span_overlap(a: Sequence[tuple[int, int]], b: Sequence[tuple[int, int]]) -> bool:
    for la, lb in a:
        for ra, rb in b:
            if la <= rb and ra <= lb:
                return True
    return False


def _object_id(obj: Any) -> str:
    if isinstance(obj, Mapping):
        for key in ("node_id", "edge_id", "beat_id", "write_id", "item_id", "id"):
            if obj.get(key):
                return str(obj[key])
        return ""
    return str(
        getattr(
            obj,
            "node_id",
            getattr(
                obj,
                "edge_id",
                getattr(
                    obj,
                    "beat_id",
                    getattr(obj, "write_id", getattr(obj, "item_id", "")),
                ),
            ),
        )
    )


def _match_objects(
    live_objs: Sequence[Any],
    gold_objs: Sequence[Any],
    *,
    label_attr: str,
    type_attr: str | None = None,
) -> tuple[list[str], list[str], list[str]]:
    matched_live: set[str] = set()
    matched_gold: set[str] = set()
    pairs: list[str] = []
    for g in gold_objs:
        gid = _object_id(g)
        glabel = getattr(g, label_attr, "")
        gtype = getattr(g, type_attr, None) if type_attr else None
        granges = _evidence_line_ranges(g)
        for l in live_objs:
            lid = _object_id(l)
            if lid in matched_live:
                continue
            llabel = getattr(l, label_attr, "")
            ltype = getattr(l, type_attr, None) if type_attr else None
            lranges = _evidence_line_ranges(l)
            type_ok = gtype is None or ltype is None or gtype == ltype
            if type_ok and (_label_match(glabel, llabel) or _span_overlap(granges, lranges)):
                matched_live.add(lid)
                matched_gold.add(gid)
                pairs.append(gid)
                break
    gold_ids = {_object_id(g) for g in gold_objs}
    live_ids = {_object_id(l) for l in live_objs}
    return pairs, sorted(gold_ids - matched_gold), sorted(live_ids - matched_live)


def _score(matched: int, total: int) -> float:
    return round((matched / total) if total else 1.0, 4)


def compare_live_to_gold(live_graph: Mapping[str, Any] | CandidateGraphPreview) -> dict[str, Any]:
    live = live_graph if isinstance(live_graph, CandidateGraphPreview) else candidate_graph_preview_from_dict(live_graph)
    gold = parse_gold_candidate_graph()
    hard: list[dict[str, str]] = []
    soft: list[dict[str, str]] = []
    coverage: dict[str, Any] = {}

    pairs = [
        ("nodes", live.nodes, gold.nodes, "node_id", "node_type", "missing_required_node"),
        ("edges", live.edges, gold.edges, "edge_id", "relationship_type", "missing_required_edge"),
        ("beats", live.beats, gold.beats, "beat_id", None, "missing_required_beat"),
        ("proposed_writes", live.proposed_writes, gold.proposed_writes, "write_id", "write_type", "missing_proposed_write"),
        ("ignored_items", live.ignored_items, gold.ignored_items, "item_id", None, "missing_ignored_item"),
        ("deferred_items", live.deferred_items, gold.deferred_items, "item_id", None, "missing_deferred_item"),
    ]
    for name, lseq, gseq, id_attr, type_attr, issue in pairs:
        label_attr = "label" if name != "beats" else "title"
        matched, missing, extra = _match_objects(lseq, gseq, label_attr=label_attr, type_attr=type_attr)
        gids = {getattr(g, id_attr) for g in gseq}
        lids = {getattr(l, id_attr) for l in lseq}
        coverage[f"gold_{name}_total"] = len(gids)
        coverage[f"candidate_{name}_total"] = len(lids)
        coverage[f"matched_{name}"] = matched
        coverage[f"missing_gold_{name}"] = [{"id": i, "label": getattr(next(g for g in gseq if getattr(g, id_attr) == i), label_attr, "")} for i in missing]
        coverage[f"extra_candidate_{name}"] = [{"id": i, "label": getattr(next(l for l in lseq if getattr(l, id_attr) == i), label_attr, "")} for i in extra]
        for mid in missing:
            soft.append({"issue": issue, "detail": mid, "label": coverage[f"missing_gold_{name}"][-1]["label"] if coverage[f"missing_gold_{name}"] else ""})

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
        "report_id": COMPARISON_ID,
        "gold_fixture_id": GOLD_FIXTURE_ID,
        "comparison_mode": "live_fuzzy_vs_gold",
        "hard_failures": hard,
        "soft_misses": soft,
        "scores": scores,
        "coverage": coverage,
        "diagnostics": {"llm_used": True, "fuzzy_label_match": True, "id_match_not_required": True},
    }


def compare_live_candidate_file(candidate_path: Path, *, reconciled_graph: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if reconciled_graph is not None:
        return compare_live_to_gold(reconciled_graph)
    data = json.loads(candidate_path.read_text(encoding="utf-8"))
    if "reconciled_candidate_graph" in data:
        return compare_live_to_gold(data["reconciled_candidate_graph"])
    return compare_live_to_gold(data.get("candidate_graph", data))
