from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import iter_target_questions, load_beat_question_targets
from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet


def _record_refs(item: dict[str, Any]) -> str:
    vals = [item.get("source_path"), item.get("source_recap_path"), item.get("source_reference"), item.get("unit_id")]
    return " ".join(str(v or "") for v in vals).lower()


def _family_needle(group_id: str, expected_path: str) -> str:
    gl = group_id.lower()
    if "grishna" in gl:
        return "npcs/grishna"
    if "pippa" in gl:
        return "npcs/pippa"
    if "bubbles" in gl:
        return "npcs/bubbles"
    if "stone_bridge" in gl or "stone bridge" in expected_path.lower():
        return "stone_bridge"
    if "hempholm" in gl or "support" in gl:
        return "support:hempholm"
    return expected_path.lower()


def _load_pr59_surface_by_key() -> dict[tuple[str, str, str, str], str]:
    path = Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr59/pr59_step2c_alias_probe_matrix.csv")
    if not path.exists():
        return {}
    out: dict[tuple[str, str, str, str], str] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["question_id"], row["group_id"], row["mode"], row["expected_path_or_unit_id"])
            out[key] = row.get("next_failure_surface") or ""
    return out


def _field_for_needle(admitted: list[dict[str, Any]], needle: str, field: str) -> str:
    for item in admitted:
        if needle in _record_refs(item):
            return str(item.get(field) or "")
    return ""


def write_pr60_artifacts(*, output_dir: Path, packets_by_mode: dict[str, list[dict[str, Any]]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pr59_surface = _load_pr59_surface_by_key()
    targets = load_beat_question_targets()
    questions = {str(q["question_id"]): q for q in iter_target_questions(targets)}

    matrix_rows: list[dict[str, Any]] = []
    preservation_rows: list[dict[str, Any]] = []

    for mode, packets in packets_by_mode.items():
        for packet in packets:
            qid = str(packet.get("question_id") or "")
            question = questions.get(qid, {})
            question_text = str(question.get("question") or packet.get("question") or "")
            candidate = packet.get("candidate_context") or []
            admitted = packet.get("admitted_context") or []
            diag = packet.get("admission_preservation_diagnostics") or {}
            rendered = render_context_packet(
                {
                    "question_number": packet.get("question_number"),
                    "question_id": packet.get("question_id"),
                    "question": question_text,
                    "retrieval_mode": mode,
                    "admission_policy": packet.get("admission_policy"),
                    "known_context_gaps": packet.get("known_context_gaps", []),
                    "admitted_context": admitted,
                    "admission_budget": packet.get("admission_budget", {}),
                }
            )
            provenance = rendered.get("provenance_map") or {}

            for item in diag.get("preserved_items") or []:
                preservation_rows.append({"question_id": qid, "mode": mode, **item})

            for ev_key, pr59_surface_name in pr59_surface.items():
                question_id, group_id, ev_mode, expected_path = ev_key
                if question_id != qid or ev_mode != mode:
                    continue
                needle = _family_needle(group_id, expected_path)
                candidate_hit = any(needle in _record_refs(i) for i in candidate)
                admitted_hit = any(needle in _record_refs(i) for i in admitted)
                rendered_section_hit = any(
                    needle in ref.lower() or needle in str(meta.get("source_path") or "").lower()
                    for ref, meta in provenance.items()
                )

                if admitted_hit and rendered_section_hit:
                    next_surface = "ok_or_later_stage"
                elif admitted_hit and not rendered_section_hit:
                    next_surface = "rendered_section_mismatch"
                elif candidate_hit and not admitted_hit:
                    next_surface = "candidate_present_admission_deferred"
                else:
                    next_surface = pr59_surface_name or "source_exists_but_step2c_miss"

                matrix_rows.append(
                    {
                        "question_id": question_id,
                        "group_id": group_id,
                        "mode": mode,
                        "expected_path_or_unit_id": expected_path,
                        "pr59_surface": pr59_surface_name,
                        "candidate_hit": candidate_hit,
                        "admitted_hit": admitted_hit,
                        "rendered_section_hit": rendered_section_hit,
                        "admission_reason": _field_for_needle(admitted, needle, "admission_reason"),
                        "presentation_lane": _field_for_needle(admitted, needle, "presentation_lane"),
                        "admission_budget_lane": _field_for_needle(admitted, needle, "admission_budget_lane"),
                        "next_failure_surface": next_surface,
                    }
                )

    def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    write_csv(output_dir / "pr60_admission_preservation_matrix.csv", preservation_rows)
    write_csv(output_dir / "pr60_step2c_surface_matrix.csv", matrix_rows)

    moved = sum(
        1
        for row in matrix_rows
        if row.get("pr59_surface") == "candidate_present_admission_deferred" and row.get("admitted_hit")
    )

    (output_dir / "pr60_retrieval_universe_summary.json").write_text(
        json.dumps(
            {
                "schema": "dmb_pr60_retrieval_universe_summary_v1",
                "admission_deferred_to_admitted": moved,
                "pr60_surface_counts": {
                    str(row.get("next_failure_surface") or ""): sum(
                        1 for r in matrix_rows if r.get("next_failure_surface") == row.get("next_failure_surface")
                    )
                    for row in matrix_rows
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (output_dir / "README.md").write_text(
        "# PR60 admission lane preservation artifacts\n\n"
        "See `pr60_admission_preservation_matrix.csv` and `pr60_step2c_surface_matrix.csv`.\n",
        encoding="utf-8",
    )

    (output_dir / "pr60_next_pr_recommendations.md").write_text(
        "# Post-PR60 Planning Recommendations\n\n"
        "1. **PR61 — renderer section repair:** route admitted items by preserved `presentation_lane`.\n"
        "2. **PR62 — generalize preservation rules** after PR60 evidence holds.\n",
        encoding="utf-8",
    )
