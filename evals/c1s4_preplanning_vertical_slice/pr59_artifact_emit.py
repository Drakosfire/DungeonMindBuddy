from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import iter_target_questions, load_beat_question_targets
from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet
from evals.c1s4_preplanning_vertical_slice.query_alias_expansion import build_step2c_query_variants
from evals.c1s4_preplanning_vertical_slice.query_variant_retrieval import (
    query_hits_for_variant,
    records_for_query_variant,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import _load_combined_records


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


def _load_pr58_status_by_key() -> dict[tuple[str, str, str, str], str]:
    path = Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr58/pr58_step2c_vs_direct_probe_matrix.csv")
    if not path.exists():
        return {}
    out: dict[tuple[str, str, str, str], str] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["question_id"], row["group_id"], row["mode"], row["expected_path"])
            out[key] = row.get("classification_status") or ""
    return out


def write_pr59_artifacts(*, output_dir: Path, packets_by_mode: dict[str, list[dict[str, Any]]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pr58_status_by_key = _load_pr58_status_by_key()
    targets = load_beat_question_targets()
    questions = {str(q["question_id"]): q for q in iter_target_questions(targets)}

    manifest_rows: list[dict[str, Any]] = []
    matrix_rows: list[dict[str, Any]] = []

    for mode, packets in packets_by_mode.items():
        _, records, _, _ = _load_combined_records(mode)  # type: ignore[arg-type]
        for packet in packets:
            qid = str(packet.get("question_id") or "")
            question = questions.get(qid, {})
            question_text = str(question.get("question") or packet.get("question") or "")
            variants = build_step2c_query_variants(question_text=question_text, retrieval_mode=mode)
            diag = packet.get("query_variant_diagnostics") or {}
            variant_hit_counts = {
                str(v.get("variant_role")): v for v in (diag.get("variant_hit_counts") or [])
            }
            rendered = render_context_packet(
                {
                    "question_number": packet.get("question_number"),
                    "question_id": packet.get("question_id"),
                    "question": question_text,
                    "retrieval_mode": mode,
                    "admission_policy": packet.get("admission_policy"),
                    "admitted_context": packet.get("admitted_context", []),
                    "admission_budget": packet.get("admission_budget", {}),
                }
            )
            provenance = rendered.get("provenance_map") or {}

            for idx, variant in enumerate(variants):
                role = str(variant.get("variant_role") or "")
                scoped_records = records_for_query_variant(records, variant)
                hits = query_hits_for_variant(
                    records=records,
                    variant=variant,
                    campaign_id="longmont-c1",
                    session_min=0,
                    session_max=3,
                )
                hit_count = len(hits)
                top_unit_ids = [str(h.get("unit_id") or "") for h in hits[:5]]
                manifest_rows.append(
                    {
                        "question_id": qid,
                        "question_number": packet.get("question_number"),
                        "retrieval_mode": mode,
                        "variant_index": idx,
                        "variant_role": role,
                        "target_lane": variant.get("target_lane"),
                        "query": variant.get("query"),
                        "reason": variant.get("reason"),
                        "record_scope": role if role != "literal_question" else "full_universe",
                        "scoped_record_count": len(scoped_records),
                        "hit_count": hit_count,
                        "top_unit_ids": "|".join(top_unit_ids),
                        "expected_target_hit": "",
                        "expected_target_rank": "",
                    }
                )

            candidate = packet.get("candidate_context") or []
            retrieved = packet.get("retrieved_context") or []
            admitted = packet.get("admitted_context") or []

            for ev_key, pr58_row_status in pr58_status_by_key.items():
                question_id, group_id, ev_mode, expected_path = ev_key
                if question_id != qid or ev_mode != mode:
                    continue
                literal_variant = variants[0]
                literal_hits = query_hits_for_variant(
                    records=records,
                    variant=literal_variant,
                    campaign_id="longmont-c1",
                    session_min=0,
                    session_max=3,
                )
                alias_queries = [v for v in variants if v.get("variant_role") != "literal_question"]
                alias_hits: list[dict[str, Any]] = []
                for variant in alias_queries:
                    alias_hits.extend(
                        query_hits_for_variant(
                            records=records,
                            variant=variant,
                            campaign_id="longmont-c1",
                            session_min=0,
                            session_max=3,
                        )
                    )
                needle = _family_needle(group_id, expected_path)
                if expected_path.lower().startswith("known_gap:"):
                    if packet.get("known_context_gaps"):
                        next_surface = "known_gap_oracle_leak_in_planner_packet"
                    else:
                        next_surface = "known_gap_eval_only_not_in_planner_packet"
                    matrix_rows.append(
                        {
                            "question_id": question_id,
                            "group_id": group_id,
                            "mode": mode,
                            "expected_path_or_unit_id": expected_path,
                            "pr58_status": pr58_row_status,
                            "literal_query_hit": False,
                            "alias_query_hit": False,
                            "merged_candidate_hit": False,
                            "retrieved_context_hit": False,
                            "admitted_context_hit": False,
                            "rendered_section_hit": False,
                            "next_failure_surface": next_surface,
                        }
                    )
                    continue
                literal_query_hit = any(needle in _record_refs(h) for h in literal_hits)
                alias_query_hit = any(needle in _record_refs(h) for h in alias_hits)
                merged_candidate_hit = any(needle in _record_refs(i) for i in candidate)
                retrieved_context_hit = any(needle in _record_refs(i) for i in retrieved)
                admitted_context_hit = any(needle in _record_refs(i) for i in admitted)
                rendered_section_hit = any(
                    needle in _record_refs({"unit_id": ref, **(provenance.get(ref) or {})})
                    for ref in provenance
                    if needle in str(ref).lower() or needle in str((provenance.get(ref) or {}).get("source_path") or "").lower()
                )
                if not rendered_section_hit:
                    rendered_section_hit = any(
                        needle in _record_refs(i)
                        for i in admitted
                        if str((provenance.get(str(i.get("unit_id") or i.get("ref") or "")) or {}).get("rendered_section_id") or "")
                    )
                for ref, meta in provenance.items():
                    if needle in ref.lower() or needle in str(meta.get("source_path") or "").lower():
                        rendered_section_hit = True
                        break

                if merged_candidate_hit and not admitted_context_hit:
                    next_surface = "candidate_present_admission_deferred"
                elif admitted_context_hit and not rendered_section_hit:
                    next_surface = "rendered_section_mismatch"
                elif admitted_context_hit and rendered_section_hit:
                    next_surface = "ok_or_later_stage"
                elif merged_candidate_hit:
                    next_surface = "step2c_candidate_hit"
                elif alias_query_hit and not literal_query_hit:
                    next_surface = "alias_probe_only"
                else:
                    next_surface = pr58_row_status or "source_exists_but_step2c_miss"

                matrix_rows.append(
                    {
                        "question_id": question_id,
                        "group_id": group_id,
                        "mode": mode,
                        "expected_path_or_unit_id": expected_path,
                        "pr58_status": pr58_row_status,
                        "literal_query_hit": literal_query_hit,
                        "alias_query_hit": alias_query_hit,
                        "merged_candidate_hit": merged_candidate_hit,
                        "retrieved_context_hit": retrieved_context_hit,
                        "admitted_context_hit": admitted_context_hit,
                        "rendered_section_hit": rendered_section_hit,
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

    write_csv(output_dir / "pr59_query_variant_manifest.csv", manifest_rows)
    write_csv(output_dir / "pr59_step2c_alias_probe_matrix.csv", matrix_rows)

    pr58_summary_path = Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr58/pr58_retrieval_universe_summary.json")
    pr58_counts = {}
    if pr58_summary_path.exists():
        pr58_counts = json.loads(pr58_summary_path.read_text(encoding="utf-8")).get("counts") or {}

    pr59_counts: dict[str, int] = {}
    for row in matrix_rows:
        status = str(row.get("next_failure_surface") or "")
        pr59_counts[status] = pr59_counts.get(status, 0) + 1

    (output_dir / "pr59_retrieval_universe_summary.json").write_text(
        json.dumps(
            {
                "schema": "dmb_pr59_retrieval_universe_summary_v1",
                "pr58_counts": pr58_counts,
                "pr59_alias_matrix_counts": pr59_counts,
                "moved_forward": sum(
                    1
                    for row in matrix_rows
                    if row.get("pr58_status") == "source_exists_but_step2c_miss"
                    and row.get("merged_candidate_hit")
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (output_dir / "README.md").write_text(
        "# PR59 query alias expansion artifacts\n\n"
        "Deterministic Step2C query variants bridge planner-language questions to materialized evidence records.\n"
        "See `pr59_query_variant_manifest.csv` for per-variant hit counts and "
        "`pr59_step2c_alias_probe_matrix.csv` for PR58→PR59 surface movement.\n",
        encoding="utf-8",
    )

    (output_dir / "pr59_next_pr_recommendations.md").write_text(
        "# Post-PR59 Planning Recommendations\n\n"
        "1. **PR60 — admission lane preservation:** If targets are candidate-visible but not admitted, preserve required-lane floors in `build_lane_budgeted_admission`.\n"
        "2. **PR61 — renderer section repair:** If admitted evidence renders under `prior_campaign_memory` instead of character/location sections, fix lane fold + `render_context_packet` routing.\n"
        "3. **PR62 — generalize alias rules:** Promote C1S4-scoped NPC/route/support alias rules into a reusable deterministic planner after PR59 evidence holds.\n"
        "4. Re-run audit + Step2C benchmark after each follow-up; do not weaken gold.\n",
        encoding="utf-8",
    )
