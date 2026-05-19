from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet

PAYLOAD_SCHEMA = "dmb_c1s4_expected_context_canvas_payload_v1"
CANVAS_BLOCK_BEGIN = "// BEGIN GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA"
CANVAS_BLOCK_END = "// END GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA"
CANVAS_CONST_NAME = "c1s4ExpectedContextCanvasData"

_DEFAULT_GOLD_PATH = Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json")

_MODE_SHORT = {
    "prior_only": "Prior only",
    "prior_plus_support_content_only": "Prior + support",
    "prior_plus_support_content_plus_lexical_hints": "Prior + hints",
}


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_gold(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or _DEFAULT_GOLD_PATH).read_text(encoding="utf-8"))


def _ratio(v: Any) -> str:
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _report_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    if "reports_by_mode" in report:
        rows: list[dict[str, Any]] = []
        for mode, mode_report in report["reports_by_mode"].items():
            for row in mode_report.get("results", []):
                x = dict(row)
                x["retrieval_mode"] = mode
                rows.append(x)
        return rows
    return report.get("results", [])



def _known_gap_totals_by_mode_question(gold: dict[str, Any] | None) -> dict[tuple[str, int, str], int]:
    out: dict[tuple[str, int, str], int] = {}
    if not isinstance(gold, dict):
        return out
    for q in gold.get("questions", []):
        qn = int(q.get("question_number") or 0)
        qid = str(q.get("question_id") or "")
        for mode, exp in (q.get("expectations_by_mode") or {}).items():
            out[(mode, qn, qid)] = len(exp.get("expected_known_gaps_contains_any", []))
    return out

def build_payload(*, report: dict[str, Any], gold: dict[str, Any] | None = None, report_path: str | None = None, gold_path: str | None = None) -> dict[str, Any]:
    reports_by_mode = report.get("reports_by_mode") or {report.get("retrieval_mode", "prior_only"): report}
    modes = list(reports_by_mode.keys())
    mode_rows = []
    total_q = total_ok = total_fail = total_forbidden = 0
    req_sum = gap_sum = 0.0
    for mode, mode_report in reports_by_mode.items():
        counts = mode_report.get("counts", {})
        mode_rows.append({
            "mode": mode,
            "questions_evaluated": counts.get("questions_evaluated", 0),
            "rows_ok": counts.get("rows_ok", 0),
            "rows_failed": counts.get("rows_failed", 0),
            "required_group_recall": _ratio((mode_report.get("metrics") or {}).get("macro_required_group_recall_at_k", 0)),
            "forbidden_context_violations": counts.get("forbidden_context_group_violations", 0),
            "known_gap_recall": _ratio((mode_report.get("metrics") or {}).get("known_gap_recall", 0)),
        })
        total_q += int(counts.get("questions_evaluated", 0) or 0)
        total_ok += int(counts.get("rows_ok", 0) or 0)
        total_fail += int(counts.get("rows_failed", 0) or 0)
        total_forbidden += int(counts.get("forbidden_context_group_violations", 0) or 0)
        req_sum += float((mode_report.get("metrics") or {}).get("macro_required_group_recall_at_k", 0) or 0)
        gap_sum += float((mode_report.get("metrics") or {}).get("known_gap_recall", 0) or 0)

    known_gap_totals = _known_gap_totals_by_mode_question(gold)

    question_rows, question_cards = [], []
    for row in _report_rows(report):
        req_groups = row.get("matched_groups") or []
        req_total = int(row.get("required_context_groups") or 0)
        req_hit = int(row.get("required_context_groups_hit") or 0)
        mode = str(row.get("retrieval_mode", report.get("retrieval_mode")))
        qn = int(row.get("question_number") or 0)
        qid = str(row.get("question_id") or "")
        known_gap_hit = len(row.get("known_gap_expectations_hit", []))
        known_gap_total = known_gap_totals.get((mode, qn, qid))
        known_gap_label = f"{known_gap_hit}/{known_gap_total}" if known_gap_total is not None else f"{known_gap_hit}/?"

        rendered_packet = row.get("rendered_context_packet") or render_context_packet({
            "question_number": row.get("question_number"),
            "question_id": row.get("question_id"),
            "question": row.get("question"),
            "retrieval_mode": mode,
            "admission_policy": row.get("admission_policy"),
            "known_context_gaps": row.get("known_context_gaps", []),
            "admitted_context": row.get("admitted_context", []),
            "admission_budget": row.get("admission_budget", {}),
        })

        question_rows.append({
            "question_number": row.get("question_number"),
            "question_id": row.get("question_id"),
            "mode": mode,
            "verdict": "PASS" if row.get("ok") else "FAIL",
            "required_groups": f"{req_hit}/{req_total}",
            "missing_required_groups": row.get("missing_required_groups", []),
            "forbidden_hits": row.get("forbidden_context_groups_hit", []),
            "known_gaps": known_gap_label,
            "violations": row.get("violations", []),
            "rendered_context_packet": rendered_packet,
            "packet_quality_metrics": row.get("packet_quality_metrics"),
        })

        question_cards.append({
            "question_number": row.get("question_number"),
            "question_id": row.get("question_id"),
            "question": row.get("question", ""),
            "mode": mode,
            "mode_short": _MODE_SHORT.get(mode, mode),
            "open_by_default": (not row.get("ok")),
            "verdict": "PASS" if row.get("ok") else "FAIL",
            "required_groups_label": f"{req_hit}/{req_total}",
            "lane_aware_required_groups_hit": int(row.get("lane_aware_required_groups_hit") or 0),
            "expected_behavior": row.get("expected_behavior", ""),
            "required_context_groups": req_groups,
            "missing_required_groups": row.get("missing_required_groups", []),
            "forbidden_context_groups_hit": row.get("forbidden_context_groups_hit", []),
            "known_gap_expectations_hit": row.get("known_gap_expectations_hit", []),
            "authority_summary": row.get("authority_summary", {}),
            "violations": row.get("violations", []),
            "rendered_context_packet": rendered_packet,
            "packet_quality_metrics": row.get("packet_quality_metrics"),
        })

    mode_count = max(1, len(modes))
    payload = {
        "schema": PAYLOAD_SCHEMA,
        "title": "C1S4 Expected Context Benchmark",
        "subtitle": "Step 2C retrieval/context packet evidence review",
        "sources": {"report": report_path or "", "gold": gold_path or str(_DEFAULT_GOLD_PATH)},
        "summary": {
            "modes": modes,
            "modeOptions": [{"value": "all", "label": "All modes"}] + [
                {"value": m, "label": _MODE_SHORT.get(m, m)} for m in modes
            ],
            "statTiles": [
                {"label": "Rows OK", "value": total_ok},
                {"label": "Rows failed", "value": total_fail},
                {"label": "Required recall (avg)", "value": _ratio(req_sum / mode_count)},
                {"label": "Known-gap recall (avg)", "value": _ratio(gap_sum / mode_count)},
                {"label": "Forbidden violations", "value": total_forbidden},
                {"label": "Modes", "value": len(modes)},
            ],
        },
        "modeRows": mode_rows,
        "questionRows": question_rows,
        "questionCards": question_cards,
        "modeDeltas": report.get("mode_deltas", {}),
        "guardrailRows": [
            {"guardrail": "Gold is eval-only", "status": "PASS", "detail": "Payload generated from Step 2C report; no retrieval performed."},
            {"guardrail": "Canvas is projection", "status": "PASS", "detail": "Canonical state remains benchmark JSON; canvas is read-only review UI."},
            {"guardrail": "No oracle material", "status": "PASS", "detail": "Step 2C does not read C1S4 oracle."},
            {"guardrail": "Canvas shell", "status": "INFO", "detail": "UI uses cursor/canvas SDK in canvas_templates/; emitter patches only the generated data block."},
        ],
    }
    return payload


def render_generated_block(payload: dict[str, Any]) -> str:
    dumped = json.dumps(payload, indent=2, sort_keys=True)
    return "\n".join([
        CANVAS_BLOCK_BEGIN,
        "// Auto-generated by evals/c1s4_preplanning_vertical_slice/expected_context_canvas_payload.py",
        "// Do not edit by hand.",
        f"const {CANVAS_CONST_NAME} = {dumped} as const;",
        f"type C1S4ExpectedContextCanvasData = typeof {CANVAS_CONST_NAME};",
        CANVAS_BLOCK_END,
    ])


def update_canvas_text(canvas_text: str, generated_block: str) -> str:
    b, e = canvas_text.find(CANVAS_BLOCK_BEGIN), canvas_text.find(CANVAS_BLOCK_END)
    if b == -1 or e == -1 or e < b:
        raise ValueError("Canvas markers missing: expected generated block markers for Step 2D")
    e += len(CANVAS_BLOCK_END)
    return canvas_text[:b] + generated_block + canvas_text[e:]


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errs = []
    for key in ["schema", "summary", "modeRows", "questionRows", "questionCards", "guardrailRows"]:
        if key not in payload:
            errs.append(f"missing key: {key}")
    if payload.get("schema") != PAYLOAD_SCHEMA:
        errs.append("schema mismatch")
    blob = json.dumps(payload)
    for forbidden in ["c1s4_oracle", "observed_c1s4", "oracle_text", "final_score"]:
        if forbidden in blob:
            errs.append(f"forbidden token in payload: {forbidden}")
    return errs
