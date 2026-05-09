from __future__ import annotations

from pathlib import Path

from evals.stage_d_entity_resolution_vertical_slice import step3_stage_d_to_e_auto as auto


def test_discover_scenarios_matches_tmp_glob(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    got = auto.discover_scenarios(str(tmp_path / "*.json"))
    assert [p.name for p in got] == ["a.json", "b.json"]


def test_run_auto_pipeline_collects_success_and_failure(
    tmp_path: Path, monkeypatch
) -> None:
    s_ok = tmp_path / "ok.scenario.json"
    s_bad = tmp_path / "bad.scenario.json"
    s_ok.write_text("{}", encoding="utf-8")
    s_bad.write_text("{}", encoding="utf-8")

    def fake_run_one(**kwargs):  # type: ignore[no-untyped-def]
        p = Path(kwargs["scenario_path"])
        if p.name == "bad.scenario.json":
            raise RuntimeError("boom")
        return {
            "scenario_id": "x",
            "stage_e_report_path": str(tmp_path / "rep.json"),
            "promotion_cost_usd": 0.0,
        }

    def fake_summary(**kwargs):  # type: ignore[no-untyped-def]
        return (tmp_path / "s.md", tmp_path / "s.json")

    (tmp_path / "rep.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(auto, "_run_one_scenario", fake_run_one)
    monkeypatch.setattr(auto, "write_stage_e_cohort_summary", fake_summary)

    payload = auto.run_auto_pipeline(scenario_glob=str(tmp_path / "*.scenario.json"))
    assert payload["runs_total"] == 2
    assert payload["runs_succeeded"] == 1
    assert payload["runs_failed"] == 1
    assert payload["stage_e_summary_json"] == str(tmp_path / "s.json")


def test_run_auto_pipeline_records_autogen_payload(tmp_path: Path, monkeypatch) -> None:
    s_ok = tmp_path / "ok.scenario.json"
    s_ok.write_text("{}", encoding="utf-8")

    def fake_run_one(**kwargs):  # type: ignore[no-untyped-def]
        return {
            "scenario_id": "x",
            "stage_e_report_path": str(tmp_path / "rep.json"),
            "promotion_cost_usd": 0.0,
        }

    def fake_summary(**kwargs):  # type: ignore[no-untyped-def]
        return (tmp_path / "s.md", tmp_path / "s.json")

    captured: dict[str, object] = {}

    def fake_autogen(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return {"generated_count": 2, "skipped_count": 0}

    (tmp_path / "rep.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(auto, "_run_one_scenario", fake_run_one)
    monkeypatch.setattr(auto, "write_stage_e_cohort_summary", fake_summary)
    monkeypatch.setattr(auto, "autogen_stage_d_scenarios", fake_autogen)

    payload = auto.run_auto_pipeline(
        scenario_glob=str(tmp_path / "*.scenario.json"),
        autogen_stage_d_gold=True,
        autogen_materialize_missing_stage_c_output=True,
        autogen_stage_c_sidecar_glob="abc/*.json",
    )
    assert payload["autogen"] == {"generated_count": 2, "skipped_count": 0}
    assert captured["overwrite"] is False
    assert captured["materialize_missing_stage_c_output"] is True
    assert captured["stage_c_sidecar_glob"] == "abc/*.json"
