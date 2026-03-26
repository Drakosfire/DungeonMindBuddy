from __future__ import annotations

import json

from evals.canon_layering.run_benchmarks import OUT_DIR, main


def test_benchmark_runner_generates_required_artifacts() -> None:
    exit_code = main()
    assert exit_code == 0

    results_path = OUT_DIR / "results.json"
    report_path = OUT_DIR / "report.md"
    determinism_path = OUT_DIR / "determinism_hash_report.json"
    assert results_path.exists()
    assert report_path.exists()
    assert determinism_path.exists()

    results = json.loads(results_path.read_text(encoding="utf-8"))
    assert results["phase_pass"] is True
    for scenario_result in results["results"]:
        assert scenario_result["pass"] is True

