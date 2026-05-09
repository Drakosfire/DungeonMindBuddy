from __future__ import annotations

import json
from pathlib import Path

from evals.stage_d_entity_resolution_vertical_slice.stage_e_scaffold_grader import (
    grade_stage_e_scaffold,
)
from evals.stage_d_entity_resolution_vertical_slice.step2_stage_e_npc_hub_scaffold import (
    run_stage_e_scaffold,
)


def _write_payload(path: Path) -> Path:
    payload = {
        "schema": "stage_d_promotion_v2",
        "campaign_id": "longmont-c1",
        "branch_scaffold_proposals": [
            {
                "slug": "kirfan",
                "display_name": "Kirfan",
                "location_slug": "upriver_river_route",
                "divergence_mode": "inherit",
                "world_parent_hub_path": "Elderwyld/Cities and Towns/Upriver River Route/NPCs/kirfan/",
                "campaign_overlay_hub_path": "Longmont Campaign/Campaign 1/NPCs/kirfan/",
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_stage_e_grader_passes_for_committed_contract(tmp_path: Path) -> None:
    promotion = _write_payload(tmp_path / "promotion.json")
    report = run_stage_e_scaffold(
        promotion_json=promotion,
        corpus_root=tmp_path / "corpus",
        commit=True,
        out_dir=tmp_path / "out",
    )
    grading = report["grading"]
    assert grading["gates_passed"] == "3/3"
    assert not grading["violations"]


def test_stage_e_grader_detects_count_drift(tmp_path: Path) -> None:
    promotion = _write_payload(tmp_path / "promotion.json")
    report = run_stage_e_scaffold(
        promotion_json=promotion,
        corpus_root=tmp_path / "corpus",
        commit=False,
        out_dir=tmp_path / "out",
    )
    report["counts"]["ops_total"] = 999
    grading = grade_stage_e_scaffold(report, corpus_root=tmp_path / "corpus")
    assert grading["per_gate_verdict"]["EE1"] == "FAIL"
    assert any("ops_total" in v for v in grading["violations"])
