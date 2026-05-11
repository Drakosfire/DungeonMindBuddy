from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from evals.sentence_routing_retrieval_falsification.cohort_baseline_run import (
    COHORT_MANIFEST_SCHEMA_V1,
    COHORT_SUMMARY_SCHEMA_V2,
    _compute_recall_via_equivalence,
    _equivalence_can_rescue,
    _normalize_substring_to_slug,
    _workspace_relative_posix,
    build_cohort_summary,
    load_cohort_manifest,
)
from src.lexicon_phase_b.schemas import RouteEquivalenceRecord

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST = _REPO_ROOT / "evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json"


def test_workspace_relative_posix_in_repo() -> None:
    path = _REPO_ROOT / "evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json"
    assert _workspace_relative_posix(path, _REPO_ROOT).startswith("evals/")


def test_workspace_relative_posix_outside_repo() -> None:
    outside = Path("/tmp/some_file.json")
    assert _workspace_relative_posix(outside, _REPO_ROOT) == "some_file.json"


def test_load_cohort_manifest_validates_schema(tmp_path: Path) -> None:
    bad = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    bad["schema"] = "wrong"
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported cohort manifest schema"):
        load_cohort_manifest(p)


def test_load_cohort_manifest_validates_paths(tmp_path: Path) -> None:
    bad = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    bad["scenarios"][0]["gold"] = "evals/sentence_routing_retrieval_falsification/gold/missing.json"
    p = tmp_path / "bad_paths.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="missing scenario path"):
        load_cohort_manifest(p)


def _report(shadow: dict) -> dict:
    return {
        "gold_schema": "x",
        "all_ok": True,
        "results": [
            {"scenario_id": "q1", "ok": True, "violations": ["b", "a"], "shadow_route_equivalences": shadow},
            {"scenario_id": "q2", "ok": False, "violations": ["d", "c"], "shadow_route_equivalences": shadow},
        ],
    }


def _records() -> list[RouteEquivalenceRecord]:
    return [
        RouteEquivalenceRecord(
            record_id="r1",
            campaign_id="c1",
            entity_kind="npc",
            display_name="Captain Lysandra Ironveil",
            from_route_id="route:x:npc:captain-lysandra-ironveil",
            to_route_id="route:y:npc:captain-lysandra-ironveil",
            edge_kind="setting_fallback",
            source_type="npc_registry",
            authority_effect="routing_only",
            confidence="high",
        ),
        RouteEquivalenceRecord(
            record_id="r2",
            campaign_id="c1",
            entity_kind="npc",
            display_name="Marla Storm",
            from_route_id="route:x:npc:marla-storm",
            to_route_id="route:y:npc:marla-storm",
            edge_kind="setting_fallback",
            source_type="npc_registry",
            authority_effect="routing_only",
            confidence="high",
        ),
    ]


def test_build_cohort_summary_curates_expected_shape() -> None:
    manifest = load_cohort_manifest(_MANIFEST)
    summary = build_cohort_summary(
        manifest=manifest,
        per_scenario_reports=[_report({"schema": "s"}), _report({"schema": "s"}), _report({"schema": "s"})],
        workspace_root=_REPO_ROOT,
        manifest_path=_MANIFEST,
        route_equivalence_records=_records(),
    )
    assert summary["schema"] == COHORT_SUMMARY_SCHEMA_V2
    assert "aggregate_llm_cost_usd" not in summary
    assert "llm_model" not in summary
    assert len(summary["scenarios"]) == 3


def test_build_cohort_summary_rejects_inconsistent_shadow_payload() -> None:
    manifest = load_cohort_manifest(_MANIFEST)
    bad_report = {
        "gold_schema": "x",
        "all_ok": True,
        "results": [
            {"scenario_id": "q1", "ok": True, "violations": [], "shadow_route_equivalences": {"a": 1}},
            {"scenario_id": "q2", "ok": True, "violations": [], "shadow_route_equivalences": {"a": 2}},
        ],
    }
    with pytest.raises(ValueError, match="inconsistent shadow_route_equivalences"):
        build_cohort_summary(manifest=manifest, per_scenario_reports=[bad_report, _report({"a": 1}), _report({"a": 1})], workspace_root=_REPO_ROOT, manifest_path=_MANIFEST, route_equivalence_records=_records())


def test_build_cohort_summary_sorts_violations() -> None:
    manifest = load_cohort_manifest(_MANIFEST)
    summary = build_cohort_summary(manifest=manifest, per_scenario_reports=[_report({"a": 1}), _report({"a": 1}), _report({"a": 1})], workspace_root=_REPO_ROOT, manifest_path=_MANIFEST, route_equivalence_records=_records())
    assert summary["scenarios"][0]["violations"][0]["violations"] == ["a", "b"]


def test_cohort_baseline_run_write_produces_summary_with_committed_manifest(tmp_path: Path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    out = tmp_path / "summary.json"
    run = subprocess.run([
        "uv", "run", "--directory", str(_REPO_ROOT), "python", "-m", "evals.sentence_routing_retrieval_falsification.cohort_baseline_run", "--write", "--manifest", str(_MANIFEST), "--baseline", str(out)
    ], capture_output=True, text=True, cwd=str(_REPO_ROOT))
    assert run.returncode == 0, run.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == COHORT_SUMMARY_SCHEMA_V2
    assert len(data["scenarios"]) == 3


def test_cohort_baseline_run_write_is_byte_identical_across_cwds(tmp_path: Path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    out_a = tmp_path / "from_repo_root.json"
    out_b = tmp_path / "from_subdir.json"
    cmd_base = [
        "uv", "run", "--directory", str(_REPO_ROOT), "python", "-m", "evals.sentence_routing_retrieval_falsification.cohort_baseline_run", "--write", "--manifest", "evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json",
    ]
    run_a = subprocess.run(cmd_base + ["--baseline", str(out_a)], capture_output=True, text=True, cwd=str(_REPO_ROOT))
    run_b = subprocess.run(cmd_base + ["--baseline", str(out_b)], capture_output=True, text=True, cwd=str(_REPO_ROOT / "tests"))
    assert run_a.returncode == 0, run_a.stderr
    assert run_b.returncode == 0, run_b.stderr
    assert out_a.read_bytes() == out_b.read_bytes()


def test_normalize_substring_to_slug_examples() -> None:
    assert _normalize_substring_to_slug("Campaign 1/PCs/karsemine") == "karsemine"
    assert _normalize_substring_to_slug("campaign 1/locations/wizards_tower_brewing_company") == "wizards-tower-brewing-company"


def test_equivalence_can_rescue_positive_and_negative() -> None:
    records = _records()
    assert _equivalence_can_rescue("captain-lysandra-ironveil", records)
    assert not _equivalence_can_rescue("not-present", records)


def test_compute_recall_via_equivalence_denominator_zero_returns_none() -> None:
    assert _compute_recall_via_equivalence(
        breakdown=[{"substring": "Campaign 1/PCs/karsemine", "matched": True}],
        records=_records(),
    ) is None


def test_compute_recall_via_equivalence_rescued_and_unrescued() -> None:
    records = _records()
    rescued = _compute_recall_via_equivalence(
        breakdown=[{"substring": "Campaign 1/NPCs/captain_lysandra_ironveil", "matched": False}],
        records=records,
    )
    assert rescued is not None
    assert rescued["recall"] == 1.0
    unrescued = _compute_recall_via_equivalence(
        breakdown=[{"substring": "Campaign 1/NPCs/unknown_person", "matched": False}],
        records=records,
    )
    assert unrescued is not None
    assert unrescued["recall"] == 0.0

def test_run_one_scenario_skip_flag_is_derived_from_scenario_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from evals.sentence_routing_retrieval_falsification import cohort_baseline_run as m
    seen = {}
    def fake_run(cmd, **kwargs):
        seen['cmd']=cmd
        class X: pass
        return X()
    monkeypatch.setattr(subprocess, 'run', fake_run)
    out = tmp_path / 'o.json'
    out.write_text('{"results": []}', encoding='utf-8')
    m.run_one_scenario(scenario={'scenario_id':'c1s1','records_jsonl':'a','gold':'b'}, route_equivalence_jsonl=[], workspace_root=_REPO_ROOT, per_scenario_out=out)
    assert '--skip-c1s1-canvas-refresh' in seen['cmd']


def test_mode_both_write_delta_schema(tmp_path: Path) -> None:
    if shutil.which('uv') is None:
        pytest.skip('uv not available')
    out = tmp_path / 'delta.json'
    run = subprocess.run(['uv','run','--directory',str(_REPO_ROOT),'python','-m','evals.sentence_routing_retrieval_falsification.cohort_baseline_run','--mode','both','--write-delta',str(out)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    data = json.loads(out.read_text(encoding='utf-8'))
    assert data['schema_id'] == 'dmb_breadcrumb_query_cohort_l3_delta_v1'
    assert 'delta_summary' in data
