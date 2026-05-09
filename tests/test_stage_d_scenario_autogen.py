from __future__ import annotations

import json
from pathlib import Path

from evals.stage_d_entity_resolution_vertical_slice.step0_stage_d_scenario_autogen import (
    autogen_stage_d_scenarios,
    build_stage_d_scenario_from_stage_c,
)


def test_build_stage_d_scenario_from_stage_c_maps_core_fields() -> None:
    stage_c = {
        "scenario_id": "stage_c_session42_c9",
        "input": {
            "campaign_id": "longmont-c9",
            "session_label": "Session 42 (C9)",
            "stage_a_events_path": "evals/stage_c_npc_candidates_vertical_slice/fixtures/stage_a_events_session42_c9.json",
            "npc_registry_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 9/_npc_registry.json",
            "pc_roster": [{"slug": "x", "display_name": "X", "aliases": []}],
        },
        "grading": {
            "expected_new_candidates_should_include_at_least_one_of": ["foo", "bar"]
        },
    }
    out = build_stage_d_scenario_from_stage_c(stage_c, suffix="session42_c9")
    assert out["scenario_id"] == "stage_d_session42_c9"
    assert out["input"]["session_number"] == 42
    assert out["input"]["stage_c_output_path"].endswith("stage_c_output_session42_c9.json")
    assert out["grading"]["expected_proposed_new_records_minimum_slugs"] == ["foo", "bar"]


def test_autogen_stage_d_scenarios_writes_when_fixture_exists(tmp_path: Path) -> None:
    stage_c_gold = tmp_path / "stage_c_one.json"
    stage_c_gold.write_text(
        json.dumps(
            {
                "scenario_id": "stage_c_session1_c1",
                "input": {
                    "campaign_id": "longmont-c1",
                    "session_label": "Session 1 (C1)",
                    "stage_a_events_path": "a.json",
                    "npc_registry_path": "r.json",
                    "pc_roster": [],
                },
                "grading": {},
            }
        ),
        encoding="utf-8",
    )
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    (fixtures / "stage_c_output_session1_c1.json").write_text("{}", encoding="utf-8")
    out_gold = tmp_path / "gold"
    payload = autogen_stage_d_scenarios(
        stage_c_gold_glob=str(stage_c_gold),
        stage_d_gold_dir=out_gold,
        stage_d_fixtures_dir=fixtures,
    )
    assert payload["generated_count"] == 1
    out_path = out_gold / "stage_d_session1_c1.json"
    assert out_path.exists()
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["scenario_id"] == "stage_d_session1_c1"


def test_autogen_materializes_missing_fixture_from_latest_sidecar(tmp_path: Path) -> None:
    stage_c_gold = tmp_path / "stage_c_one.json"
    stage_c_gold.write_text(
        json.dumps(
            {
                "scenario_id": "stage_c_session9_c1",
                "input": {
                    "campaign_id": "longmont-c1",
                    "session_label": "Session 9 (C1)",
                    "stage_a_events_path": "a.json",
                    "npc_registry_path": "r.json",
                    "pc_roster": [],
                },
                "grading": {},
            }
        ),
        encoding="utf-8",
    )
    fixtures = tmp_path / "fixtures"
    out_gold = tmp_path / "gold"
    sidecars = tmp_path / "sidecars"
    sidecars.mkdir(parents=True, exist_ok=True)
    old_sidecar = sidecars / "old.json"
    new_sidecar = sidecars / "new.json"
    old_sidecar.write_text(
        json.dumps(
            {
                "scenario_id": "stage_c_session9_c1",
                "iso_utc": "2026-05-01T00:00:00Z",
                "stage_c_output": {"tracked_npcs_active": [], "new_npc_candidates": [{"descriptor": "old"}]},
            }
        ),
        encoding="utf-8",
    )
    new_sidecar.write_text(
        json.dumps(
            {
                "scenario_id": "stage_c_session9_c1",
                "iso_utc": "2026-05-02T00:00:00Z",
                "stage_c_output": {
                    "tracked_npcs_active": [],
                    "new_npc_candidates": [{"descriptor": "newer"}],
                    "unresolved_descriptors": [],
                },
            }
        ),
        encoding="utf-8",
    )

    payload = autogen_stage_d_scenarios(
        stage_c_gold_glob=str(stage_c_gold),
        stage_d_gold_dir=out_gold,
        stage_d_fixtures_dir=fixtures,
        materialize_missing_stage_c_output=True,
        stage_c_sidecar_glob=str(sidecars / "*.json"),
    )
    fixture_path = fixtures / "stage_c_output_session9_c1.json"
    assert fixture_path.exists()
    materialized = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert materialized["new_npc_candidates"][0]["descriptor"] == "newer"
    assert payload["materialized_fixture_count"] == 1
    assert payload["generated_count"] == 1
