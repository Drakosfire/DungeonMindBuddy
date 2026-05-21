from pathlib import Path

import csv
import json

from evals.c1s4_preplanning_vertical_slice.audit_retrieval_universe import build_expected_evidence_manifest, classify_retrieval_failure, run_audit
from evals.c1s4_preplanning_vertical_slice.context_classification import is_allowed_retrieval_corpus_path


def _alias_matrix_row(
    matrix_path: Path,
    *,
    question_id: str,
    group_id: str,
    mode: str,
) -> dict[str, str]:
    with matrix_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (
                row["question_id"] == question_id
                and row["group_id"] == group_id
                and row["mode"] == mode
            ):
                return row
    raise AssertionError(f"no alias matrix row for {question_id=} {group_id=} {mode=}")


def test_expected_manifest_builds() -> None:
    rows = build_expected_evidence_manifest()
    assert any(r.group_id == "grishna_character_continuity" for r in rows)
    assert any(r.group_id == "stone_bridge_location_context" for r in rows)


def test_disk_hygiene_classification() -> None:
    assert Path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md").exists()
    assert is_allowed_retrieval_corpus_path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/pippa/README.md")
    assert not is_allowed_retrieval_corpus_path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json")


def test_taxonomy_classification() -> None:
    assert classify_retrieval_failure(exists=True, allowed=True, in_records=False, lexical_file_probe_hit=False, step2c_retrieved=False, step2c_candidate=False) == "source_not_materialized_as_retrieval_record"
    assert classify_retrieval_failure(exists=True, allowed=True, in_records=True, lexical_file_probe_hit=True, step2c_retrieved=False, step2c_candidate=False) == "source_exists_but_step2c_miss"
    assert classify_retrieval_failure(exists=True, allowed=True, in_records=True, lexical_file_probe_hit=True, step2c_retrieved=True, step2c_candidate=False) == "step2c_retrieved_but_candidate_missing"


def test_audit_validates_gold_and_step2c_report(tmp_path: Path) -> None:
    packets_path = tmp_path / "packets.json"
    packets_path.write_text(
        json.dumps({"prior_only": [], "prior_plus_support_content_only": [], "prior_plus_support_content_plus_lexical_hints": []}),
        encoding="utf-8",
    )
    report_path = Path("/tmp/c1s4_pr58_lane_aware_step2c_multimode_report.json")
    if not report_path.exists():
        report_path.write_text(
            json.dumps({"schema": "dmb_c1s4_expected_context_benchmark_multimode_report_v1", "reports_by_mode": {}}),
            encoding="utf-8",
        )
    summary = run_audit(
        output_dir=tmp_path / "audit",
        gold_path=Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json"),
        step2c_report_path=report_path,
        rebuild_step2c_packets=False,
        step2_packets_path=packets_path,
    )
    assert summary["inputs"]["gold_path"]
    assert summary["inputs"]["step2c_report_path"]
    assert summary["inputs"]["step2_packets_path"]


def test_pr59_artifact_alias_probe_uses_scoped_variant_retrieval(tmp_path: Path) -> None:
    run_audit(
        output_dir=tmp_path / "pr59",
        gold_path=Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json"),
        rebuild_step2c_packets=True,
    )
    matrix_path = tmp_path / "pr59" / "pr59_step2c_alias_probe_matrix.csv"
    row = _alias_matrix_row(
        matrix_path,
        question_id="q01_who_are_the_npcs_the_players_encountered",
        group_id="grishna_character_continuity",
        mode="prior_only",
    )
    assert row["alias_query_hit"] == "True"
    assert row["merged_candidate_hit"] == "True"

    manifest_path = tmp_path / "pr59" / "pr59_query_variant_manifest.csv"
    with manifest_path.open(newline="", encoding="utf-8") as f:
        grishna_alias_rows = [
            r
            for r in csv.DictReader(f)
            if r["question_id"] == "q01_who_are_the_npcs_the_players_encountered"
            and r["retrieval_mode"] == "prior_only"
            and r["variant_role"] == "npc_target_alias"
            and "grishna" in (r.get("query") or "").lower()
        ]
    assert grishna_alias_rows, "expected Grishna npc_target_alias manifest row"
    assert int(grishna_alias_rows[0]["hit_count"]) > 0
    assert grishna_alias_rows[0]["record_scope"] == "npc_target_alias"
    assert int(grishna_alias_rows[0]["scoped_record_count"]) > 0


def test_pr59_alias_matrix_moves_support_candidate_forward(tmp_path: Path) -> None:
    summary = run_audit(
        output_dir=tmp_path / "pr59",
        gold_path=Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json"),
        rebuild_step2c_packets=True,
    )
    assert summary["schema"] == "dmb_pr59_retrieval_universe_summary_v1"
    assert (tmp_path / "pr59" / "pr59_query_variant_manifest.csv").exists()
    assert (tmp_path / "pr59" / "pr59_step2c_alias_probe_matrix.csv").exists()
    matrix = (tmp_path / "pr59" / "pr59_step2c_alias_probe_matrix.csv").read_text(encoding="utf-8")
    assert "support:hempholm_tree_visible_threat" in matrix
    assert "merged_candidate_hit" in matrix


def test_pr62_summary_reports_q1_character_rows_rendered(tmp_path: Path) -> None:
    run_audit(
        output_dir=tmp_path / "pr62",
        gold_path=Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json"),
        rebuild_step2c_packets=True,
    )
    assert (tmp_path / "pr62" / "pr62_render_section_matrix.csv").exists()
    assert (tmp_path / "pr62" / "pr62_step2c_surface_matrix.csv").exists()
    data = json.loads((tmp_path / "pr62" / "pr62_retrieval_universe_summary.json").read_text(encoding="utf-8"))
    assert data["schema"] == "dmb_pr62_retrieval_universe_summary_v1"
    assert data["q1_character_rows_rendered"] is True
    assert data["rendered_section_mismatch_to_ok"] >= 5


def test_pr61_summary_reports_q1_grishna_moved_from_candidate_pool_gap_to_admitted_or_rendered_mismatch(
    tmp_path: Path,
) -> None:
    run_audit(
        output_dir=tmp_path / "pr61",
        gold_path=Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json"),
        rebuild_step2c_packets=True,
    )
    assert (tmp_path / "pr61" / "pr61_step2c_surface_matrix.csv").exists()
    assert (tmp_path / "pr61" / "pr61_candidate_merge_allocation_matrix.csv").exists()
    data = json.loads((tmp_path / "pr61" / "pr61_retrieval_universe_summary.json").read_text(encoding="utf-8"))
    assert data["schema"] == "dmb_pr61_retrieval_universe_summary_v1"
    assert data["q1_grishna_moved_from_candidate_pool_gap"] is True
    assert data["candidate_deferred_to_admitted"] >= 1


def test_pr60_summary_honestly_reports_no_deferred_target_moved_yet(tmp_path: Path) -> None:
    run_audit(
        output_dir=tmp_path / "pr60",
        gold_path=Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json"),
        rebuild_step2c_packets=True,
    )
    assert (tmp_path / "pr60" / "pr60_step2c_surface_matrix.csv").exists()
    assert (tmp_path / "pr60" / "pr60_admission_preservation_matrix.csv").exists()
    data = json.loads((tmp_path / "pr60" / "pr60_retrieval_universe_summary.json").read_text(encoding="utf-8"))
    assert data["schema"] == "dmb_pr60_retrieval_universe_summary_v1"
    assert data["admission_deferred_to_admitted"] == 0
    assert data["pr60_surface_counts"].get("candidate_present_admission_deferred") == 1


def test_pr57_artifacts_generated(tmp_path: Path) -> None:
    summary = run_audit(output_dir=tmp_path / "pr57")
    assert summary["schema"]
    assert (tmp_path / "pr57" / "pr57_retrieval_universe_summary.json").exists()
    assert (tmp_path / "pr57" / "pr57_expected_evidence_manifest.csv").exists()
