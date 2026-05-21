from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import iter_target_questions, load_beat_question_targets
from evals.c1s4_preplanning_vertical_slice.context_renderer import provenance_matches_expected, render_context_packet


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


def _expected_section_id(group_id: str, expected_path: str) -> str:
    gl = group_id.lower()
    if "support" in gl or "hempholm" in gl:
        return "support_knowledge"
    if "stone_bridge" in gl or "mirathorn" in gl or "location" in gl:
        return "location_worldbuilding"
    if any(token in gl for token in ("pippa", "bubbles", "grishna", "npc", "character", "party")):
        return "character_party_behavior"
    if "readme" in expected_path.lower() and "/locations/" in expected_path.lower():
        return "location_worldbuilding"
    if "/npcs/" in expected_path.lower() or "/pcs/" in expected_path.lower():
        return "character_party_behavior"
    return "prior_campaign_memory"


def _load_pr61_surface_by_key() -> dict[tuple[str, str, str, str], str]:
    path = Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr61/pr61_step2c_surface_matrix.csv")
    if not path.exists():
        return {}
    out: dict[tuple[str, str, str, str], str] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["question_id"], row["group_id"], row["mode"], row["expected_path_or_unit_id"])
            out[key] = row.get("next_failure_surface") or ""
    return out


def _find_provenance_for_target(
    provenance: dict[str, dict[str, Any]],
    *,
    expected_path: str,
    needle: str,
    admitted: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for prov in provenance.values():
        if provenance_matches_expected(prov, expected_path) or provenance_matches_expected(prov, needle):
            return prov
    for item in admitted:
        ref = str(item.get("unit_id") or item.get("ref") or "")
        prov = provenance.get(ref)
        if prov and (needle in _record_refs(item) or provenance_matches_expected(prov, expected_path)):
            return prov
    return None


def write_pr62_artifacts(*, output_dir: Path, packets_by_mode: dict[str, list[dict[str, Any]]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pr61_surface = _load_pr61_surface_by_key()
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

            for ev_key, pr61_surface_name in pr61_surface.items():
                question_id, group_id, ev_mode, expected_path = ev_key
                if question_id != qid or ev_mode != mode:
                    continue
                needle = _family_needle(group_id, expected_path)
                expected_section = _expected_section_id(group_id, expected_path)
                candidate_hit = any(needle in _record_refs(i) for i in candidate)
                admitted_hit = any(needle in _record_refs(i) for i in admitted)

                prov = _find_provenance_for_target(
                    provenance,
                    expected_path=expected_path,
                    needle=needle,
                    admitted=admitted,
                )
                rendered_section_hit = prov is not None and (
                    provenance_matches_expected(prov, expected_path)
                    or (needle in _record_refs(prov) and prov.get("rendered_section_id") == expected_section)
                )
                actual_section = str(prov.get("rendered_section_id") or "") if prov else ""
                route_reason = str(prov.get("route_reason") or "") if prov else ""

                if admitted_hit and rendered_section_hit:
                    next_surface = "ok_or_later_stage"
                elif admitted_hit and not rendered_section_hit:
                    next_surface = "rendered_section_mismatch"
                elif candidate_hit and not admitted_hit:
                    next_surface = "candidate_present_admission_deferred"
                else:
                    next_surface = pr61_surface_name or "source_exists_but_step2c_miss"

                matrix_rows.append(
                    {
                        "question_id": question_id,
                        "group_id": group_id,
                        "mode": mode,
                        "expected_path_or_unit_id": expected_path,
                        "pr61_surface": pr61_surface_name,
                        "candidate_hit": candidate_hit,
                        "admitted_hit": admitted_hit,
                        "rendered_section_hit": rendered_section_hit,
                        "expected_section_id": expected_section,
                        "actual_rendered_section_id": actual_section,
                        "presentation_lane": str((prov or {}).get("presentation_lane") or ""),
                        "admission_budget_lane": str((prov or {}).get("admission_budget_lane") or ""),
                        "source_path_in_provenance": bool((prov or {}).get("source_path")),
                        "source_reference_in_provenance": (prov or {}).get("source_reference") is not None,
                        "route_reason": route_reason,
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

    write_csv(output_dir / "pr62_render_section_matrix.csv", matrix_rows)
    write_csv(output_dir / "pr62_step2c_surface_matrix.csv", matrix_rows)

    moved = sum(
        1
        for row in matrix_rows
        if row.get("pr61_surface") == "rendered_section_mismatch" and row.get("rendered_section_hit")
    )
    q1_character_rows = [
        r
        for r in matrix_rows
        if r.get("question_id") == "q01_who_are_the_npcs_the_players_encountered"
        and any(token in str(r.get("group_id") or "").lower() for token in ("pippa", "bubbles", "grishna"))
    ]
    q1_character_rendered = bool(q1_character_rows) and all(r.get("rendered_section_hit") for r in q1_character_rows)

    surface_counts: dict[str, int] = {}
    for row in matrix_rows:
        surface = str(row.get("next_failure_surface") or "")
        surface_counts[surface] = surface_counts.get(surface, 0) + 1

    (output_dir / "pr62_retrieval_universe_summary.json").write_text(
        json.dumps(
            {
                "schema": "dmb_pr62_retrieval_universe_summary_v1",
                "rendered_section_mismatch_to_ok": moved,
                "q1_character_rows_rendered": q1_character_rendered,
                "pr62_surface_counts": surface_counts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (output_dir / "README.md").write_text(
        "# PR62 renderer / provenance section repair artifacts\n\n"
        "PR62 expands provenance metadata and routes admitted items by semantic `presentation_lane` "
        "before prior-memory fallback.\n\n"
        "See `pr62_render_section_matrix.csv` for per-target section routing and provenance coverage.\n",
        encoding="utf-8",
    )

    (output_dir / "pr62_next_pr_recommendations.md").write_text(
        "# Post-PR62 Planning Recommendations\n\n"
        "1. **Source-derived gap admission** — derive known-gap wording from retrieved evidence only; never inject gold gap strings into planner packets.\n"
        "2. **Generalize C1S4-scoped renderer/admission/merge rules** once benchmark surfaces are stable.\n",
        encoding="utf-8",
    )
