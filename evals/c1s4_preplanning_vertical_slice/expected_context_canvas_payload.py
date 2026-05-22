from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import (
    iter_target_questions,
    load_beat_question_targets,
)
from evals.c1s4_preplanning_vertical_slice.context_quality_metrics import compute_packet_quality_metrics
from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet
from evals.c1s4_preplanning_vertical_slice.planner_surface_coverage import (
    RETRIEVAL_MODES,
    TIER_A_QUESTIONS,
    build_planner_surface_rows,
    lookup_step2_packet,
    summarize_planner_surface_rows,
)

PAYLOAD_SCHEMA = "dmb_c1s4_expected_context_canvas_payload_v1"
CANVAS_BLOCK_BEGIN = "// BEGIN GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA"
CANVAS_BLOCK_END = "// END GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA"
CANVAS_CONST_NAME = "c1s4ExpectedContextCanvasData"

_DEFAULT_GOLD_PATH = Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json")
_DEFAULT_TARGETS_PATH = Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_beat_question_targets.json")
_DEFAULT_PR66_DIAGNOSTICS_PATH = Path(
    "evals/c1s4_preplanning_vertical_slice/artifacts/pr66/pr66_support_affordance_diagnostics.json"
)

_MODE_SHORT = {
    "prior_only": "Prior only",
    "prior_plus_support_content_only": "Prior + support",
    "prior_plus_support_content_plus_lexical_hints": "Prior + support + retrieval terms",
}

MODE_GUIDE: dict[str, Any] = {
    "title": "Retrieval field policy (what each lane means after PR66)",
    "scope": (
        "This canvas reviews all 38 C1S4 benchmark planning questions (Q1–Q38). "
        "Q35 is evaluator-only in every mode. Each planner-facing question appears once per "
        "retrieval mode (37 × 3 = 111 rows). Expand any card to inspect the rendered LLM context "
        "the planner would receive. PR66 adds deterministic planner affordances as a source-derived "
        "retrieval bridge for support cards. Support-enabled lanes may use those affordances; prior-only "
        "is still a boundary/control lane where support absence is policy-correct."
    ),
    "decision": (
        "The demo path is now provenance-safe support retrieval: support cards meet GM-prep questions "
        "through controlled-vocabulary planner affordances derived from title/summary/retrieval-visible "
        "fields, not through question IDs, usable_for_questions, or gold metadata."
    ),
    "modes": [
        {
            "id": "prior_only",
            "label": _MODE_SHORT["prior_only"],
            "summary": "Session/campaign memory only — no support-knowledge cards.",
            "includes": ["Prior recap memory", "Source-derived context gaps", "Admission policy metadata"],
            "excludes": ["Support-knowledge cards (even if indexed)"],
            "diagnostic_use": "Control lane: catches support leakage and shows what prior memory alone knows.",
        },
        {
            "id": "prior_plus_support_content_only",
            "label": _MODE_SHORT["prior_plus_support_content_only"],
            "summary": "Prior memory plus support cards retrieved on title, summary, and source-derived planner affordances.",
            "includes": ["Everything in prior_only", "Support cards matched on title/summary", "Planner affordances derived from title/summary"],
            "excludes": ["retrieval_terms field on support cards"],
            "diagnostic_use": "Ablation lane: isolates source-derived affordance retrieval without hand-authored retrieval_terms.",
        },
        {
            "id": "prior_plus_support_content_plus_lexical_hints",
            "label": _MODE_SHORT["prior_plus_support_content_plus_lexical_hints"],
            "summary": "Demo lane: prior + support with title, summary, source-derived planner affordances, and support-card retrieval_terms.",
            "includes": ["Everything in prior + support", "retrieval_terms field on support cards", "Planner affordances may also use retrieval_terms as visible basis"],
            "excludes": [],
            "diagnostic_use": "Demo policy: use support rank, admission, rendered status, and match-channel diagnostics to prove why retrieval improved.",
        },
    ],
    "verdict_legend": [
        {"verdict": "PASS", "meaning": "Strict gold expectations satisfied (Q1, Q3, Q5 only)."},
        {"verdict": "FAIL", "meaning": "Strict gold expectations failed (missing required groups, forbidden hits, etc.)."},
        {"verdict": "GREEN", "meaning": "Heuristic surface ok_or_later_stage — retrieval may still be thin; not strict-gold graded."},
        {"verdict": "REVIEW", "meaning": "Classified failure surface (support missing, policy gap, etc.) — inspect rendered context."},
        {"verdict": "BOUNDARY_FAIL", "meaning": "Hard prompt/control boundary violated — must stay at zero."},
        {"verdict": "EVALUATOR", "meaning": "Question is not planner-facing in this mode (e.g. Q35)."},
    ],
    "contracts": [
        "evals/c1s4_preplanning_vertical_slice/support_knowledge/SUPPORT_KNOWLEDGE_RETRIEVAL_CONTRACT.md",
        "evals/c1s4_preplanning_vertical_slice/gold/c1s4_beat_question_targets.json",
    ],
}

DEMO_MODE = "prior_plus_support_content_plus_lexical_hints"
SUPPORT_CONTENT_ONLY_MODE = "prior_plus_support_content_only"


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


def _report_index(report: dict[str, Any] | None) -> dict[tuple[str, int, str], dict[str, Any]]:
    out: dict[tuple[str, int, str], dict[str, Any]] = {}
    if not isinstance(report, dict):
        return out
    for row in _report_rows(report):
        mode = str(row.get("retrieval_mode") or report.get("retrieval_mode") or "")
        qn = int(row.get("question_number") or 0)
        qid = str(row.get("question_id") or "")
        out[(mode, qn, qid)] = row
    return out


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


def _question_text_by_number() -> dict[int, str]:
    targets = load_beat_question_targets()
    return {int(q.get("question_number") or 0): str(q.get("question") or "") for q in iter_target_questions(targets)}


def _admitted_preview(packet: dict[str, Any] | None, *, limit: int = 8) -> list[dict[str, Any]]:
    if not packet:
        return []
    preview: list[dict[str, Any]] = []
    for item in packet.get("admitted_context") or []:
        if not isinstance(item, dict):
            continue
        preview.append(
            {
                "ref": item.get("unit_id") or item.get("ref") or item.get("source_reference"),
                "source_kind": item.get("source_kind"),
                "title": str(item.get("title") or "")[:120],
                "presentation_lane": item.get("presentation_lane"),
            }
        )
        if len(preview) >= limit:
            break
    return preview


def _card_verdict(
    *,
    row: dict[str, Any],
    report_row: dict[str, Any] | None,
    qn: int,
) -> tuple[str, str]:
    """Return (verdict, grading_tier)."""
    if not row.get("planner_facing"):
        return "EVALUATOR", "evaluator_only"
    if row.get("prompt_payload_valid") is False:
        return "BOUNDARY_FAIL", "hard_boundary"
    if report_row is not None and qn in TIER_A_QUESTIONS:
        return ("PASS" if report_row.get("ok") else "FAIL"), "strict_gold"
    surface = str(row.get("next_failure_surface") or "")
    if surface == "ok_or_later_stage":
        return "GREEN", "heuristic"
    return "REVIEW", "heuristic"


def _build_surface_question_cards(
    *,
    report: dict[str, Any] | None,
    gold: dict[str, Any] | None,
    include_generated_answer: bool = False,
    max_hits: int = 50,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows = build_planner_surface_rows(
        include_evaluator_only=True,
        include_generated_answer=include_generated_answer,
        max_hits=max_hits,
    )
    summary = summarize_planner_surface_rows(rows)
    report_idx = _report_index(report)
    known_gap_totals = _known_gap_totals_by_mode_question(gold)
    q_text = _question_text_by_number()

    question_rows: list[dict[str, Any]] = []
    question_cards: list[dict[str, Any]] = []

    for row in rows:
        mode = str(row.get("mode") or "")
        qn = int(row.get("question_number") or 0)
        qid = str(row.get("question_id") or "")
        planner_facing = row.get("planner_facing") is not False
        report_row = report_idx.get((mode, qn, qid))
        packet = lookup_step2_packet(mode=mode, question_number=qn, max_hits=max_hits) if planner_facing else None

        rendered_packet: dict[str, Any] = {}
        metrics: dict[str, Any] = {}
        source_gaps: list[Any] = []
        if packet:
            rendered_packet = render_context_packet(
                {
                    "question_number": qn,
                    "question_id": qid,
                    "question": q_text.get(qn, ""),
                    "retrieval_mode": mode,
                    "admission_policy": packet.get("admission_policy"),
                    "admitted_context": packet.get("admitted_context", []),
                    "admission_budget": packet.get("admission_budget", {}),
                    "source_derived_context_gaps": packet.get("source_derived_context_gaps", []),
                }
            )
            metrics = compute_packet_quality_metrics(
                row={**row, **packet},
                packet=packet,
                rendered_context_packet=rendered_packet,
            )
            source_gaps = list(packet.get("source_derived_context_gaps") or [])

        verdict, grading_tier = _card_verdict(row=row, report_row=report_row, qn=qn)
        surface = str(row.get("next_failure_surface") or "")

        req_hit = int((report_row or {}).get("required_context_groups_hit") or 0)
        req_total = int((report_row or {}).get("required_context_groups") or 0)
        req_label = f"{req_hit}/{req_total}" if report_row and req_total else ("n/a" if grading_tier != "strict_gold" else "—")

        known_gap_hit = len((report_row or {}).get("known_gap_expectations_hit") or [])
        known_gap_total = known_gap_totals.get((mode, qn, qid))
        known_gap_label = f"{known_gap_hit}/{known_gap_total}" if known_gap_total is not None else (f"{known_gap_hit}/?" if known_gap_hit else "—")

        open_by_default = (
            verdict in {"FAIL", "BOUNDARY_FAIL", "REVIEW"}
            or surface not in {"ok_or_later_stage", "evaluator_only_not_planner_facing"}
        )

        compact = {
            "question_number": qn,
            "question_id": qid,
            "beat_id": row.get("beat_id"),
            "mode": mode,
            "verdict": verdict,
            "grading_tier": grading_tier,
            "next_failure_surface": surface,
            "required_groups": req_label,
            "known_gaps": known_gap_label,
            "violations": list((report_row or {}).get("violations") or []),
            "rendered_context_packet": rendered_packet,
            "packet_quality_metrics": metrics,
        }
        question_rows.append(compact)

        question_cards.append(
            {
                **compact,
                "question": q_text.get(qn, ""),
                "mode_short": _MODE_SHORT.get(mode, mode),
                "planner_facing": planner_facing,
                "open_by_default": open_by_default,
                "authority_label": row.get("authority_label"),
                "oracle_risk": row.get("oracle_risk"),
                "expected_mode_behavior": row.get("expected_mode_behavior"),
                "expected_behavior": (report_row or {}).get("expected_behavior") or row.get("expected_mode_behavior"),
                "retrieval_sufficiency_class": row.get("retrieval_sufficiency_class"),
                "support_policy_status": row.get("support_policy_status"),
                "support_required": row.get("support_required"),
                "support_context_rendered": row.get("support_context_rendered"),
                "first_support_candidate_rank": row.get("first_support_candidate_rank"),
                "first_support_admitted_rank": row.get("first_support_admitted_rank"),
                "support_token_share": row.get("support_token_share"),
                "prompt_payload_valid": row.get("prompt_payload_valid"),
                "source_derived_gap_count": row.get("source_derived_gap_count"),
                "source_derived_context_gaps": source_gaps[:12],
                "known_context_gaps_leaked": row.get("known_context_gaps_leaked"),
                "generated_answer_control_leak": row.get("generated_answer_control_leak"),
                "required_groups_label": req_label,
                "lane_aware_required_groups_hit": int((report_row or {}).get("lane_aware_required_groups_hit") or 0),
                "required_context_groups": (report_row or {}).get("matched_groups") or [],
                "missing_required_groups": (report_row or {}).get("missing_required_groups") or [],
                "forbidden_context_groups_hit": (report_row or {}).get("forbidden_context_groups_hit") or [],
                "known_gap_expectations_hit": (report_row or {}).get("known_gap_expectations_hit") or [],
                "authority_summary": (report_row or {}).get("authority_summary") or {},
                "admitted_context_preview": _admitted_preview(packet),
                "admitted_context_count": row.get("admitted_context_count"),
                "estimated_rendered_tokens": row.get("estimated_rendered_tokens"),
            }
        )

    return question_rows, question_cards, rows, summary


def _rank_label(value: Any) -> str:
    return "miss" if value in {None, ""} else str(value)


def _load_pr66_affordance_diagnostics(path: Path | None = None) -> dict[str, Any]:
    diag_path = path or _DEFAULT_PR66_DIAGNOSTICS_PATH
    if not diag_path.exists():
        return {}
    return json.loads(diag_path.read_text(encoding="utf-8"))


def _pr66_row_key(row: dict[str, Any]) -> tuple[str, int, str]:
    return (str(row.get("mode") or ""), int(row.get("question_number") or 0), str(row.get("question_id") or ""))


def _pr66_affordance_summary(diagnostics: dict[str, Any]) -> dict[str, Any]:
    rows = list(diagnostics.get("rows") or [])
    family_a_numbers = {10, 11, 20}
    family_a_rows = [
        r
        for r in rows
        if int(r.get("question_number") or 0) in family_a_numbers
        and r.get("support_allowed_for_mode")
    ]
    prior_policy_rows = [
        r
        for r in rows
        if str(r.get("mode") or "") == "prior_only"
        and str(r.get("authority_label") or "") == "support_knowledge_required"
    ]
    rendered = sum(1 for r in family_a_rows if r.get("required_support_rendered"))
    affordance_channel = sum(
        1
        for r in family_a_rows
        if (r.get("support_match_channels") or {}).get("planner_affordances")
    )
    title_summary_channel = sum(
        1
        for r in family_a_rows
        if (r.get("support_match_channels") or {}).get("title_summary")
    )
    retrieval_terms_channel = sum(
        1
        for r in family_a_rows
        if (r.get("support_match_channels") or {}).get("retrieval_terms")
    )
    policy_correct = sum(
        1
        for r in prior_policy_rows
        if r.get("next_failure_surface") == "support_required_policy_suppressed_expected"
    )
    return {
        "schema": "dmb_c1s4_pr66_affordance_canvas_summary_v1",
        "artifactPath": str(_DEFAULT_PR66_DIAGNOSTICS_PATH),
        "rows": rows,
        "familyARows": family_a_rows,
        "counts": {
            "diagnostic_rows": len(rows),
            "family_a_support_rows": len(family_a_rows),
            "family_a_required_support_rendered": rendered,
            "family_a_planner_affordance_channel": affordance_channel,
            "family_a_title_summary_channel": title_summary_channel,
            "family_a_retrieval_terms_channel": retrieval_terms_channel,
            "prior_only_policy_correct_suppression": policy_correct,
            "prior_only_support_required_rows": len(prior_policy_rows),
        },
        "notes": [
            "expected_support_refs_eval_only is diagnostic-only; it is not used for retrieval, ranking, indexing, or admission.",
            "planner_affordances means the support card and question met through controlled vocabulary, not benchmark IDs.",
            "prior-only support-required rows should show policy-correct suppression, not retrieval failure.",
        ],
    }


def _support_field_policy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_question: dict[int, dict[str, Any]] = defaultdict(dict)
    question_ids: dict[int, str] = {}
    beat_ids: dict[int, str] = {}
    for row in rows:
        if not row.get("planner_facing") or not row.get("support_required"):
            continue
        mode = str(row.get("mode") or "")
        if mode not in {SUPPORT_CONTENT_ONLY_MODE, DEMO_MODE}:
            continue
        qn = int(row.get("question_number") or 0)
        by_question[qn][mode] = row
        question_ids[qn] = str(row.get("question_id") or "")
        beat_ids[qn] = str(row.get("beat_id") or "")

    out: list[dict[str, Any]] = []
    for qn in sorted(by_question):
        content = by_question[qn].get(SUPPORT_CONTENT_ONLY_MODE) or {}
        terms = by_question[qn].get(DEMO_MODE) or {}
        content_candidate = content.get("first_support_candidate_rank")
        terms_candidate = terms.get("first_support_candidate_rank")
        content_admitted = content.get("first_support_admitted_rank")
        terms_admitted = terms.get("first_support_admitted_rank")
        content_token_share = float(content.get("support_token_share") or 0)
        terms_token_share = float(terms.get("support_token_share") or 0)

        out.append(
            {
                "question_number": qn,
                "question_id": question_ids.get(qn, ""),
                "beat_id": beat_ids.get(qn, ""),
                "content_only_candidate_rank": content_candidate,
                "retrieval_terms_candidate_rank": terms_candidate,
                "candidate_delta": (
                    int(content_candidate) - int(terms_candidate)
                    if content_candidate is not None and terms_candidate is not None
                    else None
                ),
                "content_only_admitted_rank": content_admitted,
                "retrieval_terms_admitted_rank": terms_admitted,
                "admitted_delta": (
                    int(content_admitted) - int(terms_admitted)
                    if content_admitted is not None and terms_admitted is not None
                    else None
                ),
                "content_only_candidate_hit": content_candidate is not None,
                "retrieval_terms_candidate_hit": terms_candidate is not None,
                "content_only_admitted_hit": content_admitted is not None,
                "retrieval_terms_admitted_hit": terms_admitted is not None,
                "content_only_support_token_share": round(content_token_share, 4),
                "retrieval_terms_support_token_share": round(terms_token_share, 4),
                "support_token_share_delta": round(terms_token_share - content_token_share, 4),
                "content_only_surface": content.get("next_failure_surface"),
                "retrieval_terms_surface": terms.get("next_failure_surface"),
            }
        )
    return out


def _support_field_policy_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = _support_field_policy_rows(rows)
    candidate_lift = sum(
        1
        for row in comparisons
        if not row["content_only_candidate_hit"] and row["retrieval_terms_candidate_hit"]
    )
    admitted_lift = sum(
        1
        for row in comparisons
        if not row["content_only_admitted_hit"] and row["retrieval_terms_admitted_hit"]
    )
    rank_improvements = sum(
        1
        for row in comparisons
        if row["candidate_delta"] is not None and int(row["candidate_delta"]) > 0
    )
    token_share_improvements = sum(
        1 for row in comparisons if float(row["support_token_share_delta"] or 0) > 0
    )
    return {
        "schema": "dmb_c1s4_support_field_policy_summary_v1",
        "demo_mode": DEMO_MODE,
        "ablation_mode": SUPPORT_CONTENT_ONLY_MODE,
        "rows": comparisons,
        "counts": {
            "support_required_questions": len(comparisons),
            "candidate_lift_from_retrieval_terms": candidate_lift,
            "admitted_lift_from_retrieval_terms": admitted_lift,
            "candidate_rank_improvements": rank_improvements,
            "support_token_share_increases": token_share_improvements,
        },
        "decision_note": (
            "Use source-derived planner affordances plus retrieval_terms as the demo support retrieval field policy; "
            "keep content-only affordances as an ablation and prior-only as a boundary/control lane."
        ),
        "metric_note": (
            "A zero pass/fail delta can still hide retrieval movement. Compare required support rank, "
            "first admitted rank, match channels, and support token share."
        ),
    }


def _mode_rows_from_planner_rows(rows: list[dict[str, Any]], report: dict[str, Any] | None) -> list[dict[str, Any]]:
    by_mode: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "green": 0, "non_green": 0, "support_missing": 0})
    for row in rows:
        if not row.get("planner_facing"):
            continue
        mode = str(row.get("mode") or "")
        by_mode[mode]["total"] += 1
        surface = str(row.get("next_failure_surface") or "")
        if surface == "ok_or_later_stage":
            by_mode[mode]["green"] += 1
        else:
            by_mode[mode]["non_green"] += 1
        if row.get("retrieval_sufficiency_class") == "support_expected_but_missing":
            by_mode[mode]["support_missing"] += 1

    strict_by_mode: dict[str, dict[str, int]] = defaultdict(lambda: {"ok": 0, "failed": 0, "evaluated": 0})
    if report:
        for row in _report_rows(report):
            mode = str(row.get("retrieval_mode") or report.get("retrieval_mode") or "")
            strict_by_mode[mode]["evaluated"] += 1
            if row.get("ok"):
                strict_by_mode[mode]["ok"] += 1
            else:
                strict_by_mode[mode]["failed"] += 1

    mode_rows: list[dict[str, Any]] = []
    for mode in RETRIEVAL_MODES:
        agg = by_mode.get(mode, {})
        strict = strict_by_mode.get(mode, {})
        mode_rows.append(
            {
                "mode": mode,
                "planner_rows": agg.get("total", 0),
                "surface_green": agg.get("green", 0),
                "surface_non_green": agg.get("non_green", 0),
                "support_expected_missing": agg.get("support_missing", 0),
                "strict_gold_evaluated": strict.get("evaluated", 0),
                "strict_gold_ok": strict.get("ok", 0),
                "strict_gold_failed": strict.get("failed", 0),
            }
        )
    return mode_rows


def _build_planner_surface_section(*, include_generated_answer: bool = False) -> dict[str, Any]:
    rows = build_planner_surface_rows(include_evaluator_only=True, include_generated_answer=include_generated_answer)
    summary = summarize_planner_surface_rows(rows)
    compact_rows: list[dict[str, Any]] = []
    for row in rows:
        surface = str(row.get("next_failure_surface") or "")
        compact_rows.append(
            {
                "question_number": row.get("question_number"),
                "question_id": row.get("question_id"),
                "beat_id": row.get("beat_id"),
                "mode": row.get("mode"),
                "planner_facing": row.get("planner_facing"),
                "authority_label": row.get("authority_label"),
                "next_failure_surface": surface,
                "retrieval_sufficiency_class": row.get("retrieval_sufficiency_class"),
                "support_policy_status": row.get("support_policy_status"),
            }
        )
    hard = summary.get("hard_boundary_failures") or {}
    return {
        "schema": "dmb_pr65_planner_surface_canvas_section_v1",
        "artifactPath": "evals/c1s4_preplanning_vertical_slice/artifacts/pr65/pr65_planner_surface_summary.json",
        "summary": summary,
        "failureSurfaceCounts": summary.get("failure_surface_counts") or {},
        "coverageByClass": summary.get("coverage_by_class") or {},
        "rows": compact_rows,
    }


def _legacy_cards_from_report(
    report: dict[str, Any],
    gold: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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

        rendered_packet = row.get("rendered_context_packet") or render_context_packet(
            {
                "question_number": row.get("question_number"),
                "question_id": row.get("question_id"),
                "question": row.get("question"),
                "retrieval_mode": mode,
                "admission_policy": row.get("admission_policy"),
                "admitted_context": row.get("admitted_context", []),
                "admission_budget": row.get("admission_budget", {}),
                "source_derived_context_gaps": row.get("source_derived_context_gaps", []),
            }
        )

        question_rows.append(
            {
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
            }
        )

        question_cards.append(
            {
                "question_number": row.get("question_number"),
                "question_id": row.get("question_id"),
                "question": row.get("question", ""),
                "mode": mode,
                "mode_short": _MODE_SHORT.get(mode, mode),
                "open_by_default": not row.get("ok"),
                "verdict": "PASS" if row.get("ok") else "FAIL",
                "grading_tier": "strict_gold",
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
                "planner_facing": True,
            }
        )
    return question_rows, question_cards


def build_payload(
    *,
    report: dict[str, Any] | None = None,
    gold: dict[str, Any] | None = None,
    report_path: str | None = None,
    gold_path: str | None = None,
    include_planner_surface: bool = True,
    include_full_surface: bool = True,
) -> dict[str, Any]:
    surface_summary: dict[str, Any] = {}
    surface_rows: list[dict[str, Any]] = []
    pr66_diagnostics = _load_pr66_affordance_diagnostics()
    pr66_summary = _pr66_affordance_summary(pr66_diagnostics) if pr66_diagnostics else {}
    pr66_by_key = {_pr66_row_key(row): row for row in pr66_summary.get("rows", [])} if pr66_summary else {}
    if include_full_surface:
        question_rows, question_cards, surface_rows, surface_summary = _build_surface_question_cards(
            report=report,
            gold=gold,
            include_generated_answer=False,
        )
        if pr66_by_key:
            for card in question_cards:
                diag = pr66_by_key.get(
                    (
                        str(card.get("mode") or ""),
                        int(card.get("question_number") or 0),
                        str(card.get("question_id") or ""),
                    )
                )
                if diag:
                    card["pr66_affordance_diagnostics"] = diag
    elif report:
        question_rows, question_cards = _legacy_cards_from_report(report, gold)
    else:
        question_rows, question_cards = [], []

    modes = list(RETRIEVAL_MODES)
    mode_rows = _mode_rows_from_planner_rows(surface_rows, report) if include_full_surface else []

    if not mode_rows and report:
        reports_by_mode = report.get("reports_by_mode") or {report.get("retrieval_mode", "prior_only"): report}
        modes = list(reports_by_mode.keys())
        mode_rows = []
        for mode, mode_report in reports_by_mode.items():
            counts = mode_report.get("counts", {})
            mode_rows.append(
                {
                    "mode": mode,
                    "strict_gold_evaluated": counts.get("questions_evaluated", 0),
                    "strict_gold_ok": counts.get("rows_ok", 0),
                    "strict_gold_failed": counts.get("rows_failed", 0),
                    "required_group_recall": _ratio((mode_report.get("metrics") or {}).get("macro_required_group_recall_at_k", 0)),
                    "forbidden_context_violations": counts.get("forbidden_context_group_violations", 0),
                    "known_gap_recall": _ratio((mode_report.get("metrics") or {}).get("known_gap_recall", 0)),
                }
            )

    hard = surface_summary.get("hard_boundary_failures") or {}
    hard_total = sum(int(v or 0) for v in hard.values()) if hard else 0
    failure_counts = surface_summary.get("failure_surface_counts") or {}
    non_green = sum(
        int(v or 0)
        for k, v in failure_counts.items()
        if k not in {"ok_or_later_stage", "evaluator_only_not_planner_facing"}
    )

    stat_tiles = [
        {"label": "Planner rows", "value": surface_summary.get("planner_surface_rows", len(question_cards))},
        {"label": "Surface green", "value": failure_counts.get("ok_or_later_stage", 0)},
        {"label": "Needs review", "value": non_green},
        {"label": "Hard boundary hits", "value": hard_total},
        {"label": "Tier A strict OK", "value": surface_summary.get("tier_a_ok_rows", 0)},
        {"label": "Questions", "value": 38},
    ]

    payload = {
        "schema": PAYLOAD_SCHEMA,
        "title": "C1S4 Planner Context Review",
        "subtitle": "Demo lane: prior + support content + retrieval_terms; content-only and prior-only are controls",
        "sources": {
            "report": report_path or "",
            "gold": gold_path or str(_DEFAULT_GOLD_PATH),
            "targets": str(_DEFAULT_TARGETS_PATH),
        },
        "modeGuide": MODE_GUIDE,
        "supportFieldPolicy": _support_field_policy_summary(surface_rows) if include_full_surface else {},
        "plannerAffordanceDiagnostics": pr66_summary if include_full_surface else {},
        "summary": {
            "modes": modes,
            "modeOptions": [{"value": "all", "label": "All modes"}]
            + [{"value": m, "label": _MODE_SHORT.get(m, m)} for m in modes],
            "statTiles": stat_tiles,
            "surfaceSummary": surface_summary,
        },
        "modeRows": mode_rows,
        "questionRows": question_rows,
        "questionCards": question_cards,
        "modeDeltas": (report or {}).get("mode_deltas", {}),
        "guardrailRows": [
            {
                "guardrail": "Full surface coverage",
                "status": "PASS" if include_full_surface else "INFO",
                "detail": "111 planner rows (37×3) plus evaluator-only Q35; each card includes rendered_context_packet.",
            },
            {
                "guardrail": "Demo retrieval field policy",
                "status": "INFO",
                "detail": "Primary demo lane uses source-derived planner affordances plus retrieval_terms; content-only is affordance-without-retrieval_terms ablation and prior-only is a boundary/control lane.",
            },
            {
                "guardrail": "PR66 affordance provenance",
                "status": "PASS" if pr66_summary else "INFO",
                "detail": "Planner affordance diagnostics loaded from PR66 artifact; expected support refs are eval-only diagnostics, not retrieval inputs.",
            },
            {
                "guardrail": "Gold is eval-only",
                "status": "PASS",
                "detail": "Strict PASS/FAIL verdict only on Q1/Q3/Q5 where gold exists; other rows use heuristic surfaces.",
            },
            {
                "guardrail": "Canvas is projection",
                "status": "PASS",
                "detail": "Canonical state remains benchmark JSON; canvas is read-only review UI.",
            },
            {
                "guardrail": "Canvas shell",
                "status": "INFO",
                "detail": "UI uses cursor/canvas SDK in canvas_templates/; emitter patches only the generated data block.",
            },
        ],
    }
    if include_planner_surface:
        payload["plannerSurfaceCoverage"] = _build_planner_surface_section()
    return payload


def render_generated_block(payload: dict[str, Any]) -> str:
    dumped = json.dumps(payload, indent=2, sort_keys=True)
    return "\n".join(
        [
            CANVAS_BLOCK_BEGIN,
            "// Auto-generated by evals/c1s4_preplanning_vertical_slice/expected_context_canvas_payload.py",
            "// Do not edit by hand.",
            f"const {CANVAS_CONST_NAME} = {dumped} as const;",
            f"type C1S4ExpectedContextCanvasData = typeof {CANVAS_CONST_NAME};",
            CANVAS_BLOCK_END,
        ]
    )


def update_canvas_text(canvas_text: str, generated_block: str) -> str:
    b, e = canvas_text.find(CANVAS_BLOCK_BEGIN), canvas_text.find(CANVAS_BLOCK_END)
    if b == -1 or e == -1 or e < b:
        raise ValueError("Canvas markers missing: expected generated block markers for Step 2D")
    e += len(CANVAS_BLOCK_END)
    return canvas_text[:b] + generated_block + canvas_text[e:]


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errs = []
    for key in ["schema", "summary", "modeRows", "questionRows", "questionCards", "guardrailRows", "modeGuide"]:
        if key not in payload:
            errs.append(f"missing key: {key}")
    if payload.get("schema") != PAYLOAD_SCHEMA:
        errs.append("schema mismatch")
    blob = json.dumps(payload)
    for forbidden in ["c1s4_oracle", "observed_c1s4", "oracle_text", "final_score"]:
        if forbidden in blob:
            errs.append(f"forbidden token in payload: {forbidden}")
    cards = payload.get("questionCards") or []
    if len(cards) >= 100:
        planner = [c for c in cards if c.get("planner_facing") is not False and c.get("verdict") != "EVALUATOR"]
        missing_render = [c for c in planner if not (c.get("rendered_context_packet") or {}).get("schema")]
        if missing_render:
            errs.append(f"{len(missing_render)} planner cards missing rendered_context_packet")
    return errs
