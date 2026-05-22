from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from evals.c1s4_preplanning_vertical_slice.generated_answer_harness import generate_answer_packet
from evals.c1s4_preplanning_vertical_slice.planner_prompt_payload import (
    build_evaluator_control_metadata,
    build_planner_prompt_payload,
    find_forbidden_prompt_material,
    validate_evaluator_control_metadata,
    validate_planner_prompt_payload,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary

PLANNER_QUESTIONS = (1, 3, 5)
MODES = (
    "prior_only",
    "prior_plus_support_content_only",
    "prior_plus_support_content_plus_lexical_hints",
)


def write_pr64_artifacts(*, output_dir: Path, modes: tuple[str, ...] = MODES, question_numbers: tuple[int, ...] = PLANNER_QUESTIONS) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_rows: list[dict[str, Any]] = []
    prompt_examples: list[dict[str, Any]] = []
    metadata_examples: list[dict[str, Any]] = []

    forbidden_key_hits = 0
    forbidden_value_hits = 0
    expected_behavior_leaks = 0
    authority_label_leaks = 0
    oracle_risk_leaks = 0
    payloads_built = 0
    payloads_valid = 0
    metadata_built = 0

    for mode in modes:
        for qn in question_numbers:
            packet = build_summary(mode=mode, question_number=qn, max_hits=50)["packets"][0]
            prompt = build_planner_prompt_payload(context_packet=packet)
            meta = build_evaluator_control_metadata(context_packet=packet)
            answer = generate_answer_packet(planner_prompt_payload=prompt, evaluator_control_metadata=meta, retrieval_mode=mode)
            payloads_built += 1
            metadata_built += 1
            prompt_errs = validate_planner_prompt_payload(prompt)
            if not prompt_errs:
                payloads_valid += 1
            key_hits = find_forbidden_prompt_material(prompt)
            value_hits = [h for h in key_hits if "forbidden value token" in h]
            key_only_hits = [h for h in key_hits if "forbidden key" in h]
            forbidden_key_hits += len(key_only_hits)
            forbidden_value_hits += len(value_hits)

            answer_text = str(answer.get("answer_text") or "")
            answer_lower = answer_text.lower()
            eb_leak = "expected behavior:" in answer_lower
            auth_leak = "authority requirement:" in answer_lower
            risk_leak = str(meta.get("oracle_risk") or "").lower() in answer_lower if meta.get("oracle_risk") else False
            expected_behavior_leaks += int(eb_leak)
            authority_label_leaks += int(auth_leak)
            oracle_risk_leaks += int(risk_leak)

            if len(prompt_examples) < 3:
                prompt_examples.append(prompt)
            if len(metadata_examples) < 3:
                metadata_examples.append(meta)

            next_surface = "ok_or_later_stage"
            if prompt_errs or key_hits:
                next_surface = "invalid_planner_prompt_payload"
            elif eb_leak or auth_leak or risk_leak:
                next_surface = "generated_answer_control_metadata_leak"

            matrix_rows.append(
                {
                    "question_id": packet.get("question_id"),
                    "mode": mode,
                    "planner_payload_valid": not bool(prompt_errs),
                    "evaluator_metadata_valid": not bool(validate_evaluator_control_metadata(meta)),
                    "forbidden_key_hits_in_prompt_payload": len(key_only_hits),
                    "forbidden_value_hits_in_prompt_payload": len(value_hits),
                    "rendered_context_present": bool((prompt.get("rendered_context") or {}).get("rendered_text")),
                    "source_derived_gap_count": len(prompt.get("source_derived_context_gaps") or []),
                    "support_allowed": prompt.get("support_knowledge_allowed"),
                    "answer_text_contains_expected_behavior": eb_leak,
                    "answer_text_contains_authority_label": auth_leak,
                    "answer_text_contains_oracle_risk": risk_leak,
                    "next_failure_surface": next_surface,
                }
            )

    with (output_dir / "pr64_prompt_payload_boundary_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(matrix_rows[0].keys()))
        writer.writeheader()
        writer.writerows(matrix_rows)

    (output_dir / "pr64_prompt_payload_examples.json").write_text(json.dumps(prompt_examples, indent=2), encoding="utf-8")
    (output_dir / "pr64_evaluator_control_metadata_examples.json").write_text(
        json.dumps(metadata_examples, indent=2), encoding="utf-8"
    )

    summary = {
        "schema": "dmb_pr64_prompt_control_split_summary_v1",
        "planner_prompt_payloads_built": payloads_built,
        "planner_prompt_payloads_valid": payloads_valid,
        "evaluator_control_metadata_built": metadata_built,
        "forbidden_prompt_key_hits": forbidden_key_hits,
        "forbidden_prompt_value_hits": forbidden_value_hits,
        "generated_answer_expected_behavior_leaks": expected_behavior_leaks,
        "generated_answer_authority_label_leaks": authority_label_leaks,
        "generated_answer_oracle_risk_leaks": oracle_risk_leaks,
    }
    (output_dir / "pr64_retrieval_universe_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "README.md").write_text(
        "# PR64 planner prompt / evaluator control split artifacts\n\n"
        "Documents the split between `planner_prompt_payload` (LLM-safe) and "
        "`evaluator_control_metadata` (benchmark/control only).\n",
        encoding="utf-8",
    )
    (output_dir / "pr64_next_pr_recommendations.md").write_text(
        "# Post-PR64 Planning Recommendations\n\n"
        "1. **PR65 benchmark coverage expansion** beyond Q1/Q3/Q5.\n"
        "2. **Live LLM answer generation** should consume `planner_prompt_payload` only.\n"
        "3. **Long-term:** remove target-derived fields from internal Step2 context packets.\n",
        encoding="utf-8",
    )
    return summary
