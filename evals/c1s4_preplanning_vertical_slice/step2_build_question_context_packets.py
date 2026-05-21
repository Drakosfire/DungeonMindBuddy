from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import (
    QuestionRetrievalMode,
    build_question_context_packet,
    is_planner_facing_question,
    iter_target_questions,
    load_beat_question_targets,
    validate_packet,
)
from evals.c1s4_preplanning_vertical_slice.preplanning_context_bundle import build_preplanning_context_bundle
from evals.c1s4_preplanning_vertical_slice.context_admission import build_budgeted_admission, build_lane_budgeted_admission
from evals.c1s4_preplanning_vertical_slice.query_lane_router import build_lane_plan
from evals.c1s4_preplanning_vertical_slice.campaign_corpus_materializer import load_campaign_corpus_records_for_c1s4
from evals.c1s4_preplanning_vertical_slice.query_alias_expansion import build_step2c_query_variants
from evals.c1s4_preplanning_vertical_slice.query_variant_retrieval import retrieve_query_variants
from evals.c1s4_preplanning_vertical_slice.step0_kb_materialize import DEFAULT_POLICY_PATH, load_kb_manifest
from evals.c1s4_preplanning_vertical_slice.support_knowledge_loader import load_normalized_support_records


class C1S4BoundaryError(RuntimeError): ...


class _MergedRetrievalResult:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self.hits = hits


def _load_combined_records(mode: QuestionRetrievalMode) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    policy = json.loads(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    manifest, session_records = load_kb_manifest(DEFAULT_POLICY_PATH)
    if manifest["forbidden_path_hits"] or manifest["forbidden_session_hits"] or manifest.get("unexpected_session_hits"):
        raise C1S4BoundaryError("Step 0 manifest is not oracle-safe; aborting Step 2 packet generation")
    combined = list(session_records)
    combined.extend(load_campaign_corpus_records_for_c1s4())
    if mode == "prior_plus_support_content_only":
        combined.extend(load_normalized_support_records(retrieval_mode="content_only"))
    elif mode == "prior_plus_support_content_plus_lexical_hints":
        combined.extend(load_normalized_support_records(retrieval_mode="content_plus_lexical_hints"))
    records_by_unit_id = {str(r.get("unit_id")): r for r in combined if r.get("unit_id")}
    return manifest, combined, records_by_unit_id, list(policy["forbidden_oracle_relpaths"])


def _retrieve(
    query: str,
    mode: QuestionRetrievalMode,
    campaign_id: str,
    *,
    max_hits: int = 8,
    lane_plan: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, Any]]:
    manifest, combined, records_by_unit_id, forbidden_oracle_relpaths = _load_combined_records(mode)
    lane_plan = lane_plan or build_lane_plan(question_text=query, retrieval_mode=mode, candidate_depth=max_hits, total_budget_chars=8000)
    variants = build_step2c_query_variants(question_text=query, retrieval_mode=mode, lane_plan=lane_plan)
    merged_hits, query_variant_diagnostics = retrieve_query_variants(
        records=combined,
        query_variants=variants,
        campaign_id=campaign_id,
        session_min=0,
        session_max=3,
        candidate_depth=max_hits,
    )
    bundle = build_preplanning_context_bundle(
        kb_id=manifest["kb_id"],
        campaign_id=campaign_id,
        allowed_sessions=manifest["included_sessions"],
        heldout_sessions=manifest["heldout_sessions"],
        query=query,
        retrieval_result=_MergedRetrievalResult(merged_hits),
        max_items=max_hits,
        forbidden_oracle_relpaths=forbidden_oracle_relpaths,
        records_by_unit_id=records_by_unit_id,
    )
    return bundle["items"], bundle["oracle_leakage_check"], query_variant_diagnostics


def build_summary(*, mode: QuestionRetrievalMode, question_number: int | None = None, limit: int | None = None, max_hits: int = 50, admission_policy: str = "lane_budgeted_v1") -> dict[str, Any]:
    targets = load_beat_question_targets()
    questions = iter_target_questions(targets)
    if question_number is not None:
        questions = [q for q in questions if q.get("question_number") == question_number]
    if limit is not None:
        questions = questions[:limit]

    packets = []
    skipped_questions = []
    auth_totals = {k: 0 for k in ["session_memory", "source_module", "adaptation_planning", "world_canon", "campaign_stateful_reference", "support_gap", "manual_support_synthesis", "unknown"]}
    oracle_path_hits: list[str] = []
    oracle_session_hits: list[str] = []

    for q in questions:
        if not is_planner_facing_question(q, retrieval_mode=mode):
            skipped_questions.append({"question_number": q.get("question_number"), "question_id": q.get("question_id"), "status": "skipped", "reason": "evaluator_only_not_planner_facing"})
            continue
        question_text = str(q.get("question") or "")
        lane_plan = build_lane_plan(question_text=question_text, retrieval_mode=mode, candidate_depth=max_hits, total_budget_chars=8000)
        candidate_context, leak, query_variant_diagnostics = _retrieve(
            question_text,
            mode,
            targets.get("campaign_id", "longmont-c1"),
            max_hits=max_hits,
            lane_plan=lane_plan,
        )
        if admission_policy == "legacy_top_k":
            retrieved_context = candidate_context[:9]
            packet = build_question_context_packet(question=q, retrieval_mode=mode, retrieved_context=retrieved_context, oracle_leakage_check=leak)
            packet["admission_policy"] = "legacy_top_k"
        else:
            packet = build_question_context_packet(question=q, retrieval_mode=mode, retrieved_context=candidate_context[:9], oracle_leakage_check=leak)
            if admission_policy == "lane_budgeted_v1":
                admission = build_lane_budgeted_admission(question_text=question_text, retrieval_mode=mode, candidates=candidate_context, lane_plan=lane_plan, candidate_depth=max_hits, total_budget_chars=8000)
            else:
                admission = build_budgeted_admission(question_text=question_text, retrieval_mode=mode, candidates=candidate_context, candidate_depth=max_hits, total_budget_chars=8000)
            packet.update(admission)
        packet["query_variant_diagnostics"] = query_variant_diagnostics
        packet["query_features"] = lane_plan.get("query_features")
        packet["lane_plan"] = lane_plan
        errs = validate_packet(packet)
        if errs:
            raise RuntimeError(f"Packet validation failed for q{q.get('question_number')}: {errs}")
        for k, v in packet["authority_summary"].items():
            auth_totals[k] += v
        oracle_path_hits.extend(packet["oracle_leakage_check"]["forbidden_path_hits"])
        oracle_session_hits.extend(packet["oracle_leakage_check"]["forbidden_session_hits"])
        packets.append(packet)

    return {
        "schema": "dmb_c1s4_step2_question_context_packet_summary_v1",
        "campaign_id": targets.get("campaign_id", "longmont-c1"),
        "retrieval_mode": mode,
        "target_artifact": {"path": "evals/c1s4_preplanning_vertical_slice/gold/c1s4_beat_question_targets.json", "planner_visibility": "forbidden"},
        "counts": {
            "questions_total": len(questions),
            "planner_packets_built": len(packets),
            "questions_skipped": len(skipped_questions),
            "packets_with_zero_context": sum(1 for p in packets if len(p["retrieved_context"]) == 0),
        },
        "skipped_questions": skipped_questions,
        "authority_summary_total": auth_totals,
        "oracle_leakage_check": {"forbidden_path_hits": sorted(set(oracle_path_hits)), "forbidden_session_hits": sorted(set(oracle_session_hits))},
        "packets": packets,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"])
    parser.add_argument("--question-number", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--admission-policy", choices=["legacy_top_k", "budgeted_v1", "lane_budgeted_v1"], default="lane_budgeted_v1")
    parser.add_argument("--max-hits", type=int, default=50)
    args = parser.parse_args()
    try:
        summary = build_summary(mode=args.mode, question_number=args.question_number, limit=args.limit, max_hits=args.max_hits, admission_policy=args.admission_policy)
    except C1S4BoundaryError as exc:
        print(json.dumps({"schema": "dmb_c1s4_step2_question_context_packet_summary_v1", "error": str(exc)}, indent=2))
        return 1
    if args.output_json:
        args.output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    leaks = summary["oracle_leakage_check"]["forbidden_path_hits"] or summary["oracle_leakage_check"]["forbidden_session_hits"]
    return 1 if leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
