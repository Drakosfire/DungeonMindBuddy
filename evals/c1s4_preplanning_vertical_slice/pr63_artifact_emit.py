from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import iter_target_questions, load_beat_question_targets
from evals.c1s4_preplanning_vertical_slice.context_renderer import provenance_matches_expected, render_context_packet
from evals.c1s4_preplanning_vertical_slice.source_derived_context_gaps import gap_text_contains_forbidden_gold_phrase


def _record_refs(item: dict[str, Any]) -> str:
    vals = [item.get("source_path"), item.get("source_recap_path"), item.get("source_reference"), item.get("unit_id")]
    return " ".join(str(v or "") for v in vals).lower()


def _load_pr62_surface_by_key() -> dict[tuple[str, str, str, str], str]:
    path = Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr62/pr62_step2c_surface_matrix.csv")
    if not path.exists():
        return {}
    out: dict[tuple[str, str, str, str], str] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["question_id"], row["group_id"], row["mode"], row["expected_path_or_unit_id"])
            out[key] = row.get("next_failure_surface") or ""
    return out


def _expected_section_id(group_id: str, expected_path: str) -> str:
    gl = group_id.lower()
    ep = expected_path.lower()
    if "known_gap" in ep or "route_gap" in gl:
        return "known_gaps_and_safety_constraints"
    if "/npcs/" in ep or any(token in gl for token in ("pippa", "bubbles", "grishna", "character", "party")):
        return "character_party_behavior"
    if expected_path.startswith("support:") or "support:hempholm" in expected_path:
        return "support_knowledge"
    if "distance" in gl or "estimate_from_play" in gl or "/session recaps/" in ep or "session_recap" in ep:
        return "prior_campaign_memory"
    if "/locations/" in ep or "location" in gl or "stone_bridge" in gl or "mirathorn" in gl:
        return "location_worldbuilding"
    return "prior_campaign_memory"


def _first_source_derived_gap(packet: dict[str, Any]) -> dict[str, Any] | None:
    gaps = packet.get("source_derived_context_gaps") or []
    if not gaps:
        return None
    first = gaps[0]
    return first if isinstance(first, dict) else None


def write_pr63_artifacts(*, output_dir: Path, packets_by_mode: dict[str, list[dict[str, Any]]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pr62_surface = _load_pr62_surface_by_key()
    targets = load_beat_question_targets()
    questions = {str(q["question_id"]): q for q in iter_target_questions(targets)}

    matrix_rows: list[dict[str, Any]] = []
    gold_phrase_leak = False
    source_derived_gaps_emitted = 0
    q3_route_gap_rendered = False

    for mode, packets in packets_by_mode.items():
        for packet in packets:
            qid = str(packet.get("question_id") or "")
            question = questions.get(qid, {})
            question_text = str(question.get("question") or packet.get("question") or "")
            candidate = packet.get("candidate_context") or []
            admitted = packet.get("admitted_context") or []
            source_gaps = packet.get("source_derived_context_gaps") or []
            if source_gaps:
                source_derived_gaps_emitted += len(source_gaps)

            rendered = render_context_packet(
                {
                    "question_number": packet.get("question_number"),
                    "question_id": packet.get("question_id"),
                    "question": question_text,
                    "retrieval_mode": mode,
                    "admission_policy": packet.get("admission_policy"),
                    "admitted_context": admitted,
                    "admission_budget": packet.get("admission_budget", {}),
                    "source_derived_context_gaps": source_gaps,
                }
            )
            provenance = rendered.get("provenance_map") or {}
            rendered_text = str(rendered.get("rendered_text") or "")

            for ev_key, pr62_surface_name in pr62_surface.items():
                question_id, group_id, ev_mode, expected_path = ev_key
                if question_id != qid or ev_mode != mode:
                    continue

                expected_section = _expected_section_id(group_id, expected_path)
                candidate_hit = any(expected_path.lower() in _record_refs(i) or group_id.lower() in _record_refs(i) for i in candidate)
                admitted_hit = any(expected_path.lower() in _record_refs(i) or group_id.lower() in _record_refs(i) for i in admitted)

                gap_obj = _first_source_derived_gap(packet) if "route_gap" in group_id.lower() or "known_gap" in expected_path.lower() else None
                gap_id = str(gap_obj.get("gap_id") or "") if gap_obj else ""
                gap_text = str(gap_obj.get("gap") or "") if gap_obj else ""
                gap_source = str(gap_obj.get("source") or "") if gap_obj else ""
                evidence_scope = str(gap_obj.get("evidence_scope") or "") if gap_obj else ""
                basis = gap_obj.get("basis") if gap_obj else {}
                basis_positive_refs = ""
                basis_missing_context_type = ""
                if isinstance(basis, dict):
                    refs = basis.get("positive_context_refs") or []
                    basis_positive_refs = "|".join(str(r) for r in refs)
                    basis_missing_context_type = str(basis.get("missing_context_type") or "")

                gold_gap_phrase_present = gap_text_contains_forbidden_gold_phrase(gap_text) or gap_text_contains_forbidden_gold_phrase(rendered_text)
                if gold_gap_phrase_present:
                    gold_phrase_leak = True

                prov = None
                rendered_section_hit = False
                if gap_obj and gap_id:
                    prov = provenance.get(gap_id)
                    rendered_section_hit = prov is not None and prov.get("rendered_section_id") == expected_section
                if not prov:
                    for pref, pentry in provenance.items():
                        if provenance_matches_expected(pentry, expected_path) or group_id.lower() in _record_refs(pentry):
                            prov = pentry
                            rendered_section_hit = pentry.get("rendered_section_id") == expected_section
                            break

                actual_section = str(prov.get("rendered_section_id") or "") if prov else ""

                if gap_obj and rendered_section_hit:
                    next_surface = "ok_or_later_stage"
                elif admitted_hit and rendered_section_hit:
                    next_surface = "ok_or_later_stage"
                elif admitted_hit and not rendered_section_hit:
                    next_surface = "rendered_section_mismatch"
                elif candidate_hit and not admitted_hit:
                    next_surface = "candidate_present_admission_deferred"
                elif gap_obj and not rendered_section_hit:
                    next_surface = "source_derived_gap_not_admitted_or_rendered"
                elif pr62_surface_name == "known_gap_missing_from_packet" and gap_obj:
                    next_surface = "ok_or_later_stage"
                else:
                    next_surface = pr62_surface_name or "source_exists_but_step2c_miss"

                if (
                    question_id == "q03_how_far_away_is_mirathorn_at_this_point"
                    and group_id == "mirathorn_exact_route_gap"
                    and rendered_section_hit
                ):
                    q3_route_gap_rendered = True

                matrix_rows.append(
                    {
                        "question_id": question_id,
                        "group_id": group_id,
                        "mode": mode,
                        "expected_path_or_unit_id": expected_path,
                        "pr62_surface": pr62_surface_name,
                        "source_derived_gap_id": gap_id,
                        "source_derived_gap_text": gap_text,
                        "source_derived_gap_source": gap_source,
                        "evidence_scope": evidence_scope,
                        "basis_positive_refs": basis_positive_refs,
                        "basis_missing_context_type": basis_missing_context_type,
                        "gold_gap_phrase_present": gold_gap_phrase_present,
                        "candidate_hit": candidate_hit,
                        "admitted_hit": admitted_hit,
                        "rendered_section_hit": rendered_section_hit,
                        "actual_rendered_section_id": actual_section,
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

    write_csv(output_dir / "pr63_source_derived_gap_matrix.csv", matrix_rows)
    write_csv(output_dir / "pr63_step2c_surface_matrix.csv", matrix_rows)

    surface_counts: dict[str, int] = {}
    for row in matrix_rows:
        surface = str(row.get("next_failure_surface") or "")
        surface_counts[surface] = surface_counts.get(surface, 0) + 1

    known_gap_missing_to_ok = sum(
        1
        for row in matrix_rows
        if row.get("pr62_surface") == "known_gap_missing_from_packet"
        and row.get("next_failure_surface") == "ok_or_later_stage"
    )
    pr62_ok_rows = sum(1 for row in matrix_rows if row.get("pr62_surface") == "ok_or_later_stage")
    pr63_ok_rows = sum(1 for row in matrix_rows if row.get("next_failure_surface") == "ok_or_later_stage")
    bogus_renderer_mismatches = [
        row
        for row in matrix_rows
        if row.get("pr62_surface") == "ok_or_later_stage"
        and row.get("next_failure_surface") == "rendered_section_mismatch"
    ]
    q3_distance_rows = [
        row
        for row in matrix_rows
        if row.get("question_id") == "q03_how_far_away_is_mirathorn_at_this_point"
        and row.get("group_id") == "mirathorn_distance_estimate_from_play"
    ]
    q3_distance_next_surface = q3_distance_rows[0].get("next_failure_surface") if q3_distance_rows else None

    (output_dir / "pr63_retrieval_universe_summary.json").write_text(
        json.dumps(
            {
                "schema": "dmb_pr63_retrieval_universe_summary_v1",
                "source_derived_gaps_emitted": source_derived_gaps_emitted,
                "q3_route_gap_rendered": q3_route_gap_rendered,
                "known_gap_missing_from_packet_to_ok": known_gap_missing_to_ok,
                "gold_gap_phrase_leakage": gold_phrase_leak,
                "pr62_ok_or_later_stage_rows": pr62_ok_rows,
                "pr63_ok_or_later_stage_rows": pr63_ok_rows,
                "bogus_renderer_mismatch_regressions": len(bogus_renderer_mismatches),
                "q3_distance_group_next_failure_surface": q3_distance_next_surface,
                "pr63_surface_counts": surface_counts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (output_dir / "README.md").write_text(
        "# PR63 source-derived context gap artifacts\n\n"
        "PR63 emits `source_derived_context_gaps` from deterministic absence analysis over allowed "
        "retrieved/admitted context. Gold `known_context_gaps` remain evaluator-only.\n\n"
        "See `pr63_source_derived_gap_matrix.csv` for per-target gap emission and rendering.\n",
        encoding="utf-8",
    )

    (output_dir / "pr63_next_pr_recommendations.md").write_text(
        "# Post-PR63 Planning Recommendations\n\n"
        "1. **Distance/play clue admission** — if Q3 still misses `mirathorn_distance_estimate_from_play`, "
        "classify as `source_derived_gap_hit_but_distance_context_missing` and address admission for "
        "`open-canon-questions` / week-estimate rows.\n"
        "2. **Planner/control metadata split** — remove evaluator fields from LLM-facing prompt payloads.\n",
        encoding="utf-8",
    )
