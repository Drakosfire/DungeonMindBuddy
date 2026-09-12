import json
from pathlib import Path

import pytest

from extraction_lab.run_campaign_memory_baseline import run_campaign_memory_baseline
from extraction_lab.run_pair_experiment import ExperimentFailure
from tests.extraction_lab.test_campaign_memory_baseline_manifest import manifest_payload


ROOT = Path(__file__).resolve().parents[2]


def test_default_is_inert_dry_run(tmp_path: Path) -> None:
    payload = manifest_payload()
    import subprocess

    payload["repository_sha"] = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out"
    result = run_campaign_memory_baseline(
        manifest_path=manifest, out_dir=out, repo_root=ROOT
    )
    assert result["mode"] == "dry_run"
    assert result["plan"]["source_ingestions"] == 21
    assert result["plan"]["experiment_model"] == "gpt-5.6-sol"
    assert result["plan"]["pricing_per_million_tokens_usd"] == {
        "input": 2.0,
        "cached_input": 0.2,
        "output": 10.0,
    }
    assert not out.exists()


def test_paid_command_explicitly_normalizes_frozen_legacy_frontmatter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = manifest_payload()
    import subprocess

    payload["repository_sha"] = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "extraction_lab.run_campaign_memory_baseline._worktree_clean",
        lambda _root: True,
    )

    def fake_batch(argv: list[str], _cwd: Path):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 1, "", "stopped")

    with pytest.raises(ExperimentFailure, match="batch_subprocess_exit_1"):
        run_campaign_memory_baseline(
            manifest_path=manifest,
            out_dir=tmp_path / "out",
            repo_root=ROOT,
            execute=True,
            batch_runner=fake_batch,
            environ={"OPENAI_API_KEY": "test"},
        )

    assert "--normalize-legacy-frontmatter" in calls[0]
