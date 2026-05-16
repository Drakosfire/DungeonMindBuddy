from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import PACKET_SCHEMA

EXPECTED_CONTEXT_GOLD_SCHEMA = "dmb_c1s4_expected_context_gold_v1"
EXPECTED_CONTEXT_REPORT_SCHEMA = "dmb_c1s4_expected_context_benchmark_report_v1"
EXPECTED_CONTEXT_MULTIMODE_REPORT_SCHEMA = "dmb_c1s4_expected_context_benchmark_multimode_report_v1"
RETRIEVAL_MODES = [
    "prior_only",
    "prior_plus_support_content_only",
    "prior_plus_support_content_plus_lexical_hints",
]
RetrievalMode = Literal[
    "prior_only",
    "prior_plus_support_content_only",
    "prior_plus_support_content_plus_lexical_hints",
]

DEFAULT_GOLD_PATH = Path(__file__).resolve().parent / "gold/c1s4_expected_context_gold.json"


def _norm(text: Any) -> str:
    value = re.sub(r"[^\w\s:/.-]", " ", str(text or "").lower())
    return " ".join(value.split())


def load_expected_context_gold(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or DEFAULT_GOLD_PATH).read_text(encoding="utf-8"))


def validate_expected_context_gold(gold: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if gold.get("schema") != EXPECTED_CONTEXT_GOLD_SCHEMA:
        errs.append("invalid gold schema")
    if gold.get("planner_visibility") != "forbidden":
        errs.append("planner_visibility must be forbidden")
    role = str(gold.get("artifact_role") or "")
    if role != "eval_only_expected_context_gold":
        errs.append("artifact_role must be eval_only_expected_context_gold")
    if "support" in role or "retrieval" in role:
        errs.append("artifact_role must not imply retrieval visibility")
    if not isinstance(gold.get("default_top_k"), int):
        errs.append("default_top_k missing")
    if not isinstance(gold.get("retrieval_modes"), list):
        errs.append("retrieval_modes missing")
    if not isinstance(gold.get("questions"), list):
        errs.append("questions missing")
    for q in gold.get("questions", []):
        if q.get("question_id") is None or q.get("question_number") is None:
            errs.append("question missing id or number")
        modes = q.get("expectations_by_mode") or {}
        for mode, exp in modes.items():
            if mode not in RETRIEVAL_MODES:
                errs.append(f"unknown mode in question {q.get('question_id')}: {mode}")
            for key in ["required_context_groups", "forbidden_context_groups"]:
                for group in exp.get(key, []):
                    if not group.get("group_id"):
                        errs.append(f"group_id missing in {q.get('question_id')}")
                    if not isinstance(group.get("match"), dict):
                        errs.append(f"match missing in group {group.get('group_id')}")
    return errs


def context_item_text(item: dict[str, Any]) -> str:
    bits: list[str] = []
    for key in ["unit_id", "source_kind", "source_layer", "authority_role", "canon_status", "title", "snippet", "source", "source_reference", "route", "normalized_route", "text"]:
        bits.append(str(item.get(key, "")))
    for route in item.get("routes", []) or []:
        bits.append(str(route.get("normalized_route", "")))
    return _norm(" ".join(bits + [json.dumps(item, sort_keys=True)]))


def context_item_ref(item: dict[str, Any]) -> str:
    return str(item.get("unit_id") or item.get("source_reference") or item.get("title") or "unknown")


def _get_session_values(item: dict[str, Any]) -> set[int]:
    out: set[int] = set()
    for key in ["session_number", "session", "source_session"]:
        v = item.get(key)
        if isinstance(v, int):
            out.add(v)
        elif isinstance(v, str) and v.isdigit():
            out.add(int(v))
    return out


def match_context_item(item: dict[str, Any], match: dict[str, Any]) -> bool:
    text = context_item_text(item)
    checks: list[bool] = []
    scalar_fields = ["source_kind", "source_layer", "authority_role", "canon_status"]
    for f in scalar_fields:
        if f in match:
            checks.append(_norm(item.get(f)) == _norm(match[f]))
        any_key = f"{f}_any"
        if any_key in match:
            checks.append(_norm(item.get(f)) in {_norm(x) for x in match[any_key]})
    contains_fields = ["unit_id", "title", "snippet", "source_reference", "text"]
    for f in contains_fields:
        k = f"{f}_contains_any"
        if k in match:
            field_text = _norm(item.get(f, ""))
            checks.append(any(_norm(tok) in field_text for tok in match[k]))
    if "route_contains_any" in match:
        route_blob = _norm(" ".join([str(item.get("route", "")), str(item.get("normalized_route", "")), str(item.get("source_reference", ""))] + [str((r or {}).get("normalized_route", "")) for r in (item.get("routes", []) or [])]))
        checks.append(any(_norm(tok) in route_blob for tok in match["route_contains_any"]))
    if "text_contains_any" in match:
        checks.append(any(_norm(tok) in text for tok in match["text_contains_any"]))
    if "session_number_any" in match:
        checks.append(bool(_get_session_values(item).intersection({int(x) for x in match["session_number_any"]})))
    return all(checks) if checks else False


def match_context_group(*, retrieved_context: list[dict[str, Any]], group: dict[str, Any], top_k: int) -> dict[str, Any]:
    min_hits = int(group.get("min_hits", 1))
    matched = [context_item_ref(i) for i in retrieved_context[:top_k] if match_context_item(i, group.get("match", {}))]
    return {"group_id": group.get("group_id"), "ok": len(matched) >= min_hits, "min_hits": min_hits, "hit_count": len(matched), "matched_context_refs": matched}


def grade_question_packet(*, packet: dict[str, Any], gold_question: dict[str, Any], retrieval_mode: RetrievalMode, top_k: int) -> dict[str, Any]:
    exp = (gold_question.get("expectations_by_mode") or {}).get(retrieval_mode, {})
    required = exp.get("required_context_groups", [])
    forbidden = exp.get("forbidden_context_groups", [])
    required_matches = [match_context_group(retrieved_context=packet.get("retrieved_context", []), group=g, top_k=top_k) for g in required]
    forbidden_matches = [match_context_group(retrieved_context=packet.get("retrieved_context", []), group=g, top_k=top_k) for g in forbidden]
    known_hits = [term for term in exp.get("expected_known_gaps_contains_any", []) if any(_norm(term) in _norm(g) for g in packet.get("known_context_gaps", []))]
    violations: list[str] = []
    missing_groups = [m["group_id"] for m in required_matches if not m["ok"]]
    forbidden_hits = [m["group_id"] for m in forbidden_matches if m["ok"]]
    if missing_groups:
        violations.append("missing_required_context_group")
    if forbidden_hits:
        violations.append("forbidden_context_group_hit")
    for term in exp.get("expected_known_gaps_contains_any", []):
        if term not in known_hits:
            violations.append("missing_expected_known_gap")
    return {
        "question_number": packet.get("question_number"),
        "question_id": packet.get("question_id"),
        "retrieval_mode": retrieval_mode,
        "top_k": top_k,
        "ok": not violations,
        "expected_behavior": exp.get("expected_behavior", ""),
        "required_context_groups": len(required),
        "required_context_groups_hit": sum(1 for x in required_matches if x["ok"]),
        "required_group_recall_at_k": (sum(1 for x in required_matches if x["ok"]) / len(required)) if required else 1.0,
        "missing_required_groups": missing_groups,
        "forbidden_context_groups": len(forbidden),
        "forbidden_context_groups_hit": forbidden_hits,
        "known_gap_expectations_hit": known_hits,
        "violations": violations,
        "matched_groups": required_matches,
        "authority_summary": packet.get("authority_summary", {}),
    }


def build_expected_context_report(*, packets: list[dict[str, Any]], gold: dict[str, Any], retrieval_mode: RetrievalMode, top_k: int | None = None) -> dict[str, Any]:
    by_q = {int(p.get("question_number")): p for p in packets}
    chosen_top_k = top_k or int(gold.get("default_top_k", 9))
    results = []
    for gq in gold.get("questions", []):
        qn = int(gq.get("question_number"))
        if qn == 35:
            continue
        pkt = by_q.get(qn)
        if not pkt:
            continue
        results.append(grade_question_packet(packet=pkt, gold_question=gq, retrieval_mode=retrieval_mode, top_k=chosen_top_k))
    req_total = sum(r["required_context_groups"] for r in results)
    req_hit = sum(r["required_context_groups_hit"] for r in results)
    row_ok = sum(1 for r in results if r["ok"])
    known_total = sum(len(((q.get("expectations_by_mode") or {}).get(retrieval_mode, {})).get("expected_known_gaps_contains_any", [])) for q in gold.get("questions", []) if int(q.get("question_number", 0)) != 35)
    known_hit = sum(len(r["known_gap_expectations_hit"]) for r in results)
    return {
        "schema": EXPECTED_CONTEXT_REPORT_SCHEMA,
        "campaign_id": gold.get("campaign_id", "longmont-c1"),
        "retrieval_mode": retrieval_mode,
        "gold_path": "evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json",
        "planner_visibility": "forbidden_gold_eval_only",
        "source_packet_schema": PACKET_SCHEMA,
        "counts": {
            "questions_in_gold": len([q for q in gold.get("questions", []) if int(q.get("question_number", 0)) != 35]),
            "questions_evaluated": len(results),
            "rows_ok": row_ok,
            "rows_failed": len(results) - row_ok,
            "required_context_groups": req_total,
            "required_context_groups_hit": req_hit,
            "forbidden_context_group_violations": sum(len(r["forbidden_context_groups_hit"]) for r in results),
            "known_gap_expectations": known_total,
            "known_gap_expectations_hit": known_hit,
        },
        "metrics": {
            "macro_required_group_recall_at_k": (req_hit / req_total) if req_total else 1.0,
            "row_pass_rate": (row_ok / len(results)) if results else 1.0,
            "forbidden_context_violation_rate": (sum(1 for r in results if r["forbidden_context_groups_hit"]) / len(results)) if results else 0.0,
            "known_gap_recall": (known_hit / known_total) if known_total else 1.0,
        },
        "results": results,
    }


def build_multimode_expected_context_report(*, reports_by_mode: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prior = reports_by_mode["prior_only"]
    content = reports_by_mode["prior_plus_support_content_only"]
    lex = reports_by_mode["prior_plus_support_content_plus_lexical_hints"]
    return {
        "schema": EXPECTED_CONTEXT_MULTIMODE_REPORT_SCHEMA,
        "campaign_id": prior.get("campaign_id", "longmont-c1"),
        "modes": RETRIEVAL_MODES,
        "reports_by_mode": reports_by_mode,
        "mode_deltas": {
            "support_content_only_vs_prior_only": {
                "required_group_recall_delta": content["metrics"]["macro_required_group_recall_at_k"] - prior["metrics"]["macro_required_group_recall_at_k"],
                "rows_ok_delta": content["counts"]["rows_ok"] - prior["counts"]["rows_ok"],
                "newly_satisfied_groups": [],
            },
            "lexical_hints_vs_content_only": {
                "required_group_recall_delta": lex["metrics"]["macro_required_group_recall_at_k"] - content["metrics"]["macro_required_group_recall_at_k"],
                "rows_ok_delta": lex["counts"]["rows_ok"] - content["counts"]["rows_ok"],
                "newly_satisfied_groups": [],
            },
        },
    }


def validate_expected_context_report(report: dict[str, Any]) -> list[str]:
    errs = []
    if report.get("schema") != EXPECTED_CONTEXT_REPORT_SCHEMA:
        errs.append("invalid report schema")
    if report.get("planner_visibility") != "forbidden_gold_eval_only":
        errs.append("planner_visibility must be forbidden_gold_eval_only")
    if report.get("source_packet_schema") != PACKET_SCHEMA:
        errs.append("invalid source_packet_schema")
    if report.get("retrieval_mode") not in RETRIEVAL_MODES:
        errs.append("unknown retrieval_mode")
    if not isinstance(report.get("results"), list):
        errs.append("results missing")
    dumped = _norm(json.dumps(report))
    if "c1s4_expected_context_gold.json" in dumped and "gold_path" not in dumped:
        errs.append("gold appears in retrieved content")
    for row in report.get("results", []):
        if row.get("question_number") == 35:
            errs.append("q35 appears as planner-facing benchmark packet")
    return errs
