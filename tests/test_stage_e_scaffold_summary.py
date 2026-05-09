from __future__ import annotations

import json
from pathlib import Path

from evals.stage_d_entity_resolution_vertical_slice.stage_e_scaffold_summary import (
    build_stage_e_cohort_payload,
    write_stage_e_cohort_summary,
)


def _report(
    *,
    gates_passed: str,
    ee1: str = "PASS",
    ee2: str = "PASS",
    ee3: str = "PASS",
    committed: int = 0,
    skipped: int = 10,
) -> dict[str, object]:
    return {
        "generated_at": "2026-05-08T00:00:00Z",
        "campaign_id": "longmont-c1",
        "promotion_source": "x.json",
        "counts": {
            "ops_total": committed + skipped,
            "preview_ok": 0,
            "preview_error": 0,
            "committed": committed,
            "commit_error": 0,
            "skipped_existing": skipped,
        },
        "grading": {
            "gates_passed": gates_passed,
            "per_gate_verdict": {"EE1": ee1, "EE2": ee2, "EE3": ee3},
            "violation_counts": {
                "EE1": 0 if ee1 == "PASS" else 1,
                "EE2": 0 if ee2 == "PASS" else 1,
                "EE3": 0 if ee3 == "PASS" else 1,
            },
        },
    }


def test_build_stage_e_cohort_payload_counts_passes() -> None:
    payload = build_stage_e_cohort_payload(
        [
            _report(gates_passed="3/3", committed=10, skipped=0),
            _report(gates_passed="2/3", ee3="FAIL", committed=0, skipped=10),
        ]
    )
    assert payload["n"] == 2
    assert payload["graded_runs"] == 2
    assert payload["passed"] == 1
    assert payload["per_gate_pass_counts"]["EE3"] == 1
    assert payload["aggregate_status_counts"]["committed"] == 10
    assert payload["aggregate_status_counts"]["skipped_existing"] == 10
    assert payload["aggregate_violation_counts"]["EE3"] == 1


def test_write_stage_e_cohort_summary_writes_json_and_md(tmp_path: Path) -> None:
    report_a = tmp_path / "a.json"
    report_b = tmp_path / "b.json"
    report_a.write_text(json.dumps(_report(gates_passed="3/3")), encoding="utf-8")
    report_b.write_text(
        json.dumps(_report(gates_passed="2/3", ee2="FAIL")), encoding="utf-8"
    )
    md_path, json_path = write_stage_e_cohort_summary(
        report_paths=[report_a, report_b], out_dir=tmp_path
    )
    assert md_path.exists()
    assert json_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "stage_e_scaffold_cohort_summary_v1"
    assert payload["n"] == 2
    assert payload["graded_runs"] == 2
    assert payload["per_gate_pass_counts"]["EE2"] == 1
