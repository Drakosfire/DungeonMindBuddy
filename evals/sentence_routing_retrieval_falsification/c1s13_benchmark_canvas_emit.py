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


def _compact_hit_rows(full: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    hits = list(full.get("hits") or [])
    out: list[dict[str, Any]] = []
    for h in hits[:limit]:
        routes = []
        for route in list(h.get("routes") or [])[:4]:
            if isinstance(route, dict):
                routes.append(str(route.get("normalized_route") or ""))
        out.append(
            {
                "unit_id": str(h.get("unit_id") or ""),
                "line_span": f"L{int(h.get('line_start') or 0)}-{int(h.get('line_end') or 0)}",
                "score": int(h.get("score") or 0),
                "source_recap_path": str(h.get("source_recap_path") or ""),
                "routes": routes,
                "why_matched": [str(x) for x in (h.get("why_matched") or [])],
            }
        )
    return out


def _collect_available_routes(report: dict[str, Any]) -> list[str]:
    src = str(report.get("records_source") or "").strip()
    if not src:
        return []
    p = Path(src)
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
    available_routes = _collect_available_routes(report)
    rows: list[dict[str, Any]] = []
    for scen in gold.get("scenarios") or []:
        sid = str(scen.get("id") or "")
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
        rows.append(
            {
                "id": sid,
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
                "hit_rows": _compact_hit_rows(full, limit=20),
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
