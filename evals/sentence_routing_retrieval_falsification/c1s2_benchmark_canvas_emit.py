#!/usr/bin/env python3
"""Inject C1S2 breadcrumb harness review data into the Cursor canvas .tsx file.

Reads a ``breadcrumb_query_run`` JSON report (natural gold) plus the gold JSON,
then replaces the region between ``BEGIN GENERATED C1S2_HARNESS_DETAIL`` /
``END GENERATED C1S2_HARNESS_DETAIL`` in the target canvas.

Example::

  uv run python -m evals.sentence_routing_retrieval_falsification.c1s2_benchmark_canvas_emit \\
    --report <path>/breadcrumb_query_natural_c1s2_report.json \\
    --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s2_v1.json \\
    --canvas-tsx ~/.cursor/projects/<workspace-slug>/canvases/c1s2-breadcrumb-query-benchmark-review.canvas.tsx
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.cursor_canvas_paths import (
    default_cursor_canvas_path,
    ensure_canvas_file_for_patch,
)

BLOCK_BEGIN = "// BEGIN GENERATED C1S2_HARNESS_DETAIL"
BLOCK_END = "// END GENERATED C1S2_HARNESS_DETAIL"

_DEFAULT_CANVAS = default_cursor_canvas_path("c1s2-breadcrumb-query-benchmark-review.canvas.tsx")
_FOCUS_SCENARIO_ID = "c1s2_glowkindle_stash_deal"


def _token_in_answer_ci(token: str, answer: str) -> bool:
    if not token or not answer:
        return False
    return token.lower() in answer.lower()


def _compact_hit_rows(full: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    hits = list(full.get("hits") or [])
    hit_rows: list[dict[str, Any]] = []
    for h in hits[:limit]:
        routes = []
        for route in list(h.get("routes") or [])[:4]:
            if isinstance(route, dict):
                routes.append(str(route.get("normalized_route") or ""))
        hit_rows.append(
            {
                "unit_id": str(h.get("unit_id") or ""),
                "line_span": f"L{int(h.get('line_start') or 0)}-{int(h.get('line_end') or 0)}",
                "score": int(h.get("score") or 0),
                "source_recap_path": str(h.get("source_recap_path") or ""),
                "routes": routes,
                "why_matched": [str(x) for x in (h.get("why_matched") or [])],
            }
        )
    return hit_rows


def _focus_payload(*, report: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    scenarios = {str(s.get("id") or ""): s for s in (gold.get("scenarios") or [])}
    row = next(
        (r for r in (report.get("results") or []) if str(r.get("scenario_id") or "") == _FOCUS_SCENARIO_ID),
        {},
    )
    scen = scenarios.get(_FOCUS_SCENARIO_ID, {})
    full = row.get("full_result") if isinstance(row.get("full_result"), dict) else {}
    trace = full.get("trace") if isinstance(full.get("trace"), dict) else {}
    hits = list(full.get("hits") or [])
    hit_rows = _compact_hit_rows(full, limit=12)

    from evals.sentence_routing_retrieval_falsification.breadcrumb_query_llm import _SYSTEM as synthesis_system

    user_template = (
        "Question:\\n{question}\\n\\n"
        "### Retrieved excerpts and routes (only source you may use)\\n"
        "{hit_context}\\n"
    )
    return {
        "scenario_id": _FOCUS_SCENARIO_ID,
        "question": str(scen.get("question") or ""),
        "expected_answer": str(scen.get("expected_answer") or ""),
        "must_hit_tokens": [str(x) for x in (scen.get("must_hit_tokens") or [])],
        "violations": list(row.get("violations") or []),
        "llm_answer_preview": str(row.get("llm_answer_preview") or ""),
        "retrieved_context_preview": str(row.get("retrieved_context") or "")[:2200],
        "retrieval_hit_context_full": str(row.get("retrieval_hit_context_full") or "")[:16000],
        "lexical_hit_context_promoted": str(row.get("retrieved_context") or "")[:16000],
        "llm_user_message": str(row.get("llm_user_message") or "")[:16000],
        "query_tokens": [str(x) for x in (trace.get("query_tokens") or [])],
        "hits_considered": int(trace.get("returned_hits") or len(hits)),
        "hit_rows": hit_rows,
        "context_support_ratio": row.get("context_support_ratio"),
        "llm_context_support_ratio": row.get("llm_context_support_ratio"),
        "llm_semantic_verdict": row.get("llm_semantic_verdict"),
        "llm_semantic_must_hits": list(row.get("llm_semantic_must_hits") or []),
        "workflow_steps": [
            "Normalize breadcrumb markdown into unit-tagged records.",
            "Run deterministic query_session_memory_for_scenario over those records.",
            "Construct hit_context from returned units + route lines.",
            "Synthesize an LLM answer from hit_context only (no direct recap read).",
            "Grade retrieval context and LLM answer separately against must-hit tokens.",
            "Optionally embed expected_answer vs LLM answer for soft similarity telemetry.",
        ],
        "anti_cheat_checks": [
            "The query step is deterministic over normalized records (no LLM in retrieval).",
            "Synthesis prompt receives only question + retrieved_context (lexical unit text; normalized route lines are not copied into the LLM prompt).",
            "Grader reports retrieval ratios separately from llm_context ratios.",
            "Expected answer is used for grading and optional embedding, not retrieval.",
            "Top hit table below exposes concrete units/lines/routes used by retrieval.",
        ],
        "mermaid_flowchart": (
            "flowchart TD\\n"
            "  A[breadcrumbed.md] --> B[normalize_breadcrumb_artifact]\\n"
            "  B --> C[records.jsonl]\\n"
            "  C --> D[natural_retrieval_bundle]\\n"
            "  D --> E[full_result.hits + trace]\\n"
            "  E --> F[hit_context]\\n"
            "  F --> G[LLM synthesis]\\n"
            "  G --> H[grade_natural_scenario]\\n"
            "  E --> H\\n"
            "  H --> I[violations + support ratios]\\n"
            "  G --> J[optional embedding similarity]\\n"
        ),
        "prompts": {
            "retrieval_prompt": "none (deterministic lexical/route query over normalized records)",
            "llm_synthesis_system_prompt": synthesis_system,
            "llm_synthesis_user_template": user_template,
        },
    }


def _build_design_rows(*, gold: dict[str, Any]) -> list[dict[str, Any]]:
    """Gold-derived card metadata (mirrors what C1S1 embeds as static ``candidates``)."""
    out: list[dict[str, Any]] = []
    for scen in gold.get("scenarios") or []:
        sid = str(scen.get("id") or "")
        notes = str(scen.get("notes") or "").strip()
        lane = str(scen.get("benchmark_lane") or "natural")
        if ";" in notes:
            lane = notes.split(";", 1)[0].strip() or lane
        excerpt = str(scen.get("expected_answer") or "")
        if len(excerpt) > 280:
            excerpt = excerpt[:280] + "…"
        out.append(
            {
                "id": sid,
                "lane": lane,
                "question": str(scen.get("question") or ""),
                "sourceLines": [],
                "sourceExcerpt": excerpt,
                "expectedAnswer": str(scen.get("expected_answer") or ""),
                "mustHitTokens": [str(x) for x in (scen.get("must_hit_tokens") or [])],
                "expectedRoutes": [str(x) for x in (scen.get("expect_route_substrings") or [])],
                "newCandidateSignals": [],
                "falsifies": notes or f"Natural gold scenario {sid} (C1S2 Session 2 lane).",
            }
        )
    return out


def _build_rows(
    *, report: dict[str, Any], gold: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    by_id = {str(r.get("scenario_id") or ""): r for r in (report.get("results") or [])}
    rows: list[dict[str, Any]] = []
    for scen in gold.get("scenarios") or []:
        sid = str(scen.get("id") or "")
        r = by_id.get(sid) or {}
        question = str(scen.get("question") or "")
        expected = str(scen.get("expected_answer") or "")
        must_tokens = [str(x) for x in (scen.get("must_hit_tokens") or [])]
        llm_prev = str(r.get("llm_answer_preview") or "")
        emb = r.get("embedding_similarity") if isinstance(r.get("embedding_similarity"), dict) else {}
        cos = emb.get("cosine_similarity")
        keyword_rows = [
            {"token": t, "in_llm_answer_ci": _token_in_answer_ci(t, llm_prev)}
            for t in must_tokens
        ]
        ok = bool(r.get("ok"))
        row_out: dict[str, Any] = {
            "id": sid,
            "ok": ok,
            "question": question,
            "expected_answer": expected,
            "llm_answer_preview": llm_prev,
            "violations": list(r.get("violations") or []),
            "context_support_ratio": r.get("context_support_ratio"),
            "llm_context_support_ratio": r.get("llm_context_support_ratio"),
            "llm_semantic_verdict": r.get("llm_semantic_verdict"),
            "llm_semantic_must_hits": list(r.get("llm_semantic_must_hits") or []),
            "embedding_cosine_similarity": float(cos) if isinstance(cos, (int, float)) else None,
            "embedding_model": emb.get("model"),
            "embedding_cost_usd": emb.get("cost_usd"),
            "keyword_rows": keyword_rows,
        }
        # Canvas nested “retrieved context” accordion: include for every scenario (not only failures).
        full = r.get("full_result") if isinstance(r.get("full_result"), dict) else {}
        row_out["retrieval_hit_context_full"] = str(r.get("retrieval_hit_context_full") or "")[:16000]
        row_out["lexical_hit_context_promoted"] = str(r.get("retrieved_context") or "")[:16000]
        row_out["llm_user_message"] = str(r.get("llm_user_message") or "")[:16000]
        row_out["fail_forensics_hit_rows"] = _compact_hit_rows(full, limit=18)
        rows.append(row_out)

    results = list(report.get("results") or [])
    passed = sum(1 for x in results if x.get("ok"))
    summary = {
        "llmModel": report.get("llm_model"),
        "passCount": passed,
        "scenarioCount": len(results),
        "scenarioEstimatedCostUsd": report.get("scenario_estimated_cost_usd"),
        "aggregateEmbeddingCostUsd": report.get("aggregate_embedding_cost_usd"),
        "embeddingSimilarityEnabled": bool(report.get("embedding_similarity_enabled")),
        "embeddingModel": report.get("embedding_model"),
        "benchmarkReportPath": str(report.get("_emit_report_path") or ""),
    }
    design = _build_design_rows(gold=gold)
    focus = _focus_payload(report=report, gold=gold)
    return rows, summary, focus, design


def _render_block(
    *,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    focus: dict[str, Any],
    design: list[dict[str, Any]],
) -> str:
    body = json.dumps(
        {
            "harnessSummaryGenerated": summary,
            "harnessScenarioDetailGenerated": rows,
            "focusScenarioGenerated": focus,
            "scenarioDesignGenerated": design,
        },
        indent=2,
        ensure_ascii=True,
    )
    return (
        f"{BLOCK_BEGIN}\n"
        "// Generated by c1s2_benchmark_canvas_emit.py — do not hand-edit.\n"
        f"const c1s2HarnessCanvasGenerated = {body} as const;\n"
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


def build_c1s2_canvas_block(
    report: dict[str, Any],
    gold: dict[str, Any],
    *,
    report_path: Path | str | None = None,
) -> str:
    rep = dict(report)
    if report_path is not None:
        rep["_emit_report_path"] = str(Path(report_path).resolve())
    rows, summary, focus, design = _build_rows(report=rep, gold=gold)
    return _render_block(rows=rows, summary=summary, focus=focus, design=design)


def patch_c1s2_canvas_paths(block: str, paths: list[Path]) -> list[dict[str, Any]]:
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


def refresh_c1s2_benchmark_canvases(
    *,
    report: dict[str, Any],
    gold: dict[str, Any],
    report_path: Path | str,
    canvas_paths: list[Path],
) -> dict[str, Any]:
    block = build_c1s2_canvas_block(report, gold, report_path=report_path)
    per_file = patch_c1s2_canvas_paths(block, canvas_paths)
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


def c1s2_canvas_refresh_auto_enabled(*, gold_path: Path, gold: dict[str, Any]) -> bool:
    if str(gold.get("schema") or "") != "dmb_breadcrumb_query_natural_gold_v1":
        return False
    if "c1s2" in gold_path.name.lower():
        return True
    for scen in gold.get("scenarios") or []:
        if str(scen.get("id") or "").startswith("c1s2_"):
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
    block = build_c1s2_canvas_block(report, gold, report_path=args.report)
    per_file = patch_c1s2_canvas_paths(block, targets)
    errors = [x for x in per_file if "error" in x]
    if errors:
        err_msg = "; ".join(str(e.get("error", e)) for e in errors)
        raise SystemExit(f"c1s2_benchmark_canvas_emit: canvas patch failed: {err_msg}")
    row_n = len(list(gold.get("scenarios") or []))
    for item in per_file:
        if "canvas_updated" in item:
            item["rows"] = row_n
    print(json.dumps({"targets": per_file}, indent=2))


if __name__ == "__main__":
    main()
