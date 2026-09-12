import json
import subprocess
from pathlib import Path

import pytest

import extraction_lab.run_pair_experiment as runner
from extraction_lab.run_pair_experiment import ExperimentFailure, run_pair_experiment


SHA = "b" * 40


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _fixture(tmp_path):
    repo = tmp_path / "repo"
    corpus = repo / "corpus"
    corpus.mkdir(parents=True)
    (corpus / "session.md").write_text("Brin leads the refugees.\n", encoding="utf-8")
    (repo / "tools").mkdir()
    (repo / "tools" / "batch_ingest_corpus.py").write_text(
        "# existing tool\n", encoding="utf-8"
    )
    _write_json(repo / "entity.json", [])
    _write_json(repo / "fact.json", [])
    _write_json(
        repo / "MODEL_POLICY.json",
        {
            "models": {"fast_smart": "requested-model"},
            "actions": {"structured_generation": "fast_smart"},
        },
    )
    manifest = tmp_path / "manifest.json"
    _write_json(
        manifest,
        {
            "schema": "dmb_extraction_pair_experiment_v1",
            "experiment_id": "pair",
            "repository_sha": SHA,
            "surface": "core_extraction",
            "corpus_root": "corpus",
            "sources": ["session.md"],
            "entity_anchors": "entity.json",
            "fact_anchors": "fact.json",
            "execution": {
                "mode": "realtime",
                "cache_policy": "isolated",
                "repetitions": 1,
            },
            "variants": {"baseline": {"batch_size": 5}, "candidate": {"batch_size": 4}},
        },
    )
    return repo, manifest


def _fake_successful_batch(
    calls, *, entity_model="observed-entity", fact_model="observed-fact"
):
    def fake(argv, cwd):
        calls.append((list(argv), cwd))
        store = Path(argv[argv.index("--store") + 1])
        corpus = Path(argv[argv.index("--corpus-root") + 1])
        paths_file = Path(argv[argv.index("--paths-file") + 1])
        locator = paths_file.read_text(encoding="utf-8").strip()
        _write_json(store / "entities.json", [])
        _write_json(store / "facts.json", [])
        _write_json(
            store / "ingest_index.json",
            {"source": {"source_path": str(corpus / locator)}},
        )
        logs = store / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (store / ".cache").mkdir()
        rows = [
            {"stage": "entity_extraction", "model_name": entity_model},
            {"stage": "fact_extraction", "model_name": fact_model},
        ]
        (logs / "model_calls.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        _write_json(
            logs / "batch_ingest_summary.json", {"results": [{"run_id": "run"}]}
        )
        _write_json(
            logs / "batch_report.json",
            {
                "run_window": {"elapsed_seconds": 1.25},
                "files": {"total": 1, "succeeded": 1, "failed": 0, "skipped": 0},
                "api_calls": {"total": 2},
                "tokens": {"input_tokens": 10, "output_tokens": 5, "cached_tokens": 0},
                "cost_estimate": {"estimated_cost_usd": 0.01},
                "local_cache": {"overall_hit_rate": 0.0},
                "timing": {"total_model_ms": 1000},
            },
        )
        return subprocess.CompletedProcess(argv, 0, stdout="batch ok", stderr="")

    return fake


def _run(repo, manifest, out, **kwargs):
    return run_pair_experiment(
        manifest_path=manifest,
        out_dir=out,
        repo_root=repo,
        repository_sha_reader=lambda _root: SHA,
        worktree_clean_reader=lambda _root: True,
        environ={"OPENAI_API_KEY": "test-only"},
        **kwargs,
    )


def test_default_dry_run_is_inert_and_creates_no_output(tmp_path) -> None:
    repo, manifest = _fixture(tmp_path)
    calls = []
    out = tmp_path / "out"
    result = _run(repo, manifest, out, batch_runner=_fake_successful_batch(calls))
    assert result["mode"] == "dry_run"
    assert result["plan"]["will_execute"] is False
    assert calls == []
    assert not out.exists()


def test_preflight_rejects_wrong_sha_dirty_tree_and_existing_output_before_calls(
    tmp_path,
) -> None:
    repo, manifest = _fixture(tmp_path)
    calls = []
    with pytest.raises(ExperimentFailure, match="repository_sha_mismatch"):
        run_pair_experiment(
            manifest_path=manifest,
            out_dir=tmp_path / "wrong",
            execute=True,
            repo_root=repo,
            batch_runner=_fake_successful_batch(calls),
            repository_sha_reader=lambda _root: "c" * 40,
            worktree_clean_reader=lambda _root: True,
            environ={"OPENAI_API_KEY": "test-only"},
        )
    with pytest.raises(ExperimentFailure, match="worktree_not_clean"):
        run_pair_experiment(
            manifest_path=manifest,
            out_dir=tmp_path / "dirty",
            execute=True,
            repo_root=repo,
            batch_runner=_fake_successful_batch(calls),
            repository_sha_reader=lambda _root: SHA,
            worktree_clean_reader=lambda _root: False,
            environ={"OPENAI_API_KEY": "test-only"},
        )
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ExperimentFailure, match="output_root_already_exists"):
        _run(
            repo,
            manifest,
            existing,
            execute=True,
            batch_runner=_fake_successful_batch(calls),
        )
    assert calls == []


def test_execute_requires_api_key_before_output_or_calls(tmp_path) -> None:
    repo, manifest = _fixture(tmp_path)
    calls = []
    out = tmp_path / "out"
    with pytest.raises(ExperimentFailure, match="openai_api_key_missing"):
        run_pair_experiment(
            manifest_path=manifest,
            out_dir=out,
            execute=True,
            repo_root=repo,
            batch_runner=_fake_successful_batch(calls),
            repository_sha_reader=lambda _root: SHA,
            worktree_clean_reader=lambda _root: True,
            environ={},
        )
    assert calls == []
    assert not out.exists()


def test_successful_pair_is_isolated_observed_and_comparable(tmp_path) -> None:
    repo, manifest = _fixture(tmp_path)
    calls = []
    out = tmp_path / "out"
    policy_before = (repo / "MODEL_POLICY.json").read_bytes()
    receipt = _run(
        repo, manifest, out, execute=True, batch_runner=_fake_successful_batch(calls)
    )
    assert receipt["status"] == "completed"
    assert receipt["comparison"]["comparable"] is True
    assert len(calls) == 2
    baseline_argv, candidate_argv = calls[0][0], calls[1][0]
    assert baseline_argv[baseline_argv.index("--batch-size") + 1] == "5"
    assert candidate_argv[candidate_argv.index("--batch-size") + 1] == "4"
    forbidden = {
        "--resume",
        "--force",
        "--use-batch-api",
        "--enforce-cheap-pass",
        "--auto-escalate",
    }
    assert forbidden.isdisjoint(baseline_argv)
    assert forbidden.isdisjoint(candidate_argv)
    baseline = receipt["variants"]["baseline"]
    candidate = receipt["variants"]["candidate"]
    assert baseline["store_path"] != candidate["store_path"]
    assert baseline["cache_path"] != candidate["cache_path"]
    assert baseline["observed_models"] == {
        "entity_extraction": "observed-entity",
        "fact_extraction": "observed-fact",
    }
    assert baseline["pipeline_contract"]["entity_model"] == "observed-entity"
    assert baseline["telemetry"]["cost_estimate"]["estimated_cost_usd"] == 0.01
    assert (repo / "MODEL_POLICY.json").read_bytes() == policy_before
    serialized = json.dumps(receipt)
    assert "winner" not in serialized.lower()
    assert "promotion" not in serialized.lower()
    assert "READY" not in serialized


def test_candidate_failure_preserves_baseline_and_never_compares(tmp_path) -> None:
    repo, manifest = _fixture(tmp_path)
    calls = []
    success = _fake_successful_batch(calls)

    def fail_candidate(argv, cwd):
        if len(calls) == 1:
            calls.append((list(argv), cwd))
            return subprocess.CompletedProcess(
                argv, 7, stdout="", stderr="candidate failed"
            )
        return success(argv, cwd)

    out = tmp_path / "out"
    with pytest.raises(ExperimentFailure, match="batch_subprocess_exit_7"):
        _run(repo, manifest, out, execute=True, batch_runner=fail_candidate)
    receipt = json.loads((out / "experiment_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "failed"
    assert receipt["variants"]["baseline"]["status"] == "completed"
    assert receipt["variants"]["candidate"]["status"] == "failed"
    assert receipt["comparison"] == {"status": "not_started"}


def test_policy_change_after_baseline_fails_before_candidate(tmp_path) -> None:
    repo, manifest = _fixture(tmp_path)
    calls = []
    success = _fake_successful_batch(calls)

    def mutate_policy(argv, cwd):
        result = success(argv, cwd)
        _write_json(repo / "MODEL_POLICY.json", {"changed": True})
        return result

    out = tmp_path / "out"
    with pytest.raises(
        ExperimentFailure, match="model_policy_changed_during_experiment"
    ):
        _run(repo, manifest, out, execute=True, batch_runner=mutate_policy)
    receipt = json.loads((out / "experiment_receipt.json").read_text(encoding="utf-8"))
    assert len(calls) == 1
    assert receipt["status"] == "failed"
    assert receipt["variants"]["baseline"]["status"] == "completed"
    assert Path(receipt["variants"]["baseline"]["extraction_lab_run_path"]).is_dir()
    assert receipt["variants"]["candidate"]["status"] == "not_started"
    assert receipt["comparison"] == {"status": "not_started"}


def test_ambiguous_observed_model_fails_closed(tmp_path) -> None:
    repo, manifest = _fixture(tmp_path)
    calls = []
    success = _fake_successful_batch(calls)

    def ambiguous(argv, cwd):
        result = success(argv, cwd)
        store = Path(argv[argv.index("--store") + 1])
        with (store / "logs" / "model_calls.jsonl").open(
            "a", encoding="utf-8"
        ) as handle:
            handle.write(
                json.dumps({"stage": "entity_extraction", "model_name": "second-model"})
                + "\n"
            )
        return result

    out = tmp_path / "out"
    with pytest.raises(ExperimentFailure, match="entity_extraction_model_ambiguous"):
        _run(repo, manifest, out, execute=True, batch_runner=ambiguous)
    receipt = json.loads((out / "experiment_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "failed"
    assert receipt["variants"]["candidate"]["status"] == "not_started"


def test_non_comparable_result_is_failed_without_quality_claim(
    monkeypatch, tmp_path
) -> None:
    repo, manifest = _fixture(tmp_path)
    calls = []

    def fake_compare(**_kwargs):
        comparison_dir = _kwargs["out_dir"]
        comparison_dir.mkdir()
        _write_json(comparison_dir / "comparison.json", {"comparable": False})
        (comparison_dir / "report.md").write_text("not comparable\n", encoding="utf-8")
        return {"comparable": False, "non_comparable_reasons": ["fixture_mismatch"]}

    monkeypatch.setattr(runner, "write_comparison", fake_compare)
    out = tmp_path / "out"
    with pytest.raises(ExperimentFailure, match="comparison_not_comparable"):
        _run(
            repo,
            manifest,
            out,
            execute=True,
            batch_runner=_fake_successful_batch(calls),
        )
    receipt = json.loads((out / "experiment_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "failed"
    assert receipt["comparison"]["comparable"] is False
    assert receipt["comparison"]["non_comparable_reasons"] == ["fixture_mismatch"]
