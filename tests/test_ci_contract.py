"""Owning-boundary guards for additive CI command extraction and classification."""

import json
import os
import shutil
import subprocess

import pytest

from scripts import ci_contract as ci


def test_original_commands_are_preserved_exactly_and_workflows_consume_them():
    expected = json.loads((ci.ROOT / "tests/fixtures/ci_original_commands.json").read_text())
    assert ci.contracts() == expected["contracts"]
    world = (ci.ROOT / ".github/workflows/world-ownership-core.yml").read_text()
    hosted = (ci.ROOT / ".github/workflows/hosted-validation.yml").read_text()
    for suite in ("world-and-content", "ingestion-and-review", "query-and-answer", "saved-page-readers"):
        assert f"run: uv run --locked python scripts/ci_contract.py run {suite}" in world
    assert "run: uv run --locked python scripts/ci_contract.py run auth-app" in hosted
    assert "node /workspace/scripts/ci_frontend_contract.mjs" in hosted
    assert '--env GITHUB_SHA="${GITHUB_SHA}"' in hosted


def test_all_discovered_files_are_classified_once():
    result = ci.validate_inventory()
    assert sum(result["lane_file_counts"].values()) == result["discovered_test_files"]


def test_discovery_includes_untracked_files_and_both_python_patterns(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    names = {"tests/test_new.py", "tests/new_test.py", "apps/live-control-ui/src/new.spec.tsx", "apps/live-control-ui/tests/new.pw.ts"}
    for name in names | {"tests/helper.py", "apps/live-control-ui/src/new.tsx"}:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    assert ci.discover(tmp_path) == names
    (tmp_path / "tests/test_new.py").unlink()
    assert ci.discover(tmp_path) == names - {"tests/test_new.py"}


@pytest.mark.parametrize("lanes,found,key", [
    ({"fast": [], "domain-integration": [], "qualification": []}, {"tests/test_new.py"}, "unclassified"),
    ({"fast": ["tests/test_gone.py"], "domain-integration": [], "qualification": []}, set(), "stale"),
    ({"fast": ["tests/test_dup.py"], "domain-integration": [], "qualification": ["tests/test_dup.py"]}, {"tests/test_dup.py"}, "duplicate"),
])
def test_inventory_fails_closed_for_missing_stale_and_duplicate_assignments(tmp_path, monkeypatch, lanes, found, key):
    (tmp_path / "ci").mkdir()
    (tmp_path / "ci/test-classification.json").write_text(json.dumps({"version": 1, "lanes": lanes}))
    monkeypatch.setattr(ci, "discover", lambda root: found)
    with pytest.raises(ValueError, match=key):
        ci.validate_inventory(tmp_path)


def test_python_runner_propagates_failure_and_stops_following_steps(tmp_path, monkeypatch, capsys):
    contract = {"probe": {"steps": [
        {"cwd": ".", "argv": ["{python}", "-c", "raise SystemExit(7)"]},
        {"cwd": ".", "argv": ["{python}", "-c", "open('must-not-run','w').close()"]},
    ]}}
    monkeypatch.setattr(ci, "contracts", lambda root: contract)
    monkeypatch.setattr(ci, "sha", lambda root: "reviewed-sha")
    assert ci.execute("probe", tmp_path) == 7
    assert not (tmp_path / "must-not-run").exists()
    report = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert report["sha"] == "reviewed-sha" and report["exit_code"] == 7
    assert report["elapsed_seconds"] >= 0


def test_changed_discovery_configuration_requires_inventory_review(tmp_path, monkeypatch):
    (tmp_path / "ci").mkdir()
    (tmp_path / "pyproject.toml").write_text('[tool.pytest.ini_options]\ntestpaths = ["tests"]\n')
    (tmp_path / "vite.config.ts").write_text("changed discovery")
    (tmp_path / "ci/test-classification.json").write_text(json.dumps({
        "version": 1, "lanes": {lane: [] for lane in ci.LANES},
        "discovery_config": {"vite.config.ts": "not-the-reviewed-digest"},
    }))
    monkeypatch.setattr(ci, "discover", lambda root: set())
    with pytest.raises(ValueError, match="discovery configuration changed"):
        ci.validate_inventory(tmp_path)


def test_node_runner_propagates_failure_without_git_or_later_steps(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "ci").mkdir()
    shutil.copyfile(ci.ROOT / "scripts/ci_frontend_contract.mjs", tmp_path / "scripts/ci_frontend_contract.mjs")
    steps = [{"cwd": ".", "argv": ["node", "-e", "process.exit(9)"]},
             {"cwd": ".", "argv": ["node", "-e", "require('fs').writeFileSync('must-not-run','')"]}]
    (tmp_path / "ci/contracts.json").write_text(json.dumps({"version": 1, "contracts": {"hosted-frontend": {"steps": steps}}}))
    result = subprocess.run(["node", "scripts/ci_frontend_contract.mjs"], cwd=tmp_path,
                            env={**os.environ, "GITHUB_SHA": "reviewed-sha"}, capture_output=True, text=True)
    assert result.returncode == 9
    assert not (tmp_path / "must-not-run").exists()
    assert json.loads(result.stdout.splitlines()[-1])["sha"] == "reviewed-sha"


def test_split_qualification_commands_preserve_the_complete_full_regression(monkeypatch):
    calls = []
    monkeypatch.setattr(ci, "validate_inventory", lambda root: {})
    monkeypatch.setattr(ci, "sha", lambda root: "a" * 40)
    monkeypatch.setattr(ci.subprocess, "run", lambda argv, **kwargs: (calls.append((argv, kwargs["cwd"])) or subprocess.CompletedProcess(argv, 0)))
    assert ci.execute("full-regression") == 0
    original = list(calls)
    calls.clear()
    for name in ("full-backend", "qualification-vitest", "qualification-build", "qualification-visual"):
        assert ci.execute(name) == 0
    assert calls == original
    assert [argv for argv, _ in original] == [[ci.sys.executable, "-m", "pytest", "tests"],
        ["npm", "test"], ["npm", "run", "build"], ["npm", "run", "ui:visual"]]
