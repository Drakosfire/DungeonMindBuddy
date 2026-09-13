import json
import subprocess
from pathlib import Path

import pytest

from extraction_lab.campaign_memory_exploratory_qualification import qualify_screen
from extraction_lab.campaign_memory_exploratory_screen_manifest import (
    MODELS,
    build_screen_manifest_payload,
)
from extraction_lab.run_campaign_memory_exploratory_screen import run_screen
from extraction_lab.run_pair_experiment import ExperimentFailure


ROOT = Path(__file__).resolve().parents[2]
SHA = "b" * 40


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _manifest(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.json"
    _write_json(path, build_screen_manifest_payload(repo_root=ROOT, repository_sha=SHA))
    return path


def _fake_census(root, *, batch_size=5, paths=None):
    n = len(list(paths)) if paths is not None else 100
    return {
        "schema": "dmb_campaign_memory_corpus_census_v1",
        "corpus_root": str(root),
        "markdown_source_count": n,
        "raw_source_bytes": n * 10,
        "parseable_source_count": n,
        "compatibility_normalized_source_count": 0,
        "rejected_source_count": 0,
        "rejection_buckets": {},
        "evidence_unit_count": n * 2,
        "evidence_unit_text_bytes": n * 20,
        "expected_entity_calls": n,
        "expected_fact_calls": n,
        "batch_size": batch_size,
        "model_calls": 0,
        "silent_skip_count": 0,
        "sources": [],
        "largest_sources": [],
        "source_bytes_distribution": {"min": 1, "median": 1, "p95": 1, "max": 1},
        "evidence_units_distribution": {"min": 1, "median": 1, "p95": 1, "max": 1},
    }


def _fake_lab(**kwargs):
    out = Path(kwargs["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "entity_results.json", [])
    _write_json(out / "fact_results.json", [])
    _write_json(
        out / "aggregate_metrics.json",
        {"entity_anchor_recall": 1.0, "fact_anchor_recall": 0.6},
    )
    return out


def _fake_batch(calls, *, cost=0.01):
    def fake(argv, cwd):
        calls.append(list(argv))
        store = Path(argv[argv.index("--store") + 1])
        model = argv[argv.index("--structured-generation-model") + 1]
        _write_json(store / "entities.json", [{"entity_id": "e1"}])
        _write_json(store / "facts.json", [{"fact_id": "f1"}])
        logs = store / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (store / ".cache").mkdir(exist_ok=True)
        rows = [
            {"stage": "entity_extraction", "model_name": model},
            {"stage": "fact_extraction", "model_name": model},
        ]
        (logs / "model_calls.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        _write_json(
            logs / "batch_report.json",
            {
                "run_window": {"elapsed_seconds": 1.25},
                "files": {"total": 7, "succeeded": 7, "failed": 0, "skipped": 0},
                "api_calls": {"total": 4},
                "tokens": {
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "cached_tokens": 2,
                    "cached_input_tokens": 2,
                    "uncached_input_tokens": 18,
                    "reasoning_tokens": 4,
                    "visible_output_tokens": 6,
                    "parsed_output_bytes": 50,
                    "cache_rate": 0.1,
                },
                "cost_estimate": {"estimated_cost_usd": cost},
                "local_cache": {"overall_hit_rate": 0.0},
            },
        )
        return subprocess.CompletedProcess(argv, 0, stdout="batch ok", stderr="")

    return fake


def _run(tmp_path: Path, out: Path, **kwargs):
    return run_screen(
        manifest_path=_manifest(tmp_path),
        out_dir=out,
        repo_root=ROOT,
        repository_sha_reader=lambda _root: SHA,
        worktree_clean_reader=lambda _root: True,
        census_fn=_fake_census,
        lab_fn=_fake_lab,
        environ={"OPENAI_API_KEY": "test-only"},
        **kwargs,
    )


def test_dry_run_sends_zero_api_calls_and_creates_no_output(tmp_path: Path) -> None:
    calls = []
    out = tmp_path / "out"
    result = _run(tmp_path, out, runner=_fake_batch(calls))
    assert result["mode"] == "dry_run"
    assert result["api_calls"] == 0
    assert result["plan"]["will_execute"] is False
    assert result["plan"]["run_order"] == MODELS
    assert result["plan"]["repetitions_per_model"] == 1
    assert result["plan"]["reasoning_effort"] == "medium"
    assert calls == []
    assert not out.exists()


def test_execute_isolates_stores_and_freezes_shared_contract(tmp_path: Path) -> None:
    calls = []
    out = tmp_path / "out"
    receipt = _run(tmp_path, out, execute=True, runner=_fake_batch(calls))
    assert receipt["status"] == "completed"
    assert [row["model"] for row in receipt["arms"]] == MODELS
    assert len(calls) == 3
    stores = [Path(argv[argv.index("--store") + 1]) for argv in calls]
    assert len(set(stores)) == 3
    for argv, model in zip(calls, MODELS, strict=True):
        joined = " ".join(argv)
        assert "--resume" not in argv
        assert "--use-batch-api" not in argv
        assert argv[argv.index("--structured-generation-model") + 1] == model
        assert argv[argv.index("--openai-service-tier") + 1] == "flex"
        assert argv[argv.index("--batch-size") + 1] == "5"
        assert argv[argv.index("--fact-contract") + 1] == "payload_lean_v1"
        assert argv[argv.index("--reasoning-effort") + 1] == "medium"
        assert "--normalize-legacy-frontmatter" in argv
        assert "PREREGISTRATION-DOGFOOD-CONTINUITY-stage4i" not in joined
        assert "gold/entity_anchors.json" not in joined
        assert "gold/fact_anchors.json" not in joined
        assert "temporal_expectations.json" not in joined
    assert receipt["pins"]["prompt"] == receipt["pins"]["prompt"]
    qualification = json.loads((out / "qualification.json").read_text(encoding="utf-8"))
    assert qualification["identity_temporal_scoring"] == "human_review_only"
    assert qualification["single_run_directional_only"] is True
    assert qualification["projections"]["gpt-5.6-luna"]["scale_factor_evidence_units"] == pytest.approx(
        200 / 14
    )


def test_budget_guard_blocks_next_call_before_crossing_ceiling(tmp_path: Path) -> None:
    calls = []
    out = tmp_path / "out"
    with pytest.raises(ExperimentFailure, match="budget_guard_would_exceed_8_usd"):
        _run(
            tmp_path,
            out,
            execute=True,
            runner=_fake_batch(calls, cost=3.0),
            planned_costs={model: 3.0 for model in MODELS},
            budget_ceiling_usd=8.0,
        )
    assert [argv[argv.index("--structured-generation-model") + 1] for argv in calls] == [
        "gpt-5.6-luna",
        "gpt-5.6-terra",
    ]


def test_qualification_refuses_partial_results_unless_stopped_receipt() -> None:
    partial = {"status": "failed", "failure": {"stage": "gpt-5.6-sol", "reason": "x"}, "arms": []}
    with pytest.raises(ValueError, match="partial"):
        qualify_screen(partial)
    stopped = qualify_screen(partial, allow_stopped=True)
    assert stopped["status"] == "stopped"
    assert stopped["identity_temporal_scoring"] == "human_review_only"
