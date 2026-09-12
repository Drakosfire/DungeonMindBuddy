import json
import hashlib

import pytest

from extraction_lab.run_pair_experiment import ExperimentFailure
from extraction_lab.run_repeat_experiment import run_repeat_experiment

from tests.extraction_lab.test_repeat_experiment_manifest import SHA, _fixture, _write


def _child_factory(
    tmp_path,
    *,
    drift_at=None,
    fail_at=None,
    mutate_pair_at=None,
    child_sha_mismatch_at=None,
):
    calls = []
    def child(**kwargs):
        calls.append(kwargs)
        if not kwargs["execute"]:
            return {"mode": "dry_run", "plan": {"source_count": 1}}
        number = len([call for call in calls if call["execute"]])
        manifest_sha = hashlib.sha256(kwargs["manifest_path"].read_bytes()).hexdigest()
        if mutate_pair_at == number:
            kwargs["manifest_path"].write_text("{}", encoding="utf-8")
        if fail_at == number:
            raise ExperimentFailure(f"rep-{number:03d}", "injected")
        variants = {}
        for side in ("baseline", "candidate"):
            run = tmp_path / f"child-{number}-{side}"
            _write(run / "benchmark_contract.json", {"corpus": {"fingerprint": "corpus"}, "gold": {"fingerprint": "gold" if drift_at != number else "drift"}})
            variants[side] = {"extraction_lab_run_path": str(run), "observed_models": {"entity_extraction": "model", "fact_extraction": "model"},
                              "telemetry": {"cost_estimate": {"estimated_cost_usd": 0.1}, "run_window": {"elapsed_seconds": 1},
                                            "tokens": {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}, "api_calls": {"total": 1}}}
        comparison_path = tmp_path / f"comparison-{number}.json"
        metric = {name: {"baseline": 1, "candidate": 1, "delta": 0} for name in ("entity_anchor_recall", "fact_anchor_recall", "unresolved_core_anchors", "total_entity_count", "total_fact_count")}
        _write(comparison_path, {"metric_deltas": metric, "anchor_transitions": {"entity": [], "fact": []}})
        return {"schema": "dmb_extraction_pair_receipt_v1", "status": "completed", "manifest_sha256": "mismatch" if child_sha_mismatch_at == number else manifest_sha, "repository_sha": SHA, "surface": "core_extraction",
                "sources": [{"locator": "one.md", "sha256": "source"}], "gold": {"entity": {"sha256": "e"}, "fact": {"sha256": "f"}},
                "model_policy_sha256": "policy", "variants": variants,
                "comparison": {"status": "completed", "comparable": True, "artifact_path": str(comparison_path)}}
    return calls, child


def test_default_is_inert_and_describes_exact_work(tmp_path):
    repo, manifest = _fixture(tmp_path)
    calls, child = _child_factory(tmp_path)
    out = tmp_path / "out"
    result = run_repeat_experiment(manifest_path=manifest, out_dir=out, repo_root=repo, pair_runner=child)
    assert result["plan"]["variant_runs"] == 6
    assert result["plan"]["source_ingestions"] == 6
    assert [call["execute"] for call in calls] == [False]
    assert not out.exists()


def test_executes_fresh_roots_and_writes_completed_artifacts(tmp_path):
    repo, manifest = _fixture(tmp_path, repetitions=2)
    calls, child = _child_factory(tmp_path)
    out = tmp_path / "out"
    result = run_repeat_experiment(manifest_path=manifest, out_dir=out, execute=True, repo_root=repo, pair_runner=child)
    roots = [call["out_dir"] for call in calls if call["execute"]]
    assert roots == [out / "rep-001", out / "rep-002"]
    assert result["status"] == "completed"
    assert (out / "qualification.json").is_file()
    assert (out / "report.md").is_file()


@pytest.mark.parametrize("mode", ["drift", "failure", "manifest"])
def test_rep_two_failure_is_fail_fast_and_never_qualifies(tmp_path, mode):
    repo, manifest = _fixture(tmp_path)
    options = {"drift_at": 2} if mode == "drift" else {"fail_at": 2} if mode == "failure" else {"mutate_pair_at": 1}
    calls, child = _child_factory(tmp_path, **options)
    out = tmp_path / "out"
    with pytest.raises(ExperimentFailure):
        run_repeat_experiment(manifest_path=manifest, out_dir=out, execute=True, repo_root=repo, pair_runner=child)
    assert len([call for call in calls if call["execute"]]) <= 2
    assert not (out / "qualification.json").exists()
    receipt = json.loads((out / "repeat_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "failed"


def test_child_manifest_sha_must_equal_parent_pin(tmp_path):
    repo, manifest = _fixture(tmp_path, repetitions=2)
    calls, child = _child_factory(tmp_path, child_sha_mismatch_at=1)
    out = tmp_path / "out"
    with pytest.raises(ExperimentFailure, match="child_pair_manifest_sha_mismatch"):
        run_repeat_experiment(
            manifest_path=manifest,
            out_dir=out,
            execute=True,
            repo_root=repo,
            pair_runner=child,
        )
    assert len([call for call in calls if call["execute"]]) == 1
    assert not (out / "qualification.json").exists()


def test_manifest_mutation_during_final_repetition_blocks_qualification(tmp_path):
    repo, manifest = _fixture(tmp_path, repetitions=2)
    calls, child = _child_factory(tmp_path, mutate_pair_at=2)
    out = tmp_path / "out"
    with pytest.raises(ExperimentFailure, match="pair_manifest_drift"):
        run_repeat_experiment(
            manifest_path=manifest,
            out_dir=out,
            execute=True,
            repo_root=repo,
            pair_runner=child,
        )
    assert len([call for call in calls if call["execute"]]) == 2
    assert not (out / "qualification.json").exists()
