"""Regression test for Stage D cohort-proposals filename collision.

Two scenarios in the same campaign written within the same second must NOT
overwrite each other. The filename pattern is keyed on
(campaign_id, scenario_id, ts) — not just (campaign_id, ts).

Pure offline: uses pytest's ``tmp_path`` fixture; no network, no real
``proposals/`` directory touched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.stage_d_entity_resolution_vertical_slice.stage_d_run_report import (
    StageDRunSummary,
    write_stage_d_cohort_proposals,
)


def _make_summary(slug: str) -> StageDRunSummary:
    return StageDRunSummary(
        run_index=0,
        iso_utc="2026-04-22T21:35:52Z",
        gates_passed=True,
        resolved_count=0,
        proposed_new_records_count=1,
        proposed_aliases_count=0,
        unresolvable_count=0,
        violation_counts={},
        per_gate_verdict={},
        primary_md_path="",
        sidecar_json_path="",
        extras={
            "stage_d_output": {
                "proposed_new_records": [
                    {
                        "slug": slug,
                        "display_name": slug.replace("-", " ").title(),
                        "aliases": [],
                        "first_session": 1,
                        "last_session": 1,
                        "notes": "",
                    }
                ],
                "proposed_aliases": [],
                "unresolvable": [],
            }
        },
    )


def test_same_campaign_different_scenarios_do_not_collide(tmp_path: Path) -> None:
    summaries_a = [_make_summary("npc-alpha")]
    summaries_b = [_make_summary("npc-beta")]

    path_a = write_stage_d_cohort_proposals(
        summaries_a,
        scenario_id="scenario_a",
        campaign_id="longmont-c1",
        proposals_root=tmp_path,
    )
    path_b = write_stage_d_cohort_proposals(
        summaries_b,
        scenario_id="scenario_b",
        campaign_id="longmont-c1",
        proposals_root=tmp_path,
    )

    assert path_a is not None
    assert path_b is not None
    assert path_a != path_b, "scenario_a and scenario_b must produce distinct files"

    written = sorted(p.name for p in tmp_path.glob("*.json"))
    assert len(written) == 2, f"expected 2 distinct files, got {written}"

    payload_a = json.loads(path_a.read_text(encoding="utf-8"))
    payload_b = json.loads(path_b.read_text(encoding="utf-8"))

    assert payload_a["scenario_id"] == "scenario_a"
    assert payload_b["scenario_id"] == "scenario_b"
    assert payload_a["campaign_id"] == "longmont-c1"
    assert payload_b["campaign_id"] == "longmont-c1"

    slugs_a = {r["slug"] for r in payload_a["proposed_records"]}
    slugs_b = {r["slug"] for r in payload_b["proposed_records"]}
    assert slugs_a == {"npc-alpha"}
    assert slugs_b == {"npc-beta"}

    for name in written:
        assert "longmont-c1__scenario_" in name, (
            f"filename {name!r} should contain campaign__scenario segment"
        )
        assert "__stage_d_proposals_" in name


def test_filename_sanitizes_scenario_id(tmp_path: Path) -> None:
    summaries = [_make_summary("npc-gamma")]
    path = write_stage_d_cohort_proposals(
        summaries,
        scenario_id="stage_d_live_from_c_session1_c1",
        campaign_id="longmont-c1",
        proposals_root=tmp_path,
    )
    assert path is not None
    assert path.exists()
    assert "longmont-c1__stage_d_live_from_c_session1_c1__stage_d_proposals_" in path.name
