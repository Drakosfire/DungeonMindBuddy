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


def _load_pr60_surface_by_key() -> dict[tuple[str, str, str, str], str]:
    path = Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr60/pr60_step2c_surface_matrix.csv")
    if not path.exists():
        return {}
    out: dict[tuple[str, str, str, str], str] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["question_id"], row["group_id"], row["mode"], row["expected_path_or_unit_id"])
            out[key] = row.get("next_failure_surface") or ""
    return out


def _field_for_needle(items: list[dict[str, Any]], needle: str, field: str) -> str:
    for item in items:
        if needle in _record_refs(item):
            return str(item.get(field) or "")
    return ""


def write_pr61_artifacts(*, output_dir: Path, packets_by_mode: dict[str, list[dict[str, Any]]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pr60_surface = _load_pr60_surface_by_key()
    targets = load_beat_question_targets()
    questions = {str(q["question_id"]): q for q in iter_target_questions(targets)}

    matrix_rows: list[dict[str, Any]] = []

    for mode, packets in packets_by_mode.items():
        for packet in packets:
            qid = str(packet.get("question_id") or "")
            question = questions.get(qid, {})
            question_text = str(question.get("question") or packet.get("question") or "")
            candidate = packet.get("candidate_context") or []
            admitted = packet.get("admitted_context") or []
            query_diag = packet.get("query_variant_diagnostics") or {}
            merge_diag = query_diag.get("merge_allocation_diagnostics") or {}
            family_hits = {
                str(row.get("family") or ""): row for row in merge_diag.get("family_required_hits") or []
            }

            literal_probe = False
            alias_probe = False
            for row in query_diag.get("variant_hit_counts") or []:
                role = str(row.get("variant_role") or "")
                hit_count = int(row.get("hit_count") or 0)
                if role == "literal_question" and hit_count > 0:
                    literal_probe = True
                elif role != "literal_question" and hit_count > 0:
                    alias_probe = True

            rendered = render_context_packet(
                {
                    "question_number": packet.get("question_number"),
                    "question_id": packet.get("question_id"),
                    "question": question_text,
                    "retrieval_mode": mode,
                    "admission_policy": packet.get("admission_policy"),
                    "admitted_context": admitted,
                    "admission_budget": packet.get("admission_budget", {}),
                }
            )
            provenance = rendered.get("provenance_map") or {}

            for ev_key, pr60_surface_name in pr60_surface.items():
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

                family_key = ""
                if "grishna" in needle:
                    family_key = "grishna"
                elif "pippa" in needle:
                    family_key = "pippa"
                elif "bubbles" in needle:
                    family_key = "bubbles"
                family_row = family_hits.get(family_key, {})
                selected_by_family = bool(family_row) and needle in str(family_row.get("source_path") or "").lower()

                if admitted_hit and rendered_section_hit:
                    next_surface = "ok_or_later_stage"
                elif admitted_hit and not rendered_section_hit:
                    next_surface = "rendered_section_mismatch"
                elif candidate_hit and not admitted_hit:
                    next_surface = "candidate_present_admission_deferred"
                else:
                    next_surface = pr60_surface_name or "source_exists_but_step2c_miss"

                matrix_rows.append(
                    {
                        "question_id": question_id,
                        "group_id": group_id,
                        "mode": mode,
                        "expected_path_or_unit_id": expected_path,
                        "pr60_surface": pr60_surface_name,
                        "literal_query_hit": literal_probe,
                        "alias_query_hit": alias_probe,
                        "pre_allocation_alias_rank": family_row.get("alias_rank", ""),
                        "selected_by_family_allocation": selected_by_family,
                        "candidate_hit": candidate_hit,
                        "admitted_hit": admitted_hit,
                        "rendered_section_hit": rendered_section_hit,
                        "merge_reason": _field_for_needle(candidate + admitted, needle, "merge_reason"),
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

    write_csv(output_dir / "pr61_candidate_merge_allocation_matrix.csv", matrix_rows)
    write_csv(output_dir / "pr61_step2c_surface_matrix.csv", matrix_rows)

    moved_from_deferred = sum(
        1
        for row in matrix_rows
        if row.get("pr60_surface") == "candidate_present_admission_deferred" and row.get("admitted_hit")
    )
    grishna_rows = [r for r in matrix_rows if "grishna" in str(r.get("group_id") or "").lower()]
    grishna_moved = any(
        r.get("pr60_surface") == "candidate_present_admission_deferred" and r.get("admitted_hit") for r in grishna_rows
    )

    surface_counts: dict[str, int] = {}
    for row in matrix_rows:
        surface = str(row.get("next_failure_surface") or "")
        surface_counts[surface] = surface_counts.get(surface, 0) + 1

    (output_dir / "pr61_retrieval_universe_summary.json").write_text(
        json.dumps(
            {
                "schema": "dmb_pr61_retrieval_universe_summary_v1",
                "candidate_deferred_to_admitted": moved_from_deferred,
                "q1_grishna_moved_from_candidate_pool_gap": grishna_moved,
                "pr61_surface_counts": surface_counts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (output_dir / "README.md").write_text(
        "# PR61 candidate merge allocation artifacts\n\n"
        "PR61 adds coverage-aware alias allocation inside the existing alias slot budget.\n\n"
        "Q1 Grishna's useful admittable NPC record should now enter `candidate_context` and be admitted "
        "by PR60 preservation.\n\n"
        "See `pr61_step2c_surface_matrix.csv` for target-surface movement vs PR60.\n",
        encoding="utf-8",
    )

    (output_dir / "pr61_next_pr_recommendations.md").write_text(
        "# Post-PR61 Planning Recommendations\n\n"
        "1. **PR62 — renderer section repair.** Several admitted character records preserve "
        "`presentation_lane=party_timeline` but still show rendered-section mismatch.\n"
        "2. **PR63 — generalize family-aware merge allocation** after benchmark surfaces are stable.\n",
        encoding="utf-8",
    )
