from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TARGET_PATH = Path(__file__).parent / "gold" / "c1s4_beat_question_targets.json"
ORACLE_TERMS = ["Torvak Hempdealer", "Hempholm", "Torbin", "Jove", "Steve", "grotesque tree", "root-like beetles", "precious metal leaves"]
VALID_AUTH = {"prior_recap_supported", "worldbuilding_required", "support_knowledge_required", "creative_generation", "oracle_only", "mixed"}
VALID_RISK = {"low", "medium", "high", "must_not_predict"}


def load_targets(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or TARGET_PATH).read_text())


def iter_questions(targets: dict[str, Any]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for beat in targets.get("beats", []):
        questions.extend(beat.get("questions", []))
    questions.extend(targets.get("meta_questions", []))
    return questions


def validate_targets(targets: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_top = {
        "schema": "dmb_c1s4_beat_question_targets_v1",
        "campaign_id": "longmont-c1",
        "source_sessions_allowed_for_planner": [1, 2, 3],
        "heldout_session": 4,
        "planner_visibility": "forbidden",
        "artifact_role": "benchmark_target_and_planning_question_spec",
    }
    for k, v in expected_top.items():
        if targets.get(k) != v:
            errors.append(f"{k} must be {v!r}")

    for beat in targets.get("beats", []):
        for req in ["beat_id", "beat_number", "title", "planned_function", "questions"]:
            if req not in beat:
                errors.append(f"missing beat field {req}")

    questions = iter_questions(targets)
    required_q_fields = ["question_id", "question_number", "question", "answer_product", "authority_label", "oracle_risk", "expected_retrieval_modes", "expected_retrieval_context_eval_only", "known_context_gaps", "must_not_include_unless_sourced", "notes"]
    for q in questions:
        for req in required_q_fields:
            if req not in q:
                errors.append(f"Q{q.get('question_number')} missing {req}")
        if q.get("authority_label") not in VALID_AUTH:
            errors.append(f"Q{q.get('question_number')} invalid authority_label")
        if q.get("oracle_risk") not in VALID_RISK:
            errors.append(f"Q{q.get('question_number')} invalid oracle_risk")

    nums = [q.get("question_number") for q in questions]
    if sorted(nums) != list(range(1, 39)):
        errors.append("Questions Q1-Q38 must exist exactly once")
    ids = [q.get("question_id") for q in questions]
    if len(ids) != len(set(ids)):
        errors.append("question_id values must be unique")
    if len(nums) != len(set(nums)):
        errors.append("question_number values must be unique")

    qmap = {q["question_number"]: q for q in questions if "question_number" in q}
    q3_gaps = " ".join(qmap.get(3, {}).get("known_context_gaps", []))
    if "Stone Bridge-to-Mirathorn" not in q3_gaps:
        errors.append("Q3 must mark Stone Bridge-to-Mirathorn route gap")
    for n, label in [(4, "support_knowledge_required"), (5, "support_knowledge_required"), (6, "mixed")]:
        if qmap.get(n, {}).get("authority_label") != label:
            errors.append(f"Q{n} authority_label must be {label}")
    if qmap.get(35, {}).get("oracle_risk") != "must_not_predict":
        errors.append("Q35 must have oracle_risk == must_not_predict")

    for q in questions:
        if q.get("authority_label") == "prior_recap_supported":
            hay = " ".join(q.get("expected_retrieval_context_eval_only", []))
            for term in ORACLE_TERMS:
                if term.lower() in hay.lower():
                    errors.append(f"oracle-sensitive term found in prior-only context: {term}")
    return errors


def main() -> int:
    errors = validate_targets(load_targets())
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1
    print("OK: c1s4 beat-question targets validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
