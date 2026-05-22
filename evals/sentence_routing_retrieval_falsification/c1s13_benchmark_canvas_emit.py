#!/usr/bin/env python3
"""Inject C1S13 breadcrumb harness review data into the Cursor canvas .tsx file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.cursor_canvas_paths import (
    default_cursor_canvas_path,
    ensure_canvas_file_for_patch,
)

BLOCK_BEGIN = "// BEGIN GENERATED C1S13_HARNESS_DETAIL"
BLOCK_END = "// END GENERATED C1S13_HARNESS_DETAIL"

_DEFAULT_CANVAS = default_cursor_canvas_path("c1s13-breadcrumb-query-benchmark-review.canvas.tsx")


def _token_in_answer_ci(token: str, answer: str) -> bool:
    if not token or not answer:
        return False
    return token.lower() in answer.lower()


def _norm_for_route_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _expected_matches_route(expected: str, route: str) -> bool:
    expected_norm = _norm_for_route_match(expected)
    route_norm = _norm_for_route_match(route)
    if not expected_norm or not route_norm:
        return False
    return expected_norm in route_norm


def _compact_hit_rows(
    full: dict[str, Any],
    *,
    limit: int,
    beat_by_unit: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    hits = list(full.get("hits") or [])
    out: list[dict[str, Any]] = []
    for h in hits[:limit]:
        routes = []
        for route in list(h.get("routes") or [])[:4]:
            if isinstance(route, dict):
                routes.append(str(route.get("normalized_route") or ""))
        uid = str(h.get("unit_id") or "").strip()
        bid = (beat_by_unit or {}).get(uid, "") if beat_by_unit else ""
        row = {
            "unit_id": uid,
            "line_span": f"L{int(h.get('line_start') or 0)}-{int(h.get('line_end') or 0)}",
            "score": int(h.get("score") or 0),
            "source_recap_path": str(h.get("source_recap_path") or ""),
            "routes": routes,
            "why_matched": [str(x) for x in (h.get("why_matched") or [])],
        }
        if bid:
            row["beat_id"] = bid
        out.append(row)
    return out


_REPO_ROOT = Path(__file__).resolve().parents[2]

_C1S13_SCENE_SPAN_GOLD = (
    _REPO_ROOT
    / "evals/sentence_routing_retrieval_falsification/manual_labels"
    / "Session 13 - The Meaty and the Dead.gold.scene_span_v1.breadcrumbed.md"
)


def _load_gold_beat_unit_map(scene_span_md: Path) -> dict[str, str]:
    """Map ``unit_id`` → gold ``beat_id`` from scene-span YAML (first frontmatter block)."""
    if not scene_span_md.is_file():
        return {}
    text = scene_span_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    yaml_body = parts[1]
    out: dict[str, str] = {}
    current: str | None = None
    unit_re = re.compile(r"^\s*unit_ids:\s*\[(.+)\]\s*$")
    beat_re = re.compile(r"^\s*-\s*beat_id:\s*(.+)\s*$")
    for line in yaml_body.splitlines():
        m_beat = beat_re.match(line)
        if m_beat:
            current = m_beat.group(1).strip()
            continue
        if current and (m_u := unit_re.match(line)):
            raw = m_u.group(1)
            for piece in raw.split(","):
                uid = piece.strip().strip("\"'")
                if uid.startswith("u-"):
                    out[uid] = current
    return out


def _rollup_retrieval_hits_by_gold_beat(
    hits: list[dict[str, Any]],
    unit_to_beat: dict[str, str],
) -> list[dict[str, Any]]:
    """Group retrieval hits by gold beat; sort beats by descending summed hit scores."""
    buckets: dict[str, list[dict[str, Any]]] = {}
    for i, h in enumerate(hits):
        uid = str(h.get("unit_id") or "").strip()
        if not uid:
            bid = "__no_unit__"
        elif uid.startswith("meta-session-"):
            bid = "__session_meta__"
        else:
            bid = unit_to_beat.get(uid, "__unmapped__")
        score = int(h.get("score") or 0)
        line_span = f"L{int(h.get('line_start') or 0)}-{int(h.get('line_end') or 0)}"
        buckets.setdefault(bid, []).append(
            {"rank": i + 1, "unit_id": uid, "score": score, "line_span": line_span}
        )
    rows: list[dict[str, Any]] = []
    for bid, hx in buckets.items():
        hx_sorted = sorted(hx, key=lambda x: int(x["rank"]))
        summed = sum(int(x["score"]) for x in hx_sorted)
        rows.append(
            {
                "beat_id": bid,
                "summed_score": summed,
                "hit_count": len(hx_sorted),
                "hits": hx_sorted,
            }
        )
    rows.sort(key=lambda x: (-int(x["summed_score"]), str(x["beat_id"])))
    return rows


def _tag_rollups_primary_gold_beat(
    rollups: list[dict[str, Any]],
    gold_beat_id: str | None,
) -> list[dict[str, Any]]:
    """Mark the rollup row that matches manual-query ``gold_beat_id`` (for canvas row highlighting)."""
    gold = (gold_beat_id or "").strip()
    for r in rollups:
        r["is_primary_gold_beat"] = bool(gold and str(r.get("beat_id") or "") == gold)
    return rollups


def _annotate_rollups_table_metrics(rollups: list[dict[str, Any]]) -> None:
    """Per-row rank and distance to the first row's Σ (current table sort order)."""
    if not rollups:
        return
    top_s = int(rollups[0].get("summed_score") or 0)
    for i, r in enumerate(rollups):
        s = int(r.get("summed_score") or 0)
        r["rollup_rank"] = i + 1
        r["delta_from_table_top"] = top_s - s
        r["ratio_to_table_top"] = round(s / max(1, top_s), 4)


def _beat_rollup_diagnostic(
    rollups: list[dict[str, Any]],
    gold_beat_id: str | None,
) -> dict[str, Any]:
    """Scenario-level rollup vs. gold-beat summary for canvas triage (threshold / meta dominance)."""
    gid = (gold_beat_id or "").strip()
    empty: dict[str, Any] = {
        "promotion_hint": "no_rollups",
        "meta_is_table_top": False,
        "gold_rank": None,
        "gold_rank_non_meta": None,
        "top_beat_id": None,
        "top_summed_score": None,
        "top_non_meta_beat_id": None,
        "top_non_meta_summed_score": None,
        "gold_summed_score": None,
        "delta_table_top_minus_gold": None,
        "delta_non_meta_top_minus_gold": None,
        "ratio_gold_to_table_top": None,
        "ratio_gold_to_non_meta_top": None,
    }
    if not rollups:
        return dict(empty)
    non_meta = [r for r in rollups if str(r.get("beat_id") or "") != "__session_meta__"]
    top_all = rollups[0]
    top_bid = str(top_all.get("beat_id") or "")
    top_s = int(top_all.get("summed_score") or 0)
    top_nm = non_meta[0] if non_meta else None
    top_nm_bid = str(top_nm.get("beat_id") or "") if top_nm else None
    top_nm_s = int(top_nm.get("summed_score") or 0) if top_nm else None

    gold_roll = next((r for r in rollups if str(r.get("beat_id") or "") == gid), None) if gid else None
    g_s = int(gold_roll.get("summed_score") or 0) if gold_roll else None

    gold_rank: int | None = None
    gold_rank_nm: int | None = None
    if gold_roll is not None:
        gold_rank = rollups.index(gold_roll) + 1
        if str(gold_roll.get("beat_id") or "") != "__session_meta__":
            for j, r in enumerate(non_meta):
                if r is gold_roll:
                    gold_rank_nm = j + 1
                    break

    delta_tbl = (top_s - g_s) if g_s is not None else None
    delta_nm = (top_nm_s - g_s) if (g_s is not None and top_nm_s is not None) else None
    ratio_tbl = round(g_s / max(1, top_s), 4) if g_s is not None else None
    ratio_nm = round(g_s / max(1, top_nm_s or 1), 4) if (g_s is not None and top_nm_s is not None) else None

    hint = "no_gold_beat"
    if not gid:
        hint = "no_gold_beat"
    elif gold_roll is None:
        hint = "gold_not_in_rollups"
    elif gold_rank == 1:
        hint = "gold_top"
    else:
        meta_top = top_bid == "__session_meta__"
        if meta_top and gold_rank_nm == 1:
            hint = "gold_top_non_meta_meta_leads_table"
        elif meta_top:
            hint = "meta_leads_table"
        elif gold_rank is not None and gold_rank <= 3 and delta_tbl is not None and delta_tbl <= 3:
            hint = "gold_near_top"
        elif ratio_tbl is not None and ratio_tbl >= 0.85:
            hint = "gold_near_top"
        else:
            hint = "gold_depressed"

    return {
        "promotion_hint": hint,
        "meta_is_table_top": top_bid == "__session_meta__",
        "gold_rank": gold_rank,
        "gold_rank_non_meta": gold_rank_nm,
        "top_beat_id": top_bid or None,
        "top_summed_score": top_s,
        "top_non_meta_beat_id": top_nm_bid,
        "top_non_meta_summed_score": top_nm_s,
        "gold_summed_score": g_s,
        "delta_table_top_minus_gold": delta_tbl,
        "delta_non_meta_top_minus_gold": delta_nm,
        "ratio_gold_to_table_top": ratio_tbl,
        "ratio_gold_to_non_meta_top": ratio_nm,
    }


def _resolve_records_meta_path(raw: str) -> Path:
    """Resolve session-memory JSONL; remap ``/workspace/DungeonMindBuddy/`` to this repo root."""
    s = (raw or "").strip()
    if not s:
        return Path()
    p = Path(s).expanduser()
    if p.is_file():
        return p
    norm = s.replace("\\", "/")
    marker = "/workspace/DungeonMindBuddy/"
    if marker in norm:
        suffix = norm.split(marker, 1)[1].lstrip("/")
        cand = (_REPO_ROOT / suffix).resolve()
        if cand.is_file():
            return cand
    return p


def _scan_records_jsonl_for_beats(path: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """Return ``(unit_id -> beat_id, corpus_stats)`` for session-memory JSONL."""
    beat_by_unit: dict[str, str] = {}
    beat_ids: set[str] = set()
    record_count = 0
    with_beat = 0
    if not path.is_file():
        return beat_by_unit, {
            "record_count": 0,
            "records_with_beat_id": 0,
            "distinct_beat_count": 0,
            "beat_ids_sample": [],
            "error": "records file missing",
        }
    for line in path.read_text(encoding="utf-8").splitlines():
        row = line.strip()
        if not row:
            continue
        try:
            obj: dict[str, Any] = json.loads(row)
        except json.JSONDecodeError:
            continue
        record_count += 1
        uid = str(obj.get("unit_id") or "").strip()
        bid = str(obj.get("beat_id") or "").strip()
        if uid and bid:
            beat_by_unit[uid] = bid
            beat_ids.add(bid)
            with_beat += 1
    sample = sorted(beat_ids)[:24]
    return beat_by_unit, {
        "record_count": record_count,
        "records_with_beat_id": with_beat,
        "distinct_beat_count": len(beat_ids),
        "beat_ids_sample": sample,
    }


def _slim_scene_packet_trace(pkt_trace: Any) -> dict[str, Any]:
    if not isinstance(pkt_trace, dict):
        return {}
    packets_raw = list(pkt_trace.get("packets") or [])
    slim: list[dict[str, Any]] = []
    for pkt in packets_raw[:6]:
        if not isinstance(pkt, dict):
            continue
        fpu = [str(x) for x in (pkt.get("first_pass_unit_ids") or [])][:10]
        pu = [str(x) for x in (pkt.get("packet_unit_ids") or [])][:16]
        slim.append(
            {
                "beat_id": str(pkt.get("beat_id") or ""),
                "score": int(pkt.get("score") or 0),
                "first_pass_unit_ids": fpu,
                "packet_unit_ids": pu,
            }
        )
    return {
        "qualified_count": int(pkt_trace.get("qualified_count") or 0),
        "units_added": int(pkt_trace.get("units_added") or 0),
        "packets": slim,
    }


def _query_trace_beat_scene(full: dict[str, Any]) -> dict[str, Any]:
    trace = full.get("trace") if isinstance(full.get("trace"), dict) else {}
    exp = trace.get("expansion") if isinstance(trace.get("expansion"), dict) else {}
    out: dict[str, Any] = {
        "expand_same_beat_limit": trace.get("expand_same_beat_limit"),
        "expand_adjacent_window": trace.get("expand_adjacent_window"),
        "expand_context": bool(trace.get("expand_context")),
        "expansion": {
            "added_adjacent": int(exp.get("added_adjacent") or 0) if exp else 0,
            "added_same_beat": int(exp.get("added_same_beat") or 0) if exp else 0,
            "added_shared_route": int(exp.get("added_shared_route") or 0) if exp else 0,
            "added_route_family": int(exp.get("added_route_family") or 0) if exp else 0,
        },
        "scene_beat_packets_trace": _slim_scene_packet_trace(trace.get("scene_beat_packets")),
    }
    return out


def _slim_harness_scene_packets(sp: Any) -> dict[str, Any] | None:
    """Shrink harness ``scene_beat_packets`` rows for canvas JSON size."""
    if not isinstance(sp, dict):
        return None
    pkts = list(sp.get("packets") or [])
    if not (
        bool(sp.get("enabled"))
        or int(sp.get("qualified_count") or 0) > 0
        or int(sp.get("units_added") or 0) > 0
        or bool(pkts)
    ):
        return None
    slim: list[dict[str, Any]] = []
    for p in pkts[:6]:
        if not isinstance(p, dict):
            continue
        slim.append(
            {
                "beat_id": str(p.get("beat_id") or ""),
                "score": int(p.get("score") or 0),
                "first_pass_unit_ids": [str(x) for x in (p.get("first_pass_unit_ids") or [])][:10],
                "packet_unit_ids": [str(x) for x in (p.get("packet_unit_ids") or [])][:14],
            }
        )
    return {
        "enabled": bool(sp.get("enabled")),
        "threshold": sp.get("threshold"),
        "top_k": sp.get("top_k"),
        "unit_limit": sp.get("unit_limit"),
        "max_packets": sp.get("max_packets"),
        "qualified_count": int(sp.get("qualified_count") or 0),
        "units_added": int(sp.get("units_added") or 0),
        "packet_beat_ids": [str(x) for x in (sp.get("packet_beat_ids") or [])][:16],
        "packets": slim,
    }


def _collect_available_routes(report: dict[str, Any]) -> list[str]:
    src = str(report.get("records_source") or "").strip()
    if not src:
        return []
    p = _resolve_records_meta_path(src)
    if not p.is_file():
        return []
    routes: set[str] = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        row = line.strip()
        if not row:
            continue
        try:
            payload = json.loads(row)
        except json.JSONDecodeError:
            continue
        for route in list(payload.get("routes") or []):
            if not isinstance(route, dict):
                continue
            normalized = str(route.get("normalized_route") or "").strip()
            if normalized:
                routes.add(normalized)
    return sorted(routes)


def _build_rows(*, report: dict[str, Any], gold: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_id = {str(r.get("scenario_id") or ""): r for r in (report.get("results") or [])}
    records_raw = str(report.get("records_source") or "").strip()
    records_path = _resolve_records_meta_path(records_raw) if records_raw else Path()
    records_source_out = str(records_path) if records_path.is_file() else records_raw
    if not records_raw:
        beat_by_unit: dict[str, str] = {}
        corpus_beat_stats = {
            "record_count": 0,
            "records_with_beat_id": 0,
            "distinct_beat_count": 0,
            "beat_ids_sample": [],
        }
    else:
        beat_by_unit, corpus_beat_stats = _scan_records_jsonl_for_beats(records_path)
    available_routes = _collect_available_routes(report)
    unit_to_gold_beat = _load_gold_beat_unit_map(_C1S13_SCENE_SPAN_GOLD)
    rows: list[dict[str, Any]] = []
    for scen in gold.get("scenarios") or []:
        sid = str(scen.get("id") or "")
        gold_beat_id = str(scen.get("gold_beat_id") or "").strip() or None
        r = by_id.get(sid) or {}
        llm_prev = str(r.get("llm_answer_preview") or "")
        full = r.get("full_result") if isinstance(r.get("full_result"), dict) else {}
        must_tokens = [str(x) for x in (scen.get("must_hit_tokens") or [])]
        expected_routes = [str(x) for x in (scen.get("expect_route_substrings") or [])]
        hit_routes: list[str] = []
        for h in list(full.get("hits") or []):
            for route in list(h.get("routes") or []):
                if isinstance(route, dict):
                    normalized = str(route.get("normalized_route") or "").strip()
                    if normalized:
                        hit_routes.append(normalized)
        retrieved_route_values = sorted(set(hit_routes))

        route_checks: list[dict[str, Any]] = []
        for expected in expected_routes:
            expected_candidates = [
                rte for rte in available_routes if _expected_matches_route(expected, rte)
            ][:5]
            matched_routes = [
                rte for rte in retrieved_route_values if _expected_matches_route(expected, rte)
            ][:3]
            route_checks.append(
                {
                    "expected": expected,
                    "expected_route_candidates": expected_candidates,
                    "matched": bool(matched_routes),
                    "matched_routes": matched_routes,
                }
            )
        # Keep "missing expected routes" aligned with the same matcher used by
        # route_checks so the canvas cannot show contradictory route status.
        missing_expected_routes = [chk["expected"] for chk in route_checks if not bool(chk["matched"])]
        raw_violations = [str(x) for x in (r.get("violations") or [])]
        effective_violations = [
            v
            for v in raw_violations
            if not (v == "missing_expected_route_hit" and not missing_expected_routes)
        ]
        effective_ok = not effective_violations
        retrieved_context_text = str(r.get("retrieved_context") or "")
        retrieval_hit_context_full = str(r.get("retrieval_hit_context_full") or "")
        se_raw = r.get("scene_beat_expansion")
        scene_exp = dict(se_raw) if isinstance(se_raw, dict) else None
        scene_pkt = _slim_harness_scene_packets(r.get("scene_beat_packets"))
        rollups_raw = _rollup_retrieval_hits_by_gold_beat(
            list(full.get("hits") or []),
            unit_to_gold_beat,
        )
        rollups_tagged = _tag_rollups_primary_gold_beat(rollups_raw, gold_beat_id)
        beat_rollup_diagnostic = _beat_rollup_diagnostic(rollups_tagged, gold_beat_id)
        _annotate_rollups_table_metrics(rollups_tagged)
        rows.append(
            {
                "id": sid,
                "gold_beat_id": gold_beat_id,
                "ok": effective_ok,
                "benchmark_ok_raw": bool(r.get("ok")),
                "question": str(scen.get("question") or ""),
                "expected_answer": str(scen.get("expected_answer") or ""),
                "llm_answer_preview": llm_prev,
                "violations": effective_violations,
                "context_support_ratio": r.get("context_support_ratio"),
                "llm_context_support_ratio": r.get("llm_context_support_ratio"),
                "llm_semantic_verdict": r.get("llm_semantic_verdict"),
                "llm_semantic_must_hits": [str(x) for x in (r.get("llm_semantic_must_hits") or [])],
                "keyword_rows": [
                    {
                        "token": t,
                        "in_llm_answer_ci": _token_in_answer_ci(t, llm_prev),
                        "in_retrieved_context_ci": _token_in_answer_ci(
                            t,
                            "\n".join([retrieved_context_text, retrieval_hit_context_full]),
                        ),
                    }
                    for t in must_tokens
                ],
                "expected_route_substrings": expected_routes,
                "retrieved_route_values": retrieved_route_values[:40],
                "route_checks": route_checks,
                "missing_expected_route_substrings": missing_expected_routes,
                "retrieval_hit_context_full": retrieval_hit_context_full[:16000],
                "lexical_hit_context_promoted": retrieved_context_text[:16000],
                "llm_user_message": str(r.get("llm_user_message") or "")[:12000],
                "scene_beat_expansion": scene_exp,
                "scene_beat_packets": scene_pkt,
                "query_trace_beat_scene": _query_trace_beat_scene(full),
                "hit_rows": _compact_hit_rows(full, limit=20, beat_by_unit=beat_by_unit or None),
                "beat_rollup_diagnostic": beat_rollup_diagnostic,
                "beat_retrieval_rollups": rollups_tagged,
            }
        )

    results = list(report.get("results") or [])
    passed = sum(1 for x in rows if x.get("ok"))
    summary = {
        "llmModel": report.get("llm_model"),
        "passCount": passed,
        "scenarioCount": len(results),
        "scenarioEstimatedCostUsd": report.get("scenario_estimated_cost_usd"),
        "benchmarkReportPath": str(report.get("_emit_report_path") or ""),
        "recordsSource": records_source_out,
        "corpusBeatStats": corpus_beat_stats,
    }
    return rows, summary


def _render_block(*, rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    body = json.dumps(
        {
            "harnessSummaryGenerated": summary,
            "harnessScenarioDetailGenerated": rows,
        },
        indent=2,
        ensure_ascii=True,
    )
    return (
        f"{BLOCK_BEGIN}\n"
        "// Generated by c1s13_benchmark_canvas_emit.py — do not hand-edit.\n"
        f"const c1s13HarnessCanvasGenerated = {body} as const;\n"
        f"{BLOCK_END}\n"
    )


def _patch_canvas_text(canvas_text: str, block: str) -> str:
    if BLOCK_BEGIN not in canvas_text or BLOCK_END not in canvas_text:
        raise ValueError(
            f"Canvas must contain {BLOCK_BEGIN!r} and {BLOCK_END!r} markers "
            "(add the empty block once, then re-run this script)."
        )
    pre, rest = canvas_text.split(BLOCK_BEGIN, 1)
    _mid, post = rest.split(BLOCK_END, 1)
    if post.startswith("\n\n"):
        post = post[1:]
    return pre + block + post


def build_c1s13_canvas_block(
    report: dict[str, Any],
    gold: dict[str, Any],
    *,
    report_path: Path | str | None = None,
) -> str:
    rep = dict(report)
    if report_path is not None:
        rep["_emit_report_path"] = str(Path(report_path).resolve())
    rows, summary = _build_rows(report=rep, gold=gold)
    return _render_block(rows=rows, summary=summary)


def patch_c1s13_canvas_paths(block: str, paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for canvas_path in paths:
        p = canvas_path.expanduser().resolve()
        try:
            ensure_canvas_file_for_patch(p)
            text = p.read_text(encoding="utf-8")
        except OSError as exc:
            out.append({"path": str(p), "error": f"{type(exc).__name__}: {exc}"})
            continue
        try:
            new_text = _patch_canvas_text(text, block)
        except ValueError as exc:
            out.append({"path": str(p), "error": f"{type(exc).__name__}: {exc}"})
            continue
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            out.append({"canvas_updated": str(p)})
        else:
            out.append({"canvas_unchanged": str(p)})
    return out


def refresh_c1s13_benchmark_canvases(
    *,
    report: dict[str, Any],
    gold: dict[str, Any],
    report_path: Path | str,
    canvas_paths: list[Path],
) -> dict[str, Any]:
    block = build_c1s13_canvas_block(report, gold, report_path=report_path)
    per_file = patch_c1s13_canvas_paths(block, canvas_paths)
    errors = [x for x in per_file if "error" in x]
    updated = [str(x["canvas_updated"]) for x in per_file if "canvas_updated" in x]
    unchanged = [str(x["canvas_unchanged"]) for x in per_file if "canvas_unchanged" in x]
    return {
        "enabled": True,
        "targets": [str(p.expanduser().resolve()) for p in canvas_paths],
        "updated": updated,
        "unchanged": unchanged,
        "errors": errors,
        "scenario_count": len(list(gold.get("scenarios") or [])),
    }


def c1s13_canvas_refresh_auto_enabled(*, gold_path: Path, gold: dict[str, Any]) -> bool:
    if str(gold.get("schema") or "") != "dmb_breadcrumb_query_natural_gold_v1":
        return False
    if "c1s13" in gold_path.name.lower():
        return True
    for scen in gold.get("scenarios") or []:
        if str(scen.get("id") or "").startswith("c1s13_"):
            return True
    return False


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument(
        "--canvas-tsx",
        type=Path,
        action="append",
        dest="canvas_tsx_list",
        default=None,
        help=(
            "Target .canvas.tsx (repeat to patch several files). "
            f"Default: Cursor-managed {_DEFAULT_CANVAS} (set DMB_CURSOR_CANVAS_DIR to override the parent canvases/ dir)."
        ),
    )
    args = p.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    gold = json.loads(args.gold.read_text(encoding="utf-8"))
    targets = [p.expanduser().resolve() for p in (args.canvas_tsx_list or [_DEFAULT_CANVAS])]
    block = build_c1s13_canvas_block(report, gold, report_path=args.report)
    per_file = patch_c1s13_canvas_paths(block, targets)
    errors = [x for x in per_file if "error" in x]
    if errors:
        err_msg = "; ".join(str(e.get("error", e)) for e in errors)
        raise SystemExit(f"c1s13_benchmark_canvas_emit: canvas patch failed: {err_msg}")
    print(json.dumps({"targets": per_file}, indent=2))


if __name__ == "__main__":
    main()
