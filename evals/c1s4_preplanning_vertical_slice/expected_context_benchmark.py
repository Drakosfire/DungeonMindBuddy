from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Literal

from evals.c1s4_preplanning_vertical_slice.context_admission import estimate_context_item_size, render_context_item_for_budget

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import PACKET_SCHEMA, iter_target_questions, load_beat_question_targets

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
LEAKAGE_TOKENS = ["c1s4_expected_context_gold.json", "c1s4_beat_question_targets.json"]
SUPPORT_KIND = "support_knowledge_card"

DEFAULT_GOLD_PATH = Path(__file__).resolve().parent / "gold/c1s4_expected_context_gold.json"


def _norm(text: Any) -> str:
    value = str(text or "").lower().replace("_", " ")
    value = re.sub(r"[^\w\s:/.-]", " ", value)
    return " ".join(value.split())


def _contains_norm(haystack: str, needle: str) -> bool:
    h = _norm(haystack)
    n = _norm(needle)
    if not n:
        return False
    if n in h:
        return True
    return n.replace(" ", "") in h.replace(" ", "")


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

    target_questions = {int(q.get("question_number")): q for q in iter_target_questions(load_beat_question_targets())}

    for q in gold.get("questions", []):
        qn = q.get("question_number")
        qid = q.get("question_id")
        if qid is None or qn is None:
            errs.append("question missing id or number")
            continue
        tq = target_questions.get(int(qn))
        if not tq:
            errs.append(f"gold question not in targets: {qid}")
            continue
        if qid != tq.get("question_id"):
            errs.append(f"question_id drift for q{qn}")
        if q.get("authority_label") != tq.get("authority_label"):
            errs.append(f"authority_label drift for q{qn}")
        if q.get("oracle_risk") != tq.get("oracle_risk"):
            errs.append(f"oracle_risk drift for q{qn}")

        modes = q.get("expectations_by_mode") or {}
        for mode, exp in modes.items():
            if mode not in RETRIEVAL_MODES:
                errs.append(f"unknown mode in question {qid}: {mode}")
            for key in ["required_context_groups", "forbidden_context_groups"]:
                for group in exp.get(key, []):
                    if not group.get("group_id"):
                        errs.append(f"group_id missing in {qid}")
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
    for f in ["source_kind", "source_layer", "authority_role", "canon_status"]:
        if f in match:
            checks.append(_norm(item.get(f)) == _norm(match[f]))
        any_key = f"{f}_any"
        if any_key in match:
            checks.append(_norm(item.get(f)) in {_norm(x) for x in match[any_key]})
    for f in ["unit_id", "title", "snippet", "source_reference"]:
        k = f"{f}_contains_any"
        if k in match:
            field_text = _norm(item.get(f, ""))
            checks.append(any(_contains_norm(field_text, tok) for tok in match[k]))
    if "route_contains_any" in match:
        route_blob = _norm(" ".join([str(item.get("route", "")), str(item.get("normalized_route", "")), str(item.get("source_reference", ""))] + [str((r or {}).get("normalized_route", "")) for r in (item.get("routes", []) or [])]))
        checks.append(any(_norm(tok) in route_blob for tok in match["route_contains_any"]))
    if "text_contains_any" in match:
        checks.append(any(_contains_norm(text, tok) for tok in match["text_contains_any"]))
    if "session_number_any" in match:
        checks.append(bool(_get_session_values(item).intersection({int(x) for x in match["session_number_any"]})))
    return all(checks) if checks else False


def match_context_group(*, retrieved_context: list[dict[str, Any]], group: dict[str, Any], top_k: int) -> dict[str, Any]:
    min_hits = int(group.get("min_hits", 1))
    matched = [context_item_ref(i) for i in retrieved_context[:top_k] if match_context_item(i, group.get("match", {}))]
    return {"group_id": group.get("group_id"), "ok": len(matched) >= min_hits, "min_hits": min_hits, "hit_count": len(matched), "matched_context_refs": matched}


def get_grading_context(packet: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    admitted = packet.get("admitted_context")
    if isinstance(admitted, list):
        return "admitted_context", admitted
    return "legacy_top_k_retrieved_context", packet.get("retrieved_context", [])


def grade_question_packet(*, packet: dict[str, Any], gold_question: dict[str, Any], retrieval_mode: RetrievalMode, top_k: int) -> dict[str, Any]:
    exp = (gold_question.get("expectations_by_mode") or {}).get(retrieval_mode, {})
    required = exp.get("required_context_groups", [])
    forbidden = exp.get("forbidden_context_groups", [])
    grading_context_kind, grading_context = get_grading_context(packet)
    required_matches = [match_context_group(retrieved_context=grading_context, group=g, top_k=top_k) for g in required]
    forbidden_matches = [match_context_group(retrieved_context=grading_context, group=g, top_k=top_k) for g in forbidden]
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
    retrieved_preview = []
    for idx, item in enumerate(grading_context[:top_k], start=1):
        matched_required_groups = [
            grp.get("group_id")
            for grp in required
            if match_context_item(item, grp.get("match", {}))
        ]
        ref = context_item_ref(item)
        source_ref = item.get("source_reference")
        retrieved_preview.append(
            {
                "rank": idx,
                "ref": ref,
                "source_kind": item.get("source_kind", "session_memory"),
                "source_layer": item.get("source_layer"),
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "source_reference": source_ref if isinstance(source_ref, (str, int, float)) else (json.dumps(source_ref, sort_keys=True) if source_ref is not None else None),
                "matched_required_groups": matched_required_groups,
            }
        )
    return {
        "question_number": packet.get("question_number"),
        "question_id": packet.get("question_id"),
        "retrieval_mode": retrieval_mode,
        "admission_policy": str(packet.get("admission_policy") or "legacy_top_k"),
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
        "retrieved_context_preview": retrieved_preview,
        "authority_summary": packet.get("authority_summary", {}),
        "grading_context_kind": grading_context_kind,
    }


def _build_depth_diagnostics(*, retrieved_context: list[dict[str, Any]], required_groups: list[dict[str, Any]], top_k: int, depths: list[int]) -> dict[str, Any]:
    def _counts(limit: int) -> dict[str, int]:
        out: dict[str, int] = {}
        for item in retrieved_context[:limit]:
            k = str(item.get("source_kind") or "session_memory")
            out[k] = out.get(k, 0) + 1
        return out
    by_group: dict[str, Any] = {}
    for grp in required_groups:
        gid = str(grp.get("group_id") or "unknown")
        first_idx = None
        first_item = None
        for idx, item in enumerate(retrieved_context, start=1):
            if match_context_item(item, grp.get("match", {})):
                first_idx = idx
                first_item = item
                break
        entry = {
            "matched_at_top_k": bool(first_idx is not None and first_idx <= top_k),
            "first_matching_rank": first_idx,
            "first_matching_ref": context_item_ref(first_item) if first_item else None,
            "first_matching_source_kind": first_item.get("source_kind", "session_memory") if first_item else None,
            "first_matching_source_layer": first_item.get("source_layer") if first_item else None,
        }
        for d in depths:
            entry[f"matched_at_top_{d}"] = bool(first_idx is not None and first_idx <= d)
        by_group[gid] = entry
    counts = {"top_k": _counts(top_k)}
    for d in depths:
        counts[f"top_{d}"] = _counts(d)
    return {"configured_top_k": top_k, "depths_checked": depths, "required_groups": by_group, "source_kind_counts_by_depth": counts}


def _simulate_budget_profile(*, retrieved_context: list[dict[str, Any]], required_groups: list[dict[str, Any]], profile_name: str, top_k: int, retrieval_mode: RetrievalMode) -> dict[str, Any]:
    profile_configs: dict[str, dict[str, Any]] = {
        "legacy_top_k_9": {"type": "legacy_top_k"},
        "flat_ranked_4000_chars": {"type": "flat_ranked", "budget_chars": 4000},
        "flat_ranked_8000_chars": {"type": "flat_ranked", "budget_chars": 8000},
        "flat_ranked_12000_chars": {"type": "flat_ranked", "budget_chars": 12000},
        "support_reserved_25pct_8000_chars": {"type": "support_reserved", "budget_chars": 8000, "support_ratio": 0.25},
        "support_reserved_35pct_8000_chars": {"type": "support_reserved", "budget_chars": 8000, "support_ratio": 0.35},
    }
    cfg = profile_configs[profile_name]
    sized = []
    for idx, item in enumerate(retrieved_context, start=1):
        chars, _ = estimate_context_item_size(item)
        sized.append({"candidate_rank": idx, "item": item, "chars": chars, "ref": context_item_ref(item), "source_kind": str(item.get("source_kind") or "session_memory")})
    admitted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if cfg["type"] == "legacy_top_k":
        admitted = sized[:top_k]
    elif cfg["type"] == "flat_ranked":
        remaining = int(cfg["budget_chars"])
        for c in sized:
            if c["chars"] <= remaining:
                admitted.append(c)
                remaining -= c["chars"]
            else:
                skipped.append(c)
    else:
        total_budget = int(cfg["budget_chars"])
        support_budget = int(total_budget * float(cfg["support_ratio"]))
        general_budget = total_budget - support_budget
        support_eligible = retrieval_mode != "prior_only"
        for c in sized:
            is_support = c["source_kind"] == SUPPORT_KIND
            if is_support:
                if not support_eligible:
                    skipped.append(c)
                    continue
                if c["chars"] <= support_budget:
                    admitted.append(c)
                    support_budget -= c["chars"]
                else:
                    skipped.append(c)
            else:
                if c["chars"] <= general_budget:
                    admitted.append(c)
                    general_budget -= c["chars"]
                else:
                    skipped.append(c)
    source_kind_counts: dict[str, int] = {}
    source_kind_chars: dict[str, int] = {}
    admitted_refs = {a["ref"] for a in admitted}
    admitted_by_rank = sorted(admitted, key=lambda x: x["candidate_rank"])
    for admitted_rank, a in enumerate(admitted_by_rank, start=1):
        a["admitted_rank"] = admitted_rank
        k = a["source_kind"]
        source_kind_counts[k] = source_kind_counts.get(k, 0) + 1
        source_kind_chars[k] = source_kind_chars.get(k, 0) + int(a["chars"])
    required_by_group: dict[str, Any] = {}
    for grp in required_groups:
        gid = str(grp.get("group_id") or "unknown")
        first_cand = next((c for c in sized if match_context_item(c["item"], grp.get("match", {}))), None)
        first_admitted = next((c for c in admitted_by_rank if match_context_item(c["item"], grp.get("match", {}))), None)
        required_by_group[gid] = {
            "first_matching_candidate_rank": first_cand["candidate_rank"] if first_cand else None,
            "first_matching_candidate_ref": first_cand["ref"] if first_cand else None,
            "admitted": first_admitted is not None,
            "admitted_rank": first_admitted["admitted_rank"] if first_admitted else None,
            "admitted_ref": first_admitted["ref"] if first_admitted else None,
        }
    out: dict[str, Any] = {
        "admitted_items": len(admitted_by_rank),
        "admitted_chars": sum(int(a["chars"]) for a in admitted_by_rank),
        "estimated_tokens": math.ceil(sum(int(a["chars"]) for a in admitted_by_rank) / 4),
        "source_kind_counts": source_kind_counts,
        "source_kind_chars": source_kind_chars,
        "admitted_preview": [
            {
                "admitted_rank": a["admitted_rank"],
                "candidate_rank": a["candidate_rank"],
                "ref": a["ref"],
                "source_kind": a["source_kind"],
                "estimated_chars": a["chars"],
                "matched_required_groups": [str(grp.get("group_id") or "unknown") for grp in required_groups if match_context_item(a["item"], grp.get("match", {}))],
            }
            for a in admitted_by_rank[:12]
        ],
        "_required_group_results": required_by_group,
    }
    if cfg["type"] == "legacy_top_k":
        out["budget_chars"] = None
    elif cfg["type"] == "flat_ranked":
        out["budget_chars"] = int(cfg["budget_chars"])
    else:
        out["budget_chars"] = int(cfg["budget_chars"])
        out["support_budget_chars"] = int(int(cfg["budget_chars"]) * float(cfg["support_ratio"]))
        out["general_budget_chars"] = int(cfg["budget_chars"]) - out["support_budget_chars"]
    return out


def _build_budget_admission_diagnostics(*, retrieved_context: list[dict[str, Any]], required_groups: list[dict[str, Any]], top_k: int, retrieval_mode: RetrievalMode, candidate_depth: int = 50) -> dict[str, Any]:
    profiles = [
        "legacy_top_k_9",
        "flat_ranked_4000_chars",
        "flat_ranked_8000_chars",
        "flat_ranked_12000_chars",
        "support_reserved_25pct_8000_chars",
        "support_reserved_35pct_8000_chars",
    ]
    candidate_pool = retrieved_context[:candidate_depth]
    profile_results: dict[str, Any] = {}
    required_out: dict[str, Any] = {}
    for p in profiles:
        sim = _simulate_budget_profile(retrieved_context=candidate_pool, required_groups=required_groups, profile_name=p, top_k=top_k, retrieval_mode=retrieval_mode)
        required_group_results = sim.pop("_required_group_results")
        profile_results[p] = sim
        for gid, grp_res in required_group_results.items():
            if gid not in required_out:
                required_out[gid] = {
                    "first_matching_candidate_rank": grp_res["first_matching_candidate_rank"],
                    "first_matching_candidate_ref": grp_res["first_matching_candidate_ref"],
                }
            required_out[gid][p] = {
                "admitted": grp_res["admitted"],
                "admitted_rank": grp_res["admitted_rank"],
                "admitted_ref": grp_res["admitted_ref"],
            }
    return {"candidate_depth": candidate_depth, "legacy_top_k": top_k, "profiles": profile_results, "required_groups": required_out}


def build_expected_context_report(*, packets: list[dict[str, Any]], gold: dict[str, Any], retrieval_mode: RetrievalMode, top_k: int | None = None, diagnostic_packets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    by_q = {int(p.get("question_number")): p for p in packets}
    chosen_top_k = top_k or int(gold.get("default_top_k", 9))
    results = []
    by_q_diag = {int(p.get("question_number")): p for p in (diagnostic_packets or packets)}
    for gq in gold.get("questions", []):
        qn = int(gq.get("question_number"))
        if qn == 35:
            continue
        pkt = by_q.get(qn)
        if not pkt:
            continue
        row = grade_question_packet(packet=pkt, gold_question=gq, retrieval_mode=retrieval_mode, top_k=chosen_top_k)
        exp = (gq.get("expectations_by_mode") or {}).get(retrieval_mode, {})
        diag_pkt = by_q_diag.get(qn, pkt)
        row["retrieval_depth_diagnostics"] = _build_depth_diagnostics(
            retrieved_context=diag_pkt.get("retrieved_context", []),
            required_groups=exp.get("required_context_groups", []),
            top_k=chosen_top_k,
            depths=[20, 50],
        )
        row["budget_admission_diagnostics"] = _build_budget_admission_diagnostics(
            retrieved_context=diag_pkt.get("retrieved_context", []),
            required_groups=exp.get("required_context_groups", []),
            top_k=chosen_top_k,
            retrieval_mode=retrieval_mode,
            candidate_depth=50,
        )
        results.append(row)
    req_total = sum(r["required_context_groups"] for r in results)
    req_hit = sum(r["required_context_groups_hit"] for r in results)
    row_ok = sum(1 for r in results if r["ok"])
    known_total = sum(len(((q.get("expectations_by_mode") or {}).get(retrieval_mode, {})).get("expected_known_gaps_contains_any", [])) for q in gold.get("questions", []) if int(q.get("question_number", 0)) != 35)
    known_hit = sum(len(r["known_gap_expectations_hit"]) for r in results)
    return {
        "schema": EXPECTED_CONTEXT_REPORT_SCHEMA,
        "campaign_id": gold.get("campaign_id", "longmont-c1"),
        "retrieval_mode": retrieval_mode,
        "admission_policy": str((packets[0].get("admission_policy") if packets else "legacy_top_k") or "legacy_top_k"),
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

    dumped_raw = json.dumps(report).lower()
    dumped = _norm(dumped_raw)
    gold_path_norm = _norm(str(report.get("gold_path", "")))
    for token in LEAKAGE_TOKENS:
        token_raw = token.lower()
        token_norm = _norm(token)
        for row in report.get("results", []):
            row_dump_raw = json.dumps(row).lower()
            if token_raw in row_dump_raw or token_norm in _norm(row_dump_raw):
                errs.append(f"retrieved context leakage token present: {token}")
                break
        if (token_raw in dumped_raw or token_norm in dumped) and token_norm not in gold_path_norm:
            errs.append(f"unexpected leakage token present in report: {token}")

    for row in report.get("results", []):
        if row.get("question_number") == 35:
            errs.append("q35 appears as planner-facing benchmark packet")
    return errs
